"""Synthetic TRAIN-only feature provenance checks; no real benchmark scores."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    out = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(out)
    return out


split = load("split_feature_fixture", "scripts/data/split_records_leakfree.py")
sel = load("train_feature_selection", "scripts/data/select_features_train_only.py")
guard = load("feature_gate", "scripts/data/feature_provenance.py")


def fixture(base):
    split_root = base / "split"
    candidate_file = base / "reviewed_candidates.json"
    names = [f"feature_{i}" for i in range(15)]
    candidate_file.write_text(json.dumps({
        "schema": "afras-candidate-feature-review-v1",
        "review_reference": "SYNTHETIC UNIT TEST ONLY",
        "candidate_features": names,
    }))
    for dataset in ("ciciot2023", "diad2024"):
        raw = base / "source" / dataset
        raw.mkdir(parents=True)
        for i in range(5):
            with (raw / f"Link_{i+1}_Core.csv").open("w", newline="") as handle:
                w = csv.DictWriter(handle, fieldnames=names + ["severity"])
                w.writeheader()
                for row in range(250):
                    label = ("High", "Medium", "Low")[row % 3]
                    data = {feat: round((row + 11 * i) % (j + 5) * 0.05 +
                            (2 if j == 0 and label == "High" else 0), 3)
                            for j, feat in enumerate(names)}
                    data["severity"] = label
                    w.writerow(data)
        split.split_dataset(raw, split_root, dataset)
    return split_root, candidate_file


class FeatureSelectionTests(unittest.TestCase):
    def test_only_train_data_used_and_provenance_revalidated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            split_root, candidate = fixture(root)
            # If selector accidentally needs VAL/TEST, this MUST fail.
            for dataset in ("ciciot2023", "diad2024"):
                for part in ("val", "test"):
                    for csvfile in (split_root / dataset / part).glob("*.csv"):
                        csvfile.unlink()
            output = root / "feature_selection.json"
            result = sel.select(split_root, candidate,
                                ["ciciot2023", "diad2024"], output)
            self.assertEqual(len(result["selected_features"]), 14)
            self.assertIn("feature_0", result["selected_features"])
            self.assertEqual(
                guard.validate_train_feature_selection(output, split_root, "ciciot2023"),
                result["selected_features"])
            self.assertEqual(
                guard.validate_train_feature_selection(output, split_root, "diad2024"),
                result["selected_features"])

    def test_invalid_features_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp) / "cand.json"
            f.write_text(json.dumps({
                "schema": "afras-candidate-feature-review-v1",
                "review_reference": "SYNTHETIC TEST ONLY",
                "candidate_features": [f"feat_{i}" for i in range(14)] + ["is_attack"],
            }))
            with self.assertRaisesRegex(ValueError, "Forbidden"):
                sel.candidate_list(f)

    def test_legacy_global_feature_list_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp) / "features.json"
            f.write_text(json.dumps({"selected_features": [f"feature_{i}" for i in range(14)]}))
            with self.assertRaisesRegex(ValueError, "Global or unverified"):
                guard.validate_train_feature_selection(f, temp, "ciciot2023")

    def test_changed_train_is_detected_before_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            split_root, candidate = fixture(root)
            with (split_root / "ciciot2023" / "train" / "Link_1_Core.csv").open("a") as f:
                f.write("tampered\n")
            with self.assertRaisesRegex(ValueError, "Changed TRAIN partition"):
                sel.select(split_root, candidate, ["ciciot2023"], root / "features.json")

    def test_rejects_changed_split_manifest_after_feature_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            split_root, candidate = fixture(root)
            output = root / "features.json"
            sel.select(split_root, candidate, ["ciciot2023"], output)
            manifest = split_root / "ciciot2023" / "manifest.json"
            manifest.write_text(manifest.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "wrong/changed split manifest hash"):
                guard.validate_train_feature_selection(output, split_root, "ciciot2023")

    def test_feature_selector_never_overwrites_prior_results(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            split_root, candidate = fixture(root)
            output = root / "features.json"
            sel.select(split_root, candidate, ["ciciot2023"], output)
            with self.assertRaises(FileExistsError):
                sel.select(split_root, candidate, ["ciciot2023"], output)


if __name__ == "__main__":
    unittest.main()
