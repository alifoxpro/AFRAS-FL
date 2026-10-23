#!/usr/bin/env python3
"""AFRAS-FL V2: source-only *exploratory* federated IDS integration pilot.

Reads native device ZIPs (including embedded RAR CSVs) only for source devices.
The named target/held-out device is NEVER opened, sampled, transformed or scored.
Outputs source-validation diagnostics ONLY, never confirmatory LODO results.

Requires Python 3.10+, numpy, pandas, torch, rarfile and system libarchive.
No data, labels or publisher-provenance claims are included in this repository.
"""
from __future__ import annotations

import argparse
import copy
import ctypes
import ctypes.util
import hashlib
import io
import json
import os
from pathlib import Path
import random
import tempfile
import zlib
import zipfile

import numpy as np
import pandas as pd
import rarfile
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

DEVICES = (
    "Ennio_Doorbell",
    "Samsung_SNH_1011_N_Webcam",
    "Provision_PT_838_Security_Camera",
    "Ecobee_Thermostat",
    "Provision_PT_737E_Security_Camera",
    "Danmini_Doorbell",
    "Philips_B120N10_Baby_Monitor",
    "SimpleHome_XCS7_1003_WHT_Security_Camera",
    "SimpleHome_XCS7_1002_WHT_Security_Camera",
)
LABELS = (
    "benign", "gafgyt_combo", "gafgyt_junk", "gafgyt_scan",
    "gafgyt_tcp", "gafgyt_udp", "mirai_ack", "mirai_scan",
    "mirai_syn", "mirai_udp", "mirai_udpplain",
)
N_FEATURES = 115
CSV_CHUNK = 8192
RAR_MAX_MEMBER_BYTES = 1_000_000_000


def split_source_devices(heldout: str, validation: str) -> tuple[list[str], str]:
    """One target held out; one other source device used for feasibility validation."""
    if heldout not in DEVICES or validation not in DEVICES:
        raise ValueError("Holdout and validation must be canonical N-BaIoT devices")
    if heldout == validation:
        raise ValueError("Validation cannot be the held-out target")
    return [d for d in DEVICES if d not in (heldout, validation)], validation


class RARReader:
    """Read original embedded RAR via libarchive; check per-member RAR CRC/size.

    Based on the existing 24-Oct local Stage-13 extraction approach.
    Original bytes are never modified. A temporary CSV is destroyed after reading.
    """
    def __init__(self, blob: bytes):
        libname = ctypes.util.find_library("archive")
        if not libname:
            raise RuntimeError("System libarchive unavailable")
        lib = ctypes.CDLL(libname)
        lib.archive_read_new.restype = ctypes.c_void_p
        for method in ("archive_read_support_format_all",
                       "archive_read_support_filter_all", "archive_read_free"):
            getattr(lib, method).argtypes = [ctypes.c_void_p]
        lib.archive_read_open_memory.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        lib.archive_read_open_memory.restype = ctypes.c_int
        lib.archive_read_next_header.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        lib.archive_read_next_header.restype = ctypes.c_int
        lib.archive_entry_pathname.argtypes = [ctypes.c_void_p]
        lib.archive_entry_pathname.restype = ctypes.c_char_p
        lib.archive_read_data.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        lib.archive_read_data.restype = ctypes.c_ssize_t
        lib.archive_error_string.argtypes = [ctypes.c_void_p]
        lib.archive_error_string.restype = ctypes.c_char_p
        self.lib = lib
        self.buffer = ctypes.create_string_buffer(blob)
        self.expected = {
            i.filename: (i.file_size, i.CRC)
            for i in rarfile.RarFile(io.BytesIO(blob)).infolist()
            if not i.isdir()
        }
        self.reader = lib.archive_read_new()
        if not self.reader:
            raise RuntimeError("archive_read_new failed")
        lib.archive_read_support_format_all(self.reader)
        lib.archive_read_support_filter_all(self.reader)
        if lib.archive_read_open_memory(self.reader, self.buffer, len(blob)) != 0:
            lib.archive_read_free(self.reader)
            raise RuntimeError("Cannot open RAR in libarchive memory")

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.lib.archive_read_free(self.reader)

    def members(self):
        lib = self.lib
        seen = set()
        while True:
            entry = ctypes.c_void_p()
            status = lib.archive_read_next_header(self.reader, ctypes.byref(entry))
            if status == 1:  # ARCHIVE_EOF
                break
            if status != 0:
                raise RuntimeError("RAR header read failed")
            leaf = lib.archive_entry_pathname(entry).decode("utf-8")
            if (leaf not in self.expected or "/" in leaf or "\\" in leaf
                    or leaf in seen or not leaf.endswith(".csv")):
                raise ValueError("Unexpected/duplicate RAR CSV: " + leaf)
            seen.add(leaf)
            expected_size, expected_crc = self.expected[leaf]
            if expected_size < 0 or expected_size > RAR_MAX_MEMBER_BYTES:
                raise ValueError("RAR member exceeds size gate: " + leaf)
            filename = None
            try:
                with tempfile.NamedTemporaryFile(
                    prefix="afras_v2_src_", suffix=".csv", delete=False
                ) as tmp:
                    filename = tmp.name
                    buf = ctypes.create_string_buffer(1 << 20)
                    count, crc = 0, 0
                    while True:
                        n = lib.archive_read_data(self.reader, buf, len(buf))
                        if n < 0:
                            raise RuntimeError("RAR decompression failure: " + leaf)
                        if n == 0:
                            break
                        data = buf.raw[:n]
                        tmp.write(data)
                        count += n
                        if count > RAR_MAX_MEMBER_BYTES:
                            raise ValueError("RAR member exceeded extraction limit")
                        crc = zlib.crc32(data, crc)
                if count != expected_size or (crc & 0xffffffff) != expected_crc:
                    raise ValueError("RAR CSV CRC/size mismatch: " + leaf)
                yield leaf, filename
            finally:
                if filename and os.path.exists(filename):
                    os.unlink(filename)
        if seen != set(self.expected):
            raise ValueError("Missing RAR members")


