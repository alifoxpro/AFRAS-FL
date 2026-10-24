# AFRAS-FL V2 — Pre-result manuscript foundation (Chat 22)

**Working title:** Cross-Device Exact-Feature Recurrence in Federated IoT Intrusion Detection: A Nine-Device Native-Prevalence Evaluation

**Research target:** MDPI *AI*. **Status:** DRAFT METHODS ONLY; genuine nine-device confirmatory results **0/54**, human authorization **NOT RECEIVED**. This document is not a submitted manuscript, accepted novelty claim, or authorization to score held-out data. Written 24 October 2026 from the frozen Stage 16 protocol and successfully verified Chat 21 Route B source evidence. The original training and statistical source code is not modified by this file.

## 1. Introduction — tightly bounded research question

Machine-learning-based IoT intrusion detection is often assessed through data partitions whose relationship to physical devices and previously observed numerical patterns is incompletely characterized. N-BaIoT provides traffic-derived features from nine commercially available IoT devices exposed to Mirai and BASHLITE/Gafgyt attack activity (Meidan et al., 2018). Its device-level heterogeneity makes it relevant to federated evaluation, but withholding a device does not, in itself, guarantee that each numerical feature vector from that device is absent from the remaining source-device datasets.

Federated averaging is an established optimization baseline (McMahan et al., 2017), while FedProx introduces a proximal local objective to address heterogeneous optimization (Li et al., 2020). Prior IoT-malware work has already investigated N-BaIoT in a nine-device federated setting (Asiri et al., 2025). Consequently, neither the use of FedAvg/FedProx nor leave-one-device-out evaluation is asserted to be novel here. The narrower, **hypothesized** contribution is a reproducible distinction between (a) exact-feature recurrence somewhere in an available source-device corpus and (b) exact-feature recurrence in the actual sampled training set encountered by the federated model; the empirical implications for native-prevalence, device-held-out detection remain **unmeasured**.

## 2. Materials and Methods

### 2.1 Dataset, provenance, and source admissions

The study uses the UCI N-BaIoT dataset (Meidan et al., 2018; DOI: 10.24432/C5RC8J). The official corpus contains nine device partitions, 7,062,606 observations, 115 ordered continuous feature columns and ten attack subtypes in two malware families in addition to the benign class. The binary endpoint uses benign versus attack; original attack-subtype labels are preserved solely for class-conditional secondary analyses. Dataset labels in this implementation are derived from native source-member paths; their packet-level correctness has not been independently re-established.

Provenance route B retains all 25 original publisher-source CSV/RAR members but repackages them into nine new device ZIP wrappers. These ZIP wrappers are **not byte-identical to the researcher's historical ZIP wrappers** and must not be described as such. An immutable source candidate manifest binds the nine reconstructed wrapper SHA-256 hashes; SHA-256 of that manifest is `4a67e3d78e75f5f771d19a8ea3bfef043a11110726fe48331583f6de414e2e6a`. The prior locally recorded 23 native-member digests were compared successfully against the publisher-sourced members; the two Ennio members were present in the public UCI source but were not independently matched against historical local originals in that comparison. The official transport checksum used for this study is a **study-observed digest**, not a publisher-issued digital signature.

Before any confirmatory training, a reproducible data admission pipeline verified 9/9 newly generated ZIP-wrapper hashes, the original 25 members, identical ordered 115-feature CSV headers, and all 99 device–class row support counts against the frozen inventory. This verification is documented in GitHub Actions run 40130453516. The admission checks do not themselves establish attack-label validity beyond the dataset-source labeling.

### 2.2 Device-disjoint experimental design

The pre-result frozen protocol specifies nine leave-one-device-out outer folds. In each fold, the held-out device supplies **all native observations** for binary evaluation, preserving the original benign/attack distribution and all supported attack classes. The remaining eight devices are independent logical federated clients. Fitted preprocessing, local training, class-weight estimation, model selection, threshold selection and checkpoint selection may not use the held-out device. This is device-disjoint evaluation, **not** a claim that all feature vectors are previously unseen.

A source-only, uniform-without-replacement sampling procedure selects 30,000 training observations per source device using the locked seed-specific priority scheme, giving 240,000 selected source observations per fold and seed. The device's native class distribution is retained in the evaluation set; the source subsampling approximates but does not enforce exact native prevalence within each training client. The same sampled source-row identities and source normalization are reused for matched FedAvg and FedProx arms.

