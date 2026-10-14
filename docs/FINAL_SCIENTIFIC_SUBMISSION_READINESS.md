# Final Scientific Readiness Audit — AFRAS-FL

**Audit date:** 2026-10-14.  
**Source branch:** \`fix/mdpi-scientific-audit-v1\`.  
**Proposed venue:** MDPI *AI* (target is provisional until authors confirm).  
**Manuscript:** \`paper/main.tex\`, kept **unchanged**.  
**Overall status:** **NOT READY FOR SUBMISSION**. The new strict protocol has
unit-tested integrity checks, **not** validated benchmark performance.

This is a scientific reproducibility and editorial checklist, not a
claim of confirmed experimental reproducibility or misconduct. Review
\`docs/FL_RL_FUZZY_SCIENTIFIC_AUDIT.md\` and
\`docs/METRICS_STATISTICAL_AND_MANUSCRIPT_AUDIT.md\` for detailed evidence.

## Machine-readable gate report

Run from the repository root:

    python scripts/analysis/audit_submission_readiness.py --target-journal mdpi-ai --seed 42 --output /tmp/afras_submission_readiness.json

\`--require-ready\` exits with status 2 if any blocker or manual-review
gate remains; **do not** use it as a normal passing CI check while original
evidence is absent. Without this option the audit is successful if the
check itself completes, even if the paper is NOT ready.

GitHub Actions generates two independent reports:
- **final-scientific-readiness-checklist**: machine-readable blocker and
  review-gate report, including SHA-256 of the manuscript source;
- **mdpi-source-statistical-audit**: line-addressable manuscript statistics
  risk flags.

Download these artifacts from the GitHub Actions workflow-run page.
The source-only script **never opens a TEST CSV, source CSV, original
archive, model checkpoint, or TRAIN/VAL CSV**. Merely finding a directory
cannot establish that its contents are authentic. It does not contact
the publisher, submit to a journal, or train a model.

The status \`IMPLEMENTED_STATIC_ONLY\` means **a file/class/CI definition
exists**, not that a real scientific result has been verified. The possible
gate statuses are \`IMPLEMENTED_STATIC_ONLY\`, \`BLOCKED\` and
\`INDEPENDENT_REVIEW_REQUIRED\`.

## Gate-by-gate review

| Gate | Current scientific interpretation | Evidence required before claiming readiness |
|---|---|---|
| Python training and leakage guard code | Exists and has synthetic unit tests | Reproducible end-to-end integration with official data, exact commit CI logs |
| Publisher datasets | **BLOCKED**: official source bytes not provided in the repository | CICIoT2023 and CIC IoT-DIAD 2024 source archives, release/version, checksums and modality |
| Original label lineage | **BLOCKED**: High/Medium/Low severity mapping remains author-declared | Every original category, Attack/Benign policy, reviewed category-to-severity rules |
| Five-network-link topology | **BLOCKED**: labels "Core/Aggregation/Edge" alone prove no physical link | Measured source identities, session/device/group exclusivity, link assignment provenance |
| Leakage-free preprocessing | **BLOCKED** pending real source files | Independently audited candidate features (>14), chronological/group splits, TRAIN-only selector/scaler and windows after split |
| Stage 3 Mamba teachers | **BLOCKED** | 5 complete per-dataset same-seed teacher checkpoints with provenance and SHA-256 hashes |
| Stage 4 federated protocol | **BLOCKED** | Independently reproduced FedAvg/FedProx/fuzzy runs, immutable TRAIN-rules, VAL-only selection and real run logs |
| Sealed TEST | **BLOCKED** | One-time frozen checkpoint evaluation after statistical plan is finalized; archived receipt and confusion counts |
| True binary IDS FPR/FNR | **BLOCKED** | TP/FP/TN/FN for each link from independently verified Attack/Benign labels; pooled rates from totals |
| Independent statistical inference | **BLOCKED** | Same-seed matched per-run outcome vectors, adequate seed design, cluster independence, multiple comparison correction |
| Historical vs strict v2 methodology | **BLOCKED for substituting results** | Explicitly distinct Methods/results; historical seven-phase rules are not reproduced by strict v2 nine-cell fuzzy |
| Neighbor coordination / deployment | **BLOCKED** | Real measured link actions and latency OR qualify the strict v2 as contextual bandit with \`mu_link=0\`, \`gamma=0\` |
| MDPI template/format | **BLOCKED if target is MDPI AI** | Approved MDPI *AI* manuscript template, required disclosures, figures, references and journal-specific submission instructions |
| Tracked changes | **Needs review** | Decide whether red \`\\rev\` / strike-through \`\\strk\` may appear in reviewer version or require clean source |
| Authors' final approval | **Needs independent review** | Corresponding author/coauthor review, ethics/license/reproducibility statement and submission package signoff |

## Confirmed manuscript-specific inconsistencies

1. The source uses \`\\documentclass[journal]{IEEEtran}\` and states
   *IEEE Internet of Things Journal*, not an MDPI *AI* template.
2. The abstract reports historical very small \`p\`-values and large
   improvements; the original run-level paired vectors are not provided.
   The 50 evaluation episodes in the Welch test tables are **not**
   demonstrated as 50 independent training runs.
3. Table \`tab:multiseed\` includes CICIoT2023 rows with **3 seeds**,
   DIAD2024 with **2 seeds**. Its caption mentions 3 seeds for both
   datasets but its explanatory prose acknowledges a missing DIAD seed.
   Preserve what is observed; do not fill a missing run with estimates.
4. The paper still contains visibly marked revisions (\`\\rev{}\`,
   \`\\strk{}\`). They may be appropriate for a response-to-reviewers
   version but require journal formatting review.
5. FPR/FNR, fairness, latency and physical five-link coordination in the
   historical manuscript have not been reconciled to independent raw
   source data, confusion counts and instrumented measurements.

The existing static statistics audit reported **19 line-level flags**
(including **10 critical line-level flags**); these are NOT 19 distinct
confirmed mistakes, nor proof of falsification. Numbers remain
historical/unverified, not contradicted by fabricated recalculations.

## Minimal ordered path to a defensible submission

1. **Dataset authorization:** retrieve true publisher ZIPs from UNB/CIC
   or contact \`cic@unb.ca\`. Never bypass registration or quietly
   substitute mirror data. Keep source archives out of public GitHub.
2. **Schema/labels/topology:** audit raw features, original classes,
   capture timestamps/groups and independent physical link evidence.
   Do not treat synthetic shards as real SDN links.
3. **Freeze protocol:** choose either historical reconstruction (only if
   original code and provenance can be recovered) or explicitly new
   strict Stage 4 v2. Predeclare true scientific comparisons and
   acceptable reported metrics. Never conflate methodologies.
4. **REAL reproducible training:** run the stage3/stage4 seed-matched
   pipeline on genuine separate TRAIN/VAL, with checkpoint SHA-256 and
   independent device/time leakage audits.
5. **Predeclare statistics and TEST:** collect adequate **independent
   training seeds**, freeze all tuning and contrasts, then open TEST
   once; preserve receipts, run-level vectors and confusion matrices.
6. **Reconcile claims:** retain only numerical conclusions that
   are justified by verified full-run artifacts. If effects differ,
   transparently update methodology, results and limitations with
   corresponding author consent.
7. **Submission formatting:** adapt an author-approved copy to the
   journal's current template and required statements, perform
   reference/figure checks and coauthor signoff.

## Unchanged assets / important caveats

The audit branch is \`fix/mdpi-scientific-audit-v1\`; **do not merge to
\`main\` without author review**. The paper's original text/tables
are intentionally preserved. Passing unit tests validates source
properties with *synthetic* fixtures only; it does NOT prove real
training correctness, reproducibility, measured fairness, deployed
latency, statistical significance or journal acceptance.
