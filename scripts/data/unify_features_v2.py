#!/usr/bin/env python3
"""Audited, streaming replacement for missing historical unify_features.py.

Works on the actual original CSV files; NEVER downloads, imputes, scales,
selects features, invents severities, or claims synthetic links are real SDN
nodes. Review source labels, candidate features and link provenance BEFORE
running this on either official benchmark.

This is a NEW protocol, not a reconstruction of the missing historic script.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.data.audit_original_csvs import OFFICIAL_PAGES
from scripts.data.label_evidence import validate_evidence_file
from scripts.data.select_features_train_only import REJECT
from scripts.data.review_raw_category_mapping import review_category_mapping

SCHEMA = "afras-harmonization-v2-config-v1"
OUTPUT_SCHEMA = "afras-harmonized-full-candidate-v2"
LINKS = ("Link_1_Core", "Link_2_Aggregation_L", "Link_3_Aggregation_R",
         "Link_4_Edge_L", "Link_5_Edge_R")
ORIGIN_FIELDS = ("__afras_original_file", "__afras_original_row",
                 "__afras_original_csv_sha256")
META_GROUP = "__afras_original_group"
META_TIME = "__afras_original_time"


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _require(ok, detail):
    if not ok:
        raise ValueError(detail)


def load_config(path, evidence, inventory, dataset, synthetic):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    _require(isinstance(config, dict) and config.get("schema") == SCHEMA
             and config.get("dataset") == dataset, "Invalid harmonization config/dataset")
    _require(config.get("modality") == inventory.get("modality"),
             "Flow/packet modality mismatch; do not mix feature formats")
    _require(config.get("modality") in ("flow", "packet"), "Unknown source modality")
    _require(config.get("source_review_reference"), "Missing source review reference")
    _require(evidence["raw_label_column"] == inventory.get("original_label_column_user_declared"),
             "Original raw label name disagrees with inventory")
    _require(evidence.get("source_url") == OFFICIAL_PAGES[dataset],
             "Mapping must identify the official benchmark documentation URL")
    mapping = config.get("feature_sources")
    _require(isinstance(mapping, dict) and len(mapping) >= 15,
             "At least 15 reviewed candidate features required, not preselected 14")
    _require(all(isinstance(k, str) and k and not REJECT.search(k)
                 and isinstance(v, str) and v and not v.startswith("__")
                 for k, v in mapping.items()),
             "Invalid or protected feature names/source columns")
    _require(len(set(mapping.values())) == len(mapping),
             "Two output candidate features cannot alias one source column")
    _require(evidence["raw_label_column"] not in mapping.values()
             and evidence["binary_attack_column"] not in mapping.values(),
             "A target/binary label cannot be used as an input feature")
    _require(not set(mapping).intersection({evidence["raw_label_column"],
             evidence["binary_attack_column"], "severity", *ORIGIN_FIELDS,
             META_GROUP, META_TIME}), "Feature name collides with provenance column")

    group_column, time_column = config.get("group_column"), config.get("time_column")
    for col in (group_column, time_column):
        _require(col is None or (isinstance(col, str) and bool(col) and
                 not col.startswith("__")), "Invalid group/time source column")
    _require(group_column != time_column or group_column is None,
             "Group and timestamp source fields must differ")

    raw_link = config.get("link_column")
    link_values = config.get("link_values")
    if synthetic:
        _require(raw_link is None and link_values is None,
                 "Synthetic links cannot be combined with declared original link IDs")
    else:
        _require(isinstance(raw_link, str) and bool(raw_link),
                 "No actual source link ID; use --exploratory-synthetic-links "
                 "ONLY for explicitly nonphysical pilot data")
        _require(isinstance(link_values, dict) and len(link_values) == 5 and
                 set(link_values.values()) == set(LINKS),
                 "An explicitly reviewed one-to-one mapping of five real source link IDs is required")
        _require(all(isinstance(k, str) and k for k in link_values),
                 "Invalid source link value")
        _require(raw_link not in mapping.values()
                 and raw_link not in (evidence["raw_label_column"],
                                     evidence["binary_attack_column"]),
                 "Link identifiers must not become predictive features")
    blocked_meta = set(mapping.values()) | {evidence["raw_label_column"]}
    _require((not group_column or group_column not in blocked_meta)
             and (not time_column or time_column not in blocked_meta),
             "Group/time metadata cannot appear among model features")
    return config


def run(dataset, raw_dir, inventory_path, mapping_path, config_path, output_root,
        exploratory_synthetic_links=False):
    """Fail closed and publish atomically: NO half-processed datasets."""
    raw_dir = Path(raw_dir).resolve()
    output_root = Path(output_root).resolve()
    inventory_path = Path(inventory_path).resolve()
    mapping_path = Path(mapping_path).resolve()
    config_path = Path(config_path).resolve()
    target = output_root / dataset
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite harmonized data: {target}")
    _require(dataset in OFFICIAL_PAGES, "Unknown dataset")
    _require(raw_dir.is_dir(), "Missing real raw CSV directory")
    _require(not output_root.is_relative_to(raw_dir),
             "Output directory cannot be inside raw source tree")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    _require(inventory.get("schema") == "afras-original-csv-inventory-v1"
             and inventory.get("dataset") == dataset,
             "Original inventory schema/dataset mismatch")
    evidence = validate_evidence_file(mapping_path, dataset)
    # This also checks that EVERY observed attack category is mapped and
    # compares the declared source archive digest when one was inventoried.
    coverage = review_category_mapping(inventory_path, mapping_path, dataset)
    config = load_config(config_path, evidence, inventory, dataset,
                         exploratory_synthetic_links)
    files_meta = inventory.get("files")
    _require(isinstance(files_meta, dict) and files_meta,
             "No inventoried original CSVs")
    filepaths = {}
    for rel, meta in sorted(files_meta.items()):
        _require(isinstance(rel, str) and not Path(rel).is_absolute() and
                 ".." not in Path(rel).parts and rel.endswith(".csv"),
                 f"Unsafe source relative path {rel!r}")
        file = (raw_dir / rel).resolve()
        _require(file.is_file() and file.is_relative_to(raw_dir),
                 f"Source file not found within audited raw tree: {rel}")
        _require(digest(file) == meta.get("sha256"),
                 f"Source file checksum mismatch: {rel}")
        filepaths[rel] = file

    features = list(config["feature_sources"])
    fields = (features + ["severity", evidence["raw_label_column"],
              evidence["binary_attack_column"]] + list(ORIGIN_FIELDS))
    if config.get("group_column"):
        fields.append(META_GROUP)
    if config.get("time_column"):
        fields.append(META_TIME)
    _require(len(fields) == len(set(fields)), "Duplicate output header fields")
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_root, prefix=f".{dataset}-v2-staging-") as tmp:
        stage = Path(tmp)
        handles, writers = {}, {}
        try:
            for link in LINKS:
                handle = (stage / (link + ".csv")).open("w", encoding="utf-8", newline="")
                handles[link] = handle
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writers[link] = writer
            per_link = Counter()
            per_label = Counter()
            n = 0
            seen_link_vals = set()
            file_rows = {}
            for rel, file in filepaths.items():
                expected = files_meta[rel]
                current = 0
                with file.open("r", encoding="utf-8-sig", newline="") as inp:
                    reader = csv.DictReader(inp)
                    cols = reader.fieldnames
                    _require(cols and len(cols) == len(set(cols)),
                             f"Duplicate or missing CSV header: {rel}")
                    needed = (set(config["feature_sources"].values()) |
                              {evidence["raw_label_column"]})
                    needed |= {c for c in (config.get("group_column"),
                                            config.get("time_column"),
                                            config.get("link_column")) if c}
                    _require(needed.issubset(cols),
                             f"Missing original columns from {rel}: {sorted(needed-set(cols))}")
                    for idx, row in enumerate(reader):
                        _require(None not in row and all(v is not None for v in row.values()),
                                 f"Malformed original row in {rel}:{idx+2}")
                        category = row[evidence["raw_label_column"]]
                        _require(category in evidence["raw_label_map"],
                                 f"Unmapped original label {category!r} at {rel}:{idx+2}")
                        observed = evidence["raw_label_map"][category]
                        if exploratory_synthetic_links:
                            # Deterministic balanced shards, not measured SDN links.
                            link = LINKS[n % len(LINKS)]
                        else:
                            raw_link = row[config["link_column"]]
                            _require(raw_link in config["link_values"],
                                     f"Unmapped actual source link {raw_link!r} in {rel}:{idx+2}")
                            seen_link_vals.add(raw_link)
                            link = config["link_values"][raw_link]
                        out = {}
                        for name, original in config["feature_sources"].items():
                            raw_val = row[original].strip()
                            try:
                                val = float(raw_val)
                            except ValueError as exc:
                                raise ValueError(
                                    f"Non-numeric candidate feature {original!r} at {rel}:{idx+2}") from exc
                            _require(math.isfinite(val),
                                     f"Nonfinite feature {original!r} at {rel}:{idx+2}; "
                                     "no across-split imputation is permitted")
                            out[name] = raw_val
                        out["severity"] = observed["severity"]
                        out[evidence["raw_label_column"]] = category
                        out[evidence["binary_attack_column"]] = str(observed["is_attack"])
                        out["__afras_original_file"] = rel
                        out["__afras_original_row"] = str(idx)
                        out["__afras_original_csv_sha256"] = expected["sha256"]
                        for key, dest in ((config.get("group_column"), META_GROUP),
                                          (config.get("time_column"), META_TIME)):
                            if key:
                                value = row[key].strip()
                                _require(value != "", f"Missing original {key} at {rel}:{idx+2}")
                                out[dest] = value
                        writers[link].writerow(out)
                        per_link[link] += 1
                        per_label[category] += 1
                        n += 1
                        current += 1
                _require(current == expected.get("rows"),
                         f"Source CSV row count mismatch: {rel}")
                _require(digest(file) == expected["sha256"],
                         f"Original source changed during conversion: {rel}")
                file_rows[rel] = current
            _require(n == inventory.get("original_rows"),
                     "Inventoried original row count != harmonized row count")
            _require(dict(per_label) == inventory.get("all_original_label_counts"),
                     "Original attack-label counts changed during harmonization")
            _require(all(per_link[l] for l in LINKS),
                     "Five nonempty links are required")
            if not exploratory_synthetic_links:
                _require(seen_link_vals == set(config["link_values"]),
                         "Not all five declared original link identities were observed")
        finally:
            for handle in handles.values():
                handle.close()

        mode = ("EXPLORATORY_SYNTHETIC_NONPHYSICAL" if exploratory_synthetic_links
                else "DECLARED_SOURCE_LINK_MAPPING_UNVERIFIED_TOPOLOGY")
        report = {
            "schema": OUTPUT_SCHEMA,
            "dataset": dataset, "modality": config["modality"],
            "link_assignment_mode": mode,
            "source_inventory_sha256": digest(inventory_path),
            "mapping_evidence_sha256": digest(mapping_path),
            "harmonization_config_sha256": digest(config_path),
            "source_review_reference": config["source_review_reference"],
            "original_source_artifact_sha256": inventory.get("source_artifact_sha256"),
            "external_source_authenticity_reviewed": False,
            "topology_independently_verified": False,
            "severity_policy_independently_verified": False,
            "complete_original_label_coverage_checked": coverage["complete_category_coverage"],
            "raw_original_rows": n,
            "raw_file_rows": file_rows,
            "raw_label_counts": dict(sorted(per_label.items())),
            "candidate_features": features,
            "source_feature_columns": config["feature_sources"],
            "raw_label_column": evidence["raw_label_column"],
            "derived_binary_attack_column": evidence["binary_attack_column"],
            "group_column_for_split": META_GROUP if config.get("group_column") else None,
            "time_column_for_split": META_TIME if config.get("time_column") else None,
            "link_files": {
                link: {
                    "file": link + ".csv",
                    "sha256": digest(stage / (link+".csv")),
                    "rows": per_link[link],
                } for link in LINKS
            },
            "restrictions": [
                "Do not claim actual five-SDN-link topology without independently verified link identity",
                "Synthetic links cannot support confirmatory network topology/generalization claims",
                "Pre-split chronological ordering, device/group overlap and duplicate flows remain unverified",
                "Use split-before-window, TRAIN-only feature selection and TRAIN-fitted normalization",
                "Preserved source labels and researcher-reviewed severity are not proof of mapping validity",
                "This NEW preprocessing cannot reproduce the missing historical code by itself",
            ],
        }
        (stage / "harmonization_manifest.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        os.rename(stage, target)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(OFFICIAL_PAGES), required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--label-evidence", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path,
                        default=REPO / "data" / "full_candidate_5links")
    parser.add_argument("--exploratory-synthetic-links", action="store_true",
                        help="Deterministic NONPHYSICAL five-way shards: exploratory ONLY")
    args = parser.parse_args()
    manifest = run(args.dataset, args.input_dir, args.inventory,
                   args.label_evidence, args.config, args.output_root,
                   exploratory_synthetic_links=args.exploratory_synthetic_links)
    print(f"Created {args.dataset}: {manifest['raw_original_rows']} source rows; "
          f"{manifest['link_assignment_mode']}. "
          "Original data integrity/topology not independently certified.")


if __name__ == "__main__":
    main()
