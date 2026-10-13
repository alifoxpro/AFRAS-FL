#!/usr/bin/env python3
"""Inspect and optionally safely extract an OFFICIALLY DOWNLOADED CSV ZIP.

This tool NEVER performs HTTP downloads, bypasses a publisher's download
form, generates labels/features/clients, or trains a model. Researchers
download original archives themselves, keeping provider terms intact.

It checks archive/path integrity and enumerates ACTUAL CSV headers, then
(optionally) atomically extracts ONLY selected CSVs under a size budget.
The SHA-256 recorded here establishes local file identity, not authenticity
unless compared to an independently sourced publisher digest.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

SOURCE_PAGES = {
    "ciciot2023": "https://www.unb.ca/cic/datasets/iotdataset-2023.html",
    "diad2024": "https://www.unb.ca/cic/datasets/iot-diad-2024.html",
}
REPORT_SCHEMA = "afras-official-archive-preflight-v1"
_GIB = 1024 ** 3


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_name(member):
    """Reject ZIP-slip, drive paths, hidden tricks, symlinks and collisions."""
    name = member.filename
    if not name or "\x00" in name or "\\" in name or ":" in name:
        raise ValueError(f"Unsafe archive member path: {name!r}")
    stripped = name[:-1] if member.is_dir() else name
    if not stripped or stripped.startswith("/") or "//" in stripped:
        raise ValueError(f"Unsafe absolute or malformed member: {name!r}")
    parts = stripped.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"Unsafe traversal member: {name!r}")
    if member.create_system == 3:
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise ValueError(f"Archive contains unsafe symbolic link: {name!r}")
    return PurePosixPath(*parts)


def inspect(archive, dataset, modality, csv_prefix=None, label_column=None,
            max_expanded_gib=35, max_members=20000,
            expected_archive_sha256=None):
    """Read archive metadata + CSV headers, never any attack-label rows."""
    archive = Path(archive).resolve()
    if dataset not in SOURCE_PAGES:
        raise ValueError("Unknown source dataset")
    if modality not in ("flow", "packet"):
        raise ValueError("Explicit flow or packet modality required")
    if dataset == "ciciot2023" and modality != "flow":
        raise ValueError("This protocol expects the official CICIoT2023 CSV features")
    if not archive.is_file():
        raise FileNotFoundError(f"Original ZIP not found: {archive}")
    if not archive.name.lower().endswith(".zip"):
        raise ValueError("The input must be a ZIP, not a path pretending to be an archive")
    if max_expanded_gib <= 0 or max_members <= 0:
        raise ValueError("Extraction limits must be positive")
    if expected_archive_sha256 is not None and not re.fullmatch(
            r"[0-9a-f]{64}", expected_archive_sha256):
        raise ValueError("Expected SHA-256 must be 64 lowercase hex digits")
    prefix = None
    if csv_prefix:
        p = csv_prefix.replace("\\", "/").strip("/")
        if not p or any(x in ("", ".", "..") for x in p.split("/")):
            raise ValueError("Invalid CSV directory prefix")
        prefix = p + "/"

    selected = []
    paths_seen = set()
    expanded = 0
    candidate_headers = {}
    with zipfile.ZipFile(archive) as zipf:
        infos = zipf.infolist()
        if len(infos) > max_members:
            raise ValueError("Archive contains too many members")
        for member in infos:
            safe = _safe_name(member)
            canonical = str(safe).casefold()
            if canonical in paths_seen:
                raise ValueError(f"Duplicate/case-colliding ZIP path: {safe}")
            paths_seen.add(canonical)
            if member.is_dir():
                continue
            if member.flag_bits & 0x1:
                raise ValueError("Encrypted archive members are unsupported")
            if member.file_size > int(max_expanded_gib * _GIB):
                raise ValueError("One file exceeds uncompressed ZIP safety budget")
            if member.file_size and member.file_size > max(member.compress_size, 1) * 10000:
                raise ValueError("Suspicious compression ratio in ZIP")
            if not str(safe).lower().endswith(".csv"):
                continue
            if prefix and not str(safe).startswith(prefix):
                continue
            expanded += member.file_size
            if expanded > int(max_expanded_gib * _GIB):
                raise ValueError("Uncompressed CSV total exceeds safety budget")
            with zipf.open(member) as stream:
                wrapper = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
                try:
                    head = next(csv.reader(wrapper), None)
                finally:
                    wrapper.detach()
            if (not head or any(not col.strip() for col in head)
                    or len(head) != len(set(head))):
                raise ValueError(f"Missing/duplicate/blank CSV headers: {safe}")
            if label_column and label_column not in head:
                raise ValueError(
                    f"Declared label column {label_column!r} absent from {safe}")
            key = json.dumps(head, ensure_ascii=False)
            candidate_headers.setdefault(key, []).append(str(safe))
            selected.append({
                "path": str(safe), "uncompressed_bytes": member.file_size,
                "compressed_bytes": member.compress_size,
                "crc32_zip_metadata": f"{member.CRC:08x}",
                "header_columns": head,
            })
    if not selected:
        raise ValueError("No CSV files matched the requested directory/modality")
    if len(candidate_headers) != 1:
        raise ValueError(
            "Mixed CSV schemas: select the appropriate flow/packet directory "
            "with --csv-prefix before harmonization")
    actual = sha256(archive)
    if expected_archive_sha256 is not None and actual != expected_archive_sha256:
        raise ValueError("Archive SHA-256 differs from independently supplied digest")
    return {
        "schema": REPORT_SCHEMA,
        "dataset": dataset,
        "modality": modality,
        "official_source_page": SOURCE_PAGES[dataset],
        "original_archive_name": archive.name,
        "original_archive_bytes": archive.stat().st_size,
        "original_archive_sha256": actual,
        "expected_sha256_match": expected_archive_sha256 is not None,
        "external_authenticity_independently_verified": False,
        "csv_prefix": prefix,
        "label_column_explicitly_checked": label_column,
        "csv_files": selected,
        "total_csv_uncompressed_bytes": expanded,
        "selected_csv_count": len(selected),
        "original_csv_headers": selected[0]["header_columns"],
        "source_real_link_ids_verified": False,
        "severity_policy_verified": False,
        "warnings": [
            "Local SHA-256 identifies bytes; it does not prove publisher authenticity",
            "No High/Medium/Low mapping or artificial link labels are generated",
            "Original CSV filenames/row order are NOT proof of chronology",
            "Do not reuse downstream TEST rows for mapping or feature choices",
        ],
    }


def extract_selected(archive, report, output_root, max_expanded_gib=35):
    """Atomic extraction with checked paths and bounded streaming writes."""
    output_root = Path(output_root).resolve()
    archive = Path(archive).resolve()
    destination = output_root / report["dataset"] / report["modality"]
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing raw CSVs: {destination}")
    if output_root.is_relative_to(archive.parent) and output_root == archive.parent:
        raise ValueError("Output directory must differ from the original ZIP parent")
    if report["original_archive_sha256"] != sha256(archive):
        raise ValueError("Archive changed between inspection and extraction")
    if report["total_csv_uncompressed_bytes"] > int(max_expanded_gib * _GIB):
        raise ValueError("Archive exceeds configured extraction budget")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
            dir=destination.parent, prefix=".raw-csv-stage-") as tmp:
        stage = Path(tmp)
        extracted = 0
        with zipfile.ZipFile(archive) as zipf:
            for entry in report["csv_files"]:
                name = entry["path"]
                member = zipf.getinfo(name)
                safe = _safe_name(member)
                if member.file_size != entry["uncompressed_bytes"]:
                    raise ValueError("ZIP member changed since inspection")
                target = stage.joinpath(*safe.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zipf.open(member) as inp, target.open("xb") as out:
                    count = 0
                    while True:
                        block = inp.read(1024 * 1024)
                        if not block:
                            break
                        count += len(block)
                        extracted += len(block)
                        if (count > entry["uncompressed_bytes"]
                                or extracted > int(max_expanded_gib * _GIB)):
                            raise ValueError("Expanded member exceeded ZIP safety limit")
                        out.write(block)
                    if count != entry["uncompressed_bytes"]:
                        raise ValueError("ZIP member produced unexpected uncompressed size")
        os.rename(stage, destination)
    return destination


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", required=True, choices=sorted(SOURCE_PAGES))
    p.add_argument("--modality", required=True, choices=("flow", "packet"))
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--label-column", help="Exact original label header once reviewed")
    p.add_argument("--csv-prefix", help="Subfolder inside ZIP containing one CSV schema")
    p.add_argument("--expected-sha256", help="Digest independently provided by dataset distributor")
    p.add_argument("--max-expanded-gib", type=float, default=35)
    p.add_argument("--max-members", type=int, default=20000)
    p.add_argument("--extract", action="store_true", help="Explicitly extract CSVs only")
    p.add_argument("--output-root", type=Path, default=Path("data/raw_official_csv"))
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    if a.report.exists():
        p.error(f"Refusing to overwrite existing audit: {a.report}")
    result = inspect(
        a.archive, a.dataset, a.modality, a.csv_prefix, a.label_column,
        a.max_expanded_gib, a.max_members, a.expected_sha256)
    if a.extract:
        output = extract_selected(a.archive, result, a.output_root,
                                  a.max_expanded_gib)
        result["extracted_csv_root"] = str(output)
    else:
        result["extracted_csv_root"] = None
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"Inspected {result['selected_csv_count']} CSVs; "
          f"SHA256={result['original_archive_sha256']}; "
          f"extracted={bool(a.extract)}. No dataset authenticity claimed.")


if __name__ == "__main__":
    main()
