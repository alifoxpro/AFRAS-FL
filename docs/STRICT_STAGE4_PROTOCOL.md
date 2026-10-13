# Strict Stage 4: federated contextual-bandit Q learning with TRAIN-only AFRAS-FL rules

**Scientific status:** proposed **new experiment**, code added for audit. No
CICIoT2023/DIAD2024 GPU experiment or held-out TEST has been run by this PR.
Not equivalent to the historical manuscript's published tables.

## What this implements

- Exact upstream split-manifest and strict Stage3 teacher provenance validation,
  including **same-seed** teacher checkpoints from
  \`experiments/strict_stage3/<dataset>/seed_<seed>/<link>/\` and stored
  teacher/scaler SHA-256 checksums.
- Mamba checkpoint trained on TRAIN and selected by VAL is loaded per client.
- **28-dimensional aligned state**: 14 TRAIN-standardized feature means,
  11 feature standard deviations, and 3 Mamba softmax probabilities.
  All state positions have the same semantic meaning across federated clients.
  No embedding PCA is fitted on pooled or held-out data.
- The original 7-phase \`AFRASFLPipeline\` is **fitted only on TRAIN** feature
  columns 0 and 1 and true TRAIN severity labels; no VAL/TEST rule mining.
  This new *fixed two-feature* design is different from the manuscript's
  variance-selected features; audit methodological compatibility.
- Independent B2 FedAvg, B3 FedProx, B4 FedProx + action-dependent fuzzy
  rewards start from the same seeded Q-network initialization. Their
  respective best rounds are selected using **VAL only**.
- Rewards are fully specified in \`strict_fed_core.py\` and no longer use
  nonstationary Q-magnitude confidence. Latency is an assumed action-cost
  **proxy**, not measured milliseconds.
- The DQN-shaped Q-network is trained for a **contextual bandit**
  (\`discount_gamma=0\`) because action choice has not been shown to control
  the next state. Do not claim long-horizon RL, PBRS invariance, or deployed SDN
  feedback from these results.
- \`R_link\` is still **unimplemented**: nonzero \`--mu-link\` is prohibited.
  This B4 model is *fuzzy without neighbor link reward*; it is **not the full
  historical AFRAS-FL configuration**.
- Only *action-success rate* and two explicitly named error rates are reported.
  Without verification that Low is benign and High denotes all true attacks,
  they cannot be called binary IDS FPR/FNR.
- Every run creates fresh output \`experiments/strict_stage4/<dataset>/seed_<seed>\`
  and refuses overwrites, so prior legacy checkpoints cannot be mixed in.

## Run prerequisites and invocation

1. Create the ordered train/val/test split with \`scripts/data/split_records_leakfree.py\`.
2. Generate a reviewed TRAIN-only feature-selection manifest from a full candidate pool,
   then train fresh Mamba teachers with \`scripts/training/train_mamba_strict.py\`
   **using the same seed** as Stage 4. Run the preflight from
   \`docs/TRAINING_EXECUTION_PREFLIGHT.md\` before Stage 3 and before Stage 4.
3. For each dataset run:

\`\`\`bash
python scripts/training/train_federated_strict.py \
  --dataset ciciot2023 --rounds 10 --local-epochs 1 --seed 42 \
  --lambda-fuzzy 0.25 --mu-link 0
\`\`\`

For reduced debugging experiments use \`--pilot --max-train-windows 5000\`
and **label all such outputs PILOT; they cannot substantiate full-data claims**.

## Hard limits

- Does not read TEST at any point. A separate, sealed evaluation command with
  frozen checkpoints is required later for honest held-out testing.
- Requires actual data and strict Stage3 checkpoints **not included** in GitHub.
- Current simulated FL pools client models on one machine; this does **not**
  prove data confidentiality or differential privacy.
- Upstream data harmonization/14-feature selection may already have used
  labels or global data. This code does **not** certify it leakage-free.
- Real group-disjoint, cross-session or cross-device evaluation needs IDs and
  splits grounded in the source datasets.
- Class imbalance, sample count, normalization, rule mining and reward
  differences make historical MSR/FPR and future numbers noncomparable without
  controlled reruns.
