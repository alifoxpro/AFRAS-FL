# AFRAS-FL V2 — Chat 9 Stage 18 Scientific Code Audit and Execution Admission

**Date:** 24 October 2026  
**Target journal:** *AI* (MDPI)  
**Scope:** Existing research branch and Draft PR #1, **not** `main`  
**Audit outcome:** **ENGINEERING GO TO PREPARE; CONFIRMATORY EXECUTION CONDITIONAL / NOT YET AUTHORIZED**.

## 1. Evidence verified in this execution

| Gate | Direct execution evidence | Decision |
|---|---|---|
| Frozen training specification | `stage16_v2/FROZEN_CORE_PROTOCOL_V1_2026-10-24.json` prespecifies 9 folds × 2 methods × 3 seeds, native heldout prevalence, 8 clients/fold, 115–64–32–1 MLP, AdamW 0.001, 5×3 rounds/epochs, batch 128, sample 30k/device | **Frozen core retained, unchanged** |
| Code & independent replay QA | GitHub Actions [40080276612](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40080276612) reports **19/19 actual Python fixture tests PASS**, including fail-closed target gate, strict source membership, honest original class support, raw-prediction completeness, signed-zero canonicalization, and actual-sampled-feature digest bank integrity | **Synthetic QA PASS** |
| Real native source-only 8-client integration | GitHub Actions [40075927293](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40075927293), exactly 8 real source clients, 240,000 sampled training rows, one FedAvg round, **zero target inference** | **Source-only feasibility PASS** |
| Full frozen-budget native training | GitHub Actions [40080030910](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40080030910): real UCI, 8 clients, 30k/device, **five rounds × three local epochs**, FedAvg train duration 20.03 sec; FedProx 25.04 sec, source losses finite, both completed; 54-run plan generated without opening target | **Full source-training budget feasibility PASS** |
| Actual sampled-source exposure check | Latest engine saves digest-only `actually_trained_source_feature_digests.csv.gz`, 240k canonical raw-float64 selected-source fingerprints; replay independently verifies count, source IDs, SHA-256 and rows | **Software QA PASS; native-current-revision verification recorded separately when complete** |
| Actual nine-heldout native test results | No target inference authorized; earlier studies used Samsung source-side exploratory validation | **0/54 confirmatory runs; no target metrics** |

All real-data feasibility results above are **source-only**, not test accuracy. The 20.03/25.04 sec durations are **training-loop durations only**; archive acquisition, native CSV decoding, other seeds/folds and full-target prediction overhead are not included. Full original researcher-local ZIP authorization is distinct from the public-UCI source-only CI receipts.

## 2. Blocking scientific correction discovered before test outcomes

The Stage 13 observation that **90.74% of native held-out records match a numerical vector from the entire collection of other devices** MUST NOT be misrepresented as *training-visible exact exposure*. The frozen experiment actually trains on **30,000 selected rows per one of eight source devices**, not on all 6.7 million source rows.

Prospective clarification: [PRE_RESULT_EXPOSURE_ESTIMAND_CLARIFICATION_2026-10-24.md](../stage16_v2/PRE_RESULT_EXPOSURE_ESTIMAND_CLARIFICATION_2026-10-24.md).

Two non-interchangeable quantities are now defined:
- **Full-source-corpus availability recurrence** (existing Stage 13, model-independent).
- **Actual sampled-training exposure** (fold/seed-specific membership in the 240k vectors truly passed to the model).

No change was made to fixed model architecture, optimizer, dataset folds, sampling cap, number of rounds, seeds or primary test endpoint. Every raw target prediction is paired with a canonical 115-feature digest; the selected-source digest-only bank is separately SHA-bound and must survive replay. Full-corpus support masks (42 attack cells with both strata) do not guarantee that the same 42 cells remain estimable under actual sampled-training exposure. No absent-class or empty-exposure recall may be imputed.

## 3. Remaining independent review and execution conditions

1. **Human code/scientific approval:** A responsible researcher or supervisor independently inspects this branch's exact engine, replay, target isolation, sampled-source fingerprints and disclosure history; records an approval identity. GitHub unit CI is not a substitute for human scientific sign-off.
2. **Immutable source-lineage manifest:** Supply the actual nine original user-local N-BaIoT device ZIPs and previously audited local SHA-256 manifest; do not use public UCI repackaged ZIPs with different outer hashes as if they were original byte-identical local archives.
3. **Exact file-byte hashes:** After the final code revision, record SHA-256 of **frozen protocol, LODO engine, independent replay, and local manifest**. The `plan_and_run_54.py --plan-output ... --source-manifest ...` command computes the relevant values with **zero target access**.
4. **Human-issued authorization receipt:** Only after (1)–(3), explicitly issue a *local, uncommitted* JSON receipt whose `status`, `authorized`, `approved_by`, `protocol_sha256`, `engine_sha256`, `replay_sha256`, `source_manifest_sha256` match the code's audit gate. No assistant-authored placeholder counts as approval.
5. **Storage and interruption safeguards:** Run from an adequately provisioned, retained research workstation; do not upload raw predictions, source fingerprints, unapproved private ZIPs, or checkpoints to the public GitHub repo. Every completed run requires independent replay, matching code/data hashes and original per-class row support. A partial run is **not** a completed result.
6. **Statistics/research novelty disclosure:** Primary comparison remains FedProx versus FedAvg by nine paired devices; no cherry-picking of seeds, folds, exposure cells or thresholds. Earlier Samsung source-validation-informed optimizer selection must be transparently disclosed; novel algorithm claims remain NO-GO.

## 4. Executable critical-path ledger

`stage18_v2/plan_and_run_54.py` deterministically lists all **54 distinct jobs** (nine target devices × two methods × three fixed seeds). Default operation **never opens source or target archives**; `--execute` requires an explicitly reviewed and source-manifest-bound approval receipt. Once authorized, each job writes all original target raw predictions, sample-source digest evidence, a checkpoint, and an independent replay; partially completed runs cannot be silently counted or overwritten.

**Current decision:** **CONDITIONAL GO TO SEEK RESPONSIBLE-HUMAN SIGN-OFF.** Confirmatory execution remains **BLOCKED**; Stage 18 is **0/54**. This decision does not imply journal novelty has been demonstrated or that MDPI *AI* will accept the eventual manuscript.
