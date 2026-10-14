#!/usr/bin/env python3
"""Static MDPI AI manuscript package audit; never rewrites/manipulates results.

Authoritative journal class/template MUST be obtained directly from MDPI.
This tool is an evidence inventory, not a substitute for compilation, journal
staff review, source archive verification, or author/coauthor approval.

Reads ONLY paper/main.tex and paper/references.bib; examines existence of
referenced graphic and local TeX/Bib dependencies. Does not open TEST or data.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "afras-manuscript-package-evidence-v1"
MDPI_LATEX_URL = "https://www.mdpi.com/authors/latex"
MDPI_AI_INSTRUCTIONS = "https://www.mdpi.com/journal/ai/instructions"


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def no_comments(source):
    """Remove ordinary TeX comments while retaining escaped percent signs."""
    out = []
    for line in source.splitlines():
        cleaned = []
        for i, ch in enumerate(line):
            if ch == "%" and (i == 0 or not
                              (len(line[:i]) - len(line[:i].rstrip("\\"))) % 2):
                break
            cleaned.append(ch)
        out.append("".join(cleaned))
    return "\n".join(out)


def graphic_refs(source):
    return re.findall(
        r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^{}]+)\}",
        no_comments(source))


def _safe_relative(name, label):
    # A small conservative file-name validator for source dependencies.
    path = Path(name)
    _require(bool(name) and not path.is_absolute() and not
             any(part in ("..", "") for part in path.parts)
             and "\\" not in name and ":" not in name
             and not name.startswith("/"), f"Unsafe {label} path: {name!r}")
    return path


def citations_and_bibkeys(tex, bib):
    source = no_comments(tex)
    used = set()
    for match in re.finditer(
            r"\\(?:cite|citep|citet|citealp|citeauthor|nocite)"
            r"(?:\[[^\]]*\]){0,2}\s*\{([^{}]+)\}", source):
        used.update(x.strip() for x in match.group(1).split(",") if x.strip())
    # BibTeX entry lines: @article{key, @inproceedings{key, etc.
    defined = set(re.findall(r"(?m)^\s*@\w+\s*[({]\s*([^,\s{}()]+)\s*,",
                             bib))
    return sorted(used - defined - {"*"}), sorted(used), sorted(defined)


def inspect_package(root, target_journal="mdpi-ai"):
    if target_journal != "mdpi-ai":
        raise ValueError("Only provisional MDPI AI editorial preparation supported")
    root = Path(root).resolve()
    source = root / "paper/main.tex"
    _require(source.is_file(), "Missing paper/main.tex")
    raw = source.read_bytes()
    text = raw.decode("utf-8")
    cleaned = no_comments(text)
    manuscript_dir = source.parent

    cls = re.search(r"\\documentclass(?:\[([^\]]*)\])?\{([^{}]+)\}", cleaned)
    template = cls.group(2) if cls else "NOT_DECLARED"
    options = cls.group(1).split(",") if cls and cls.group(1) else []
    figure_items = graphic_refs(text)
    unresolved, resolved = [], []
    for filename in figure_items:
        rel = _safe_relative(filename.strip(), "figure")
        ext = ("",) if rel.suffix else ("", ".png", ".pdf", ".jpg",
                                        ".jpeg", ".eps", ".svg")
        possibilities = [folder / (str(rel) + suffix)
                         for folder in (manuscript_dir / "figures", manuscript_dir)
                         for suffix in ext]
        exists = any(p.is_file() and p.resolve().is_relative_to(root)
                     for p in possibilities)
        (resolved if exists else unresolved).append(filename)

    bibs = re.findall(r"\\bibliography\s*\{([^{}]+)\}", cleaned)
    bib_paths = []
    for entry in bibs:
        bib_paths += [str(_safe_relative(part.strip(), "bibliography"))
                      for part in entry.split(",")]
    local_bibs = [
        manuscript_dir / (f if f.endswith(".bib") else f + ".bib")
        for f in bib_paths
    ]
    missing_bibs = [f.name for f in local_bibs if not f.is_file()]
    missing_citations, used_citations, bib_keys = [], [], []
    if not missing_bibs and local_bibs:
        bib_text = "\n".join(f.read_text(encoding="utf-8") for f in local_bibs)
        missing_citations, used_citations, bib_keys = citations_and_bibkeys(
            text, bib_text)

    input_files = []
    for item in re.findall(r"\\(?:input|include)\s*\{([^{}]+)\}", cleaned):
        rel = _safe_relative(item, "input")
        f = manuscript_dir / (item if rel.suffix else item + ".tex")
        input_files.append({"file": str(rel), "present": f.is_file()})
    missing_inputs = [p["file"] for p in input_files if not p["present"]]

    labels = re.findall(r"\\label\s*\{([^{}]+)\}", cleaned)
    duplicates = sorted({label for label in labels if labels.count(label) > 1})
    refs = set(re.findall(
        r"\\(?:ref|eqref|autoref|cref|Cref|pageref)\s*\{([^{}]+)\}", cleaned))
    missing_refs = sorted(refs - set(labels))

    style_names = re.findall(r"\\bibliographystyle\s*\{([^{}]+)\}", cleaned)
    ieee = template == "IEEEtran"
    official_class = template in ("Definitions/mdpi", "mdpi")
    ieee_specific = sorted({
        match for match in re.findall(
            r"\\(IEEEkeywords|IEEEmembership|IEEEauthorblock[A-Z]\w*|markboth)"
            r"\b", cleaned)
    })
    redlines = sorted({
        match for match in re.findall(r"\\(rev|strk)\s*\{", cleaned)
    })

    def appears_any(pattern):
        return bool(re.search(pattern, cleaned, re.I))

    statements = {
        "author_contributions": appears_any(r"Author Contributions"),
        "funding": appears_any(r"\\(?:funding|section\*?)\s*\{Funding|Funding"),
        "institutional_review": appears_any(r"Institutional Review Board Statement"),
        "informed_consent": appears_any(r"Informed Consent Statement"),
        "data_availability": appears_any(r"Data Availability Statement"),
        "conflicts_of_interest": appears_any(r"Conflicts of Interest"),
        "acknowledgments": appears_any(r"Acknowledgments|Acknowledgements"),
    }
    warnings = []
    blockers = []
    if not official_class:
        blockers.append("WRONG_JOURNAL_CLASS")
    if unresolved:
        blockers.append("UNRESOLVED_GRAPHICS")
    if missing_bibs:
        blockers.append("MISSING_BIBLIOGRAPHY_FILES")
    if missing_citations:
        blockers.append("MISSING_BIBLIOGRAPHY_CITATIONS")
    if missing_inputs:
        blockers.append("MISSING_LATEX_INPUTS")
    if duplicates:
        blockers.append("DUPLICATE_LATEX_LABELS")
    if missing_refs:
        blockers.append("UNRESOLVED_LATEX_REFERENCES")
    if ieee_specific or style_names == ["IEEEtran"]:
        warnings.append("IEEE_SPECIFIC_MARKUP_NEEDS_CONVERSION_REVIEW")
    if redlines:
        warnings.append("TRACKED_REVISION_MARKERS_NEED_JOURNAL_REVIEW")
    if not all(statements.values()):
        warnings.append("EDITORIAL_DECLARATIONS_NEED_AUTHOR_REVIEW")
    if official_class and "ai" not in [o.strip() for o in options]:
        warnings.append("VERIFY_MDPI_AI_OPTION_IN_CURRENT_OFFICIAL_TEMPLATE")
    # Scientific integrity: a syntactically complete package never certifies
    # clinical/security dataset provenance or numerical validity.
    return {
        "schema": SCHEMA,
        "status": "NOT_READY_FOR_SUBMISSION" if blockers else
                  "MANUAL_SCIENTIFIC_AND_EDITORIAL_REVIEW_REQUIRED",
        "target_journal_provisional": "MDPI AI",
        "publisher_template_url": MDPI_LATEX_URL,
        "journal_instructions_url": MDPI_AI_INSTRUCTIONS,
        "manuscript_sha256": hashlib.sha256(raw).hexdigest(),
        "manuscript_class": template,
        "class_options": [x.strip() for x in options],
        "figure_references": len(figure_items),
        "figure_files_resolved": len(resolved),
        "figure_files_missing": len(unresolved),
        "missing_figure_paths": sorted(set(unresolved)),
        "bibliography_sources": bib_paths,
        "missing_bibliography_files": missing_bibs,
        "citation_keys_used": len(used_citations),
        "bibliography_keys_defined": len(bib_keys),
        "undefined_citation_keys": missing_citations,
        "missing_tex_inputs": missing_inputs,
        "duplicate_tex_labels": duplicates,
        "undefined_tex_refs": missing_refs,
        "bibstyle_commands": style_names,
        "ieee_specific_macros": ieee_specific,
        "revision_macros_in_use": redlines,
        "editorial_declarations_present_in_source": statements,
        "blockers": blockers,
        "manual_review_flags": warnings,
        "unverified": [
            "Venue not confirmed by authors",
            "Sources are NOT a submission-ready MDPI class until official class and compile checked",
            "Scientific results and original raw data are NOT authenticated by this audit",
            "Missing declarations may be in other forms and may be conditional",
            "No compilation/PDF layout, external hyperlinks or figure content examined",
            "Original paper and figures are never modified by this audit",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    report = inspect_package(a.repo_root)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if a.output:
        if a.output.exists():
            p.error("Refusing to overwrite old source package inventory")
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
