# AFRAS-FL V2 — Chat 11 Stage18 Final Data and Research Approval Handover

**Recorded date:** 24 October 2026  
**Research target:** MDPI *AI*, Route A — feature recurrence-aware evaluation, **not a proven novel algorithm**.  
**Current status:** `READY_FOR_RESPONSIBLE_RESEARCHER_REVIEW`, **NOT AUTHORIZED FOR TEST**.  
**Frozen core:** `stage16_v2/FROZEN_CORE_PROTOCOL_V1_2026-10-24.json` unchanged.

## Current hard evidence

1. Stage13 prior independent researcher-local audit records exact SHA-256 and byte size for the original **nine ZIP archives**. All nine canonical ZIP names remain present in the researcher's connected Library at original sizes (Library metadata inspected again during Chat11). **File presence/size is not a current-turn recomputation of raw bytes.**
2. The machine-readable nine-ZIP checksum manifest was rebuilt from that audited evidence, without inventing checksums: `stage18_v2/ORIGINAL_NINE_LOCAL_ZIP_HASH_MANIFEST_2026-10-24.json`. It contains `local_archives` with canonical `device`, `filename`, `local_sha256` and `local_bytes`. Nine local ZIP sizes sum to **1,773,532,530 bytes**.
3. [GitHub Actions Chat11 evidence](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40082690399) **PASS**: validated 9 manifest entries, generated 54 **unexecuted** uniquely keyed fold×method×seed tasks, and SHA-bound them to the original-local-ZIP manifest checksum: `76612c1104f477001f2735bf8e0bf7479ecaabbd71e2f85a2714d0d3bd664f93`. The workflow deliberately neither downloaded nor opened original ZIP bytes, and computed **zero target predictions**.
4. Stage18 QA at [run 40082663948](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40082663948) PASS, current source-only test and hard authorization checks. Earlier real public-original UCI source-only experiment [40081405252](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40081405252) PASS: FedAvg float64 cold/warm cache exact training-loss parity plus FedProx, each 5×3 with eight sources, target Ennio unstaged.
5. GitHub Draft PR #1 remains open with **zero submitted reviewer records**. The `NOT_AUTHORIZED_HUMAN_REVIEW_TEMPLATE.json` is `authorized:false`. No actual 9×2×3 confirmatory test inference is complete (0/54).

## What the responsible researcher must actually review

- **Current exact code**: `stage18_v2/lodo_engine.py`, `replay_predictions.py`, `plan_and_run_54.py`, imported `stage17_v2/source_only_pilot.py`, Stage16 frozen core, Stage16 exposure amendment, requirements and class-support inventory.
- **Data identity**: On the execution machine containing all nine original device ZIPs, independently compute each SHA-256 and ensure equality with the manifest above. Device ZIP **outer** hashes matter to the current engine; published original source-member identity (25/25 audit pass) does not automatically mean a repackaged ZIP has the same wrapper hash.
- **Sample/scoring isolation**: Training fits eight source devices and uses their 30k/device uniform selected native rows for source-only normalization, class weights and gradients. Entire original ninth target device is evaluated only after last-round training, with original native class prevalence.
- **Observational exposure distinction**: Full-eight-source-corpus exact-feature recurrence ≠ the specific 240k actually sampled source vectors. Both must be measured and reported separately; none may tune a model/threshold.
- **Non-blind historical validation**: Samsung source-only validation previously guided the optimizer choice. Do not label all nine folds prospectively historically blind.
- **Storage/ethics**: Raw target predictions, membership fingerprint bank and checkpoints are research outputs. Keep them private under an approved data retention/access plan. FL simulation using centralized research processing does not establish deployment privacy.

## Minimal zero-test plan generation on the original-data execution machine

```bash
python stage18_v2/plan_and_run_54.py \
  --source-manifest stage18_v2/ORIGINAL_NINE_LOCAL_ZIP_HASH_MANIFEST_2026-10-24.json \
  --plan-output /secure/AFRAS_V2_54_PLAN_2026-10-24.json
```

This command opens **no ZIPs** and issues **no approval**. The output gives current protocol/engine/replay/loader/requirements/inventory/runner/exposure amendment SHA values and the SHA of the original nine-ZIP manifest.

## The execution gate remains explicitly shut

- A *responsible human researcher or supervisor* must read/approve the scientific procedure and its exact files, confirm original archive data admission and explicitly acknowledge the target-score plan before it may proceed.
- The approval receipt must be created **privately** by the human responsible for the research; its mandatory true flags are `human_review_complete`, `independent_data_admission_complete` and `no_target_results_reviewed`. All bound SHA fields must match the current plan. An automatically populated flag or AI-generated reviewer signature would be dishonest.
- Only **after** that approval, and only with verified original bytes and sufficient private storage, an operator may run the explicit `plan_and_run_54.py --execute` mode; each run must produce complete raw rows and independently replayed metrics.
- An author/self-approval may not substitute for genuinely independent review when the journal/supervisor requires an independent reviewer. The repository gate checks a record and hashes, **not** the authenticity of a human signature.
- No change to fixed hyperparameters after any target result is examined.

## Stage decision

| Gate | Evidence state |
|---|---|
| Nine archive metadata and expected SHA manifest | **RECOVERED AND CI STRUCTURE PASS** |
| Actual local nine-ZIP bytes checked *at final execution environment* | **NOT YET CONFIRMED** |
| Full source-only eight-client, five-round FL feasibility | **PASS** |
| Locked 54-run schedule | **PASS (PLAN ONLY)** |
| Independent human code/scientific authorization | **PENDING; no GitHub reviews recorded** |
| Native nine-heldout × two-method × three-seed results | **0/54; NO-GO** |
| Statistical results and MDPI AI submission | **NOT READY** |

**Do not count CI success, public UCI source-only learning, or the pre-result overlap audit as final held-out results or independent reviewer approval.**
