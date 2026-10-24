# AFRAS-FL V2 — Chat 15 Novelty Risk and Exact Contribution Gap (Pre-Result)

**Date:** 24 October 2026  
**Target journal:** *AI* (MDPI)  
**Protocol condition:** No authorized outer-heldout original native results exist; 0/54 test fits.  
**Verdict:** **CONDITIONAL GO ONLY for an evaluation-methodology / measurement contribution; NO-GO for novel fuzzy algorithm, LODO itself, or basic FedAvg/FedProx comparisons.**

## Recent directly verified prior art and consequences

| Study / stable publisher link | What the evidence actually establishes | Impact on our contribution |
|---|---|---|
| Asiri et al. (2025), “Decentralized Federated Learning for IoT Malware Detection at the Multi-Access Edge: A Two-Tier, Privacy-Preserving Design”, *Future Internet*, 17(10), 475. https://doi.org/10.3390/fi17100475 | **Uses N-BaIoT and explicit NINE leave-one-device-out federations (eight source clients, one target device)**, plus a decentralized/privacy architecture and benign-only autoencoder. Reported training uses 30 rounds and five repeats; evaluation samples are rebalanced to 50% benign/attack. | A claim that nine-fold N-BaIoT FL LODO is unprecedented is **FALSE**. Our distinct test must compare **unchanged native prevalence, supervised binary source-sampled training, class-specific exposure / overlap** rather than invent novelty from LODO. |
| Bilal et al. (2026), “Dataset-centric evaluation of federated intrusion detection models in IoT networks”, *Scientific Reports*, 16, 2683. https://doi.org/10.1038/s41598-025-32567-w | Published 16 Jan 2026. Benchmarks FedAvg, FedProx, FedNova on Edge-IIoTset, CIC-IoT2023, and TII-SSRC-23, with cross-dataset generalization and non-IID client types. It **does not use N-BaIoT** as one of its 3 main datasets. | Calling a data-centric generalization benchmark or FedAvg-vs-FedProx comparison novel is **UNSUPPORTED**. Narrow originality claim must concern *measurement of exact device-source numeric feature recurrence and its relation to model-visible source sampling* on N-BaIoT. |
| “HED-ID: a federated expert system for interpretable and resource-adaptive intrusion detection on edge devices” (2026), *Scientific Reports*. https://www.nature.com/articles/s41598-026-61336-6 | Article describes removing duplicate flow rows using SHA-256 as part of feature-data sanitization; cross-device evaluation is described for ToN-IoT settings. | “First to notice duplicate network records or use hashing to reduce leakage” is **NOT SUPPORTABLE**. Their record filtering is not demonstrated to be the same estimand as **full-source raw 115D N-BaIoT equality vs actual 240k sampled model-visible training equality**. Confirm full-text and methods before any comparison claim. |
| “Privacy-Preserving Intrusion Detection in IoT via Federated Learning” (2025 conference; online 18 Feb 2026), DOI 10.1109/Cyber-RCI68134.2025.11385047. https://doi.org/10.1109/Cyber-RCI68134.2025.11385047 | Explicit N-BaIoT benchmark and device-related non-IID partitioning; feature selection plus centralized comparator. | Another direct N-BaIoT FL baseline. Cannot claim first use of its nine devices as FL clients, or new privacy mechanism from simulating FL on a centralized runner. |
| “Federated Learning for IoT Intrusion Detection: A Comparative Study of FedAvg and FedAvgM on the N-BaIoT Dataset” (IEEE AESPC 2025), DOI 10.1109/AESPC67542.2025.11326850. https://doi.org/10.1109/AESPC67542.2025.11326850 | N-BaIoT FedAvg and FedAvgM convergence/communication comparison exists. | Neither the N-BaIoT dataset choice nor basic supervised FL comparisons are independently publishable novel method claims. |

## What the project can still test defensibly

**Potential measurable contribution:** Original dataset-wide, cross-device exact *115-feature* numerical vector recurrence can be high (historical Stage13 descriptive estimate ~90.74%) while the fitted eight-client FL model has access only to a 30k per source-device uniform subsample (240,000 training rows per fold). Therefore two quantities must never be conflated:

1. **Full-source availability recurrence**: target feature vector equals a vector somewhere in all original eight source device archives, regardless of whether that row was selected for training.
2. **Actual sampled-training exposure**: target feature vector equals a vector among the **actually trained** 8×30k original source rows, calculated **fold- and seed-specifically**.

This study can pair these descriptive strata with native full-target binary attack recall and benign false-positive rate, original attack-class support and nine-device FedAvg/FedProx BA — while explicitly reporting non-estimable missing classes, qualitative statistical uncertainty and sensitivity to attack-label confounding.

**No causal inference:** A recurrence/exposure grouping is not randomized. In N-BaIoT the cross-device exact matches have historically been overwhelmingly attack-labelled. A naive exposed-vs-unexposed overall recall difference can reflect attack family composition, class support, data construction, or label prevalence — not “FL memorization causes generalization”. Attack-class and device stratification only partially mitigate confounding; do not claim captured-packet identity.

**No method novelty:** Normalized first-order TSK fuzzy inference is equivalent to a linear model on a fixed expanded basis under the original reported assumptions, and the previously proposed fuzzy algorithm has not survived originality equivalence checks. A paper reframed as an *evaluation/measurement study* cannot honestly be titled as if a newly invented AFRAS-FL optimizer were validated.

## Decision before any expensive confirmatory training

**Conditional continuation criteria:**
1. The final eight-source real-data FL engine and classwise exact feature fingerprint recorder are frozen and directly verified.
2. Native original ZIP manifest admission is actually performed on the data used for the study, or a documented reasoned risk acceptance is made using existing bona fide historical byte audit; do not replace cryptographic proof with basename/size-only metadata.
3. A responsible human approves or takes accountable ownership of the exact scientific protocol and records it without pretending a non-existent independent scientific peer review happened.
4. All 54 planned heldout fits are retained regardless of success; full native original target prevalence preserved. Only nine devices are independent clusters for paired statistics.
5. Secondary recurrence / actual training exposure support, empirical effect sizes, and at least one discriminative study finding must emerge before claiming a materially novel evaluation contribution.

**No guaranteed acceptance or pre-result novelty proof.** Distinctive method wording should be “an exposure-aware, native-prevalence evaluation audit of cross-device FL intrusion detection” rather than “first nine-device LODO FL” or “new fuzzy federated optimizer”.

This is a literature-specific **screening**, not a claim of exhaustively searching all related works or of confirmed priority/novelty. Full text verification and journal referee interpretation can alter the verdict.
