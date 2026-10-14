#!/usr/bin/env python3
"""Fail-closed, source-only AFRAS-FL manuscript SUBMISSION READINESS audit.

This is a checklist/evidence inventory, NOT a detector of scientific truth.
No raw CSV, TEST CSV, model checkpoint or confidential source archive is read.
File *existence* never proves publisher authenticity, valid split or metrics.
No network, GitHub credentials, training, model evaluation or writes to source.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

SCHEMA = "afras-final-scientific-readiness-audit-v1"
DATASETS = ("ciciot2023", "diad2024")
LINKS = ("Link_1_Core", "Link_2_Aggregation_L", "Link_3_Aggregation_R",
         "Link_4_Edge_L", "Link_5_Edge_R")
PASS = "IMPLEMENTED_STATIC_ONLY"
BLOCKED = "BLOCKED"
REVIEW = "INDEPENDENT_REVIEW_REQUIRED"


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_repository(root, target_journal="mdpi-ai", seed=42):
    """Build machine-readable evidence gates; no sensitive data is opened."""
    root = Path(root).resolve()
    if target_journal not in ("mdpi-ai", "ieee-iotj"):
        raise ValueError("Unsupported target journal")
    if type(seed) is not int or seed < 0:
        raise ValueError("Seed must be a nonnegative integer")
    manuscript = root / "paper/main.tex"
    if not manuscript.is_file():
        raise FileNotFoundError("Cannot audit manuscript without paper/main.tex")
    tex = manuscript.read_text(encoding="utf-8")
    gates = []

    def gate(identifier, state, scope, reason, evidence, next_step):
        if state not in (PASS, BLOCKED, REVIEW):
            raise ValueError("Invalid readiness state")
        gates.append({
            "id": identifier,
            "status": state,
            "scope": scope,
            "why": reason,
            "evidence": evidence,
            "next_action": next_step,
        })

    source_code = [
        "scripts/data/audit_original_csvs.py",
        "scripts/data/prepare_official_dataset_archive.py",
        "scripts/data/unify_features_v2.py",
        "scripts/data/split_records_leakfree.py",
        "scripts/data/select_features_train_only.py",
        "scripts/data/strict_test_guard.py",
        "scripts/training/strict_fuzzy_core.py",
        "scripts/training/strict_fed_core.py",
        "scripts/training/train_mamba_strict.py",
        "scripts/training/train_federated_strict.py",
        "scripts/evaluation/evaluate_strict_test.py",
        "scripts/analysis/audit_metrics_statistics.py",
    ]
    absent_code = [rel for rel in source_code if not (root / rel).is_file()]
    gate(
        "STRICT_PIPELINE_CODE", BLOCKED if absent_code else PASS, "implementation",
        "Source files exist only; no conclusion about runtime fitness or validated results.",
        {"required_code_files": len(source_code), "missing_files": absent_code},
        "Restore missing programs, rerun CI and perform verified real-data integration."
        if absent_code else "Next: authenticated sources + integration/training evidence.")

    workflow = root / ".github/workflows/strict-split-tests.yml"
    gate(
        "CI_TEST_DEFINITION", PASS if workflow.is_file() else BLOCKED, "implementation",
        "A CI definition is NOT proof that any particular commit has passing jobs.",
        {"workflow_present": workflow.is_file()},
        "Verify the exact branch HEAD's GitHub Actions conclusion and logs.")

    expected_template = "mdpi" if target_journal == "mdpi-ai" else "ieee"
    is_ieee = bool(re.search(r"\\documentclass(?:\[[^\]]*\])?\{IEEEtran\}", tex))
    is_mdpi = bool(re.search(r"\\documentclass(?:\[[^\]]*\])?\{Definitions\}", tex))
    matches = is_mdpi if expected_template == "mdpi" else is_ieee
    gate(
        "TARGET_JOURNAL_TEMPLATE", PASS if matches else BLOCKED, "manuscript",
        "Journal class file must match the requested target, not just render.",
        {"requested_journal": target_journal,
         "detected_class": "IEEEtran" if is_ieee else
                           ("Definitions" if is_mdpi else "unknown")},
        "Prepare a separate properly templated manuscript only with researcher approval; "
        "do NOT silently overwrite paper/main.tex.")

    has_redlines = bool(re.search(r"\\(?:rev|strk)\s*\{", tex))
    gate(
        "TRACKED_REVISION_MARKUP", REVIEW if has_redlines else PASS, "manuscript",
        "Visible \\rev / \\strk color/strikeout changes need submission-format review.",
        {"revision_macros_in_use": has_redlines},
        "Check the journal's revision submission requirements; produce a clean "
        "copy only on explicit authorization.")

    historical_p = bool(re.search(r"\\times\s*10\^\{-[0-9]+\}", tex))
    episode_tests = bool(re.search(r"Welch\s*\$t\$-tests.{0,120}n\s*=\s*50", tex, re.S))
    gate(
        "MANUSCRIPT_SIGNIFICANCE", BLOCKED if historical_p or episode_tests else REVIEW,
        "statistical_inference",
        "Very small historical p-values and evaluation-episode unit cannot be "
        "independently reproduced from repository evidence.",
        {"has_historical_p_value_notation": historical_p,
         "has_50_episode_welch_comparison": episode_tests},
        "Provide all paired independent seed-run vectors, original evaluation "
        "logs/IDs and a prespecified cluster/seed-level testing and multiplicity plan.")

    has_two_seed_diad = bool(re.search(
        r"DIAD2024[^\n]*\$\s*2\s*\$\s*\\\\", tex))
    gate(
        "REPLICATION_INDEPENDENT_SEEDS", BLOCKED, "statistical_inference",
        "Reported multi-seed summary uses at most three seeds for CICIoT2023 "
        "and two for DIAD2024; independent raw run vectors unavailable.",
        {"manuscript_diad_two_seed_rows": has_two_seed_diad,
         "original_run_vectors_authenticated": False},
        "Freeze predeclared comparisons and obtain adequate matched independent "
        "training runs; do not substitute evaluation episodes for seeds.")

    for ds in DATASETS:
        raw = root / "data/raw_official_csv" / ds / "flow"
        gate(
            f"OFFICIAL_SOURCE_{ds.upper()}",
            REVIEW if raw.is_dir() else BLOCKED, "source_authenticity",
            "Raw CSV presence is not publisher authentication, feature modality "
            "validation, licensing or independent SHA evidence.",
            {"expected_local_csv_directory_present": raw.is_dir(),
             "publisher_checksum_verified_by_auditor": False},
            "Obtain original flow CSVs from CIC with source release/checksum "
            "and manually reconcile raw headers, labels, device/group/time fields.")

        split_manifest = root / "data/full_candidate_strict_split" / ds / "manifest.json"
        gate(
            f"STRICT_SPLIT_{ds.upper()}",
            REVIEW if split_manifest.is_file() else BLOCKED, "data_leakage",
            "Presence of a split manifest cannot establish source/group "
            "independence; this check does not open TEST or manifest contents.",
            {"manifest_present": split_manifest.is_file(), "test_opened": False},
            "Audit original capture/time/group provenance, embargo, "
            "feature-selection and all TRAIN-only transforms before training.")

        teachers = [root / "experiments/strict_stage3" / ds /
                    f"seed_{seed}" / link / "provenance.json" for link in LINKS]
        complete = all(p.is_file() for p in teachers)
        gate(
            f"STAGE3_TEACHERS_{ds.upper()}",
            REVIEW if complete else BLOCKED, "training",
            "Teacher provenance is required for all five links and the chosen seed; "
            "presence alone does not verify weights/checksums or real training.",
            {"seed": seed, "teacher_provenance_files_present":
             sum(p.is_file() for p in teachers), "expected_links": len(LINKS)},
            "Train and verify all five source-authenticated Mamba teachers, "
            "using TRAIN data and VAL checkpoint selection.")

        run = root / "experiments/strict_stage4" / ds / f"seed_{seed}" / "RUN_PROVENANCE.json"
        gate(
            f"STAGE4_FEDERATED_{ds.upper()}",
            REVIEW if run.is_file() else BLOCKED, "training",
            "A provenance path is insufficient proof of completed or secure "
            "federated training, dynamic RL or meaningful five-link topology.",
            {"stage4_run_provenance_present": run.is_file(), "seed": seed},
            "Verify FedAvg/FedProx/Q-learning run logs, v2 fuzzy rule SHA "
            "and source matching; report only actually implemented terms.")

        test_receipt = (root / "experiments/strict_test_eval" / ds /
                        f"seed_{seed}" / "TEST_UNSEAL_RECEIPT.json")
        gate(
            f"ONE_TIME_SEALED_TEST_{ds.upper()}",
            REVIEW if test_receipt.is_file() else BLOCKED, "evaluation",
            "Receipt existence marks TEST unsealing attempt, not a successful "
            "or valid outcome. No TEST files or receipts are read by this audit.",
            {"unseal_receipt_present": test_receipt.is_file(), "test_opened": False},
            "After freezing models/analysis, audit the one-time TEST receipt "
            "and immutable outputs separately; never retune against TEST.")

    gate(
        "HISTORICAL_DATA_PIPELINE_REPRODUCIBILITY", BLOCKED, "reproducibility",
        "Original data/unify_features.py and historical published checkpoints/"
        "per-seed artifacts are not authenticated by newly added scripts.",
        {"new_v2_implementation_not_historical_recovery": True},
        "Recover original preprocessing and artifacts or explicitly distinguish "
        "new strict experiment from historical manuscript results.")

    gate(
        "FIVE_PHYSICAL_LINK_AND_SEVERITY_EVIDENCE", BLOCKED, "data_provenance",
        "A researcher-declared five-link client map and High/Medium/Low "
        "policy do not establish five observed physical network links or "
        "dataset-grounded severity definitions.",
        {"physical_link_independence_verified": False,
         "raw_label_severity_policy_independently_verified": False},
        "Provide documented original link/session/device fields and signed-off "
        "original-category to binary/severity mapping for both datasets.")

    gate(
        "RL_NEIGHBOR_AND_DEPLOYMENT_CLAIMS", BLOCKED, "method_claim_alignment",
        "Strict v2 uses gamma=0 contextual-bandit rewards, mu_link=0 and an "
        "assumed action-cost latency proxy; no deployed SDN/neighbor MDP evidence.",
        {"strict_protocol": "strict-fed-contextual-bandit-v2",
         "neighbor_reward_verified": False,
         "measured_deployment_latency": False},
        "Implement and independently evaluate neighbor feedback/latency, or "
        "qualify corresponding claims as unsupported/exploratory.")

    gate(
        "FUZZY_HISTORICAL_VERSUS_STRICT_V2", BLOCKED, "method_claim_alignment",
        "TRAIN-scale-consistent nine-cell strict fuzzy v2 is a NEW method; "
        "it is not a measured reproduction of historical seven-phase AFRAS-FL.",
        {"strict_fuzzy_is_new_protocol": True},
        "Use distinct manuscript methodology/results for any future v2 study; "
        "do not paste v2 unit tests as proof of earlier manuscript numbers.")

    gate(
        "REAL_FPR_FNR_FAIRNESS_AND_LATENCY", BLOCKED, "evaluation",
        "Binary FPR/FNR require authenticated original attack labels; "
        "Jain action-success fairness is not class/device fairness; "
        "reported latency/overhead requires hardware traces.",
        {"historical_source_confusion_counts_authenticated": False},
        "Collect sealed per-client and pooled confusion counts, uncertainty, "
        "time traces and evidence of original attack/benign categories.")

    gate(
        "SUBMISSION_REVIEW_AND_COAUTHOR_APPROVAL", REVIEW, "editorial",
        "Manuscript suitability, ethics/data license, references, author consent "
        "and chosen journal policy require accountable human review.",
        {"human_approval_present_in_this_static_audit": False},
        "Obtain a final source/data/statistical review and all coauthor signoffs.")

    summary = dict(Counter(g["status"] for g in gates))
    ready = summary.get(BLOCKED, 0) == 0 and summary.get(REVIEW, 0) == 0
    return {
        "schema": SCHEMA,
        "as_of_utc_date": str(date.today()),
        "target_journal": target_journal,
        "scope": "source-only; no training, TEST inspection, or publisher archive validation",
        "manuscript_source_sha256": _sha256(manuscript),
        "readiness": "READY_FOR_INDEPENDENT_FINAL_REVIEW" if ready else
                     "NOT_READY_FOR_SUBMISSION",
        "counts": {"blocked": summary.get(BLOCKED, 0),
                   "independent_review_required": summary.get(REVIEW, 0),
                   "implemented_static_only": summary.get(PASS, 0),
                   "total": len(gates)},
        "gates": gates,
        "cautions": [
            "Passing synthetic CI does not reproduce historical performance",
            "Any available data or checkpoint path is only a local existence signal",
            "No sealed TEST file, run output, or original source CSV is read",
            "Do not submit old/strict v2 results under interchangeable names",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--target-journal", choices=("mdpi-ai", "ieee-iotj"),
                        default="mdpi-ai")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-ready", action="store_true",
                        help="Exit nonzero when any submission blocker/review item remains")
    a = parser.parse_args()
    result = inspect_repository(a.repo_root, a.target_journal, a.seed)
    data = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if a.output:
        if a.output.exists():
            parser.error(f"Refusing to overwrite previous readiness audit: {a.output}")
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(data, encoding="utf-8")
    else:
        print(data, end="")
    if a.require_ready and result["readiness"] != "READY_FOR_INDEPENDENT_FINAL_REVIEW":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
