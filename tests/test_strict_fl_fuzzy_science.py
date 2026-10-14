"""No external ML library required; synthetic scientific property tests."""
import json
import math
import random
import unittest

from scripts.training.strict_fuzzy_core import (
    SCHEMA, fit_train_only_rules, infer_rule)
from scripts.training.strict_fed_core import (
    normalized_client_weights, mosar_reward)


def sample_data():
    # Balanced, readable clusters with overlapping per-class boundaries.
    rows, labels = [], []
    for severity, x0 in ((0, -2.0), (1, 0.0), (2, 2.0)):
        for i in range(90):
            a = x0 + (i % 7 - 3) * .06
            b = x0 * .5 + (i % 5 - 2) * .035
            rows.append([a, b])
            labels.append(severity)
    return rows, labels


class StrictFuzzyScaleTests(unittest.TestCase):
    def test_fit_and_inference_share_exact_training_units(self):
        x, y = sample_data()
        package = fit_train_only_rules(x, y, ["train_mean_0", "train_mean_1"])
        self.assertEqual(package["schema"], SCHEMA)
        self.assertEqual(package["n_train"], len(y))
        self.assertLessEqual(package["n_rules"], 9)
        self.assertEqual(package["partition"], "TRAIN")
        self.assertTrue(package["no_wavelet_or_synthetic_oversampling"])
        self.assertEqual(set(package["feature_names"]),
                         {"train_mean_0", "train_mean_1"})
        self.assertFalse(any("scaler" in k for k in package))
        for z, source in ((0, [-2.0, -1.0]), (1, [0.0, 0.0]), (2, [2.0, 1.0])):
            action, strength = infer_rule(package, source)
            self.assertEqual(action, (2, 1, 0)[z])
            self.assertGreater(strength, 0)
            self.assertLessEqual(strength, 1)

    def test_deterministic_rule_derivation(self):
        x, y = sample_data()
        a = fit_train_only_rules(x, y, ["a", "b"])
        b = fit_train_only_rules(x, y, ["a", "b"])
        self.assertEqual(json.dumps(a, sort_keys=True),
                         json.dumps(b, sort_keys=True))
        self.assertEqual(sum(rule["support"] for rule in a["rules"]),
                         len(y))
        self.assertTrue(all(r["confidence"] >= .50 for r in a["rules"]))

    def test_labels_change_training_rule_outputs(self):
        x, y = sample_data()
        p1 = fit_train_only_rules(x, y, ["a", "b"])
        inverted = [2 - z for z in y]
        p2 = fit_train_only_rules(x, inverted, ["a", "b"])
        self.assertNotEqual(infer_rule(p1, [-2, -1])[0],
                            infer_rule(p2, [-2, -1])[0])
        self.assertEqual(p1["membership_params"], p2["membership_params"])

    def test_future_observations_do_not_refit_memberships(self):
        x, y = sample_data()
        p = fit_train_only_rules(x, y, ["a", "b"])
        saved = json.dumps(p, sort_keys=True)
        infer_rule(p, [1000000, -1000000])
        self.assertEqual(saved, json.dumps(p, sort_keys=True))

    def test_no_train_rules_with_constant_features(self):
        with self.assertRaisesRegex(ValueError, "Constant/non-informative"):
            fit_train_only_rules([[1, 4]] * 70, [i % 3 for i in range(70)],
                                 ["a", "b"])

    def test_fails_closed_on_nan_or_inf(self):
        x, y = sample_data()
        x[1][0] = math.nan
        with self.assertRaisesRegex(ValueError, "finite"):
            fit_train_only_rules(x, y, ["a", "b"])
        x, y = sample_data()
        p = fit_train_only_rules(x, y, ["a", "b"])
        with self.assertRaisesRegex(ValueError, "finite"):
            infer_rule(p, [0, math.inf])

    def test_rejects_bad_labels_and_shapes(self):
        x, y = sample_data()
        y[0] = 3
        with self.assertRaisesRegex(ValueError, "severity"):
            fit_train_only_rules(x, y, ["a", "b"])
        with self.assertRaisesRegex(ValueError, "two"):
            fit_train_only_rules([[0, 1, 2]] * 70, [1]*70, ["a", "b"])
        with self.assertRaisesRegex(ValueError, "feature names"):
            fit_train_only_rules(x, y, ["a", "a"])

    def test_no_unsupported_rule_confidence_or_support(self):
        x, y = sample_data()
        with self.assertRaisesRegex(ValueError, "min_support"):
            fit_train_only_rules(x, y, ["a", "b"], min_support=0)
        with self.assertRaisesRegex(ValueError, "min_confidence"):
            fit_train_only_rules(x, y, ["a", "b"], min_confidence=math.nan)
        with self.assertRaisesRegex(ValueError, "No adequately supported"):
            fit_train_only_rules(x, y, ["a", "b"], min_support=len(y)+1)


class FedAvgAndRewardAuditTests(unittest.TestCase):
    def test_exact_five_client_weights(self):
        weights = normalized_client_weights([10, 20, 30, 40, 50],
                                             expected_clients=5)
        self.assertAlmostEqual(sum(weights), 1.0)
        self.assertEqual(weights, [1/15, 2/15, 3/15, 4/15, 5/15])

    def test_invalid_fedavg_client_weights_fail(self):
        for sizes in ([], [0, 2], [-1, 2], [2.1, 1], [True, 1]):
            with self.subTest(sizes=sizes), self.assertRaises(ValueError):
                normalized_client_weights(sizes)
        with self.assertRaisesRegex(ValueError, "cardinality"):
            normalized_client_weights([1, 2], expected_clients=5)

    def test_weighted_fedavg_expected_vs_unweighted(self):
        weights = normalized_client_weights([1, 3])
        client_params = [1.0, 5.0]
        aggregate = sum(w*p for w, p in zip(weights, client_params))
        self.assertAlmostEqual(aggregate, 4.0)
        self.assertNotEqual(aggregate, sum(client_params)/len(client_params))

    def test_teacher_probability_terms_are_action_invariant(self):
        """Teacher confidence/accuracy terms shift all actions equally.

        Therefore those terms cannot be claimed to separately optimize
        action choice; record as method limitation, not a fake ablation.
        """
        low = [.2, .3, .5]
        high = [.9, .05, .05]
        for good, bad in ((2, 0), (2, 1), (1, 0)):
            d_low = mosar_reward(0, good, low) - mosar_reward(0, bad, low)
            d_high = mosar_reward(0, good, high) - mosar_reward(0, bad, high)
            self.assertAlmostEqual(d_low, d_high)


if __name__ == "__main__":
    unittest.main()