def iter_native_csv(source_root: Path, device: str):
    """Only opens source ZIPs explicitly requested by the caller."""
    path = source_root / (device + ".zip")
    with zipfile.ZipFile(path, "r") as archive:
        prefix = device + "/"
        members = {name for name in archive.namelist() if not name.endswith("/")}
        expected = {prefix + "benign_traffic.csv", prefix + "gafgyt_attacks.rar"}
        if device not in DEVICES[:2]:
            expected.add(prefix + "mirai_attacks.rar")
        if members != expected:
            raise ValueError("Unexpected native ZIP member layout: " + device)
        with archive.open(prefix + "benign_traffic.csv", "r") as source:
            yield "benign", source
        for family in ("gafgyt", "mirai"):
            member = prefix + family + "_attacks.rar"
            if member not in expected:
                continue
            with RARReader(archive.read(member)) as rar:
                family_seen = set()
                for leaf, filename in rar.members():
                    label = family + "_" + leaf.removesuffix(".csv")
                    if label not in LABELS:
                        raise ValueError("Unrecognized class: " + label)
                    family_seen.add(label)
                    yield label, filename
                wanted = {label for label in LABELS if label.startswith(family + "_")}
                if family_seen != wanted:
                    raise ValueError("Incomplete family: " + family + " / " + device)


class PrioritySample:
    """Uniform without-replacement sample, bounded to k rows of each source class."""
    def __init__(self, k: int, seed: int):
        self.k = k
        self.rng = np.random.default_rng(seed)
        self.values = np.empty((0, N_FEATURES), dtype=np.float32)
        self.priorities = np.empty((0,), dtype=np.float64)
        self.observed = 0

    def ingest(self, arr: np.ndarray):
        if arr.ndim != 2 or arr.shape[1] != N_FEATURES:
            raise ValueError("Wrong feature width")
        if not np.isfinite(arr).all():
            raise ValueError("Nonfinite numeric observation")
        self.observed += len(arr)
        keys = self.rng.random(len(arr))
        take = min(self.k, len(keys))
        if take == 0:
            return
        index = np.argpartition(keys, take - 1)[:take]
        candidates = np.asarray(arr[index], dtype=np.float32)
        if not np.isfinite(candidates).all():
            raise ValueError("float32 overflow during sample conversion")
        x = np.concatenate((self.values, candidates))
        p = np.concatenate((self.priorities, keys[index]))
        n = min(self.k, len(p))
        select = np.argpartition(p, n - 1)[:n]
        self.values = x[select].copy()
        self.priorities = p[select].copy()


