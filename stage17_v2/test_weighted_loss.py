"""Pre-confirmatory source-only weighted-BCE model checks (synthetic data).

No claims of improved N-BaIoT performance are made by these tests.
"""
import unittest

import numpy as np
import torch

import source_only_pilot as p


class SourceWeightedLossTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(3107)
        self.X = rng.normal(size=(60, p.N_FEATURES)).astype(np.float32)
        self.y = np.r_[np.zeros(12), np.ones(48)].astype(np.float32)
        torch.manual_seed(309)
        self.initial = {k: v.detach().clone() for k, v in p.BinaryMLP().state_dict().items()}
        self.kw = dict(initial=self.initial, dataset=(self.X, self.y),
                       method="fedavg", mu=0.0, local_epochs=2, batch_size=15,
                       lr=0.01, random_seed=3107, backend=torch.device("cpu"))

    def test_weighted_update_differs_from_unweighted_update(self):
        unweighted = p.train_client(**self.kw, loss_balance="none")
        weighted = p.train_client(**self.kw, loss_balance="inverse-prevalence")
        differences = [
            not torch.equal(unweighted[name], weighted[name])
            for name in unweighted
        ]
        self.assertTrue(any(differences), "Weighted BCE had no effect on source training")
        self.assertTrue(all(torch.isfinite(t).all().item() for t in weighted.values()))

    def test_zero_mu_fedprox_same_as_weighted_fedavg(self):
        a = p.train_client(**self.kw, loss_balance="inverse-prevalence")
        fedprox = dict(self.kw, method="fedprox")
        b = p.train_client(**fedprox, loss_balance="inverse-prevalence")
        for name in a:
            self.assertTrue(torch.equal(a[name], b[name]), name)

    def test_invalid_weighting_mode_fails(self):
        with self.assertRaisesRegex(ValueError, "Unknown class-loss"):
            p.train_client(**self.kw, loss_balance="invalid")

    def test_single_class_training_source_fails(self):
        data = dict(self.kw, dataset=(self.X, np.ones_like(self.y)))
        with self.assertRaisesRegex(ValueError, "both canonical binary classes"):
            p.train_client(**data, loss_balance="inverse-prevalence")


if __name__ == "__main__":
    unittest.main()
