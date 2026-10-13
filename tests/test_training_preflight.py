"""Synthetic preflight checks: no model training, no TEST opening."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, REPO / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


preflight = load("strict_real_preflight", "scripts/training/preflight_real_training.py")
guard_tests = load("fixture_for_preflight", "tests/test_strict_test_guard.py")


class ExecutionPreflightTests(unittest.TestCase):
    def test_no_real_data_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            record = preflight.assess(
                "ciciot2023", 42, "stage3", root / "missing_split",
                root / "missing_features.json", root / "stage3", root / "stage4",
                check_dependencies=False)
            self.assertFalse(record["ready_for_execution"])
            self.assertTrue(any("Missing split manifest" in x for x in record["blockers"]))
            self.assertTrue(any("TRAIN-only feature JSON" in x for x in record["blockers"]))
            self.assertFalse(record["test_csv_opened"])

    def test_stage4_sources_verified_without_test_csv(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            dataset, seed, split_root, stage3_root, old_stage4, feature = (
                guard_tests.fixture(root))
            for file in (split_root / dataset / "test").glob("*.csv"):
                file.unlink()
            result = preflight.assess(
                dataset, seed, "stage4", split_root, feature, stage3_root,
                root / "not_trained_stage4_yet", check_dependencies=False)
            self.assertFalse(result["blockers"])
            self.assertFalse(result["ready_for_execution"])  # dependencies unverified
            self.assertEqual(len(result["verified_clients"]), 5)
            self.assertFalse(result["test_csv_opened"])

    def test_wrong_seed_blocks_teachers(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            ds, seed, split_root, stage3_root, old_stage4, features = guard_tests.fixture(root)
            result = preflight.assess(ds, seed + 1, "stage4", split_root, features,
                                      stage3_root, root / "stage4_new",
                                      check_dependencies=False)
            self.assertFalse(result["ready_for_execution"])
            self.assertTrue(any("Missing Stage 3 artifact" in x for x in result["blockers"]))

    def test_modified_seed_scoped_checkpoint_blocks_training(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            ds, seed, split_root, stage3_root, old_stage4, features = guard_tests.fixture(root)
            target = stage3_root / ds / f"seed_{seed}" / "Link_1_Core" / "mamba_val_best.pt"
            target.write_bytes(b"corrupt")
            result = preflight.assess(ds, seed, "stage4", split_root, features,
                                      stage3_root, root / "stage4_new",
                                      check_dependencies=False)
            self.assertTrue(any("provenance mismatch" in x for x in result["blockers"]))

    def test_existing_seed_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            ds, seed, split_root, stage3_root, old_stage4, features = guard_tests.fixture(root)
            record = preflight.assess(ds, seed, "stage4", split_root, features,
                                      stage3_root, old_stage4,
                                      check_dependencies=False)
            self.assertTrue(any("already exist" in x for x in record["blockers"]))


if __name__ == "__main__":
    unittest.main()
