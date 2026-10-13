#!/usr/bin/env python3
"""Inventory the ACTUAL original CSVs: labels, columns, counts and SHA-256.

This is a pre-experiment source audit, NOT a label/severity mapper, not a
classifier and not a claim of external dataset authenticity. Does not infer
Benign from Low. Do not scan a sealed TEST partition with this utility.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

OFFICIAL_PAGES = {
    "ciciot2023": "https://www.unb.ca/cic/datasets/iotdataset-2023.html",
    "diad2024": "https://www.unb.ca/cic/datasets/iot-diad-2024.html",
}
SCHEMA = "afras-original-csv-inventory-v1"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_csv(path, label_column):
    if not label_column or label_column in ("severity", "__afras_source_row_id"):
        raise ValueError("Specify an original raw label column, not derived severity")
    counts = Counter()
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        if not fields or len(fields) != len(set(fields)):
            raise ValueError(f"Missing/duplicated raw CSV headers: {path}")
        if label_column not in fields:
            raise ValueError(f"Original label column {label_column!r} missing: {path}")
        for row_num, row in enumerate(reader, start=2):
            category = row.get(label_column)
            if category is None or not category.strip():
                raise ValueError(f"Blank original label at {path}:{row_num}")
            if None in row:  # too many fields vs header
                raise ValueError(f"Malformed CSV field count at {path}:{row_num}")
            if any(value is None for value in row.values()):
                raise ValueError(f"Missing trailing CSV fields at {path}:{row_num}")
            counts[category] += 1
    if not counts:
        raise ValueError(f"Empty original raw CSV: {path}")
    return {
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "rows": sum(counts.values()),
        "original_label_counts": dict(sorted(counts.items())),
        "columns": fields,
    }


def inventory(dataset, root, label_column, output, modality=None,
              source_artifact=None, reference_sha256=None, file_pattern="*.csv"):
    """Refuses overwrite and refuses to claim source verification without a digest."""
    if dataset not in OFFICIAL_PAGES:
        raise ValueError("Unrecognized benchmark identity")
    root, output = Path(root).resolve(), Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite earlier inventory: {output}")
    if not root.is_dir():
        raise FileNotFoundError(f"Original CSV directory not found: {root}")
    if not modality or modality not in ("flow", "packet"):
        raise ValueError("Declare source modality explicitly: flow or packet")
    if reference_sha256 and not source_artifact:
        raise ValueError("Reference digest supplied without original source artifact")
    if reference_sha256 and (len(reference_sha256) != 64 or
                             any(c not in "0123456789abcdef" for c in reference_sha256)):
        raise ValueError("Expected reference digest must be lowercase SHA-256")
    if not file_pattern.endswith(".csv") or ".." in file_pattern:
        raise ValueError("CSV glob pattern must end in .csv")
    files = sorted(p for p in root.rglob(file_pattern) if p.is_file())
    if not files:
        raise FileNotFoundError(f"No matching raw CSV files at {root}")
    if source_artifact:
        source_artifact = Path(source_artifact).resolve()
        if not source_artifact.is_file():
            raise FileNotFoundError(f"Original source artifact missing: {source_artifact}")
        actual_source_hash = sha256(source_artifact)
        if reference_sha256 and reference_sha256 != actual_source_hash:
            raise ValueError("Original artifact SHA-256 differs from reference digest")
    else:
        actual_source_hash = None
    details, aggregate = {}, Counter()
    total_rows = 0
    for file in files:
        rel = file.relative_to(root).as_posix()
        item = audit_csv(file, label_column)
        details[rel] = item
        total_rows += item["rows"]
        aggregate.update(item["original_label_counts"])
    result = {
        "schema": SCHEMA,
        "dataset": dataset,
        "modality": modality,
        "official_description_url": OFFICIAL_PAGES[dataset],
        "original_label_column_user_declared": label_column,
        "source_artifact_sha256": actual_source_hash,
        "reference_sha256_confirmed": bool(reference_sha256),
        "external_source_authenticity_reviewed": False,
        "severity_mapping_verified": False,
        "source_files_count": len(files),
        "original_rows": total_rows,
        "all_original_label_counts": dict(sorted(aggregate.items())),
        "files": details,
        "warnings": [
            "Original CSV labels and digests were measured locally, NOT independently certified",
            "Any High/Medium/Low severity mapping requires separate documented review",
            "The official pages describe categories but do not authenticate these local bytes",
            "This audit reads RAW source files, never TRAIN/VAL/TEST partition outputs",
            "Do not claim a DIAD2024 zero-shot test if DIAD labels inform model development",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=sorted(OFFICIAL_PAGES), required=True)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--label-column", required=True)
    parser.add_argument("--modality", choices=("flow", "packet"), required=True)
    parser.add_argument("--source-artifact", type=Path)
    parser.add_argument("--reference-sha256", help="Trusted independently recorded digest")
    parser.add_argument("--file-pattern", default="*.csv")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = inventory(args.dataset, args.input_dir, args.label_column, args.output,
                       modality=args.modality, source_artifact=args.source_artifact,
                       reference_sha256=args.reference_sha256,
                       file_pattern=args.file_pattern)
    print(f"Inventory of {report['source_files_count']} original files, "
          f"{report['original_rows']} rows saved to {args.output}; "
          "severity_mapping_verified=False")


if __name__ == "__main__":
    main()
