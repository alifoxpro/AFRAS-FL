# AFRAS-FL V2 — Chat 18 Real Data Provenance Execution and Research Gate Decision

**Date:** 24 October 2026  
**Target:** MDPI *AI*  
**Working branch:** `research/afras-v2-stage17-source-only-pilot-20261024` (Draft PR #1)  
**Final decision:** **REAL DATA-PROVENANCE PARTIAL PASS; HUMAN AUTHORIZATION NOT RECEIVED; ORIGINAL HELDOUT 0/54 — NO-GO.**

## 1. True original-byte provenance added, not just tests

During Chat18, the research agent downloaded the official UCI N-BaIoT 1.7GB transport on a GitHub Actions runner, recomputed its actual SHA-256 and **extracted and hashed all 25 original native CSV/RAR device-member bytes** across nine original N-BaIoT devices. The independently fetched official transport SHA was:

```text
64929678b081d8e579a8d7c488cf11cc588403f282d5fb065b4156edbd55de9b
```

This matches the previously observed study-specific official transport SHA; **this is NOT asserted to be an official publisher-signed checksum**. GitHub Actions [run 40094660919](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40094660919) **PASS**: nine devices, **25 native members independently read and hashed**, and zero model/heldout target predictions. Receipt artifact: `afras-chat18-uci-25-native-member-rebuild-versus-original-nine-zip-audit`.

**Significant and honest discrepancy:** Independently **reconstructed outer ZIP wrappers** produced by the Stage17 packaging procedure matched **0/9 historical user-local outer ZIP SHA-256 values**. ZIP wrapper bytes depend on compression/header/packaging, not just identical inner file contents. This result therefore **does not prove that the current nine user Library ZIP bytes are wrong**; it means the reconstructed public wrappers must **NOT** be substituted for the original nine SHA-bound user archive files or classified as fresh local 9/9 admission.

## 2. Prior user-local native bytes independently matched to official UCI

The user's Library `AFRAS_V2_CHAT6_SOURCE_INTEGRITY_RECONCILIATION.json` supplied original local `member_comparisons` for **23** native CSV/RAR members across eight devices, each including original local SHA-256, full member byte count and earlier official comparison. The two original Ennio Doorbell native members **were absent** from that *particular* 23-member comparison.

Recovered these exact 23 previously recorded user-local digest/size pairs, without inventing entries, in `stage18_v2/HISTORICAL_LOCAL_ORIGINAL_23_MEMBER_SHA256_CHAT6.json`. Independent GitHub Actions [run 40095070517](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40095070517) **PASS**: downloaded the genuine 25-member byte-receipt artifact from the independently successful public original UCI run and matched all **23/23** historic user-original native member SHA-256 and byte sizes to these newly computed official public-source digests. It explicitly reported the two Ennio member **local comparison SHA values unavailable** in this prior record. Its evidence artifact is `afras-v2-chat18-23-local-vs-25-official-byte-provenance-evidence`.

This 23/23 validation is a **substantive real-data identity cross-check**, not synthetic CI. But it is not fresh local 9/9 outer ZIP hashing, not an independent review of the two missing Ennio local member hashes, and not FL effectiveness evidence.

## 3. The current exact nine Library ZIP bytes remain unverified this turn

The File Library lists each original archive with its canonical filename and recorded byte size (sum **1,773,532,530 bytes**), all **9/9 metadata matches**. One Ennio user-Library ZIP was successfully materialized into the model workspace at `/mnt/data/afras_chat18_originals/Ennio_Doorbell.zip`. However, model-side Python and container execution returned `ClientError`, so **actual SHA-256 of the current original user-Library ZIP bytes could not be computed**. Fresh execution-machine original outer ZIP admission remains **NOT COMPLETE**.

Run the already-implemented `stage18_v2/verify_original_nine_zip_bytes_windows.ps1` or `verify_original_nine_zip_bytes.py` against the **same exact nine original research ZIPs** intended for the 54 runs, and preserve the generated unmodified byte-by-byte admission receipt. Do not use newly wrapped public UCI files in place of original local archives without establishing a new reviewed data manifest.

## 4. Research authorization and actual inference remain unperformed

GitHub [Draft PR #1](https://github.com/alifoxpro/AFRAS-FL/pull/1) had **zero submitted human reviews** when checked during Chat18. The committed `NOT_AUTHORIZED_HUMAN_REVIEW_TEMPLATE.json` deliberately has `authorized:false`. No AI-created signature, `approved_by`, or artificial human review was used.

The original frozen 9 heldout devices × FedAvg/FedProx × three seeds = **54** experiments remain **planned 54/54, executed 0/54**. The original Stage16 core, 30k original training samples/source device, 5 communication rounds, 3 local epochs, optimizer, random seeds and fixed 0.5 classification threshold were NOT changed. The true source-only eight-client pilot and synthetic Stage18/19 software QA remain qualified feasibility evidence, not genuine native target scores.

The human-scientific signoff is an **internal self-imposed study integrity gate**, not a claim that MDPI requires independent supervisory preapproval of every experiment on public data. A genuinely accountable researcher's review is required because **this research workflow itself** froze and enforced such a process. The agent must not impersonate them.

## 5. Status table

| Stage | Chat18 evidence-based status |
|---|---|
| 13 — Original native source provenance | Fresh official UCI 25/25 **member extraction/hash PASS**; 23/23 of historical user-local member SHA values independently matched freshly downloaded official bytes; two Ennio historic member comparisons absent; **original current 9/9 outer ZIP-byte admission NOT COMPLETE** |
| 15 — Originality of data-centric FL study | **CONDITIONAL**; no novel fuzzy FL algorithm or first N-BaIoT nine-fold LODO claim |
| 16 — Locked protocol | **FROZEN**; original code+data SHA plan maintained |
| 17 — Full-budget eight-source FL feasibility | **PASS with source-only limitations** |
| 18 — Engine, replay and 54 task schedule | **Software QA PASS**; 54 planned |
| 18 — Responsible-human science review | **PENDING**, zero submitted GitHub reviews |
| 18 — Original nine outer-target fold inference | **0/54 — BLOCKED** |
| 19 — Device-paired and exact-feature exposure statistical implementations | **Software/synthetic tests PASS, NO GENUINE TEST ESTIMATES** |
| 20 — MDPI AI manuscript and submission | **NO-GO** |

## 6. Minimum critical path, with no unnecessary code added

1. On an actual workstation containing **all nine original user ZIP files**, use the committed SHA-256 scanner to create a real local **9/9 original outer ZIP admission** receipt. The current public UCI 0/9 reconstructed wrapper digest matches cannot replace this.
2. Obtain a real qualified responsible-researcher/supervisor review or explicit accountable decision on the *exact current SHA-bound Stage16/18/19 release*. Record both acceptance of scientific limitations (including previously explored Samsung source validation) and actual original-data admission; issue the locally held approval receipt only after real authorization.
3. Then (and only then) execute the frozen 54 native FL runs with all original target rows, retain immutable raw predictions/checkpoints/source bank and independent replay receipts, and evaluate the three preregistered Stage19 nested exposure strata plus nine-device paired statistics. Retain negative and non-estimable results.
4. Only if a defensible empirical novelty claim survives the literature comparison, prepare the English MDPI *AI* manuscript with reproducibility and transparent limitations.

**No human approval or original native heldout BA/FPR was generated in Chat18.**
