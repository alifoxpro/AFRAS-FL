#!/usr/bin/env python3
"""Evaluate all predeclared Stage 4 policies on TEST exactly once.

No fitting, retraining, threshold selection or policy selection in this script.
No conventional binary IDS FPR/FNR is claimed without an audited label mapping.
"""
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "training"))

from scripts.data.strict_test_guard import PHASES, sha256_file, validate_frozen_run
from scripts.data.label_evidence import validate_raw_rows
from scripts.training.strict_fed_core import (decision_metrics, jain_fairness, binary_intrusion_metrics, pooled_binary_counts)
from scripts.training.train_mamba_strict import load_features
from scripts.training.train_federated_strict import build_states, teacher_predictions
from train_isolated import MambaOnlyModel, create_windows
from train_rl_multiagent_StrategyB import DQNNetwork


def load_test_states(paths, features, window_size, stride, device, batch_size,
                     label_evidence=None):
    """Apply frozen TRAIN scaler, frozen Mamba teacher; no TEST fitting."""
    values, labels = load_features(paths["test_csv"], features)
    with np.load(paths["train_fitted_scaler"], allow_pickle=False) as archive:
        mean, scale = archive["mean"], archive["scale"]
        if mean.shape != (14,) or scale.shape != (14,) or not (
                np.isfinite(mean).all() and np.isfinite(scale).all() and
                np.all(scale > 0)):
            raise ValueError("Invalid TRAIN-only scaler parameters")
    scaled = ((values - mean) / scale).astype(np.float32)
    if not np.isfinite(scaled).all():
        raise ValueError("TEST normalization resulted in invalid features")
    windows, truth = create_windows(scaled, labels, window_size, stride)
    if len(truth) == 0:
        raise ValueError("Empty TEST window partition")
    binary = None
    if label_evidence is not None:
        validated = validate_raw_rows(
            paths["test_csv"], label_evidence,
            expected_sha256=paths["test_sha256"],
            take_binary_last=(window_size, stride))
        binary = validated["binary_window_labels"]
        if len(binary) != len(truth):
            raise ValueError("Window-aligned binary attack labels do not match TEST windows")
    teacher = MambaOnlyModel(n_features=14, n_classes=3).to(device)
    teacher.load_state_dict(torch.load(paths["teacher_checkpoint"],
                                       weights_only=True, map_location=device))
    probs = teacher_predictions(teacher, windows, device, batch_size)
    return build_states(windows, probs), truth, binary


def predict_actions(model, states, device, batch_size):
    actions = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(states), batch_size):
            x = torch.from_numpy(states[start:start + batch_size]).to(device)
            actions.extend(model(x).argmax(dim=1).cpu().tolist())
    return [int(a) for a in actions]


def evaluate_phase(phase, checkpoint, test_clients, device, batch_size):
    model = DQNNetwork(state_dim=28, n_actions=3).to(device)
    model.load_state_dict(torch.load(checkpoint, weights_only=True, map_location=device))
    per_client, matrix, scores = {}, np.zeros((3, 3), dtype=np.int64), []
    binary_reports = []
    for link, (states, truth, binary) in sorted(test_clients.items()):
        pred = predict_actions(model, states, device, batch_size)
        report = decision_metrics(truth.tolist(), pred)
        if binary is not None:
            binary_report = binary_intrusion_metrics(binary, pred)
            report["binary_ids"] = binary_report
        else:
            binary_report = None
        binary_reports.append(binary_report)
        per_client[link] = report
        scores.append(report["action_success_rate"])
        matrix += np.asarray(report["severity_action_counts"], dtype=np.int64)
    total = int(matrix.sum())
    correct = int(matrix[0, 2] + matrix[1, 1] + matrix[2, 0])
    binary_pooled = pooled_binary_counts(
        binary_reports, expected_clients=len(test_clients))
    if binary_pooled is not None and binary_pooled["n"] != total:
        raise ValueError("Pooled binary labels do not cover every evaluated window")
    return {
        "phase": phase,
        "checkpoint_sha256": sha256_file(checkpoint),
        "per_client": per_client,
        "pooled_action_success": correct / total,
        "mean_client_action_success": float(np.mean(scores)),
        "jain_fairness_client_action_success": float(jain_fairness(scores)),
        "total_test_windows": total,
        "pooled_severity_action_matrix": matrix.tolist(),
        "pooled_binary_ids": binary_pooled,
        "labels": {"rows": ["High", "Medium", "Low"],
                   "columns": ["ALLOW", "RATE_LIMIT", "BLOCK"]},
    }


def emit_csv(path, data):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["phase", "client", "n", "action_success_rate",
                         "false_block_on_low", "false_allow_on_high",
                         "binary_FPR", "binary_FNR", "TP", "FP", "TN", "FN"])
        for phase in PHASES:
            for link, item in sorted(data[phase]["per_client"].items()):
                binary = item.get("binary_ids") or {}
                writer.writerow([
                    phase, link, item["n"], item["action_success_rate"],
                    item["false_block_on_low"], item["false_allow_on_high"],
                    binary.get("FPR"), binary.get("FNR"), binary.get("TP"),
                    binary.get("FP"), binary.get("TN"), binary.get("FN")])


