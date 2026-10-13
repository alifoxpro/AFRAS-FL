#!/usr/bin/env python3
"""Strict federated contextual-bandit Q-learning, using TRAIN-only AFRAS-FL rules.

This is a new, leakage-guarded experimental protocol; not a reproduction of
historical paper results and not a sequential long-horizon SDN environment.
No TEST file is loaded or evaluated during this Stage 4 training program.

Usage:
  python scripts/training/train_federated_strict.py --dataset ciciot2023 \
    --mu-link 0 --rounds 10 --seed 42

Requires strict Stage 3 teacher checkpoints created with the same split,
selected feature list and dataset. Validation chooses model checkpoints.
"""
import argparse
import copy
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, TensorDataset

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "training"))

from scripts.data.strict_manifest import validate_stage3_inputs
from scripts.data.feature_provenance import validate_train_feature_selection
from scripts.data.label_evidence import audit_train_val
from scripts.training.strict_fed_core import decision_metrics, jain_fairness, mosar_reward
from scripts.training.train_mamba_strict import arrays_for_split, sha256_file
from train_isolated import MambaOnlyModel, seed_everything
from train_rl_multiagent_StrategyB import AFRASFLPipeline, FuzzyInferenceEngine, DQNNetwork

STATE_DIM = 28


def teacher_predictions(model, windows, device, batch_size):
    model.eval()
    blocks = []
    with torch.no_grad():
        for start in range(0, len(windows), batch_size):
            tensor = torch.from_numpy(windows[start:start+batch_size]).to(device)
            probs = torch.softmax(model(tensor), dim=1)
            blocks.append(probs.cpu().numpy().astype(np.float32))
    return np.concatenate(blocks, axis=0)


def build_states(windows, teacher_probs):
    """Common, interpretable 28D state; no PCA or VAL-fitted transforms.

    14 window feature means + 11 window feature standard deviations +
    3 teacher probabilities. Cross-client features share semantic positions.
    """
    if windows.ndim != 3 or windows.shape[2] != 14:
        raise ValueError("Strict federated state requires exactly 14 selected features")
    if teacher_probs.shape != (len(windows), 3):
        raise ValueError("Teacher prediction/window alignment mismatch")
    means = windows.mean(axis=1)
    stds = windows.std(axis=1)[:, :11]
    states = np.concatenate([means, stds, teacher_probs], axis=1).astype(np.float32)
    if states.shape[1] != STATE_DIM or not np.isfinite(states).all():
        raise ValueError("Malformed or nonfinite federated state")
    return states


def maybe_train_subset(state, targets, probs, maximum, seed):
    if not maximum or len(targets) <= maximum:
        return state, targets, probs
    indices = np.random.default_rng(seed).choice(len(targets), maximum, replace=False)
    indices.sort()
    return state[indices], targets[indices], probs[indices]


