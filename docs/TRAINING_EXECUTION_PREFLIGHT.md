# Stage 3 → Stage 4 execution readiness (2026-10)

**This document does not report a trained model.** The public repository
currently lacks the authenticated original CICIoT2023/DIAD2024 data, full
candidate-column split files and newly trained checkpoint artifacts.
Synthetic GitHub Actions tests verify guards and Python syntax, not
GPU training, throughput, test accuracy, or the manuscript's metrics.

## Per-seed artifact layout — mandatory

Strict Stage 3 teacher outputs are isolated by dataset, seed AND client:

\`\`\`
experiments/strict_stage3/
  ciciot2023/seed_42/Link_1_Core/
    mamba_val_best.pt
    train_fitted_scaler.npz
    provenance.json
  ciciot2023/seed_123/Link_1_Core/ ...
\`\`\`

Strict Stage 4 must load only a teacher trained with the **same seed**.
Both the teacher checkpoint and train-fitted scaler SHA-256 are now included
in Stage 3 provenance and verified by Stage 4, the Stage 4 preflight and
the frozen TEST evaluator. No silent fallback to legacy non-seeded paths.
Any older Stage 3 runs must be **re-trained from scratch** in the new layout.
Different seeds must never share selected teacher checkpoints.

## Safe execution sequence (no real run has been launched)

1. Authenticate the original raw benchmark data. Review attack-to-severity
   mapping, original group/session/time keys and original-to-harmonized row
   lineage. The old already-selected 14-column data cannot serve as a
   fresh candidate-feature pool.
2. Obtain at least 15 nonlabel candidate feature columns from authentic raw
   sources, split TRAIN/VAL/TEST *before* windows/feature fitting.
3. Select the 14 columns from TRAIN only using
   \`scripts/data/select_features_train_only.py\`. Save the split manifest,
   candidate review and mapping evidence with full source hashes.
4. **Before Stage 3**, run the following preflight on the machine holding
   verified TRAIN/VAL files:

\`\`\`bash
python scripts/training/preflight_real_training.py \
  --dataset ciciot2023 --stage stage3 --seed 42 \
  --split-root /verified/full_candidate_strict_split \
  --feature-json /verified/selected_14_train_only.json \
  --output /logs/preflight_ciciot_seed42_stage3.json
\`\`\`

Exit code 0 means required declared TRAIN/VAL files, source hashes, matching
feature provenance, five clients and Python modules were *available*.
It **does not certify the raw dataset, the experimental methodology, GPU
performance or model convergence**. Exit code 2 indicates blockers; resolve
them before training. No TEST CSV is opened during preflight.

5. Train each Mamba teacher only after the preflight passes:

\`\`\`bash
python scripts/training/train_mamba_strict.py \
  --dataset ciciot2023 --seed 42 \
  --split-root /verified/full_candidate_strict_split \
  --feature-json /verified/selected_14_train_only.json
\`\`\`

6. **Before Stage 4**, verify all FIVE seed-matched Stage 3 checkpoints:

\`\`\`bash
python scripts/training/preflight_real_training.py \
  --dataset ciciot2023 --stage stage4 --seed 42 \
  --split-root /verified/full_candidate_strict_split \
  --feature-json /verified/selected_14_train_only.json
\`\`\`

7. Only then, run strict Stage 4 with its corresponding seed:

\`\`\`bash
python scripts/training/train_federated_strict.py \
  --dataset ciciot2023 --seed 42 \
  --split-root /verified/full_candidate_strict_split \
  --feature-json /verified/selected_14_train_only.json --mu-link 0
\`\`\`

8. Keep TEST sealed for the final explicitly preregistered evaluation.
   Do not use TEST for development, hyperparameter choice or feature
   selection. Report all seeds, including failures, rather than selecting
   the best only.

## Important limitations

- \`check_dependencies=True\` verifies installed Python modules, **not**
  that the GPU has enough RAM or that end-to-end data training succeeds.
- Strict Stage 4 has a **new contextual-bandit reward protocol**, not the
  manuscript's historical fully deployed SDN-MDP. No active neighbor action
  coordination exists; \`mu_link=0\` is mandatory.
- The 14-column selector in the strict scripts is TRAIN-only and differs
  from the original pre-split SHAP/LIME ranking. It must be discussed as
  a *new experiment* if real runs are eventually performed.
- The original paper's FPR/FNR and MSR should not be replaced by invented,
  synthetic or unverified scores.
