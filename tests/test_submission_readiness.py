"""Synthetic source-only submission gates; no actual benchmark/test data used."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = (Path(__file__).resolve().parents[1] /
       "scripts/analysis/audit_submission_readiness.py")
spec = importlib.util.spec_from_file_location("readiness_source_audit", SRC)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def specimen(root, paper_class=r"\documentclass[journal]{IEEEtran}", redlines=True):
    paper = root / "paper"
    paper.mkdir(parents=True, exist_ok=True)
    parts = [
        paper_class,
        r"\begin{document}",
        "Two-sided Welch $t$-tests with $n = 50$ evaluation episodes.",
        r"CICIoT2023 p = 1.8 \times 10^{-15}",
        r"DIAD2024 & B4 & $0.9213$ & $0.0739$ & $2$ \\",
        r"\end{document}",
    ]
    if redlines:
        parts.insert(3, r"\rev{This is a tracked revision.}")
    (paper / "main.tex").write_text("\n".join(parts), encoding="utf-8")
    return root


def ids(result):
    return {gate["id"]: gate for gate in result["gates"]}


class FinalReadinessAuditTests(unittest.TestCase):
    def test_missing_benchmark_data_and_ieee_paper_are_not_ready_for_mdpi(self):
        with tempfile.TemporaryDirectory() as t:
            root = specimen(Path(t))
            report = module.inspect_repository(root, target_journal="mdpi-ai")
            gates = ids(report)
            self.assertEqual(report["readiness"], "NOT_READY_FOR_SUBMISSION")
            self.assertEqual(gates["TARGET_JOURNAL_TEMPLATE"]["status"], module.BLOCKED)
            self.assertEqual(gates["MANUSCRIPT_SIGNIFICANCE"]["status"], module.BLOCKED)
            self.assertEqual(gates["REPLICATION_INDEPENDENT_SEEDS"]["status"], module.BLOCKED)
            self.assertTrue(gates["REPLICATION_INDEPENDENT_SEEDS"]["evidence"]
                            ["manuscript_diad_two_seed_rows"])
            self.assertEqual(gates["TRACKED_REVISION_MARKUP"]["status"], module.REVIEW)
            self.assertFalse(gates["OFFICIAL_SOURCE_CICIOT2023"]["evidence"]
                             ["expected_local_csv_directory_present"])
            self.assertEqual(report["counts"]["total"], len(report["gates"]))

    def test_existing_source_directory_still_requires_human_authentication(self):
        with tempfile.TemporaryDirectory() as t:
            root = specimen(Path(t))
            source = root / "data/raw_official_csv/ciciot2023/flow"
            source.mkdir(parents=True)
            (source / "malicious_unopened.csv").write_text("FAKE\n", encoding="utf-8")
            audit = module.inspect_repository(root)
            gate = ids(audit)["OFFICIAL_SOURCE_CICIOT2023"]
            self.assertEqual(gate["status"], module.REVIEW)
            self.assertFalse(gate["evidence"]["publisher_checksum_verified_by_auditor"])
            self.assertEqual(audit["readiness"], "NOT_READY_FOR_SUBMISSION")

    def test_unseal_receipt_presence_is_not_test_success(self):
        with tempfile.TemporaryDirectory() as t:
            root = specimen(Path(t))
            output = root / "experiments/strict_test_eval/ciciot2023/seed_42"
            output.mkdir(parents=True)
            (output / "TEST_UNSEAL_RECEIPT.json").write_bytes(b"not even JSON")
            result = module.inspect_repository(root)
            gate = ids(result)["ONE_TIME_SEALED_TEST_CICIOT2023"]
            self.assertEqual(gate["status"], module.REVIEW)
            self.assertTrue(gate["evidence"]["unseal_receipt_present"])
            self.assertFalse(gate["evidence"]["test_opened"])

    def test_never_reads_raw_files_test_receipt_or_checkpoints(self):
        with tempfile.TemporaryDirectory() as t:
            root = specimen(Path(t))
            raw = root / "data/raw_official_csv/ciciot2023/flow"
            raw.mkdir(parents=True)
            (raw / "fake.csv").write_text("not benchmark", encoding="utf-8")
            receipt = root / "experiments/strict_test_eval/ciciot2023/seed_42"
            receipt.mkdir(parents=True)
            (receipt / "TEST_UNSEAL_RECEIPT.json").write_text("not json")
            original = Path.open

            def guard_open(path, *args, **kwargs):
                if path.suffix.lower() in (".csv", ".pt", ".npz") or (
                        "TEST" in path.name and path.suffix == ".json"):
                    raise AssertionError("Read forbidden data or TEST artifact")
                return original(path, *args, **kwargs)

            with patch.object(Path, "open", guard_open):
                out = module.inspect_repository(root)
            self.assertEqual(out["readiness"], "NOT_READY_FOR_SUBMISSION")

    def test_template_matching_and_no_revision_marks(self):
        with tempfile.TemporaryDirectory() as t:
            root = specimen(Path(t), paper_class=r"\documentclass{Definitions}",
                            redlines=False)
            out = ids(module.inspect_repository(root, "mdpi-ai"))
            self.assertEqual(out["TARGET_JOURNAL_TEMPLATE"]["status"], module.PASS)
            self.assertEqual(out["TRACKED_REVISION_MARKUP"]["status"], module.PASS)
            self.assertEqual(ids(module.inspect_repository(root, "ieee-iotj"))
                             ["TARGET_JOURNAL_TEMPLATE"]["status"], module.BLOCKED)

    def test_invalid_journal_or_seed_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = specimen(Path(t))
            with self.assertRaisesRegex(ValueError, "Unsupported target"):
                module.inspect_repository(root, target_journal="unknown")
            with self.assertRaisesRegex(ValueError, "Seed"):
                module.inspect_repository(root, seed=-1)
            with self.assertRaisesRegex(ValueError, "Seed"):
                module.inspect_repository(root, seed=True)

    def test_missing_manuscript_blocks_static_audit(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(FileNotFoundError, "paper/main.tex"):
                module.inspect_repository(Path(t))

    def test_code_existence_is_not_real_training(self):
        with tempfile.TemporaryDirectory() as t:
            root = specimen(Path(t))
            paths = [
                "scripts/data/audit_original_csvs.py",
                "scripts/data/prepare_official_dataset_archive.py",
                "scripts/data/unify_features_v2.py",
                "scripts/data/split_records_leakfree.py",
                "scripts/data/select_features_train_only.py",
                "scripts/data/strict_test_guard.py",
                "scripts/training/strict_fuzzy_core.py",
                "scripts/training/strict_fed_core.py",
                "scripts/training/train_mamba_strict.py",
                "scripts/training/train_federated_strict.py",
                "scripts/evaluation/evaluate_strict_test.py",
                "scripts/analysis/audit_metrics_statistics.py",
            ]
            for path in paths:
                f = root / path
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("# Source exists, NOT proof of correctness")
            out = module.inspect_repository(root)
            self.assertEqual(ids(out)["STRICT_PIPELINE_CODE"]["status"], module.PASS)
            self.assertEqual(out["readiness"], "NOT_READY_FOR_SUBMISSION")

    def test_per_seed_teacher_inventory_is_existence_only(self):
        with tempfile.TemporaryDirectory() as t:
            root = specimen(Path(t))
            for link in module.LINKS:
                f = root / "experiments/strict_stage3/ciciot2023" / "seed_47" / link / "provenance.json"
                f.parent.mkdir(parents=True)
                f.write_bytes(b"invalid, never parsed")
            info = module.inspect_repository(root, seed=47)
            item = ids(info)["STAGE3_TEACHERS_CICIOT2023"]
            self.assertEqual(item["status"], module.REVIEW)
            self.assertEqual(item["evidence"]["teacher_provenance_files_present"], 5)
            self.assertEqual(ids(info)["STAGE3_TEACHERS_DIAD2024"]["status"], module.BLOCKED)


if __name__ == "__main__":
    unittest.main()
