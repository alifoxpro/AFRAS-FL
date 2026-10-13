#!/usr/bin/env python3
"""Pre-window, per-link record partitions for scientific evaluation.

Ordered 70/15/15 split with an embargo between partitions. Optionally
fail if a group identifier appears in two partitions. This utility does NOT
train a model, validate prior preprocessing, or certify end-to-end absence
of leakage. Existing teacher checkpoints/caches must NOT be reused.
"""
import argparse
import csv
import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

LINK_PATTERN = "Link_*.csv"
SPLITS = ("train", "val", "test")


def digest_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ordered_ranges(n_rows, window_size=20, proportions=(0.70, 0.15, 0.15)):
    """Return nonoverlapping half-open row ranges with W-1 embargo rows."""
    if window_size < 2:
        raise ValueError("window_size must be at least 2")
    if len(proportions) != 3 or abs(sum(proportions) - 1.0) > 1e-8:
        raise ValueError("proportions must total 1")
    embargo = window_size - 1
    usable = n_rows - 2 * embargo
    if usable < 3 * window_size:
        raise ValueError("Not enough original records for all three windows")
    n_train = int(usable * proportions[0])
    n_val = int(usable * proportions[1])
    n_test = usable - n_train - n_val
    if min(n_train, n_val, n_test) < window_size:
        raise ValueError("Each split must retain at least one full window")
    r = {
        "train": (0, n_train),
        "val": (n_train + embargo, n_train + embargo + n_val),
        "test": (n_train + embargo + n_val + embargo, n_rows),
    }
    assert r["train"][1] + embargo == r["val"][0]
    assert r["val"][1] + embargo == r["test"][0]
    return r


def _time_key(value):
    value = value.strip()
    if not value:
        raise ValueError("Empty time-column value")
    try:
        return (0, float(value))
    except ValueError:
        return (1, datetime.fromisoformat(value.replace("Z", "+00:00")))


def _count_source(path, group_column=None, time_column=None):
    count = 0
    previous_time = None
    with open(path, newline="", encoding="utf-8-sig") as inp:
        reader = csv.DictReader(inp)
        fields = reader.fieldnames
        if not fields or "severity" not in fields:
            raise ValueError(f"{path}: missing 'severity' column")
        if "__afras_source_row_id" in fields:
            raise ValueError("Input already contains generated source-row IDs")
        for name in (group_column, time_column):
            if name and name not in fields:
                raise ValueError(f"{path}: missing required column '{name}'")
        for row in reader:
            if row.get("severity") is None or not row["severity"].strip():
                raise ValueError(f"{path}: missing severity label at record {count}")
            if time_column:
                key = _time_key(row[time_column])
                if previous_time is not None and key < previous_time:
                    raise ValueError(
                        f"{path}: time column is not nondecreasing at record {count}")
                previous_time = key
            count += 1
    return count, fields


def _partition_for_index(idx, ranges):
    for name in SPLITS:
        start, stop = ranges[name]
        if start <= idx < stop:
            return name
    return None  # embargo record


def _split_one(source, dataset_root, window_size, group_column, time_column):
    n, fields = _count_source(source, group_column, time_column)
    ranges = ordered_ranges(n, window_size)
    basename = source.name
    handles = {}
    writers = {}
    group_db = None
    counts = Counter()
    class_counts = {part: Counter() for part in SPLITS}
    try:
        for part in SPLITS:
            directory = dataset_root / part
            directory.mkdir(parents=True, exist_ok=True)
            f = open(directory / basename, "w", newline="", encoding="utf-8")
            handles[part] = f
            writer = csv.DictWriter(f, fieldnames=fields + ["__afras_source_row_id"])
            writer.writeheader()
            writers[part] = writer
        if group_column:
            group_db = sqlite3.connect(str(dataset_root / "__cross_link_group_index.sqlite"))
            group_db.execute(
                "CREATE TABLE IF NOT EXISTS groups (grp TEXT PRIMARY KEY, partition TEXT NOT NULL)")
        with open(source, newline="", encoding="utf-8-sig") as inp:
            reader = csv.DictReader(inp)
            for idx, record in enumerate(reader):
                part = _partition_for_index(idx, ranges)
                if part is None:
                    continue
                if group_db:
                    group = record[group_column].strip()
                    if not group:
                        raise ValueError(f"Empty group at row {idx} of {basename}")
                    group_db.execute(
                        "INSERT OR IGNORE INTO groups(grp, partition) VALUES (?, ?)",
                        (group, part))
                    got = group_db.execute(
                        "SELECT partition FROM groups WHERE grp = ?", (group,)
                    ).fetchone()[0]
                    if got != part:
                        raise ValueError(
                            f"Group '{group}' crosses {got}/{part} in {basename}; "
                            "use group-aware source partitioning, not this ordered splitter")
                record["__afras_source_row_id"] = str(idx)
                writers[part].writerow(record)
                counts[part] += 1
                class_counts[part][record["severity"]] += 1
    finally:
        for f in handles.values():
            f.close()
        if group_db:
            group_db.close()
    for part in SPLITS:
        if counts[part] != ranges[part][1] - ranges[part][0]:
            raise RuntimeError("Partition count mismatch")
    return {
        "source_file": basename,
        "source_sha256": digest_file(source),
        "n_original": n,
        "embargo_rows_at_each_boundary": window_size - 1,
        "ranges_half_open": {k: list(v) for k, v in ranges.items()},
        "group_column_checked": group_column,
        "time_column_checked": time_column,
        "partitions": {
            part: {
                "records": counts[part],
                "severity_counts": dict(class_counts[part]),
                "relative_path": f"{part}/{basename}",
                "sha256": digest_file(dataset_root / part / basename),
            } for part in SPLITS
        },
    }


