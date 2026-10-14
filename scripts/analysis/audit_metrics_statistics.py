#!/usr/bin/env python3
"""Source-only manuscript statistics audit and exact paired seed analysis.

Never reads TEST windows/checkpoints; never creates new test performance data.
Statistical tests accept only EXPLICIT user-supplied matched per-run values
from independent training seeds under the same frozen evaluation definition.
A shared TEST across seeds is not independent test sampling; any p-value
conditional on that TEST only describes model-training seed variability.
"""
import argparse
import hashlib
import itertools
import json
import math
import re
import statistics
from pathlib import Path

SCHEMA = "afras-statistical-claims-audit-v1"
INPUT_SCHEMA = "afras-declared-paired-seed-values-v1"


def _finding(lines, finding_id, pattern, severity, explanation, action):
    results = []
    rx = re.compile(pattern, re.IGNORECASE)
    for line_number, line in enumerate(lines, start=1):
        if rx.search(line):
            results.append({
                "id": finding_id, "priority": severity,
                "line": line_number, "excerpt": line.strip()[:220],
                "finding": explanation, "required_evidence": action,
            })
    return results


def audit_manuscript(tex):
    """Classify evidence gaps, WITHOUT representing claims as proven false."""
    lines = tex.splitlines()
    findings = []
    findings += _finding(
        lines, "EPISODE_AS_INDEPENDENT_UNIT", r"Welch\s*\$t\$-tests.*n\s*=\s*50",
        "critical",
        "50 evaluation episodes may reuse one model and overlapping flows; "
        "they are not established as 50 independent training runs.",
        "Provide raw episode/session IDs, clustering, training seeds and the "
        "independence assumptions; reanalyze at an appropriate experimental unit.")
    findings += _finding(
        lines, "SEED_COUNT_2_NOT_SUFFICIENT", r"DIAD2024.*\$\s*2\s*\$",
        "critical",
        "This DIAD2024 row reports only 2 independent training seeds; no "
        "reliable inferential effect size/p-value can be established from it.",
        "Provide at least 5-6 paired independent training seeds and immutable "
        "run-level provenance, then prespecify the inferential test.")
    findings += _finding(
        lines, "RUN_LEVEL_REPLICATION_MISSING", r"only three seeds are reported",
        "critical",
        "Three training seeds and reused TEST episodes do not independently "
        "verify the historical episode-level very small p-values.",
        "Provide all per-seed run-level metrics, raw logs, checkpoint/split "
        "hashes, and predeclared comparisons.")
    findings += _finding(
        lines, "HISTORICAL_P_VALUE_NOT_REPRODUCED",
        r"(\\times\s*10\^\{-1[0-9]\}|Cohen.?s\s*\$d)",
        "warning",
        "Manuscript p-values/effect sizes are historical claims whose run-level "
        "input vectors and independence design are not present in this repository.",
        "Recompute from source run vectors and disclose correct experimental "
        "unit and multiplicity correction; never transfer them to Stage4 v2.")
    findings += _finding(
        lines, "SOURCE_METRIC_MAPPING_UNVERIFIED",
        r"(false.positive rate from|FedProx false.positive rate from|FPR of \$|FPR.*150)",
        "critical",
        "Historical FPR is not demonstrated to equal binary IDS FP/(FP+TN) "
        "on authenticated source Attack/Benign labels.",
        "Verify every original category, binary Attack/Benign derivation and "
        "per-run confusion counts. Low severity need not mean benign.")
    findings += _finding(
        lines, "DEPLOYMENT_LATENCY_NOT_VERIFIED",
        r"approximately\s*\$7\\%\$.*per.round",
        "warning",
        "Historical runtime overhead is not independently reproduced by "
        "the synthetic code tests.",
        "Provide hardware details, wall-clock profiles, warm-up, uncertainty "
        "and matched workload logs.")
    # The caption states 3 seeds for both datasets, but DIAD rows contain 2.
    captions = [x for x in lines if "Multi-seed mean-of-run replication" in x]
    diad_two = any(re.search(r"DIAD2024.*\$\s*2\s*\$", x) for x in lines)
    if captions and diad_two and any(r"42, 123, 2026" in c for c in captions):
        start = next(i for i, x in enumerate(lines, 1)
                     if "Multi-seed mean-of-run replication" in x)
        findings.append({
            "id": "MULTISEED_CAPTION_SCOPE_MISMATCH", "priority": "warning",
            "line": start,
            "excerpt": lines[start-1].strip()[:220],
            "finding": "Caption lists three seeds for both benchmarks, while "
                       "DIAD2024 table rows list n=2; explanatory prose "
                       "clarifies the omission but caption is misleading.",
            "required_evidence": "Indicate per-dataset seed sets explicitly; "
                                 "preserve missing DIAD runs as missing, not imputed.",
        })
    return {
        "schema": SCHEMA,
        "manuscript_sha256": hashlib.sha256(tex.encode("utf-8")).hexdigest(),
        "status": "STATIC_ONLY_NO_REAL_TRAINING_EVIDENCE",
        "findings": findings,
        "critical_count": sum(x["priority"] == "critical" for x in findings),
        "methods_limitations": [
            "Episode-level samples need defensible statistical independence",
            "Repeated windows/clients from one shared corpus are clustered",
            "Training-seed variation is not independent dataset generalization",
            "No real dataset run-level evidence or original label authentication exists",
            "No historical p-values, effects, FPR/FNR, or deployment timing are verified",
        ],
    }


