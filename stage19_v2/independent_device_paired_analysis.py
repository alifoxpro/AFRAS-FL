#!/usr/bin/env python3
"""AFRAS V2: pre-result, nine-device paired analysis of 54 confirmed FL runs.

Run ONLY after actual originally approved 9 folds x 2 arms x 3 seeds have
completed, with independently replayed raw target predictions. This script
does not train, score new test data, authorize research, or discover models.

Primary point estimand: mean across NINE devices of (FedProx-FedAvg) in
balanced accuracy, after averaging three locked seeds within each device.
Uncertainty unit: nine devices; no row-wise or seed-wise pseudo-replication.
"""
from __future__ import annotations
import argparse
import csv
from itertools import product
import hashlib
import json
import math
from pathlib import Path
import random

CANONICAL_DEVICES=(
    "Ennio_Doorbell","Samsung_SNH_1011_N_Webcam",
    "Provision_PT_838_Security_Camera","Ecobee_Thermostat",
    "Provision_PT_737E_Security_Camera","Danmini_Doorbell",
    "Philips_B120N10_Baby_Monitor",
    "SimpleHome_XCS7_1003_WHT_Security_Camera",
    "SimpleHome_XCS7_1002_WHT_Security_Camera",
)
METHODS=("FedAvg","FedProx")
SEEDS=(3107,3108,3109)
N=len(CANONICAL_DEVICES)


def sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()


def full_plan_tasks(plan:dict):
    """Demand all 54 canonical keys, not a chosen subset of favorable folds."""
    if (plan.get("status")!="PLAN_ONLY__NO_TARGET_OPENED"
            or plan.get("runs_planned")!=54
            or plan.get("runs_executed_by_planner")!=0
            or not isinstance(plan.get("source_manifest_sha256"),str)
            or len(plan["source_manifest_sha256"])!=64
            or plan.get("frozen_core_full_execution_authorized") is not False):
        raise ValueError("Not a frozen 54-task research plan")
    tasks=plan.get("tasks")
    if not isinstance(tasks,list) or len(tasks)!=54:
        raise ValueError("All 54 task records are mandatory")
    expected=[]
    for idx,device in enumerate(CANONICAL_DEVICES,1):
        clients=[x for x in CANONICAL_DEVICES if x!=device]
        for method,seed in product(METHODS,SEEDS):
            expected.append({
                "task_id":f"fold_{idx:02d}__{device}__{method}__seed{seed}",
                "fold":idx,"heldout_device":device,"method":method,
                "seed":seed,"source_clients":clients,
                "expected_training_source_clients":8,
                "native_test_policy":"All original native heldout rows; no target subsampling"
            })
    if tasks!=expected:
        raise ValueError("Missing, reordered or changed 54-task roster")
    return tasks


def validate_confusion(metrics):
    c=metrics.get("confusion")
    if not isinstance(c,dict) or set(c)!={"tp","tn","fp","fn"}:
        raise ValueError("Original target four-cell confusion required")
    if any(not isinstance(c[k],int) or isinstance(c[k],bool) or c[k]<0 for k in c):
        raise ValueError("Invalid count")
    n=sum(c.values())
    if n!=metrics.get("native_target_rows") or n<2:
        raise ValueError("Incomplete target support")
    pos=c["tp"]+c["fn"]
    neg=c["tn"]+c["fp"]
    if min(pos,neg)<=0:
        raise ValueError("Target class support not positive")
    BA=(c["tp"]/pos+c["tn"]/neg)/2
    FPR=c["fp"]/neg
    recall=c["tp"]/pos
    if not all(math.isclose(obs,calc,abs_tol=1e-11,rel_tol=0)
               for obs,calc in (
                   (metrics.get("balanced_accuracy"),BA),
                   (metrics.get("benign_fpr"),FPR),
                   (metrics.get("attack_recall"),recall),
               )):
        raise ValueError("Independent replay metrics contradict raw confusion")
    classwise=metrics.get("classwise_native_metrics",{})
    if not isinstance(classwise,dict) or "benign" not in classwise:
        raise ValueError("Expected 11 native class supports")
    if classwise["benign"].get("support")!=neg:
        raise ValueError("Original heldout benign support differs")
    return {"balanced_accuracy":BA,"benign_fpr":FPR,
            "attack_recall":recall,"rows":n}


