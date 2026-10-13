"""No third-party dependencies: verify reward and measurement semantics."""
import unittest
from scripts.training.strict_fed_core import (
    ACTION_FOR_SEVERITY, decision_metrics, jain_fairness, mosar_reward)


class FederatedRewardTests(unittest.TestCase):
    def test_correct_actions(self):
        self.assertEqual(ACTION_FOR_SEVERITY, (2, 1, 0))
        for severity in range(3):
            correct = ACTION_FOR_SEVERITY[severity]
            probs = [0.2, 0.3, 0.5]
            good = mosar_reward(severity, correct, probs)
            other = mosar_reward(severity, (correct + 1) % 3, probs)
            self.assertGreater(good, other)

    def test_fuzzy_bonus_is_action_dependent(self):
        probs = [0.1, 0.2, 0.7]
        guided = mosar_reward(0, 2, probs, fuzzy_action=2,
                              fuzzy_confidence=0.8, lambda_fuzzy=0.25)
        unguided = mosar_reward(0, 2, probs)
        self.assertAlmostEqual(guided - unguided, 0.25 * 0.3 * 0.8)
        self.assertLess(mosar_reward(0, 2, probs, fuzzy_action=0,
                                    lambda_fuzzy=0.25), unguided)

    def test_link_reward_must_be_disabled(self):
        with self.assertRaisesRegex(ValueError, "mu_link must be zero"):
            mosar_reward(1, 1, [0.2, 0.7, 0.1], mu_link=0.1)

    def test_jain_and_no_denominator_hack(self):
        self.assertAlmostEqual(jain_fairness([0.5, 0.5, 0.5]), 1.0)
        self.assertEqual(jain_fairness([0, 0, 0]), 0.0)

    def test_interpretability_metrics(self):
        val = decision_metrics([0, 1, 2, 2], [2, 1, 2, 0])
        self.assertEqual(val["n"], 4)
        self.assertEqual(val["action_success_rate"], .75)
        self.assertEqual(val["false_block_on_low"], 0.5)
        self.assertEqual(val["false_allow_on_high"], 0.0)
        self.assertEqual(val["severity_action_counts"][2], [1, 0, 1])

    def test_absent_classes_are_null(self):
        val = decision_metrics([1, 1], [1, 0])
        self.assertIsNone(val["false_block_on_low"])
        self.assertIsNone(val["false_allow_on_high"])


if __name__ == "__main__":
    unittest.main()
