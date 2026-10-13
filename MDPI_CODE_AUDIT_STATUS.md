# MDPI scientific-code audit — patch v1 (not a validated experiment)

This branch is **for review**, not a claim that any published metric has been reproduced. Starting point: upstream commit `8d4ac7e62219e5916a554f987f4582977b0abacc`.

## Included changes
- Correct repository-root paths in training scripts and experiment launchers.
- Use the dataset's end-of-window `severity` labels for DQN training/evaluation instead of the Mamba classifier's `argmax` pseudo-labels. The separate **B0 rule-mining stage continues to use teacher pseudo-labels**; its scientific suitability still needs review.
- Validate window/cache lengths (but not row-by-row identity, hashes, or data-split provenance).
- Refuse to resume old checkpoints when label provenance is unknown, to avoid silently mixing old and corrected results. Run with a fresh `--suffix`.
- Refuse `MU_LINK != 0` because `_get_neighbor_actions()` currently returns `None`; **this is a fail-fast safeguard, not a neighbor coordination implementation**. The current default `--mu-link 0.10` therefore now *intentionally fails*. Use `--mu-link 0` only for an explicitly link-disabled diagnostic; those results are NOT comparable to claimed full-model results.
- Seed the Python `random` RNG alongside NumPy/PyTorch.

## Still NOT corrected or verified
1. **Training-data leakage**: data must be partitioned at record/group level *before* windows, feature fitting, PCA, Mamba scoring, fuzzy mining and evaluation. A fresh untouched held-out TEST set is required.
2. The dataset-to-`severity` mapping, benign/attack semantics and reported FPR/FNR must be verified against original labels. An action-versus-severity match is **not** the same as binary intrusion detection accuracy.
3. The independent PBRS baseline, action-dependent fuzzy shaping claims, and the federated neighbor-action mechanism require new implementation and experiments.
4. Configuration and seed provenance, row-level cache alignment, independent evaluation and unbiased reruns are missing.
5. The repository has no committed source datasets, split manifests, raw results or model checkpoints. No full training, inference, GPU run or metric reconciliation was performed in this patch.
6. Existing README and reviewer experiment commands still refer to some missing paths/scripts; those instructions are not end-to-end executable until reconciled.

**Do not update MDPI tables or claim improved scores from this source-only patch.**