def verify_one(run_dir:Path,task:dict,plan:dict,approval:dict):
    receipt_path=run_dir/"run_receipt.json"
    replay_path=run_dir/"independent_replay.json"
    if not receipt_path.is_file() or not replay_path.is_file():
        raise FileNotFoundError("Missing run/replay pair "+task["task_id"])
    r=json.loads(receipt_path.read_text(encoding="utf8"))
    x=json.loads(replay_path.read_text(encoding="utf8"))
    if (r.get("status")!="CONFIRMATORY_RAW_PREDICTION_OUTPUT"
            or r.get("mode")!="confirmatory"
            or r.get("target_test_scored") is not True
            or r.get("target_archive_opened") is not True
            or r.get("target_results") is None
            or r.get("heldout_device")!=task["heldout_device"]
            or r.get("training_devices")!=task["source_clients"]
            or r.get("source_clients")!=8
            or r.get("model")!=task["method"]
            or r.get("seed")!=task["seed"]
            or r.get("authorization_receipt")!=approval
            or r.get("protocol_sha256")!=plan["protocol_sha256"]
            or r.get("engine_sha256")!=plan["engine_sha256"]
            or r.get("training",{}).get("rounds")!=5
            or r.get("training",{}).get("local_epochs")!=3):
        raise ValueError("Run not exact authorized frozen task "+task["task_id"])
    if (r.get("code_hashes_at_gate",{}).get("replay_sha256")!=plan["replay_sha256"]
            or r["code_hashes_at_gate"].get("orchestration_sha256")!=plan["orchestration_sha256"]
            or r["code_hashes_at_gate"].get("source_manifest_sha256",plan["source_manifest_sha256"])!=plan["source_manifest_sha256"]
            or r.get("execution_environment",{}).get("requirements_sha256")!=plan["requirements_sha256"]):
        raise ValueError("Run code/plan evidence mismatch "+task["task_id"])
    if (x.get("status")!="INDEPENDENT_FULL_NATIVE_TARGET_PREDICTION_REPLAY"
            or x.get("device")!=task["heldout_device"]
            or x.get("method")!=task["method"]
            or x.get("seed")!=task["seed"]
            or x.get("protocol_sha256")!=plan["protocol_sha256"]
            or x.get("engine_sha256")!=plan["engine_sha256"]
            or x.get("native_inventory_sha256")!=plan["native_inventory_sha256"]):
        raise ValueError("Independent replay mismatch "+task["task_id"])
    target=r["target_results"]
    if not (target.get("raw_file")=="target_predictions.csv.gz"
            and target.get("raw_sha256")==x.get("prediction_file_sha256")
            and target.get("rows")==x["metrics"].get("native_target_rows")):
        raise ValueError("Raw native target artifact mismatch "+task["task_id"])
    if sha(run_dir/"target_predictions.csv.gz")!=target["raw_sha256"]:
        raise ValueError("Raw prediction checksum corruption "+task["task_id"])
    if sha(run_dir/"final_checkpoint.pt")!=r["checkpoint_sha256"]:
        raise ValueError("Final trained checkpoint corruption "+task["task_id"])
    bank=r.get("actual_training_feature_exposure",{})
    actual=x.get("actual_training_exposure_integrity",{})
    if not (bank.get("num_rows")==240000
            and bank.get("filename")=="actually_trained_source_feature_digests.csv.gz"
            and actual.get("actual_training_source_rows")==240000
            and actual.get("source_sample_digest_sha256")==bank.get("sha256")
            and sha(run_dir/bank["filename"])==bank["sha256"]):
        raise ValueError("Actual source sample fingerprint bank mismatch "+task["task_id"])
    sample=r.get("sampling")
    if not isinstance(sample,dict) or set(sample)!=set(task["source_clients"]):
        raise ValueError("Source-client sample census incomplete")
    hashes={}
    for dev in task["source_clients"]:
        d=sample[dev]
        if d.get("sample_size")!=30000:
            raise ValueError("Source sample was not locked 30k")
        h=d.get("sample_row_ids_sha256")
        if not isinstance(h,str) or len(h)!=64:
            raise ValueError("Missing source sample row IDs hash")
        hashes[dev]=h
    prep=r.get("preprocessing_train_only",{}).get("sha256")
    if not isinstance(prep,str) or len(prep)!=64:
        raise ValueError("Missing eight-source-only transform hash")
    return {"metrics":validate_confusion(x["metrics"]),
            "native_class_support":target.get("native_class_support"),
            "source_sampling_sha256":hashes,
            "source_transform_sha256":prep,
            "source_manifest_sha256":r.get("authorization_receipt",{}).get("source_manifest_sha256")}


