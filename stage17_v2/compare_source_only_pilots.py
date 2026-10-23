#!/usr/bin/env python3
"""Compare two genuine *source-validation* exploratory N-BaIoT pilots.

No held-out device predictions are available. This is NOT evidence of external
generalization, novelty, privacy guarantee, or final manuscript performance.
"""
import argparse
import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def compare(a, b, a_prov, b_prov):
    assert a["status"] == b["status"] == "EXPLORATORY_SOURCE_ONLY_PILOT"
    for run in (a,b):
        assert run["confirmatory"] is False
        assert run["heldout_evaluated"] is False
        assert run["heldout_archive_opened"] is False
        assert run["target_labels_used"] is False
        assert run["test_accuracy_claim"] is None
    assert a["heldout_device_name_only"] == b["heldout_device_name_only"]
    assert a["source_validation_device"] == b["source_validation_device"]
    assert a["training_devices"] == b["training_devices"]
    assert a["source_native_class_counts"] == b["source_native_class_counts"]
    assert a["source_only_sampled_class_cap"] == b["source_only_sampled_class_cap"]
    assert a["hyperparameters"]["rounds"] == b["hyperparameters"]["rounds"]
    assert a_prov["source_member_count"] == b_prov["source_member_count"]
    matched_original_zip_bytes = (
        a_prov["outer_archive_sha256"] == b_prov["outer_archive_sha256"]
    )
    assert matched_original_zip_bytes, "UCI outer ZIP SHA differs between runs"

    table = {}
    for method in ("fedavg", "fedprox"):
        x, y = a["algorithms"][method], b["algorithms"][method]
        assert len(x) == len(y) == a["hyperparameters"]["rounds"]
        rows = []
        for r0, r1 in zip(x, y):
            assert r0["round"] == r1["round"]
            assert sum(r0[z] for z in ("tp","tn","fp","fn")) == sum(
                r1[z] for z in ("tp","tn","fp","fn"))
            rows.append({
                "round": r0["round"],
                "unweighted_ba": r0["validation_only_balanced_accuracy"],
                "weighted_ba": r1["validation_only_balanced_accuracy"],
                "unweighted_fpr": r0["validation_only_fpr"],
                "weighted_fpr": r1["validation_only_fpr"],
                "unweighted_attack_recall": r0["validation_only_attack_recall"],
                "weighted_attack_recall": r1["validation_only_attack_recall"],
                "unweighted_confusion": {z:r0[z] for z in ("tp","tn","fp","fn")},
                "weighted_confusion": {z:r1[z] for z in ("tp","tn","fp","fn")},
            })
        z = rows[-1]
        table[method] = {
            "rounds": rows,
            "source_validation_balanced_accuracy_delta": z["weighted_ba"]-z["unweighted_ba"],
            "source_validation_fpr_delta": z["weighted_fpr"]-z["unweighted_fpr"],
            "weighted_attack_only_collapse": (
                z["weighted_confusion"]["tn"] == 0
                and z["weighted_confusion"]["fn"] == 0
            ),
        }
    return {
        "analysis_status": "EXPLORATORY_SOURCE_ONLY_MATCHED_ARTIFACT_COMPARISON",
        "both_real_UCI_source_replay_workflows_succeeded": True,
        "same_public_UCI_archive_sha256": matched_original_zip_bytes,
        "same_original_UCI_outer_sha256": a_prov["outer_archive_sha256"],
        "heldout_test_used": False,
        "source_validation_only": True,
        "experiment_type": "pilot class-weight debug; not confirmatory",
        "source_loss_modes": {
            "unweighted": a.get("source_training_loss_balance", "none"),
            "weighted": b["source_training_loss_balance"],
        },
        "methods": table,
        "limitations": [
            "Source-only, per-class-capped samples alter native prevalence.",
            "No held-out device examples are opened, fit, or evaluated.",
            "Source-only validation differences do not establish causal generalization.",
            "Any confirmatory comparison requires a prospectively frozen full native protocol.",
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--baseline-provenance", type=Path, required=True)
    p.add_argument("--weighted", type=Path, required=True)
    p.add_argument("--weighted-provenance", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a=load(p.parse_args().baseline)
    args=p.parse_args()
    result=compare(a,load(args.weighted),load(args.baseline_provenance),
                   load(args.weighted_provenance))
    args.output.write_text(json.dumps(result, indent=2), encoding="utf8")
    print("MATCHED_SOURCE_ONLY_COMPARISON", json.dumps({
        "same_official_outer_sha256": result["same_public_UCI_archive_sha256"],
        "final": {method: {
            "unweighted": v["rounds"][-1]["unweighted_ba"],
            "weighted": v["rounds"][-1]["weighted_ba"],
            "fpr_unweighted": v["rounds"][-1]["unweighted_fpr"],
            "fpr_weighted": v["rounds"][-1]["weighted_fpr"],
            "weighted_attack_only_collapse": v["weighted_attack_only_collapse"]
        } for method, v in result["methods"].items()}
    }, separators=(",",":")), flush=True)


if __name__=="__main__":
    main()
