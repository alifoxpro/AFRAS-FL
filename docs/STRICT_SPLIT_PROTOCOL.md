# Step 2 — Pre-window split and leakage safeguards

This is a **source-only implementation**. No experiments have been rerun and no MDPI scores are verified.

The new \`scripts/data/split_records_leakfree.py\` produces **ordered** partitions (70/15/15 of usable rows), with a \`window_size-1\` embargo between partitions. It writes \`manifest.json\` recording source SHA-256, counts, source row ranges, class counts, split-file checksums, group/time checks, and limitations. It refuses to overwrite outputs. Splitting occurs **before** windows, not after.

For every dataset's per-link CSVs under \`data/unified_14features_5links/<dataset>/Link_*.csv\`:

\`\`\`bash
python scripts/data/split_records_leakfree.py --datasets ciciot2023 diad2024 --window-size 20
python -m unittest discover -s tests -p 'test_split_records.py' -v
\`\`\`

**Important conditions and restrictions:**
- The source rows must already be ordered in a defensible sequence. With \`--time-column event_time\`, the script verifies nondecreasing timestamps, but DOES NOT sort or fabricate chronology.
- For genuine device/session/campaign disjointness, provide \`--group-column <column>\`. The script will **fail** if any group straddles partitions. It does not silently shuffle groups, so contiguous sequence semantics remain under the user's control.
- If the provided unified CSVs lack a stable time or group ID, their absence **must be disclosed**. This script does not establish end-to-end group-disjointness by itself.
- **Do not run the existing \`train_isolated.py\`, \`StrategyA.py\`, or \`StrategyB.py\` on these files as though the full pipeline is now leakage-free.** Those scripts still have train-wide feature fitting / teacher-cache and evaluation reuse issues. A separate, split-aware Stage 3 Mamba training + Stage 4 strictly held-out evaluation implementation is required.
- Never reuse prior Mamba checkpoints, cached \`.npy\` outputs, PCA, feature selectors, fuzzy rules, normalization state or RL checkpoints from unsplit data.
- TEST must not be used to select model configurations, tune mitigation rules, or fit any preprocessing.
- Group keys and time keys can differ across official datasets; determine them from the real source files, not guesses.