def emit_markdown(path, frozen, results):
    lines = [
        "# Frozen TEST report — NEW, distinct experimental protocol",
        "",
        "Dataset: " + frozen["dataset"],
        "Stage 4 provenance SHA-256: " + frozen["stage4_provenance_sha256"],
        "",
        "**Not the original manuscript results.** TEST cannot be reused to",
        "tune or select a model after observing these values.",
        "",
        "| Predeclared phase | Pooled action success | Mean client success | JFI | N windows |",
        "|---|---:|---:|---:|---:|",
    ]
    for phase in PHASES:
        r = results[phase]
        lines.append("| {} | {:.6f} | {:.6f} | {:.6f} | {} |".format(
            phase, r["pooled_action_success"], r["mean_client_action_success"],
            r["jain_fairness_client_action_success"], r["total_test_windows"]))
    if any(results[p]["pooled_binary_ids"] is not None for p in PHASES):
        lines += ["", "## Binary IDS metrics — DECLARED original raw-label mapping",
                  "Decision: ALLOW predicts benign; RATE_LIMIT and BLOCK predict attack.",
                  "Authenticity of the raw-source labels still requires external review.",
                  "", "| Phase | FPR | FNR | TP | FP | TN | FN |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for phase in PHASES:
            m = results[phase]["pooled_binary_ids"]
            if m is not None:
                fmt = lambda v: ("undefined" if v is None else f"{v:.6f}")
                lines.append(f"| {phase} | {fmt(m['FPR'])} | {fmt(m['FNR'])} | "
                             f"{m['TP']} | {m['FP']} | {m['TN']} | {m['FN']} |")
    lines += [
        "", "Full 3x3 confusion matrices and per-client statistics are in TEST_RESULTS.json.",
        "Rows are High/Medium/Low. Columns are ALLOW/RATE_LIMIT/BLOCK.",
        "Category-level errors are distinct from binary IDS FPR/FNR.",
        "This does not certify source-device/group independence or upstream preprocessing.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", choices=("ciciot2023", "diad2024"), required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--split-root", type=Path,
                   default=REPO / "data" / "full_candidate_strict_split")
    p.add_argument("--stage3-root", type=Path,
                   default=REPO / "experiments" / "strict_stage3")
    p.add_argument("--stage4-root", type=Path,
                   default=REPO / "experiments" / "strict_stage4")
    p.add_argument("--feature-json", type=Path,
                   default=REPO / "data" / "selected_14_train_only.json")
    p.add_argument("--output-root", type=Path,
                   default=REPO / "experiments" / "strict_test_eval")
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--label-evidence", type=Path, default=None,
                   help="Exact SHA-pinned raw category/binary mapping registered in Stage 4")
    p.add_argument("--unseal-test", action="store_true",
                   help="Explicit acknowledgment that frozen TEST will be opened")
    args = p.parse_args()
    if not args.unseal_test:
        p.error("TEST is sealed: pass --unseal-test ONLY after final validation freeze")
    if args.batch_size < 1:
        p.error("--batch-size must be positive")

    output = args.output_root.resolve() / args.dataset / f"seed_{args.seed}"
    if output.exists():
        raise FileExistsError(f"TEST was already unsealed/attempted: {output}")
    frozen = validate_frozen_run(args.dataset, args.seed, args.split_root,
                                 args.stage3_root, args.stage4_root, args.feature_json,
                                 label_evidence_path=args.label_evidence)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)  # Claim this seed once, before inference.
    receipt = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "UNSEALED_ATTEMPT_STARTED",
        "stage4_provenance_sha256": frozen["stage4_provenance_sha256"],
        "split_manifest_sha256": frozen["split_manifest_sha256"],
        "raw_label_evidence_sha256": frozen["raw_label_evidence_sha256"],
        "test_files_sha256": {
            link: v["test_sha256"] for link, v in frozen["clients"].items()},
        "frozen_policy_sha256": {
            phase: sha256_file(f) for phase, f in frozen["phases"].items()},
    }
    (output / "TEST_UNSEAL_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")

    device = torch.device(args.device)
    test_clients = {
        link: load_test_states(paths, frozen["features"], frozen["window_size"],
                               frozen["stride"], device, args.batch_size,
                               frozen["raw_label_evidence"])
        for link, paths in sorted(frozen["clients"].items())
    }
    result = {
        phase: evaluate_phase(phase, frozen["phases"][phase],
                              test_clients, device, args.batch_size)
        for phase in PHASES
    }
    payload = {
        "schema": "strict-sealed-test-eval-v1",
        "scientific_status": "One-time TEST, NEW protocol, not original manuscript",
        "dataset": args.dataset, "seed": args.seed,
        "feature_list_sha256": frozen["feature_list_sha256"],
        "split_manifest_sha256": frozen["split_manifest_sha256"],
        "stage4_provenance_sha256": frozen["stage4_provenance_sha256"],
        "test_used_for_model_selection": False,
        "binary_label_status": ("DECLARED_RAW_LABELS_CROSSCHECKED" if frozen["raw_label_evidence"]
                                else "NO_RAW_ATTACK_LABELS_FPR_FNR_UNAVAILABLE"),
        "raw_label_evidence_sha256": frozen["raw_label_evidence_sha256"],
        "predeclared_phase_order": list(PHASES),
        "results": result,
        "remaining_limits": [
            "Even declared cross-checked binary labels need independent raw-source authenticity review",
            "No proof of source session/group-disjointness or preprocessing lineage",
            "No sequential MDP, operational latency, or nonzero neighbor reward",
            "Do not retune models and reuse the same TEST as untouched",
        ],
    }
    (output / "TEST_RESULTS.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    emit_csv(output / "TEST_PER_CLIENT.csv", result)
    emit_markdown(output / "TEST_REPORT.md", frozen, result)
    print(f"One-time frozen TEST evaluation saved at {output}")


if __name__ == "__main__":
    main()
