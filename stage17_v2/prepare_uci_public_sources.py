#!/usr/bin/env python3
"""Stage 17 V2: prepare SOURCE-ONLY native archives from the official UCI ZIP.

This helper is intended for a disposable, exploratory GitHub Actions runner.
It copies only the eight source devices' file members into separate native-format
device ZIP wrappers. It NEVER opens, extracts or parses held-out-device members.

Input package: official N-BaIoT original UCI download (CC BY 4.0)
  https://doi.org/10.24432/C5RC8J
The downloaded outer ZIP includes target bytes as part of the transport object;
a literal "held-out bytes were never downloaded" claim would be false.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from source_only_pilot import DEVICES, split_source_devices

UCI_URL = "https://archive.ics.uci.edu/static/public/442/detection+of+iot+botnet+attacks+n+baiot.zip"


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as fd:
        for chunk in iter(lambda: fd.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def desired_members(device):
    expected = [f"{device}/benign_traffic.csv", f"{device}/gafgyt_attacks.rar"]
    if device not in DEVICES[:2]:
        expected.append(f"{device}/mirai_attacks.rar")
    return expected


def find_unique_members(outer: zipfile.ZipFile, sources):
    names = [i.filename for i in outer.infolist() if not i.is_dir()]
    files = {}
    for device in sources:
        for expected in desired_members(device):
            candidates = [
                n for n in names if n == expected or n.endswith("/" + expected)
            ]
            if len(candidates) != 1:
                raise RuntimeError(
                    "Official outer archive does not contain exactly one: "
                    + expected + " (matches=" + str(len(candidates)) + ")"
                )
            files[expected] = candidates[0]
    if len(files) != sum(len(desired_members(d)) for d in sources):
        raise RuntimeError("Unexpected source file accounting")
    return files


def pack_sources(outer_path: Path, root: Path, heldout: str, validation: str):
    train, val = split_source_devices(heldout, validation)
    sources = [*train, val]
    if heldout in sources or len(sources) != 8:
        raise RuntimeError("Violation of eight-source-only invariant")
    root.mkdir(parents=True, exist_ok=True)
    records = []
    with zipfile.ZipFile(outer_path, "r") as outer:
        matches = find_unique_members(outer, sources)
        for device in sources:
            dest = root / (device + ".zip")
            if dest.exists():
                raise FileExistsError(dest)
            temporary = root / (device + ".zip.part")
            temporary.unlink(missing_ok=True)
            inner = []
            try:
                with zipfile.ZipFile(
                    temporary, mode="x", compression=zipfile.ZIP_STORED,
                    allowZip64=True
                ) as out:
                    for local_name in desired_members(device):
                        source_name = matches[local_name]
                        digest = hashlib.sha256()
                        length = 0
                        # Reading outer.open verifies official downloaded ZIP CRC
                        # for that member as it reaches EOF.
                        with outer.open(source_name, "r") as fd:
                            with out.open(local_name, mode="w", force_zip64=True) as dst:
                                while True:
                                    data = fd.read(1 << 20)
                                    if not data:
                                        break
                                    length += len(data)
                                    digest.update(data)
                                    dst.write(data)
                        expected_bytes = outer.getinfo(source_name).file_size
                        if length != expected_bytes:
                            raise ValueError("Native member size mismatch: " + local_name)
                        inner.append({
                            "source_entry": source_name,
                            "dest_entry": local_name,
                            "bytes": length,
                            "source_entry_sha256": digest.hexdigest(),
                        })
                        print("COPIED_SOURCE_MEMBER", local_name, length, flush=True)
                temporary.rename(dest)
            finally:
                temporary.unlink(missing_ok=True)
            records.append({
                "device": device,
                "source_zip": str(dest),
                "source_zip_sha256": sha256_file(dest),
                "inner_files": inner,
            })
    return {
        "status": "OFFICIAL_PUBLIC_UCI_SOURCE_MEMBERS_STAGED_EXPLORATORY",
        "publisher_source": UCI_URL,
        "citation": "Meidan et al. (2018), UCI Dataset 442, DOI 10.24432/C5RC8J",
        "license": "CC-BY-4.0",
        "outer_archive_sha256": sha256_file(outer_path),
        "heldout_device_name_only": heldout,
        "heldout_member_contents_opened": False,
        "outer_download_transport_includes_heldout_compressed_bytes": True,
        "validation_device": validation,
        "training_devices": train,
        "source_member_count": sum(len(r["inner_files"]) for r in records),
        "device_files": records,
        "confirmatory": False,
        "warnings": [
            "Direct UCI HTTP acquisition is documented but no official published SHA-256 attestation is assumed.",
            "Only source-device member bytes are decoded, hashed and repacked.",
            "This exploratory source-only debug protocol is not the final eight-training-client LODO test.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--outer-zip", required=True, type=Path)
    p.add_argument("--source-root", required=True, type=Path)
    p.add_argument("--record", required=True, type=Path)
    p.add_argument("--heldout", default=DEVICES[0], choices=DEVICES)
    p.add_argument("--validation", default=DEVICES[1], choices=DEVICES)
    args = p.parse_args()
    if not args.outer_zip.is_file():
        p.error("Official outer ZIP does not exist")
    if args.record.exists():
        raise FileExistsError(args.record)
    result = pack_sources(
        args.outer_zip, args.source_root, args.heldout, args.validation
    )
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(result, indent=2), encoding="utf8")
    print("EIGHT_SOURCE_NATIVE_ARCHIVES_READY", args.record, flush=True)


if __name__ == "__main__":
    main()
