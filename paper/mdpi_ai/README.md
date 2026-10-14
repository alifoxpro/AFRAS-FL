# AFRAS-FL — MDPI *AI* manuscript (editorial conversion draft)

> **NOT READY FOR SUBMISSION.** This is a journal-format conversion of
> \`paper/main.tex\` from the current GitHub repository, not a reanalysis,
> replication, or claim that the manuscript's original numerical results
> have been validated.

## Files and unchanged originals

- **New draft:** \`paper/mdpi_ai/main.tex\`
- **Unchanged source:** \`paper/main.tex\` (IEEE IoT-J manuscript)
- **Unchanged citations:** \`paper/references.bib\`
- **Unchanged figures:** \`paper/figures/\` (34 graphic inclusions)
- **Updated safety check:** \`scripts/analysis/validate_mdpi_conversion.py\`
- **Scientific readiness:** \`docs/FINAL_SCIENTIFIC_SUBMISSION_READINESS.md\`
- **Editorial conversion requirements:**
  \`docs/MDPI_AI_EDITORIAL_CONVERSION_PLAN.md\`

The scientific wording, equations, tables, results, figure paths, label
references and citations are retained from the IEEE source. The only
changes INSIDE the scientific body are three explicit red-to-black
text-color commands (two diagram values and one theory group). Abstract
and keywords are unmodified. Journal-specific wrappers also differ.

The CI confirms scientific-body equality after reversing **only three
explicitly whitelisted cosmetic red-to-black text-color commands**.
Changing a numerical result, equation, citation or figure path fails the
check. Reviewer additions now print in black; struck deletions are
hidden in PDF output but remain in the source. Historical scientific
claims remain **unverified**, not endorsed or corrected.

## How to compile in a separate folder

Get the **current official MDPI LaTeX template** from:

https://www.mdpi.com/authors/latex

The template comes with \`template.tex\` and a \`Definitions/\`
directory (mdpi.cls, journal names, bibliography styles, logos).
Download the latest publisher package yourself; *MDPI's files have not
been copied into the GitHub branch*.

At the time of this source conversion, the official template page
lists publisher-maintained downloadable bibliography style variants.
For MDPI *AI*, confirm with journal instructions which of these
is appropriate, and use the publisher's \`Definitions/\` files:
https://www.mdpi.com/journal/ai/instructions

Repository layout to compile:

    paper/
      main.tex                         # ORIGINAL: never overwrite
      references.bib                   # Existing citation data
      figures/                         # All original figures
      mdpi_ai/
        main.tex                       # NEW: separate MDPI AI draft
        Definitions/                   # Add MDPI-supplied template files locally
          mdpi.cls
          journalnames.tex
          mdpi.bst
          ...

From PowerShell in the repository's root:

    cd paper\mdpi_ai
    pdflatex -interaction=nonstopmode -halt-on-error main.tex
    bibtex main
    pdflatex -interaction=nonstopmode -halt-on-error main.tex
    pdflatex -interaction=nonstopmode -halt-on-error main.tex

Run BibTeX only when the publisher-supplied current class and style
require it. The figure path is \`../figures/\` and the bibliography
is \`../references\`. Start LaTeX in \`paper/mdpi_ai/\`; running from
another working directory changes relative paths.

### Source-only CI validation

From the repository root:

    python scripts/analysis/validate_mdpi_conversion.py \
      --source paper/main.tex \
      --converted paper/mdpi_ai/main.tex

A SHA-256 match for the scientific body after exactly three cosmetic
color substitutions are normalized, matching abstract, 34 figure
references and retained citations is required.
The test does **not** perform \`pdflatex\` compilation, open PDF figures,
or authenticate published results. A separate local compilation and
human page-by-page review are still necessary.

## Editorial changes implemented

- MDPI class: \`\\documentclass[ai,article,submit,moreauthors,pdftex]{Definitions/mdpi}\`
- MDPI title/front matter and original author ORCIDs, affiliation and
  designated corresponding author transcribed from the source IEEE
  manuscript (author confirmation still required).
- MDPI \`\\abstract{}\` and \`\\keyword{}\` wrappers, preserving their
  original content.
- Alias lowercase theorem/proposition/remark/definition/example
  environments to the MDPI capitalized environments, preserving body.
- Reuse all original figures and bibliography without copying or
  renaming their assets.
- MDPI bibliography heading through \`\\reftitle{References}\` and
  publisher-class \`adjustwidth\` and \`PublishersNote\` pattern.

Class metadata and additional style settings should always be compared
with the downloaded current MDPI *AI* \`template.tex\` before submission.

## Human/editorial steps still blocking publication

- The MDPI class/style files must be obtained from the official MDPI
  website and the new source **must actually compile** with them.
- The archived IEEE source contains reviewer additions and struck
  deletions. In **paper/mdpi_ai/main.tex**, additions are rendered in
  standard black and struck deletions are suppressed in the PDF only.
  The commands and their arguments remain available in the LaTeX source
  and the IEEE original is preserved unchanged.
- \`\\authorcontributions\`, \`\\funding\`, \`\\dataavailability\`,
  \`\\conflictsofinterest\`, ethics/consent (as applicable), acknowledgments
  and any necessary disclosures are author decisions. They are
  **TODO comments, not invented declarations or blank attestations**.
- Confirm all author spellings, affiliation addresses, corresponding
  author email, journal target, APC, citation style, author contributions
  and required institution policies.
- The original CICIoT2023 and CIC IoT-DIAD2024 benchmark releases and
  raw-label/real-link evidence have not been authenticated; strict
  real-data training/TEST remain undone.
- The original historical means, p-values and deployability claims
  cannot be certified by converting them to MDPI format. They must
  receive scientific author review before a genuine submission.

## Why this manuscript should not be submitted yet

Formatting is only an *editorial* gate. The real scientific readiness
checker continues to report **NOT READY FOR SUBMISSION** until the
underlying experimental claims can be supported by source archives,
reproducible training/test artifacts, per-seed evidence and documented
source label/SDN topology semantics. Do not substitute the newly
written strict Stage 4 v2 contextual-bandit results for the historical
seven-phase AFRAS-FL manuscript without a separately approved Methods,
Results, Discussion and new study design.
