#!/usr/bin/env python3
"""Verify *formatting-only* GitHub IEEE -> MDPI AI manuscript conversion.

Fail CLOSED whenever a scientific body token is altered, removed, inserted,
reordered or reinterpreted. Figures/bib remain shared read-only assets.
This checker does not authenticate historic results or compile MDPI PDFs.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "afras-mdpi-structural-conversion-integrity-v1"
BODY_START = r"\section{Introduction}\label{sec:introduction}"
SOURCE_END = r"\bibliographystyle{IEEEtran}"
MDPI_BODY_END = "% MDPI editorial declarations REQUIRE confirmation"
ABSTRACT_START = r"\begin{abstract}"
ABSTRACT_END = r"\end{abstract}"
MDPI_ABSTRACT_START = "% Abstract is inherited verbatim, including historical unverified metrics.\n\\abstract{\n"
MDPI_ABSTRACT_END = "\n}\n\n\\keyword{"


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def span(text, before, after, label):
    if text.count(before) != 1 or text.count(after) != 1:
        raise ValueError(f"Expected exactly one {label} delimiters")
    a = text.index(before) + len(before)
    b = text.index(after, a)
    return text[a:b]


def _source_title(src):
    m = re.search(r"\\title\{([^\n]+)\}", src)
    if not m:
        raise ValueError("Source paper title missing")
    return m.group(1).strip()


def _source_keywords(src):
    return span(src, r"\begin{IEEEkeywords}", r"\end{IEEEkeywords}", "source keywords").strip()


def _source_body(src):
    return span(src, BODY_START, SOURCE_END, "IEEE manuscript body").rstrip()


def _new_body(mdpi):
    marker = "% Scientific body copied unchanged from paper/main.tex.\n"
    return span(mdpi, marker + BODY_START, MDPI_BODY_END, "MDPI manuscript body").rstrip()


def verify_conversion(ieee, mdpi):
    if (r"\documentclass[ai,article,submit,moreauthors,pdftex]{Definitions/mdpi}"
            not in mdpi):
        raise ValueError("MDPI AI must use the explicit publisher class path/option")
    if re.search(r"\\documentclass.*\{IEEEtran\}", mdpi):
        raise ValueError("Original IEEE class must not be reused for MDPI AI")
    if r"\bibliographystyle{IEEEtran}" in mdpi or r"\IEEEkeywords" in mdpi:
        raise ValueError("IEEE bibliography/keywords not converted")
    if r"\bibliography{../references}" not in mdpi:
        raise ValueError("MDPI manuscript must reference the original bibliography")
    if r"\graphicspath{{../figures/}}" not in mdpi:
        raise ValueError("MDPI manuscript must reuse exact source figures")
    original_body = BODY_START + _source_body(ieee)
    new_body = BODY_START + _new_body(mdpi)
    if original_body != new_body:
        raise ValueError(
            "SCIENTIFIC BODY ALTERED: formatting-only conversion must preserve "
            "all sections, figures, equations, numerical values and citations verbatim")
    source_title = _source_title(ieee)
    if r"\Title{" + source_title + "}" not in mdpi:
        raise ValueError("Source title changed without author authorization")
    ab = span(ieee, ABSTRACT_START, ABSTRACT_END, "original abstract").strip()
    new_ab = span(mdpi, MDPI_ABSTRACT_START, MDPI_ABSTRACT_END, "MDPI abstract").strip()
    if ab != new_ab:
        raise ValueError("Original unverified abstract altered: author review required")
    source_keys = _source_keywords(ieee)
    if r"\keyword{" + source_keys + "}" not in mdpi:
        raise ValueError("Original keyword sequence altered")
    figs = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}", original_body)
    citations = re.findall(
        r"\\cite(?:p|t)?(?:\[[^\]]*\])?\{([^{}]+)\}", original_body)
    if not figs or not citations:
        raise ValueError("Expected source figures/citations were lost")
    if mdpi.count(r"\begin{document}") != 1 or mdpi.count(r"\end{document}") != 1:
        raise ValueError("MDPI document start/end unbalanced")
    return {
        "schema": SCHEMA,
        "integrity": "SOURCE_BODY_AND_ABSTRACT_BYTE_FOR_BYTE_IDENTICAL",
        "source_scientific_body_sha256": sha(original_body),
        "converted_scientific_body_sha256": sha(new_body),
        "original_abstract_sha256": sha(ab),
        "converted_abstract_sha256": sha(new_ab),
        "figure_inclusions": len(figs),
        "citation_commands": len(citations),
        "source_title": source_title,
        "source_keywords_preserved": True,
        "manuscript_ready_for_submission": False,
        "limitations": [
            "No real-dataset result authenticated; these are preserved historical claims",
            "No MDPI Definitions class bundled; compilation requires official publisher ZIP",
            "Author declarations, target journal/current citation options and full rendered PDF await approval",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path("paper/main.tex"))
    p.add_argument("--converted", type=Path, default=Path("paper/mdpi_ai/main.tex"))
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    report = verify_conversion(
        a.source.read_text(encoding="utf-8"),
        a.converted.read_text(encoding="utf-8"))
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if a.output:
        if a.output.exists():
            p.error("Refusing to overwrite old MDPI conversion integrity report")
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
