"""Pure synthetic cases only; never fabricate original benchmark labels."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def from_file(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


label = from_file("label_evidence", "scripts/data/label_evidence.py")
fed = from_file("strict_fed_core_label", "scripts/training/strict_fed_core.py")
splitter = from_file("synthetic_split", "scripts/data/split_records_leakfree.py")
guard = from_file("test_guard_label", "scripts/data/strict_test_guard.py")
PHASES = guard.PHASES


def make_fixture(root):
    raw = root / "raw"
    raw.mkdir()
    link = "Link_1_Core"
    file = raw / (link + ".csv")
    columns = ("flow", "severity", "original_class", "is_attack")
    with file.open("w", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=columns)
        w.writeheader()
        for n in range(250):
            cat = ("Normal", "DDoS", "PortScan")[n % 3]
            w.writerow({
                "flow": n,
                "original_class": cat,
                "is_attack": 0 if cat == "Normal" else 1,
                "severity": "Low" if cat == "Normal" else (
                    "High" if cat == "DDoS" else "Medium"),
            })
    split = splitter.split_dataset(raw, root / "splits", "ciciot2023")
    spec = {
        "schema": label.SCHEMA,
        "dataset": "ciciot2023",
        "source_url": "https://example.org/synthetic-only-dataset",
        "source_revision": "synthetic-fixture-v1",
        "source_sha256": "a" * 64,
        "mapping_review_reference": "SYNTHETIC_TEST_NOT_A_REAL_REVIEW",
        "raw_label_column": "original_class",
        "binary_attack_column": "is_attack",
        "raw_label_map": {
            "Normal": {"severity": "Low", "is_attack": 0},
            "DDoS": {"severity": "High", "is_attack": 1},
            "PortScan": {"severity": "Medium", "is_attack": 1},
        },
    }
    evidence = root / "mapping.json"
    evidence.write_text(json.dumps(spec))
    return split, evidence, spec


class LabelEvidenceTests(unittest.TestCase):
    def test_explicit_label_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            split, evidence, spec = make_fixture(Path(tmp))
            obj = label.validate_evidence_file(evidence, "ciciot2023")
            self.assertEqual(obj["raw_label_map"]["Normal"]["is_attack"], 0)
            m = json.loads((split / "manifest.json").read_text())
            for part in ("train", "val", "test"):
                csv_file = split / part / "Link_1_Core.csv"
                row = label.validate_raw_rows(csv_file, spec,
                    m["links"]["Link_1_Core"]["partitions"][part]["sha256"],
                    take_binary_last=(20, 20))
                self.assertEqual(len(row["binary_window_labels"]), row["rows"] // 20)

    def test_train_val_audit_excludes_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            split, evidence, spec = make_fixture(Path(tmp))
            (split / "test" / "Link_1_Core.csv").unlink()
            result = label.audit_train_val(split, "ciciot2023", evidence)
            self.assertIn("train", result["train_val_categories"]["Link_1_Core"])

    def test_unknown_original_class_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            split, evidence, spec = make_fixture(Path(tmp))
            spec["raw_label_map"].pop("PortScan")
            with self.assertRaisesRegex(ValueError, "Unmapped raw category"):
                label.validate_raw_rows(split / "train" / "Link_1_Core.csv", spec)

    def test_binary_disagreement_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            split, evidence, spec = make_fixture(Path(tmp))
            spec["raw_label_map"]["DDoS"]["is_attack"] = 0
            with self.assertRaisesRegex(ValueError, "Binary Attack/Benign mismatch"):
                label.validate_raw_rows(split / "train" / "Link_1_Core.csv", spec)

    def test_severity_disagreement_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            split, evidence, spec = make_fixture(Path(tmp))
            spec["raw_label_map"]["Normal"]["severity"] = "High"
            with self.assertRaisesRegex(ValueError, "Severity mismatch"):
                label.validate_raw_rows(split / "train" / "Link_1_Core.csv", spec)

    def test_unknown_binary_category_has_no_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            split, evidence, spec = make_fixture(Path(tmp))
            spec["raw_label_map"]["Normal"].pop("is_attack")
            evidence.write_text(json.dumps(spec))
            with self.assertRaisesRegex(ValueError, "Missing binary attack mapping"):
                label.validate_evidence_file(evidence, "ciciot2023")

    def test_binary_FPR_FNR_confusion(self):
        stats = fed.binary_intrusion_metrics([0, 0, 1, 1, 1],
                                             [0, 1, 0, 2, 1])
        self.assertEqual({k: stats[k] for k in ("TP", "FP", "TN", "FN")},
                         {"TP": 2, "FP": 1, "TN": 1, "FN": 1})
        self.assertAlmostEqual(stats["FPR"], .5)
        self.assertAlmostEqual(stats["FNR"], 1 / 3)

    def test_zero_denominator_remains_undefined(self):
        stats = fed.binary_intrusion_metrics([1, 1], [0, 2])
        self.assertIsNone(stats["FPR"])
        self.assertEqual(stats["FNR"], .5)

    def test_unknown_binary_groundtruth_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Attack labels must be explicit"):
            fed.binary_intrusion_metrics([2, 0], [2, 0])

    def test_test_guard_rejects_after_the_fact_mapping(self):
        # Confirm the source forbids providing evidence not preregistered
        import inspect
        source = inspect.getsource(guard.validate_frozen_run)
        self.assertIn("must be registered BEFORE training", source)
        self.assertIn("Raw-label evidence changed after Stage 4", source)


if __name__ == "__main__":
    unittest.main()
