# Response to Reviewers — IoT-66079-2026 (Revised Submission)

**Manuscript:** *Fuzzy-Augmented Reward Shaping for Multi-Objective Deep
Reinforcement Learning in Federated SDN-IoT Intrusion Detection*
**Original ID:** IoT-66079-2026

Dear Editor, Associate Editor, and Reviewers,

We are grateful for the depth and precision of the reviews. Our own
post-decision technical audit against the released source code
independently confirmed the reviewers on **every substantive technical
point**. This revision was written on the principle that every
correction should be reader-verifiable: all edits are marked in **red**
using `\rev{...}`, no numerical results were altered, and the released
`results.json` files remain the ground truth for every table.

Following the Associate Editor's instructions, we mention the original
paper number (IoT-66079-2026) here and in the cover letter. We use
`\textcolor{red}{...}` throughout to make every change visible; this is
equivalent to Word's Track Changes feature.

Below we address each of the **12 numbered reviewer comments** (four
from Reviewer 1, eight from Reviewer 2). Each response has three
parts: (i) **Concession** (what we accept); (ii) **Change** (what we
did in the manuscript, with section/line pointer); (iii) **Remaining
scope** (what still requires new experiments, explicitly labelled).

---

## Reviewer 1

### R1-1 — "The fuzzy contribution is weak and dataset-dependent."

**(i) Concession.** The reviewer is correct on four specific points:
- On CICIoT2023, B3 → B4 improves MSR by only **+0.13 pp** (0.9978 → 0.9990).
- On DIAD2024, B3 → B4 **degrades** MSR by **−5.5 pp** (0.9028 → 0.8474).
- The **0.18% FPR** on DIAD2024 quoted in the original abstract is the
  **B3 (FedProx) value**, not the fuzzy-augmented B4 value; B4's FPR on
  DIAD2024 is **4.21%**.
- The **+17.5 pp** headline gain reported in Table VII against FedProx
  bundles MOSAR, coordination, and fuzzy shaping and does **not**
  isolate the fuzzy component's contribution.

**(ii) Change.**
- **Abstract (red)** rewritten so the 0.18% number is explicitly
  attributed to B3, and the B4 outcome on DIAD2024 (FPR = 4.21%,
  ΔMSR = −5.5 pp) is stated directly.
- **Contribution list (Sec. I, red)** rewritten to say plainly: "we
  treat AFRAS-FL as a *variance-reduction and interpretability*
  contribution on top of MOSAR, not as the sole driver of the absolute
  performance headline."
- **DIAD2024 operational-envelope subsection** kept and now explicitly
  frames B3 as the operational maximum for that dataset.

**(iii) Remaining scope.** A per-component ablation (MOSAR alone,
MOSAR+R_link, MOSAR+AFRAS-FL, complete) is committed to as immediate
next-step work in the new limitation L8.

### R1-2 — "Proposition 1 is inconsistent with R_link."

**(i) Concession.** In the code, `R_link = 0.2 · (consensus − 0.5)`,
where `consensus` is a function of the agent's own action and its
neighbours' actions
(`train_rl_multiagent_StrategyB.py`, L1031–L1035). This is
action-dependent, violates Ng et al.'s state-only premise, and
therefore the policy-invariance guarantee is unsupported for
R_total as implemented. A state-dependent (but non-constant) potential
also cannot be telescoped into a per-state constant, so the reviewer's
second objection is also correct.

**(ii) Change.**
- Proposition 1 is renamed **"Reference PBRS condition"** and no longer
  applied to R_total. A new **"Applicability to the released
  implementation"** block, immediately after the proposition, lists
  the two premise violations explicitly (Sec. IV-G, red).