def percentile(sorted_values:list[float],pct:float):
    if not sorted_values:
        raise ValueError("No bootstrap values")
    z=pct*(len(sorted_values)-1)
    i=int(z)
    f=z-i
    return sorted_values[i]*(1-f)+sorted_values[min(len(sorted_values)-1,i+1)]*f


def inference(paired_differences:list[float],replicates:int=10000,seed:int=3107):
    if len(paired_differences)!=9 or any(not math.isfinite(d) or abs(d)>1 for d in paired_differences):
        raise ValueError("Require exactly nine finite device-level differences")
    observed=sum(paired_differences)/9
    # Exact randomization over ALL 2^9 device sign flips, without treating
    # 54 device-seed observations or millions of native rows as independent.
    dist=[]
    for signs in product((-1,1),repeat=9):
        dist.append(sum(sign*x for sign,x in zip(signs,paired_differences))/9)
    pval=sum(abs(q)>=abs(observed)-1e-15 for q in dist)/len(dist)
    rng=random.Random(seed)
    boot=sorted(sum(paired_differences[rng.randrange(9)] for _ in range(9))/9
                for _ in range(replicates))
    return {"paired_difference":observed,
            "unit_of_inference":"NINE_HELDOUT_DEVICES__NOT_ROWS_OR_SEEDS",
            "two_sided_exact_sign_flip_p":pval,
            "sign_flip_combinations":512,
            "bootstrap_seed":seed,
            "device_paired_bootstrap_replicates":replicates,
            "percentile_95_ci":[percentile(boot,.025),percentile(boot,.975)],
            "caution":"Sign-flip symmetry and nine-device bootstrap limitations; observational FL evaluation, not a causal recurrence intervention"}


