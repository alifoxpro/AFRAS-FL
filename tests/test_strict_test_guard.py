"""Synthetic immutability checks; no models or source datasets required."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


splitter = load("test_splitter", "scripts/data/split_records_leakfree.py")
guard = load("test_guard", "scripts/data/strict_test_guard.py")


def fixture(home):
    ds, seed = "ciciot2023", 42
    features = [f"f{i}" for i in range(14)]
    feature_json = home / "data" / "unified_selected_14.json"
    feature_json.parent.mkdir()
    feature_json.write_text(json.dumps({"selected_features": features}))
    raw = home / "raw"
    raw.mkdir()
    for j in range(5):
        with (raw / f"Link_{j+1}_Core.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=features + ["severity"])
            w.writeheader()
            for row_id in range(250):
                row = {name: row_id + n for n, name in enumerate(features)}
                row["severity"] = ("High", "Medium", "Low")[row_id % 3]
                w.writerow(row)
    split_root = home / "splits"
    stage3_root = home / "stage3"
    stage4_root = home / "stage4"
    out = splitter.split_dataset(raw, split_root, ds, window_size=20)
    split = json.loads((out / "manifest.json").read_text())
    teacher_map, scaler_map, provenance_map = {}, {}, {}
    for link, entry in split["links"].items():
        d = stage3_root / ds / link
        d.mkdir(parents=True)
        checkpoint, scaler = d / "mamba_val_best.pt", d / "train_fitted_scaler.npz"
        checkpoint.write_bytes(("checkpoint " + link).encode())
        scaler.write_bytes(("scaler " + link).encode())
        p = {
            "protocol": guard.STAGE3_SCHEMA,
            "dataset": ds, "link": link,
            "test_access": "NONE — not accessed",
            "features": features, "feature_list_sha256": guard.sha256_file(feature_json),
            "window_size": 20, "stride": 20,
            "train_sha256": entry["partitions"]["train"]["sha256"],
            "val_sha256": entry["partitions"]["val"]["sha256"],
        }
        pfile = d / "provenance.json"
        pfile.write_text(json.dumps(p))
        teacher_map[link] = guard.sha256_file(checkpoint)
        scaler_map[link] = guard.sha256_file(scaler)
        provenance_map[link] = guard.sha256_file(pfile)
    run_path = stage4_root / ds / "seed_42"
    run_path.mkdir(parents=True)
    phases = []
    for phase in guard.PHASES:
        file = run_path / (phase + ".pt")
        file.write_bytes(phase.encode())
        phases.append({
            "phase": phase, "checkpoint": file.name,
            "checkpoint_sha256": guard.sha256_file(file),
            "best_round_val_only": 3, "best_val_mean_action_success": 0.6,
            "validation_only": True,
        })
    run = {
        "schema": guard.STAGE4_SCHEMA, "dataset": ds,
        "test_access": "NONE", "mu_link_effective": 0,
        "discount_gamma": 0,
        "source_experiment": "new protocol, NOT historical manuscript output",
        "split_manifest_sha256": guard.sha256_file(out / "manifest.json"),
        "settings": {
            "dataset": ds, "seed": seed, "pilot": False, "max_train_windows": 0,
            "window_size": 20, "stride": 20, "mu_link": 0.0,
        },
        "phases": phases,
        "client_checkpoint_sha256": teacher_map,
        "client_stage3_scaler_sha256": scaler_map,
        "client_stage3_provenance_sha256": provenance_map,
        "client_train_counts": {link: 78 for link in split["links"]},
        "fuzzy_train_only": {link: {"train_only": True} for link in split["links"]},
    }
    (run_path / "RUN_PROVENANCE.json").write_text(json.dumps(run))
    return ds, seed, split_root, stage3_root, stage4_root, feature_json


class FrozenTESTGuards(unittest.TestCase):
    def validate(self, obj):
        return guard.validate_frozen_run(*obj)

    def test_accepts_five_immutable_clients_and_three_models(self):
        with tempfile.TemporaryDirectory() as t:
            result = self.validate(fixture(Path(t)))
            self.assertEqual(len(result["clients"]), 5)
            self.assertEqual(tuple(result["phases"]), guard.PHASES)

    def test_detects_modified_test_csv(self):
        with tempfile.TemporaryDirectory() as t:
            f = fixture(Path(t))
            with (f[2] / f[0] / "test" / "Link_1_Core.csv").open("a") as file:
                file.write("unexpected\n")
            with self.assertRaisesRegex(ValueError, "TEST split checksum mismatch"):
                self.validate(f)

    def test_detects_modified_policy(self):
        with tempfile.TemporaryDirectory() as t:
            f = fixture(Path(t))
            (f[4] / f[0] / "seed_42" / "B3_FedProx.pt").write_bytes(b"altered")
            with self.assertRaisesRegex(ValueError, "Policy checkpoint changed"):
                self.validate(f)

    def test_detects_modified_teacher_scaler(self):
        with tempfile.TemporaryDirectory() as t:
            f = fixture(Path(t))
            (f[3] / f[0] / "Link_2_Core" / "train_fitted_scaler.npz").write_bytes(b"altered")
            with self.assertRaisesRegex(ValueError, "Train-fitted scaler changed"):
                self.validate(f)

    def test_detects_modified_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            f = fixture(Path(t))
            m = f[2] / f[0] / "manifest.json"
            m.write_text(m.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "Split manifest modified"):
                self.validate(f)

    def test_rejects_pilot_experiments(self):
        with tempfile.TemporaryDirectory() as t:
            f = fixture(Path(t))
            file = f[4] / f[0] / "seed_42" / "RUN_PROVENANCE.json"
            data = json.loads(file.read_text())
            data["settings"]["pilot"] = True
            file.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "PILOT"):
                self.validate(f)

    def test_train_and_val_csv_not_required_during_test(self):
        with tempfile.TemporaryDirectory() as t:
            f = fixture(Path(t))
            for split in ("train", "val"):
                for file in (f[2] / f[0] / split).glob("*.csv"):
                    file.unlink()
            self.assertEqual(len(self.validate(f)["clients"]), 5)

    def test_detects_modified_stage3_provenance(self):
        with tempfile.TemporaryDirectory() as t:
            f = fixture(Path(t))
            p = f[3] / f[0] / "Link_3_Core" / "provenance.json"
            p.write_text(p.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "Stage 3 provenance changed"):
                self.validate(f)


if __name__ == "__main__":
    unittest.main()
