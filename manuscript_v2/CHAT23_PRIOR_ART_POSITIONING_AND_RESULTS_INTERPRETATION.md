# AFRAS-FL V2 — Chat 23: Evidence-Based Prior-Art Positioning and Results Interpretation Lock

**Document class:** manuscript-ready text for incorporation into a later journal submission; no empirical performance results. **As-of evidence:** 25 October 2026 scientific review; GitHub draft PR #1, `5275de3a98a9254b36ffbc1e99e1ba93e676fbc4` before this text-only commit. **No change** to Stage 16 frozen model/data plan or any Stage 18/19 analytical code. The source-validated Route B plan remains **54 planned / 0 confirmed executed**; accountable human approval has not been furnished in the inspected evidence.

**Citation convention:** Harvard author–date for drafting, at researcher's request. Convert to the journal's current numeric MDPI style and template before actual submission. No citations should be inferred from unreviewed source-code comments alone.

## 1.2. Prior work and precise scientific gap (manuscript section)

Device heterogeneity and covariate shift are persistent challenges for intrusion detection trained on Internet of Things (IoT) traffic. The N-BaIoT dataset provides labelled benign and botnet-attack traffic-derived records for nine commercial IoT devices, allowing experiments that are partitioned according to device rather than according to randomly assigned traffic rows (Meidan et al., 2018). However, a device-disjoint partition constrains the *originating device identifier* and does not, by itself, establish that every held-out numerical observation has a previously unseen feature representation.

The federated-learning literature establishes both iterative model averaging and proximal regularization as well-studied optimization strategies. FedAvg combines updates obtained through local client optimization (McMahan et al., 2017), while FedProx adds a proximity term to local objectives with the aim of improving learning under heterogeneous client settings (Li et al., 2020). Consequently, an isolated FedAvg–FedProx comparison, even if experimentally complete, cannot support a claim of a newly introduced federated optimization method.

Prior IoT-malware detection research has already reported N-BaIoT experiments in which each of the nine devices is held out in turn during federated evaluation. Asiri et al. (2025), for example, evaluated a decentralized, two-tier privacy-preserving IoT malware-detection architecture under known-device and leave-one-device-out regimes. Their architecture, unsupervised anomaly detector and privacy/security components differ materially from the present study's centralized research simulation and supervised binary multilayer perceptron. Nevertheless, the existence of that study rules out claims that nine-device N-BaIoT leave-one-device-out federated evaluation is itself unprecedented.

Recent dataset-centric work also complicates originality claims framed solely around generalization, client heterogeneity or algorithm comparison. Bilal et al. (2026) evaluated FedAvg, FedProx and FedNova under in-domain, cross-dataset and joint-data settings using different IoT/IIoT datasets, highlighting that the particular evaluation regime has substantial consequences for claims of transfer. That design investigates cross-dataset rather than the present study's canonical-feature recurrence between N-BaIoT device partitions. Yue, Lu and Xie (2026), by contrast, studied calibrated evidence and attack-family holdout for N-BaIoT and IoT-23. Withholding an attack *family* differs from withholding a device that may share attack classes and repeated feature representations with the training pool. Their work cautions against equating high native-data discrimination with generalization to genuinely unseen malware families.

Against this background, the present study poses a deliberately narrower question: **When a complete IoT device is held out from federated training, to what extent are exact numerical feature vectors from that device (i) present somewhere in the other eight complete source-device datasets, (ii) present in the exact seed-dependent observations selected for training, or (iii) absent from the other eight devices altogether; and how do device-held-out detection outcomes vary descriptively across those classes of source availability?** The distinction between source-corpus availability and actual model-visible training membership is particularly important because the preregistered study samples only 30,000 rows from each source device rather than all accessible source observations.

The contribution is consequently **a proposed evaluation and measurement framework**, not an original fuzzy-logic algorithm, a claim of differential privacy or a demonstration that repeated feature vectors correspond to identical captured packets. Whether its empirical findings constitute a sufficiently substantive advance over prior evaluations remains an open question until the 54 prespecified native-data experiments and corresponding independent analyses have been completed.

## 4. Discussion — evidence-dependent interpretation guide (NOT substantive findings)

The complete manuscript's Discussion must be written **only after** the authorised original-prevalence predictions, independent replay and frozen Stage 19 analyses exist. The following points define permissible interpretation without preselecting a favourable outcome:

