#!/usr/bin/env python3
"""AFRAS-FL V2 pre-result nested exact feature exposure audit.

Only run AFTER all 54 native heldout runs have been authorized, completed
and independently replayed. Builds a digest-only SQLite source-availability
index from all nine original ZIPs once. It never trains/fits/chooses thresholds
or passes full-corpus membership into any model.

Mutually exclusive observational strata for a heldout target record:
  trained_exact       exact 115D vector in its actual 8*30000 source sample
  available_not_used  absent from sampled source but somewhere in eight full
                      original source corpora
  unavailable         absent from all eight original nonheldout corpora
"""
from __future__ import annotations
import argparse
import csv
import gzip
import json
from pathlib import Path
import sqlite3
import sys
import hashlib
import math

from independent_device_paired_analysis import (
    CANONICAL_DEVICES, full_plan_tasks, verify_one, sha
)
from training_exposure_strata import (
    LABELS, PRED, NA, valid_digest, training_fingerprints
)

ROOT=Path(__file__).resolve().parent.parent
STRATA=("trained_exact","available_not_used","unavailable")


def create_digest_index(path:Path):
    """SQLite fixed-width exact vector hash index; no source feature vectors."""
    if path.exists():
        raise FileExistsError("Refuse preexisting feature membership database")
    path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(str(path))
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("PRAGMA synchronous=FULL")
    con.execute("CREATE TABLE vectors (digest BLOB PRIMARY KEY, device_mask INTEGER NOT NULL) WITHOUT ROWID")
    con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return con


def add_device_fingerprints(con,device_index:int,digests):
    """Upsert original-device bitmask; repetitions within a device do not add devices."""
    if device_index not in range(9):
        raise ValueError("Unknown device index")
    mask=1<<device_index
    unique=set(digests)
    if any(not isinstance(d,bytes) or len(d)!=16 for d in unique):
        raise ValueError("Require canonical 16-byte BLAKE2b-128 digests")
    con.executemany(
        "INSERT INTO vectors(digest,device_mask) VALUES(?,?) "
        "ON CONFLICT(digest) DO UPDATE SET "
        "device_mask=(vectors.device_mask | excluded.device_mask)",
        ((sqlite3.Binary(d),mask) for d in unique)
    )
    return len(unique)


def classify(mask:int,target_index:int,actually_trained:bool):
    """Tests exclude the heldout device itself even if it has the same vector."""
    if target_index not in range(9) or not isinstance(mask,int) or mask<0:
        raise ValueError("Bad target/source device membership mask")
    original_source_available=bool(mask & ~(1<<target_index))
    if actually_trained and not original_source_available:
        raise ValueError("Trained source vector missing from full source corpus")
    if actually_trained:
        return "trained_exact"
    if original_source_available:
        return "available_not_used"
    return "unavailable"


def original_vector_digests(X):
    """IDENTICAL raw-float64 signed-zero digest convention to Stage18."""
    import numpy as np
    if X.ndim!=2 or X.shape[1]!=115 or not np.isfinite(X).all():
        raise ValueError("Bad original 115D original source numeric features")
    values=np.asarray(X,dtype="<f8",order="C").copy()
    values[values==0.0]=0.0
    return [
        hashlib.blake2b(row.tobytes(),digest_size=16).digest()
        for row in values
    ]


