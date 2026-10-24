# AFRAS-FL V2 — Stage-13 Raw-Source Admission Delta (Chat 7)

**24 October 2026 — Original public UCI byte identity verified, residual metadata correction documented.**

The prior Chat-6 execution rehashed all nine locally uploaded device ZIP wrappers against recorded local-manifest digests, independently inspected the 23 native source member streams in eight devices and matched their SHA-256 against streams from a directly downloaded public UCI archive. Chat-7 downloaded the same original public UCI archive again (outer ZIP SHA-256 `64929678b081d8e579a8d7c488cf11cc588403f282d5fb065b4156edbd55de9b`) and specifically checked two Ennio original members:

| Original Ennio native member | Byte size | Direct UCI member SHA-256 vs local original |
|---|---:|---|
| `Ennio_Doorbell/benign_traffic.csv` | 37,135,498 | `75cc608d3196950ad1cb14fc050babb96098128106b55ed84226e3ea97dba821` — MATCH |
| `Ennio_Doorbell/gafgyt_attacks.rar` | 52,525,066 | `2ded0dca827f13a921bf5b36f3b257ed65c83d60095cc7c78ecdbcf343f2b7ba` — MATCH |

**Cumulative reproducible source member byte matching: 25/25 PASS** (9 benign CSV and 16 original attack RAR files over nine N-BaIoT devices). See GitHub Actions [run 40057763038](https://github.com/alifoxpro/AFRAS-FL/actions/runs/40057763038) and the corresponding checksum-only receipt.

All 9 benign CSV **true original byte** SHA-256 digests were computed in Chat 6 and nine are now reference-matched to public UCI member bytes. The earlier Stage13 SQLite `completed.csv_sha256` field contains a **header digest** rather than a CSV-byte digest for 9 benign files. `AFRAS_V2_CHAT7_STAGE13_CORRECTED_SHA256_SUPERSESSION.json` declares the exact corrected digests as a versioned sidecar overriding the invalid prior claims, without rewriting the original SQLite database.

**What can now be asserted:** Original native member content matches the current directly downloaded UCI public archive, and source row class names follow their original native paths. **What must not be asserted:** independently verified true network-event identity, source path attack impact ground truth, zero hash collision mathematically, or corrected SQLite fields if the migration is not applied. Source provenance is substantially admitted **with an explicit SQLite metadata exception**; final publication data/code package must include sidecar and either repair or exclude the old broken field.