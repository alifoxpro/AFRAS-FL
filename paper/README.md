# Fuzzy-Augmented Reward Shaping for Multi-Objective DRL in Federated SDN-IoT Intrusion Detection

**Paper resubmission package — IEEE Internet of Things Journal (IoT-J)**
**Original manuscript ID:** IoT-66079-2026
**Resubmission date:** 2026-08-06

---

## Authors

| # | Name | Affiliation | ORCID | Email |
|---|------|-------------|-------|-------|
| 1 ⭐ | Ali Hussein Fadel (Corresponding) | Computer Science, University of Tabriz | [0000-0003-1360-130X](https://orcid.org/0000-0003-1360-130X) | ali_hussein_fadel@uodiyala.edu.iq |
| 2 | Jaber Karimpour | Computer Science, University of Tabriz | [0000-0001-6193-3240](https://orcid.org/0000-0001-6193-3240) | karimpour@tabrizu.ac.ir |
| 3 | Zolfaghar Salmanian | Computer Engineering, University of Tabriz | [0000-0002-1019-4123](https://orcid.org/0000-0002-1019-4123) | salmanian@tabrizu.ac.ir |

---

## Files

| File | Description |
|---|---|
| `main.tex` | LaTeX source (IEEEtran journal class) |
| `main.pdf` | Compiled manuscript (15 pages, tracked changes in red) |
| `IEEEtran.cls`, `IEEEtran.bst` | IEEE style files |
| `references.bib` | Bibliography |
| `figures/` | 34 figures (organized by section) |
| `cover_letter.md` | Cover letter for the resubmission |
| `response_letter.md` | Point-by-point response to 12 reviewer comments |

---

## Companion Code Repository

Source code, training scripts, and released `results.json` artefacts:
**https://github.com/alihusseinfadel/AFRAS-FL**

---

## Compilation

Requires MiKTeX or TeX Live with:
- IEEEtran journal class (included)
- Standard packages: amsmath, amssymb, tikz, booktabs, multirow, subcaption, soul, xcolor

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Output: `main.pdf` — 15 pages, ~10 MB.

---

## Reproducibility Statement

All numerical results are reproducible from the companion repository. See the "Reproducibility statement" section of `main.pdf` for details on the aggregation and analysis scripts that populate each table.
