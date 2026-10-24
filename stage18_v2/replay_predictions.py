#!/usr/bin/env python3
"""AFRAS-FL V2: INDEPENDENT replay of complete raw held-out predictions.

No trained model is imported or fitted. Recomputes confusion matrices and
full-target class support from gzipped per-observation predictions. Verifies
native historical class-support audit (analysis-only), raw artifact SHA and
scientific zero-denominator handling. Does not impute absent-class recall.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

DEVICES=(
 "Ennio_Doorbell","Samsung_SNH_1011_N_Webcam",
 "Provision_PT_838_Security_Camera","Ecobee_Thermostat",
 "Provision_PT_737E_Security_Camera","Danmini_Doorbell",
 "Philips_B120N10_Baby_Monitor",
 "SimpleHome_XCS7_1003_WHT_Security_Camera",
 "SimpleHome_XCS7_1002_WHT_Security_Camera"
)
LABELS=("benign","gafgyt_combo","gafgyt_junk","gafgyt_scan","gafgyt_tcp",
        "gafgyt_udp","mirai_ack","mirai_scan","mirai_syn",
        "mirai_udp","mirai_udpplain")
HEADER=("device","attack_class","source_row_index","y_true","attack_probability")


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()


def native_expected(inventory:Path,target:str):
    """Existing Stage13 full-device source counts are ONLY an after-run check."""
    if target not in DEVICES:
        raise ValueError("Noncanonical heldout device")
    result={}
    with inventory.open(newline="",encoding="utf8") as f:
        rd=csv.DictReader(f)
        if not {"device","class","total_rows"}.issubset(rd.fieldnames or ()):
            raise ValueError("Invalid source support inventory")
        for r in rd:
            if r["device"]!=target:
                continue
            if r["class"] not in LABELS or r["class"] in result:
                raise ValueError("Bad/duplicate class in native inventory")
            n=int(r["total_rows"])
            if n<0:
                raise ValueError("Negative native support")
            result[r["class"]]=n
    if set(result)!=set(LABELS):
        raise ValueError("Expected exactly eleven class-support entries")
    if result["benign"]<1 or sum(v for k,v in result.items() if k!="benign")<1:
        raise ValueError("Full target lacks primary binary classes")
    return result


def replay_one(prediction_path:Path,target:str,expected:dict):
    """Streaming O(11) memory, canonical class and row-order verification."""
    if target not in DEVICES:
        raise ValueError("Unknown target")
    counts={name:0 for name in LABELS}
    true_pos={name:0 for name in LABELS if name!="benign"}
    tn=fp=0
    n=0
    with gzip.open(prediction_path,"rt",encoding="utf8",newline="") as f:
        rd=csv.DictReader(f)
        if tuple(rd.fieldnames or ())!=HEADER:
            raise ValueError("Prediction record field mismatch")
        for r in rd:
            cls=r["attack_class"]
            if r["device"]!=target or cls not in LABELS:
                raise ValueError("Unexpected device or class in raw predictions")
            row_no=int(r["source_row_index"])
            if row_no!=counts[cls]:
                raise ValueError("Missing/duplicate/disordered native row index")
            label=int(r["y_true"])
            if label not in (0,1) or label!=int(cls!="benign"):
                raise ValueError("Source-class vs binary label conflict")
            p=float(r["attack_probability"])
            if not math.isfinite(p) or not 0.0<=p<=1.0:
                raise ValueError("Invalid model output probability")
            predicted=int(p>=0.5)
            if cls=="benign":
                tn+=int(predicted==0)
                fp+=int(predicted==1)
            else:
                true_pos[cls]+=int(predicted==1)
            counts[cls]+=1
            n+=1
    if counts!=expected or n!=sum(expected.values()):
        raise ValueError("Incomplete/extra heldout raw predictions")
    attack_count=sum(v for k,v in expected.items() if k!="benign")
    tp=sum(true_pos.values())
    fn=attack_count-tp
    if n!=(tp+tn+fp+fn) or n<1 or attack_count<1 or expected["benign"]<1:
        raise ValueError("Pooled confusion or denominator invariant failed")
    attack_recall=tp/attack_count
    benign_specificity=tn/expected["benign"]
    class_metrics={}
    for cls in LABELS:
        support=expected[cls]
        if cls=="benign":
            class_metrics[cls]={
                "support":support,
                "benign_false_positive_rate":fp/support,
                "attack_recall":"NOT_APPLICABLE"
            }
        else:
            class_metrics[cls]={
                "support":support,
                "true_positives":true_pos[cls],
                "attack_recall":(
                    true_pos[cls]/support if support else "NON_ESTIMABLE"
                )
            }
    return {
        "target_device":target,
        "native_target_rows":n,
        "classwise_native_metrics":class_metrics,
        "confusion":{"tp":tp,"tn":tn,"fp":fp,"fn":fn},
        "balanced_accuracy":(attack_recall+benign_specificity)/2,
        "attack_recall":attack_recall,
        "benign_fpr":fp/expected["benign"],
        "benign_specificity":benign_specificity,
        "classification_threshold":0.5,
        "raw_prediction_file_sha256":sha(prediction_path),
        "estimation_unit":"one heldout device; not one row",
        "exposure_recurring_metrics":"NOT_IN_BASE_REPLAY; analysis-only join pending",
    }


def replay_and_validate(receipt_path:Path, inventory:Path, output:Path):
    r=json.loads(receipt_path.read_text(encoding="utf8"))
    if not (r.get("mode")=="confirmatory"
            and r.get("status")=="CONFIRMATORY_RAW_PREDICTION_OUTPUT"
            and r.get("target_test_scored") is True
            and r.get("target_archive_opened") is True
            and len(r.get("training_devices",()))==8
            and r["heldout_device"] not in r["training_devices"]
            and r.get("source_clients")==8
            and r.get("target_results")):
        raise ValueError("Not a complete authorized 8-client target receipt")
    t=r["target_results"]
    path=receipt_path.parent/t["raw_file"]
    if path.name!="target_predictions.csv.gz" or not path.is_file():
        raise ValueError("Missing required full-target raw prediction artifact")
    if sha(path)!=t["raw_sha256"]:
        raise ValueError("Target prediction file checksum mismatch")
    expected=native_expected(inventory,r["heldout_device"])
    if (t["rows"]!=sum(expected.values())
            or t["native_class_support"]!=expected):
        raise ValueError("Final target support diverges from original inventory")
    metrics=replay_one(path,r["heldout_device"],expected)
    results={
        "status":"INDEPENDENT_FULL_NATIVE_TARGET_PREDICTION_REPLAY",
        "source_replay":"row-wise gzip prediction read, not model inference",
        "device":r["heldout_device"],
        "method":r["model"],
        "seed":r["seed"],
        "protocol_sha256":r["protocol_sha256"],
        "engine_sha256":r["engine_sha256"],
        "prediction_file_sha256":t["raw_sha256"],
        "native_inventory_sha256":sha(inventory),
        "metrics":metrics,
    }
    if output.exists():
        raise FileExistsError("Refusing to replace independent replay evidence")
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x",encoding="utf8") as f:
        json.dump(results,f,indent=2,allow_nan=False)
    return results


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--receipt",required=True,type=Path)
    a.add_argument("--native-inventory",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    args=a.parse_args()
    v=replay_and_validate(args.receipt,args.native_inventory,args.output)
    print("INDEPENDENT_REPLAY_PASS",v["device"],v["method"],
          v["seed"],v["metrics"]["native_target_rows"],flush=True)


if __name__=="__main__":
    main()
