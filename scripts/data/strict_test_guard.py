"""Verify frozen artifacts for one-time held-out TEST evaluation.

No training, fitting or phase selection occurs in this module.
TRAIN and VAL CSV files are NOT opened; only recorded source hashes are checked.
"""
import hashlib
import json
import math
from pathlib import Path

from scripts.data.label_evidence import validate_evidence_file

STAGE3_SCHEMA = "strict-stage3-train-val-only-v1"
STAGE4_SCHEMA = "strict-fed-contextual-bandit-v1"
SPLIT_SCHEMA = "afras-fl-strict-ordered-split-v1"
PHASES = ("B2_FedAvg", "B3_FedProx", "B4_TrainOnlyFuzzy_FedProx")


def sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def validate_frozen_run(dataset, seed, split_root, stage3_root, stage4_root, feature_json,
                        label_evidence_path=None):
    """Return verified file paths and frozen phase names; only TEST CSVs opened."""
    split_dir = Path(split_root).resolve() / dataset
    stage4_dir = Path(stage4_root).resolve() / dataset / f"seed_{seed}"
    split_file = split_dir / "manifest.json"
    provenance_file = stage4_dir / "RUN_PROVENANCE.json"
    manifest, run = _read(split_file), _read(provenance_file)

    _require(manifest.get("schema") == SPLIT_SCHEMA, "Split schema mismatch")
    _require(manifest.get("dataset") == dataset, "Split dataset mismatch")
    _require(manifest.get("method") == "source_order_with_embargo; split_before_windowing",
             "Unexpected split method")
    _require(run.get("schema") == STAGE4_SCHEMA and run.get("dataset") == dataset,
             "Stage 4 dataset/protocol mismatch")
    _require(run.get("test_access") == "NONE", "Training already exposed TEST")
    _require(run.get("mu_link_effective") == 0 and run.get("discount_gamma") == 0,
             "Unverified link/MDP settings")
    _require(run.get("source_experiment") == "new protocol, NOT historical manuscript output",
             "Unexpected historical/experimental provenance")
    _require(run.get("split_manifest_sha256") == sha256_file(split_file),
             "Split manifest modified after Stage 4")
    settings = run.get("settings", {})
    _require(isinstance(settings, dict) and
             str(settings.get("dataset")) == dataset and settings.get("seed") == seed,
             "Training settings/seed mismatch")
    _require(settings.get("pilot") is False and settings.get("max_train_windows") == 0,
             "PILOT/subsampled training is not eligible for final TEST")
    window = settings.get("window_size")
    stride = settings.get("stride")
    _require(isinstance(window, int) and window >= 2 and
             isinstance(stride, int) and 0 < stride <= window and
             window == manifest.get("window_size"), "Invalid window/stride")
    _require(settings.get("mu_link") in (0, 0.0),
             "Nonzero neighbor-reward configuration is unsupported")
    registered_sha = run.get("raw_label_evidence_sha256")
    if registered_sha is None:
        _require(label_evidence_path is None,
                 "Raw-label evidence must be registered BEFORE training, not added at TEST")
        label_evidence = None
    else:
        _require(label_evidence_path is not None,
                 "Missing pre-registered raw-label evidence for frozen TEST")
        _require(sha256_file(label_evidence_path) == registered_sha,
                 "Raw-label evidence changed after Stage 4")
        label_evidence = validate_evidence_file(label_evidence_path, dataset)


    feature_path = Path(feature_json).resolve()
    contents = json.loads(feature_path.read_text(encoding="utf-8"))
    features = contents.get("selected_features") if isinstance(contents, dict) else contents
    _require(isinstance(features, list) and len(features) == 14 and
             all(isinstance(f, str) and f and f != "severity" for f in features) and
             len(set(features)) == len(features), "Expected 14 valid unique features")
    feature_sha = sha256_file(feature_path)

    phases = run.get("phases")
    _require(isinstance(phases, list) and len(phases) == len(PHASES) and
             all(isinstance(p, dict) for p in phases) and
             tuple(p.get("phase") for p in phases) == PHASES,
             "Frozen validation-phase list missing or reordered")
    models = {}
    for phase in phases:
        name = phase["phase"]
        _require(phase.get("validation_only") is True and
                 isinstance(phase.get("best_round_val_only"), int) and
                 phase["best_round_val_only"] > 0, f"Unfrozen VAL selection: {name}")
        score = phase.get("best_val_mean_action_success")
        _require(isinstance(score, (int, float)) and math.isfinite(score) and 0 <= score <= 1,
                 f"Invalid VAL score: {name}")
        _require(phase.get("checkpoint") == name + ".pt",
                 f"Unexpected policy filename: {name}")
        model_file = stage4_dir / (name + ".pt")
        _require(model_file.is_file() and
                 sha256_file(model_file) == phase.get("checkpoint_sha256"),
                 f"Policy checkpoint changed: {name}")
        models[name] = model_file

    manifest_links = manifest.get("links", {})
    _require(isinstance(manifest_links, dict) and len(manifest_links) == 5,
             "Exactly five TEST clients are required")
    clients = {}
    for link, meta in sorted(manifest_links.items()):
        _require(isinstance(link, str) and link.startswith("Link_") and
                 link.replace("_", "").isalnum(), "Unsafe client label")
        stage3_dir = Path(stage3_root).resolve() / dataset / link
        teacher_meta_path = stage3_dir / "provenance.json"
        teacher_meta = _read(teacher_meta_path)
        _require(teacher_meta.get("protocol") == STAGE3_SCHEMA and
                 teacher_meta.get("dataset") == dataset and teacher_meta.get("link") == link,
                 f"Invalid Stage 3 provenance for {link}")
        _require(str(teacher_meta.get("test_access", "")).startswith("NONE"),
                 f"Teacher already accessed TEST: {link}")
        _require(teacher_meta.get("features") == features and
                 teacher_meta.get("feature_list_sha256") == feature_sha and
                 teacher_meta.get("window_size") == window and
                 teacher_meta.get("stride") == stride, f"Teacher preprocessing mismatch: {link}")
        _require(run.get("client_stage3_provenance_sha256", {}).get(link) ==
                 sha256_file(teacher_meta_path), f"Stage 3 provenance changed: {link}")
        teacher_file = stage3_dir / "mamba_val_best.pt"
        scaler_file = stage3_dir / "train_fitted_scaler.npz"
        _require(teacher_file.is_file() and
                 run.get("client_checkpoint_sha256", {}).get(link) == sha256_file(teacher_file),
                 f"Teacher checkpoint changed: {link}")
        _require(scaler_file.is_file() and
                 run.get("client_stage3_scaler_sha256", {}).get(link) == sha256_file(scaler_file),
                 f"Train-fitted scaler changed: {link}")
        partitions = meta.get("partitions", {})
        for part in ("train", "val"):
            _require(partitions.get(part, {}).get("sha256") ==
                     teacher_meta.get(part + "_sha256"),
                     f"Split lineage mismatch: {link}/{part}")
        _require(run.get("client_train_counts", {}).get(link, 0) > 0 and
                 run.get("fuzzy_train_only", {}).get(link, {}).get("train_only") is True,
                 f"TRAIN-only federated setup not verified: {link}")
        test_meta = partitions.get("test", {})
        _require(test_meta.get("relative_path") == "test/" + link + ".csv",
                 f"Unexpected TEST path: {link}")
        test_file = (split_dir / "test" / (link + ".csv")).resolve()
        _require(test_file.is_file() and test_file.parent == (split_dir / "test").resolve(),
                 f"Missing TEST file: {link}")
        _require(test_meta.get("records", 0) >= window and
                 sha256_file(test_file) == test_meta.get("sha256"),
                 f"TEST split checksum mismatch: {link}")
        clients[link] = {
            "test_csv": test_file,
            "test_sha256": test_meta["sha256"],
            "teacher_checkpoint": teacher_file,
            "train_fitted_scaler": scaler_file,
        }
    return {
        "dataset": dataset, "window_size": window, "stride": stride,
        "features": features, "feature_list_sha256": feature_sha,
        "split_manifest_sha256": sha256_file(split_file),
        "stage4_provenance_sha256": sha256_file(provenance_file),
        "phases": models, "clients": clients,
        "raw_label_evidence": label_evidence,
        "raw_label_evidence_sha256": registered_sha,
    }