The nine folds are crossed with two algorithms and the three prespecified random seeds 3107, 3108 and 3109. Thus, 9 × 2 × 3 = **54** confirmatory model fits are required, with no selection of favourable folds or seeds.

### 2.3 Preprocessing and fixed predictive model

For each source vector, the 115 original `float64` features undergo elementwise inverse hyperbolic sine transformation **before** conversion to `float32`. The mean and standard deviation for normalization are estimated from the union of the eight *sampled training-source* partitions; source columns with estimated standard deviation below `1e-6` are assigned scale 1. At test time, the same feature order, transformation and frozen source-derived scaling are applied without refitting on the held-out device.

The classifier is a binary multilayer perceptron with widths 115–64–32–1, ReLU hidden activations and a final logit. Each client minimizes binary cross-entropy with logits and a positive-class weight equal to its sampled benign-to-attack count ratio. Local optimization uses AdamW with learning rate 0.001, weight decay 0, batch size 128 and three local epochs per communication round. The server aggregates eight client state dictionaries by the numbers of source samples; all clients participate in each of five rounds. The optimizer is reinstantiated for each client's local optimization at every round.

The FedAvg arm uses this fixed optimizer and aggregation schedule (McMahan et al., 2017). The FedProx arm adds `(0.01/2) * ||w_local - w_round_start||²` to the local objective, with all other prescribed settings held equal (Li et al., 2020). Final checkpoint selection is the last scheduled round, and the fixed attack-probability threshold is 0.5. No outer-device tuning or retrospectively optimized threshold is permitted.

### 2.4 Exact-feature recurrence variables

To distinguish source availability from sampled model exposure, native original `float64` feature vectors are canonicalized to little-endian IEEE-754 bytes, with signed zero normalized, and assigned 128-bit BLAKE2b fingerprints. A digest match is an indicator of equal canonical numeric feature representation, **not** a verified match of the underlying network capture, packet sequence, attack occurrence or causal leakage. Cryptographic hash collisions are theoretically possible; original row semantics are not independently recoverable from a fingerprint alone.

The **full-source availability** indicator marks a target row if its fingerprint occurs in any observation from the complete eight-device source corpus. The **actual training exposure** indicator marks a target row if its fingerprint occurs among the 240,000 source observations selected under the fold's original random seed. These indicators are not interchangeable.

After all model predictions have been generated and securely retained, the preregistered secondary analysis separates target observations into three mutually exclusive feature-availability strata: (1) exact vector present in the selected source training examples; (2) present elsewhere in the complete source corpus but not among selected training examples; and (3) absent from all eight source corpora. Within supported held-out device/attack-class cells, report attack recall for each stratum and only descriptive contrasts where denominators are nonzero. For benign observations, report false-positive rate rather than attack recall. Missing class or stratum denominators are labelled **NON_ESTIMABLE**, not zero. This observational analysis cannot establish that recurrent vectors caused any difference in classification.

### 2.5 Outcomes, statistical inference and independent evidence replay

The primary evaluation endpoint is the native-prevalence binary balanced accuracy on each complete held-out device:

`BA = 0.5 * [TP/(TP+FN) + TN/(TN+FP)]`.

For each device and algorithm, balanced accuracy is averaged across the three fixed seeds. The primary contrast is the equal-device-weighted mean of nine *paired* device differences, FedProx minus FedAvg. The **nine held-out devices** are the inferential units; neither the 54 training runs nor the millions of observations are treated as statistically independent devices.

The prespecified analysis enumerates all 2^9 = 512 sign reversals of the nine paired differences to calculate a two-sided sign-flip statistic and resamples nine complete device pairs 10,000 times for a percentile bootstrap interval. The sign-flip interpretation depends on the symmetry/exchangeability assumptions relevant to the paired design, and bootstrap intervals with only nine devices are necessarily uncertain. The analysis additionally reports device-specific balanced accuracy, benign false-positive rate, attack recall, worst-device performance and all paired effects. No post-result hyperparameter, threshold, fold or seed changes are permitted in the confirmatory analysis.

