# Stage 18 — Strict eight-client native N-BaIoT LODO engine

**Current status: software candidate, target TEST EXECUTION BLOCKED.** This branch has not produced any actual held-out N-BaIoT predictions. Draft PR #1 remains unmerged and the fixed Stage16 research protocol explicitly sets `full_execution_authorized: false`.

## Code

- `lodo_engine.py`: a native original ZIP/RAR 8-client FedAvg/FedProx driver implementing the fixed 115–64–32–1 MLP, source-only uniform 30k/device sampler, `asinh`-then-training-source normalization, AdamW 0.001, client-specific inverse-prevalence weighted BCE, sample-count aggregation, 5×3 FL rounds/epochs, FedProx coefficient 0.01 and seeds [3107,3108,3109].
- `replay_predictions.py`: standard-library-only independent replay that streams every gzipped raw native target prediction and independently checks row identifiers, source-label consistency, probability range, native full class count and artifact SHA-256, then computes full-device BA, benign FPR, attack recall, and supported per-class attack recall.
- `test_lodo_engine_and_replay.py`: synthetic-only isolation, authorization, sampling, AdamW/FedProx and lossless prediction-row replay QA; passing tests DO NOT prove final test accuracy.

## Hard security/scientific gates

The default `--mode preflight` opens **only the eight source ZIPs**. It cannot read even one feature or label from the designated ninth held-out device. Use it to verify the real eight-client training loop, sampling, CPU cost and logging.

```bash
python stage18_v2/lodo_engine.py \
  --mode preflight \
  --source-root /path/to/original/native/nine/zips \
  --heldout Ennio_Doorbell --method FedAvg --seed 3107 \
  --preflight-cap 30000 --preflight-rounds 1 --preflight-epochs 1 \
  --output-dir /tmp/afras_v2_stage18_source_preflight
```

The normal confirmatory mode **always rejects** missing, malformed or stale authorization. It requires an explicit externally reviewed, **uncommitted** JSON with:

```json
{
  "status": "AUTHORIZED_FOR_CONFIRMATORY_TEST",
  "authorized": true,
  "approved_by": "<responsible human researcher / supervisor>",
  "human_review_complete": true,
  "independent_data_admission_complete": true,
  "no_target_results_reviewed": true,
  "protocol_sha256": "<actual frozen protocol file SHA-256>",
  "engine_sha256": "<actual reviewed lodo_engine.py SHA-256>",
  "replay_sha256": "<actual reviewed replay_predictions.py SHA-256>",
  "native_loader_sha256": "<actual reviewed stage17_v2/source_only_pilot.py SHA-256>",
  "requirements_sha256": "<actual requirements-pilot.txt SHA-256>",
  "native_inventory_sha256": "<actual Stage16 analysis-only inventory SHA-256>",
  "orchestration_sha256": "<actual stage18_v2/plan_and_run_54.py SHA-256>",
  "exposure_analysis_protocol_sha256": "<actual Stage16 pre-result exposure addendum SHA-256>",
  "source_manifest_sha256": "<actual original nine-local-ZIP manifest SHA-256>"
}
```

This JSON is an auditable approval **receipt, not a cryptographic signature**. This repository does not fabricate an authorized receipt. Use `stage18_v2/NOT_AUTHORIZED_HUMAN_REVIEW_TEMPLATE.json` only as a fail-closed reference; it MUST remain `authorized:false` until the responsible person actually approves a **private local copy**. Generate the immutable 54-run ledger and real file-byte hashes using `python stage18_v2/plan_and_run_54.py --plan-output /path/to/plan.json --source-manifest /path/to/official_local_nine_zip_manifest.json`. The reproducibility hashes include the imported native ZIP/RAR loader and original class-support inventory because these affect scientific results. Until scientific and code review, DO NOT run `--mode confirmatory`, create an approval receipt, or inspect target accuracy.

Once properly authorized, each method/seed/fold invocation trains **all eight source clients** on the same 30k/device deterministic samples; only after training is finalization complete, it streams **every original heldout native record** through the locked last-round model. The run outputs a per-row `target_predictions.csv.gz`, class support receipt, training trace, fitted source-only standardization statistics, code hash and final checkpoint. No test-side filtering/deduplication/rebalancing or target-side threshold tuning is supported.

