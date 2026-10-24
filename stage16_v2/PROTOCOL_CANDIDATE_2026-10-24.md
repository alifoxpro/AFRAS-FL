# AFRAS-FL V2 — Stage-16 Pre-result Experimental Protocol

**Version:** 2026-10-24-chat7.1  
**Status:** **CANDIDATE (NOT FROZEN)**  
**Target:** MDPI *AI*, original empirical evaluation methodology.  
**Historical design limitation:** All N-BaIoT class supports and recurrence labels were audited before this protocol. In prior feasibility work, Samsung was used for *source-side validation* to choose a learnable optimizer/budget; seven others were exploratory training sources. Ennio was never evaluated as a target. **Do not claim that all nine devices were historically untouched independent outer test lockboxes.** Prospective lock applies only to future target prediction outcomes after code/protocol freeze.

## Scope and primary estimand

Binary benign-versus-attack classification with 115 raw native numeric N-BaIoT features, source-path label map and exactly nine held-out device folds. In each fold, one complete device is excluded from all fitting, preprocessing, threshold setting and model selection. The other eight devices are source federated clients. The held-out test comprises **every original row at its original natural class prevalence** with no test-side deduplication, balancing, pruning, threshold tuning or filtering.

**Primary endpoint:** equally weighted mean over nine devices of binary balanced accuracy, BA=(TPR+TNR)/2, where TPR is attack recall and TNR is benign specificity. The prespecified paired method contrast is FedProx minus FedAvg in per-device BA, after averaging repeated seeds **within each device**.

## Model candidate — common-budget trial

- One MLP architecture: 115 inputs, hidden layers 64 and 32 ReLU, one binary logit; fixed decision threshold 0.5.
- Preprocessing: `asinh(x)`, then training-source-only featurewise means/SDs; no held-out data permitted in fitted moments. Zero-variance dimensions use safe scale=1. Reject nonfinite samples rather than silently dropping target rows; document source validation policy before execution.
- **Methods:** source-only sample-count-weighted FedAvg, and FedProx with coefficient 0.01. Identical source samples, initial network, local optimizer and compute budget for both methods.
- **Provisional** AdamW lr=0.001 (weight decay 0), five communication rounds, three local epochs each, local batch size 128, training-client-specific inverse-prevalence weighted BCE; no test-driven early stopping.
- **Provisional** native-prevalence-preserving uniform training-side cap of **30,000 rows/device** (not per-class quota). This is a resource-control proposal and must be profiled and finalized on source-only data before outer prediction release. Original held-out tests are **not** sampled. Training-side class counts and sampling seeds must be retained.
- Preset seeds 3107, 3108, 3109; 9 folds × 2 methods × 3 seeds = 54 **planned** core FL fits, not actual runs.
- Non-FL references: source-only local-model baseline and a **non-private** exact-feature-source-lookup diagnostic. They must be identified separately from equal-architecture FL comparisons, with data access and cost differences described.

## Class-conditional exposure diagnostic

Define recurrent if a target row has the same canonical 115-dimensional numerical vector in *any other source device*; otherwise feature-unseen. This is not equivalent to unseen attack-family or to a shared captured network event. Exposure labels are computed by a documented hash/equality procedure solely for **post hoc diagnostic stratification** after final predictions, never for training-side selection. Original Stage13 evidence already discloses exposure supports; methodological analysis is conditional on that fact.

The checked native 99 device/class cells include 10 unsupported attack cells, 38 supported attack cells containing recurrent rows only, and **42 supported attack cells containing both recurrent and unseen rows**. Only those 42 cells are eligible for within-class attack recall contrast; do not compute '0%' for undefined subgroups. Total recurrent benign rows = 6, making a recurrent-benign FPR estimate too unstable to interpret.

Always report total class supports and per-device results. The recurrent and feature-unseen populations have drastically different benign/attack prevalence, so overall accuracy gaps do not identify an overlap effect. Treat all subgroup effects as associations, not identified causal effects.

## Secondary, statistics and negative results

Secondary: per-device native benign FPR, attack recall, worst-device BA, supported class-specific recall and exposure recall gaps, operation counts and communication bytes. Inference clusters at nine **devices**; 54 method/seed fits and 7,062,606 rows are not independent test units. Paired per-device effects, uncertainty intervals and raw device outcomes take priority over significance claims. An exact 2^9 sign-flip analysis may be considered only if exchangeability assumptions are argued. Secondary subgroup findings are exploratory and multiple comparisons disclosed.

Report every finished fold, seed and negative result. No selective stopping based on observed target accuracy. Save per-sample raw target probabilities and labels, device/class identifiers, model hyperparameters, source membership, sampling indices, training class supports, code SHA, checkpoints and reproducible environment for independent metric replay.

## Freeze gate — hard stop before test inference

- Official-source raw member byte provenance 25/25 is now supported, but the nine erroneous benign CSV `csv_sha256` SQLite fields need either an **applied repair** or a transparently versioned supersession receipt. Source-provided labels remain unadjudicated event-level truth.
- Stage-15 is a **conditional design GO**, not proven novelty; the strongest preceding FL/LODO and duplicate-aware methods must be cited accurately.
- Profile and then lock the source-sampling budget and fixed hyperparameters **once**, with complete training-only validation/preflight checks and a commit SHA; do not tune to any held-out-device metrics.
- Explicitly acknowledge Samsung's prior source-validation use in scientific transparency and avoid the false claim of a fully untouched historical nine-device test.
- Test machinery must reject any target device in source preprocessing or fitting; guard against missing native class denominators and persist raw predictions for all original target rows.

**Decision:** analysis/schema and eligibility counts READY; final experimental hyperparameter budget and Stage-16 frozen protocol NOT YET READY. No Stage-18 confirmatory target results have been produced.