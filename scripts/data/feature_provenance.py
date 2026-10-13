"""Validate predeclared TRAIN-only feature-selection provenance.

This gate reads the split MANIFEST, not VAL/TEST CSVs. It cannot guarantee
pre-split source harmonization is free of leakage; it rejects the historically
globally-selected feature list when training new strict experiments.
"""
import json
from pathlib import Path

from scripts.data.select_features_train_only import (
    SCHEMA, REJECT, SPLIT_SCHEMA, sha256,
)


def validate_train_feature_selection(feature_path, split_root, dataset, n_features=14):
    feature_path = Path(feature_path)
    selected = json.loads(feature_path.read_text(encoding="utf-8"))
    if not isinstance(selected, dict) or selected.get("schema") != SCHEMA:
        raise ValueError(
            "Global or unverified feature selection refused. Use TRAIN-only "
            "scripts/data/select_features_train_only.py and a reviewed candidate list.")
    names = selected.get("selected_features")
    if not isinstance(names, list) or len(names) != n_features or len(set(names)) != len(names):
        raise ValueError("Feature selection must contain exactly 14 unique features")
    if any(not isinstance(name, str) or not name or REJECT.search(name) for name in names):
        raise ValueError("Selected feature list contains protected target/identifier metadata")
    if dataset not in selected.get("datasets", []):
        raise ValueError("Requested dataset was not in TRAIN-only feature selection")
    candidate_hash = selected.get("candidate_features_sha256")
    if not isinstance(candidate_hash, str) or len(candidate_hash) != 64:
        raise ValueError("Missing original reviewed-candidate SHA-256")
    root = Path(split_root) / dataset
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SPLIT_SCHEMA or manifest.get("dataset") != dataset:
        raise ValueError("Invalid original split manifest")
    expected_m = selected.get("split_manifest_sha256_by_dataset", {}).get(dataset)
    if sha256(manifest_path) != expected_m:
        raise ValueError("TRAIN-only selection has wrong/changed split manifest hash")
    expected_files = selected.get("train_sha256_by_dataset_link", {}).get(dataset)
    if not isinstance(expected_files, dict) or set(expected_files) != set(manifest["links"]):
        raise ValueError("TRAIN-only selection missing source-link hashes")
    for link, info in manifest["links"].items():
        if expected_files[link] != info["partitions"]["train"]["sha256"]:
            raise ValueError(f"TRAIN-only selection has wrong source partition: {link}")
    return names
