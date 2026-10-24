#!/usr/bin/env python3
"""Verify exactly nine archived original N-BaIoT ZIP *byte identities*.

Standalone standard-library research data admission. Reads *outer ZIP bytes
only*, never opens feature rows, labels, RAR members, or heldout predictions.
An audit receipt is not human authorization; it can support sign-off.

Usage:
 python stage18_v2/verify_original_nine_zip_bytes.py \
   --source-root /secure/original/nine_zip_files \
   --manifest stage18_v2/ORIGINAL_NINE_LOCAL_ZIP_HASH_MANIFEST_2026-10-24.json \
   --receipt /secure/evidence/native_original_zip_admission.json
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()


def validate_original_source_manifest(source_root:Path,manifest_path:Path):
    m=json.loads(manifest_path.read_text(encoding="utf8"))
    if m.get("manifest_schema")!="AFRAS_V2_ORIGINAL_NINE_DEVICE_ZIP_EXPECTED_BYTES_V1":
        raise ValueError("Unknown original device ZIP manifest schema")
    entries=m.get("local_archives")
    if not isinstance(entries,list) or len(entries)!=9:
        raise ValueError("Expected nine audited device ZIP entries")
    seen=set()
    verified=[]
    for entry in entries:
        dev=entry.get("device")
        filename=entry.get("filename")
        exp_sha=entry.get("local_sha256")
        size=entry.get("local_bytes")
        if (not isinstance(dev,str) or not dev
                or dev in seen or filename!=dev+".zip"
                or "/" in filename or "\\" in filename
                or not isinstance(exp_sha,str) or len(exp_sha)!=64
                or any(c not in "0123456789abcdef" for c in exp_sha)
                or not isinstance(size,int) or size<1):
            raise ValueError("Invalid or duplicated audited source entry")
        seen.add(dev)
        path=source_root/filename
        if not path.is_file():
            raise FileNotFoundError("Missing original local source ZIP: "+filename)
        if path.stat().st_size!=size:
            raise ValueError("Original source ZIP byte size differs: "+filename)
        actual=sha256_file(path)
        if actual!=exp_sha:
            raise ValueError("Original source ZIP SHA-256 mismatch: "+filename)
        verified.append({
            "device":dev,"filename":filename,"bytes":size,
            "sha256":actual,"status":"BYTE_IDENTICAL_TO_PRIOR_AUDITED_LOCAL_ORIGINAL",
        })
        print("ORIGINAL_ZIP_BYTES_MATCH",dev,size,flush=True)
    return {
        "status":"ALL_NINE_ORIGINAL_ZIP_BYTES_MATCH_AUDITED_MANIFEST",
        "original_zips_verified":len(verified),
        "original_zips_total_size":sum(x["bytes"] for x in verified),
        "original_source_manifest_sha256":sha256_file(manifest_path),
        "member_decompression_performed":False,
        "heldout_model_predictions_generated":False,
        "human_scientific_approval_created":False,
        "files":verified,
        "limitations":"Byte identity matches earlier user-local archive checks. Public UCI source-member comparisons were separately audited. Does not verify label semantics or grant model-testing authorization."
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root",type=Path,required=True)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--receipt",type=Path,required=True)
    args=parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError("Preserve original admission evidence; no overwrite")
    if not args.source_root.is_dir():
        raise FileNotFoundError("Original nine ZIP directory unavailable")
    result=validate_original_source_manifest(args.source_root,args.manifest)
    args.receipt.parent.mkdir(parents=True,exist_ok=True)
    with args.receipt.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2)
    print("ALL_NINE_ORIGINAL_ZIP_ADMISSION_PASS",result["original_zips_verified"],flush=True)


if __name__=="__main__":
    main()