def load_one_device(source_root: Path, device: str, k: int,
                    seed: int, expected_header: list[str] | None):
    samples, labels, supports = [], [], {}
    for label, source in iter_native_csv(source_root, device):
        reservoir = PrioritySample(k, seed + DEVICES.index(device) * 101 + LABELS.index(label))
        found_chunk = False
        for chunk in pd.read_csv(
            source, dtype=np.float64, chunksize=CSV_CHUNK, on_bad_lines="error"
        ):
            header = list(chunk.columns)
            if len(header) != N_FEATURES:
                raise ValueError("Expected 115 numeric features")
            if expected_header is None:
                expected_header = header
            elif header != expected_header:
                raise ValueError("Noncanonical ordered feature header")
            found_chunk = True
            reservoir.ingest(chunk.to_numpy(dtype=np.float64, copy=False))
        if not found_chunk or reservoir.observed == 0:
            raise ValueError("Empty native class CSV: " + device + ":" + label)
        supports[label] = {
            "raw_rows_scanned": reservoir.observed,
            "sample_rows": len(reservoir.values),
        }
        samples.append(reservoir.values)
        labels.append(np.full(
            len(reservoir.values), int(label != "benign"), dtype=np.float32
        ))
    if not samples or "benign" not in supports:
        raise ValueError("Source device has no benign class")
    X, y = np.vstack(samples), np.concatenate(labels)
    if X.shape[1] != N_FEATURES or set(np.unique(y)) != {0., 1.}:
        raise ValueError("Pilot source device has invalid binary class support")
    return X, y, supports, expected_header


def preprocess_train_only(clients, validation):
    transformed = [np.arcsinh(v[0]).astype(np.float32) for v in clients.values()]
    fit = np.concatenate(transformed, axis=0)
    mu = fit.mean(axis=0, dtype=np.float64).astype(np.float32)
    sd = fit.std(axis=0, dtype=np.float64).astype(np.float32)
    sd[sd < 1e-6] = 1.0
    normalized = {
        name: ((np.arcsinh(X).astype(np.float32) - mu) / sd, y)
        for name, (X, y) in clients.items()
    }
    Xval, yval = validation
    v = ((np.arcsinh(Xval).astype(np.float32) - mu) / sd, yval)
    for X, _y in [*normalized.values(), v]:
        if not np.isfinite(X).all():
            raise ValueError("Nonfinite transformed features")
    return normalized, v, {"mean": mu.tolist(), "scale": sd.tolist()}


class BinaryMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(N_FEATURES, 64), nn.ReLU(),
            nn.Linear(64, 32), nn.ReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.layers(x).squeeze(1)


def weighted_fedavg(states, counts):
    """Sample-weighted aggregation; no target or source-validation data included."""
    if not states or any(n <= 0 for n in counts):
        raise ValueError("Aggregation requires positive client sample counts")
    weight = np.asarray(counts, dtype=np.float64)
    weight /= weight.sum()
    if set(states[0]) != set.intersection(*(set(state) for state in states)):
        raise ValueError("Client model parameter sets differ")
    aggregate = {}
    for key in states[0]:
        tensors = [state[key].detach().cpu() for state in states]
        if not all(torch.is_floating_point(t) for t in tensors):
            raise ValueError("Unsupported non-floating state buffer: " + key)
        aggregate[key] = sum(
            (float(w) * t for w, t in zip(weight, tensors)),
            torch.zeros_like(tensors[0])
        )
    return aggregate