Every output run must retain complete held-out row-level probabilities and native labels, trained checkpoint, source-client/sample receipt, actual-training fingerprint sidecar, code/data SHA-256, and independent row-by-row metric replay. The replay recomputes class support, binary confusion and metrics without reusing model inference code. Missing, corrupt or unauthorised runs invalidate the prespecified full 54-run result set.

### 2.6 Scope, prior exposure, and privacy limitations

Historical exploratory source-side optimizer selection used Samsung device data. Thus, although each later outer fold is logically device-disjoint, the nine-device study must **not** be presented as historically blind with respect to all modeling choices. This historical exposure is disclosed as a limitation.

The experiment implements logical federated clients on a centrally accessible research execution host. The design supports controlled comparison of federated aggregation procedures but does not provide a verified deployment-level privacy, secure aggregation or differential-privacy guarantee. Any recurrent-feature association is descriptive and cannot be interpreted as a causal intervention or identification of duplicated capture events. The work neither introduces a new mathematical fuzzy method nor claims priority for device-held-out N-BaIoT federated evaluation.

## 3. Results — WITHHELD PENDING GENUINE CONFIRMATORY EXECUTION

**No claim is currently authorised for this section.** As of the Chat 22 integrity review, the exact 54-run plan exists but **0/54** genuine outer-held-out confirmatory model fits or corresponding independent metric replays are evidenced. Previously reported exploratory source-validation accuracy is not a substitute. Fill this section only from all 54 authorised replayed runs and the frozen Stage 19 analyses. Report unfavourable results and operational failures.

**Required tables/figures after execution:** device × method balanced accuracy/FPR/recall; nine paired device differences and 95% paired bootstrap interval; class-support/estimability table; actual-training vs full-corpus recurrence by device/class; stratified recall/FPR with denominators; runtime and model-communication measures. The reported evidence should decide whether the data-centric evaluation produces a substantive new scientific inference beyond established N-BaIoT studies.

## Data and Code Availability — pre-submission placeholder

The underlying public dataset is available from the UCI Machine Learning Repository (DOI: 10.24432/C5RC8J) under CC BY 4.0. Research source code, frozen protocol and pre-result analysis definitions are in the draft research branch of `https://github.com/alifoxpro/AFRAS-FL`; the published version tag, immutable archive DOI and the availability/retention policy for the raw held-out predictions and potentially sensitive fingerprint sidecars are **not yet established**. No claim of public access to ungenerated outputs may be made. This paragraph requires factual update prior to journal submission.

## References (Harvard style)

Asiri, M., Khemakhem, M.A., Alhebshi, R.M., Alsulami, B.S. and Eassa, F.E. (2025) 'Decentralized federated learning for IoT malware detection at the multi-access edge: A two-tier, privacy-preserving design', *Future Internet*, 17(10), 475. https://doi.org/10.3390/fi17100475.

Li, T., Sahu, A.K., Zaheer, M., Sanjabi, M., Talwalkar, A. and Smith, V. (2020) 'Federated optimization in heterogeneous networks', *Proceedings of Machine Learning and Systems*, 2. Available at: https://proceedings.mlsys.org/paper_files/paper/2020/hash/1f5fe83998a09396ebe6477d9475ba0c-Abstract.html.

McMahan, H.B., Moore, E., Ramage, D., Hampson, S. and Agüera y Arcas, B. (2017) 'Communication-efficient learning of deep networks from decentralized data', *Proceedings of Machine Learning Research*, 54, pp. 1273–1282. Available at: https://proceedings.mlr.press/v54/mcmahan17a.html.

Meidan, Y., Bohadana, M., Mathov, Y., Mirsky, Y., Breitenbacher, D., Shabtai, A. and Elovici, Y. (2018) *Detection of IoT botnet attacks (N-BaIoT)* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5RC8J.

---

**Evidence provenance:** Internal frozen protocol `stage16_v2/FROZEN_CORE_PROTOCOL_V1_2026-10-24.json`; empirical source/native-support CI: `https://github.com/alifoxpro/AFRAS-FL/actions/runs/40130453516`; code `stage18_v2/lodo_engine.py`, `stage18_v2/replay_predictions.py`; pre-result analysis `stage19_v2/`. The manuscript uses outside literature only for dataset/baseline/prior-art context. It does not infer unobserved final performance.
