"""Streaming harmonization v2: SYNTHETIC fixtures only, no original benchmarks."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


raw_audit = load("audit_raw_v2_test", "scripts/data/audit_original_csvs.py")
harmonize = load("harmonize_v2_test", "scripts/data/unify_features_v2.py")
split = load("split_v2_test", "scripts/data/split_records_leakfree.py")
strict = load("strict_manifest_v2_test", "scripts/data/strict_manifest.py")


def fixture(root):
    dataset = "ciciot2023"
    raw = root / "raw"
    raw.mkdir()
    header = [f"Original numeric {i}" for i in range(15)]
    original_csv = raw / "original.csv"
    with original_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,
                                fieldnames=header + ["Original Label", "Observed Link",
                                                     "Capture Session", "Event Time"])
        writer.writeheader()
        for client in range(5):
            for i in range(220):
                row = {name: str(i + 0.13 * k) for k, name in enumerate(header)}
                row.update({
                    "Original Label": ("BENIGN", "DDOS", "RECON")[i % 3],
                    "Observed Link": f"observed_{client+1}",
                    "Capture Session": f"g_{client}_{i}",
                    "Event Time": str(i),
                })
                writer.writerow(row)
    fake_artifact = root / "synthetic-original-package.test"
    fake_artifact.write_bytes(b"SYTHETIC ONLY, NOT OFFICIAL UNB BYTES")
    inventory = root / "raw_inventory.json"
    raw_audit.inventory(
        dataset, raw, "Original Label", inventory,
        modality="flow", source_artifact=fake_artifact,
        reference_sha256=raw_audit.sha256(fake_artifact))
    evidence = root / "reviewed_mapping.json"
    evidence.write_text(json.dumps({
        "schema": "afras-raw-label-evidence-v1",
        "dataset": dataset,
        "source_url": raw_audit.OFFICIAL_PAGES[dataset],
        "source_revision": "UNIT-TEST-ONLY",
        "source_sha256": raw_audit.sha256(fake_artifact),
        "mapping_review_reference": "UNIT-TEST-ONLY-NOT-AN-ACTUAL-REVIEW",
        "raw_label_column": "Original Label",
        "binary_attack_column": "is_attack",
        "raw_label_map": {
            "BENIGN": {"severity": "Low", "is_attack": 0},
            "DDOS": {"severity": "High", "is_attack": 1},
            "RECON": {"severity": "Medium", "is_attack": 1},
        },
    }))
    config = root / "harmonization_config.json"
    config.write_text(json.dumps({
        "schema": harmonize.SCHEMA,
        "dataset": dataset,
        "modality": "flow",
        "source_review_reference": "SYNTHETIC-NOT-A-REAL-REVIEW",
        "feature_sources": {
            f"feature_{i}": f"Original numeric {i}" for i in range(15)
        },
        "link_column": "Observed Link",
        "link_values": {
            f"observed_{i+1}": label
            for i, label in enumerate(harmonize.LINKS)
        },
        "group_column": "Capture Session",
        "time_column": "Event Time",
    }))
    return dataset, raw, inventory, evidence, config


class HarmonizeV2Tests(unittest.TestCase):
    def test_preserves_original_records_labels_and_source_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ds, raw, inv, labels, cfg = fixture(root)
            record = harmonize.run(ds, raw, inv, labels, cfg, root / "unified")
            self.assertEqual(record["raw_original_rows"], 1100)
            self.assertEqual(record["link_assignment_mode"],
                             "DECLARED_SOURCE_LINK_MAPPING_UNVERIFIED_TOPOLOGY")
            self.assertFalse(record["topology_independently_verified"])
            self.assertEqual(len(record["candidate_features"]), 15)
            self.assertEqual(len(record["link_files"]), 5)
            first = root / "unified" / ds / "Link_1_Core.csv"
            with first.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 220)
            self.assertEqual(rows[0]["Original Label"], "BENIGN")
            self.assertEqual(rows[0]["is_attack"], "0")
            self.assertEqual(rows[0]["severity"], "Low")
            self.assertEqual(rows[0]["__afras_original_file"], "original.csv")
            self.assertEqual(rows[0]["__afras_original_row"], "0")
            self.assertEqual(rows[0]["feature_0"], "0.0")
            self.assertEqual(rows[0]["__afras_original_group"], "g_0_0")
            self.assertEqual(record["link_files"]["Link_1_Core"]["sha256"],
                             harmonize.digest(first))
            self.assertEqual(record["raw_label_counts"],
                             {"BENIGN": 370, "DDOS": 365, "RECON": 365})

    def test_split_consumes_provenance_and_source_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ds, raw, inv, labels, cfg = fixture(root)
            harmonize.run(ds, raw, inv, labels, cfg, root / "unified")
            out = split.split_dataset(
                root / "unified" / ds, root / "splits", ds,
                group_column="__afras_original_group",
                time_column="__afras_original_time")
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["source_harmonization"]["link_assignment_mode"],
                             "DECLARED_SOURCE_LINK_MAPPING_UNVERIFIED_TOPOLOGY")
            self.assertTrue(manifest["group_disjoint_verified"])
            self.assertEqual(len(strict.validate_stage3_inputs(out, ds)), 5)

    def test_synthetic_links_explicit_and_strict_training_refuses_them(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ds, raw, inv, labels, config = fixture(root)
            info = json.loads(config.read_text())
            info.pop("link_column")
            info.pop("link_values")
            config.write_text(json.dumps(info))
            with self.assertRaisesRegex(ValueError, "No actual source link ID"):
                harmonize.run(ds, raw, inv, labels, config, root / "rejected")
            data = harmonize.run(ds, raw, inv, labels, config, root / "explore",
                                  exploratory_synthetic_links=True)
            self.assertEqual(data["link_assignment_mode"],
                             "EXPLORATORY_SYNTHETIC_NONPHYSICAL")
            with self.assertRaisesRegex(ValueError, "Synthetic nonphysical"):
                split.split_dataset(root / "explore" / ds, root / "strict_split", ds)
            experimental = split.split_dataset(
                root / "explore" / ds, root / "pilot_split", ds,
                allow_exploratory_synthetic_links=True)
            with self.assertRaisesRegex(strict.StrictManifestError, "Nonphysical synthetic"):
                strict.validate_stage3_inputs(experimental, ds)

    def test_changed_original_csv_aborts_before_publish(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ds, raw, inv, labels, config = fixture(root)
            with (raw / "original.csv").open("a") as file:
                file.write("tampered\n")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                harmonize.run(ds, raw, inv, labels, config, root / "out")
            self.assertFalse((root / "out" / ds).exists())

    def test_unknown_label_in_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ds, raw, inv, labels, cfg = fixture(root)
            mapping = json.loads(labels.read_text())
            mapping["raw_label_map"].pop("RECON")
            labels.write_text(json.dumps(mapping))
            with self.assertRaisesRegex(ValueError, "Incomplete/excess"):
                harmonize.run(ds, raw, inv, labels, cfg, root / "out")
            self.assertFalse((root / "out" / ds).exists())

    def test_metadata_cannot_be_model_candidate_feature(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ds, raw, inv, labels, cfg = fixture(root)
            config = json.loads(cfg.read_text())
            config["feature_sources"]["is_attack"] = "Event Time"
            cfg.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "protected feature"):
                harmonize.run(ds, raw, inv, labels, cfg, root / "out")

    def test_unknown_link_fails_without_experimental_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ds, raw, inv, labels, cfg = fixture(root)
            config = json.loads(cfg.read_text())
            config["link_values"]["observed_1"] = "Link_5_Edge_R"
            cfg.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "one-to-one"):
                harmonize.run(ds, raw, inv, labels, cfg, root / "out")

    def test_duplicate_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ds, raw, inv, labels, cfg = fixture(root)
            harmonize.run(ds, raw, inv, labels, cfg, root / "out")
            with self.assertRaises(FileExistsError):
                harmonize.run(ds, raw, inv, labels, cfg, root / "out")

    def test_source_review_and_modality_are_required(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ds, raw, inv, labels, cfg = fixture(root)
            config = json.loads(cfg.read_text())
            config["modality"] = "packet"
            cfg.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "modality mismatch"):
                harmonize.run(ds, raw, inv, labels, cfg, root / "out")


if __name__ == "__main__":
    unittest.main()