def aggregate(task_results:dict,plan:dict):
    tasks=full_plan_tasks(plan)
    keys=[t["task_id"] for t in tasks]
    if set(keys)!=set(task_results) or len(task_results)!=54:
        raise ValueError("All 54 independently verified runs are mandatory")
    cells={}
    for t in tasks:
        key=(t["heldout_device"],t["method"],t["seed"])
        cells[key]=task_results[t["task_id"]]
    # Require all same-target original test prevalence, matching source samples
    # and source-only normalization across methods at each device/seed.
    for d in CANONICAL_DEVICES:
        norms=[]
        for seed in SEEDS:
            avg=cells[(d,"FedAvg",seed)]
            prox=cells[(d,"FedProx",seed)]
            if (avg["native_class_support"]!=prox["native_class_support"]
                    or avg["metrics"]["rows"]!=prox["metrics"]["rows"]
                    or avg["source_sampling_sha256"]!=prox["source_sampling_sha256"]
                    or avg["source_transform_sha256"]!=prox["source_transform_sha256"]):
                raise ValueError("Unmatched baseline source/test evidence "+d+str(seed))
            norms.append(avg["native_class_support"])
        if not all(x==norms[0] for x in norms):
            raise ValueError("Native heldout class support changed between seeds "+d)
    by_device=[]
    for d in CANONICAL_DEVICES:
        rows={}
        for method in METHODS:
            met={}
            for field in ("balanced_accuracy","benign_fpr","attack_recall"):
                met[field]=sum(cells[(d,method,seed)]["metrics"][field]
                               for seed in SEEDS)/len(SEEDS)
            rows[method]=met
        diff=rows["FedProx"]["balanced_accuracy"]-rows["FedAvg"]["balanced_accuracy"]
        by_device.append({"device":d,"FedAvg":rows["FedAvg"],
                          "FedProx":rows["FedProx"],
                          "device_paired_ba_difference":diff,
                          "independent_seed_replicates":3})
    means={method:sum(x[method]["balanced_accuracy"] for x in by_device)/9
           for method in METHODS}
    diffs=[x["device_paired_ba_difference"] for x in by_device]
    stat=inference(diffs)
    if not math.isclose(stat["paired_difference"],means["FedProx"]-means["FedAvg"],
                        abs_tol=1e-12,rel_tol=0):
        raise ValueError("Device-paired method contrast arithmetic failed")
    return {
        "status":"FINAL_ALL_54_INDEPENDENTLY_VERIFIED_DEVICE_PAIRED_ANALYSIS",
        "total_runs":54,"n_heldout_devices":9,
        "seeds":list(SEEDS),"methods":list(METHODS),
        "primary_endpoint":"equal-device-weighted mean native heldout binary BA",
        "primary_method_contrast":"FedProx-minus-FedAvg after within-device three-seed mean",
        "mean_native_device_balanced_accuracy":means,
        "worst_device_seed_averaged_balanced_accuracy":{
            method:min(x[method]["balanced_accuracy"] for x in by_device)
            for method in METHODS},
        "paired_inference":stat,
        "by_device":by_device,
        "full_source_vs_actual_training_exposure":
            "NOT_ESTIMATED_HERE; separate exact-feature source membership analysis required",
        "scientific_novelty_established":False,
        "journal_submission_approved":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--runs-root",type=Path,required=True)
    p.add_argument("--approval-gate",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        raise FileExistsError("Never overwrite immutable statistics evidence")
    plan=json.loads(args.plan.read_text(encoding="utf8"))
    tasks=full_plan_tasks(plan)
    approval=json.loads(args.approval_gate.read_text(encoding="utf8"))
    if (approval.get("status")!="AUTHORIZED_FOR_CONFIRMATORY_TEST"
            or approval.get("authorized") is not True
            or approval.get("human_review_complete") is not True
            or approval.get("independent_data_admission_complete") is not True):
        raise PermissionError("This output requires real preauthorized completed experiments")
    for k in ("protocol_sha256","engine_sha256","replay_sha256",
              "native_loader_sha256","requirements_sha256",
              "native_inventory_sha256","orchestration_sha256",
              "exposure_analysis_protocol_sha256",
              "original_nine_zip_admission_scanner_sha256",
              "source_manifest_sha256"):
        if approval.get(k)!=plan.get(k):
            raise PermissionError("Approval and 54-run plan revision differ on "+k)
    # Read only after all 54 required receipts exist; never generate a
    # partial, cherry-picked 3- or 8-device significance test.
    for task in tasks:
        folder=args.runs_root/task["task_id"]
        for fname in ("run_receipt.json","independent_replay.json"):
            if not (folder/fname).is_file():
                raise FileNotFoundError("Missing mandatory original result "+str(folder/fname))
    results={t["task_id"]:verify_one(args.runs_root/t["task_id"],t,plan,approval)
             for t in tasks}
    result=aggregate(results,plan)
    result["source_plan_sha256"]=sha(args.plan)
    result["authorization_receipt_sha256"]=sha(args.approval_gate)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,allow_nan=False)
    print("DEVICE_LEVEL_ALL_54_PAIRED_EVIDENCE_PASS",
          result["paired_inference"]["paired_difference"],flush=True)


if __name__=="__main__":
    main()