def build_from_original_nine(con,original_root:Path,manifest:Path,inventory:Path):
    """Audit raw original ZIP bytes again before reading all 25 native members.

    This touches all nine original corpora ONLY AFTER all 54 model fits; it
    does not expose target vectors/membership to the model or hyperparameters.
    """
    sys.path.insert(0,str(ROOT/"stage17_v2"))
    sys.path.insert(0,str(ROOT/"stage18_v2"))
    import pandas as pd
    import numpy as np
    import source_only_pilot as native
    import verify_original_nine_zip_bytes as auditor
    import replay_predictions as independent
    receipt=auditor.validate_original_source_manifest(original_root,manifest)
    if receipt["original_zips_verified"]!=9:
        raise ValueError("Native original ZIP admission incomplete")
    expected_header=None
    all_rows=0
    result={}
    for index,dev in enumerate(CANONICAL_DEVICES):
        expected_support=independent.native_expected(inventory,dev)
        found={k:0 for k in expected_support}
        for cls,source in native.iter_native_csv(original_root,dev):
            for frame in pd.read_csv(source,dtype=np.float64,
                                     chunksize=native.CSV_CHUNK,on_bad_lines="error"):
                header=list(frame.columns)
                if len(header)!=115 or (expected_header is not None and
                                       header!=expected_header):
                    raise ValueError("Unexpected original feature header")
                if expected_header is None:
                    expected_header=header
                values=frame.to_numpy(dtype=np.float64,copy=False)
                digests=original_vector_digests(values)
                add_device_fingerprints(con,index,digests)
                found[cls]+=len(values)
        if found!=expected_support:
            raise ValueError("Original class support mismatch during availability census: "+dev)
        con.commit()
        all_rows+=sum(found.values())
        result[dev]={"original_rows":sum(found.values()),
                     "native_class_support":found}
        print("FULL_SOURCE_FEATURE_AVAILABILITY_DEVICE_SCANNED",
              dev,result[dev]["original_rows"],flush=True)
    if all_rows!=7062606:
        raise ValueError("Original nine N-BaIoT rows differ from audited total")
    con.execute("INSERT INTO meta(key,value) VALUES('original_row_count',?)",(str(all_rows),))
    con.execute("INSERT INTO meta(key,value) VALUES('original_nine_manifest_sha256',?)",
                (sha(manifest),))
    con.commit()
    return receipt,result


def study_one_target(pred:Path,device:str,bank:set[str],source_index):
    """Compute denominator-safe classwise THREE-group full-source contrast."""
    device_ix=CANONICAL_DEVICES.index(device)
    cur=source_index.cursor()
    counts={c:0 for c in LABELS}
    values={c:{grp:{"support":0,"attack_predictions":0}
               for grp in STRATA} for c in LABELS}
    with gzip.open(pred,"rt",encoding="utf8",newline="") as file:
        rd=csv.DictReader(file)
        if tuple(rd.fieldnames or ())!=PRED:
            raise ValueError("Original heldout prediction file has incorrect header")
        for row in rd:
            cls=row["attack_class"]
            if row["device"]!=device or cls not in counts:
                raise ValueError("Unrecognized target device/class")
            if int(row["source_row_index"])!=counts[cls]:
                raise ValueError("Original row ID missing, duplicated or not ordered")
            if int(row["y_true"])!=int(cls!="benign"):
                raise ValueError("Original native binary label/source class mismatch")
            dig=row["feature_digest"]
            if not valid_digest(dig):
                raise ValueError("Invalid canonical original 115D digest")
            prob=float(row["attack_probability"])
            if not math.isfinite(prob) or not 0<=prob<=1:
                raise ValueError("Bad original target model probability")
            lookup=cur.execute("SELECT device_mask FROM vectors WHERE digest=?",
                               (bytes.fromhex(dig),)).fetchone()
            mask=lookup[0] if lookup else 0
            grp=classify(mask,device_ix,dig in bank)
            values[cls][grp]["support"]+=1
            values[cls][grp]["attack_predictions"]+=int(prob>=0.5)
            counts[cls]+=1
    out={}
    for cls in LABELS:
        groups=values[cls]
        out[cls]={
            "original_target_support":counts[cls],
            "native_rate_type":"BENIGN_FPR" if cls=="benign" else "ATTACK_RECALL",
            "three_nonoverlapping_strata":{},
            "three_strata_all_estimable":all(groups[g]["support"]>0 for g in STRATA),
        }
        for grp in STRATA:
            g=groups[grp];n=g["support"]
            out[cls]["three_nonoverlapping_strata"][grp]={
                "support":n,
                "native_rate":g["attack_predictions"]/n if n else NA,
            }
        if sum(groups[g]["support"] for g in STRATA)!=counts[cls]:
            raise ValueError("Native row class support not conserved")
    return {"device":device,"full_target_rows":sum(counts.values()),
            "classwise":out,
            "causality":"NONE; exact 115D numeric features are not packet IDs"}


