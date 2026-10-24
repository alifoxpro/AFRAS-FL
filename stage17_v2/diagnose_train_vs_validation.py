#!/usr/bin/env python3
"""AFRAS-FL V2 Chat 6: source-only TRAIN-vs-SOURCE-VALIDATION collapse diagnosis.

All observations are real source-device N-BaIoT samples. The designated outer
LODO target device is never opened, inspected, transformed or scored. This is
an EXPLORATORY debugging diagnostic, not an 8-client confirmatory LODO result.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn
import source_only_pilot as p


@torch.no_grad()
def class_score_summary(state, data, device):
    m = p.BinaryMLP().to(device)
    m.load_state_dict(state)
    m.eval()
    X, y = data
    scores = []
    for start in range(0, len(X), 2048):
        xb = torch.from_numpy(X[start:start + 2048]).to(device)
        scores.extend(torch.sigmoid(m(xb)).cpu().numpy().tolist())
    scores = np.asarray(scores, dtype=np.float64)
    y = np.asarray(y)
    if not np.isfinite(scores).all():
        raise ValueError("Nonfinite predicted scores")
    by_class = {}
    for idx, name in ((0, "benign"), (1, "attack")):
        mask = y == idx
        if not mask.any():
            raise ValueError("Source diagnostics require both classes")
        z = scores[mask]
        by_class[name] = {
            "n": int(mask.sum()),
            "probability_mean": float(z.mean()),
            "probability_median": float(np.median(z)),
            "probability_q10": float(np.quantile(z, 0.1)),
            "probability_q90": float(np.quantile(z, 0.9)),
            "attack_prediction_fraction_at_0_5": float(np.mean(z >= 0.5)),
        }
    return by_class


def metrics(state, data, device):
    native = p.evaluate_source_validation(state, data, device)
    return {
        "tp": native["tp"], "tn": native["tn"], "fp": native["fp"],
        "fn": native["fn"],
        "balanced_accuracy": native["validation_only_balanced_accuracy"],
        "attack_recall": native["validation_only_attack_recall"],
        "benign_fpr": native["validation_only_fpr"],
        "scores_by_true_label": class_score_summary(state, data, device),
    }


def pooled_training_metrics(state, clients, device):
    """In-sample training diagnostics only; not source-held-out performance."""
    rows = {name: metrics(state, data, device) for name, data in clients.items()}
    totals = {k: sum(z[k] for z in rows.values())
              for k in ("tp", "tn", "fp", "fn")}
    tp, tn, fp, fn = (totals[k] for k in ("tp", "tn", "fp", "fn"))
    if tp + fn < 1 or tn + fp < 1:
        raise ValueError("Pooled source training support missing")
    totals.update({
        "balanced_accuracy": float(0.5 * (
            tp / (tp + fn) + tn / (tn + fp))),
        "attack_recall": float(tp / (tp + fn)),
        "benign_fpr": float(fp / (tn + fp)),
        "devices": rows,
    })
    return totals


def distance(global_state, other_state):
    return float(np.sqrt(sum(
        torch.sum((global_state[key] - other_state[key]).to(torch.float64) ** 2).item()
        for key in global_state
    )))


def diagnose(clients, validation, args):
    """Exactly reproduces the prior 3-round sampling-based training schedule.

    Measurements on training samples are used only to identify underfitting,
    local-vs-aggregation collapse, and source-to-source transfer loss.
    """
    device = torch.device(args.backend)
    out = {}
    for mode in ("none", "inverse-prevalence"):
        for method in ("fedavg", "fedprox"):
            torch.manual_seed(args.seed)
            global_state = {k: v.detach().cpu().clone()
                            for k, v in p.BinaryMLP().state_dict().items()}
            series = [{
                "round": 0,
                "source_train_global": pooled_training_metrics(
                    global_state, clients, device),
                "separate_source_validation": metrics(
                    global_state, validation, device),
                "mean_local_update_l2": None,
                "local_training_self_metrics": None,
            }]
            for round_no in range(1, args.rounds + 1):
                states = []
                sizes = []
                local_metrics = {}
                delta_norms = {}
                for index, (source, train_data) in enumerate(clients.items()):
                    local_state = p.train_client(
                        global_state, train_data, method, args.fedprox_mu,
                        args.local_epochs, args.batch_size, args.lr,
                        args.seed + round_no * 1009 + index, device,
                        mode
                    )
                    states.append(local_state)
                    sizes.append(len(train_data[1]))
                    local_metrics[source] = metrics(local_state, train_data, device)
                    delta_norms[source] = distance(global_state, local_state)
                global_state = p.weighted_fedavg(states, sizes)
                source_global = pooled_training_metrics(global_state, clients, device)
                val = metrics(global_state, validation, device)
                event = {
                    "round": round_no,
                    "source_train_global": source_global,
                    "separate_source_validation": val,
                    "mean_local_update_l2": float(np.mean(list(delta_norms.values()))),
                    "local_client_update_l2": delta_norms,
                    "local_training_self_metrics": local_metrics,
                }
                series.append(event)
                print("SOURCE_TRAIN_VS_VALIDATION", json.dumps({
                    "method": method, "loss_mode": mode,
                    "round": round_no,
                    "train_balanced_accuracy": source_global["balanced_accuracy"],
                    "train_benign_fpr": source_global["benign_fpr"],
                    "source_validation_balanced_accuracy": val["balanced_accuracy"],
                    "source_validation_benign_fpr": val["benign_fpr"],
                    "mean_local_update_l2": event["mean_local_update_l2"],
                }, separators=(",", ":")), flush=True)
            out[method + "__" + mode] = series
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--heldout", choices=p.DEVICES,
                        default="Ennio_Doorbell")
    parser.add_argument("--validation", choices=p.DEVICES,
                        default="Samsung_SNH_1011_N_Webcam")
    parser.add_argument("--seed", type=int, default=3107)
    parser.add_argument("--max-per-class", type=int, default=128)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--local-epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--fedprox-mu", type=float, default=0.01)
    parser.add_argument("--backend", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Output exists; refusing accidental override")
    if not args.source_root.is_dir():
        parser.error("Source directory missing")
    if (args.max_per_class < 1 or args.rounds < 1
            or args.local_epochs < 1 or args.batch_size < 1
            or args.lr <= 0 or args.fedprox_mu < 0):
        parser.error("Invalid pilot hyperparameters")
    training, source_val = p.split_source_devices(args.heldout, args.validation)
    if args.heldout in training or source_val == args.heldout:
        raise ValueError("Target isolation broken")
    torch.set_num_threads(2)
    clients = {}
    expected_header = None
    support = {}
    validation = None
    for device in [*training, source_val]:
        X, y, info, expected_header = p.load_one_device(
            args.source_root, device, args.max_per_class,
            args.seed, expected_header)
        support[device] = info
        if device == source_val:
            validation = X, y
        else:
            clients[device] = X, y
    clients, validation, _normalization = p.preprocess_train_only(clients, validation)
    if len(clients) != 7 or len(validation[1]) < 2:
        raise ValueError("Source device accounting failure")
    arms = diagnose(clients, validation, args)
    record = {
        "status": "REAL_SOURCE_ONLY_TRAIN_VS_SOURCE_VALIDATION_DIAGNOSTIC",
        "confirmatory": False,
        "outer_target_archive_opened": False,
        "outer_target_evaluated": False,
        "heldout_target_name_only": args.heldout,
        "train_device_names": training,
        "source_validation_device_name": source_val,
        "source_class_counts": support,
        "source_only_sampling_changes_native_prevalence": True,
        "no_hyperparameter_selection_using_target": True,
        "all_models_trained_on_source_train_clients_only": True,
        "arms": arms,
        "protocol": {
            "seed": args.seed, "max_per_class": args.max_per_class,
            "rounds": args.rounds, "local_epochs": args.local_epochs,
            "batch_size": args.batch_size, "lr": args.lr,
            "fedprox_mu": args.fedprox_mu, "backend": args.backend,
        },
        "source_code_sha256": hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest(),
        "limitations": [
            "Training-side in-sample results detect optimization behavior only.",
            "Separately withheld validation source is distinct from training devices.",
            "Results are not final LODO target performance, statistical evidence or method superiority.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf8") as f:
        json.dump(record, f, indent=2, allow_nan=False)
    print("REAL_SOURCE_TRAIN_DIAGNOSTIC_COMPLETE", args.output, flush=True)


if __name__ == "__main__":
    main()