def split_dataset(input_dir, output_root, dataset, window_size=20,
                  group_column=None, time_column=None,
                  allow_exploratory_synthetic_links=False):
    """Refuse overwriting existing data, and publish only after all links pass."""
    input_dir, output_root = Path(input_dir).resolve(), Path(output_root).resolve()
    files = sorted(input_dir.glob(LINK_PATTERN))
    if not files:
        raise FileNotFoundError(f"No {LINK_PATTERN} input files in {input_dir}")
    harmonization = None
    source_report = input_dir / "harmonization_manifest.json"
    if source_report.is_file():
        harmonization = json.loads(source_report.read_text(encoding="utf-8"))
        if (harmonization.get("schema") != "afras-harmonized-full-candidate-v2"
                or harmonization.get("dataset") != dataset
                or set(harmonization.get("link_files", {})) !=
                   {f.stem for f in files}):
            raise ValueError("Invalid source harmonization manifest / five-link inventory")
        for source in files:
            provenance = harmonization["link_files"][source.stem]
            if (provenance.get("file") != source.name
                    or provenance.get("sha256") != digest_file(source)):
                raise ValueError(f"Harmonized source file changed: {source}")
        if (harmonization.get("link_assignment_mode") ==
                "EXPLORATORY_SYNTHETIC_NONPHYSICAL"
                and not allow_exploratory_synthetic_links):
            raise ValueError(
                "Synthetic nonphysical links cannot enter strict splits by default. "
                "Use --allow-exploratory-synthetic-links ONLY for visibly tagged pilots")
    target = output_root / dataset
    if target.exists():
        raise FileExistsError(f"Split output already exists: {target}")
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{dataset}-staging-", dir=output_root) as tmp:
        stage = Path(tmp)
        manifests = {}
        for source in files:
            manifests[source.stem] = _split_one(
                source, stage, window_size, group_column, time_column)
        # Global key index covers ALL links. Do not publish the SQLite scratch file.
        (stage / "__cross_link_group_index.sqlite").unlink(missing_ok=True)
        manifest = {
            "schema": "afras-fl-strict-ordered-split-v1",
            "dataset": dataset,
            "method": "source_order_with_embargo; split_before_windowing",
            "window_size": window_size,
            "proportions_requested": [0.70, 0.15, 0.15],
            "source_harmonization": ({
                "manifest_sha256": digest_file(source_report),
                "link_assignment_mode": harmonization["link_assignment_mode"],
                "topology_independently_verified":
                    harmonization.get("topology_independently_verified", False),
            } if harmonization else None),
            "group_disjoint_verified": bool(group_column),
            "group_disjoint_scope": "ALL_CLIENT_LINKS_WITHIN_DATASET" if group_column else None,
            "time_order_verified": bool(time_column),
            "limitations": [
                "Source order must represent a defensible chronology or sequence.",
                "Exact duplicate features and earlier upstream transformations are not audited.",
                "No teacher checkpoint, scaler, PCA or fuzzy rules may be fitted on val/test.",
                "An untouched independent test must remain sealed until final evaluation.",
            ],
            "links": manifests,
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        os.rename(stage, target)
    return target


def main():
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", nargs="+", default=["ciciot2023", "diad2024"])
    parser.add_argument("--input-root", type=Path, required=True,
                        help="Explicit path to independently reviewed UNSELECTED candidate-feature source CSVs")
    parser.add_argument("--output-root", type=Path, default=repo / "data" / "full_candidate_strict_split")
    parser.add_argument("--window-size", type=int, default=20)
    parser.add_argument("--group-column", default=None,
                        help="If provided, abort when a group appears in two splits")
    parser.add_argument("--time-column", default=None,
                        help="If provided, require nondecreasing numeric/ISO time")
    parser.add_argument("--allow-exploratory-synthetic-links", action="store_true",
                        help="ALLOW only labeled synthetic pilot shards; strict Stage 3 refuses these")
    args = parser.parse_args()
    for dataset in args.datasets:
        target = split_dataset(
            args.input_root / dataset, args.output_root, dataset,
            window_size=args.window_size,
            group_column=args.group_column,
            time_column=args.time_column,
            allow_exploratory_synthetic_links=args.allow_exploratory_synthetic_links,
        )
        print(f"Created {target} (manifest.json + per-link train/val/test CSV files)")


if __name__ == "__main__":
    main()
