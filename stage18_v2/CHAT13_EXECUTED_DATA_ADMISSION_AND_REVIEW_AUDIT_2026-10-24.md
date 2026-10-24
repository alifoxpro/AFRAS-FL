# AFRAS-FL V2 — Chat 13: Stage 18 Original Data Admission / Responsible Review Gate

**Execution date:** 24 October 2026  
**Target:** MDPI *AI*  
**Research branch:** `research/afras-v2-stage17-source-only-pilot-20261024`  
**Scientific decision:** **NO-GO for original held-out target evaluation until actual all-nine-byte evidence and responsible-human review are obtained.**

## 1. What was directly and independently verified in Chat 13

- The ChatGPT Library **currently lists each of the nine original N-BaIoT device ZIP files**. Independently compared the Library entries by **exact canonical basename and byte size** against `stage18_v2/ORIGINAL_NINE_LOCAL_ZIP_HASH_MANIFEST_2026-10-24.json`: **9/9 name-and-length metadata MATCH**, total expected **1,773,532,530 bytes**.
- **This metadata comparison did not recompute present ZIP SHA-256 bytes.** One 62,909,588-byte Ennio archive was materialized to the execution sandbox, but the Python and container runtimes repeatedly returned execution errors. Never infer a fresh 9/9 byte gate PASS from current Library metadata.
- GitHub [Stage18 Python QA run 40089105731](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40089105731): **31/31 actual Python fixture checks PASS** against current engine/replay/admission logic, including fail-closed original-ZIP admission software checks. They are not real nine-original-byte admissions.
- **New genuine Windows PowerShell 5.1+/7 original-ZIP byte scanner:** `stage18_v2/verify_original_nine_zip_bytes_windows.ps1`. It uses built-in `Get-FileHash -Algorithm SHA256`, validates all nine canonical device filenames, SHA and byte lengths against the prior-audited manifest; fails on a mismatch and emits **no PASS receipt** unless all nine actual provided files agree. This is separate corroborating evidence for the existing Python admission scanner and does not generate test predictions, model parameters or scientific approval.
- [Windows workflow 40089124494](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40089124494): **PASS**, executing the PowerShell scanner on **nine small synthetic source-file fixtures**, then intentionally corrupting one and verifying that admission refuses it and produces no receipt. Synthetic PASS must not be relabeled as authentic source admission. Earlier workflow iterations failed on negative-path CI exit-code handling; the corrected final workflow succeeded.
- [GitHub PR #1](https://github.com/alifoxpro/AFRAS-FL/pull/1) is still **DRAFT**, with **zero submitted human PR reviews** during the latest check. No responsible-human scientific approval or valid SHA-bound authorization receipt has been supplied in the research context.

## 2. The one concrete operator data check now ready without a Python installation

On a Windows research computer with the same nine **original ZIP bytes** arranged in a directory, from the repository root, run:

```powershell
powershell -NoProfile -File .\stage18_v2\verify_original_nine_zip_bytes_windows.ps1 -SourceRoot "D:\AFRAS\nine_original_zip_files" -Manifest ".\stage18_v2\ORIGINAL_NINE_LOCAL_ZIP_HASH_MANIFEST_2026-10-24.json" -Receipt "D:\AFRAS\evidence\original_nine_zip_sha256_receipt.json"
```

Use the true directory containing the original nine files. A receipt is valid only if **all nine original ZIPs were actually opened byte-for-byte**, the scanner reports 9/9 SHA matches, and the emitted JSON has `original_zips_verified: 9` and `human_scientific_approval_created: false`. It matches the *previous original-local auditor hashes* rather than an independent publisher-declared authoritative outer-ZIP checksum; public inner-file identities were separately compared in Stage13 audits.

The **research's authoritative pre-execution byte gate is still inside** `plan_and_run_54.py --execute`, which runs `verify_original_nine_zip_bytes.py` before loading the first source/target data and checks the human-approved manifest. The Windows receipt is corroborating evidence useful for the reviewer, not a bypass.

## 3. Human scientific approval remains separate, not automatable by this assistant

The reviewer must genuinely inspect the exact current code and research claims, verify original data admission, target fold isolation and historical Samsung exploration disclosure, and issue an explicit private review record against exact code/data SHA hashes. The repository's `NOT_AUTHORIZED_HUMAN_REVIEW_TEMPLATE.json` remains `authorized: false`, and no artificial signature, reviewer identity, or `authorized: true` file was created.

At the time of this report:
- Stage 13 previously established 25/25 original UCI inner-member-byte matches; present nine original **outer-ZIP** byte gate in this execution environment is **UNVERIFIED**.
- Stage 15: **CONDITIONAL novelty**, algorithmic-firstness **NO-GO**.
- Stage 16: frozen 9-fold × 2-method × 3-seed settings preserved.
- Stage 17: real eight-source-only FL and full source-training budgets were verified in previous GitHub workflows, not final target results.
- Stage 18: **54/54 jobs deterministically planned; 0/54 confirmatory held-out runs executed; human signoff PENDING**.
- Stages 19 and 20: no final device-clustered outcomes or MDPI AI submission-ready claim.

**Next binding evidence:** (i) actual original-nine-byte 9/9 receipt from the secured research execution machine, and (ii) a qualified responsible-human review/approval of the exact SHA-bound Stage18 release. Only after these can the locked 54-run supervised FL target evaluation begin. Do not cherry-pick folds, seeds, thresholds or trial results to justify paper novelty.
