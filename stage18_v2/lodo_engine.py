#!/usr/bin/env python3
"""AFRAS-FL V2: locked-protocol eight-client LODO engine.

DEFAULT = SOURCE-ONLY PRE-FLIGHT; the named target ZIP IS NEVER OPENED.
The full-target evaluation branch requires an explicit code/protocol/replay-hash
matched authorization receipt. Never create that receipt automatically.

Real N-BaIoT native ZIP/RAR files are external inputs (never bundled).
The only scientifically confirmatory output is a completely gated, native
prevalence, all-target-row result. The 2026-10-24 core spec is otherwise fixed.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stage17_v2"))
import source_only_pilot as native

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "stage16_v2" / "FROZEN_CORE_PROTOCOL_V1_2026-10-24.json"
REPLAY = Path(__file__).with_name("replay_predictions.py")
HEADER = ("device","attack_class","source_row_index","y_true","feature_digest","attack_probability")
N = native.N_FEATURES


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda: f.read(1 << 20), b""):
            hasher.update(buf)
    return hasher.hexdigest()


def verify_frozen_core(path: Path):
    o = json.loads(path.read_text(encoding="utf8"))
    m = o["modeling"]
    if not (o["status"] == "CORE_METHODS_AND_ANALYSIS_SPECIFICATION_FROZEN_PRE_RESULT"
            and o["folds"]["count"] == 9
            and o["folds"]["source_clients"] == 8
            and tuple(o["data"]["device_names"]) == native.DEVICES
            and tuple(m["architecture"]) == (115,64,32,1)
            and m["optimizer"] == "AdamW"
            and m["communication_rounds"] == 5
            and m["local_epochs_per_round"] == 3
            and m["local_batch_size"] == 128
            and m["source_uniform_sample_per_device_without_replacement"] == 30000
            and tuple(m["random_seeds"]) == (3107,3108,3109)
            and m["lr"] == 0.001
            and m["weight_decay"] == 0
            and m["fedprox_mu"] == 0.01
            and m["threshold"] == 0.5
            and set(m["baseline_methods"]) == {"FedAvg","FedProx"}):
        raise ValueError("Frozen core does not match audited Stage16 v1")
    return o


def fold_sources(target: str) -> tuple[str, ...]:
    if target not in native.DEVICES:
        raise ValueError("Invalid target")
    sources = tuple(d for d in native.DEVICES if d != target)
    if len(sources) != 8 or target in sources:
        raise ValueError("Source membership invariant violated")
    return sources


class UniformDeviceTopK:
    """Uniform without replacement over ALL original rows/classes of one device.

    One RNG per source device (seed + canonical_index*111), single stream of
    random keys across CSVs. Keep the k smallest keys and original identifiers.
    """
    def __init__(self, limit: int, seed: int):
        if limit < 2:
            raise ValueError("Sample limit must be >= 2")
        self.k = limit
        self.rng = np.random.default_rng(seed)
        self.x = np.empty((0, N), dtype=np.float64)
        self.labels = np.empty((0,), dtype=np.float32)
        self.keys = np.empty((0,), dtype=np.float64)
        self.class_ids = np.empty((0,), dtype=np.int8)
        self.row_ids = np.empty((0,), dtype=np.int64)
        self.total_seen = 0
        self.original_class_counts = {}

    def ingest(self, data: np.ndarray, class_name: str, start_row: int):
        if data.ndim != 2 or data.shape[1] != N or not np.isfinite(data).all():
            raise ValueError("Invalid original numeric source observations")
        if class_name not in native.LABELS:
            raise ValueError("Unknown class")
        n = len(data)
        self.total_seen += n
        self.original_class_counts[class_name] = (
            self.original_class_counts.get(class_name, 0) + n
        )
        if not n:
            return
        keys = self.rng.random(n)
        count = min(n, self.k)
        ix = np.argpartition(keys, count - 1)[:count]
        raw_candidates = np.asarray(data[ix], dtype=np.float64)
        candidates = raw_candidates  # retain native float64 until after asinh
        labels = np.full(len(ix), float(class_name != "benign"), dtype=np.float32)
        classes = np.full(len(ix), native.LABELS.index(class_name), dtype=np.int8)
        original_rows = np.asarray(start_row + ix, dtype=np.int64)
        joint_key = np.concatenate((self.keys, keys[ix]))
        select_n = min(self.k, len(joint_key))
        chosen = np.argpartition(joint_key, select_n - 1)[:select_n]
        self.x = np.concatenate((self.x, candidates))[chosen].copy()
        self.labels = np.concatenate((self.labels, labels))[chosen].copy()
        self.keys = joint_key[chosen].copy()
        self.class_ids = np.concatenate((self.class_ids, classes))[chosen].copy()
        self.row_ids = np.concatenate((self.row_ids, original_rows))[chosen].copy()

    def finish(self):
        if self.total_seen < self.k or len(self.labels) != self.k:
            raise ValueError("Source contains fewer rows than the locked sample cap")
        if not (self.labels == 0).any() or not (self.labels == 1).any():
            raise ValueError("Sample lacks both binary classes")
        # Stable order by key; same selected examples, train order reproducible.
        order = np.lexsort((self.row_ids, self.class_ids, self.keys))
        self.x = self.x[order]
        self.labels = self.labels[order]
        self.class_ids = self.class_ids[order]
        self.row_ids = self.row_ids[order]
        h = hashlib.sha256()
        h.update(self.class_ids.tobytes())
        h.update(self.row_ids.tobytes())
        sample_hash = h.hexdigest()
        counts = {
            cls: int((self.class_ids == native.LABELS.index(cls)).sum())
            for cls in native.LABELS
        }
        canonical = np.asarray(self.x, dtype="<f8", order="C").copy()
        canonical[canonical == 0.0] = 0.0
        raw_digest_hex = [
            hashlib.blake2b(row.tobytes(), digest_size=16).hexdigest()
            for row in canonical
        ]
        # Hashes of EXACT SOURCE SAMPLES actually used for training, distinct
        # from Stage13 FULL-source-availability recurrence. Never raw features.
        return self.x, self.labels, {
            "sampled_raw_feature_digests": raw_digest_hex,
            "native_rows": self.total_seen,
            "native_class_counts": self.original_class_counts,
            "sample_size": int(len(self.labels)),
            "sample_class_counts": counts,
            "sample_row_ids_sha256": sample_hash,
        }


def load_source_only(root: Path, device: str, k: int, seed: int,
                     ordered_header: list[str] | None):
    sample = UniformDeviceTopK(k, seed + native.DEVICES.index(device) * 111)
    for cls, source in native.iter_native_csv(root, device):
        start = 0
        for frame in pd.read_csv(
                source, dtype=np.float64, chunksize=native.CSV_CHUNK,
                on_bad_lines="error"):
            header = list(frame.columns)
            if len(header) != N or (ordered_header is not None and header != ordered_header):
                raise ValueError("Source numeric features/header mismatch")
            if ordered_header is None:
                ordered_header = header
            X = frame.to_numpy(dtype=np.float64, copy=False)
            sample.ingest(X, cls, start)
            start += len(X)
        if not start:
            raise ValueError("Source native class CSV unexpectedly empty")
    x, y, receipt = sample.finish()
    return (x,y), receipt, ordered_header


def load_source_with_verified_cache(root: Path, device: str, k: int, seed: int,
                                    ordered_header: list[str] | None,
                                    cache_root: Path, source_zip_sha256: str|None):
    """Source-only immutable per-device/seed/k native-float64 sample cache.

    The held-out target cannot be read here unless the caller explicitly
    supplies it; run() supplies only fold_sources(target). Each cache entry is
    bound to the byte-identical original source ZIP, native loader code,
    engine code, selected sample, and original header. Cached *raw float64*
    vectors are transformed on eight-source union separately for each fold.
    """
    if device not in native.DEVICES or k<2 or seed<0:
        raise ValueError("Invalid original source device sampling cache key")
    cache_root.mkdir(parents=True,exist_ok=True)
    digest=source_zip_sha256 or file_sha256(root/(device+".zip"))
    loader_hash=file_sha256(Path(native.__file__))
    engine_hash=file_sha256(Path(__file__))
    basename=f"{device}__seed{seed}__k{k}__float64_v1"
    array_path=cache_root/(basename+".npz")
    receipt_path=cache_root/(basename+".receipt.json")
    if array_path.exists() or receipt_path.exists():
        if not (array_path.is_file() and receipt_path.is_file()):
            raise ValueError("Partial sample cache: require manual integrity review")
        meta=json.loads(receipt_path.read_text(encoding="utf8"))
        if not (meta.get("cache_schema")=="RAW_FLOAT64_UNIFORM_SAMPLE_V1"
                and meta.get("device")==device
                and meta.get("seed")==seed and meta.get("cap")==k
                and meta.get("source_zip_sha256")==digest
                and meta.get("native_loader_sha256")==loader_hash
                and meta.get("sampler_engine_sha256")==engine_hash
                and meta.get("compressed_sample_sha256")==file_sha256(array_path)):
            raise ValueError("Stale or tampered original-source cache")
        with np.load(array_path,allow_pickle=False) as bank:
            X=bank["source_raw_float64"]
            y=bank["source_binary_label"]
            header=list(bank["original_feature_header"])
            record=json.loads(str(bank["source_sample_receipt_json"].item()))
        if (X.dtype!=np.float64 or y.dtype!=np.float32
                or X.shape!=(k,N) or y.shape!=(k,)
                or not np.isfinite(X).all()
                or not set(np.unique(y))=={0.,1.}
                or len(header)!=N
                or (ordered_header is not None and ordered_header!=header)
                or record.get("sample_size")!=k
                or record.get("sampled_raw_feature_digests")!=raw_feature_digests(X)):
            raise ValueError("Cached source samples differ from native float64 receipt")
        record["sample_cache_status"]="VERIFIED_HIT"
        return (X,y),record,header
    pair,record,header=load_source_only(root,device,k,seed,ordered_header)
    X,y=pair
    if X.dtype!=np.float64 or len(record["sampled_raw_feature_digests"])!=k:
        raise ValueError("Source sample cache requires native float64 and exact raw digests")
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(prefix=basename+".",suffix=".npz",
                            dir=cache_root,delete=False) as handle:
        temporary=Path(handle.name)
        np.savez_compressed(handle,source_raw_float64=X,source_binary_label=y,
            original_feature_header=np.asarray(header,dtype=np.str_),
            source_sample_receipt_json=np.asarray(json.dumps(record)))
    try:
        compressed_digest=file_sha256(temporary)
        metadata={
            "cache_schema":"RAW_FLOAT64_UNIFORM_SAMPLE_V1",
            "device":device,"seed":seed,"cap":k,
            "source_zip_sha256":digest,
            "native_loader_sha256":loader_hash,
            "sampler_engine_sha256":engine_hash,
            "compressed_sample_sha256":compressed_digest,
            "sample_row_ids_sha256":record["sample_row_ids_sha256"],
        }
        # Never silently overwrite a verified source sample or its metadata.
        if array_path.exists() or receipt_path.exists():
            raise FileExistsError("Concurrent cache writer or already-filled cache")
        temporary.replace(array_path)
        with receipt_path.open("x",encoding="utf8") as out:
            json.dump(metadata,out,indent=2)
    finally:
        temporary.unlink(missing_ok=True)
    record["sample_cache_status"]="NEW_SOURCE_CACHE"
    return pair,record,header


def source_transform(clients: dict):
    # Apply asinh on original native float64 FIRST, then cast once to float32,
    # exactly mirroring write_all_target_predictions() after final training.
    if any(X.dtype != np.float64 for X,_ in clients.values()):
        raise ValueError("Source input must retain raw float64 until asinh transform")
    xform = [np.arcsinh(X).astype(np.float32) for X,_ in clients.values()]
    matrix = np.concatenate(xform, axis=0)
    mu = matrix.mean(axis=0, dtype=np.float64).astype(np.float32)
    std = matrix.std(axis=0, dtype=np.float64).astype(np.float32)
    std[std < 1e-6] = 1.0
    out = {}
    for (name, (_X,y)), xx in zip(clients.items(),xform):
        normalized = (xx-mu)/std
        if not np.isfinite(normalized).all():
            raise ValueError("Source preprocessed features not finite")
        out[name]=(normalized.astype(np.float32),y)
    return out, mu, std


def local_adamw(start, data, method, mu_fedprox, round_seed,
                local_epochs, batch_size, lr):
    X, y = data
    nneg = int(np.count_nonzero(y == 0))
    npos = int(np.count_nonzero(y == 1))
    if nneg < 1 or npos < 1:
        raise ValueError("Source class weighting undefined")
    torch_device = torch.device("cpu")
    model = native.BinaryMLP().to(torch_device)
    model.load_state_dict(start)
    model.train()
    fixed_start = [p.detach().clone() for p in model.parameters()]
    optimizer = torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=0.0)
    positive_weight = torch.tensor(nneg/npos, dtype=torch.float32)
    loader = DataLoader(
        TensorDataset(torch.from_numpy(X),torch.from_numpy(y)),
        batch_size=batch_size,shuffle=True,
        generator=torch.Generator().manual_seed(round_seed)
    )
    epoch_losses=[]
    for _ in range(local_epochs):
        batch_losses=[]
        for xb,yb in loader:
            optimizer.zero_grad(set_to_none=True)
            pred=model(xb)
            loss=nn.functional.binary_cross_entropy_with_logits(
                pred,yb,pos_weight=positive_weight)
            if method == "FedProx":
                loss = loss+0.5*mu_fedprox*sum(
                    (p-ref).square().sum()
                    for p,ref in zip(model.parameters(),fixed_start))
            if not torch.isfinite(loss):
                raise RuntimeError("Nonfinite source train loss")
            loss.backward()
            optimizer.step()
            batch_losses.append(float(loss.detach().item()))
        epoch_losses.append(float(np.mean(batch_losses)))
    state={name:t.detach().cpu().clone()
           for name,t in model.state_dict().items()}
    return state,epoch_losses


def train_eight(clients: dict, method: str, seed: int, spec: dict,
                rounds: int, epochs: int):
    m=spec["modeling"]
    if method not in ("FedAvg","FedProx") or len(clients)!=8:
        raise ValueError("Exactly eight source clients and a locked baseline required")
    torch.manual_seed(seed)
    current={k:v.detach().cpu().clone()
             for k,v in native.BinaryMLP().state_dict().items()}
    trace=[]
    start_time=perf_counter()
    for rnd in range(1,rounds+1):
        states=[];sizes=[];losses={}
        for index,(name,data) in enumerate(clients.items()):
            state,el=local_adamw(
                current,data,method,m["fedprox_mu"],
                seed+rnd*1009+index,epochs,
                m["local_batch_size"],m["lr"]
            )
            states.append(state)
            sizes.append(len(data[1]))
            losses[name]=el
        current=native.weighted_fedavg(states,sizes)
        trace.append({"round":rnd,"mean_final_local_loss":
                      float(np.mean([v[-1] for v in losses.values()])),
                      "per_client_epoch_losses":losses})
        print("EIGHT_SOURCE_TRAIN_ROUND",
              json.dumps({"method":method,"seed":seed,"round":rnd,
                          "mean_loss":trace[-1]["mean_final_local_loss"]}),
              flush=True)
    return current,trace,float(perf_counter()-start_time)


def assert_approval(gate_path: Path|None, spec_path: Path):
    """Fail closed. The gate is an explicit auditable receipt, not a signature."""
    if gate_path is None or not gate_path.is_file():
        raise PermissionError("Confirmatory target scoring requires a gate file")
    approval=json.loads(gate_path.read_text(encoding="utf8"))
    sha = {
        "protocol_sha256":file_sha256(spec_path),
        "engine_sha256":file_sha256(Path(__file__)),
        "replay_sha256":file_sha256(REPLAY),
        "native_loader_sha256":file_sha256(Path(native.__file__)),
        "requirements_sha256":file_sha256(ROOT/"stage17_v2"/"requirements-pilot.txt"),
        "native_inventory_sha256":file_sha256(
            ROOT/"stage16_v2"/"EXPOSURE_ELIGIBILITY_ANALYSIS_ONLY.csv"),
        "orchestration_sha256":file_sha256(
            ROOT/"stage18_v2"/"plan_and_run_54.py"),
        "exposure_analysis_protocol_sha256":file_sha256(
            ROOT/"stage16_v2"/"PRE_RESULT_EXPOSURE_ESTIMAND_CLARIFICATION_2026-10-24.md"),
    }
    if (approval.get("status") != "AUTHORIZED_FOR_CONFIRMATORY_TEST"
            or approval.get("authorized") is not True
            or not isinstance(approval.get("approved_by"),str)
            or not approval["approved_by"].strip()
            or approval.get("human_review_complete") is not True
            or approval.get("independent_data_admission_complete") is not True
            or approval.get("no_target_results_reviewed") is not True
            or any(approval.get(k)!=v for k,v in sha.items())):
        raise PermissionError("Approval absent or current audited code hashes differ")
    return approval,sha


def raw_feature_digests(original_float64: np.ndarray):
    """Reproduce Stage13 numerical-feature equality without model access.

    Canonicalized little-endian IEEE754 float64, normalize signed zeros,
    BLAKE2b-128 over the 115 ordered feature values. Generated ONLY during
    post-training target prediction streaming; never used to fit the model.
    """
    if original_float64.ndim!=2 or original_float64.shape[1]!=N:
        raise ValueError("Incorrect vector width for Stage13 digest")
    if not np.isfinite(original_float64).all():
        raise ValueError("Invalid nonfinite numerical feature fingerprint")
    canonical=np.array(original_float64,dtype="<f8",order="C",copy=True)
    canonical[canonical==0.0]=0.0
    view=memoryview(canonical).cast("B")
    step=N*8
    return [
        hashlib.blake2b(view[i:i+step],digest_size=16).hexdigest()
        for i in range(0,len(view),step)
    ]


@torch.no_grad()
def write_all_target_predictions(root: Path, heldout: str, state,
                                 ordered_header, mean, std, output: Path):
    """Only invoked AFTER successful target-scoring gate check and training."""
    model=native.BinaryMLP()
    model.load_state_dict(state)
    model.eval()
    class_counts={label:0 for label in native.LABELS}
    output.parent.mkdir(parents=True,exist_ok=True)
    # output must not be an existing unverified or partial result
    with gzip.open(output,"xt",encoding="utf8",newline="",compresslevel=3) as dest:
        wr=csv.writer(dest)
        wr.writerow(HEADER)
        for cls,source in native.iter_native_csv(root,heldout):
            count=0
            for frame in pd.read_csv(
                    source,dtype=np.float64,chunksize=native.CSV_CHUNK,
                    on_bad_lines="error"):
                header=list(frame.columns)
                if header!=ordered_header:
                    raise ValueError("Held-out native feature header mismatch")
                X=frame.to_numpy(dtype=np.float64,copy=False)
                if not np.isfinite(X).all():
                    raise ValueError("Nonfinite target values; refuse silent filtering")
                features=((np.arcsinh(X).astype(np.float32)-mean)/std)
                if not np.isfinite(features).all():
                    raise ValueError("Nonfinite target preprocessing")
                probabilities=torch.sigmoid(
                    model(torch.from_numpy(features))
                ).cpu().numpy()
                if not np.isfinite(probabilities).all():
                    raise ValueError("Nonfinite target probabilities")
                digests=raw_feature_digests(X)
                for i,pr in enumerate(probabilities):
                    wr.writerow((heldout,cls,count+i,int(cls!="benign"),
                                 digests[i],repr(float(pr))))
                count+=len(probabilities)
            class_counts[cls]=count
    return class_counts,file_sha256(output)


def run(args):
    spec=verify_frozen_core(args.protocol)
    method=args.method
    seed=args.seed
    if seed not in spec["modeling"]["random_seeds"]:
        raise ValueError("Seed not listed in frozen core")
    sources=fold_sources(args.heldout)
    if args.output_dir.exists():
        raise FileExistsError("Refusing existing output directory, even if empty")
    # Gate is checked BEFORE any target or source archive is opened.
    approval=None
    hashes=None
    if args.mode=="confirmatory":
        if (args.preflight_cap != 0 or args.preflight_rounds != 0
                or args.preflight_epochs != 0):
            raise ValueError("Pilot overrides forbidden in confirmatory mode")
        approval, hashes=assert_approval(args.approval_gate,args.protocol)
        manifest_path=getattr(args,"source_manifest",None)
        if manifest_path is None or not manifest_path.is_file():
            raise PermissionError("Original source manifest required for confirmatory execution")
        if approval.get("source_manifest_sha256")!=file_sha256(manifest_path):
            raise PermissionError("Source manifest digest differs from approved receipt")
    else:
        if args.approval_gate:
            raise ValueError("Do not use a target-approval gate in source preflight")
    source_hashes={}
    if args.mode=="confirmatory":
        source_hashes=native.verify_source_archive_hashes(
            args.source_root,args.source_manifest,list(sources),args.heldout
        )
    args.output_dir.mkdir(parents=True,exist_ok=False)
    sample_k=(spec["modeling"]["source_uniform_sample_per_device_without_replacement"]
              if args.mode=="confirmatory" else args.preflight_cap or 30000)
    round_count=(spec["modeling"]["communication_rounds"]
                 if args.mode=="confirmatory" else args.preflight_rounds or 1)
    local_epochs=(spec["modeling"]["local_epochs_per_round"]
                  if args.mode=="confirmatory" else args.preflight_epochs or 1)
    header=None
    clients={}
    native_receipts={}
    sampled_digest_sets={}
    for source in sources:
        cache_root=getattr(args,"source_cache_root",None)
        if cache_root is None:
            pair,rec,header=load_source_only(
                args.source_root,source,sample_k,seed,header)
        else:
            pair,rec,header=load_source_with_verified_cache(
                args.source_root,source,sample_k,seed,header,
                cache_root,source_hashes.get(source))
        clients[source]=pair
        sampled = rec.pop("sampled_raw_feature_digests", None)
        if sampled is not None:
            if len(sampled) != rec["sample_size"]:
                raise ValueError("Source sampled feature digest count mismatch")
            sampled_digest_sets[source] = sampled
        elif args.mode == "confirmatory":
            raise ValueError("Missing true feature exposure from sampled training source")
        native_receipts[source]=rec
        print("SOURCE_ONLY_DEVICE_LOADED",source,rec["native_rows"],
              rec["sample_size"],flush=True)
    if len(sampled_digest_sets) == 8:
        digest_path=args.output_dir/"actually_trained_source_feature_digests.csv.gz"
        with gzip.open(digest_path, "xt", encoding="utf8", newline="") as fd:
            wr=csv.writer(fd)
            wr.writerow(("training_source_device","raw_float64_feature_digest"))
            for source in sources:
                for h in sampled_digest_sets[source]:
                    wr.writerow((source,h))
        source_sample_digest_receipt={
            "filename":digest_path.name,
            "sha256":file_sha256(digest_path),
            "num_rows":sum(len(v) for v in sampled_digest_sets.values()),
            "status":"ACTUAL_SELECTED_TRAINING_ROWS_ONLY_NOT_FULL_SOURCE_CORPUS",
        }
    else:
        source_sample_digest_receipt=None
    processed,mean,std=source_transform(clients)
    state,trace,seconds=train_eight(
        processed,method,seed,spec,round_count,local_epochs)
    source_stats=hashlib.sha256(mean.tobytes()+std.tobytes()).hexdigest()
    result={
       "status":("PRE_FLIGHT_SOURCE_ONLY" if args.mode=="preflight" else
                 "CONFIRMATORY_RAW_PREDICTION_OUTPUT"),
       "mode":args.mode,
       "heldout_device":args.heldout,
       "training_devices":list(sources),
       "source_clients":len(sources),
       "target_archive_opened":args.mode=="confirmatory",
       "target_test_scored":args.mode=="confirmatory",
       "binary_threshold":spec["modeling"]["threshold"],
       "model":method,"seed":seed,
       "sampling":native_receipts,
       "actual_training_feature_exposure":source_sample_digest_receipt,
       "preprocessing_train_only":{
           "mean":mean.tolist(),"scale":std.tolist(),
           "sha256":source_stats
       },
       "training":{"rounds":round_count,"local_epochs":local_epochs,
                   "seconds":seconds,"round_trace":trace},
       "protocol_sha256":file_sha256(args.protocol),
       "engine_sha256":file_sha256(Path(__file__)),
       "code_version":"STAGE18_V2_COMMIT_NOT_HARDCODED",
       "label_source":"original native source path",
       "source_original_zip_sha256_checked":source_hashes,
       "execution_environment":{
           "python":sys.version,
           "platform":platform.platform(),
           "torch":torch.__version__,
           "numpy":np.__version__,
           "pandas":pd.__version__,
           "source_code_commit":subprocess.run(
               ["git","rev-parse","HEAD"],cwd=ROOT,
               capture_output=True,text=True,check=False,timeout=5
           ).stdout.strip() or "UNAVAILABLE",
           "requirements_sha256":file_sha256(ROOT/"stage17_v2"/"requirements-pilot.txt")
       },
       "not_privacy_claim":"Client data was read by a centralized research runner",
       "target_results":None
    }
    if args.mode=="confirmatory":
        original=json.loads(args.source_manifest.read_text(encoding="utf8"))
        target_record=[entry for entry in original["local_archives"]
                       if entry["device"]==args.heldout]
        if len(target_record)!=1:
            raise ValueError("Original manifest must contain heldout device exactly once")
        target_zip=args.source_root/(args.heldout+".zip")
        target_digest=file_sha256(target_zip)
        if target_digest!=target_record[0]["local_sha256"].lower():
            raise ValueError("Heldout target archive bytes diverge from pre-admitted source")
        result["target_archive_sha256"]=target_digest
        predpath=args.output_dir/"target_predictions.csv.gz"
        class_counts,predsha=write_all_target_predictions(
            args.source_root,args.heldout,state,header,mean,std,predpath)
        result["target_results"]={
            "raw_file":predpath.name,"raw_sha256":predsha,
            "native_class_support":class_counts,"rows":sum(class_counts.values())
        }
        result["authorization_receipt"]=approval
        result["code_hashes_at_gate"]=hashes
        torch.save(state,args.output_dir/"final_checkpoint.pt")
        result["checkpoint_sha256"]=file_sha256(
            args.output_dir/"final_checkpoint.pt")
    else:
        result["no_target_features_or_labels_accessed"]=True
        result["preflight_only"]=True
    with (args.output_dir/"run_receipt.json").open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,allow_nan=False)
    print("STAGE18_MODE_COMPLETE",args.mode,method,args.heldout,seed,flush=True)


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--mode",choices=("preflight","confirmatory"),default="preflight")
    a.add_argument("--source-root",required=True,type=Path)
    a.add_argument("--output-dir",required=True,type=Path)
    a.add_argument("--protocol",type=Path,default=CORE)
    a.add_argument("--heldout",choices=native.DEVICES,default=native.DEVICES[0])
    a.add_argument("--method",choices=("FedAvg","FedProx"),default="FedAvg")
    a.add_argument("--seed",type=int,default=3107)
    a.add_argument("--approval-gate",type=Path,default=None)
    a.add_argument("--source-manifest",type=Path,default=None)
    a.add_argument("--source-cache-root",type=Path,default=None)
    a.add_argument("--preflight-cap",type=int,default=0)
    a.add_argument("--preflight-rounds",type=int,default=0)
    a.add_argument("--preflight-epochs",type=int,default=0)
    args=a.parse_args()
    if any(v<0 for v in (args.preflight_cap,args.preflight_rounds,
                         args.preflight_epochs)):
        a.error("Preflight overrides cannot be negative")
    if not args.source_root.is_dir():
        a.error("Original source ZIP directory not accessible")
    torch.set_num_threads(2)
    run(args)


if __name__=="__main__":
    main()
