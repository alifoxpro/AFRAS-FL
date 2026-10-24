#!/usr/bin/env python3
"""Chat18: independently compare official public UCI N-BaIoT member bytes with
the historical nine locally-audited original ZIP wrappers.

This tool is DATA ADMISSION RESEARCH ONLY. It never loads native feature rows
or labels for modeling, fits any model, scores a heldout fold or grants any
person's scientific approval.

Important: byte-identical original CSV/RAR members can be repacked into
different ZIP wrapper bytes. Therefore outer ZIP equality is explicitly
reported SEPARATELY from native-member extraction/identity and must NEVER be
fabricated from filename or ZIP length.

The official transport SHA is a previously observed study-specific digest,
NOT an official publisher-published checksum.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import shutil
import sys
import os

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"stage17_v2"))
from prepare_uci_public_sources import (
    desired_members,find_unique_members,sha256_file
)
from source_only_pilot import DEVICES

PREVIOUS_OBSERVED_OUTER_SHA="64929678b081d8e579a8d7c488cf11cc588403f282d5fb065b4156edbd55de9b"

def do_compare(official_outer:Path,expected_manifest:Path,output_root:Path):
    if not official_outer.is_file():
        raise FileNotFoundError("Official UCI dataset transport unavailable")
    if not expected_manifest.is_file():
        raise FileNotFoundError("Historical audited local manifest unavailable")
    if output_root.exists():
        raise FileExistsError("No overwrite of original-data receipt/output directory")
    prior=json.loads(expected_manifest.read_text(encoding="utf8"))
    records=prior.get("local_archives",[])
    if (prior.get("manifest_schema")!="AFRAS_V2_ORIGINAL_NINE_DEVICE_ZIP_EXPECTED_BYTES_V1"
            or len(records)!=9 or [x.get("device") for x in records]!=list(DEVICES)):
        raise ValueError("Expected canonical original nine archive manifest")
    for x in records:
        if x["filename"]!=x["device"]+".zip" or not isinstance(x["local_bytes"],int):
            raise ValueError("Invalid historical research filename/size")
        if len(x.get("local_sha256",""))!=64:
            raise ValueError("Invalid expected outer-wrapper SHA")
    outer_sha=sha256_file(official_outer)
    if outer_sha!=PREVIOUS_OBSERVED_OUTER_SHA:
        raise ValueError("Downloaded UCI package differs from already source-audited official transport")
    output_root.mkdir(parents=True,exist_ok=False)
    build_root=output_root/"rebuilt_official_device_archives"
    build_root.mkdir()
    reports=[]
    with zipfile.ZipFile(official_outer,"r") as source:
        members=find_unique_members(source,DEVICES)
        if len(members)!=25:
            raise ValueError("Native N-BaIoT original 25 device CSV/RAR members missing")
        for entry in records:
            dev=entry["device"]
            outpath=build_root/(dev+".zip")
            copied=[]
            # Exactly mirror Stage17's existing source-only packaging, including
            # stored member compression choice, Zip64 and member naming.
            with zipfile.ZipFile(outpath,mode="x",compression=zipfile.ZIP_STORED,
                                 allowZip64=True) as reconstructed:
                for local in desired_members(dev):
                    remote=members[local]
                    h=hashlib.sha256()
                    read=0
                    with source.open(remote,"r") as src:
                        with reconstructed.open(local,mode="w",force_zip64=True) as dst:
                            while chunk:=src.read(1<<20):
                                h.update(chunk)
                                read+=len(chunk)
                                dst.write(chunk)
                    if read!=source.getinfo(remote).file_size:
                        raise ValueError("Native member extraction incomplete: "+remote)
                    copied.append({
                        "name":local,"source_member_path":remote,
                        "source_member_bytes":read,
                        "source_member_sha256":h.hexdigest()
                    })
            digest=sha256_file(outpath)
            size=outpath.stat().st_size
            # Honest distinction: the same inner member bytes do NOT imply
            # byte identity of a ZIP wrapper with a different timestamp/encoding.
            same=(digest==entry["local_sha256"] and size==entry["local_bytes"])
            reports.append({
                "device":dev,
                "expected_previous_local_zip_sha256":entry["local_sha256"],
                "expected_previous_local_zip_bytes":entry["local_bytes"],
                "reconstructed_official_zip_sha256":digest,
                "reconstructed_official_zip_bytes":size,
                "outer_zip_byte_identical_to_previous_local_audit":same,
                "native_members_from_official_transport":copied,
                "native_member_count":len(copied),
            })
            print("UCI_ORIGINAL_DEVICE_MEMBER_PROVENANCE",dev,
                  "members",len(copied),"outer_sha_matches_prior",same,flush=True)
    out={
        "status":"OFFICIAL_UCI_25_NATIVE_MEMBERS_RECONSTRUCTED_AND_HASHED__NOT_HUMAN_AUTHORIZATION",
        "official_dataset":"UCI N-BaIoT DOI:10.24432/C5RC8J",
        "downloaded_original_transport_sha256":outer_sha,
        "transport_comparison":"MATCHES_PREVIOUSLY_OBSERVED_TRANSPORT_SHA__NOT_PUBLISHER_SIGNATURE",
        "expected_research_local_manifest_sha256":sha256_file(expected_manifest),
        "official_native_device_count":len(reports),
        "official_native_member_count":sum(r["native_member_count"] for r in reports),
        "historical_outer_zip_exact_matches":sum(r["outer_zip_byte_identical_to_previous_local_audit"] for r in reports),
        "all_historical_local_zip_wrappers_reproduced_byte_identically":all(
            r["outer_zip_byte_identical_to_previous_local_audit"] for r in reports),
        "current_user_Library_zip_bytes_read":False,
        "full_nine_local_zip_admission_of_user_library_bytes":False,
        "actual_native_test_rows_scored":0,
        "research_authorization_granted":False,
        "caution":"Public publisher transport/inner members were independently downloaded and checked; current user's original nine Library ZIP bytes were NOT available to this GitHub workflow. Packaging SHA differences are not necessarily member-content differences.",
        "reconstructed_device_reports":reports
    }
    receipt=output_root/"uci_original_native_member_comparison_receipt.json"
    receipt.write_text(json.dumps(out,indent=2),encoding="utf8")
    print("OFFICIAL_UCI_25_NATIVE_MEMBERS_CHECKED",
          out["official_native_member_count"],
          "OUTER_WRAPPER_EQUALITY",out["historical_outer_zip_exact_matches"],"/9",flush=True)
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-outer",required=True,type=Path)
    p.add_argument("--historical-original-manifest",required=True,type=Path)
    p.add_argument("--output-root",required=True,type=Path)
    args=p.parse_args()
    do_compare(args.official_outer,args.historical_original_manifest,args.output_root)

if __name__=="__main__":
    main()
