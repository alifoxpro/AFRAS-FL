#!/usr/bin/env python3
"""AFRAS Stage19 preregistered actual-training-exposure descriptive audit.

Never trains or tunes models. Requires all 54 independently replayed runs.
Uses exact 115D canonical native float64 BLAKE2b-128 fingerprints.
Full-source-corpus availability recurrence is a DIFFERENT variable.
"""
import argparse
import csv
import gzip
import json
import math
from pathlib import Path
from independent_device_paired_analysis import full_plan_tasks, verify_one, sha

LABELS=("benign","gafgyt_combo","gafgyt_junk","gafgyt_scan",
        "gafgyt_tcp","gafgyt_udp","mirai_ack","mirai_scan",
        "mirai_syn","mirai_udp","mirai_udpplain")
PRED=("device","attack_class","source_row_index","y_true","feature_digest","attack_probability")
BANK=("training_source_device","raw_float64_feature_digest")
NA="NON_ESTIMABLE"


def valid_digest(d):
    return isinstance(d,str) and len(d)==32 and all(c in "0123456789abcdef" for c in d)


def training_fingerprints(path,clients,per_client=30000):
    if len(clients)!=8 or len(set(clients))!=8:
        raise ValueError("Exactly eight source clients required")
    counts={x:0 for x in clients}
    values=set()
    with gzip.open(path,"rt",newline="",encoding="utf8") as f:
        rdr=csv.DictReader(f)
        if tuple(rdr.fieldnames or ())!=BANK:
            raise ValueError("Wrong sampled source bank schema")
        for row in rdr:
            dev=row["training_source_device"]
            d=row["raw_float64_feature_digest"]
            if dev not in counts or not valid_digest(d):
                raise ValueError("Invalid source device or vector digest")
            counts[dev]+=1
            if counts[dev]>per_client:
                raise ValueError("Unexpected extra source sample")
            values.add(d)
    if set(counts.values())!={per_client}:
        raise ValueError("Missing source training sample fingerprint rows")
    return values


def analyze_target(pred_file,device,source_digests,expected):
    """Full-row device/class exact-training-exposure join; no target tuning."""
    if set(expected)!=set(LABELS):
        raise ValueError("All eleven native target labels required")
    counts={x:0 for x in LABELS}
    groups={x:{"exposed":0,"unexposed":0,"hit_exposed":0,"hit_unexposed":0}
            for x in LABELS}
    with gzip.open(pred_file,"rt",newline="",encoding="utf8") as f:
        rdr=csv.DictReader(f)
        if tuple(rdr.fieldnames or ())!=PRED:
            raise ValueError("Target raw prediction header mismatch")
        for row in rdr:
            cls=row["attack_class"]
            if row["device"]!=device or cls not in LABELS:
                raise ValueError("Unrecognized original heldout class/device")
            if int(row["source_row_index"])!=counts[cls]:
                raise ValueError("Original heldout class row index gap/duplicate")
            if int(row["y_true"])!=int(cls!="benign"):
                raise ValueError("Original source-derived binary label mismatch")
            digest=row["feature_digest"]
            prob=float(row["attack_probability"])
            if not valid_digest(digest) or not math.isfinite(prob) or not 0<=prob<=1:
                raise ValueError("Invalid native float64 digest or probability")
            state="exposed" if digest in source_digests else "unexposed"
            groups[cls][state]+=1
            pred_attack=prob>=.5
            if (cls!="benign" and pred_attack) or (cls=="benign" and pred_attack):
                groups[cls]["hit_"+state]+=1
            counts[cls]+=1
    if counts!={c:int(expected[c]) for c in LABELS}:
        raise ValueError("Native class support not conserved")
    result={}
    for cls,g in groups.items():
        a=g["exposed"]; b=g["unexposed"]
        ae=g["hit_exposed"]/a if a else NA
        be=g["hit_unexposed"]/b if b else NA
        result[cls]={
            "native_support":counts[cls],
            "actually_trained_exposed_rows":a,
            "not_training_exposed_rows":b,
            "metric_type":"BENIGN_FPR" if cls=="benign" else "ATTACK_RECALL",
            "exposed_metric":ae,"unexposed_metric":be,
            "exposed_minus_unexposed":ae-be if a and b else NA,
            "both_strata_estimable":bool(a and b),
        }
    return {
        "device":device,
        "original_target_rows":sum(counts.values()),
        "eligible_attack_classes":sum(result[c]["both_strata_estimable"]
                                      for c in LABELS if c!="benign"),
        "classwise":result,
        "interpretation":"Observational numerical feature equality; not causal, not identical packets",
    }


