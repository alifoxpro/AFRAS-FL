"""Synthetic ZIP fixtures only; never claims authentic CIC data access."""
import csv
import importlib.util
import io
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "scripts/data/prepare_official_dataset_archive.py"
spec = importlib.util.spec_from_file_location("official_archive_preflight", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def csv_bytes(labels=("BenignTraffic", "DDoS-UDP_Flood")):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["flow_duration", "Rate", "label"])
    for i, value in enumerate(labels):
        writer.writerow([i + .5, 2 * i, value])
    return stream.getvalue().encode("utf-8")


def make_zip(root, entries=None):
    archive = root / "original_CIC.zip"
    entries = entries if entries is not None else {
        "CSV/part-0.csv": csv_bytes(),
        "CSV/part-1.csv": csv_bytes(("BenignTraffic", "Recon-PortScan")),
        "README.txt": b"synthetic example archive only",
    }
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for path, data in entries.items():
            zipf.writestr(path, data)
    return archive


class DownloadedArchiveTests(unittest.TestCase):
    def test_archive_headers_and_sha_are_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = make_zip(root)
            report = mod.inspect(
                archive, "ciciot2023", "flow", "CSV", "label",
                expected_archive_sha256=mod.sha256(archive))
            self.assertEqual(report["selected_csv_count"], 2)
            self.assertEqual(report["original_csv_headers"],
                             ["flow_duration", "Rate", "label"])
            self.assertTrue(report["expected_sha256_match"])
            self.assertFalse(report["external_authenticity_independently_verified"])
            self.assertFalse(report["source_real_link_ids_verified"])
            self.assertFalse(report["severity_policy_verified"])

    def test_safe_explicit_csv_extraction_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = make_zip(root)
            preflight = mod.inspect(archive, "ciciot2023", "flow",
                                    csv_prefix="CSV")
            output = mod.extract_selected(archive, preflight, root / "extracted")
            self.assertEqual((output / "CSV" / "part-0.csv").read_bytes(), csv_bytes())
            self.assertFalse((output / "README.txt").exists())
            with self.assertRaises(FileExistsError):
                mod.extract_selected(archive, preflight, root / "extracted")

    def test_reject_bad_zip_path_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = make_zip(root, {"../../other.csv": csv_bytes()})
            with self.assertRaisesRegex(ValueError, "traversal"):
                mod.inspect(archive, "ciciot2023", "flow")
            self.assertFalse((root / "other.csv").exists())

    def test_reject_windows_drive_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = make_zip(root, {"C:/outside.csv": csv_bytes()})
            with self.assertRaisesRegex(ValueError, "Unsafe archive"):
                mod.inspect(archive, "ciciot2023", "flow")

    def test_reject_member_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "original_CIC.zip"
            with zipfile.ZipFile(archive, "w") as zipf:
                member = zipfile.ZipInfo("CSV/source.csv")
                member.create_system = 3
                member.external_attr = (stat.S_IFLNK | 0o777) << 16
                zipf.writestr(member, b"/etc/passwd")
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                mod.inspect(archive, "ciciot2023", "flow")

    def test_reject_mixed_modality_csv_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mixed = make_zip(root, {
                "flow/flow.csv": csv_bytes(),
                "packet/packet.csv": b"jitter,Label 2 for AD\n1,attack\n",
            })
            with self.assertRaisesRegex(ValueError, "Mixed CSV schemas"):
                mod.inspect(mixed, "diad2024", "flow")
            ok = mod.inspect(mixed, "diad2024", "flow", csv_prefix="flow")
            self.assertEqual(ok["selected_csv_count"], 1)

    def test_reject_label_header_not_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = make_zip(root)
            with self.assertRaisesRegex(ValueError, "Declared label"):
                mod.inspect(archive, "ciciot2023", "flow", "CSV", "attack_name")

    def test_wrong_reference_sha_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = make_zip(root)
            with self.assertRaisesRegex(ValueError, "differs"):
                mod.inspect(archive, "ciciot2023", "flow",
                            expected_archive_sha256="0" * 64)

    def test_reject_extraction_size_over_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = make_zip(root)
            with self.assertRaisesRegex(ValueError, "budget"):
                mod.inspect(archive, "ciciot2023", "flow",
                            max_expanded_gib=1e-11)

    def test_csv_input_is_not_valid_as_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "some.csv"
            path.write_bytes(csv_bytes())
            with self.assertRaisesRegex(ValueError, "must be a ZIP"):
                mod.inspect(path, "ciciot2023", "flow")

    def test_reject_duplicate_case_colliding_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = make_zip(root, {
                "CSV/Part_1.csv": csv_bytes(),
                "CSV/part_1.csv": csv_bytes(),
            })
            with self.assertRaisesRegex(ValueError, "Duplicate/case-colliding"):
                mod.inspect(archive, "ciciot2023", "flow")


if __name__ == "__main__":
    unittest.main()
