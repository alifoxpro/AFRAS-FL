# Step 2 — Original dataset and raw-category audit

**Status: audit tools and synthetic tests only. Original benchmark bytes NOT available in this public GitHub repository.** This document records verified official-source descriptions but does not claim the raw datasets, any per-row mapping, manuscript scores or benchmark splits have been independently validated.

## Official dataset documentation

- CICIoT2023 (University of New Brunswick / Canadian Institute for Cybersecurity): https://www.unb.ca/cic/datasets/iotdataset-2023.html
  - Officially described as 33 malicious attacks across seven families, together with benign traffic; the original release includes CSV features, PCAPs, examples and supplementary code.
  - Do NOT assume that every downloaded CSV variant has the same exact case-sensitive label-column name. Determine it from the authentic header.
- CIC IoT-DIAD 2024 (same institution): https://www.unb.ca/cic/datasets/iot-diad-2024.html
  - The official page documents `AD_Flow-based-features` and `DI_AD_Packet-based-features`, with **different feature sets and labeling conventions**.
  - The flow-based feature list ends with a `Label` field, while the packet-based documentation describes a separate anomaly-detection label (`Label 2 for AD`). Use the ACTUAL original CSV header; do not infer an exact string from the documentation.

**Neither official page specifies this AFRAS-FL project's custom High/Medium/Low severity decisions.** Every original attack category must be mapped to those categories with an explicit, reviewed research protocol; Low does not automatically mean Benign.

## First inventory original data (BEFORE any partition or training)

The researcher must provide authenticated original CSV files from the official download and note the original archive's release identifier and SHA-256. This command scans **local original raw CSVs**, not TRAIN/VAL/TEST and not synthetic or preselected 14-feature CSVs:

```bash
python scripts/data/audit_original_csvs.py \
  --dataset ciciot2023 \
  --modality flow \
  --input-dir /actual/official/CICIoT2023/CSV \
  --label-column ACTUAL_RAW_LABEL_HEADER \
  --source-artifact /actual/official_archive.zip \
  --reference-sha256 VERIFIED_INDEPENDENT_SOURCE_SHA256 \
  --output experiments/source_audit/CICIoT2023_inventory.json
```

For DIAD, change `--dataset diad2024`, input directory and `--modality flow` or `packet`. Scan the modalities **separately** and document which one was used. If no independently verified digest is available, **omit both** `--source-artifact` and `--reference-sha256` or specify only the artifact. A locally computed SHA-256 is NOT independent external validation.

`audit_original_csvs.py` inventories raw headers, category counts, file counts, record counts and SHA-256s. It rejects blank labels, duplicate CSV headers, unknown original label headers, conflicting reference hashes and overwriting an earlier inventory. Its output deliberately sets:

```json
{
  "external_source_authenticity_reviewed": false,
  "severity_mapping_verified": false
}
```

These flags remain false even when a researcher-supplied digest matches.

## Second verify an exhaustive, independently reviewed category mapping

After reviewing the actual label list, create `afras-raw-label-evidence-v1` evidence using the template in [RAW_LABEL_MAPPING_AND_BINARY_FPR_FNR.md](RAW_LABEL_MAPPING_AND_BINARY_FPR_FNR.md). The source URL must be the matching official UNB documentation page; list **every** observed category and an explicit `is_attack=0/1` and `severity=High/Medium/Low` assignment. The source digest must match the inventoried original source archive when supplied.

```bash
python scripts/data/review_raw_category_mapping.py \
  --dataset ciciot2023 \
  --inventory experiments/source_audit/CICIoT2023_inventory.json \
  --mapping /audited/CICIoT2023_raw_label_evidence.json \
  --output experiments/source_audit/CICIoT2023_mapping_review.json
```

The tool **fails closed** when even one observed raw label is omitted, an extra label is invented, a declared source hash disagrees with the measured artifact or a required severity/binary class is missing.

This is a coverage and internal-consistency check only. It does NOT confer authority on the researcher's mapping or derive a Benign flag automatically. DIAD's original `Label` may be multiclass only; where the original archive lacks a binary attack column, generate a derived field **only after** independent mapping review, and preserve the original category + exact source row identifier. The strict downstream `label_evidence.py` requires both fields and will refuse data when the derivation is absent.

## Third preserve and verify end-to-end row lineage

The public repository **does not contain** the original `data/unify_features.py` / raw harmonization script previously referenced by README. Recreating source-to-harmonized data therefore remains BLOCKED until that original code and the original data are supplied and audited.

The eventual harmonization must document: file version and checksum, source row ID, original attack category, reviewed binary attack flag, custom severity decision, all original candidate features, any missingness/imputation, original capture/session/group keys, source time ordering and link assignment rules. It must not silently assign unknown labels to Low. Pre-split feature engineering and near-duplicate cross-link flows are still not audited.

## Scientific interpretation

- The official datasets contain documented malicious/benign categories, but that alone does not validate the paper's original FPR/FNR values or its severity-to-action utility.
- CICIoT2023 and DIAD2024 labels are NOT interchangeable simply because the datasets describe similar attack families.
- The new strict, jointly trained experiments on both datasets cannot be described as DIAD 'unseen zero-shot' evaluation.
- All CI tests here use synthetic CSVs and do NOT constitute a real dataset audit.
- If original raw source artifacts cannot be obtained, disclose the limitation and do not claim reproducibility or validated binary IDS rates from this study.

**Required owner inputs to finish Step 2:** (1) official downloaded raw CSV directory / archive for each benchmark, (2) its source-to-5-link harmonization script or transformation specification, (3) custom original-category -> High/Medium/Low policy with independent review and (4) group/time keys if present.
