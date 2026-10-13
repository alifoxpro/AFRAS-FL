#!/usr/bin/env python3
"""Train fresh Mamba-only teacher networks on strict TRAIN, select using VAL.

No test file is read in this script. This is Stage 3 ONLY, not an end-to-end
leakage-free DQN/FL evaluation. Do not use old Mamba or DQN checkpoints.

Example:
 python scripts/training/train_mamba_strict.py --dataset ciciot2023 \
   --epochs 20 --seed 42

The source CSVs must first have been partitioned by
scripts/data/split_records_leakfree.py with --window-size 20.
"""
import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "training"))

from scripts.data.strict_manifest import validate_stage3_inputs
from train_isolated import MambaOnlyModel, create_windows, SEV_MAP, seed_everything

CLASS_COUNT = 3
SEVERITIES = tuple(SEV_MAP)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_features(path, features):
    needed = features + ["severity"]
    df = pd.read_csv(path, usecols=lambda col: col in needed, low_memory=True)
    missing = sorted(set(needed) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required fields in {path}: {missing}")
    series = df["severity"].astype(str).str.strip()
    unexpected = set(series.unique()) - set(SEVERITIES)
    if unexpected:
        raise ValueError(f"Unexpected severity labels in {path}: {sorted(unexpected)}")
    x = df[features].to_numpy(dtype=np.float32, copy=True)
    if not np.isfinite(x).all():
        raise ValueError(f"Nonfinite features in {path}; preprocessing must be train-fitted")
    y = series.map(SEV_MAP).to_numpy(dtype=np.int64, copy=True)
    return x, y


def arrays_for_split(train_path, val_path, features, window_size, stride):
    """Fit normalization to TRAIN records only; then build independent windows."""
    x_train, y_train = load_features(train_path, features)
    x_val, y_val = load_features(val_path, features)
    scaler = StandardScaler().fit(x_train)
    x_train = scaler.transform(x_train).astype(np.float32)
    x_val = scaler.transform(x_val).astype(np.float32)
    train_windows, train_targets = create_windows(x_train, y_train, window_size, stride)
    val_windows, val_targets = create_windows(x_val, y_val, window_size, stride)
    if min(len(train_targets), len(val_targets)) == 0:
        raise ValueError("No complete TRAIN or VAL windows")
    return (train_windows, train_targets), (val_windows, val_targets), scaler


def loaders(train_arrays, val_arrays, batch_size):
    tx, ty = train_arrays
    vx, vy = val_arrays
    tr = DataLoader(TensorDataset(torch.from_numpy(tx), torch.from_numpy(ty)),
                    batch_size=batch_size, shuffle=True, num_workers=0)
    va = DataLoader(TensorDataset(torch.from_numpy(vx), torch.from_numpy(vy)),
                    batch_size=batch_size, shuffle=False, num_workers=0)
    class_counts = Counter(map(int, ty))
    weights = torch.tensor([len(ty) / (CLASS_COUNT * max(class_counts.get(i, 1), 1))
                            for i in range(CLASS_COUNT)], dtype=torch.float32)
    return tr, va, weights, dict(class_counts)


def epoch_metrics(model, loader, criterion, device, optimizer=None):
    train = optimizer is not None
    model.train(train)
    total_loss, count = 0.0, 0
    preds, targets = [], []
    for x, y in loader:
        x = x.to(device)
        y = y.to(device)
        with torch.set_grad_enabled(train):
            logits = model(x)
            loss = criterion(logits, y)
            if train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
        total_loss += float(loss.item()) * len(y)
        count += len(y)
        preds.extend(logits.detach().argmax(dim=1).cpu().tolist())
        targets.extend(y.detach().cpu().tolist())
    if count == 0:
        raise ValueError("Empty loader")
    return {
        "loss": total_loss / count,
        "accuracy": sum(p == y for p, y in zip(preds, targets)) / count,
        "f1_macro": float(f1_score(targets, preds, labels=[0, 1, 2],
                                   average="macro", zero_division=0)),
    }


def train_link(dataset, link, paths, features, feature_sha, args, output_root):
    out = output_root / dataset / link
    if out.exists():
        raise FileExistsError(
            f"Refusing to reuse existing strict-stage3 checkpoint/results: {out}")
    (tr, va, scaler) = arrays_for_split(
        paths["train"], paths["val"], features, args.window_size, args.stride)
    train_dl, val_dl, class_weights, class_counts = loaders(tr, va, args.batch_size)
    device = torch.device(args.device)
    model = MambaOnlyModel(n_features=len(features), n_classes=CLASS_COUNT).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    out.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(out / "train_fitted_scaler.npz",
                        mean=scaler.mean_, scale=scaler.scale_)
    history = []
    best = float("inf")
    best_epoch = None
    ckpt = out / "mamba_val_best.pt"
    for epoch in range(args.epochs):
        train_metrics = epoch_metrics(model, train_dl, criterion, device,
                                      optimizer=optimizer)
        val_metrics = epoch_metrics(model, val_dl, criterion, device)
        history.append({"epoch": epoch + 1, "train": train_metrics,
                        "val": val_metrics})
        if val_metrics["loss"] < best:
            best = val_metrics["loss"]
            best_epoch = epoch + 1
            torch.save(model.state_dict(), ckpt)
        print(f"{dataset}/{link} epoch={epoch+1}/{args.epochs} "
              f"train_loss={train_metrics['loss']:.4f} "
              f"val_loss={val_metrics['loss']:.4f} "
              f"val_f1={val_metrics['f1_macro']:.4f}", flush=True)
    model.load_state_dict(torch.load(ckpt, map_location=device, weights_only=True))
    final_val = epoch_metrics(model, val_dl, criterion, device)
    metadata = {
        "protocol": "strict-stage3-train-val-only-v1",
        "dataset": dataset,
        "link": link,
        "seed": args.seed,
        "features": features,
        "feature_list_sha256": feature_sha,
        "train_sha256": sha256_file(paths["train"]),
        "val_sha256": sha256_file(paths["val"]),
        "window_size": args.window_size,
        "stride": args.stride,
        "train_windows": len(tr[1]),
        "val_windows": len(va[1]),
        "class_distribution_train_windows": class_counts,
        "epochs": args.epochs,
        "best_epoch_selected_on_val": best_epoch,
        "final_val_metrics": final_val,
        "test_access": "NONE — the test CSV was not accessed",
        "model": "MambaOnlyModel (train_isolated.py)",
        "notes": "Not an independent test score; requires strict RL and test protocol",
    }
    (out / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    (out / "provenance.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("ciciot2023", "diad2024", "all"), required=True)
    parser.add_argument("--split-root", type=Path,
                        default=REPO / "data" / "unified_14features_5links_strict_split")
    parser.add_argument("--feature-json", type=Path,
                        default=REPO / "data" / "unified_selected_14.json")
    parser.add_argument("--output-root", type=Path,
                        default=REPO / "experiments" / "strict_stage3")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--window-size", type=int, default=20)
    parser.add_argument("--stride", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    if min(args.epochs, args.batch_size, args.window_size, args.stride) < 1:
        parser.error("epochs, batch size, window size and stride must be positive")
    if not 0 < args.learning_rate <= 1:
        parser.error("learning rate must be positive and at most 1")
    feature_info = json.loads(args.feature_json.read_text(encoding="utf-8"))
    features = feature_info["selected_features"] if isinstance(feature_info, dict) else feature_info
    if not features or len(features) != len(set(features)) or "severity" in features:
        raise ValueError("Invalid feature selection JSON")
    feature_sha = sha256_file(args.feature_json)
    random.seed(args.seed)
    seed_everything(args.seed)
    datasets = ("ciciot2023", "diad2024") if args.dataset == "all" else (args.dataset,)
    for dataset in datasets:
        directory = args.split_root / dataset
        inputs = validate_stage3_inputs(directory, dataset, window_size=args.window_size)
        # Do not resume old checkpoints/caches; provenance is unique for each run.
        for link, paths in inputs.items():
            train_link(dataset, link, paths, features, feature_sha, args, args.output_root)


if __name__ == "__main__":
    main()
