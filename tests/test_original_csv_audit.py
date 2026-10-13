"""Synthetic source-integrity checks; never use mock labels as benchmark evidence."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "data" / "audit_original_csvs.py"
spec = importlib.util.spec_from_file_location("raw_csv_audit", MODULE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def make_csv(path, rows=None, header=("flow", "Label")):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = rows if rows is not None else [
        ("1", "Normal"), ("2", "AttackX"), ("3", "AttackX")
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        wr = csv.writer(file)
        wr.writerow(header)
        wr.writerows(rows)


class RawSourceAuditTests(unittest.TestCase):
    def test_full_local_inventory_does_not_certify_severity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_csv(root / "raw" / "capture1.csv")
            make_csv(root / "raw" / "nested" / "capture2.csv",
                     rows=[("2", "Normal"), ("3", "AttackY")])
            out = root / "output.json"
            report = audit.inventory("diad2024", root / "raw", "Label", out,
                                     modality="flow")
            self.assertEqual(report["source_files_count"], 2)
            self.assertEqual(report["original_rows"], 5)
            self.assertEqual(report["all_original_label_counts"],
                             {"AttackX": 2, "AttackY": 1, "Normal": 2})
            self.assertFalse(report["severity_mapping_verified"])
            self.assertFalse(report["external_source_authenticity_reviewed"])
            self.assertFalse(report["reference_sha256_confirmed"])
            self.assertTrue(out.is_file())

    def test_reject_derived_severity_as_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_csv(root / "raw" / "capture.csv")
            with self.assertRaisesRegex(ValueError, "original raw label"):
                audit.inventory("ciciot2023", root / "raw", "severity",
                                root / "result.json", modality="flow")

    def test_reject_invented_label_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_csv(root / "raw" / "capture.csv")
            with self.assertRaisesRegex(ValueError, "missing"):
                audit.inventory("diad2024", root / "raw", "is_attack",
                                root / "result.json", modality="flow")

    def test_refuses_to_reuse_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_csv(root / "raw" / "file.csv")
            out = root / "results.json"
            audit.inventory("ciciot2023", root / "raw", "Label", out,
                            modality="flow")
            with self.assertRaises(FileExistsError):
                audit.inventory("ciciot2023", root / "raw", "Label", out,
                                modality="flow")

    def test_reference_hash_required_to_confirm_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_csv(root / "raw" / "file.csv")
            archive = root / "SOURCE_ARCHIVE.zip"
            archive.write_bytes(b"synthetic test fixture, NOT actual benchmark")
            with self.assertRaisesRegex(ValueError, "differs"):
                audit.inventory("diad2024", root / "raw", "Label", root / "bad.json",
                                modality="flow", source_artifact=archive,
                                reference_sha256="0" * 64)
            self.assertFalse((root / "bad.json").exists())
            report = audit.inventory(
                "diad2024", root / "raw", "Label", root / "good.json",
                modality="flow", source_artifact=archive,
                reference_sha256=audit.sha256(archive))
            self.assertTrue(report["reference_sha256_confirmed"])
            self.assertFalse(report["external_source_authenticity_reviewed"])

    def test_blank_labels_are_not_filled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_csv(root / "raw" / "file.csv",
                     rows=[("1", "Normal"), ("2", "")])
            with self.assertRaisesRegex(ValueError, "Blank original label"):
                audit.inventory("ciciot2023", root / "raw", "Label",
                                root / "result.json", modality="flow")

    def test_reject_duplicates_in_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_csv(root / "raw" / "file.csv", header=("Label", "Label"))
            with self.assertRaisesRegex(ValueError, "duplicated"):
                audit.inventory("ciciot2023", root / "raw", "Label",
                                root / "result.json", modality="flow")


if __name__ == "__main__":
    unittest.main()