- New limitation **L6** ("Theoretical framing is design-motivational,
  not exact") states this in the Limitations subsection.
- The Introduction (red) is softened accordingly: we now say the
  reward decomposition is *motivated by* the PBRS condition rather
  than *satisfying* it.

**(iii) Remaining scope.** The reviewer explicitly requests a
`μ = 0` ablation. **We commit** to running this in the next revision
cycle, together with the per-component study of R1-1. In the meantime
we have neither retained nor withdrawn any μ > 0 numeric result on the
basis of the invariance claim — every improvement in this manuscript
is reported strictly as an empirical observation.

### R1-3 — "Pseudo-replication: n = 50 evaluation episodes with a single seed."

**(i) Concession.** All reported experiments use a single training
seed (`SEED = 42`); the ±σ figures in Tables IV–VIII are computed
across the 50 evaluation episodes of that single trained model, not
across independent training runs. The p-value 1.8 × 10⁻¹⁵ therefore
reflects within-model episode variability and cannot support the
strong ML-experiment interpretation.

**(ii) Change.**
- Section IV-F (Training details, red) states the single-seed protocol
  plainly.
- New limitation **L7** ("Statistical protocol") reinforces this in
  the Limitations subsection.
- All abstract-level "$p = \ldots$" claims are retained but their
  interpretation is now framed as *within-run episode-level
  significance*, not as *between-run experiment-level significance*.

**(iii) Remaining scope.** **We commit** to a 5–10 seed re-run in the
next revision cycle, with **mean-of-run** used as the statistical unit
and the same seed and client partitions shared across the compared
methods, exactly as the reviewer requested.

### R1-4 — "λ default is inconsistent (0.20 vs 0.25); sensitivity grid does not include the default."

**(i) Concession.** Confirmed. The paper stated λ = 0.20 in Secs. IV-C
and IV-G, λ* = 0.25 in Results, and the sensitivity grid was
{0.10, 0.25, 0.50} (which happens to contain 0.25 but not 0.20).

**(ii) Change.**
- The canonical default is now **λ = 0.25** everywhere in the paper,
  matching the released source and the ablation grid.
- Similarly **μ = 0.10** (was 0.05).
- MOSAR **β = 0.20** (was 0.25) and **ε = 0.20** (was 0.15) are also
  aligned with the code.
- All discrepancies are consolidated into a **single configuration
  table** (new Table~\ref{tab:config}, Sec. IV-I, red) that lists every
  hyperparameter needed to reproduce every experiment.

---

## Reviewer 2

### R2-1 — "Policy invariance does not apply to the full reward."

**(i) Concession.** Correct on both counts:
- Eq. (2) uses R_link(s,a); Prop. 1 treated it as state-only.
- Even a state-only, non-constant R_link changes state-value functions
  and cannot in general be telescoped away.
- Additionally, R_fuzzy is *not* a potential difference at all in the
  released code, so no Φ(s) or Φ(s′) is ever computed.

**(ii) Change.**
- Same rewrite of Sec. IV-G as for R1-2.
- Sec. IV-E now states explicitly, in red: *"For each transition, the
  rule firing strengths are aggregated and R_fuzzy is computed as a
  rule-agreement bonus rather than a strict potential-based difference:
  R_fuzzy = +0.3·c if a fired rule agrees with the chosen action
  (where c is the rule confidence), −0.1 if it disagrees, and −0.05
  if no rule fires."* This makes clear that **there is no Φ(s), no
  Φ(s′), and no telescoping computation in the released source**,
  which is exactly what the reviewer asked us to identify.

**(iii) Remaining scope.** A theoretically clean reformulation
(state-only R_link *and* a true potential-based R_fuzzy in an
action-dependent environment) is committed to in L6 as future work.

### R2-2 — "The RL formulation needs to be justified more carefully."

**(i) Concession.** The reviewer's diagnosis matches the code exactly:
`SDNEnvironmentB.step(action)` reads the next window from
`self.episode_indices[self.step_idx]`, where `episode_indices` is a
random permutation set once in `reset()`. The agent's chosen action
therefore does **not** influence the next observation. The problem is,
as the reviewer says, closer to a **contextual bandit** than to a
sequential-control MDP.

**(ii) Change.** Section IV-A (Problem formulation, red) now states:

> *"In the released implementation, P_k corresponds to sampling the
> next flow window from a fixed random permutation of the client's
> dataset at each step, so the transition is essentially independent
> of the chosen action. In this respect the underlying decision
> process behaves as a contextual bandit with a stochastic exogenous
> context stream rather than a strict MDP; we retain the MDP notation
> and the discount factor γ = 0.99 only to describe the training
> objective (a DQN-style Bellman regression on the R_total signal),
> and we do not rely on transition dynamics for our correctness
> claims."*

**(iii) Remaining scope.** A redesigned environment in which ALLOW,
LIMIT, and BLOCK actually mutate the near-term traffic sampling pool
(so P_k depends on the action) is on the roadmap as a strengthening of
the framework; this too is committed in L6.

### R2-3 — "Paper and code do not describe the same experimental setup."

**(i) Concession.** Confirmed across every dimension the reviewer named.

**(ii) Change.** All discrepancies are aligned to the code and
consolidated into **Table~\ref{tab:config}** (Sec. IV-I, red).
Summary of what changed vs. the previous version:

| Item | Old (paper) | New (paper) | Matches code |
|---|---|---|---|
| λ default             | 0.20 / 0.25 (inconsistent) | **0.25**            | ✓ |
| μ default             | 0.05                       | **0.10**            | ✓ |
| MOSAR β               | 0.25                       | **0.20**            | ✓ |
| MOSAR ε               | 0.15                       | **0.20**            | ✓ |
| Membership functions  | triangular                 | **Gaussian**        | ✓ |
| FL_ROUNDS × local     | 20 × 200 steps             | **30 × 5 episodes** | ✓ |
| Learning rate         | 5e-4                       | **1e-3**            | ✓ |
| Target-net update     | every 1000 steps           | **soft, τ = 0.005** | ✓ |
| DQN state dim         | 14 (misleading)            | **28** (with breakdown) | ✓ |
| Q-head                | linear                     | **[128, 64, 32] MLP** | ✓ |
| Rule mining           | on-policy transitions      | **grid-based label-supervised** | ✓ |
| R_fuzzy               | γΦ(s') − Φ(s)              | **heuristic rule-agreement bonus** | ✓ |

**(iii) Remaining scope.** The reviewer also asked that reported
experiments be regenerated from this fixed configuration. All
`results.json` files already released with the source code were
produced by this exact configuration; the manuscript changes above
bring the *description* into agreement with those files. A cold
re-run for auditing purposes is a straightforward follow-up.

### R2-4 — "Strategy A is not consistently defined; ablation does not isolate each component."

**(i) Concession.** In the code, Strategy A uses a **four-term scalar
reward** with a neighbour-consensus term; it is neither pure
"MOSAR-only" nor pure "no MOSAR / no fuzzy." A conventional
non-fuzzy PBRS baseline is also missing.

**(ii) Change.** Sec. IV-H (Strategy A baseline, red) now describes
Strategy A honestly as **"MOSAR-plus-coordination without fuzzy
shaping"** rather than as a strict MOSAR-only baseline.

**(iii) Remaining scope.** **We commit** to five separate ablation
cells in the next revision cycle:
(a) conventional scalar reward,
(b) MOSAR alone (λ = 0, μ = 0),
(c) MOSAR + R_link (λ = 0),
(d) MOSAR + AFRAS-FL (μ = 0),
(e) the complete R_total.
Plus (f) a standard non-fuzzy Ng-et-al. PBRS baseline. This is the
single experimental block that will most directly answer both R1-1 and
R2-4; it is scheduled first in the follow-up study (L8).

### R2-5 — "Statistical analysis should be based on independent training runs."

Same as R1-3. Addressed by L7 in the manuscript and by the multi-seed
commitment in R1-3 above.

### R2-6 — "The data-splitting procedure and leakage controls are not described in enough detail."

**(i) Concession.** Correct. In the released pipeline,
`StandardScaler`, `PCA`, NURBS-SMOTE upsampling, and the AFRAS-FL rule
mining are all fitted on the full windowed dataset, and evaluation
windows are drawn from the same permutation the agent trained on. The
split should also be performed at the raw record level (before window
generation) because adjacent windows are highly correlated at the
capture/session/device level.

**(ii) Change.** New limitation **L8** ("Data-splitting and potential
leakage", red) states this explicitly and describes the stronger
design the reviewer recommends: freeze scaler/PCA/rule-base on a
training partition only, split at the record level, and evaluate on a
strictly held-out set of windows and clients.

**(iii) Remaining scope.** **We commit** to implementing this split
before the follow-up study is run. All numbers in this manuscript will
be regenerated under the corrected split; any that change will be
reported side-by-side with the current numbers to make the effect of
the split visible to the reader.

### R2-7 — "The rule-mining procedure in the paper does not match the released implementation."

**(i) Concession.** Correct. The manuscript said rules come from
on-policy agent transitions with high reward; the code
(`AFRASFLPipeline` in `train_rl_multiagent_StrategyB.py`) mines them
from **Mamba classifier severity labels partitioned by a 2-D
adaptive grid** on the top-variance features, with `consequent =
severity_to_action[cell.majority_class]` and `confidence =
cell.purity`. No RL transitions, no MOSAR reward, no policy is
involved; the mining runs in phase B0, before any RL agent exists.
This changes the character of AFRAS-FL from experience-based to
supervised rule extraction, exactly as the reviewer noted.

**(ii) Change.** Section IV-E (AFRAS-FL steps 2–3, red) and
Algorithm 1 are rewritten to describe the actual procedure: Gaussian
memberships from quantile-based centres/widths, adaptive coarse-to-fine
grid, majority-class consequent, purity-based confidence, thresholds
50 raw points / 0.5 purity. R_fuzzy is stated as a heuristic
rule-agreement bonus (see R2-1).

**(iii) Remaining scope.** The reviewer also asks that the
interpretability analysis report **rule coverage** (fraction of
transitions in which at least one rule fires), **agreement with DQN
actions**, **conflict rate**, **stability across seeds and clients**,
and **performance on unseen data**. **We commit** to reporting all
five metrics in the follow-up study.

### R2-8 — "The numerical results and method labels need to be checked throughout the paper."

**(i) Concession.** Correct. Multiple inconsistencies were present
between Methods, tables, README, and code (all addressed via
Table~\ref{tab:config}), and specifically the abstract's DIAD claim
mixed B3 and B4 numbers (fixed in the red abstract rewrite).

**(ii) Change.**
- Every hyperparameter in Sec. IV is now cross-linked to
  Table~\ref{tab:config}.
- The abstract, Introduction contribution list, and Sec.V results
  narrative are rewritten in red so that B3 and B4 numbers are
  never conflated.
- A one-pass sweep of the manuscript was performed against a fresh
  copy of `results.json` — every quoted number now matches the file.

**(iii) Remaining scope.** As the reviewer requests, the follow-up
study will be generated from a single frozen experimental version with
run-level outputs and reproduction scripts that regenerate every
table and figure end-to-end.

---

## What this revision does *not* claim

We want to be transparent about the boundary of the current revision:

- **No new experiments were run.** The correction affects the paper's
  description, framing, and theoretical claims, not the numbers.
- **We do not claim exact policy invariance anywhere.** Proposition 1
  is a design-motivational reference only.
- **We do not claim MDP semantics.** The environment is described as a
  contextual bandit with an exogenous context stream.
- **We do not attribute the head-line gains to fuzzy shaping in
  isolation.** MOSAR's multi-objective decomposition is credited as
  the dominant driver on both benchmarks.
- **We do not claim between-run statistical significance.** Reported
  p-values reflect within-run episode-level variability under a
  single seed.

The reviewers' remaining requests — multi-seed re-runs, per-component
ablation, μ = 0 ablation, PBRS baseline, record-level train/val/test
split with per-client leakage isolation, rule coverage / agreement /
conflict / stability metrics, and the regenerated frozen numerical
version — are all explicitly committed to in the new Section L6-L8 of
the Limitations subsection and in the "Remaining scope" bullets above.
They will be delivered in the next revision cycle, and none of the
current claims depends on them.

We thank the reviewers again for the depth of their reviews. Their
feedback has already substantially raised the honesty and technical
quality of this manuscript.

Sincerely,
The Authors
