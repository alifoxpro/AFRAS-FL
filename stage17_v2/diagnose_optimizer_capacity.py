#!/usr/bin/env python3
"""AFRAS-FL V2: exactly one source-only optimization-capacity check.

NOT confirmatory. Seven original source devices train, Samsung (another source)
validates, Ennio outer target is neither opened nor evaluated. The adjustment
from the failed SGD 3x1 pilot is an intentionally *exploratory* rescue:
AdamW lr=0.001 with inverse-prevalence BCE, 5 rounds x 3 local epochs.
It changes both optimizer and budget, so it cannot identify which caused any
improvement. Do not use these validation outcomes to claim target generalization.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
import source_only_pilot as p


def train_adamw(initial, data, seed, epochs, batch, lr, device):
    X, y = data
    benign = int((y == 0).sum())
    attack = int((y == 1).sum())
    if min(benign, attack) < 1:
        raise ValueError("Source class support missing")
    model = p.BinaryMLP().to(device)
    model.load_state_dict(initial)
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.0)
    positive_weight = torch.as_tensor(benign / attack, dtype=torch.float32, device=device)
    loader = DataLoader(
        TensorDataset(torch.from_numpy(X), torch.from_numpy(y)),
        batch_size=batch, shuffle=True,
        generator=torch.Generator().manual_seed(seed)
    )
    losses = []
    for epoch in range(epochs):
        batch_losses = []
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.binary_cross_entropy_with_logits(
                model(xb), yb, pos_weight=positive_weight)
            if not torch.isfinite(loss):
                raise RuntimeError("Nonfinite source loss")
            loss.backward()
            optimizer.step()
            batch_losses.append(float(loss.item()))
        losses.append(float(np.mean(batch_losses)))
    return {k: v.detach().cpu().clone() for k,v in model.state_dict().items()}, losses


def report(state, clients, val, device):
    per = {}
    for src, train in clients.items():
        out = p.evaluate_source_validation(state, train, device)
        per[src] = {key: out[key] for key in ("tp","tn","fp","fn")}
    totals = {key:sum(r[key] for r in per.values())
              for key in ("tp","tn","fp","fn")}
    TP,TN,FP,FN=(totals[k] for k in ("tp","tn","fp","fn"))
    overall={
        "train_balanced_accuracy": 0.5 * (TP/(TP+FN)+TN/(TN+FP)),
        "train_benign_fpr": FP/(TN+FP),
        "train_attack_recall": TP/(TP+FN),
        "in_sample_train_confusion": totals,
        "per_source_training": per,
    }
    other=p.evaluate_source_validation(state,val,device)
    overall["source_validation"]={
        "balanced_accuracy":other["validation_only_balanced_accuracy"],
        "benign_fpr":other["validation_only_fpr"],
        "attack_recall":other["validation_only_attack_recall"],
        "confusion":{k:other[k] for k in ("tp","tn","fp","fn")},
    }
    return overall


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    ap.add_argument("--heldout",default="Ennio_Doorbell",choices=p.DEVICES)
    ap.add_argument("--validation",default="Samsung_SNH_1011_N_Webcam",choices=p.DEVICES)
    args=ap.parse_args()
    if args.output.exists():
        raise FileExistsError("Refusing to overwrite previous experiment")
    seven, other=p.split_source_devices(args.heldout,args.validation)
    sources=[*seven,other]
    if args.heldout in sources or len(set(sources))!=8:
        raise ValueError("Outer-target isolation violation")
    torch.set_num_threads(2)
    seed=3107
    torch.manual_seed(seed)
    clients={}
    val=None
    expected_header=None
    support={}
    for dev in sources:
        X,y,count,expected_header=p.load_one_device(
            args.source_root,dev,128,seed,expected_header)
        support[dev]=count
        if dev==other:val=(X,y)
        else:clients[dev]=(X,y)
        print("REAL_SOURCE_LOADED",dev,len(y),flush=True)
    clients,val,normalization=p.preprocess_train_only(clients,val)
    device=torch.device("cpu")
    torch.manual_seed(seed)
    weights={k:v.detach().cpu().clone()
             for k,v in p.BinaryMLP().state_dict().items()}
    results=[{"round":0,**report(weights,clients,val,device)}]
    for r in range(1,6):
        states=[];sizes=[];local_losses={}
        for ix,(dev,data) in enumerate(clients.items()):
            local,losses=train_adamw(
                weights,data,seed+r*1009+ix,3,128,0.001,device)
            states.append(local);sizes.append(len(data[1]))
            local_losses[dev]=losses
        weights=p.weighted_fedavg(states,sizes)
        measured=report(weights,clients,val,device)
        measured["round"]=r
        measured["local_epoch_losses"]=local_losses
        results.append(measured)
        print("ADAMW_SOURCE_DIAGNOSTIC",json.dumps({
            "round":r,
            "train_ba":measured["train_balanced_accuracy"],
            "train_benign_fpr":measured["train_benign_fpr"],
            "source_val_ba":measured["source_validation"]["balanced_accuracy"],
            "source_val_benign_fpr":measured["source_validation"]["benign_fpr"],
        },separators=(",",":")),flush=True)
    output={
        "status":"EXPLORATORY_REAL_UCI_SOURCE_ONLY_OPTIMIZATION_CAPACITY_CHECK",
        "outer_target":args.heldout,
        "outer_target_accessed":False,
        "source_training_clients":seven,
        "source_validation_device":other,
        "source_class_counts":support,
        "source_only_class_capped_sampling":128,
        "modifications_vs_failed_SGD":"AdamW instead of SGD and 5x3 versus 3x1; mode comparison not causally isolated",
        "class_weighting":"inverse prevalence based on each training client only",
        "protocol":{"seed":seed,"rounds":5,"local_epochs":3,
                    "batch_size":128,"lr":0.001,"optimizer":"AdamW",
                    "weight_decay":0,"model":"115-64-32-1 MLP",
                    "source_validation_threshold":0.5},
        "results":results,
        "source_code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "confirmatory":False,
        "generalization_claim_permitted":False,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("x",encoding="utf8") as f:
        json.dump(output,f,indent=2,allow_nan=False)
    print("EXPLORATORY_ADAMW_NATIVE_UCI_SOURCE_PILOT_COMPLETE",args.output,flush=True)


if __name__=="__main__":
    main()
