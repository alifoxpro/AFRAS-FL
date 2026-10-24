# AFRAS-FL V2 — Stage 15 Candidate Novelty Gate (24 October 2026)

**Decision: CONDITIONAL DESIGN GO; NOT publication-level novelty GO.** The original fuzzy / federated / LODO algorithmic-firstness claims remain **NO-GO**.

## Evidence-supported hypothesis

A device-disjoint federated leave-one-device-out split need not imply unseen **numerical feature vectors**. The 24 October N-BaIoT 115-feature audit reports 6,408,420 / 7,062,606 (90.74%) held-out observations recurrent in at least one other device's training union. This is class-asymmetric: **6 recurrent benign rows and 6,408,414 recurrent attack rows**. Equal vectors are not evidence of identical packets/events. Neither recurring features nor feature-unseen rows are synonymous with known or novel malware families.

An independently recomputed 99-cell support table shows **10 structurally absent attack cells**, **38 recurrent-only attack cells**, and **42 attack cells with both recurrent and unseen support**. Only the 42 support a within-device/class exposure-conditioned attack-recall comparison. The six recurrent benign observations preclude a reliable recurrent-benign FPR comparison; no absent-class recall should be reported as 0%.

## Strict closest-prior-art boundaries

| Existing work | Clearly already established | Candidate difference for AFRAS-FL V2 |
|---|---|---|
| Asiri et al., 2025, *Future Internet* 17(10):475, DOI [10.3390/fi17100475](https://doi.org/10.3390/fi17100475) | Federated N-BaIoT, 9 device LODO, autoencoder, sensitivity/specificity | Cannot claim first LODO or first device-specific FPR; study **cross-device exact-vector recurrence as a separate exposure variable** |
| Yue et al., 2026, *Entropy* 28(9):1026, DOI [10.3390/e28091026](https://doi.org/10.3390/e28091026) | Duplicate-aware N-BaIoT processing, attack-**family** holdout, calibrated benign FPR and device analyses | Distinct **device-holdout** recurrence within native supported attack classes; not a new deduplication or unseen-family detector |
| *Uncertainty-Aware Zero-Day Botnet Detection*, 2026, *Sensors* 26(18):5863, DOI [10.3390/s26185863](https://doi.org/10.3390/s26185863) | Reports severe **Bot-IoT naive split** duplication (~97%), separate N-BaIoT zero-day tests and edge deployment | Their Bot-IoT within-split duplicates are **not equivalent** to our N-BaIoT between-device 115-feature recurrence |
| [FL-DP-NBaIoT v2.0 (Zenodo)](https://zenodo.org/records/21898821), 2026 | Software/reproducibility archive describing FedAvg-like comparisons and N-BaIoT 8-source/1-held-out LODO | Cannot claim first supervised FL comparisons or LODO; peer-reviewed status of this artifact **not independently established** |
| IEEE Cyber-RCI, DOI [10.1109/Cyber-RCI68134.2025.11385047](https://doi.org/10.1109/Cyber-RCI68134.2025.11385047) | Supervised N-BaIoT FL, non-IID partitioning, centralized comparison | FL and device heterogeneity not novel alone |

These checks do **not** prove first-in-literature priority. Reviewers may find closer work.

## Smallest defensible empirical contribution

1. A 9-device, 25-original-member public-byte-verified and class-support-aware exposure census.
2. Actual matched FedAvg/FedProx supervised **device-disjoint** predictions on **all native target rows**, and an honest nonprivate exact-feature memorization diagnostic.
3. Within-class and within-device attack-recall contrasts for only the **42 eligible** cells, device-clustered statistics, and analysis of whether model comparisons change when exposure is disclosed.
4. Fully reported negative results, limits on causal inference and source-path label ground truth; no unverified claimed security or FL privacy improvement.

## Research gate and stop rule

**CONDITIONAL GO for a bounded pre-result protocol and complete fair experiments; not a proven novel algorithm or an MDPI AI acceptance prediction.** The paper must produce demonstrably new **evaluation insight**, not merely a statement that feature duplicates exist. If the final effects and methods yield no scientifically substantive interpretation beyond the cited works, pivot the contribution/journal rather than proliferating fuzzy modifications.

All final target predictions remain **not run** at this point. Prior source-only AdamW BA=99.61% on Samsung is feasibility, not final LODO. Historical model-selection exposure to Samsung and the other source devices must be disclosed; do not misrepresent nine historically blind lockboxes.