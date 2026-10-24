# AFRAS-FL V2 — Chat 12 Execution Gate Audit and Responsible-Researcher Review

**Recorded:** 24 October 2026  
**Current branch:** `research/afras-v2-stage17-source-only-pilot-20261024` (Draft PR #1)  
**Scientific status:** `CONDITIONAL_ENGINEERING_PASS__HUMAN_APPROVAL_AND_LOCAL_BYTE_RECHECK_REQUIRED`  
**Target experiment status:** **0/54 full target LODO experiments completed.**

## 1. Confirmed evidence and software implementation delta

- The user's Library lists all nine canonical original N-BaIoT device ZIP files. Their nine **file-size metadata values** agree with the prior original-file manifest; a Library listing does **not** prove current raw SHA-256.
- The earlier independently recorded full original-file SHA-256 manifest is retained at `stage18_v2/ORIGINAL_NINE_LOCAL_ZIP_HASH_MANIFEST_2026-10-24.json`. It was already tied to the 54-run no-data planner in Chat 11.
- In Chat 12, the local shell and Python runtime returned execution errors. One original Ennio ZIP was materialized into a working-container path, but **its SHA was not recomputed in this chat**. There is **no new 9/9 raw-byte PASS claim**.
- The `plan_and_run_54.py --execute` path now invokes `verify_original_nine_zip_bytes.validate_original_source_manifest()` **before creating the experiment output root or launching the first FL training subprocess**, independently rehashing all nine original local ZIP outer byte streams against the exact approved manifest. If one file is missing, altered or different in size/SHA, it fails before any target model predictions.
- Upon verified success the runner preserves `ORIGINAL_NINE_ZIP_BYTE_ADMISSION.json` in the private experiment root. On a resume the previous admission receipt must exactly agree with newly computed evidence.
- The admission scanner `verify_original_nine_zip_bytes.py` is now also an explicit `original_nine_zip_admission_scanner_sha256` **human approval gate dependency**. All frozen training specifications remain unchanged.
- Synthetic software CI at [GitHub Actions 40083823861](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40083823861) passed **31/31 Python tests**, including two new before-first-fit nine-archive corruption/pass tests. This confirms **tested code controls**, not actual native-byte admission.
- The current no-data reviewer packet workflow has been updated to publish **nine implementation/analysis SHA-256 fields plus the original nine-file manifest SHA** alongside all 54 planned task IDs, without generating authorization or decoding the dataset.

## 2. Explicit hard-science boundary

Reading ZIP compressed bytes to calculate SHA-256 is permitted as a **data-integrity check**. This does not reveal label/feature rows to the model, which still trains only on the other eight devices in each frozen fold. The independent per-run raw-target prediction replay continues to require all original heldout rows and per-class denominator reconciliation.

The earlier Stage 13 full-corpus recurrence census is **not** evidence that an example was actually among the 240,000 sampled source training rows. The pre-result Stage 16 exposure analysis amendment and sampled-source digest sidecars remain unchanged.

## 3. Responsible-human scientific and implementation review (pending)

Review the exact branch commit and record reviewer identity and date **only after real review**. A GitHub review or signed private local review receipt can document this, subject to the responsible researcher's governance. The machine-readable approval JSON is **not a cryptographic digital signature**; merely setting booleans to true without inspection would not establish independent review.

**Required checks, before even one target test is scored:**

1. Verify that nine local files in the actual training environment are exactly the original audited SHA-256 ZIPs and retain the emitted private `ORIGINAL_NINE_ZIP_BYTE_ADMISSION.json`.
2. Review frozen `FROZEN_CORE_PROTOCOL_V1_2026-10-24.json`, pre-result exposure amendment, 54-job runner, core engine, independent replay, source loader/aggregation, Python requirements, native class-support inventory, and the original ZIP admission scanner. The no-data review packet reports all current SHA-256 values. The original nine-device manifest is a separate tenth SHA-bound item.
3. Inspect heldout exclusion, uniform source 30k-device sampling, `float64→asinh→float32` parity, source-only fitted preprocessing, local AdamW optimizer reset per client/round, weighted BCE, FedProx penalty, exactly eight source clients, all original target rows and zero-denominator handling.
4. Confirm 54 tasks are exactly nine outer devices × two methods × three fixed seeds; all target outputs are private, complete, and subject to independent checksum/row-count replay. No cherry-picking or tuning using target predictions is allowed.
5. Account for historical Samsung source-only optimizer selection: prospective nine-way LODO evaluation is NOT nine historically blind independent lockboxes.
6. Accept the scientifically narrow conditional contribution: feature-vector exact equality does not prove identical captured network events, and full-source availability does not equal actual sampled-model exposure. Algorithmic/fuzzy novelty remains **NO-GO**.

Only after the above checks and valid original ZIP source-byte receipt are available should the responsible researcher explicitly issue a **private**, SHA-bound `AUTHORIZED_FOR_CONFIRMATORY_TEST` receipt matching the gate. **This file has not been issued in Chat 12.**

## 4. Commands for the accountable operator

From the reviewed repository branch on the authorized execution machine containing the original local nine-ZIP directory:

```bash
# A: data admission only; no labels/targets/models read:
python stage18_v2/verify_original_nine_zip_bytes.py \
  --source-root /secure/afras/original_nine_zips \
  --manifest stage18_v2/ORIGINAL_NINE_LOCAL_ZIP_HASH_MANIFEST_2026-10-24.json \
  --receipt /secure/afras/evidence/original_nine_zip_admission.json

# B: immutable plan only, no target evaluation:
python stage18_v2/plan_and_run_54.py \
  --source-manifest stage18_v2/ORIGINAL_NINE_LOCAL_ZIP_HASH_MANIFEST_2026-10-24.json \
  --plan-output /secure/afras/evidence/current_54_job_plan.json
```

The plan exposes current required code SHA-256 values; these become valid review evidence **only for the exact audited commit**, not a generic all-purpose authorization. After the responsible human reviewer has signed off, execute the locked jobs using the documented private `--execute`, `--approval-gate`, `--source-root`, `--source-manifest` and `--output-root` options. The executor repeats the nine-source SHA-256 audit before first training and preserves independent replay artifacts.

## 5. Stage ledger

| Stage | Status at end of Chat 12 |
|---|---|
| 13 — Original published dataset provenance | Original 25/25 member-byte identity prior audit; current local full nine-ZIP byte admission **PENDING** |
| 15 — Route A novel evaluation question | **CONDITIONAL GO**, not originality acceptance |
| 16 — Training and test core | **FROZEN v1**, no change to model hyperparameters |
| 17 — Real source-only FL feasibility | **PASS** (previously demonstrated) |
| 18 — 54-task plan, gated runner, independent replay software | **PASS engineering with CI, subject to external review** |
| 18 — 9 original ZIP bytes freshly rehashed on final machine | **NOT YET VERIFIED** |
| 18 — Recorded responsible human review/approval | **PENDING** |
| 18 — Final native LODO fits | **0/54; NO-GO** |
| 19 — Independent final statistics | **NOT COMPLETE** |
| 20 — MDPI AI manuscript submission | **NOT READY** |

**Do not confuse test-harness success with verified manuscript claims, human authorization, or 54 genuine heldout experiments.**
