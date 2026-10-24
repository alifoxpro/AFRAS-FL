#!/usr/bin/env python3
"""AFRAS V2 frozen 54-run ledger and optionally explicit operator-gated runner.

Default action is PLAN ONLY: no archives opened, no model run or target scored.
The optional --execute mode requires the existing human-approved SHA-bound
receipt (and original local ZIP manifest); never fabricates authorization.

Every completed run must pass independent raw-row metric replay before it can
be marked completed. No output is overwritten or skipped without validation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import lodo_engine as engine
import replay_predictions as replay

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
INVENTORY=ROOT/"stage16_v2"/"EXPOSURE_ELIGIBILITY_ANALYSIS_ONLY.csv"


def locked_tasks(protocol=engine.CORE):
    spec=engine.verify_frozen_core(protocol)
    methods=tuple(spec["modeling"]["baseline_methods"])
    seeds=tuple(spec["modeling"]["random_seeds"])
    devices=tuple(spec["data"]["device_names"])
    if len(devices)!=9 or len(methods)!=2 or len(seeds)!=3:
        raise ValueError("Locked core is not exactly nine x two x three")
    tasks=[]
    for fold,device in enumerate(devices,1):
        clients=engine.fold_sources(device)
        for method in methods:
            for seed in seeds:
                tasks.append({
                    "task_id":f"fold_{fold:02d}__{device}__{method}__seed{seed}",
                    "fold":fold,
                    "heldout_device":device,
                    "method":method,
                    "seed":int(seed),
                    "source_clients":list(clients),
                    "expected_training_source_clients":8,
                    "native_test_policy":"All original native heldout rows; no target subsampling",
                })
    ids=[task["task_id"] for task in tasks]
    if len(ids)!=54 or len(set(ids))!=54:
        raise ValueError("Exactly 54 unique locked task IDs required")
    for device in devices:
        if sum(t["heldout_device"]==device for t in tasks)!=6:
            raise ValueError("Every device must have exactly two methods x three seeds")
    return tasks


def create_plan(protocol:Path=engine.CORE, manifest:Path|None=None):
    tasks=locked_tasks(protocol)
    result={
        "status":"PLAN_ONLY__NO_TARGET_OPENED",
        "source":"FROZEN_CORE_PROTOCOL_V1_2026-10-24.json",
        "protocol_sha256":engine.file_sha256(protocol),
        "engine_sha256":engine.file_sha256(Path(engine.__file__)),
        "independent_replay_sha256":engine.file_sha256(Path(replay.__file__)),
        "manifest_sha256":(engine.file_sha256(manifest) if manifest else None),
        "frozen_core_full_execution_authorized":False,
        "runs_planned":54,
        "runs_executed_by_planner":0,
        "human_approval_receipt_embedded":False,
        "tasks":tasks,
        "warning":"Generating this ledger does NOT authorize or perform target inference."
    }
    return result


def verify_completed(run_folder:Path, expected:dict):
    receipt_path=run_folder/"run_receipt.json"
    evidence_path=run_folder/"independent_replay.json"
    if not receipt_path.is_file() or not evidence_path.is_file():
        return False
    rec=json.loads(receipt_path.read_text(encoding="utf8"))
    evidence=json.loads(evidence_path.read_text(encoding="utf8"))
    if (rec.get("heldout_device")!=expected["heldout_device"]
        or rec.get("model")!=expected["method"]
        or rec.get("seed")!=expected["seed"]
        or rec.get("mode")!="confirmatory"
        or rec.get("training_devices")!=expected["source_clients"]
        or rec.get("training",{}).get("rounds")!=5
        or rec.get("training",{}).get("local_epochs")!=3
        or evidence.get("status")!="INDEPENDENT_FULL_NATIVE_TARGET_PREDICTION_REPLAY"
        or evidence.get("device")!=expected["heldout_device"]
        or evidence.get("method")!=expected["method"]
        or evidence.get("seed")!=expected["seed"]
        or evidence.get("prediction_file_sha256")
             !=rec.get("target_results",{}).get("raw_sha256")):
        raise ValueError("Existing run files do not match locked task: "+expected["task_id"])
    raw_path=run_folder/"target_predictions.csv.gz"
    if engine.file_sha256(raw_path)!=evidence["prediction_file_sha256"]:
        raise ValueError("Existing raw predictions changed: "+expected["task_id"])
    checkpoint=run_folder/"final_checkpoint.pt"
    if engine.file_sha256(checkpoint)!=rec["checkpoint_sha256"]:
        raise ValueError("Existing checkpoint changed: "+expected["task_id"])
    if evidence.get("protocol_sha256")!=rec.get("protocol_sha256"):
        raise ValueError("Existing replay protocol mismatch")
    bank=rec.get("actual_training_feature_exposure")
    exposure=evidence.get("actual_training_exposure_integrity")
    if (not isinstance(bank,dict) or not isinstance(exposure,dict)
            or bank.get("filename")!="actually_trained_source_feature_digests.csv.gz"
            or bank.get("num_rows")!=240000
            or bank.get("sha256")!=exposure.get("source_sample_digest_sha256")
            or exposure.get("actual_training_source_rows")!=240000):
        raise ValueError("Missing independently verified actual-source exposure bank")
    actual_bank=run_folder/bank["filename"]
    if not actual_bank.is_file() or engine.file_sha256(actual_bank)!=bank["sha256"]:
        raise ValueError("Actually trained source digest bank changed")
    return True


def execute_tasks(args,plan):
    """Only invoked by the user's explicit --execute plus valid approval."""
    if args.approval_gate is None or args.source_manifest is None:
        raise PermissionError("Operator must provide approval gate and original manifest")
    gate,_sha=engine.assert_approval(args.approval_gate,args.protocol)
    if gate.get("source_manifest_sha256")!=engine.file_sha256(args.source_manifest):
        raise PermissionError("Original ZIP manifest is not the approved one")
    if not INVENTORY.is_file():
        raise FileNotFoundError("Native class-support inventory absent")
    if args.source_root is None or not args.source_root.is_dir():
        raise FileNotFoundError("Original nine local native ZIPs required")
    root=args.output_root
    root.mkdir(parents=True,exist_ok=True)
    completed=0
    for task in plan["tasks"]:
        folder=root/task["task_id"]
        if folder.exists():
            if verify_completed(folder,task):
                print("RESUME_VERIFIED_COMPLETE",task["task_id"],flush=True)
                completed+=1
                continue
            raise FileExistsError("Partial or uncertified run; manual inspection needed: "+str(folder))
        cmd=[
            sys.executable,str(Path(engine.__file__)),"--mode","confirmatory",
            "--source-root",str(args.source_root),
            "--output-dir",str(folder),
            "--protocol",str(args.protocol),
            "--source-manifest",str(args.source_manifest),
            "--approval-gate",str(args.approval_gate),
            "--heldout",task["heldout_device"],
            "--method",task["method"],
            "--seed",str(task["seed"]),
        ]
        subprocess.run(cmd,check=True)
        independent=[
            sys.executable,str(Path(replay.__file__)),
            "--receipt",str(folder/"run_receipt.json"),
            "--native-inventory",str(INVENTORY),
            "--output",str(folder/"independent_replay.json")
        ]
        subprocess.run(independent,check=True)
        if not verify_completed(folder,task):
            raise RuntimeError("Unverified post-run evidence: "+task["task_id"])
        completed+=1
        print("VERIFIED_CONFIRMATORY_TASK",completed,"/",len(plan["tasks"]),task["task_id"],flush=True)
    return completed


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol",type=Path,default=engine.CORE)
    p.add_argument("--plan-output",type=Path,required=True)
    p.add_argument("--execute",action="store_true",
                   help="Explicitly run 54 fits after independently approved hash-bound receipt")
    p.add_argument("--source-root",type=Path,default=None)
    p.add_argument("--source-manifest",type=Path,default=None)
    p.add_argument("--approval-gate",type=Path,default=None)
    p.add_argument("--output-root",type=Path,default=None)
    args=p.parse_args()
    if args.plan_output.exists():
        raise FileExistsError("Refusing to overwrite plan")
    if args.execute and args.output_root is None:
        p.error("--execute requires --output-root")
    plan=create_plan(args.protocol,args.source_manifest)
    args.plan_output.parent.mkdir(parents=True,exist_ok=True)
    args.plan_output.write_text(json.dumps(plan,indent=2),encoding="utf8")
    print("EXACT_54_RUNS_PLAN_ONLY",len(plan["tasks"]),
          "no target archives opened",flush=True)
    if args.execute:
        count=execute_tasks(args,plan)
        print("GATED_CONFIRMATORY_EXECUTION_COMPLETE",count,flush=True)


if __name__=="__main__":
    main()
