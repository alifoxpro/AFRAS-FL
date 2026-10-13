#!/usr/bin/env python3
"""Check declared severity/binary mappings against ACTUAL inventoried raw labels.

Completeness and file-hash consistency are checked. Does not independently
prove a researcher's severity policy or the upstream dataset's authenticity.
"""
import argparse
import json
from pathlib import Path

from scripts.data.audit_original_csvs import SCHEMA as INVENTORY_SCHEMA, sha256
from scripts.data.label_evidence import validate_evidence_file


def review_category_mapping(inventory_path, mapping_path, dataset):
    inventory_path, mapping_path = Path(inventory_path), Path(mapping_path)
    inv = json.loads(inventory_path.read_text(encoding="utf-8"))
    mapping = validate_evidence_file(mapping_path, dataset)
    if inv.get("schema") != INVENTORY_SCHEMA or inv.get("dataset") != dataset:
        raise ValueError("Incorrect original-source inventory")
    if mapping.get("raw_label_column") != inv.get("original_label_column_user_declared"):
        raise ValueError("Raw-category column does not match observed original inventory")
    if mapping.get("source_url") != inv.get("official_description_url"):
        raise ValueError("Source URL differs from official benchmark documentation")
    original_artifact_sha = inv.get("source_artifact_sha256")
    if original_artifact_sha and mapping["source_sha256"] != original_artifact_sha:
        raise ValueError("Raw source archive/record hash differs from mapping")
    observed = inv.get("all_original_label_counts", {})
    declared = mapping["raw_label_map"]
    if not observed or not isinstance(observed, dict):
        raise ValueError("Inventory has no original labels")
    missing = sorted(set(observed) - set(declared))
    extra = sorted(set(declared) - set(observed))
    if missing or extra:
        raise ValueError(f"Incomplete/excess label mapping; missing={missing}, extra={extra}")
    counts = {"0_benign": 0, "1_attack": 0}
    severity = {"High": 0, "Medium": 0, "Low": 0}
    for label, n in observed.items():
        val = declared[label]
        counts[f'{val["is_attack"]}_' + ("attack" if val["is_attack"] else "benign")] += n
        severity[val["severity"]] += n
    if counts["0_benign"] == 0 or counts["1_attack"] == 0:
        raise ValueError("Expected both attack and benign raw classes for binary IDS audit")
    if any(n == 0 for n in severity.values()):
        raise ValueError("All three severity classes needed for the three-class system")
    return {
        "schema": "afras-category-mapping-coverage-review-v1",
        "dataset": dataset,
        "source_inventory_sha256": sha256(inventory_path),
        "mapping_evidence_sha256": sha256(mapping_path),
        "source_artifact_digest_claimed": mapping["source_sha256"],
        "original_artifact_sha256_measured": original_artifact_sha,
        "reference_sha256_confirmed": inv.get("reference_sha256_confirmed", False),
        "observed_category_count": len(observed),
        "complete_category_coverage": True,
        "binary_class_counts": counts,
        "severity_class_counts": severity,
        "original_csvs_scanned": inv.get("source_files_count"),
        "remaining_manual_gate": [
            "Independently confirm official raw source bytes / archive SHA-256",
            "Audit and justify each attack-type -> High/Medium/Low severity choice",
            "Inspect original -> harmonized row ID join and derived binary labels",
            "Audit device/group-disjoint splits and pre-split feature engineering",
            "This check is NOT approval of manuscript FPR/FNR values",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--mapping", type=Path, required=True)
    p.add_argument("--dataset", choices=("ciciot2023", "diad2024"), required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError("Will not overwrite previous mapping review")
    result = review_category_mapping(args.inventory, args.mapping, args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Reviewed coverage for {result['observed_category_count']} raw labels; "
          "source authenticity/severity policy still require independent review.")


if __name__ == "__main__":
    main()
