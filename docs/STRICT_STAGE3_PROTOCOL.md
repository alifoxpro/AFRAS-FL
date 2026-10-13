# Strict Stage 3 — Mamba-only teacher training (TRAIN/VAL, no TEST)

**Status:** source implementation with CI syntax/manifest tests. No GPU training has
been performed on CICIoT2023 or DIAD2024 here, and no previously reported metric
is revalidated by this source commit.

## Prerequisites
- \`scripts/data/split_records_leakfree.py\` has generated the split CSVs.
- Use a reviewed TRAIN-only feature manifest \`data/selected_14_train_only.json\`,
  generated **after** splitting from at least 15 independently reviewed
  candidate feature columns. Historical \`unified_selected_14.json\` is
  refused; audit source feature selection before claims.
- Source dataset row order is valid; no group/time leakage is present.
- Python 3.10+, PyTorch, numpy, pandas, scipy, sklearn, matplotlib, seaborn.
- Sufficient RAM/GPU memory for original per-link CSVs and windows.

## Example

\`\`\`bash
python scripts/data/split_records_leakfree.py --input-root /verified/unselected_5link_csvs --datasets ciciot2023 diad2024 --window-size 20 --group-column VERIFIED_SESSION_ID --time-column VERIFIED_EVENT_TIME
python scripts/data/select_features_train_only.py --candidate-json /reviewed/candidates.json --datasets ciciot2023 diad2024 --n-features 14
python scripts/training/preflight_real_training.py --dataset ciciot2023 --stage stage3 --seed 42
python scripts/training/train_mamba_strict.py --dataset ciciot2023 --epochs 30 --seed 42
\`\`\`

New seed-scoped per-client outputs are stored under
\`experiments/strict_stage3/<dataset>/seed_<seed>/<link>/\`, including:
- \`mamba_val_best.pt\`: teacher selected exclusively by validation loss.
- \`train_fitted_scaler.npz\`: normalization statistics fitted only on TRAIN.
- \`history.json\`: TRAIN/VAL per-epoch history.
- \`provenance.json\`: hashes, seed, chosen epoch, feature selection reference,
  train/val windows and validation metrics.

The script refuses to overwrite existing output, use original unsplit caches,
load old checkpoints, or access test CSVs. Test metrics **must not** appear in
\`provenance.json\`.

## Scientific and technical limitations
1. This is a **teacher-only** Stage 3. The old Strategy A/B modules still perform
   unsafe pooled PCA/cache preparation and evaluation. **DO NOT** feed this
   checkpoint into those old pipelines and label the result leakage-free.
2. No independent test metrics are produced or claimed.
3. The strict TRAIN-only feature manifest is source-hash checked and rejected
   when it lacks proper split lineage; this still does NOT independently audit
   original candidate feature derivation or raw data preprocessing. The upstream raw \`severity\` taxonomy
   and attack-vs-benign interpretation must also be independently verified.
4. The split script's schema verifies row ranges/embargo, not cross-client
   duplicate flows, session/campaign overlap or leakage in raw upstream
   transformations.
5. The strict Stage 4 RL + federated policy must be trained on TRAIN-derived
   features/teacher predictions, use VAL only for tuning, and evaluate an
   **untouched** TEST once at the end.
6. Existing \`results_StrategyB\` and manuscript table values remain historical
   and unverified against this new, different experimental protocol.
