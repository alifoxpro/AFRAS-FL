"""Ensure separate MDPI conversion never corrupts IEEE scientific manuscript."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/analysis/validate_mdpi_conversion.py"
spec = importlib.util.spec_from_file_location("mdpi_source_integrity", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MDPIConversionIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
        cls.conversion = (ROOT / "paper/mdpi_ai/main.tex").read_text(encoding="utf-8")

    def test_current_repo_conversion_retains_full_scientific_body(self):
        audit = mod.verify_conversion(self.source, self.conversion)
        self.assertEqual(audit["integrity"], "SCIENTIFIC_TEXT_IDENTICAL_EXCEPT_THREE_COSMETIC_RED_TO_BLACK_CHANGES")
        self.assertEqual(audit["whitelisted_cosmetic_color_command_count"], 3)
        self.assertEqual(audit["clean_reading_style"], "rev_black_strk_hidden")
        self.assertNotIn(r"\textcolor{red}", self.conversion)
        self.assertNotIn(r"\color{red}", self.conversion)
        self.assertEqual(audit["figure_inclusions"], 34)
        self.assertEqual(audit["source_scientific_body_sha256"],
                         audit["converted_scientific_body_sha256"])
        self.assertEqual(audit["original_abstract_sha256"],
                         audit["converted_abstract_sha256"])
        self.assertFalse(audit["manuscript_ready_for_submission"])

    def test_modified_statistic_detected(self):
        changed = self.conversion.replace("0.9990", "0.9998", 1)
        self.assertNotEqual(changed, self.conversion)
        with self.assertRaisesRegex(ValueError, "SCIENTIFIC BODY ALTERED|abstract altered"):
            mod.verify_conversion(self.source, changed)

    def test_changed_abstract_claim_detected(self):
        changed = self.conversion.replace("improves the FedAvg baseline", "improves the FedAvg twice", 1)
        self.assertNotEqual(changed, self.conversion)
        with self.assertRaisesRegex(ValueError, "abstract altered"):
            mod.verify_conversion(self.source, changed)

    def test_removed_body_figure_detected(self):
        changed = self.conversion.replace("fig15_fuzzy_convergence.png",
                                          "fig15_renamed_and_unreviewed.png", 1)
        self.assertNotEqual(changed, self.conversion)
        with self.assertRaisesRegex(ValueError, "SCIENTIFIC BODY ALTERED"):
            mod.verify_conversion(self.source, changed)

    def test_source_title_change_detected(self):
        changed = self.conversion.replace(
            r"\Title{Fuzzy-Augmented Reward Shaping",
            r"\Title{Fabricated Accuracy Claim", 1)
        self.assertNotEqual(changed, self.conversion)
        with self.assertRaisesRegex(ValueError, "title changed"):
            mod.verify_conversion(self.source, changed)

    def test_wrong_class_and_wrong_references_fail(self):
        with self.assertRaisesRegex(ValueError, "publisher class"):
            mod.verify_conversion(
                self.source,
                self.conversion.replace(
                    r"\documentclass[ai,article,submit,moreauthors,pdftex]",
                    r"\documentclass[entropy,article,submit,moreauthors,pdftex]", 1))
        with self.assertRaisesRegex(ValueError, "original bibliography"):
            mod.verify_conversion(self.source,
                                   self.conversion.replace(
                                       r"\bibliography{../references}",
                                       r"\bibliography{invented_source}", 1))

    def test_red_style_or_deleted_text_not_resurrected(self):
        changed = self.conversion.replace(
            r"\\newcommand{\\rev}[1]{#1}",
            r"\\newcommand{\\rev}[1]{\\textcolor{red}{#1}}", 1)
        self.assertNotEqual(changed, self.conversion)
        with self.assertRaisesRegex(ValueError, "render revisions black"):
            mod.verify_conversion(self.source, changed)
        altered = self.conversion.replace(
            r"\\newcommand{\\strk}[1]{}",
            r"\\newcommand{\\strk}[1]{#1}", 1)
        self.assertNotEqual(altered, self.conversion)
        with self.assertRaisesRegex(ValueError, "hide deletions"):
            mod.verify_conversion(self.source, altered)

    def test_no_figure_writes_or_original_mutation(self):
        source_path = ROOT / "paper/main.tex"
        converted_path = ROOT / "paper/mdpi_ai/main.tex"
        self.assertNotEqual(source_path, converted_path)
        self.assertEqual(mod.sha(self.source),
                         mod.sha(source_path.read_text(encoding="utf-8")))
        self.assertIn("% Scientific body copied unchanged from paper/main.tex.",
                      self.conversion)


if __name__ == "__main__":
    unittest.main()
