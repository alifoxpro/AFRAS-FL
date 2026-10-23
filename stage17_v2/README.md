# AFRAS-FL V2 — Stage 17 Source-Only Feasibility Pilot

**Status:** Implementation candidate, **NOT EXECUTED** in the current assistant environment. Not a confirmatory experiment. This code was prepared specifically for N-BaIoT V2 and is separate from the repository's historical CICIoT2023/DIAD2024 DQN/MOSAR training.

## Scientific boundaries

This is a bounded debugging pilot. The named **held-out target archive is never opened**, and no target data or target labels are used. Seven source devices train a binary MLP via sample-weighted FedAvg and FedProx, while an eighth *source* device provides diagnostics. That source validation design is exploratory, and not the final 8-training-client LODO design.

**Do not report pilot output as target-device generalization, confirmatory LODO performance, or algorithmic improvement.** The `--max-per-class` cap changes the original prevalence; it is used to manage development resources only. All source-side data are read from native device ZIPs with internal RAR CSVs; no data are bundled.

## Environment

Python 3.10+, numpy, pandas, torch, rarfile, and a system libarchive install discoverable by `ctypes.util.find_library("archive")`. This package has **not** been dependency-pinned or validated on any platform. RAR decompression behavior and resource limits require real-source testing.

## Native files

Put the nine original device ZIP archives in an input directory, named after their canonical device identifiers. The prototype only accesses the **seven training devices plus the one source validation device**. It must not access the held-out target ZIP.

These local ZIPs are source materials obtained by the researcher; external UCI publisher-byte authenticity is not established by executing this script. Review data-use rights separately.

## Example command

```bash
python -m unittest discover -s stage17_v2 -p "test_*.py" -v

python stage17_v2/source_only_pilot.py \
  --source-root /path/to/native_device_zips \
  --heldout Ennio_Doorbell \
  --validation Samsung_SNH_1011_N_Webcam \
  --max-per-class 128 \
  --rounds 3 \
  --local-epochs 1 \
  --batch-size 128 \
  --lr 0.01 \
  --fedprox-mu 0.01 \
  --seed 3107 \
  --output ./stage17_v2_pilot_result.json
```

## Local SHA-256 source integrity preflight (recommended)

Before using real locally staged native N-BaIoT ZIPs, pass the original Stage-13 JSON manifest with exactly nine canonical entries under \`local_archives\`, each providing \`device\`, \`filename\`, and \`local_sha256\`. The pilot recalculates SHA-256 **only for the eight source archives** and rejects any mismatch. The named held-out archive is never opened or hashed:

\`\`\`bash
# Append to the pilot command:
--manifest /path/to/NBaIoT_Nine_Device_Local_File_Manifest_2026-10-23.json
\`\`\`

Manifest validation verifies local archive byte identity against existing local records, **not official UCI publisher-byte provenance**. Do not confuse this with the 89 nested CSV-byte checksum audit. The Stage-13 code-level issue of nine benign CSV header-hash values still needs its targeted data-admission correction.

## Expected output

An output JSON is written only at the end of successful execution. It records held-out exclusion flags, training and source validation device identities, class counts, source-train-fitted transforms, local data subsampling, method-specific source validation diagnostics, and source code checksum.

**All statuses are descriptive assertions of this script's expected control flow; independent testing and a heldout-archive-open sentinel are required before treating target exclusion as verified.**

## Remaining implementation and gate requirements

1. Run unit tests in a Python runtime with pinned dependencies, then verify native RAR/ZIP decoding and resource safety against a small source subset.
2. Run an end-to-end source-only pilot and retain stdout, environment, hashes and output JSON.
3. Fix data-admission/provenance limitations from Stage 13 and secure a defensible Stage 15 originality decision.
4. Replace this exploratory seven-training-client/one-source-validation arrangement with *nested training-side validation, then all eight clients train* in each frozen outer fold.
5. Use **all** original source training examples unless a separate prespecified experiment justifies sampling. The original held-out test folds must retain native prevalence.
6. Freeze the full methods, budgets, seeds and primary comparison **before** any confirmatory held-out predictions.

Original repository main branch is unchanged by this isolated research branch until reviewed and merged.
