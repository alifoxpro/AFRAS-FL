# Official CICIoT2023 and CIC IoT-DIAD 2024 acquisition

Status: Official benchmark ZIPs have NOT been downloaded or run here. The
University of New Brunswick (CIC) distribution requires the researcher's
individual access through a registration form. No registration is bypassed,
no personal data is collected and no third-party mirror is silently substituted.

## Official University source pages

- CICIoT2023: https://www.unb.ca/cic/datasets/iotdataset-2023.html
- CIC IoT-DIAD 2024: https://www.unb.ca/cic/datasets/iot-diad-2024.html

The official Download links lead to university registration forms:
- https://cicresearch.ca/IOTDataset/CIC_IOT_Dataset2023/
- https://cicresearch.ca/IOTDataset/CIC-IoT-IDAD-Dataset-2024/

When checked anonymously on 2026-10-14, these forms returned
"Server error. Please try again later." This might be temporary.
Researchers should complete the forms themselves when functional.

## Local Windows workflow after authorized ZIP download

Save the original ZIP unmodified to your local disk and use PowerShell
from the AFRAS-FL repository folder. First list the ZIP directories:

    python -m zipfile -l "D:\Datasets\CICIoT2023.zip"

Inspect original CSV headers and generate a SHA-256 inventory, WITHOUT extraction:

    python scripts/data/prepare_official_dataset_archive.py ^
      --dataset ciciot2023 --modality flow ^
      --archive "D:\Datasets\CICIoT2023.zip" ^
      --csv-prefix CSV ^
      --report "D:\AFRAS_Audit\CICIoT2023_zip_report.json"

For PowerShell, write this as ONE line rather than using the above Windows
cmd.exe line-continuation character ^. The CSV directory prefix is an
EXAMPLE, not a guaranteed root directory name. Use the ZIP listing to
choose the exact prefix. If only one CSV schema is in the archive,
omit --csv-prefix.

Inspect original_csv_headers in the JSON report. Then extract, after
replacing ACTUAL_LABEL_COLUMN by the exact original header:

    python scripts/data/prepare_official_dataset_archive.py --dataset ciciot2023 --modality flow --archive "D:\Datasets\CICIoT2023.zip" --csv-prefix CSV --label-column ACTUAL_LABEL_COLUMN --extract --output-root "D:\Datasets\AFRAS_Official_CSV" --report "D:\AFRAS_Audit\CICIoT2023_extracted_report.json"

Extraction writes into .../AFRAS_Official_CSV/ciciot2023/flow and
preserves original inner ZIP directories. The script bounds uncompressed
size, prevents ZIP-slip, rejects unsafe symlinks, duplicate paths,
mismatching/ambiguous CSV headers and overwriting earlier outputs.

DIAD2024 has SEPARATE AD_Flow-based-features (Flow) and
DI_AD_Packet-based-features (Packet) files and feature schemas. Repeat
the commands with --dataset diad2024 and choose an explicit original
CSV folder for --csv-prefix. DO NOT merge different modalities.

## Required next evidence and constraints

1. Inventory extracted raw files using scripts/data/audit_original_csvs.py.
2. Check all original categories and build an independently justified
   raw label -> binary Attack/Benign -> High/Medium/Low severity mapping
   using scripts/data/review_raw_category_mapping.py.
3. Check original feature-unit equivalence BETWEEN datasets. Do not
   infer it based on similar names; the released feature sets differ.
4. Produce an explicit reviewed source link ID mapping if real physical
   SDN links exist. The original benchmark CSVs do NOT automatically
   demonstrate five distinct Core/Aggregation/Edge controller links.
5. Only with verified original columns and their provenance, run
   scripts/data/unify_features_v2.py and later strict TRAIN/VAL/TEST.

WARNING: a locally computed or operator-supplied SHA-256 records file
identity but does not independently prove publisher authenticity.
The original ZIP must remain outside public GitHub. No old manuscript
metrics are revalidated by this scanner. paper/main.tex remains untouched.