def load_client(dataset, link, paths, feature_names, args, out_root):
    """Validate strict teacher provenance and produce TRAIN/VAL state arrays."""
    stage3_dir = args.stage3_root / dataset / f"seed_{args.seed}" / link
    provenance = stage3_dir / "provenance.json"
    if not provenance.is_file():
        raise FileNotFoundError(f"Missing strict Stage 3 provenance: {provenance}")
    p = json.loads(provenance.read_text(encoding="utf-8"))
    if p.get("seed") != args.seed:
        raise ValueError("Strict Stage 3 teacher seed does not match Stage 4")
    if p.get("protocol") != "strict-stage3-train-val-only-v1":
        raise ValueError("Untrusted or old Stage 3 checkpoint")
    if p.get("dataset") != dataset or p.get("link") != link:
        raise ValueError("Wrong Stage 3 dataset/client")
    if p.get("features") != feature_names or p.get("window_size") != args.window_size:
        raise ValueError("Stage 3 features/window mismatch")
    if p.get("stride") != args.stride:
        raise ValueError("Stage 3 stride mismatch")
    if p.get("feature_list_sha256") != sha256_file(args.feature_json):
        raise ValueError("Stage 3 feature-list file changed")
    if p.get("train_sha256") != sha256_file(paths["train"]):
        raise ValueError("Stage 3 TRAIN source mismatch")
    if p.get("val_sha256") != sha256_file(paths["val"]):
        raise ValueError("Stage 3 VAL source mismatch")
    checkpoint = stage3_dir / "mamba_val_best.pt"
    scaler_path = stage3_dir / "train_fitted_scaler.npz"
    if not checkpoint.is_file() or not scaler_path.is_file():
        raise FileNotFoundError("Missing strict Stage 3 teacher/scaler")
    train_pair, val_pair, scaler = arrays_for_split(
        paths["train"], paths["val"], feature_names, args.window_size, args.stride)
    if p.get("teacher_checkpoint_sha256") != sha256_file(checkpoint):
        raise ValueError("Stage 3 teacher artifact checksum mismatch")
    if p.get("train_fitted_scaler_sha256") != sha256_file(scaler_path):
        raise ValueError("Stage 3 scaler artifact checksum mismatch")
    with np.load(scaler_path, allow_pickle=False) as saved:
        if not np.allclose(saved["mean"], scaler.mean_) or not np.allclose(saved["scale"], scaler.scale_):
            raise ValueError("Stage 3 scaler does not match TRAIN-only recomputation")
    device = torch.device(args.device)
    teacher = MambaOnlyModel(n_features=len(feature_names), n_classes=3).to(device)
    teacher.load_state_dict(torch.load(checkpoint, map_location=device, weights_only=True))
    p_tr = teacher_predictions(teacher, train_pair[0], device, args.batch_size)
    p_val = teacher_predictions(teacher, val_pair[0], device, args.batch_size)
    tr_state = build_states(train_pair[0], p_tr)
    val_state = build_states(val_pair[0], p_val)
    tr_state, tr_labels, tr_probs = maybe_train_subset(
        tr_state, train_pair[1], p_tr, args.max_train_windows,
        args.seed + int(hashlib.sha256(link.encode()).hexdigest()[:6], 16))
    val_labels = val_pair[1]
    if min(len(tr_labels), len(val_labels)) < 30:
        raise ValueError("Too few independent TRAIN/VAL windows")
    return {
        "link": link,
        "train_state": tr_state,
        "train_label": tr_labels,
        "train_prob": tr_probs,
        "val_state": val_state,
        "val_label": val_labels,
        "n_train": len(tr_labels),
        "stage3_provenance_sha256": sha256_file(provenance),
        "stage3_checkpoint_sha256": sha256_file(checkpoint),
        "stage3_scaler_sha256": sha256_file(scaler_path),
    }


def train_rules(client, out, max_rules_samples, seed):
    """Mine the original 7-phase fuzzy pipeline from TRAIN samples only."""
    x = client["train_state"]
    y = client["train_label"]
    if max_rules_samples and len(y) > max_rules_samples:
        idx = np.random.default_rng(seed).choice(len(y), max_rules_samples, replace=False)
        idx.sort()
        x, y = x[idx], y[idx]
    if len(y) < 50:
        raise ValueError("AFRAS-FL rule mining requires at least 50 TRAIN windows")
    feature_names = ["train_feature_0_mean", "train_feature_1_mean"]
    pipeline = AFRASFLPipeline(
        x[:, :2].astype(np.float32), y.astype(np.int64),
        feature_names, client["link"], out)
    package = pipeline.run_all()
    return FuzzyInferenceEngine(package["rules"],
                                package["membership_params"],
                                package["feature_names"]), package


def rule_arrays(engine, states):
    action = np.full(len(states), -1, dtype=np.int64)
    confidence = np.zeros(len(states), dtype=np.float32)
    for i, state in enumerate(states):
        proposed, strength = engine.infer(state[:2])
        if proposed is not None:
            action[i] = int(proposed)
            confidence[i] = float(np.clip(strength, 0, 1))
    return action, confidence


def reward_table(client, lambda_fuzzy):
    n = client["n_train"]
    table = np.empty((n, 3), dtype=np.float32)
    for i in range(n):
        fuzzy_action = int(client["rule_action"][i])
        if fuzzy_action == -1:
            fuzzy_action = None
        for action in range(3):
            table[i, action] = mosar_reward(
                severity=int(client["train_label"][i]), action=action,
                teacher_probs=client["train_prob"][i],
                fuzzy_action=fuzzy_action,
                fuzzy_confidence=float(client["rule_confidence"][i]),
                lambda_fuzzy=lambda_fuzzy, mu_link=0)
    return table


def local_fit(global_model, client, reward_targets, args, seed, mu_prox):
    device = torch.device(args.device)
    local = copy.deepcopy(global_model).to(device)
    local.train()
    frozen_global = [p.detach().clone() for p in global_model.parameters()]
    ds = TensorDataset(torch.from_numpy(client["train_state"]),
                       torch.from_numpy(reward_targets))
    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=True,
                        num_workers=0, generator=generator)
    optimizer = torch.optim.Adam(local.parameters(), lr=args.learning_rate)
    for _ in range(args.local_epochs):
        for x, rewards in loader:
            x = x.to(device)
            rewards = rewards.to(device)
            q = local(x)
            exploratory = torch.rand(len(x), device=device) < args.epsilon
            random_action = torch.randint(0, 3, (len(x),), device=device)
            greedy = q.detach().argmax(dim=1)
            chosen = torch.where(exploratory, random_action, greedy)
            prediction = q.gather(1, chosen[:, None]).squeeze(1)
            reward = rewards.gather(1, chosen[:, None]).squeeze(1)
            loss = F.mse_loss(prediction, reward)
            if mu_prox:
                prox = sum(((p - baseline.to(device)) ** 2).sum()
                           for p, baseline in zip(local.parameters(), frozen_global))
                loss = loss + (mu_prox / 2.0) * prox
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(local.parameters(), 1.0)
            optimizer.step()
    return {k: v.detach().cpu().clone() for k, v in local.state_dict().items()}