def train_client(initial, dataset, method, mu, local_epochs,
                 batch_size, lr, random_seed, backend):
    model = BinaryMLP().to(backend)
    model.load_state_dict(initial)
    model.train()
    reference = [p.detach().clone() for p in model.parameters()]
    optimizer = torch.optim.SGD(model.parameters(), lr=lr)
    X, y = dataset
    iterator = DataLoader(
        TensorDataset(torch.from_numpy(X), torch.from_numpy(y)),
        batch_size=batch_size, shuffle=True,
        generator=torch.Generator().manual_seed(random_seed)
    )
    for _epoch in range(local_epochs):
        for xb, yb in iterator:
            xb, yb = xb.to(backend), yb.to(backend)
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.binary_cross_entropy_with_logits(model(xb), yb)
            if method == "fedprox":
                penalty = sum(
                    (p - p0).square().sum()
                    for p, p0 in zip(model.parameters(), reference)
                )
                loss = loss + 0.5 * mu * penalty
            loss.backward()
            optimizer.step()
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


@torch.no_grad()
def evaluate_source_validation(initial, validation, backend):
    model = BinaryMLP().to(backend)
    model.load_state_dict(initial)
    model.eval()
    X, y = validation
    pred = []
    for start in range(0, len(X), 4096):
        xb = torch.from_numpy(X[start:start + 4096]).to(backend)
        pred.extend((torch.sigmoid(model(xb)) >= 0.5).cpu().numpy().tolist())
    p = np.asarray(pred, dtype=np.int8)
    z = y.astype(np.int8)
    tp = int(((p == 1) & (z == 1)).sum())
    tn = int(((p == 0) & (z == 0)).sum())
    fp = int(((p == 1) & (z == 0)).sum())
    fn = int(((p == 0) & (z == 1)).sum())
    if tp + fn == 0 or tn + fp == 0:
        raise ValueError("Validation device lacks benign or attack support")
    recall = tp / (tp + fn)
    specificity = tn / (tn + fp)
    return {
        "validation_only_balanced_accuracy": 0.5 * (recall + specificity),
        "validation_only_attack_recall": recall,
        "validation_only_fpr": 1.0 - specificity,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
    }


def pilot_one_method(method, clients, validation, args, backend):
    torch.manual_seed(args.seed)
    initial = {k: v.detach().cpu().clone()
               for k, v in BinaryMLP().state_dict().items()}
    traces = []
    for round_no in range(1, args.rounds + 1):
        states, sizes = [], []
        for idx, (device, dataset) in enumerate(clients.items()):
            s = train_client(
                initial, dataset, method, args.fedprox_mu,
                args.local_epochs, args.batch_size, args.lr,
                args.seed + round_no * 1009 + idx, backend
            )
            states.append(s)
            sizes.append(len(dataset[1]))
        initial = weighted_fedavg(states, sizes)
        result = evaluate_source_validation(initial, validation, backend)
        result["round"] = round_no
        traces.append(result)
    return traces



