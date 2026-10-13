"""Synthetic tests for the TRAIN/VAL-only strict-stage3 file guard."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


splitter = load("strict_split", REPO / "scripts" / "data" / "split_records_leakfree.py")
guard = load("strict_manifest", REPO / "scripts" / "data" / "strict_manifest.py")


def fixture(root):
    source = root / "source" / "Link_1_Core.csv"
    source.parent.mkdir(parents=True)
    with source.open("w", newline="") as file:
        w = csv.DictWriter(file, fieldnames=["feat", "severity"])
        w.writeheader()
        for i in range(250):
            w.writerow({"feat": i, "severity": ["High", "Medium", "Low"][i % 3]})
    out = splitter.split_dataset(source.parent, root / "split", "ciciot2023")
    return out


class ManifestGuardTests(unittest.TestCase):
    def test_validation_does_not_require_test_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = fixture(root)
            (out / "test" / "Link_1_Core.csv").unlink()
            data = guard.validate_stage3_inputs(out, "ciciot2023")
            self.assertEqual(set(data["Link_1_Core"]), {"train", "val"})

    def test_detects_train_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = fixture(root)
            with (out / "train" / "Link_1_Core.csv").open("a") as file:
                file.write("extra,Low\n")
            with self.assertRaisesRegex(guard.StrictManifestError, "Hash mismatch"):
                guard.validate_stage3_inputs(out, "ciciot2023")

    def test_rejects_wrong_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = fixture(Path(tmp))
            with self.assertRaisesRegex(guard.StrictManifestError, "Dataset mismatch"):
                guard.validate_stage3_inputs(out, "diad2024")

    def test_rejects_changed_window_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = fixture(Path(tmp))
            with self.assertRaisesRegex(guard.StrictManifestError, "Window length"):
                guard.validate_stage3_inputs(out, "ciciot2023", window_size=40)

    def test_rejects_malformed_embargo(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = fixture(Path(tmp))
            path = out / "manifest.json"
            metadata = json.loads(path.read_text())
            metadata["links"]["Link_1_Core"]["embargo_rows_at_each_boundary"] = 0
            path.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(guard.StrictManifestError, "Insufficient embargo"):
                guard.validate_stage3_inputs(out, "ciciot2023")


if __name__ == "__main__":
    unittest.main()
