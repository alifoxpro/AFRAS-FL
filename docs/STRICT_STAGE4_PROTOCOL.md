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
- **Stage 4 v2** no longer uses the historical seven-phase AFRASFLPipeline.
  The legacy training rule pipeline normalized/denoised TRAIN inputs a second
  time, but rule inference used the original state coordinates: a feature-scale
  mismatch that can distort ALLOW/RATE_LIMIT/BLOCK actions.
- A NEW deterministic nine-cell Gaussian fuzzy rule bank is instead fitted
  on only the first two Stage 3 TRAIN-standardized state means, and these
  exact coordinates are passed to inference. No additional normalization,
  wavelet, NURBS-SMOTE or VAL/TEST rule mining is performed. It must NEVER
  be described as reproduction of the full historical seven-phase method.
- Independent B2 FedAvg, B3 FedProx, B4 FedProx + action-dependent fuzzy
  rewards start from the same seeded Q-network initialization. Their
  respective best rounds are selected using **VAL only**.
  FedAvg checks positive integer sample counts and identical finite tensor
  names, shapes, dtypes and devices, with sample-weighted float64 accumulation.
  FedProx penalizes local deviation from the frozen global parameters.
  These are code-level invariants, NOT claims of secure aggregation or privacy.
- Rewards are fully specified in strict_fed_core.py. Latency is an assumed
  action-cost **proxy**, not measured milliseconds. Teacher confidence and
  accuracy terms are action-independent within each state, so they cannot
  separately alter the preferred action; they are NOT evidence of five
  independently optimized action objectives.
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
- Every run creates fresh output experiments/strict_stage4/<dataset>/seed_<seed>
  and refuses overwrites. The v2 schema, source matching and SHA-pinned
  per-client TRAIN_RULES.json keep legacy/v1/v2 rules from being mixed.

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