def aggregate_state_dict(states, sizes):
    """Example-weighted FedAvg; shared 28D semantics across all clients."""
    weights = np.asarray(sizes, dtype=float)
    weights /= weights.sum()
    averaged = {}
    for name in states[0]:
        averaged[name] = sum(float(weight) * sd[name] for weight, sd in zip(weights, states))
    return averaged


def evaluate_validation(model, clients, device, batch_size):
    model.eval()
    reports = {}
    with torch.no_grad():
        for cl in clients:
            actions = []
            states = cl["val_state"]
            for start in range(0, len(states), batch_size):
                logits = model(torch.from_numpy(states[start:start+batch_size]).to(device))
                actions.extend(logits.argmax(dim=1).cpu().tolist())
            reports[cl["link"]] = decision_metrics(cl["val_label"], actions)
    success = [r["action_success_rate"] for r in reports.values()]
    return {
        "mean_per_link_action_success": float(np.mean(success)),
        "jain_fairness_action_success": jain_fairness(success),
        "per_client": reports,
    }


def train_one_phase(name, clients, args, root, fuzzy):
    """B2/B3/B4 independently initialized and selected only by VAL."""
    seed_everything(args.seed)
    random.seed(args.seed)
    device = torch.device(args.device)
    global_model = DQNNetwork(state_dim=28, n_actions=3).to(device)
    history = []
    best_score = -1.0
    best_round = None
    ckpt = root / f"{name}.pt"
    for rd in range(args.rounds):
        snapshots = []
        for ci, client in enumerate(clients):
            table = reward_table(client, args.lambda_fuzzy if fuzzy else 0.0)
            local_snapshot = local_fit(
                global_model, client, table, args,
                seed=args.seed + rd * 1000 + ci,
                mu_prox=(args.fedprox_mu if name != "B2_FedAvg" else 0.0))
            snapshots.append(local_snapshot)
        global_model.load_state_dict(
            aggregate_state_dict(snapshots, [c["n_train"] for c in clients]))
        results = evaluate_validation(global_model, clients, device, args.batch_size)
        score = results["mean_per_link_action_success"]
        history.append({"round": rd + 1, "validation": results})
        if score > best_score:
            best_score, best_round = score, rd + 1
            torch.save(global_model.state_dict(), ckpt)
        print(f"{name}: round={rd + 1}/{args.rounds}, "
              f"validation_action_success={score:.5f}", flush=True)
    (root / f"{name}_validation_history.json").write_text(
        json.dumps(history, indent=2), encoding="utf-8")
    return {
        "phase": name, "best_round_val_only": best_round,
        "best_val_mean_action_success": best_score,
        "checkpoint": ckpt.name, "validation_only": True,
        "checkpoint_sha256": sha256_file(ckpt),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["ciciot2023", "diad2024"], required=True)
    parser.add_argument("--split-root", type=Path,
                        default=REPO / "data" / "full_candidate_strict_split")
    parser.add_argument("--stage3-root", type=Path,
                        default=REPO / "experiments" / "strict_stage3")
    parser.add_argument("--feature-json", type=Path,
                        default=REPO / "data" / "selected_14_train_only.json")
    parser.add_argument("--output-root", type=Path,
                        default=REPO / "experiments" / "strict_stage4")
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--local-epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--epsilon", type=float, default=0.1)
    parser.add_argument("--fedprox-mu", type=float, default=0.01)
    parser.add_argument("--lambda-fuzzy", type=float, default=0.25)
    parser.add_argument("--mu-link", type=float, default=0.0)
    parser.add_argument("--window-size", type=int, default=20)
    parser.add_argument("--stride", type=int, default=20)
    parser.add_argument("--max-train-windows", type=int, default=0)
    parser.add_argument("--max-rule-windows", type=int, default=3000)
    parser.add_argument("--label-evidence", type=Path, default=None,
                        help="Predeclared raw label/attack mapping. Audit TRAIN/VAL only; seal SHA-256.")
    parser.add_argument("--pilot", action="store_true",
                        help="Required if max-train-windows is used; outputs must be labeled PILOT")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    if abs(args.mu_link) > 1e-12:
        parser.error("R_link has no validated neighbor actions: --mu-link MUST be 0")
    if any(v <= 0 for v in (args.rounds, args.local_epochs, args.batch_size,
                           args.window_size, args.stride, args.max_rule_windows)):
        parser.error("Rounds, epochs, batch/window size, stride, rule sample size must be positive")
    if not (0 < args.learning_rate <= 1 and 0 <= args.epsilon <= 1 and
            0 <= args.lambda_fuzzy <= 1 and 0 <= args.fedprox_mu <= 1):
        parser.error("Invalid optimization/reward hyperparameters")
    if args.stride > args.window_size:
        parser.error("stride may not exceed window size in strict Stage 4")
    if args.max_train_windows < 0 or (args.max_train_windows and not args.pilot):
        parser.error("Subsampling TRAIN requires --pilot; results are not full-run statistics")
    features = validate_train_feature_selection(args.feature_json, args.split_root, args.dataset)
    if len(features) != 14:
        parser.error("28D strict state requires exactly 14 reviewed TRAIN-selected features")
    inputs = validate_stage3_inputs(args.split_root / args.dataset, args.dataset,
                                    window_size=args.window_size)
    if len(inputs) != 5:
        raise ValueError(f"Federated 5-client setup requires five links; found {len(inputs)}")
    label_audit = (audit_train_val(args.split_root / args.dataset, args.dataset,
                                   args.label_evidence)
                   if args.label_evidence is not None else None)
    output = args.output_root / args.dataset / f"seed_{args.seed}"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing strict Stage 4 run: {output}")
    seed_everything(args.seed)
    random.seed(args.seed)
    clients = [load_client(args.dataset, name, paths, features, args, output)
               for name, paths in inputs.items()]
    output.mkdir(parents=True, exist_ok=False)
    rule_summary = {}
    for ci, client in enumerate(clients):
        engine, pkg = train_rules(client, output / "TRAIN_RULES" / client["link"],
                                  args.max_rule_windows, args.seed + ci)
        client["rule_action"], client["rule_confidence"] = rule_arrays(
            engine, client["train_state"])
        rule_summary[client["link"]] = {
            "rules": int(pkg["n_rules"]),
            "train_only": True, "feature_columns": [0, 1],
        }
    phases = [
        train_one_phase("B2_FedAvg", clients, args, output, fuzzy=False),
        train_one_phase("B3_FedProx", clients, args, output, fuzzy=False),
        train_one_phase("B4_TrainOnlyFuzzy_FedProx", clients, args, output, fuzzy=True),
    ]
    settings = {k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items()}
    metadata = {
        "schema": "strict-fed-contextual-bandit-v1",
        "dataset": args.dataset,
        "split_manifest_sha256": sha256_file(
            args.split_root / args.dataset / "manifest.json"),
        "scientific_status": "TRAIN/VAL only; no independent TEST, no deployment claim",
        "source_experiment": "new protocol, NOT historical manuscript output",
        "data_source": "split-before-window TRAIN/VAL",
        "test_access": "NONE",
        "raw_label_evidence_sha256": label_audit["evidence_sha256"] if label_audit else None,
        "raw_label_provenance": label_audit["source_provenance"] if label_audit else None,
        "raw_label_train_val_audit": label_audit["train_val_categories"] if label_audit else None,
        "mu_link_effective": 0,
        "discount_gamma": 0,
        "action_space": ["ALLOW", "RATE_LIMIT", "BLOCK"],
        "client_checkpoint_sha256": {
            c["link"]: c["stage3_checkpoint_sha256"] for c in clients},
        "client_stage3_provenance_sha256": {
            c["link"]: c["stage3_provenance_sha256"] for c in clients},
        "client_stage3_scaler_sha256": {
            c["link"]: c["stage3_scaler_sha256"] for c in clients},
        "client_train_counts": {c["link"]: c["n_train"] for c in clients},
        "fuzzy_train_only": rule_summary,
        "phases": phases,
        "settings": settings,
        "limitations": [
            "Action-exogenous contextual bandit: not a dynamic SDN MDP",
            "Source feature selection and dataset label taxonomy not audited",
            "No validated neighbor coordination; mu_link forced to zero",
            "Decision success and false-block-on-Low are not clinical binary IDS FPR/FNR",
            "No independent TEST scores are emitted in Stage 4",
        ],
    }
    (output / "RUN_PROVENANCE.json").write_text(json.dumps(metadata, indent=2),
                                                 encoding="utf-8")
    print(f"TRAIN/VAL federated simulation completed: {output}; no TEST evaluated")


if __name__ == "__main__":
    main()
