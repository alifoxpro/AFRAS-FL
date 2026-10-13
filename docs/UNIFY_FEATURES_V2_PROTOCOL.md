# Replacement preprocessing: unify_features_v2.py

**New protocol, NOT recovered original code.** The missing historical
\`data/unify_features.py\` cannot be reconstructed or assumed to have the same
feature transformations or five-node topology. This replacement operates only
on real source CSVs you obtain independently. The public GitHub repository
does not include CICIoT2023 or CIC IoT-DIAD 2024 datasets.

Official sources:
- CICIoT2023: https://www.unb.ca/cic/datasets/iotdataset-2023.html
  (original extracted CSV features and complementary source information).
- CIC IoT-DIAD 2024: https://www.unb.ca/cic/datasets/iot-diad-2024.html
  (separate **AD_Flow-based-features** and **DI_AD_Packet-based-features**).
Read the ACTUAL CSV headers; do not assume the same feature labels, capture
times, device IDs or link topology across releases/modalities.

## Initial step — inspect the official ZIP safely

Once access to the university's registration-based download is available,
use the offline ZIP inspector before extracting. It detects original CSV
headers and file checksums, rejects dangerous archive paths and never
invents five physical SDN link IDs. See
[OFFICIAL_CSV_DOWNLOAD_AND_ARCHIVE_PREFLIGHT.md](OFFICIAL_CSV_DOWNLOAD_AND_ARCHIVE_PREFLIGHT.md)
and scripts/data/prepare_official_dataset_archive.py. **No publisher ZIP
has been obtained in this repository.**

## Step A — Get original CSVs from the above university pages

Download them to your own research machine. Keep the original raw ZIP and
all raw CSVs unmodified. Record download URL/revision/sha256 and separately
document any checksum independently published by the dataset provider.
Do not share huge licensed/restricted archives via Git.

## Step B — Inventory original categories and columns

Run per dataset and per modality, specifying the REAL source label column.
The command is a template: placeholders MUST be replaced using raw headers.

\`\`\`bash
python scripts/data/audit_original_csvs.py \
  --dataset ciciot2023 --modality flow \
  --input-dir /actual/CICIoT2023/CSV \
  --label-column ACTUAL_RAW_LABEL_COLUMN \
  --source-artifact /actual/original_archive.zip \
  --output /audit/ciciot_raw_inventory.json
\`\`\`

This inventories actual file SHA-256s, row counts, columns and raw categories,
not a mapping from categories to severity.

## Step C — REVIEW (do not infer) original labels and feature aliases

Create an exhaustive \`afras-raw-label-evidence-v1\` JSON as documented in
\`docs/RAW_LABEL_MAPPING_AND_BINARY_FPR_FNR.md\`. Every actual raw category
must have an explicitly justified \`is_attack\` (0 or 1) AND
\`severity\` (High/Medium/Low). None of these are assigned automatically.
Use the official dataset documentation URL as \`source_url\`; if an
original archive was inventoried, its digest must match \`source_sha256\`.

Create a separate harmonization configuration \`ciciot_v2_config.json\`:

\`\`\`json
{
  "schema": "afras-harmonization-v2-config-v1",
  "dataset": "ciciot2023",
  "modality": "flow",
  "source_review_reference": "REVIEWED_RAW_SCHEMA_DOCUMENT_OR_COMMIT",
  "feature_sources": {
    "feature_example_01": "ACTUAL_RAW_COLUMN_01",
    "feature_example_02": "ACTUAL_RAW_COLUMN_02"
  },
  "link_column": "ACTUAL_MEASURED_NETWORK_LINK_COLUMN",
  "link_values": {
    "ACTUAL_SOURCE_LINK_VALUE_1": "Link_1_Core",
    "ACTUAL_SOURCE_LINK_VALUE_2": "Link_2_Aggregation_L",
    "ACTUAL_SOURCE_LINK_VALUE_3": "Link_3_Aggregation_R",
    "ACTUAL_SOURCE_LINK_VALUE_4": "Link_4_Edge_L",
    "ACTUAL_SOURCE_LINK_VALUE_5": "Link_5_Edge_R"
  },
  "group_column": "ACTUAL_ORIGINAL_CAPTURE_OR_SESSION_COLUMN",
  "time_column": "ACTUAL_ORIGINAL_TIMESTAMP_COLUMN"
}
\`\`\`

The example only shows TWO features for readability: **the actual mapping
requires at least 15 distinct, nonlabel numeric candidate features**.
Only directly equivalent measurements with reviewed unit definitions may be
mapped to the same canonical feature across datasets. No automatic numeric
conversion, target-derived feature, imputation, normalization, label lookup
or feature selection is performed. Group/time fields are optional ONLY if
the source truly lacks them; their absence limits statistical claims.

**Important:** Original CICIoT2023/DIAD2024 CSVs do NOT automatically prove
that the five requested SDN topology links exist. If there is no genuine
source link ID that independently maps to these five roles, the normal
harmonizer FAILS. Inventing such a column or calling fabricated shards real
five-link data would misrepresent the experiment.

## Step D — Harmonize original CSVs into five declared links

After independently checking the original source link column:

\`\`\`bash
python scripts/data/unify_features_v2.py \
  --dataset ciciot2023 \
  --input-dir /actual/CICIoT2023/CSV \
  --inventory /audit/ciciot_raw_inventory.json \
  --label-evidence /reviewed/ciciot_raw_label_evidence.json \
  --config /reviewed/ciciot_v2_config.json \
  --output-root data/full_candidate_5links
\`\`\`

The output is \`data/full_candidate_5links/ciciot2023/\` containing
\`Link_1_Core.csv\` etc and \`harmonization_manifest.json\`.

Every original record is preserved in a deterministic input-file order,
with:
- reviewed numeric candidate features (15 or more, **not** preselected 14);
- original category, explicit reviewed derived binary is_attack, severity;
- \`__afras_original_file\`, \`__afras_original_row\` and original file hash;
- optional original capture/group ID and timestamp;
- SHA-256 manifest for every client file and all configuration/evidence.

The harmonizer streams rows to disk rather than accumulating all features
in memory. It aborts rather than inventing missing/NaN/Infinity values,
unknown labels, impossible source links or unverifiable file hashes.
Destination paths are never overwritten, and failed outputs are not published.
Source-link mapping is still **researcher-declared, NOT independently
authenticated**.

### If original source has NO five-link topology

For **technical exploration only**, remove \`link_column\` and
\`link_values\` from config and run:

\`\`\`bash
python scripts/data/unify_features_v2.py ... --exploratory-synthetic-links
\`\`\`

This creates deterministic round-robin shards with a manifest permanently
tagged \`EXPLORATORY_SYNTHETIC_NONPHYSICAL\`. **These are NOT actual
Core/Aggregation/Edge network devices** and MUST NOT be described as such.
The strict splitter refuses them by default. You may allow tagged pilot
split creation using \`--allow-exploratory-synthetic-links\`, but Stage 3
strict training explicitly rejects that provenance. This prevents a
synthetic 5-way split from being mislabeled as real-world topology evidence.

## Step E — Strict split, TRAIN-only feature selection, Stage 3/4

Only after the real link/group/time policy is scientifically justified:

\`\`\`bash
python scripts/data/split_records_leakfree.py \
  --input-root data/full_candidate_5links \
  --output-root data/full_candidate_strict_split \
  --datasets ciciot2023 \
  --group-column __afras_original_group \
  --time-column __afras_original_time \
  --window-size 20

python scripts/data/select_features_train_only.py \
  --split-root data/full_candidate_strict_split \
  --candidate-json /reviewed/candidate_features.json \
  --datasets ciciot2023 diad2024 \
  --output data/selected_14_train_only.json
\`\`\`

Run the second command **only after BOTH official datasets** are audited,
harmonized and split with compatible candidate columns. For one dataset
choose \`--datasets ciciot2023\` but label its results as single-dataset
TRAIN-only feature selection, not cross-dataset selection.

After that follow \`docs/TRAINING_EXECUTION_PREFLIGHT.md\` and **do not**
open TEST for tuning.

## Scientific limitations remaining

This new tool does **NOT** establish: authentic dataset bytes, the original
historical preprocessing recipe, source-level duplicate/session
independence, true topology link IDs, identical physical meaning of shared
features, unbiased severity assignment, or reproduced original manuscript
metrics. GitHub Actions tests use synthetic CSV fixtures only.

**Paper file \`paper/main.tex\` is untouched.**