def check_and_compute(plan,approved,runs_root:Path,root:Path,manifest:Path,
                      inventory:Path,sqlite_path:Path):
    tasks=full_plan_tasks(plan)
    if not (approved.get("status")=="AUTHORIZED_FOR_CONFIRMATORY_TEST"
            and approved.get("authorized") is True
            and approved.get("human_review_complete") is True
            and approved.get("independent_data_admission_complete") is True
            and approved.get("source_manifest_sha256")==sha(manifest)):
        raise PermissionError("Unapproved original-data 54-run study")
    for field in ("protocol_sha256","engine_sha256","replay_sha256",
                  "native_loader_sha256","requirements_sha256",
                  "native_inventory_sha256","orchestration_sha256",
                  "exposure_analysis_protocol_sha256","source_manifest_sha256",
                  "original_nine_zip_admission_scanner_sha256",
                  "primary_analysis_sha256","sample_exposure_analysis_sha256",
                  "full_source_exposure_analysis_sha256"):
        if approved.get(field)!=plan.get(field):
            raise PermissionError("Stage18/19 approved revision mismatch: "+field)
    if plan.get("full_source_exposure_analysis_sha256")!=sha(Path(__file__)):
        raise PermissionError("Original preregistered source availability code changed")
    # Before even building the all-source index, confirm every retained fit
    # and complete original target prediction/metric replay are valid.
    receipts={}
    for task in tasks:
        directory=runs_root/task["task_id"]
        if not (directory/"run_receipt.json").is_file() or not (
                directory/"independent_replay.json").is_file():
            raise FileNotFoundError("All 54 genuine native heldout outputs required")
        receipts[task["task_id"]]=verify_one(directory,task,plan,approved)
    con=create_digest_index(sqlite_path)
    try:
        byte_proof,census=build_from_original_nine(con,root,manifest,inventory)
        results=[]
        exposure_by_device_seed={}
        for task in tasks:
            directory=runs_root/task["task_id"]
            bank_file=directory/"actually_trained_source_feature_digests.csv.gz"
            bank=training_fingerprints(bank_file,task["source_clients"])
            r=study_one_target(directory/"target_predictions.csv.gz",
                               task["heldout_device"],bank,con)
            expected_support=receipts[task["task_id"]]["native_class_support"]
            if {c:r["classwise"][c]["original_target_support"] for c in LABELS}!=expected_support:
                raise ValueError("Target class support differs from independent replay")
            signature={
                c:tuple(r["classwise"][c]["three_nonoverlapping_strata"][g]["support"]
                        for g in STRATA) for c in LABELS
            }
            key=(task["heldout_device"],task["seed"])
            if key in exposure_by_device_seed and signature!=exposure_by_device_seed[key]:
                raise ValueError("Paired FL methods have inconsistent exposure strata")
            exposure_by_device_seed[key]=signature
            r.update({"method":task["method"],"seed":task["seed"],
                      "task_id":task["task_id"]})
            results.append(r)
        return {
            "status":"ALL_54_FULL_CORPUS_VS_ACTUAL_TRAINING_EXPOSURE",
            "original_total_rows":7062606,
            "full_corpus_index_sha256":sha(sqlite_path),
            "source_bytes_checked":byte_proof["original_zips_verified"],
            "three_strata":list(STRATA),
            "binary_threshold":0.5,
            "target_rows_kept_at_original_prevalence":True,
            "effect_interpretation":"OBSERVATIONAL_ASSOCIATION_ONLY",
            "trained_exact_must_imply_full_source_availability":True,
            "absent_class_values":"NON_ESTIMABLE; NEVER ZERO",
            "native_census":census,
            "per_run":results,
        }
    finally:
        con.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("plan","approval-gate","runs-root","source-root",
                "source-manifest","native-inventory","sqlite-index","output"):
        p.add_argument("--"+arg,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.sqlite_index.exists():
        raise FileExistsError("Never silently overwrite scientific study/index")
    plan=json.loads(a.plan.read_text(encoding="utf8"))
    approval=json.loads(a.approval_gate.read_text(encoding="utf8"))
    result=check_and_compute(plan,approval,a.runs_root,a.source_root,
                             a.source_manifest,a.native_inventory,a.sqlite_index)
    result["plan_sha256"]=sha(a.plan)
    result["analysis_code_sha256"]=sha(Path(__file__))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf8") as fd:
        json.dump(result,fd,indent=2,allow_nan=False)
    print("FULL_SOURCE_VS_TRAINING_EXPOSURE_ALL_54_PASS",flush=True)


if __name__=="__main__":
    main()
