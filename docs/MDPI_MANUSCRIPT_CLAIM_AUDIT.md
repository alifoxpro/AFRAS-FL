# AFRAS-FL MDPI manuscript/source claim audit — 2026-10-14

**Scope**: source inspection only of the user-supplied LaTeX ZIP
\`2026-10-01_MDPI_LaTeX_submission(1).zip\`, original \`main.tex\`
SHA-256 \`03f189fd6644e8a5691e1bda00c7a11df9e4c5132160db3b334345b27ab49ba6\`,
and the public Strategy B training code. **No datasets, split manifests, per-seed
raw logs, or genuine trained checkpoints were provided as validation evidence.**
Do not treat reported measurements as reproduced.

## Critical discrepancies that require source artifacts

1. **Conflicting canonical CICIoT2023 B4 numbers**.
   - \`tab:phase_msr\`: MSR=0.9990; FPR=0.0026.
   - \`tab:lambda_ablation\`, supposedly canonical lambda=0.25:
     MSR=0.9995; FPR=0.0143.
   - \`tab:lambda_mu_sweep\`, lambda=0.25 mu=0.10:
     MSR=0.9990; FPR=0.0026.
   These cannot be claimed as the *identical evaluation run/partition* without
   reconciling run IDs, seeds, model hashes, data splits and denominators.
2. **Suspicious duplicate condition results** in \`tab:lambda_mu_sweep\`:
   CICIoT2023 at lambda=0.25 has identical MSR=0.9397, JFI=0.9843,
   FPR=0.0045, reward=0.549 for both mu=0.05 and mu=0.20. Identical
   rounded values are possible; verify raw records rather than alleging fraud.
3. **Inactive mu/link signal in published legacy code**:
   \`StrategyB.py\` method \`_get_neighbor_actions()\` returns \`None\`.
   The link reward cannot support claimed sensitivity to mu in that version.
4. **High/Medium/Low are severity decisions, not self-evident attack labels**:
   original code maps High->BLOCK, Medium->RATE_LIMIT, Low->ALLOW, and computes
   false-block on Low. The manuscript additionally defines High/Medium as
   attack and Low as benign. The supplied archive does not include a verified
   raw-class mapping for both source datasets. Do not call the code's
   severity-based numbers standard IDS FPR/FNR before documenting that mapping.
5. **Source-artifact and leakage-free claims**:
   the manuscript claims release of code, splits and results and a validated
   strict train-only pipeline. The public GitHub repo did not contain the
   purported data, split manifests, raw evaluation logs and checkpoints.
   The newly added strict pipeline is a **different, not yet experimentally
   run** contextual-bandit protocol; do not substitute it for historical
   manuscript results.
6. **PBRS theoretical contradiction**:
   the manuscript asserts the expectation
   E[gamma Phi(s_next) - Phi(s)]=0 under exogenous context sampling.
   For stationary equal-marginal context distributions the expectation is
   (gamma-1) E[Phi], which is not generally zero.
7. **Post-hoc L9**:
   rule-base mitigation was designed after strict TEST FPR inspection.
   The same TEST is therefore development data for L9 and cannot be used
   as an untouched confirmatory test of L9's improvement. Require a NEW holdout.
8. **Statistical interpretation**:
   paper reports five-seed B3 vs B4 p=0.933 (CIC) and p=0.971 (DIAD),
   so no run-level superiority claim is supported. Independent per-seed
   raw vectors are required before independently rechecking p-values.

## Prioritized evidence requirements

1. Original per-link label map \`raw_attack_name -> raw_binary_attack_flag
   -> severity\`, including source dataset version and deterministic script.
2. Split manifests containing row IDs, group/session IDs, seeds, raw hashes
   and withheld TEST seals (not just declared 70/15/15 proportions).
3. Independent five-seed TRAIN logs, VAL metrics, preselected policy checkpoint
   hashes, all three experiment phase versions and a common evaluation schema.
4. Ablation/sweep run registry: dataset, split hash, seed, lambda, mu, model hash,
   commit SHA, independent-run ID, metric denominator and raw confusion counts.
5. An untouched external holdout for L9 or label it strictly exploratory.

## Re-run static audit locally

\`\`\`bash
python scripts/analysis/audit_mdpi_claims.py path/to/main.tex \
  --legacy-strategy-b training/train_rl_multiagent_StrategyB.py \
  --output manuscript_source_audit.json
\`\`\`

This audit is a **consistency/evidence gate**. It cannot verify whether
the historical numbers are true without dataset and experiment artifacts.