def verify_source_archive_hashes(source_root: Path, manifest_path: Path,
                                 source_devices: list[str], heldout: str) -> dict[str, str]:
    """Validate source ZIP bytes against recorded local manifest (not UCI attestation).

    The excluded target is NEVER opened or hashed. The original manifest may
    list all nine devices, but only the eight source archive paths are touched.
    """
    if heldout not in DEVICES or heldout in source_devices or len(source_devices) != 8 or len(set(source_devices)) != 8:
        raise ValueError("Local hash preflight must exclude exactly one held-out device")
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    archives = manifest.get("local_archives")
    if not isinstance(archives, list) or len(archives) != len(DEVICES):
        raise ValueError("Expected nine original local archive manifest records")
    records = {}
    for entry in archives:
        device = entry.get("device")
        if device not in DEVICES or device in records:
            raise ValueError("Unknown/duplicate local manifest device")
        if entry.get("filename") != device + ".zip":
            raise ValueError("Unexpected device archive filename")
        digest = entry.get("local_sha256")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest.lower())):
            raise ValueError("Invalid source archive SHA-256 in manifest")
        records[device] = digest.lower()
    if set(records) != set(DEVICES):
        raise ValueError("Incomplete canonical device manifest")
    checked = {}
    for device in source_devices:
        if device not in records:
            raise ValueError("Unlisted device")
        path = source_root / (device + ".zip")
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1 << 20), b""):
                h.update(chunk)
        actual = h.hexdigest()
        if actual != records[device]:
            raise ValueError("Source ZIP SHA-256 mismatch: " + device)
        checked[device] = actual
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path,
                        help="Directory containing the original device-name ZIPs")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=None,
                        help="Optional recorded local SHA-256 manifest; sources only")
    parser.add_argument("--heldout", default=DEVICES[0], choices=DEVICES)
    parser.add_argument("--validation", default=DEVICES[1], choices=DEVICES)
    parser.add_argument("--max-per-class", type=int, default=128)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--local-epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--fedprox-mu", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=3107)
    parser.add_argument("--backend", choices=["cpu", "cuda"], default="cpu")
    args = parser.parse_args()
    if args.max_per_class < 1 or args.rounds < 1 or args.local_epochs < 1:
        parser.error("Sample cap, rounds and local epochs must be positive")
    if args.batch_size < 1 or args.lr <= 0 or args.fedprox_mu < 0:
        parser.error("Invalid batch size, learning rate or proximal parameter")
    train_devices, validation_device = split_source_devices(
        args.heldout, args.validation
    )
    if args.backend == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA backend requested but unavailable")
    if not args.source_root.is_dir():
        parser.error("--source-root directory does not exist")

    # SECURITY/SCIENCE INVARIANT: no target/held-out archive path is opened here.
    sources = [*train_devices, validation_device]
    checked_source_sha256 = (
        verify_source_archive_hashes(args.source_root, args.manifest, sources, args.heldout)
        if args.manifest is not None else {}
    )
    clients = {}
    validation = None
    supports = {}
    header = None
    for device in sources:
        X, y, class_counts, header = load_one_device(
            args.source_root, device, args.max_per_class, args.seed, header
        )
        supports[device] = class_counts
        if device == validation_device:
            validation = (X, y)
        else:
            clients[device] = (X, y)
        print("SOURCE_DEVICE_SAMPLED", device, "rows", len(y), flush=True)

    clients, val, normalization = preprocess_train_only(clients, validation)
    device_backend = torch.device(args.backend)
    methods = {
        "fedavg": pilot_one_method(
            "fedavg", clients, val, args, device_backend
        ),
        "fedprox": pilot_one_method(
            "fedprox", clients, val, args, device_backend
        ),
    }
    output = {
        "status": "EXPLORATORY_SOURCE_ONLY_PILOT",
        "confirmatory": False,
        "heldout_evaluated": False,
        "heldout_archive_opened": False,
        "target_labels_used": False,
        "test_accuracy_claim": None,
        "heldout_device_name_only": args.heldout,
        "source_validation_device": validation_device,
        "training_devices": train_devices,
        "source_archive_names_used": [d + ".zip" for d in sources],
        "source_zip_hashes_recomputed": args.manifest is not None,
        "source_zip_sha256": checked_source_sha256,
        "source_hash_manifest_path": str(args.manifest) if args.manifest else None,
        "hash_scope": "ONLY_EIGHT_SOURCE_ARCHIVES_NEVER_TARGET",
        "source_native_class_counts": supports,
        "source_only_sampled_class_cap": args.max_per_class,
        "changed_native_prevalence_for_debugging": True,
        "preprocessing_fit_device_scope": train_devices,
        "preprocessing_fit_statistics": normalization,
        "protocol_candidate_not_frozen": True,
        "algorithms": methods,
        "hyperparameters": {
            "seed": args.seed, "rounds": args.rounds,
            "local_epochs": args.local_epochs, "batch_size": args.batch_size,
            "lr": args.lr, "fedprox_mu": args.fedprox_mu,
            "backend": args.backend,
        },
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scientific_note": (
            "All diagnostics use a SOURCE-side validation device only. "
            "This stratified debug pilot is not a valid LODO test estimate "
            "and may not be quoted as confirmatory scientific performance."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError("Refusing to overwrite pilot evidence")
    # Write once after successful completion, leaving no false-success JSON.
    with args.output.open("x", encoding="utf8") as f:
        json.dump(output, f, indent=2, allow_nan=False)
    print("SOURCE_ONLY_EXPLORATORY_PILOT_COMPLETE", args.output, flush=True)


if __name__ == "__main__":
    main()
