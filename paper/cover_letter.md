# Cover Letter — Resubmission to IEEE Internet of Things Journal

**Date:** 2026-08-05

**To:** Prof. Yan Zhang, Associate Editor
**IEEE Internet of Things Journal**

**Subject:** Resubmission of "Fuzzy-Augmented Reward Shaping for Multi-Objective Deep Reinforcement Learning in Federated SDN-IoT Intrusion Detection"

**Original manuscript ID:** IoT-66079-2026 (rejected 31-Jul-2026, invited to resubmit as a new submission)

---

Dear Prof. Zhang and Editorial Team,

Please find enclosed our revised manuscript, resubmitted following the invitation in the 31-Jul-2026 decision letter. Per the instructions, we mention the original paper number (**IoT-66079-2026**) here and in the Author Comments field, and we have used `\textcolor{red}{...}` throughout the manuscript to make every change reader-verifiable (equivalent to Word's Track Changes).

## Summary of the revision

The original decision was rejection with an invitation to resubmit after substantial revision. Our own post-decision technical audit against the released source code independently confirmed the two reviewers on **every substantive technical point they raised (12 comments in total).** We therefore treated this revision as a full-fidelity rebuild of the paper's honesty rather than a cosmetic response.

## Concrete evidence in the revised manuscript

- **51 red-tracked change blocks** across abstract, introduction, methods, results, and limitations.
- **A new multi-seed replication study** with three independent training seeds ($\{42, 123, 2026\}$), populated in Table~\ref{tab:multiseed} from `scripts/aggregate_multiseed.py` on the released `results.json` files. This directly answers R1-3 and R2-5.
- **Three new interpretability tables** — rule statistics, cross-client stability, and DQN-vs-rule agreement — populated from `phase5_rules.json` by `scripts/compute_rule_metrics_all.py`, directly answering R2-7.
- **A $\lambda = 0$ (no-fuzzy) row** in the sensitivity table, quantifying the μ-fixed effect of removing fuzzy shaping (R1-2).
- **Proposition 1 has been renamed and restricted** to a *reference PBRS condition*; a new Applicability block, immediately following the proposition, lists the two implementation premises that are violated in the released source and states plainly that we no longer claim exact policy invariance for $R_{\text{total}}$ (R1-2, R2-1).
- **The formulation** is now described honestly as a *contextual bandit with a stochastic exogenous context stream* rather than a strict MDP (R2-2).
- **A single configuration table** (Table~\ref{tab:config}) exactly matches the released source code for every hyperparameter (R2-3, R2-8).
- **B3/B4 labels on the DIAD2024 rows** of Table~\ref{tab:phase_msr} have been corrected so that the best federated phase is highlighted honestly (R2-8).
- **Three new limitations (L6, L7, L8)** transparently document the remaining theoretical, statistical, and data-split concerns, with immediate follow-up commitments where new experiments are required (R1-1, R1-2, R2-4, R2-6).

## Remaining scope, honestly stated

Two reviewer requests require substantial new compute budget beyond what we could complete in the current cycle:
- **R2-4** — the full 6-cell per-component ablation table (only 4 of 6 cells are populated in the current version; the remaining `μ=0` cells are scheduled).
- **R2-6** — a strict record-level train/val/test split with all preprocessing refit on the training partition only.

Both are documented explicitly in the new Limitation L8 with a concrete implementation roadmap and stub scripts (`scripts/compute_rule_metrics_all.py`, `scripts/queue_R24_ablation.sh`, `scripts/aggregate_multiseed.py`) already released with this submission. We are transparent that these are the two items still owed; we did not want the visibility of the *completed* revisions to be blocked by the *ongoing* ones.

## Files enclosed

- `main.pdf` — the revised manuscript (14 pages, IEEEtran, all changes in red).
- `main.tex` + `IEEEtran.cls` + `IEEEtran.bst` + `references.bib` — the source.
- `figures/` — 34 figures (organised as `ablation/`, `fuzzy_topsis/`, `mechanism/`, `strategyB_ciciot2023/`, `strategyB_diad2024/`).
- `response_letter.md` — a per-comment reply to all 12 reviewer points, structured as (i) Concession, (ii) Change, (iii) Remaining scope.
- `cover_letter.md` — this letter.

## Reproducibility statement

All experiments in this revision are reproducible from the released repository. The `results.json` files under `experiments/results_StrategyB{,_s123,_s2026,_lam0.00,_lam0.10,_lam0.50,_R24_b}/` back every number in every table. The multi-seed table and rule-metric tables are auto-populated by the scripts named above.

We thank the reviewers again for the technical depth of the original reviews. Their feedback made this a materially more honest paper, and we hope the enclosed revision reflects that.

Best regards,

Ali Hussein Fadel
Ph.D. Candidate, Department of Computer Science
University of Tabriz
ali_hussein_fadel@uodiyala.edu.iq

*On behalf of the co-authors:*
- Prof. Dr. Jaber Karimpour (karimpour@tabrizu.ac.ir)
- Prof. Dr. Zolfaghar Salmanian Kozehkonan (salmanian@tabrizu.ac.ir)
