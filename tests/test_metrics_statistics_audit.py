"""Synthetic scientific metric/statistics checks; not real benchmark evidence."""
import math
import unittest
from scripts.analysis.audit_metrics_statistics import (
    audit_manuscript, exact_paired_sign_flip, holm_adjust,
    declared_seed_comparisons, INPUT_SCHEMA)
from scripts.training.strict_fed_core import (
    binary_intrusion_metrics, pooled_binary_counts)

TEX = r"""
\begin{abstract}
On CICIoT2023 we report Cohen's $d=2.29$ and p = 1.8 \times 10^{-15}.
\end{abstract}
Two-sided Welch $t$-tests with $n = 50$ evaluation episodes.
\rev{\emph{(L7) Statistical protocol.} only three seeds are reported here.}
\rev{\caption{Multi-seed mean-of-run replication on both datasets (seeds $\{42, 123, 2026\}$).}}
DIAD2024 & B4 (Fuzzy) & $0.9213$ & $0.0739$ & $2$ \\
The FedProx false-positive rate from 26.98 to 0.18.
AFRAS-FL adds approximately $7\%$ per-round computational overhead.
"""


class BinaryIDSMetricTests(unittest.TestCase):
    def test_exact_binary_confusion_and_undefined_values(self):
        r = binary_intrusion_metrics([1, 1, 0, 0], [2, 0, 1, 0])
        self.assertEqual([r[n] for n in ("TP", "FN", "FP", "TN")],
                         [1, 1, 1, 1])
        self.assertEqual(r["accuracy"], .5)
        self.assertEqual(r["precision_attack"], .5)
        self.assertEqual(r["recall_attack"], .5)
        self.assertEqual(r["f1_attack"], .5)
        self.assertEqual(r["FPR"], .5)
        self.assertEqual(r["FNR"], .5)

    def test_denominator_absence_returns_none_not_zero(self):
        all_attacks = binary_intrusion_metrics([1, 1], [1, 0])
        self.assertIsNone(all_attacks["FPR"])
        self.assertIsNone(all_attacks["TNR"])
        all_benign = binary_intrusion_metrics([0, 0], [0, 0])
        self.assertIsNone(all_benign["FNR"])
        self.assertIsNone(all_benign["recall_attack"])
        self.assertIsNone(all_benign["precision_attack"])
        self.assertIsNone(all_benign["f1_attack"])

    def test_macro_aggregation_from_counts_not_avg_of_FPRs(self):
        a = binary_intrusion_metrics([0, 0, 0, 0], [1, 0, 0, 0])
        b = binary_intrusion_metrics([0, 1], [0, 2])
        pooled = pooled_binary_counts([a, b], expected_clients=2)
        self.assertEqual(pooled["FP"], 1)
        self.assertEqual(pooled["TN"], 4)
        self.assertAlmostEqual(pooled["FPR"], 1 / 5)
        self.assertEqual(pooled["n"], 6)

    def test_mixed_binary_coverage_fails_closed(self):
        report = binary_intrusion_metrics([0, 1], [0, 1])
        with self.assertRaisesRegex(ValueError, "Partial original binary"):
            pooled_binary_counts([report, None], expected_clients=2)
        self.assertIsNone(pooled_binary_counts([None, None], expected_clients=2))

    def test_pooled_rejects_invalid_counts(self):
        with self.assertRaisesRegex(ValueError, "Invalid per-client"):
            pooled_binary_counts([{"TP": 1.5, "FP": 0, "FN": 0, "TN": 1}])
        with self.assertRaisesRegex(ValueError, "complete set"):
            pooled_binary_counts([], expected_clients=5)


class ManuscriptStatsTests(unittest.TestCase):
    def test_flags_episode_unit_and_missing_seed_evidence(self):
        audit = audit_manuscript(TEX)
        ids = {v["id"] for v in audit["findings"]}
        self.assertIn("EPISODE_AS_INDEPENDENT_UNIT", ids)
        self.assertIn("RUN_LEVEL_REPLICATION_MISSING", ids)
        self.assertIn("SEED_COUNT_2_NOT_SUFFICIENT", ids)
        self.assertIn("MULTISEED_CAPTION_SCOPE_MISMATCH", ids)
        self.assertIn("DEPLOYMENT_LATENCY_NOT_VERIFIED", ids)
        self.assertIn("SOURCE_METRIC_MAPPING_UNVERIFIED", ids)
        self.assertEqual(audit["status"], "STATIC_ONLY_NO_REAL_TRAINING_EVIDENCE")
        self.assertGreaterEqual(audit["critical_count"], 3)
        self.assertTrue(all(v["line"] >= 1 for v in audit["findings"]))

    def test_no_claims_fabricated_from_blank_tex(self):
        report = audit_manuscript("No quantitative results.")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["critical_count"], 0)

    def test_five_seeds_two_sided_exact_p_cannot_be_below_005(self):
        a = {str(x): 1.0 for x in range(5)}
        b = {str(x): 0.0 for x in range(5)}
        p = exact_paired_sign_flip(a, b)
        self.assertEqual(p["n_paired_seeds"], 5)
        self.assertEqual(p["p_unadjusted"], 2 / 32)
        self.assertEqual(p["mean_paired_difference_A_minus_B"], 1.0)
        self.assertIsNone(p["cohen_dz_paired"])
        self.assertFalse(p["source_runs_independently_authenticated"])

    def test_six_seeds_two_sided_exact_p_and_no_overclaim(self):
        a = {str(x): 1.0 for x in range(6)}
        b = {str(x): 0.0 for x in range(6)}
        result = exact_paired_sign_flip(a, b)
        self.assertEqual(result["p_unadjusted"], 2 / 64)
        self.assertTrue(result["conditional_on_frozen_test"])

    def test_paired_seed_sign_flip_rejects_episodes_and_mismatches(self):
        with self.assertRaisesRegex(ValueError, "5..16"):
            exact_paired_sign_flip({1: 0.7}, {1: 0.4})
        with self.assertRaisesRegex(ValueError, "identical"):
            exact_paired_sign_flip({str(k): .5 for k in range(5)},
                                   {str(k): .6 for k in range(1, 6)})
        with self.assertRaisesRegex(ValueError, "finite"):
            exact_paired_sign_flip({str(k): float('nan') for k in range(5)},
                                   {str(k): .7 for k in range(5)})

    def test_holm_family_maintains_monotonicity(self):
        results = holm_adjust({"A": .01, "B": .03, "C": .04})
        self.assertAlmostEqual(results["A"], .03)
        self.assertAlmostEqual(results["B"], .06)
        self.assertAlmostEqual(results["C"], .06)

    def test_declared_summary_cannot_pass_without_required_protocol(self):
        report = {
            "schema": INPUT_SCHEMA, "statistical_unit": "evaluation_episode",
            "dataset": "ciciot2023", "metric": "pooled_action_success",
            "protocol": "strict-sealed-test-eval-v1",
            "predeclared_comparisons": {
                "B4-B3": {"A": {str(i): .8 for i in range(5)},
                          "B": {str(i): .7 for i in range(5)}}},
        }
        with self.assertRaisesRegex(ValueError, "independent seed"):
            declared_seed_comparisons(report)
        report["statistical_unit"] = "independent_training_seed"
        result = declared_seed_comparisons(report)
        self.assertIn("p_holm_adjusted", result["results"]["B4-B3"])
        self.assertTrue(result["exploratory_until_frozen_source_validation"])


if __name__ == "__main__":
    unittest.main()
