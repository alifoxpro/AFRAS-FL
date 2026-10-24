# AFRAS-FL V2 — Pre-Result Stage19 Actual-Training-Exposure Analysis Specification

**24 October 2026 — before original full target-model predictions.**  
**Core training protocol:** `stage16_v2/FROZEN_CORE_PROTOCOL_V1_2026-10-24.json`, unchanged.  
**Software:** `stage19_v2/training_exposure_strata.py` with accompanying synthetic-only tests.  
**Target scoring:** still explicitly **BLOCKED** (0/54 genuine heldout runs).

## Exact estimand

For each heldout `device × method × seed` (9 × 2 × 3), identify whether a target row's **canonical signed-zero-normalized 115-feature IEEE754 float64 BLAKE2b-128** fingerprint is present in the corresponding **actual 240,000 model-visible training examples** (8 × 30,000) selected on the eight non-heldout source devices. Fingerprinting follows original float64 values before the float32 model input transformation. This is a feature-vector equality indicator, **not** equality of original captured packets and not proof of attack-data leakage.

This is **not interchangeable** with Stage13's `full-source-availability` recurrence against all ~6.7 million original non-heldout rows. No direct full-source/actual-training join or source availability difference estimates are claimed by this specific secondary script.

## Prespecified descriptive outputs

Retain **every target row in its original native class and prevalence**, use fixed attack threshold `0.5` without tuning and compute two separate support strata per heldout device and each original attack subtype:

- `actually_trained_exposed_rows`: target attack instances with fingerprint membership in the seed-specific model training sample bank.
- `not_training_exposed_rows`: target instances with no exact fingerprint match in that sample bank.
- `attack_recall_exposed` and `attack_recall_not_exposed` only when denominators exist, with a descriptive difference only when **both** strata are nonempty.
- For original benign class, report **false positive rate**, not attack recall, within each supported exposure stratum.
- For a native zero-support class/stratum, emit `NON_ESTIMABLE`, never impute a zero rate or treat missing classes as model failures.

Eligibility is measured from the *actual source training samples for that fold and seed*. The former Stage13 “42 eligible attack device/class cells” concerns **full-source availability** and must not be copied or promised to hold for actual-training exposure.

## Mandatory anti-cherry-picking / integrity checks

The script refuses any result unless **all 54** predefined `run_receipt.json` and `independent_replay.json` outputs exist, their original raw target prediction SHA-256 and checkpoints pass the independent primary Stage19 result verifier, and the exact sampled-source fingerprint bank has full eight-client support. It verifies that FedAvg and FedProx for the same heldout device and seed have identical sampled-source row hashes, source normalization hashes and exposure support.

The user / responsible researcher must keep the source fingerprint sidecar private: hashed source membership can disclose dataset information, and FL simulation on centrally hosted source files does **not** itself guarantee privacy.

## Interpretation and inference

The exact exposed-vs-unexposed subgroup analyses are **descriptive and associational**, not randomized. N-BaIoT cross-device exact numerical recurrence is historically concentrated in attack-labelled records and attack-family composition can confound observed differences. Comparisons are stratified by attack subtype and heldout device to avoid interpreting category-mix differences as memorization. The prespecified **primary** inference remains the independent nine-device paired FedProx-minus-FedAvg mean native balanced accuracy with fixed 3 seeds per device, all 512 sign-flips and nine-device paired bootstrap; this exposure code does **not** replace it.

No empirical exposure effect, strong generalization, originality, or MDPI *AI* acceptance is claimed from the software without 54 actual native test outputs.

## Software acceptance evidence

GitHub Actions [40090465223](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40090465223) passed **13/13 synthetic-only Stage19 tests** (eight previous primary analysis tests and five new exposure-stratum tests). They exercise source bank 8-client row-count checks, missing/corrupt membership, original full-target class row support, correct benign-FPR-vs-attack-recall semantics, non-estimability and refusal of partially available 54-run data.

**Status:** Stage19 primary + partial secondary **code QA PASS**, Stage19 full true data analysis **NOT COMPLETE**, Stage18 heldout **0/54**, Stage20 submission **NO-GO**.
