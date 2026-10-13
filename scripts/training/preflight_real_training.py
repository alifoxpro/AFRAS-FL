#!/usr/bin/env python3
"""Fail-closed preflight for strict TRAIN/VAL experiments — NEVER opens TEST.

Checks actual availability of five verified TRAIN/VAL CSVs, TRAIN-only feature
selection, matched per-seed checkpoints (Stage 4), Python dependencies,
and output collision. Does not train or infer any accuracy.
"""
import argparse
import importlib.util
import json
from pathlib import Path

from scripts.data.strict_manifest import validate_stage3_inputs
from scripts.data.feature_provenance import validate_train_feature_selection
from scripts.data.select_features_train_only import sha256


REQUIRED_MODULES = ("numpy", "pandas", "sklearn", "scipy", "torch", "matplotlib")


def assess(dataset, seed, stage, split_root, feature_json, stage3_root,
           stage4_root, check_dependencies=True):
    if stage not in ("stage3", "stage4"):
        raise ValueError("stage must be stage3 or stage4")
    if dataset not in ("ciciot2023", "diad2024"):
        raise ValueError("Unsupported dataset")
    if not isinstance(seed, int):
        raise ValueError("Seed must be integer")
    split_root = Path(split_root).resolve()
    feature_json = Path(feature_json).resolve()
    stage3_root = Path(stage3_root).resolve()
    stage4_root = Path(stage4_root).resolve()
    findings, warnings = [], []
    def blocker(message):
        findings.append(message)
    if check_dependencies:
        missing = [m for m in REQUIRED_MODULES if importlib.util.find_spec(m) is None]
        if missing:
            blocker("Missing required Python dependencies: " + ", ".join(missing))
    else:
        warnings.append("Dependency check skipped; NOT an execution-ready certification")

    files, features = None, None
    manifest_path = split_root / dataset / "manifest.json"
    if not manifest_path.is_file():
        blocker("Missing split manifest: " + str(manifest_path))
    if not feature_json.is_file():
        blocker("Missing TRAIN-only feature JSON: " + str(feature_json))
    if manifest_path.is_file() and feature_json.is_file():
        try:
            features = validate_train_feature_selection(
                feature_json, split_root, dataset)
        except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as e:
            blocker("TRAIN feature provenance rejected: " + str(e))
        try:
            files = validate_stage3_inputs(split_root / dataset, dataset, window_size=20)
        except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as e:
            blocker("TRAIN/VAL split validation rejected: " + str(e))
    if files is not None and len(files) != 5:
        blocker(f"Expected 5 federated clients, found {len(files)}")
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not manifest.get("group_disjoint_verified"):
                warnings.append("No verified group/session-disjointness in manifest")
            if not manifest.get("time_order_verified"):
                warnings.append("No declared source-time-order verification in manifest")
        except (ValueError, OSError, json.JSONDecodeError):
            blocker("Split manifest cannot be parsed")
    if stage == "stage3":
        out = stage3_root / dataset / f"seed_{seed}"
        if out.exists():
            blocker("Seed-scoped Stage 3 outputs already exist; refusal to overwrite: " + str(out))
    else:
        out = stage4_root / dataset / f"seed_{seed}"
        if out.exists():
            blocker("Seed-scoped Stage 4 outputs already exist; refusal to overwrite: " + str(out))
        if files is not None and features is not None:
            for link in sorted(files):
                directory = stage3_root / dataset / f"seed_{seed}" / link
                cp = directory / "mamba_val_best.pt"
                scaler = directory / "train_fitted_scaler.npz"
                prov = directory / "provenance.json"
                for required in (cp, scaler, prov):
                    if not required.is_file():
                        blocker("Missing Stage 3 artifact: " + str(required))
                if prov.is_file():
                    try:
                        record = json.loads(prov.read_text(encoding="utf-8"))
                        if (record.get("protocol") != "strict-stage3-train-val-only-v1"
                                or record.get("seed") != seed
                                or record.get("dataset") != dataset
                                or record.get("link") != link
                                or record.get("features") != features
                                or record.get("feature_list_sha256") != sha256(feature_json)
                                or record.get("train_sha256") != sha256(files[link]["train"])
                                or record.get("val_sha256") != sha256(files[link]["val"])
                                or (cp.is_file() and record.get("teacher_checkpoint_sha256") != sha256(cp))
                                or (scaler.is_file() and record.get("train_fitted_scaler_sha256") != sha256(scaler))):
                            blocker("Stage 3 provenance mismatch: " + str(prov))
                    except (ValueError, OSError, json.JSONDecodeError):
                        blocker("Invalid Stage 3 provenance JSON: " + str(prov))
    warnings.extend([
        "Source raw CSV authenticity/harmonization is NOT independently established",
        "One-time TEST remains sealed: this preflight did NOT read TEST CSVs",
        "No real-training or accuracy result is generated by this report",
    ])
    return {
        "schema": "afras-strict-training-preflight-v1",
        "dataset": dataset, "seed": seed, "stage": stage,
        "ready_for_execution": not findings and check_dependencies,
        "blockers": findings, "warnings": warnings,
        "verified_clients": sorted(files) if files else [],
        "features_count": len(features) if features else None,
        "test_csv_opened": False,
        "stage3_checkpoint_scope": f"{dataset}/seed_{seed}/<link>",
    }


def main():
    from pathlib import Path
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("ciciot2023", "diad2024"), required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stage", choices=("stage3", "stage4"), required=True)
    parser.add_argument("--split-root", type=Path,
                        default=repo / "data" / "unified_14features_5links_strict_split")
    parser.add_argument("--feature-json", type=Path,
                        default=repo / "data" / "selected_14_train_only.json")
    parser.add_argument("--stage3-root", type=Path,
                        default=repo / "experiments" / "strict_stage3")
    parser.add_argument("--stage4-root", type=Path,
                        default=repo / "experiments" / "strict_stage4")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = assess(args.dataset, args.seed, args.stage, args.split_root,
                    args.feature_json, args.stage3_root, args.stage4_root)
    report = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        if args.output.exists():
            parser.error("Refusing to overwrite an earlier preflight report")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
    print(report)
    if not result["ready_for_execution"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
