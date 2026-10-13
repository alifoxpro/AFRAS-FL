#!/usr/bin/env python3
"""Source-only LaTeX/legacy-code evidence audit; DOES NOT reproduce metrics."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def table_by_label(tex, name):
    """Find a LaTeX table by its label (not by arbitrary nearby mentions)."""
    for m in re.finditer(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", tex, re.S):
        if "\\label{" + name + "}" in m.group():
            return m.group(), tex.count("\n", 0, m.start()) + 1
    return None


def numbers_for_row(table, pattern):
    if not table:
        return None
    for row in re.split(r"\\\\", table[0]):
        if not re.search(pattern, row):
            continue
        values = []
        for col in row.split("&")[1:]:
            match = re.search(r"\$(.*?)\$", col, re.S)
            if not match:
                continue
            math = re.sub(r"\\(?:mathbf|mathrm|textbf)\{([^{}]*)\}",
                          r"\1", match.group(1))
            number = re.search(r"(?<![\w.])-?\d+\.\d+", math)
            if number:
                values.append(float(number.group()))
        if values:
            return values
    return None


def audit(tex, strategy_b=None):
    found = []
    def flag(identifier, priority, detail, action):
        found.append({"id": identifier, "priority": priority,
                      "finding": detail, "next_action": action})
    phase = table_by_label(tex, "tab:phase_msr")
    lam = table_by_label(tex, "tab:lambda_ablation")
    sweep = table_by_label(tex, "tab:lambda_mu_sweep")
    first = numbers_for_row(phase, r"B4\s*\(Fuzzy\)")
    second = numbers_for_row(lam, r"0\.25")
    third = numbers_for_row(sweep, r"\\lambda\s*=\s*0\.25\s*,\s*\\mu\s*=\s*0\.10")
    low = numbers_for_row(sweep, r"\\lambda\s*=\s*0\.25\s*,\s*\\mu\s*=\s*0\.05")
    high = numbers_for_row(sweep, r"\\lambda\s*=\s*0\.25\s*,\s*\\mu\s*=\s*0\.20")
    if first and second and (first[0], first[2]) != (second[0], second[2]):
        flag("CANONICAL_TABLE_CONFLICT", "critical",
             {"phase_table_MSR_FPR": [first[0], first[2]],
              "lambda_ablation_MSR_FPR": [second[0], second[2]]},
             "Reconcile from raw run ID, checkpoint, split, seed and evaluation protocol.")
    if third and second and (third[0], third[2]) != (second[0], second[2]):
        flag("LAMBDA_SWEEP_CONFLICT", "critical",
             {"sweep_MSR_FPR": [third[0], third[2]],
              "lambda_ablation_MSR_FPR": [second[0], second[2]]},
             "Publish provenance; if differently scoped, relabel rather than claiming identical conditions.")
    if low and high and low[:4] == high[:4]:
        flag("IDENTICAL_MU_ROWS", "warning",
             {"lambda025_mu005": low[:4], "lambda025_mu020": high[:4]},
             "Check raw independent run logs; equal values alone do not establish misconduct.")
    if "Code, splits, and result artefacts are released" in tex:
        flag("RELEASE_ARTIFACT_GAP", "critical",
             "Claimed released splits and result artefacts require verification.",
             "Provide immutable public URLs, split files/hashes and per-seed result evidence.")
    if re.search(r"\\mathbb\{E\}\\s*\\bigl\[\\gamma_\{\\text\{RL\}\}", tex):
        flag("PBRS_EXPECTATION", "critical",
             "Expected potential difference is not generally zero under exogenous contexts.",
             "For stationary contexts it equals (gamma-1)*E[Phi], not zero in general.")
    if "High or Medium (i.e." in tex and "otherwise" in tex:
        flag("BINARY_LABEL_LINEAGE", "critical",
             "Treating High/Medium as attacks and Low as benign needs auditable raw labels.",
             "Publish original label -> severity mapping and verify on both datasets.")
    if "designed" in tex and "after observing the strict-test FPR" in tex:
        flag("L9_POST_HOC_TEST_TUNING", "critical",
             "L9 modification was designed after strict TEST inspection.",
             "Treat L9 as exploratory; confirm on independent new untouched TEST.")
    if "strictly leakage-free" in tex or "Leakage-free record-level" in tex:
        flag("STRICT_SPLIT_EVIDENCE", "critical",
             "Archive alone lacks proof of complete upstream data provenance and split integrity.",
             "Audit raw harmonization, grouping, feature selection, TRAIN-only fitted transforms.")
    if "p = 0.933" in tex and "p = 0.971" in tex:
        flag("RUN_LEVEL_NON_SIGNIFICANCE", "info",
             "B3-vs-B4 run-level p-values 0.933 and 0.971 cannot establish superiority.",
             "Retain non-significance caveat and publish five-seed raw vectors.")
    if strategy_b and re.search(r"def\s+_get_neighbor_actions\(self\)\s*:\s*return\s+None", strategy_b):
        flag("R_LINK_INACTIVE", "critical",
             "Legacy StrategyB _get_neighbor_actions always returns None.",
             "Implement validated neighbor coordination and rerun mu sweeps; do not infer causal mu effects.")
    return {
        "schema": "mdpi-afras-source-audit-v1",
        "manuscript_sha256": hashlib.sha256(tex.encode()).hexdigest(),
        "tables": {k: (table_by_label(tex, k) is not None) for k in
                   ("tab:phase_msr", "tab:lambda_ablation",
                    "tab:lambda_mu_sweep", "tab:rls_test", "tab:multiseed")},
        "extracted": {"phase_B4": first, "lambda_025": second,
                      "sweep_025_010": third,
                      "sweep_025_005": low, "sweep_025_020": high},
        "findings": found,
        "warning": "Static source audit only. Raw results, strict TEST and labels remain unverified.",
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("main_tex", type=Path)
    cli.add_argument("--legacy-strategy-b", type=Path)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    tex = args.main_tex.read_text(encoding="utf-8")
    code = args.legacy_strategy_b.read_text(encoding="utf-8") if args.legacy_strategy_b else None
    output = json.dumps(audit(tex, code), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
