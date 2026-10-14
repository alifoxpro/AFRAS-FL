# Stage 4 v2 — Scientific audit of Federated Learning, RL, and Fuzzy decisions

Audit date: 2026-10-14. Branch: fix/mdpi-scientific-audit-v1.
**Status: source corrections and synthetic tests only.** No official
CICIoT2023/DIAD2024 source CSVs, retrained Mamba checkpoints, five-client
GPU/CPU training run, deployment traces or sealed real-dataset TEST scores
are present. NEVER cite these tests as reproduction of the manuscript.

## Finding P0: Fuzzy train/inference feature-scale mismatch

In the prior strict Stage 4, train_rules() reused the historical
AFRASFLPipeline, whose phase1_denoise() applied a SECOND StandardScaler and
wavelet denoising to the rule-fitting TRAIN coordinates. But rule_arrays()
passed the ORIGINAL stage3-standardized x[:, :2] to FuzzyInferenceEngine.
The Gaussian membership parameters did not live on the inference scale.
Consequently a rule's firing strength/action could be miscalibrated.

Correction: scripts/training/strict_fuzzy_core.py replaces the historical
pipeline **only in the NEW strict Stage 4** with a deterministic 3x3
Gaussian cell model using 2 preselected Stage3 TRAIN-standardized window
means. Training quantiles, Gaussian centers, widths, class-majority rules,
confidence and support all come solely from TRAIN. No secondary scaler,
sequence-wide denoising, VAL/TEST labels or oversampling is used. Inference
uses exactly the same two input coordinates and immutable TRAIN parameters.
Unsupported/constant features, invalid labels and insufficient rule support
fail closed; no fabricated rule fallback.

**Interpretation:** this is NOT the paper's seven-phase EKF/wavelet /
NURBS-SMOTE / grid-and-boundary rule organization. Therefore its eventual
experimental result is a new method and cannot replace prior reported
AFRAS-FL scores unless the Methods and claims are appropriately revised
AFTER authentic data experiments.

## Finding P1: Federated sample weights and tensor schema

Before correction, aggregate_state_dict() accepted arbitrary sizes and
tensor schema without explicit validation. Zero/negative sample counts,
NaN/Inf tensors or mismatched parameter names could invalidate FedAvg.

Correction: strict_fed_core.normalized_client_weights() requires positive
integer client TRAIN counts and unit-sum finite weights. Stage4 now
validates identical parameter names, shapes, dtypes, device and finiteness
across local CPU tensors; performs weighted float64 accumulation and casts
back to the model parameter dtype. FedProx's pre-existing explicit
mu/2 * squared distance from the frozen global parameters is maintained.

Limits: five links are simulated on one machine. No secure aggregation,
differential privacy, physical five-node topology or client/network
communication is established. Session/device-level independence remains
unverified until raw data/group identifiers are inspected.

## Finding P1: RL and reward semantics

Stage4's action-selection problem remains an action-exogenous contextual
bandit with gamma=0, using full TRAIN-derived reward tables. Calling this
a long-horizon causal SDN MDP or deployed DQN controller is inaccurate.

Re-check of mosar_reward(): for a fixed state/severity, the teacher
probability of the true severity and maximum teacher confidence enter the
reward as **action-invariant constants**. Subtracting two action rewards
cancels these contributions exactly. They should NOT be represented as
independent incentives for action choice. Action-dependent factors are
correctness/detection, assumed action latency cost, severity-weighted
impact and (in B4 only) the TRAIN-only fuzzy rule bonus. R_link is NOT
implemented: mu_link MUST equal zero.

The already implemented conventional binary IDS FPR/FNR requires an
independently reviewed raw Attack/Benign mapping. High/Medium/Low
action success and 'false block on Low' are not equivalent to
binary IDS FPR/FNR without that evidence.

## Reproducibility barriers and immutable output

- Stage4 RUN_PROVENANCE now has protocol strict-fed-contextual-bandit-v2.
- The sealed TEST validator refuses incompatible v1/legacy run metadata.
- Every TRAIN-only per-link fuzzy-rule JSON is checksum-registered and
  rechecked before unsealing TEST; the two feature names and scale
  are pinned to the Stage3 state semantics.
- Stage3 teacher/scaler SHA-256 and its seed remain independently pinned.
- VAL selects best rounds; TEST must not guide hyperparameter selection.
- All raw data authenticity, original severity policy and real physical
  SDN five-link assignment are still UNVERIFIED.

## Tests and interpretation

tests/test_strict_fl_fuzzy_science.py checks deterministic training-only
rule construction, matched fuzzy scale, expected actions, refusal of
NaN/Inf/fractional class labels, invalid sample weights and
action-invariant teacher reward offsets.
tests/test_strict_test_guard.py checks versioned stage4 metadata and
refuses tampered fuzzy-rule JSON or mismatched inference scales.

CI only runs lightweight synthetic source/property tests; it does NOT
install the full training dependencies, run PyTorch forward/backward
steps or verify performance on the original benchmark. Real end-to-end
execution and reproducibility remain blocked pending publisher data.

The scientific paper at paper/main.tex and branch main are unchanged.
