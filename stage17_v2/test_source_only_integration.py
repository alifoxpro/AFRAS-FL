"""Synthetic source-only integration smoke test.

Covers the Stage-17 CLI control flow while replacing the expensive native
archive loader with a deterministic fixture. This is NOT a native ZIP/RAR test.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import source_only_pilot as m


class SourceOnlyIntegrationSmoke(unittest.TestCase):
    def test_run_mocked_native_loader_writes_source_only_metadata(self):
        target = m.DEVICES[0]
        source_val = m.DEVICES[1]
        requests = []
        header = [f"feature_{i}" for i in range(m.N_FEATURES)]

        def fake_loader(root, device, max_per_class, seed, expected_header):
            # The held-out target is deliberately NOT present in the fixture.
            self.assertNotEqual(device, target, "Held-out target was opened")
            self.assertEqual(expected_header, header if requests else None)
            requests.append(device)
            i = m.DEVICES.index(device)
            rng = np.random.default_rng(seed + i)
            X = rng.normal(size=(12, m.N_FEATURES)).astype(np.float32)
            y = np.asarray([0.0] * 6 + [1.0] * 6, dtype=np.float32)
            counts = {"benign": {"raw_rows_scanned": 6, "sample_rows": 6},
                      "gafgyt_combo": {"raw_rows_scanned": 6, "sample_rows": 6}}
            return X, y, counts, header

        with tempfile.TemporaryDirectory(prefix="afras_v2_pilot_test_") as directory:
            root = Path(directory)
            out = root / "pilot.json"
            argv = [
                "source_only_pilot.py",
                "--source-root", str(root),
                "--heldout", target,
                "--validation", source_val,
                "--max-per-class", "6",
                "--rounds", "1",
                "--local-epochs", "1",
                "--batch-size", "6",
                "--lr", "0.005",
                "--seed", "3107",
                "--output", str(out),
            ]
            with patch.object(sys, "argv", argv), patch.object(
                m, "load_one_device", side_effect=fake_loader
            ):
                m.main()
            result = json.loads(out.read_text(encoding="utf8"))
            self.assertEqual(len(requests), 8)
            self.assertEqual(len(set(requests)), 8)
            self.assertNotIn(target, requests)
            self.assertEqual(result["heldout_device_name_only"], target)
            self.assertFalse(result["heldout_evaluated"])
            self.assertFalse(result["heldout_archive_opened"])
            self.assertFalse(result["confirmatory"])
            self.assertEqual(len(result["training_devices"]), 7)
            self.assertEqual(result["source_validation_device"], source_val)
            self.assertEqual(result["status"], "EXPLORATORY_SOURCE_ONLY_PILOT")
            self.assertEqual(set(result["algorithms"]), {"fedavg", "fedprox"})
            self.assertEqual(len(result["algorithms"]["fedavg"]), 1)
            self.assertEqual(len(result["algorithms"]["fedprox"]), 1)


if __name__ == "__main__":
    unittest.main()
