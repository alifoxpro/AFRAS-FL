# AFRAS-FL V2 — Pre-Result Stage19 Independent Device-Level Statistical Analysis Lock

**Date:** 24 October 2026  
**Target journal:** MDPI *AI*  
**Registration state:** BEFORE any genuine nine-device held-out confirmatory FL predictions; the full dataset execution gate is still **BLOCKED**.  
**Frozen core source:** `stage16_v2/FROZEN_CORE_PROTOCOL_V1_2026-10-24.json`; unchanged.  
**Implementation:** `stage19_v2/independent_device_paired_analysis.py`.

## Precisely fixed primary estimand

The target test is the full unmodified native test distribution of each of the nine UCI N-BaIoT devices, not a globally reweighted mixture and not a cap of 128 samples per attack class. Each outer device is excluded from all model fitting and fitted preprocessing. Two baselines (`FedAvg`, `FedProx`) and three original random seeds (3107, 3108, 3109) create exactly **54** prescribed fits, no more and no less.

For a target device `d`, method `m` and seed `s`, the original class-support-weighted binary confusion is checked independently from every native predicted row, with 0.5 fixed classification threshold. Device–method BA is the arithmetic mean across its three seeds. Then the prespecified device paired contrast is

```text
delta_d = mean_seed(BA[d, FedProx, seed]) - mean_seed(BA[d, FedAvg, seed])
primary_delta = (1 / 9) * sum_over_nine_devices(delta_d)
```

Thus the **nine devices**, not 54 run results and not millions of attack observations, are the units of uncertainty. Also report both baseline mean device BA, worst device mean BA, native benign FPR and attack recall by device.

## Pre-result uncertainty computation

- Enumerate **all 512** possible +/- sign reversals of the nine paired device differences; a two-sided exact sign-flip randomization p-value counts `abs(delta_flipped) >= abs(primary_delta)`. This is a finite-n paired symmetry assessment, **not** automatic evidence of a causal mechanism.
- Generate **10,000 fixed-seed (3107) percentile bootstrap resamples of nine complete paired device differences**, sampling nine devices with replacement; return the 2.5th and 97.5th percentiles. No within-device rows or three seeds are independently bootstrap-sampled.
- Report all nine paired differences and both original baselines, regardless of sign, including failures and method ties. Small-nine-cluster sample size means both tests and percentile intervals need cautious interpretation.
- No post-result changes to architecture, threshold, optimizer, training sample cap, folds, seeds or chosen statistical test.

## Non-negotiable evidence gates

The script refuses to produce any result unless *all 54* task IDs match the frozen plan and each folder contains an authorized `run_receipt.json` and independent native `independent_replay.json`. It checks original full-target row totals, model/seed/device identity, code hashes, native class-support inventory hash, raw gzip prediction SHA-256, final checkpoint SHA-256, true eight-source training sample evidence and sample/normalization parity between methods at each device and seed. Incomplete results cannot be silently dropped or used to form a reduced-significance analysis.

At current Chat14 authoring time, **0/54 real held-out confirmatory fits exist**. GitHub Actions [40089900716](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40089900716) passed **8/8 synthetic tests** for exact 54-task coverage, native BA arithmetic, matched source samples, two-sided 512 sign flips and proper nine-device bootstrap. Synthetic QA is not empirical N-BaIoT test performance.

## Route A exposure and novelty boundaries

Previous Stage13 full-source-corpus recurrence (~90.74%) is NOT the same as presence among the sampled **8×30,000 truly model-visible source-training rows**. The core primary paired BA contrast is independent of either recurrence grouping. The signed-zero-normalized float64 exact vector equality may describe source–target feature repetition, but it is not necessarily identical captured traffic or a causal generalization mechanism.

The primary statistics implementation **does not yet provide** the required secondary within-attack-class, exposed-versus-not-exposed recall analysis. The original Stage13 '42 classes/cells with both strata' must not be reused as actual-training-exposure support. Implement and independently test the separate per-row exposure join before claiming the data-centric Route A analysis is complete. Report absent-class recall as `NON_ESTIMABLE`, not zero. Benign recurrence is sparse, so do not claim reliable exposed-versus-unexposed benign FPR contrasts when denominators vanish.

Algorithmic/fuzzy mathematical novelty remains **NO-GO**; the originality of the data-centric evaluation contribution is only conditional. High accuracy alone is not proof of journal novelty or privacy.

**GO/NO-GO:** Statistical-code preregistration software GO; actual target scoring and paper submission NO-GO until original bytes are rechecked at execution, qualified responsible-human approval exists, and 54 original runs are completed and independently replayed.
