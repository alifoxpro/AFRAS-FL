# AFRAS-FL V2 — Stage 16 Pre-Result Clarification of Exposure Estimands

**Date:** 24 October 2026  
**Status:** Prospective analysis clarification, recorded **before any outer held-out model predictions**  
**Frozen core:** `FROZEN_CORE_PROTOCOL_V1_2026-10-24.json` **unchanged**  
**Confirmatory execution:** STILL BLOCKED until reviewed code, dataset receipt and responsible-researcher authorization.

## Why this clarification is mandatory

Stage 13 measured feature-vector recurrence against the **entire available corpus** of the eight other devices. This is **not equivalent to exposure of a fitted model** when only 30,000 rows per source device are actually sampled for training. An observation can match a row present somewhere in an original source archive without that row ever being used by FedAvg or FedProx.

The claim "90.74% of test rows were seen in model training" is **prohibited**.

## Two separate variables, both defined before target prediction inspection

**Variable A — Full-source availability recurrence:** For a held-out observation, whether its canonical 115-feature raw float64 vector exactly matches any row in the full original corpus of the eight non-heldout devices. This is the *existing Stage 13 measurement*, independent of training subsampling. It characterizes **potential source availability**, not learned model exposure.

**Variable B — Actual sampled-training exposure:** For each fold and random seed, whether the exact same canonical 115-feature raw float64 vector occurs among **the 30,000 source rows that were actually selected for training on each of the eight source clients** (240,000 total source rows). This is the appropriate indicator for model-visible exact feature matching. The matched FedAvg and FedProx arms share identical samples and source-only normalization at the same fold and seed.

Equality uses normalized signed zeros and BLAKE2b-128 of little-endian IEEE754 float64 feature bytes, with byte-level collision risk disclosed. No claim of identical captured packets/events follows from this equality. Actual sampled rows retain their native feature vectors for fingerprinting *before* model input float32 conversion, making an exact source digest comparable to target-row digests.

**Variable B may be a proper subset of Variable A.** The amount and supported class strata must be established from the executed deterministic source samples, not inferred from the 90.74% full-corpus overlap.

## Analysis-only integrity receipt

During source-only sample selection, save a **digest-only** immutable local sidecar of the exact selected source training vectors per fold/seed/run, keyed by source device. Bind its SHA-256 and expected 240,000 rows into the run receipt. The independent prediction replay must check this file, its source identities, row counts and SHA-256; a run missing the evidence cannot count as confirmed. Never upload this potentially sensitive source-membership bank to public CI or release it publicly without a separate data-governance assessment.

The full-target raw output must continue to contain the unchanged original held-out sample prevalence, source-path label and post-training raw float64 feature digest for **every original target row**. Neither A nor B is available to model tuning, threshold selection, normalization or early stopping.

## Statistical estimands and support

**Unchanged primary endpoint:** Native held-out binary balanced accuracy, averaged equally over the nine devices. The prespecified primary comparison remains FedProx minus FedAvg, paired by fold and seed with inference at the device level.

**Secondary diagnostics:** (i) attack recall for exact-source-available versus not available, and (ii) attack recall for actually training-exposed versus not exposed, only within held-out device and specific attack class when both comparison groups have nonzero support. No absent class, zero-sized exposure stratum or recurrent-benign FPR receives an imputed score.

The earlier **42** eligible attack device/class cells apply only to *full-source availability recurrence* and **must not be copied** to the actual-training-exposure analysis: actual exposed/unexposed cell support must be measured from selected source-sample fingerprints per seed.

Exposure differences are observational associations, not the causal effect of deduplication, leakage, identical captured events or previously unseen attack families. Seed replicates are not independent devices; model comparisons use nine device-level paired units.

## Locking / change control

This clarification changes **no training algorithm**, fixed optimizer, sampling cap, class weights, round count, device folds, seed choices, decision threshold or primary inference. It corrects the meaning of a key secondary exposure variable and preserves both the original Stage 13 full-corpus census and the per-experiment actual-sample bank.

Further exposure-dependent analytic choices after seeing final target predictions must be marked explicitly exploratory. Human review of the full code revision and exact output schema is required before the 54-run authorization receipt is created.
