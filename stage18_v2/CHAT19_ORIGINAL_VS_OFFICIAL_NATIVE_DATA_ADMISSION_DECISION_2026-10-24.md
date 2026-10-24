# AFRAS-FL V2 — Chat 19: Evidence-Based Native Data Admission Decision

**24 October 2026 | Scientific execution handover | MDPI *AI* target**  
**Research branch:** `research/afras-v2-stage17-source-only-pilot-20261024` (Draft PR #1).  
**Decision:** **DATA PROVENANCE ENGINEERING ADVANCED; ORIGINAL HELDOUT CONFIRMATORY TESTING STILL BLOCKED, 0/54.** No genuine human review or approval has been issued.

## 1. Direct source evidence reviewed today

- The ChatGPT Library still lists all nine researcher-original N-BaIoT ZIPs, exact filename/byte-length metadata matching the historic nine-file manifest: **9/9 metadata matches, 1,773,532,530 total bytes**. These are *not* fresh SHA-256 over the original Library ZIP content.
- Materialization of the researcher's Ennio ZIP succeeded, but execution tools for reading the mounted bytes returned `ClientError`; an honest original Library **9/9 ZIP byte SHA-256 PASS was not obtained** in this Chat19 execution environment.
- An independent publisher-source GitHub Action [40096007454](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40096007454) successfully downloaded the original public UCI transport with the previously observed SHA `64929678b081d8e579a8d7c488cf11cc588403f282d5fb065b4156edbd55de9b`, decoded/reconstructed **all 25 CSV/RAR native members from nine devices**, and compared **23/23 previously recorded researcher-local original member hashes** with those new genuine downloaded UCI member-byte SHA-256s. The historical local member SHA set did not contain two Ennio members; those two have official-public member hashes but no corresponding independently rechecked local-member comparison in that 23/23 evidence.
- The nine ZIP outer wrappers rebuilt by the standard Python ZIP packaging logic matched **0/9 of the historical user original ZIP wrapper SHA hashes**. This does **not** imply a difference in native CSV/RAR member contents. It does imply the repackaged wrappers must not be mislabeled as fresh SHA checks of the original researcher Library ZIPs.
- GitHub PR #1 is open and **DRAFT**, with **zero submitted human review records**; historical source-only eight-client training feasibility evidence remains a *nonconfirmatory* preflight and never counts as LODO target outcomes.

## 2. Substantive new alternative source-admission route (NOT automatically adopted)

Previously, Stage18 could only admit the researcher's exact nine local outer ZIP wrapper SHA-256s, unavailable for fresh local hashing in this container. Chat19 generated a second *candidate* dataset route using **the 25 original native members from the public UCI transport**:

- `stage18_v2/compare_official_uci_nine_original_archives.py` now produces `PUBLISHER_UCI_NINE_REPACKAGED_ZIPS_CANDIDATE_MANIFEST__NOT_AUTHORIZED.json` with the measured SHA-256 and byte size of **each of the nine reconstructed source ZIPs**.
- [GitHub Action 40096007454](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40096007454) independently rehashed 9/9 of those **publisher-repackaged candidate wrappers** and recorded original-public 25 native member identities. Its artifact includes the original transport/member receipt, **an explicitly unapproved nine-device candidate manifest**, and 9/9 new-wrapper SHA receipt. The 23/23 historical local-inner-member crosscheck also passes.
- `stage18_v2/verify_original_nine_zip_bytes.py` now **distinguishes candidate repackaged-UCI ZIP byte matches from researcher-original ZIP byte matches** in its receipt status. Mixing the two provenance claims is prohibited. [Stage18 QA 40096080927](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40096080927) **33/33 synthetic tests PASS**, including the new false-original-provenance regression.
- This is a scientific data-admission **OPTION**, not silently a change to the frozen protocol or user data. The 115 numeric feature columns/11 original class labels originate from the same actual public UCI corpus; the source ZIP transport wrappers have been newly constructed. The qualified responsible researcher must explicitly decide whether this content-equivalent publisher-native source provenance is admissible for the intended study, document the transport difference, and bind the exact **candidate manifest SHA** to any private scientific execution authorization. If not accepted, use the actual researcher's nine original ZIP files on the execution machine and verify their exact old wrapper hashes.

**Scientific integrity warning:** The published 25 source-member byte count alone does not authenticate a human scientific review; the two Ennio historic-original member comparisons remain unverified in this latest crosscheck. The normal `plan_and_run_54.py --execute` engine still fails closed without the exact approved SHA-bound `source_manifest_sha256` and human review receipt.

## 3. Corrected final 13-SHA researcher review packet

The previous review README listed too few hash fields, omitting the three Stage19 preregistered analyses. Corrected `stage18_v2/README.md` and regenerated the current exact-version review packet [GitHub Actions run 40096091665](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40096091665), **PASS**:

- **13 of 13** actual frozen protocol, loader, engine, replay, orchestration, inventory, requirements, original-source admission scanner, original manifest and Stage19 analytical file-byte SHA values reconcile with the deterministic current `54`-task plan.
- The packet explicitly documents `authorized:false`, `human_review_complete:false`, `independent_data_admission_complete:false`, `0/54` real target-score executions. Neither the review packet nor the publisher provenance artifact is itself scientific authorization.
- Note that the 13-hash packet presently includes the historical **researcher-original manifest**. Any researcher-approved switch to the **publisher-repackaged candidate manifest** necessarily creates a **new version-specific 13-hash plan and approval**, not an invisible substitution.

## 4. Two genuine source-admission choices (researcher decision required)

| Data route | Current underlying evidence | Necessary pre-test requirement |
|---|---|---|
| **A — Original researcher Library ZIPs** | Exact filename and size 9/9; historical user-local wrapper SHA list, direct recent actual-byte hash unavailable | Copy all nine byte-identical originals to the secured execution computer and obtain a genuine 9/9 SHA receipt with `verify_original_nine_zip_bytes.py` or PowerShell before responsible-human scientific review authorization |
| **B — Original publisher UCI native member bytes rewrapped into nine ZIPs** | Public UCI transport SHA matches historical observed transport; 25 native members reconstituted/hashed, 23 historical local member comparisons match, 9/9 *newly repackaged wrapper* hashes verified; 0/9 old wrapper hashes match | Responsible researcher explicitly and prospectively accepts a documented publisher-native-wrapper substitution, reviews the provenance discrepancy and real-code release, supplies the exact candidate SHA manifest in the approved receipt; source archives themselves are reconstructed using the code-identified original public transport |

Both routes retain the **same core modeling protocol** only if the original native member contents, class support and feature order are independently validated. An approval of route B cannot be claimed to be an approval of route A.

## 5. Final explicit gate ledger

| Stage | Current status |
|---|---|
| 13 — Historical original dataset source | LIMITED PASS: 23/23 new vs old member comparisons, public 25 source members, 9/9 Library basename/size |
| 13 — Fresh user original nine outer-ZIP raw-byte SHA | **NOT COMPLETE**; candidate publisher wrapper route independently SHA-verified but **not approved** |
| 15 — Novelty | CONDITIONAL GO only for the narrow exposure-aware original-prevalence evaluation; N-BaIoT FL LODO was published in 2025 |
| 16 — Original 9×2×3 learning protocol | FROZEN, `full_execution_authorized:false` unchanged |
| 17 — Original 8-source FL preflight | PASS within nonconfirmatory-source-only limits |
| 18 — Source code verification | 33/33 Python software QA PASS; current 13-SHA/54-task plan PASS |
| 18 — Responsible human scientific/code review | **NOT COMPLETE**, zero review submissions |
| 18 — Genuine target inference | **0/54**, **BLOCKED** |
| 19 — Device-paired statistics / three-way recurrence scripts | Source-code implementation pre-result QA PASS; **real-data analysis NOT COMPLETE** |
| 20 — MDPI *AI* article submission | **NO-GO** — neither empirical native test outcomes nor a demonstrated original contribution exists |

**No change to original Stage16 hyperparameters, 30k samples/device, nine devices, 5 rounds × 3 epochs, AdamW, three seeds, source-only preprocessing, fixed threshold, or chosen baseline methods.** No true target predictions, model selection or statistical outcome estimates were generated here.

## 6. Critical next execution action — not more synthetic tests

The accountable human researcher must make exactly one of the two source-provenance decisions above, re-verify it on the execution machine, and genuinely sign off the scientifically reviewed exact code/data manifest hash. After that and only after that, execute the **frozen original 54 real N-BaIoT LODO runs** through `stage18_v2/plan_and_run_54.py --execute` with full raw heldout target predictions, checkpoint/sample evidence, and independent per-run replay. Preserve all failures/negative outcomes; then run the locked nine-device paired and source-exposure analyses before revisiting the publication decision.

**Publication caution:** This is a data-centric measurement proposal, not a novel fuzzy FL algorithm or a claim that exact numerical feature equality represents a duplicated captured network packet. The internal responsible-human signoff is a project integrity gate, not a universal journal requirement for public-data studies.