def analyze_all(plan,root,approved):
    tasks=full_plan_tasks(plan)
    if approved.get("status")!="AUTHORIZED_FOR_CONFIRMATORY_TEST" or approved.get("authorized") is not True:
        raise PermissionError("Genuine authorized complete FL runs are required")
    for task in tasks:
        folder=root/task["task_id"]
        if not (folder/"run_receipt.json").is_file() or not (
                folder/"independent_replay.json").is_file():
            raise FileNotFoundError("Not all 54 independent replay results exist")
    out=[]
    parity={}
    training_parity={}
    for task in tasks:
        folder=root/task["task_id"]
        receipt=json.loads((folder/"run_receipt.json").read_text())
        verified=verify_one(folder,task,plan,approved)
        bank=folder/"actually_trained_source_feature_digests.csv.gz"
        vectors=training_fingerprints(bank,task["source_clients"])
        if sha(bank)!=receipt["actual_training_feature_exposure"]["sha256"]:
            raise ValueError("Source sample bank checksum changed")
        result=analyze_target(
            folder/"target_predictions.csv.gz",task["heldout_device"],
            vectors,verified["native_class_support"]
        )
        result.update({"task_id":task["task_id"],"method":task["method"],
                       "seed":task["seed"],"unique_source_training_vectors":len(vectors)})
        key=(task["heldout_device"],task["seed"])
        train_identity=(verified["source_sampling_sha256"],
                        verified["source_transform_sha256"])
        if key in training_parity and training_parity[key]!=train_identity:
            raise ValueError("FedAvg versus FedProx source-sample/normalization mismatch")
        training_parity[key]=train_identity
        signature={c:(result["classwise"][c]["actually_trained_exposed_rows"],
                      result["classwise"][c]["not_training_exposed_rows"])
                   for c in LABELS}
        if key in parity and parity[key]!=signature:
            raise ValueError("FedAvg versus FedProx actual-training exposure differs")
        parity[key]=signature
        out.append(result)
    return {"status":"ACTUAL_SAMPLED_TRAINING_EXPOSURE_ALL_54_REPLAYED",
            "runs":54,"devices":9,"true_source_training_rows_per_run":240000,
            "full_source_corpus_availability_not_computed":True,
            "causal_conclusions_prohibited":True,
            "non_estimable_is_not_zero":True,"per_run":out}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan",required=True,type=Path)
    p.add_argument("--runs-root",required=True,type=Path)
    p.add_argument("--approval-gate",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists():
        raise FileExistsError("Do not overwrite scientific analysis")
    plan=json.loads(a.plan.read_text())
    approved=json.loads(a.approval_gate.read_text())
    for field in ("protocol_sha256","engine_sha256","replay_sha256",
                  "native_loader_sha256","requirements_sha256",
                  "native_inventory_sha256","orchestration_sha256",
                  "exposure_analysis_protocol_sha256",
                  "original_nine_zip_admission_scanner_sha256",
                  "primary_analysis_sha256",
                  "sample_exposure_analysis_sha256",
                  "full_source_exposure_analysis_sha256",
                  "source_manifest_sha256"):
        if approved.get(field)!=plan.get(field):
            raise PermissionError("Wrong authorization revision")
    if approved.get("human_review_complete") is not True or approved.get(
            "independent_data_admission_complete") is not True:
        raise PermissionError("Human review and original data admission missing")
    files={
        "primary_analysis_sha256":Path(__file__).with_name("independent_device_paired_analysis.py"),
        "sample_exposure_analysis_sha256":Path(__file__),
        "full_source_exposure_analysis_sha256":
            Path(__file__).with_name("full_source_vs_training_exposure.py"),
    }
    for field,source in files.items():
        if plan.get(field)!=sha(source):
            raise PermissionError("Post-review Stage19 analytical code change: "+field)
    outcome=analyze_all(plan,a.runs_root,approved)
    outcome["analysis_sha256"]=sha(Path(__file__))
    outcome["plan_sha256"]=sha(a.plan)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf8") as f:
        json.dump(outcome,f,indent=2,allow_nan=False)
    print("ALL_54_EXACT_ACTUAL_TRAINING_EXPOSURE_ANALYSIS_PASS",flush=True)


if __name__=="__main__":
    main()
