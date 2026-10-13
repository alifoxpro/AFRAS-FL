"""Strict tests of declared mapping vs raw CSV vocabulary; synthetic only."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT / file)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


audit = load("audit_original_for_map", "scripts/data/audit_original_csvs.py")
review = load("review_category_mapping", "scripts/data/review_raw_category_mapping.py")


def fixture(root):
    raw = root / "source"
    raw.mkdir()
    f = raw / "original.csv"
    with f.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=["originalLabel", "measurement"])
        w.writeheader()
        for i in range(240):
            w.writerow({"originalLabel": ("BENIGN", "FLOOD", "RECON")[i % 3],
                        "measurement": str(i)})
    archive = root / "source_archive.test"
    archive.write_bytes(b"fixture only not original source archive")
    inventory = root / "inventory.json"
    audit.inventory("diad2024", raw, "originalLabel", inventory,
                    modality="flow", source_artifact=archive,
                    reference_sha256=audit.sha256(archive))
    mapping = {
        "schema": "afras-raw-label-evidence-v1",
        "dataset": "diad2024",
        "source_url": audit.OFFICIAL_PAGES["diad2024"],
        "source_revision": "SYNTHETIC_TEST_ONLY",
        "source_sha256": audit.sha256(archive),
        "mapping_review_reference": "NOT-A-REAL-REVIEW",
        "raw_label_column": "originalLabel",
        "binary_attack_column": "future_derived_attack_flag",
        "raw_label_map": {
            "BENIGN": {"severity": "Low", "is_attack": 0},
            "FLOOD": {"severity": "High", "is_attack": 1},
            "RECON": {"severity": "Medium", "is_attack": 1},
        },
    }
    mp = root / "reviewed_mapping.json"
    mp.write_text(json.dumps(mapping))
    return inventory, mp, mapping


class ReviewedMappingCoverageTests(unittest.TestCase):
    def test_complete_coverage_without_claiming_authenticity(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv, mp, spec = fixture(Path(tmp))
            result = review.review_category_mapping(inv, mp, "diad2024")
            self.assertTrue(result["complete_category_coverage"])
            self.assertEqual(result["binary_class_counts"]["0_benign"], 80)
            self.assertEqual(result["binary_class_counts"]["1_attack"], 160)
            self.assertEqual(result["severity_class_counts"],
                             {"High": 80, "Medium": 80, "Low": 80})
            self.assertTrue(result["remaining_manual_gate"])

    def test_extra_or_missing_raw_categories_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv, mp, spec = fixture(Path(tmp))
            del spec["raw_label_map"]["RECON"]
            mp.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, "Incomplete/excess"):
                review.review_category_mapping(inv, mp, "diad2024")

    def test_unverified_severity_policy_rejects_incomplete_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv, mp, spec = fixture(Path(tmp))
            spec["raw_label_map"]["RECON"]["severity"] = "High"
            mp.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, "All three severity"):
                review.review_category_mapping(inv, mp, "diad2024")

    def test_original_archive_digest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv, mp, spec = fixture(Path(tmp))
            spec["source_sha256"] = "0"*64
            mp.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, "archive/record hash differs"):
                review.review_category_mapping(inv, mp, "diad2024")

    def test_fake_official_source_page_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv, mp, spec = fixture(Path(tmp))
            spec["source_url"] = "https://example.org/fake-dataset"
            mp.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, "official benchmark documentation"):
                review.review_category_mapping(inv, mp, "diad2024")


if __name__ == "__main__":
    unittest.main()