1. **If** a high share of target feature vectors is available elsewhere in the full source corpus but a smaller share is found among the true 240,000 training-source rows, the discrepancy would demonstrate why corpus-level recurrence cannot be described as model training exposure. It would **not** quantify memorisation, nor would it prove original captured events were shared across devices.
2. **If** attack recall differs across exposed/unexposed strata within supported attack class and held-out device, the differences are observational; source distribution, attack subtype and device identity may confound them. Explain supports and missing cells, with no causal claim that training exposure produced a specific gain.
3. **If** FedProx and FedAvg differ on the preselected device-level balanced-accuracy contrast, report both signed effect size and full device heterogeneity. Sign-flip inference rests on paired-sign symmetry under the null; with nine target devices, a bootstrap confidence interval and nominal significance cannot eliminate uncertainty, historical model-selection exposure or multiplicity in secondary exploratory comparisons.
4. **If** the two methods are statistically indistinguishable or perform poorly on specific held-out devices, report this evidence and explore whether fixed training budget, heterogeneous class composition, source-sample sparsity or model undercapacity offer *plausible* explanations. Such explanations are hypotheses, not established causal mechanisms; do not re-tune the frozen experiment with knowledge of the held-out results.
5. **If** the exact-feature membership contrasts have too few within-class observations to estimate robust differences, classify them as NON_ESTIMABLE, even if such an outcome weakens the novelty claim.
6. A reliable secondary analysis must separate device holdout, attack-family holdout and cross-dataset testing. The frozen nine-device analysis contains no independent novel-family or external-dataset claim. Any subsequent additional dataset or post-test model setting must be explicitly labelled exploratory rather than retrospectively preregistered.
7. The earlier exploratory use of Samsung device data for optimizer/model feasibility must be disclosed. The final nine-fold scheme is *algorithmically device held-out*, but it cannot be portrayed as nine historically untouched prospective lockboxes. The centrally orchestrated client simulation is not direct evidence of real deployment confidentiality, secured aggregation or on-device data isolation.

## 3. Results — structured extraction schema, not fabricated measurements

The following output tables are the only publication-ready quantitative shells until authorised native execution occurs. **All metric cells are intentionally empty; do not interpret empty as zero.**

**Table R1. Complete native device outcome matrix:** 9 devices × 2 methods, each a mean over the original 3 seeds. Report original held-out test rows, original benign support, attack support, device-specific balanced accuracy, benign false-positive rate, attack recall, and min/max across seeds. Preserve device IDs and show per-seed values in a supplementary table.

**Table R2. Prespecified paired method comparison:** 9 device-level paired (FedProx minus FedAvg) balanced-accuracy differences; mean across nine devices; two-sided exhaustive 512-sign-flip p-value; fixed 10,000-resample paired-device percentile interval; the smallest individual-device result. State assumptions and sample size in caption.

**Table R3. Exact-feature availability versus actual training exposure:** All supported native device/class cells, three mutually exclusive membership strata, each original denominator and estimated native attack recall or benign false-positive rate. Label absent strata NON_ESTIMABLE, not zero, and retain the actual 30,000 rows/client source-sampling identities.

**Table R4. Research reproducibility evidence:** All 54 immutable task IDs, executable commit, 13 source SHA values, selected manifest digest, exact Python/PyTorch/NumPy/Pandas/rarfile/libarchive runtime, run checkpoint and raw prediction SHA values, source-bank membership receipts, independent replay results, failures and resource usage. Keep private sensitive source membership banks governed separately.

The final abstract, Discussion, Conclusion and the choice whether to submit to *AI* must be **conditional on the full results**, and no p-value, acceptance likelihood or prediction accuracy may be supplied before then.

## References (Harvard author–date; sources verified against publisher or repository records)

Asiri, M., Khemakhem, M.A., Alhebshi, R.M., Alsulami, B.S. and Eassa, F.E. (2025) 'Decentralized federated learning for IoT malware detection at the multi-access edge: A two-tier, privacy-preserving design', *Future Internet*, 17(10), article 475. https://doi.org/10.3390/fi17100475.

Bilal, M.A., Ul Islam, I., Idrees, S., Qasim, M., Khan, M.J. and Khan, J. (2026) 'Dataset-centric evaluation of federated intrusion detection models in IoT networks', *Scientific Reports*, 16, article 2683. https://doi.org/10.1038/s41598-025-32567-w.

Li, T., Sahu, A.K., Zaheer, M., Sanjabi, M., Talwalkar, A. and Smith, V. (2020) 'Federated optimization in heterogeneous networks', *Proceedings of Machine Learning and Systems*, 2. https://proceedings.mlsys.org/paper/2020/hash/1f5fe83998a09396ebe6477d9475ba0c-Abstract.html.

McMahan, H.B., Moore, E., Ramage, D., Hampson, S. and Agüera y Arcas, B. (2017) 'Communication-efficient learning of deep networks from decentralized data', *Proceedings of Machine Learning Research*, 54, pp. 1273–1282. https://proceedings.mlr.press/v54/mcmahan17a.html.

Meidan, Y., Bohadana, M., Mathov, Y., Mirsky, Y., Breitenbacher, D., Shabtai, A. and Elovici, Y. (2018) *Detection of IoT botnet attacks (N-BaIoT)* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5RC8J.

Yue, J., Lu, Y. and Xie, Y. (2026) 'Detecting unseen IoT attacks with calibrated dual evidence under low false-positive budget', *Entropy*, 28(9), article 1026. https://doi.org/10.3390/e28091026.

### Final scientific integrity and audit note

Author attribution, quantitative interpretation and final journal formatting require the accountable researcher. MDPI's current reference guide uses a numeric in-text referencing convention, even though this working manuscript is in Harvard style; convert only when finalising the actual MDPI-specific submission. This text is source-grounded academic drafting, **not independent evidence of new results**. Current immutable Route B technical verification: https://github.com/alifoxpro/AFRAS-FL/actions/runs/40130453516.
