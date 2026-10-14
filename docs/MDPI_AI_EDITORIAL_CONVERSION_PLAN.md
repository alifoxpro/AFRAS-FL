# MDPI AI — non-destructive editorial conversion plan and source-asset audit

**Date reviewed:** 2026-10-14  
**Journal target:** *MDPI AI* is only a **provisional target** inferred from the
research workflow; do not submit, rewrite the paper, change journal style or
alter authorship without the corresponding author's confirmation.
**Source manuscript:** \`paper/main.tex\` is an IEEE Internet of Things Journal
revision prepared in \`IEEEtran\`, not an MDPI AI submission. The official
manuscript PDF, source LaTeX, references, tables, figures, scientific values
and all coauthor information remain unchanged on this branch.

## Official sources: always obtain the current publisher template

- MDPI official LaTeX downloads, class directory \`Definitions\`:
  https://www.mdpi.com/authors/latex
- MDPI AI author instructions:
  https://www.mdpi.com/journal/ai/instructions
- MDPI AI journal homepage:
  https://www.mdpi.com/journal/AI
- Official MDPI article template, author **MDPI**, on Overleaf:
  https://www.overleaf.com/latex/templates/mdpi-article-template/fcpwsspfzsph

The publisher's \`template.tex\` uses MDPI's class and a \`Definitions\`
subfolder containing required classes/styles; a representative class
directive has the form:

    \documentclass[ai,article,submit,moreauthors,pdftex]{Definitions/mdpi}

Class options, metadata commands, bibliography style, declarations and
template distribution may change. **Use the current MDPI-supplied
\`template.tex\` unchanged as the starting point**; the class directive
above illustrates syntax rather than claiming it is a universally
current drop-in replacement for the IEEE document. Do **not** simply
replace \`IEEEtran\` with \`Definitions/mdpi\` in \`paper/main.tex\`:
IEEE and MDPI frontmatter / citation / metadata structures are different.

Publisher-supplied templates/classes may carry licensing, formatting and
distribution restrictions; do not copy a third-party mirror's \`mdpi.cls\`
into the public AFRAS-FL repository as an ad hoc workaround.

## Results of the source-only dependency inspection

The new checker \`scripts/analysis/audit_mdpi_source_package.py\` examined
the files committed on the audit branch (not the full typeset PDF):

| Item | Checked status |
|---|---|
| Figure inclusion references | 34 |
| Figure file paths missing from the checked repository tree | 0 |
| Citation keys absent from \`paper/references.bib\` | 0 |
| Bibliography source files | \`paper/references.bib\` present |
| LaTeX class | \`IEEEtran\` — wrong for MDPI AI |
| Bibliography style | \`IEEEtran\` — requires MDPI template review |
| Manuscript revision coloring/strike-through | \`\\rev\`, \`\\strk\` — needs author/editor decision |

These are **static token/path checks**. They DO NOT establish successful
LaTeX compilation, figure resolution / copyright, literature correctness,
valid journal formatting, original dataset provenance, or scientific truth.
The checker also reports duplicate labels, undefined LaTeX references and
missing TeX input dependencies if detected.

Run the checker locally:

    python scripts/analysis/audit_mdpi_source_package.py --repo-root . --output /tmp/afras_mdpi_package.json

GitHub Actions stores the matching JSON as
\`mdpi-latex-dependency-inventory\` on the audit branch. Read
\`manual_review_flags\` and \`editorial_declarations_present_in_source\`
for the list of possible author disclosures.

## Conversion: remaining human-approved tasks

1. **Confirm target journal.** If the real intended venue is still IEEE
   Internet of Things Journal, do NOT convert to MDPI at all. Journal
   change may also affect the paper's scope, references, ethics
   declarations, APC, review status and coauthor agreement.
2. **Create a separate MDPI working manuscript** only on author approval:
   e.g. a new local submission directory, not overwriting
   \`paper/main.tex\`. Start from the up-to-date publisher template,
   keep original \`paper/figures\` and \`paper/references.bib\` separately,
   and preserve a hash of the original \`paper/main.tex\`.
3. **Recreate frontmatter using MDPI's official template:** title,
   author names, corresponding author, affiliations, emails, ORCID,
   abstract and keywords. Do not copy IEEE \`\\IEEEmembership\`,
   \`\\markboth\`, \`\\IEEEkeywords\` or the journal header into MDPI.
   Never change author identities or claimed institution without approval.
4. **Port sections, equations, algorithms, tables, TikZ and figures**
   without altering scientific content. Review incompatible IEEE LaTeX
   macros and style packages. MDPI caption/figure/table requirements
   may differ; recompile using the **actual** MDPI class from the
   institution's release, and inspect every page manually.
5. **Rebuild bibliography and citations** in MDPI's required style using
   publisher-shipped bibliography settings. A resolved citation key
   alone does not establish proper citation formatting or source validity.
6. **Required or conditionally required editorial statements:** author
   contributions, funding, institutional ethics where applicable,
   informed consent where applicable, data availability, conflicts of
   interest, acknowledgments as applicable, and disclosure of
   substantive AI assistance as required by the venue's current
   policy. Do not invent an ethics clearance, funding award or data
   availability declaration.
7. **Remove tracked-change markup only upon approval.** The original
   red \`\\rev\` and strikethrough \`\\strk\` indicate a reviewer revision;
   a clean manuscript and a marked revision may have different roles.
8. **Scientific integrity blocker remains:** converting document
   formatting does NOT independently validate raw CICIoT2023/DIAD2024
   data, 5 physical SDN links, historical 50-episode p-values,
   performance measures, contextual-bandit vs true multi-step RL,
   fuzzy pipeline equivalence, latency claims or sealed TEST.
   Do not send the manuscript with an unverified empirical narrative.

## Immediate author decision required

**Which is the actual target journal for this manuscript:
(1) MDPI AI or (2) IEEE Internet of Things Journal?**

The question matters because the current source, title block, bibliography
and existing cover/reviewer letters all explicitly target IEEE IoT-J,
while the scientific-audit branch is named MDPI. Converting it without
confirmation would risk preparing the wrong editorial package.

**No original scientific manuscript file was edited by this audit.**
