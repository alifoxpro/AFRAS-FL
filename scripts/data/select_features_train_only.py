#!/usr/bin/env python3
"""Select a common cross-dataset feature set from TRAIN ONLY.

Supervised ANOVA-F scores are computed on TRAIN rows only (five links per
dataset). No VAL or TEST CSV may be loaded in this program. Candidates MUST
come from an independently reviewed schema allowlist, never test outcomes.
This is a NEW protocol, not reproduction of historic SHAP/LIME selection.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

SCHEMA = "afras-train-feature-selection-v1"
SPLIT_SCHEMA = "afras-fl-strict-ordered-split-v1"
REJECT = re.compile(
    r"(^__|(^|_)(label|class|target|attack|benign|severity|outcome|"
    r"session|device|flow_id|row_id|link_id|src_ip|dst_ip|ip_address|"
    r"group_id|timestamp|source_row_id)(_|$))", re.I)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def candidate_list(path):
    """Fail closed: requiring independently reviewed, feature-only whitelist."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != "afras-candidate-feature-review-v1":
        raise ValueError("Missing reviewed candidate feature schema")
    if not isinstance(value.get("review_reference"), str) or not value["review_reference"].strip():
        raise ValueError("Candidate features need review_reference / source schema provenance")
    features = value.get("candidate_features")
    if not isinstance(features, list) or len(features) < 14 or len(set(map(str, features))) != len(features):
        raise ValueError("At least 14 unique candidate feature names required")
    for name in features:
        if not isinstance(name, str) or not name or REJECT.search(name):
            raise ValueError(f"Forbidden target/identifier or invalid candidate feature: {name!r}")
    return features, value["review_reference"]


def read_manifest(split_root, dataset):
    root = Path(split_root) / dataset
    mf = root / "manifest.json"
    manifest = json.loads(mf.read_text(encoding="utf-8"))
    if manifest.get("dataset") != dataset or manifest.get("schema") != SPLIT_SCHEMA:
        raise ValueError(f"Invalid split manifest: {mf}")
    links = manifest.get("links")
    if not isinstance(links, dict) or len(links) != 5:
        raise ValueError("Exactly five source links per dataset required")
    return root, manifest, sha256(mf)


def stream_moments(path, features, expected_sha, moments):
    if sha256(path) != expected_sha:
        raise ValueError(f"Changed TRAIN partition: {path}")
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not (set(features) | {"severity"}).issubset(reader.fieldnames):
            raise ValueError(f"Missing candidate features or severity in TRAIN: {path}")
        count = 0
        for row in reader:
            category = row["severity"]
            if category not in ("High", "Medium", "Low"):
                raise ValueError(f"Invalid TRAIN severity: {category!r}")
            if category not in moments:
                moments[category] = {
                    feature: [0, 0.0, 0.0] for feature in features}
            for feature in features:
                try:
                    value = float(row[feature])
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Invalid numeric TRAIN feature {feature}") from exc
                if not math.isfinite(value):
                    raise ValueError(f"Nonfinite TRAIN feature {feature}")
                state = moments[category][feature]
                state[0] += 1
                delta = value - state[1]
                state[1] += delta / state[0]
                state[2] += delta * (value - state[1])
            count += 1
    if count == 0:
        raise ValueError(f"Empty TRAIN file: {path}")
    return count


def anova_score(moments, feature):
    class_states = [moments[label][feature] for label in ("High", "Medium", "Low")
                    if label in moments and moments[label][feature][0] > 0]
    n = sum(s[0] for s in class_states)
    k = len(class_states)
    if n <= k or k < 2:
        raise ValueError("Insufficient independent TRAIN severity classes for ANOVA")
    overall_mean = sum(s[0] * s[1] for s in class_states) / n
    between = sum(s[0] * (s[1] - overall_mean)**2 for s in class_states) / (k-1)
    within = sum(s[2] for s in class_states) / (n-k)
    if within <= 1e-20:
        if between > 1e-20:
            raise ValueError(f"Near-perfect class separator {feature}: investigate target leakage")
        return 0.0
    return float(between / within)


def select(split_root, candidates_file, datasets, output_file, n_features=14):
    if n_features < 1:
        raise ValueError("n_features must be positive")
    candidates, reference = candidate_list(candidates_file)
    if n_features > len(candidates):
        raise ValueError("More selected features than candidates")
    if len(set(datasets)) != len(datasets) or not datasets:
        raise ValueError("Dataset list must be unique and nonempty")
    per_dataset, hashes, samples, per_file = {}, {}, {}, {}
    for dataset in datasets:
        root, manifest, manifest_sha = read_manifest(split_root, dataset)
        hashes[dataset] = manifest_sha
        moments = {}
        samples[dataset] = 0
        per_file[dataset] = {}
        for link, entry in sorted(manifest["links"].items()):
            if (not link.startswith("Link_") or "/" in link or "\\" in link
                    or ".." in link):
                raise ValueError("Invalid TRAIN link name")
            meta = entry["partitions"]["train"]
            if meta.get("relative_path") != f"train/{link}.csv":
                raise ValueError("Unexpected TRAIN partition path")
            path = root / "train" / (link+".csv")
            n = stream_moments(path, candidates, meta["sha256"], moments)
            if n != meta["records"]:
                raise ValueError("TRAIN record count changed")
            per_file[dataset][link] = meta["sha256"]
            samples[dataset] += n
        per_dataset[dataset] = {f: anova_score(moments, f) for f in candidates}
    # Dataset-balanced ranking so the larger dataset cannot dominate.
    # Ranks avoid cross-dataset F-score scale and class-imbalance differences.
    ranks = {d: {f: rank for rank, f in enumerate(
        sorted(candidates, key=lambda x: (-per_dataset[d][x], x)), start=1)}
        for d in datasets}
    ordering = sorted(candidates, key=lambda f: (
        sum(ranks[d][f] for d in datasets) / len(datasets), f))
    chosen = ordering[:n_features]
    record = {
        "schema": SCHEMA,
        "method": "TRAIN-only supervised ANOVA-F (mean per-dataset feature rank)",
        "selected_features": chosen,
        "candidate_features_sha256": sha256(candidates_file),
        "candidate_review_reference": reference,
        "split_manifest_sha256_by_dataset": hashes,
        "train_sha256_by_dataset_link": per_file,
        "train_rows_by_dataset": samples,
        "datasets": datasets,
        "feature_rank_by_dataset": ranks,
        "n_selected": n_features,
        "limits": [
            "Does not prove correctness of original raw data harmonization",
            "Source label taxonomy may already encode target leakage",
            "Session/group overlap and target-correlated IDs require independent audit",
            "ANOVA is a new method, NOT historical XAI SHAP/LIME results",
        ],
    }
    output_file = Path(output_file)
    if output_file.exists():
        raise FileExistsError(f"Will not overwrite feature selection: {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return record


def main():
    repo = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split-root", type=Path,
                   default=repo / "data" / "unified_14features_5links_strict_split")
    p.add_argument("--candidate-json", type=Path, required=True)
    p.add_argument("--datasets", nargs="+", default=["ciciot2023", "diad2024"])
    p.add_argument("--n-features", type=int, default=14)
    p.add_argument("--output", type=Path,
                   default=repo / "data" / "selected_14_train_only.json")
    args = p.parse_args()
    out = select(args.split_root, args.candidate_json, args.datasets,
                 args.output, args.n_features)
    print(f"Selected {out['n_selected']} TRAIN-only features: {out['selected_features']}")


if __name__ == "__main__":
    main()
