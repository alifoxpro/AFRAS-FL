"""Non-confirmatory Stage 17 V2 unit tests.

Requires numpy, pandas, torch, rarfile to import the pilot.
These tests do NOT train on native N-BaIoT and do not certify accuracy.
"""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import torch

import source_only_pilot as m


class SplitAndIsolationTests(unittest.TestCase):
    def test_eight_available_sources_and_one_validation_source(self):
        for heldout in m.DEVICES:
            for val in m.DEVICES:
                if heldout == val:
                    with self.assertRaises(ValueError):
                        m.split_source_devices(heldout, val)
                else:
                    train, validation = m.split_source_devices(heldout, val)
                    self.assertEqual(len(train), 7)
                    self.assertEqual(validation, val)
                    self.assertNotIn(heldout, train)
                    self.assertNotEqual(heldout, validation)
                    self.assertEqual(set(train + [validation, heldout]), set(m.DEVICES))

    def test_invalid_device_rejected(self):
        with self.assertRaises(ValueError):
            m.split_source_devices("bogus", m.DEVICES[1])

    def test_source_validation_preprocessing_does_not_learn_target_statistics(self):
        rng = np.random.default_rng(17)
        clients = {
            "one": (rng.normal(size=(12, m.N_FEATURES)).astype(np.float32),
                    np.zeros(12, dtype=np.float32)),
            "two": (rng.normal(size=(17, m.N_FEATURES)).astype(np.float32),
                    np.ones(17, dtype=np.float32)),
        }
        Xval = np.full((11, m.N_FEATURES), 1.0e4, dtype=np.float32)
        yval = np.zeros(11, dtype=np.float32)
        original_clients = {d: (v[0].copy(), v[1].copy()) for d,v in clients.items()}
        norm, val, stats = m.preprocess_train_only(clients, (Xval, yval))
        self.assertTrue(np.isfinite(norm["one"][0]).all())
        self.assertTrue(np.isfinite(val[0]).all())
        self.assertTrue(np.allclose(stats["mean"],
            np.arcsinh(np.concatenate([clients["one"][0], clients["two"][0]])).mean(axis=0)))
        for d in clients:
            self.assertTrue(np.array_equal(clients[d][0], original_clients[d][0]))


class ReservoirTests(unittest.TestCase):
    def test_fixed_cap_across_chunks_and_preserved_rows(self):
        arr = np.arange(1000 * m.N_FEATURES, dtype=np.float64).reshape(1000, m.N_FEATURES)
        sample = m.PrioritySample(37, 44)
        for chunk in np.array_split(arr, 13):
            sample.ingest(chunk)
        self.assertEqual(sample.observed, 1000)
        self.assertEqual(sample.values.shape, (37, m.N_FEATURES))
        originals = {tuple(x.astype(np.float32)) for x in arr}
        self.assertTrue(all(tuple(v) in originals for v in sample.values))

    def test_reproducibility_same_chunks_same_seed(self):
        rng = np.random.default_rng(8)
        arr = rng.normal(size=(300, m.N_FEATURES))
        a, b = m.PrioritySample(40, 8), m.PrioritySample(40, 8)
        for chunk in np.array_split(arr, 9):
            a.ingest(chunk)
            b.ingest(chunk)
        self.assertTrue(np.array_equal(a.values, b.values))
        self.assertTrue(np.array_equal(a.priorities, b.priorities))

    def test_nonfinite_rejected(self):
        sample = m.PrioritySample(4, 2)
        x = np.zeros((4, m.N_FEATURES))
        x[0,0] = np.nan
        with self.assertRaises(ValueError):
            sample.ingest(x)

    def test_bad_feature_width_rejected(self):
        with self.assertRaises(ValueError):
            m.PrioritySample(10, 1).ingest(np.zeros((4, 7)))


class AggregationAndOptimizationTests(unittest.TestCase):
    def test_weighted_fedavg_by_sample_count(self):
        a = {"weight": torch.tensor([1.0, 3.0])}
        b = {"weight": torch.tensor([5.0, 7.0])}
        out = m.weighted_fedavg([a, b], [1, 3])
        self.assertTrue(torch.allclose(out["weight"], torch.tensor([4.0, 6.0])))

    def test_aggregation_rejects_zero_client_count(self):
        with self.assertRaises(ValueError):
            m.weighted_fedavg([{"weight": torch.tensor([1.0])}], [0])

    def test_identical_fedavg_and_fedprox_when_mu_zero(self):
        rng = np.random.default_rng(9)
        X = rng.normal(size=(19,m.N_FEATURES)).astype(np.float32)
        y = np.r_[np.zeros(9), np.ones(10)].astype(np.float32)
        torch.manual_seed(3107)
        initial = {k:v.clone() for k,v in m.BinaryMLP().state_dict().items()}
        args = (initial, (X,y))
        a = m.train_client(*args, "fedavg", 0., 2, 8, 0.005, 3107, torch.device("cpu"))
        b = m.train_client(*args, "fedprox", 0., 2, 8, 0.005, 3107, torch.device("cpu"))
        for key in a:
            self.assertTrue(torch.allclose(a[key], b[key], atol=0, rtol=0), key)

    def test_source_validation_evaluation_uses_no_target_inputs(self):
        rng = np.random.default_rng(12)
        X = rng.normal(size=(11, m.N_FEATURES)).astype(np.float32)
        y = np.r_[np.zeros(5), np.ones(6)].astype(np.float32)
        initial = {k:v.clone() for k,v in m.BinaryMLP().state_dict().items()}
        result = m.evaluate_source_validation(initial, (X,y), torch.device("cpu"))
        self.assertEqual(result["tp"]+result["tn"]+result["fp"]+result["fn"], 11)
        self.assertTrue(0 <= result["validation_only_balanced_accuracy"] <= 1)


if __name__ == "__main__":
    unittest.main()
