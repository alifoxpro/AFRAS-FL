"""Fail-closed raw-category and binary-label audit; stdlib-only.

This checks consistency with a *declared* source mapping and recorded CSV hashes.
It cannot independently prove authenticity of original dataset annotations.
No category is silently assumed to be Benign merely because severity is Low.
"""
import csv
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "afras-raw-label-evidence-v1"
SEVERITIES = ("High", "Medium", "Low")
HEX_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_evidence_file(path, dataset):
    """Validate an explicit, pre-registered map; no default/inferred mappings."""
    path = Path(path).resolve()
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("schema") != SCHEMA or obj.get("dataset") != dataset:
        raise ValueError("Raw-label evidence schema or dataset mismatch")
    for key in ("source_url", "source_revision", "mapping_review_reference"):
        value = obj.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing declared source provenance: {key}")
    if not obj["source_url"].startswith("https://"):
        raise ValueError("A resolvable HTTPS original-source URL is required")
    if not isinstance(obj.get("source_sha256"), str) or not HEX_SHA256.fullmatch(obj["source_sha256"]):
        raise ValueError("Original dataset SHA-256 must be provided")
    raw = obj.get("raw_label_column")
    binary = obj.get("binary_attack_column")
    if not isinstance(raw, str) or not isinstance(binary, str) or not raw or not binary:
        raise ValueError("Explicit raw label and binary attack column names required")
    if raw == binary or raw == "severity" or binary == "severity":
        raise ValueError("Raw, binary and severity columns must be distinct")
    mp = obj.get("raw_label_map")
    if not isinstance(mp, dict) or not mp:
        raise ValueError("An exhaustive, nonempty raw-label mapping is required")
    for category, labels in mp.items():
        if not isinstance(category, str) or not category.strip():
            raise ValueError("Raw category names must be strings")
        if not isinstance(labels, dict) or labels.get("severity") not in SEVERITIES:
            raise ValueError(f"Missing severity mapping for raw category: {category}")
        if type(labels.get("is_attack")) is not int or labels["is_attack"] not in (0, 1):
            raise ValueError(f"Missing binary attack mapping for raw category: {category}")
    return obj


def validate_raw_rows(csv_path, evidence, expected_sha256=None, take_binary_last=None):
    """Audit every CSV row, including its original raw/binary fields.

    If window_size/stride specified, return attack labels from LAST record
    of each window, exactly matching create_windows() end-of-window labels.
    """
    csv_path = Path(csv_path)
    if expected_sha256 is not None and sha256(csv_path) != expected_sha256:
        raise ValueError(f"Source partition hash mismatch: {csv_path}")
    raw_key, binary_key = evidence["raw_label_column"], evidence["binary_attack_column"]
    required = {raw_key, binary_key, "severity", "__afras_source_row_id"}
    mapping = evidence["raw_label_map"]
    window_size, stride = take_binary_last if take_binary_last else (None, None)
    if take_binary_last and (window_size < 1 or stride < 1):
        raise ValueError("window_size and stride must be positive")
    window_labels = []
    category_count = {}
    previous_id = -1
    nrows = 0
    with open(csv_path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"Missing raw-label provenance columns in {csv_path}: "
                             f"{sorted(required-set(reader.fieldnames or []))}")
        for i, row in enumerate(reader):
            original = row[raw_key]
            if original not in mapping:
                raise ValueError(f"Unmapped raw category {original!r} at CSV row {i}")
            expected = mapping[original]
            if row["severity"] != expected["severity"]:
                raise ValueError(f"Severity mismatch for {original!r} at CSV row {i}")
            if row[binary_key] not in ("0", "1") or int(row[binary_key]) != expected["is_attack"]:
                raise ValueError(f"Binary Attack/Benign mismatch at CSV row {i}")
            try:
                source_id = int(row["__afras_source_row_id"])
            except (ValueError, TypeError) as exc:
                raise ValueError("Missing/invalid original source row ID") from exc
            if source_id <= previous_id:
                raise ValueError("Source row IDs are non-increasing or duplicated")
            previous_id = source_id
            category_count[original] = category_count.get(original, 0) + 1
            if take_binary_last and i >= window_size - 1 and (i - (window_size-1)) % stride == 0:
                window_labels.append(int(row[binary_key]))
            nrows += 1
    if nrows == 0:
        raise ValueError("Empty source partition")
    return {"rows": nrows, "category_counts": category_count,
            "binary_window_labels": window_labels if take_binary_last else None}


def audit_train_val(split_dir, dataset, evidence_path):
    """Never read TEST CSV in the train/validation stage."""
    split_dir = Path(split_dir)
    evidence = validate_evidence_file(evidence_path, dataset)
    m = json.loads((split_dir / "manifest.json").read_text(encoding="utf-8"))
    if m.get("dataset") != dataset:
        raise ValueError("Split manifest belongs to another dataset")
    links = m.get("links", {})
    if not links:
        raise ValueError("Empty split manifest")
    summary = {}
    for link, meta in sorted(links.items()):
        summary[link] = {}
        for part in ("train", "val"):
            path = split_dir / part / (link + ".csv")
            expected = meta["partitions"][part]
            data = validate_raw_rows(path, evidence, expected["sha256"])
            if data["rows"] != expected["records"]:
                raise ValueError("Partition record count mismatch")
            summary[link][part] = data["category_counts"]
    return {"schema": SCHEMA, "dataset": dataset,
            "evidence_sha256": sha256(evidence_path),
            "source_provenance": {
                k: evidence[k] for k in
                ("source_url", "source_revision", "source_sha256",
                 "mapping_review_reference")},
            "train_val_categories": summary,
            "caveat": "Declared CSV lineage, not independent validation of original annotations"}
