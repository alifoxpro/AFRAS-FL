#!/usr/bin/env bash
# Chat27 fixed native data acquisition only. No target fitting or scoring.
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "Usage: bash PREPARE_ROUTE_B_NATIVE_BYTES.sh /secure/work/route_b" >&2
  exit 2
fi
DEST=$(realpath -m "$1")
REPO=${AFRAS_REPO:-$PWD}
mkdir -p "$DEST"
# The original published comparator requires its output root NOT to exist.
# Keep original user-facing location while isolating construction in staging.
BUILD="$DEST/.route_b_build_staging"
for protected in "$BUILD" "$DEST/rebuilt_official_device_archives" \
    "$DEST/PUBLISHER_UCI_NINE_REPACKAGED_ZIPS_CANDIDATE_MANIFEST__NOT_AUTHORIZED.json" \
    "$DEST/uci_original_native_member_comparison_receipt.json"; do
  if [[ -e "$protected" || -L "$protected" ]]; then
    echo "REFUSING REBUILD: existing output requires manual verification: $protected" >&2
    exit 4
  fi
done
[[ -d "$REPO/stage18_v2" ]] || { echo "Set AFRAS_REPO to cloned GitHub repo" >&2; exit 2; }
if [[ ! -f "$DEST/UCI_PUBLIC_ORIGINAL.zip" ]]; then
  curl --fail --location --retry 3 --retry-delay 10 \
    --speed-time 90 --speed-limit 1024 --max-time 1800 \
    -o "$DEST/UCI_PUBLIC_ORIGINAL.zip" \
    'https://archive.ics.uci.edu/static/public/442/detection+of+iot+botnet+attacks+n+baiot.zip'
fi
python - "$DEST/UCI_PUBLIC_ORIGINAL.zip" <<'PYCODE'
import sys, hashlib
from pathlib import Path
p=Path(sys.argv[1]); h=hashlib.sha256()
with p.open("rb") as f:
    while data:=f.read(1<<20): h.update(data)
if h.hexdigest()!="64929678b081d8e579a8d7c488cf11cc588403f282d5fb065b4156edbd55de9b":
    raise SystemExit("UCI STUDY-OBSERVED SOURCE HASH NOT MATCHED")
print("PUBLISHER_UCI_TRANSPORT_STUDY_OBSERVED_SHA_PASS")
PYCODE
python "$REPO/stage18_v2/compare_official_uci_nine_original_archives.py" \
  --official-outer "$DEST/UCI_PUBLIC_ORIGINAL.zip" \
  --historical-original-manifest "$REPO/stage18_v2/ORIGINAL_NINE_LOCAL_ZIP_HASH_MANIFEST_2026-10-24.json" \
  --output-root "$BUILD"
python - "$REPO" "$BUILD" <<'PYCODE'
import sys
from pathlib import Path
repo,build=map(Path,sys.argv[1:])
pinned=repo/"stage18_v2/PUBLISHER_UCI_NINE_ZIPS_CANDIDATE_MANIFEST__NOT_AUTHORIZED.json"
produced=build/"PUBLISHER_UCI_NINE_REPACKAGED_ZIPS_CANDIDATE_MANIFEST__NOT_AUTHORIZED.json"
assert pinned.read_bytes()==produced.read_bytes(),"Candidate manifest differs from reviewed bytes"
sys.path.insert(0,str(repo/"stage18_v2"))
from verify_original_nine_zip_bytes import validate_original_source_manifest
receipt=validate_original_source_manifest(build/"rebuilt_official_device_archives",pinned)
assert receipt["original_zips_verified"]==9
assert receipt["status"]=="ALL_NINE_PUBLISHER_REPACKAGED_CANDIDATE_ZIP_BYTES_MATCH_MANIFEST"
print("NINE_ROUTE_B_BYTES_PASS__NO_HUMAN_AUTHORIZATION_GRANTED")
PYCODE
# Preserve preexisting project source path; fail rather than overwrite partial data.
mv "$BUILD/rebuilt_official_device_archives" "$DEST/rebuilt_official_device_archives"
mv "$BUILD/PUBLISHER_UCI_NINE_REPACKAGED_ZIPS_CANDIDATE_MANIFEST__NOT_AUTHORIZED.json" \
   "$DEST/PUBLISHER_UCI_NINE_REPACKAGED_ZIPS_CANDIDATE_MANIFEST__NOT_AUTHORIZED.json"
mv "$BUILD/uci_original_native_member_comparison_receipt.json" \
   "$DEST/uci_original_native_member_comparison_receipt.json"
rmdir "$BUILD"
echo "ROUTE_B_NINE_ARCHIVES_READY__NOT_HUMAN_AUTHORIZATION"
echo "SOURCE_ROOT=$DEST/rebuilt_official_device_archives"
