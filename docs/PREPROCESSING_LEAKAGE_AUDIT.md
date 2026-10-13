# Step 1 — Audit and repair: Preprocessing, feature selection and leakage

## Status (source code only)

New TRAIN-only feature selection, split-hash validation, metadata exclusion
and cross-client group-disjoint checking are implemented on the audit branch.
GitHub CI uses SYNTHETIC CSVs only. No original CICIoT2023/DIAD2024
datasets, raw harmonization code, group IDs, or original training outputs
have been audited. Therefore we DO NOT certify the paper leakage-free.

## Confirmed risks in historical upstream code

1. `analysis/xai_unified_selection.py`: loads samples from the five
   unified CSVs before split, fits the XGBoost baseline on the complete
   sampled dataset, computes SHAP/LIME across this data and emits
   `unified_selected_14.json`. Use of this file for TEST assessment risks
   supervised feature-selection leakage. The old XAI feature list is NOT
   accepted by the NEW strict Stage 3/4/TEST scripts.
2. `training/train_top3_models.py`: shuffles source rows, normalizes all
   records with StandardScaler.fit_transform before splitting, and
   splits after creating windows. This is not a temporal or group
   independent evaluation. The historical path must be treated as legacy.
3. `training/train_isolated.py`: creates windows before the random
   train/val/test split. Although later scaling fits on TRAIN windows,
   windows can overlap across partitions if stride/window settings
   change and sessions may be shared. Use the strict split FIRST.
4. `analysis/profile_a3_severity.py` and `analysis/profile_a6_dirichlet.py`
   fit StandardScaler/PCA on broadly pooled data and are not independent
   untouched-TEST evaluations. Their outputs cannot establish causal
   improvement without split-aware reruns.
5. The public README references `data/unify_features.py`, yet this raw
   harmonization script and the actual unified CSVs are NOT included in
   the public repository. Exact source->severity/feature lineage, any
   pre-split imputation, and exact duplicate flows remain unverified.


IMPORTANT: The default historical input path `data/unified_14features_5links/`
contains already-selected 14-feature CSVs. Splitting these records alone
CANNOT undo prior supervised feature-selection leakage. The TRAIN-only
selector deliberately requires at least 15 candidate columns and will
fail on the old preselected 14-column data. Regenerate a complete
unselected candidate pool from authenticated upstream raw sources first.

## Required reviewed candidate list

After confirming original dataset schemas, independently review and
provide a JSON FILE of at least 15 previously UNSELECTED common numeric feature names:

    {
      "schema": "afras-candidate-feature-review-v1",
      "review_reference": "ORIGINAL-SCHEMA-REVIEW-AND-COMMIT",
      "candidate_features": ["FEATURE_NAME_1", "...", "FEATURE_NAME_20"]
    }

The example is NOT an actual candidate list. Use real audited column names
from source TRAIN headers. Do not include raw class/severity, label,
attack/benign, time, device/group/session identifiers, IP addresses or
derived target metadata. The selector fail-closes common risky names, but
this is not proof that other features are nonleaking.

## Ordered experiment workflow (no real data run has occurred)

1. Recreate verifiable harmonized, ordered per-link CSVs from the
   authenticated raw benchmarks. Preserve raw labels, traceable row IDs
   and genuine group/session identifiers.
2. Run record-level split before fitting transforms or windows:

    python scripts/data/split_records_leakfree.py --input-root /verified/UNSELECTED_FULL_CANDIDATE_5LINK_CSVS --output-root data/full_candidate_strict_split --datasets ciciot2023 diad2024 --group-column SESSION_ID --time-column TIMESTAMP_COLUMN --window-size 20

   Replace SESSION_ID and TIMESTAMP_COLUMN with ACTUAL verified names.
   The splitter now checks each declared group ACROSS ALL FIVE CLIENT
   LINKS. If a group is present in different partitions, it refuses
   to create the split. The split does not independently verify raw
   session IDs nor cross-dataset duplicates.
3. Run NEW TRAIN-only feature selection, after split:

    python scripts/data/select_features_train_only.py --split-root data/full_candidate_strict_split --candidate-json /reviewed/candidate_features.json --datasets ciciot2023 diad2024 --n-features 14

   The output `data/selected_14_train_only.json` contains the TRAIN-only
   supervised ANOVA ranking, per-dataset ranks, source split-manifest
   SHA-256, candidate-list SHA-256 and TRAIN partition SHA-256s.
   It never reads VAL or TEST CSVs. This is not a SHAP/LIME re-run.
4. Train Stage 3 from TRAIN and select by VAL:

    python scripts/training/train_mamba_strict.py --split-root data/full_candidate_strict_split --dataset ciciot2023 --seed 42

5. Train Stage 4 with the same pinned features, TRAIN-only rules and
   validation-only selected policies:

    python scripts/training/train_federated_strict.py --split-root data/full_candidate_strict_split --dataset ciciot2023 --mu-link 0 --seed 42

6. Before a one-time TEST, independently audit group/session disjointness,
   missing preprocessing transformations, raw attack/benign annotations
   and missing/duplicate flows. Only then unseal TEST as described in
   `docs/STRICT_TEST_EVALUATION_PROTOCOL.md`.

### Experimental-design warning

Selecting features using TRAIN from both CICIoT2023 and DIAD2024 is a
NEW **joint-training** design. It is NOT valid to subsequently call
DIAD2024 'entirely unseen' or 'zero-shot OOD'. For an actual unseen
DIAD benchmark, feature choice, normalization and model training must
be locked using CICIoT2023 TRAIN only, before touching DIAD labels;
a distinct transfer-evaluation pipeline is needed (not yet implemented).

### What remains unverified

- Source-row chronological ordering, authenticated session/group IDs.
- Cross-link and cross-dataset duplicates/near-duplicates not sharing IDs.
- Source raw category->binary attack->severity mapping correctness.
- Pre-split harmonization/derived features, label contamination, XAI validity.
- Any reproducible trained-model metrics, confidence intervals or manuscript results.

**Do not treat CI success as experimental verification.**