def exact_paired_sign_flip(values_a, values_b, min_seeds=5, max_exact=16):
    """Exact TWO-SIDED paired sign-flip at the training-SEED level.

    Predeclared comparison A minus B. These are declared same-seed run
    summaries, not episodes. A shared held-out TEST remains a shared TEST:
    this inference is conditional on that fixed dataset and its labeling.
    """
    if not isinstance(values_a, dict) or not isinstance(values_b, dict):
        raise ValueError("Both paired arms must provide seed keyed dictionaries")
    if set(values_a) != set(values_b):
        raise ValueError("Both arms must have identical independent training seed IDs")
    seed_names = sorted(values_a, key=str)
    n = len(seed_names)
    if not min_seeds <= n <= max_exact:
        raise ValueError(f"Exact analysis requires {min_seeds}..{max_exact} "
                         "matched training seeds; never substitute episodes")
    values = []
    for seed in seed_names:
        a, b = values_a[seed], values_b[seed]
        if (type(a) not in (int, float) or type(b) not in (int, float)
                or not math.isfinite(a) or not math.isfinite(b)
                or not 0 <= a <= 1 or not 0 <= b <= 1):
            raise ValueError("Run-level action-success rates must be finite in [0,1]")
        values.append((float(a), float(b)))
    diffs = [a - b for a, b in values]
    observed = abs(math.fsum(diffs))
    magnitudes = [abs(d) for d in diffs]
    extreme, total = 0, 2 ** n
    for signs in itertools.product((-1, 1), repeat=n):
        statistic = abs(math.fsum(s * d for s, d in zip(signs, magnitudes)))
        if statistic >= observed - 1e-12:
            extreme += 1
    sd = statistics.stdev(diffs)
    return {
        "analysis": "exact_two_sided_paired_sign_flip",
        "unit": "independent_training_seed",
        "n_paired_seeds": n,
        "mean_A": statistics.mean(a for a, _ in values),
        "mean_B": statistics.mean(b for _, b in values),
        "mean_paired_difference_A_minus_B": statistics.mean(diffs),
        "sd_paired_difference": sd,
        "cohen_dz_paired": statistics.mean(diffs) / sd if sd > 0 else None,
        "p_unadjusted": extreme / total,
        "permutations_enumerated": total,
        "conditional_on_frozen_test": True,
        "source_runs_independently_authenticated": False,
        "limitations": [
            "User-declared seed values cannot independently certify original runs",
            "A common TEST corpus across seeds does NOT give independent test sets",
            "Permutation null assumes exchangeable signs of paired differences",
            "The smallest two-sided exact p for n=5 is 0.0625",
            "Prespecify comparison family; correct multiplicity before claims",
        ],
    }


def holm_adjust(pvalues):
    """Holm step-down family-wise error adjusted p-values."""
    if not isinstance(pvalues, dict) or not pvalues:
        raise ValueError("Provide a nonempty preregistered comparison family")
    items = sorted(pvalues.items(), key=lambda entry: entry[1])
    if any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
           for _, p in items):
        raise ValueError("Invalid comparison p-value")
    n = len(items)
    adjusted, floor = {}, 0.0
    for rank, (key, p) in enumerate(items):
        floor = max(floor, min(1.0, p * (n - rank)))
        adjusted[key] = floor
    return adjusted


def declared_seed_comparisons(doc):
    """Descriptive/conditional exact tests; NEVER certifies the raw source."""
    if doc.get("schema") != INPUT_SCHEMA or doc.get("statistical_unit") != \
            "independent_training_seed":
        raise ValueError("Unsupported declared independent seed summary")
    if doc.get("dataset") not in ("ciciot2023", "diad2024"):
        raise ValueError("Declare one dataset; never pool mismatched source domains")
    if doc.get("metric") != "pooled_action_success":
        raise ValueError("Only frozen, identically defined action success supported")
    if doc.get("protocol") != "strict-sealed-test-eval-v1":
        raise ValueError("Do not mix historical/strict statistical output definitions")
    trials = doc.get("predeclared_comparisons")
    if not isinstance(trials, dict) or not trials:
        raise ValueError("Name your comparison family BEFORE seeing TEST results")
    results = {}
    for name, arms in trials.items():
        if not isinstance(name, str) or not name or not isinstance(arms, dict):
            raise ValueError("Malformed predeclared comparisons")
        if set(arms) != {"A", "B"}:
            raise ValueError("Every contrast needs exactly two paired seed arms")
        results[name] = exact_paired_sign_flip(arms["A"], arms["B"])
    corrected = holm_adjust({name: result["p_unadjusted"]
                             for name, result in results.items()})
    for name, result in results.items():
        result["p_holm_adjusted"] = corrected[name]
    return {
        "schema": "afras-declared-seed-contrast-analysis-v1",
        "dataset": doc["dataset"],
        "statistical_unit": "independent_training_seed",
        "source_runs_independently_authenticated": False,
        "exploratory_until_frozen_source_validation": True,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--declared-paired-seeds", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = audit_manuscript(args.manuscript.read_text(encoding="utf-8"))
    if args.declared_paired_seeds is not None:
        paired = json.loads(args.declared_paired_seeds.read_text(encoding="utf-8"))
        payload["user_declared_seed_statistics"] = declared_seed_comparisons(paired)
    else:
        payload["seed_level_statistics_status"] = \
            "BLOCKED_NO_MATCHED_ORIGINAL_RUN_VECTORS"
    report = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        if args.output.exists():
            parser.error("Refusing overwrite of prior audit results")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
