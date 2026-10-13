"""Validate train/val inputs against the immutable ordered-split manifest.

Critically this module never reads TEST CSVs or checks TEST file contents.
It only verifies TRAIN and VAL files already created by the split utility.
"""
import hashlib
import json
from pathlib import Path

SUPPORTED_SCHEMA = "afras-fl-strict-ordered-split-v1"


class StrictManifestError(ValueError):
    pass


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_stage3_inputs(split_dir, dataset, window_size=20):
    """Return {link: {train: Path, val: Path}} after checksum validation.

    TRAIN/VAL are validated against their recorded manifest hashes and record
    counts; TEST is neither opened, listed, nor checked. This verifies file
    identity, not whether the original upstream feature engineering leaked.
    """
    root = Path(split_dir).resolve()
    manifest_file = root / "manifest.json"
    if not manifest_file.is_file():
        raise StrictManifestError(f"Missing strict-split manifest: {manifest_file}")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("schema") != SUPPORTED_SCHEMA:
        raise StrictManifestError("Unsupported split manifest schema")
    if manifest.get("dataset") != dataset:
        raise StrictManifestError("Dataset mismatch in strict-split manifest")
    if manifest.get("window_size") != window_size:
        raise StrictManifestError("Window length differs from split embargo specification")
    if manifest.get("method") != "source_order_with_embargo; split_before_windowing":
        raise StrictManifestError("Unsupported split method")
    links = manifest.get("links")
    if not isinstance(links, dict) or not links:
        raise StrictManifestError("No links in split manifest")
    verified = {}
    for link, entry in sorted(links.items()):
        if not link.startswith("Link_") or "/" in link or "\\" in link or ".." in link:
            raise StrictManifestError(f"Unsafe or unexpected link name: {link}")
        ranges = entry.get("ranges_half_open", {})
        if entry.get("embargo_rows_at_each_boundary", 0) < window_size - 1:
            raise StrictManifestError("Insufficient embargo in split manifest")
        try:
            train_end = ranges["train"][1]
            val_start, val_end = ranges["val"]
            test_start = ranges["test"][0]
        except (KeyError, IndexError, TypeError) as exc:
            raise StrictManifestError("Missing or malformed partition row ranges") from exc
        if train_end + window_size - 1 > val_start or val_end + window_size - 1 > test_start:
            raise StrictManifestError("Overlapping or insufficiently separated partitions")
        verified[link] = {}
        for split in ("train", "val"):
            meta = entry.get("partitions", {}).get(split)
            if not isinstance(meta, dict) or meta.get("records", 0) < window_size:
                raise StrictManifestError(f"{link}/{split} has too few records")
            expected_path = root / split / (link + ".csv")
            # Reject substitutions, directory traversal and unexpected output layout.
            if meta.get("relative_path") != f"{split}/{link}.csv":
                raise StrictManifestError(f"Unexpected {split} file path in manifest")
            path = expected_path.resolve()
            if path.parent != (root / split).resolve() or not path.is_file():
                raise StrictManifestError(f"Missing {split} file: {expected_path}")
            if _sha256(path) != meta.get("sha256"):
                raise StrictManifestError(f"Hash mismatch: {expected_path}")
            verified[link][split] = path
    return verified
