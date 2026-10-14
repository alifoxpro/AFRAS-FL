"""Synthetic fixtures only: inspect TeX dependencies without source edits."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts/analysis/audit_mdpi_source_package.py"
spec = importlib.util.spec_from_file_location("mdpi_packaging_evidence", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture(root, mdpi=False, add_image=True):
    paper = root / "paper"
    paper.mkdir(parents=True)
    base = (r"\documentclass[ai,article,submit]{Definitions/mdpi}"
            if mdpi else r"\documentclass[journal]{IEEEtran}")
    tex = "\n".join([
        base,
        r"\usepackage{graphicx}",
        r"\graphicspath{{figures/}}",
        r"\begin{document}",
        r"\section{Introduction}\label{sec:intro}",
        r"Fake science is never assumed to be real \cite{valid_ref}.",
        r"\begin{figure}\includegraphics[width=\linewidth]{viz/chart.png}\caption{A picture}\end{figure}",
        r"See Section~\ref{sec:intro}.",
        r"\bibliographystyle{IEEEtran}" if not mdpi else r"\bibliographystyle{mdpi}",
        r"\bibliography{references}",
        r"\end{document}",
        "",
    ])
    (paper / "main.tex").write_text(tex, encoding="utf-8")
    (paper / "references.bib").write_text(
        "@article{valid_ref,\n title={Test},\n author={Synthetic}\n}\n",
        encoding="utf-8")
    if add_image:
        image = paper / "figures/viz/chart.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"FAKE IMAGE BYTES, EXISTS ONLY")
    return root


class MDPIManuscriptPackageTests(unittest.TestCase):
    def test_real_mdpi_class_recognized_without_pretending_submission_ready(self):
        with tempfile.TemporaryDirectory() as d:
            root = fixture(Path(d), mdpi=True)
            result = mod.inspect_package(root)
            self.assertEqual(result["manuscript_class"], "Definitions/mdpi")
            self.assertEqual(result["figure_files_missing"], 0)
            self.assertEqual(result["citation_keys_used"], 1)
            self.assertEqual(result["undefined_citation_keys"], [])
            self.assertEqual(result["undefined_tex_refs"], [])
            self.assertEqual(result["status"],
                             "MANUAL_SCIENTIFIC_AND_EDITORIAL_REVIEW_REQUIRED")
            self.assertEqual(result["blockers"], [])
            self.assertEqual(result["figure_files_resolved"], 1)

    def test_ieee_style_is_not_mdpi_ai(self):
        with tempfile.TemporaryDirectory() as d:
            root = fixture(Path(d))
            report = mod.inspect_package(root)
            self.assertEqual(report["status"], "NOT_READY_FOR_SUBMISSION")
            self.assertIn("WRONG_JOURNAL_CLASS", report["blockers"])
            self.assertIn("IEEE_SPECIFIC_MARKUP_NEEDS_CONVERSION_REVIEW",
                          report["manual_review_flags"])

    def test_missing_figures_and_citations_are_never_silently_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            root = fixture(Path(d), mdpi=True, add_image=False)
            path = root / "paper/main.tex"
            path.write_text(path.read_text().replace("valid_ref", "unknown_reference"))
            result = mod.inspect_package(root)
            self.assertIn("UNRESOLVED_GRAPHICS", result["blockers"])
            self.assertIn("MISSING_BIBLIOGRAPHY_CITATIONS", result["blockers"])
            self.assertEqual(result["undefined_citation_keys"], ["unknown_reference"])
            self.assertEqual(result["missing_figure_paths"], ["viz/chart.png"])

    def test_duplicate_labels_missing_ref_missing_input_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = fixture(Path(d), mdpi=True)
            tex = root / "paper/main.tex"
            tex.write_text(tex.read_text() + "\n" +
                           r"\label{sec:intro}\ref{sec:missing}\input{chapter_not_found}")
            report = mod.inspect_package(root)
            self.assertEqual(report["duplicate_tex_labels"], ["sec:intro"])
            self.assertEqual(report["undefined_tex_refs"], ["sec:missing"])
            self.assertEqual(report["missing_tex_inputs"], ["chapter_not_found"])
            self.assertIn("MISSING_LATEX_INPUTS", report["blockers"])

    def test_latex_comments_do_not_fake_used_citations(self):
        txt = "\n".join([
            r"\cite{valid_ref} % \cite{invented}",
            r"This is 10\% correct. \cite{second_ref} % note",
            r"50\\% percent sign begins comment \cite{hidden}",
        ])
        result = mod.no_comments(txt)
        self.assertNotIn("invented", result)
        self.assertIn("second_ref", result)
        self.assertNotIn("hidden", result)

    def test_unsafe_traversal_from_latex_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = fixture(Path(d), mdpi=True)
            tex = root / "paper/main.tex"
            tex.write_text(tex.read_text().replace("viz/chart.png", "../../private.png"))
            with self.assertRaisesRegex(ValueError, "Unsafe figure"):
                mod.inspect_package(root)

    def test_does_not_read_test_or_source_datasets(self):
        with tempfile.TemporaryDirectory() as d:
            root = fixture(Path(d), mdpi=True)
            trap = root / "data" / "source"
            trap.mkdir(parents=True)
            (trap / "sensitive.csv").write_bytes(b"SENSITIVE DATA NEVER OPEN")
            result = mod.inspect_package(root)
            self.assertEqual(result["figure_files_resolved"], 1)
            self.assertFalse(any("sensitive" in str(x) for x in result.values()))

    def test_figure_macro_in_comment_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root = fixture(Path(d), mdpi=True)
            tex = root / "paper/main.tex"
            tex.write_text(tex.read_text() +
                           "\n% " + r"\includegraphics{non_existent.png}")
            result = mod.inspect_package(root)
            self.assertEqual(result["figure_references"], 1)


if __name__ == "__main__":
    unittest.main()
