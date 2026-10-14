# Evaluation metrics, statistical independence, and manuscript evidence audit

Date: 2026-10-14. Scope: **source analysis and synthetic tests only**.
The IEEE manuscript file `paper/main.tex` remains unmodified; historical
benchmark CSVs, TEST checkpoints and run-level statistical vectors are absent.

## Observed manuscript evidence gaps (not conclusions of misconduct)

- **Episode pseudoreplication risk**: manuscript table captions at approximately
  lines **623** and **1083** describe two-sided Welch tests using **n=50
  evaluation episodes**. These are not demonstrated to be 50 independent
  retrainings: overlapping source windows, shared checkpoints and common
  client traffic can induce correlation. Therefore raw episode p-values
  cannot by themselves establish independent training-run significance.
- **Independent seed counts**: L7/Table `tab:multiseed` reports CICIoT2023
  with 3 seed-level means and DIAD2024 with **2**. The caption mentions
  3 seeds (42, 123, 2026), but the DIAD rows explicitly list n=2. The
  manuscript discussion admits this limitation. Even larger seed counts
  alone do not establish independent TEST datasets or population-level
  generalization.
- **Historical statistical effects**: manuscript abstract and
  `tab:strategy_ab_stats` report very small p-values and Cohen's d, but
  the public repository does not contain independently verified raw seed
  vectors, evaluation-episode identifiers or original artifact hashes that
  would permit reanalysis. Do not transfer these p-values to Stage 4 v2.
- **Metric interpretation**: historical MSR and source FPR/FNR are not
  interchangeable with the NEW strict protocol's action-success rate and
  conventional binary IDS counts. Review the original Attack/Benign mapping.
  Rate denominators and averaging weights must be declared.
- **Runtime/fairness**: Jain's fairness from client action-success is not a
  guarantee of fair detection across benign/attack classes or devices.
  Reported latency and computational overhead require actual timing logs.
  The strict code's latency term is a cost **proxy**, not milliseconds.

The repo's static audit now emits line-addressable JSON findings from
`paper/main.tex`. As checked in GitHub Actions, it detected **10 critical
line-level findings among 19 total line-level findings**, NOT 10 distinct
proven methodological violations. An automated match is a review flag, not
proof that the reported scientific conclusion is wrong.

## Corrections in the NEW strict evaluation protocol

`scripts/training/strict_fed_core.py`:

- Action-success = fraction of windows with the appropriate severity-specific
  action (High→BLOCK, Medium→RATE_LIMIT, Low→ALLOW); not automatically
  binary IDS accuracy or the paper's historical MSR.
- Provides an explicit severity × action 3×3 confusion matrix and per-severity
  support, precision, recall and F1. Also reports macro F1 and balanced
  accuracy averaged over **classes actually present**. Absent-class recall is
  `null`, not fabricated zero.
- For binary intrusion classification, requires independently declared raw
  Attack/Benign evidence, with ALLOW→benign and RATE_LIMIT/BLOCK→attack.
  Reports TP, TN, FP, FN, FPR=FP/(FP+TN), FNR=FN/(FN+TP), precision, recall,
  F1 and accuracy. Undefined denominators produce `null`.
- The pooled binary confusion counts are **summed across all five clients**,
  then rates derived from summed denominators (micro pooling), **not** a
  mean of per-client rates. Mixed availability of original binary labels
  across clients stops TEST evaluation, rather than reporting incomplete FPR.
- Jain's fairness is computed on five per-client action-success rates;
  fairness of security outcomes across traffic classes is not implied.

`scripts/evaluation/evaluate_strict_test.py` now uses this fail-closed pooled
metric function. The original, unreleased real-dataset TEST remains sealed;
no TEST performance figures have been produced by these code changes.

## Statistical test policy and how to use it

`scripts/analysis/audit_metrics_statistics.py` performs two independent tasks.

**Static audit (safe now, NO TEST access):**

    python scripts/analysis/audit_metrics_statistics.py --manuscript paper/main.tex --output /tmp/afras_source_statistics_audit.json

The report explicitly records `BLOCKED_NO_MATCHED_ORIGINAL_RUN_VECTORS`
for inferential statistics. It never invents a p-value.

**Conditional analysis of supplied future run-level summaries:**

When authentic and version-matched per-seed results exist, construct an
`afras-declared-paired-seed-values-v1` document with: dataset, metric
`pooled_action_success`, protocol `strict-sealed-test-eval-v1`,
statistical_unit `independent_training_seed`, and a
`predeclared_comparisons` dictionary whose each comparison has exactly
`A` and `B` maps from **identical seed IDs** to [0,1] run metrics.
Run with `--declared-paired-seeds`. **This input is user-declared and the
tool does NOT independently authenticate the source checkpoints/logs**:
results remain exploratory until the run provenance and the hypotheses are
independently reviewed.

The tool computes:
- a **two-sided exact paired sign-flip** permutation p-value for 5–16
  fully paired independent training seeds, provided signs are exchangeable
  under the null;
- paired mean difference and `d_z` when the SD of paired differences
  is nonzero; 
- **Holm-adjusted** p-values for every contrast in the declared family.

For 5 paired seeds, the smallest possible two-sided exact p-value is
`2/2^5 = 0.0625`. Thus five perfectly concordant differences cannot
reach unadjusted p<0.05 in that exact test. Six matched seeds are the
minimum that can do so in this special all-same-direction configuration;
more may be required for power or multiplicity correction.

**Key caveat:** multiple seeds applied to the SAME held-out TEST are repeated
model fits on one fixed evaluation set. Training-seed permutation assesses
training randomness conditional on that test set, **not** independence of
patient/flow/device captures or expected performance across new networks.

Never optimize hyperparameters, choose phases after reading TEST, or reopen
a "one-time frozen" TEST to decide comparisons. Seed-number adequacy,
source independence and the power of any inference require specialist review.
A single canonical seed is not an inferential replicate; episodes/windows
cannot be substituted for independent training seeds.

## Evidence still missing before scientific publication

- Original independently sourced dataset archives, checksums and reviewed
  raw label-to-binary/severity mapping for BOTH datasets.
- Original preprocessing and SDN five-link provenance; genuine group/device
  independence and capture chronology.
- Frozen per-seed model and evaluation artifacts, consistent metric definitions,
  sample counts, class support and per-client confusion counts.
- Predeclared hypotheses, same-seed matched runs, statistical independence
  rationale, multiplicity adjustment and confidence interval/power plan.
- Hardware timing logs if latency and computational overhead are claimed.

**This audit does not rewrite any existing manuscript table or claim that
the historical paper numbers are reproduced.**