Any completed result must be independently replayed:

```bash
python stage18_v2/replay_predictions.py \
  --receipt /path/to/result/run_receipt.json \
  --native-inventory stage16_v2/EXPOSURE_ELIGIBILITY_ANALYSIS_ONLY.csv \
  --output /path/to/result/independent_replay.json
```

The inventory already contains native class counts from the earlier public dataset audit; it is permitted as an **after-run audit-only** denominator check, never model tuning. It also contains exact-feature recurrence information: the FL engine does not read the recurrence labels or use test predictions to choose a model.

## Chat 10 correctness and source-cache admission (pre-test amendment)

The independent 24 October 2026 code review found that the earlier source loader converted selected training rows to \`float32\` **before** applying the \`asinh\` transform, whereas target inference applied \`asinh\` to original \`float64\` rows and converted afterward. This mismatch was corrected. Both model fitting and target prediction now use:

\`\`\`text
original native 115-dimensional float64 -> asinh in float64
-> float32 -> normalization fitted on sampled training sources ONLY
\`\`\`

Source rows retain original float64 until preprocessing and fingerprinting. No model architecture, trained sample IDs, frozen training optimizer, FL rounds, local epochs, seed or threshold was changed. Real evaluation from any earlier source-only pilot uses its original corresponding code version and is not silently relabeled as the revised implementation.

The 54-run executor now uses a **private per-device/seed sample cache** to avoid rereading full nested ZIP/RAR archives for each method and fold. Each raw-float64 cached sample is bound to **original source-device ZIP SHA-256, native loader code SHA-256, engine code SHA-256, seed, k and compressed cache SHA-256**. The cache is loaded only in the \`fold_sources(target)\` loop; the held-out target cache is never read in that fold. Cache corruption or stale code/data is fatal, not a silent recompute. Actual sampled-training source-vector membership is independently checked in replay.

\`stage18_v2/plan_and_run_54.py --plan-output /path/to/plan.json\` remains **PLAN ONLY** without target access. A separate \`--execute\` requires reviewed, locally supplied original archives, an explicit responsible-human-approved private receipt and a pinned manifest SHA. Results from older code revisions are not silently resumed as current results; the runner verifies original protocol, engine, replay, source-sample sidecar and checkpoint hashes.

The original full-source-availability recurrence (Stage 13, ~90.74%) must never be renamed "model-visible training overlap": frozen training uses only eight 30k-device source subsamples. A distinct pre-result clarification names true sampled-training exposure as a separate analysis-only variable.

**Real-data gate evidence:** GitHub Actions \`afras-v2-chat10-float64-cache-source-admission.yml\` is the public-original-UCI source-only cold/warm cache and 5×3 FedAvg/FedProx regression. Its final workflow outcome must be checked rather than inferred from source compilation or synthetic QA. It does **not** open/score any held-out target.

## Scientific limitations / review checklist

1. Software unit tests and a real source-only preflight must both pass; audit that target data cannot leak via source fitting or preprocessing.
2. Validate native class counts, all original heldout rows and lossless per-record output in the independent replay.
3. Confirm correct optimistic AdamW optimizer state behavior: optimizer **resets per client per round** (as in the source-only pilot); this is a reproducibility choice, not proof of optimized FedProx.
4. All sources are processed by a centralized experimental runner. **No cryptographic privacy guarantee** follows from the label FL. Source device pool size and per-round communication bytes must be reported, but network transfer has not been benchmarked.
5. Use all 9 outer folds × both baselines × 3 seeds and preserve negative outcomes; do not select only successful seeds. Effects are paired by 9 devices, not by millions of test observations.
6. Earlier Samsung source-device validation guided optimizer selection; this history must be disclosed and the final nine-device study must not be misrepresented as fully historically blind.
7. The prior source-recurrence census is a *post-prediction analytic stratum*, not a causal intervention. Do not describe exact numerical-feature duplication as captured-packet equality.
8. Full device raw predictions will be large. Never upload them to public CI or a GitHub repository without deliberate research data management approval.

**Status convention:** unit-test PASS != real eight-client preflight PASS != confirmatory LODO performance PASS != novelty/journal acceptance.
