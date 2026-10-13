# Source-aware label mapping and binary IDS rates — audit step

## Status

Code only; benchmark source CSVs and independently authenticated raw labels
are not available in the public GitHub repository. This step does not
assert that CICIoT2023/DIAD2024 category annotations were verified.

Old code mapped unknown raw `severity` strings silently to Low:
`SEV_MAP.get(s, 2)`. It now raises an exception on unknown severity.

## Why prior FPR/FNR cannot yet be trusted

The legacy reward evaluation uses High -> BLOCK, Medium -> RATE_LIMIT,
Low -> ALLOW. It calls blocking Low a false positive and allowing High
a false negative. That is NOT conventional binary intrusion detection
unless a raw Benign/Attack class mapping supports those denominators.

Under the NEW strict pipeline, severity-action errors are kept separate
from binary FPR/FNR. To enable real binary counts, prepare a REVIEWED,
predeclared mapping document containing ALL of:

- `schema`: `afras-raw-label-evidence-v1`
- `dataset`: ciciot2023 or diad2024
- `source_url`: actual HTTPS reference to original benchmark dataset
- `source_revision`: original raw benchmark release / data revision
- `source_sha256`: real 64-character SHA-256 of source file/archive
- `mapping_review_reference`: traceable review note or upstream code commit
- `raw_label_column`: EXACT column retaining original category name
- `binary_attack_column`: EXACT original 0=Benign / 1=Attack flag
- `raw_label_map`: EXHAUSTIVE object, each category mapped to an explicit
  `{severity: High|Medium|Low, is_attack: 0|1}` based on original labels

Template (not real evidence; do NOT copy its example values into results):

    {
      "schema": "afras-raw-label-evidence-v1",
      "dataset": "ciciot2023",
      "source_url": "https://ORIGINAL-DATASET-REFERENCE",
      "source_revision": "ORIGINAL-RELEASE-ID",
      "source_sha256": "ACTUAL_64_CHARACTER_SHA256",
      "mapping_review_reference": "REVIEWED_MAPPING_SCRIPT_OR_CITATION",
      "raw_label_column": "ORIGINAL_CATEGORY_COLUMN_NAME",
      "binary_attack_column": "ORIGINAL_0_OR_1_ATTACK_COLUMN_NAME",
      "raw_label_map": { "RAW_CATEGORY_NAME": {"severity": "High", "is_attack": 1} }
    }

Split CSVs also MUST retain the raw label column and original binary flag
(in addition to `severity` and `__afras_source_row_id`). If those columns
were dropped by upstream harmonization, do not reconstruct or infer them
from severity. Instead regenerate data from authenticated source labels.

## Protocol for newly trained Stage 4 models

Before opening TEST, audit every TRAIN and VAL record. The evidence file
checksum is frozen in Stage 4 run provenance. Example:

    python scripts/training/train_federated_strict.py --dataset ciciot2023 --label-evidence /verified/ciciot-label-map.json --mu-link 0

Then, only AFTER all training and tuning is frozen:

    python scripts/evaluation/evaluate_strict_test.py --dataset ciciot2023 --seed 42 --label-evidence /verified/ciciot-label-map.json --unseal-test

The guard fails if an evidence file was added after Stage 4 or its SHA
changes. If no preregistered evidence exists, the strict evaluator does
not compute binary FPR/FNR: it reports severity-action metrics only.

## Binary attack decision policy

- Prediction = benign for ALLOW (action 0).
- Prediction = attack for RATE_LIMIT (1) or BLOCK (2).
- TP = attacks rate-limited/blocked.
- FN = attacks allowed.
- FP = benign events rate-limited/blocked.
- TN = benign events allowed.
- FPR = FP / (FP + TN), FNR = FN / (FN + TP).
- Missing positive or negative denominators yield `null` (undefined).
- For each TEST window, the original binary label of the LAST record
  is used, consistent with `create_windows` end-of-window severity.

These are classification decision metrics, not an estimate of real-world
blocking costs, precision of threat triage or measured network latency.

## Outstanding scientific limitations

1. Matching self-declared CSV columns to a self-declared mapping checks
   internal consistency, **not authenticity**: independently audit
   transformation from original raw dataset labels and source SHA.
2. Split ordering, duplicates, feature-selection leakage and group overlaps
   must be checked separately.
3. Stage 4 and test paths are NEW contextual-bandit experiment protocols,
   not an independent reproduction of the historical manuscript.
4. Do not re-use the same TEST to adjust the category mapping, thresholds
   or decision policy after inspecting the results.
