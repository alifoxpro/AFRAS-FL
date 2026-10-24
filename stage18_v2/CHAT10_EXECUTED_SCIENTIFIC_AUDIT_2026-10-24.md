# AFRAS-FL V2 — Chat 10 Final Scientific Execution Audit

**Date:** 24 October 2026  
**Target:** MDPI *AI*; Route A, data-centric exact-feature exposure-aware FL evaluation  
**Branch:** `research/afras-v2-stage17-source-only-pilot-20261024` — Draft PR #1 only  
**Decision:** **REAL SOURCE-ONLY FL/ENGINEERING GATES PASS; CONFIRMATORY TARGET SCORING STILL NO-GO WITHOUT EXPLICIT RESPONSIBLE-HUMAN REVIEW.**

## 1. Critical scientific implementation defect fixed BEFORE confirmatory runs

The previous eight-client source sampler cast native `float64` features to `float32` **before** applying `asinh`; the held-out prediction code applied `asinh` to the original `float64` features **before** casting. The codepaths were not exactly identical. Both now use:

```text
native 115-feature float64 vector
  -> asinh at float64 precision
  -> float32
  -> mean/SD normalization FIT SOLELY ON THE EIGHT SOURCE-CLIENT TRAINING SAMPLES
```

The locked architecture, source row IDs, 30k/client sampling protocol, optimizer, FedAvg/FedProx proximal constant, seeds, local epochs, rounds and probability decision threshold were not changed. Native `float64` is retained for the exact-feature digest bank; the `source_transform` routine now refuses prematurely cast source inputs. Earlier pilot learning curves are tied to their corresponding old implementation and must not be retrospectively misreported as current-code training results.

## 2. Science-compatible 54-run acceleration and reproducibility

The 9 folds × 2 methods × 3 seeds = **54** locked confirmatory jobs are enumerated by `plan_and_run_54.py`, which generates a 54-task ledger with ZERO native-data access unless an explicitly human-reviewed SHA-256 receipt and nine original ZIP file manifest are supplied.

A private, lazy **per-device/per-seed uniform-source-sample cache** is now implemented to avoid repeatedly decoding millions of source RAR/CSV rows for each method/fold. Each cache record is bound to exact original source ZIP SHA-256, imported loader SHA-256, engine SHA-256, seed, sample cap, compressed-array SHA-256 and exact raw `float64` source feature fingerprint list. Only the **eight non-target source devices** for a fold are opened/read through `fold_sources(target)`; the target cache is never looked up during that fold.

A completed 54-run job can be resumed only if its current engine/protocol/replay code hashes, approval, checkpoint, prediction gzip and source-fingerprint sidecar all match. Stale or partial jobs are not silently counted.

The exposure-analysis question was clarified prospectively in Chat9: **full eight-source-corpus recurrence** is NOT the same as **actual 240k-sampled-training source exposure**. Both are analysis-only with suitable class-conditional support and cannot be used to tune the binary detector.

## 3. Fresh direct execution evidence from Chat10

| Evidence | GitHub Actions | Result |
|---|---|---|
| Stage18 synthetic code/approval/cache/precision/replay QA | [40081544229](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40081544229) | **25/25 PASS** |
| Original public UCI eight-source float64 cache cold/warm full-budget regression | [40081405252](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40081405252) | **PASS**; full 5 FL rounds × 3 local epochs, 30k rows per each of 8 source clients |
| Duplicate FedAvg, same source samples & normalization; identical round-by-round loss | [40081405252](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40081405252) | **PASS**, cold vs warm 5-round learning curves exactly match |
| FedProx full-budget on SAME warm source cache | [40081405252](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40081405252) | **PASS**, five finite loss records |
| Version-bound original public UCI source provenance | [40081405252](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40081405252) | Eight source archives prepared from public-original 1.7GB UCI transport; **Ennio held-out ZIP not staged** |
| Immutable 54-task plan and eight current file-hash fields, non-authorizing human template | [40081631032](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40081631032) | **PASS:** 54 unique tasks, **0 executed**, 8 current code/inventory/analysis SHA values, human permission `false` |

Actual Chat10 **training-loop times** (not download/decompression/orchestration): FedAvg cold 40.33 s; FedAvg warm 39.88 s; FedProx warm 48.22 s. Cache saves repeated native-source loading, not necessarily gradient compute. The FedAvg cold/warm learning curves and fitted source normalization hashes were exactly equal.

**No held-out data were scored.** No native held-out balanced accuracy or FPR is reported.

## 4. Explicit authorization and reproducibility state

The committed `stage18_v2/NOT_AUTHORIZED_HUMAN_REVIEW_TEMPLATE.json` intentionally has `authorized:false` and is NOT a research approval. GitHub PR #1 has **zero submitted human review records** as of this Chat10 check. Although the frozen original dataset lineage has 25/25 published-source member-byte matches, reviewer attestation, current local nine-original-ZIP manifest SHA and a privately issued, exact-hash human approval receipt remain mandatory under the research protocol.

The final `assert_approval` requires the actual SHA-256 of **eight** implementation/analysis dependencies:

1. Stage16 frozen core specification.
2. Stage18 LODO model/train/test engine.
3. Independent full native-target raw-prediction replay.
4. Imported native ZIP/RAR loader and FedAvg aggregation source.
5. Pinned scientific Python requirements.
6. Native per-device/per-class test-support inventory.
7. Exact 54-job orchestration/resume runner.
8. Prospective full-corpus-versus-actual-training feature-exposure analysis clarification.

A **ninth**, independently validated original nine-ZIP local source manifest SHA is also required. The review packet deliberately lacks that privately held source-manifest digest; **do not invent one**.

## 5. GO / NO-GO summary

| Research component | Decision |
|---|---|
| Public original-UCI source lineage and source-only execution | PASS within stated provenance limits |
| Native `float64` train-vs-target preprocessing parity | Corrected, synthetic regression and public-source 5×3 runtime validated |
| Exact per-device/seed source caching / replay sidecar | Native COLD/WARM pass; actual source membership bank integrity verified earlier |
| Plan of 54 code-version-bound candidate jobs | PASS; **54 planned** |
| Responsible-human scientific/code review and signed private hash-bound receipt | **NOT RECEIVED** |
| Confirmatory nine-heldout × two-baseline × three-seed test predictions | **0/54 — NOT RUN** |
| Device-clustered statistics, exposure-conditioned effect estimates and publication novelty | **NOT ESTABLISHED** |
| Submission-readiness to MDPI *AI* | **NO-GO**, pending real target outcomes |

**Next critical path:** Obtain responsible-researcher review/authorization of the exact reviewed code release + original-nine ZIP manifest; only after approval run the locked 54-job native test set with immutable raw predictions and independent replay. Do not add another algorithm, tune the threshold on target data, silently skip unsuccessful folds, or claim high source-only pilot accuracy is a heldout result.
