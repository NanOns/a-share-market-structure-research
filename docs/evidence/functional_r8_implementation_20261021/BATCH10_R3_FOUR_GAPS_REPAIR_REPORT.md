# BATCH10-R3 Four-Gap Repair Report — R2 continuation

- Date: 2026-10-22 (Asia/Shanghai)
- Branch: `codex/v4-unified-development`
- Audited baseline: `5cfa4c5e9793538a640749d39cf50dbe39acc8c5`
- Pre-execution repository HEAD verified against origin: `29ce4d1d150fca80f14a5282139cb41fe0650b41`
- Result: **candidate repair passed for the requested historical chain; Lane L remains WAIT**.
- All generated candidate material is under `G:/codex_tmp/v4_daily_candidate_chain_20261020`; historical sources remain explicitly NON_PIT.

## Repairs and evidence

1. **10/19 ReadIndex and 10/20–10/21 succession.** Bound the 10/19 dated membership and native Identity authority into the R2 ReadIndex authority. The direct PG ReadIndex page and 28766 dated API return READY under the 10/21 snapshot context. The immutable successor chain now runs 10/20 `283fec0e…ab7562` → 10/21 `f8c09d96…686430`; 10/21 period oracle checked 637,268 values with zero differences.
2. **RPS5 delta3 and complete 5,226-object D0.** The 10/20 successor binds the exact R3 Core bytes (`123111b8…aa83`), all 5,226 unique identities and the matching 5,226 D0/prewatch objects. RPS5 validation has 5,202 exact, 24 unknown, and zero mismatches. D0 aggregates are TRUE 141 / FALSE 5,033 / UNKNOWN 52. R8 candidate publication, D0 PG publication, predicate digest, and 28766 exact-token context readback all passed. The 10/21 successor was rebuilt from the new predecessor and independently published/read back.
3. **Forward lanes.** Lane H is connected to the candidate chain and has 73,115 `RETROSPECTIVE_RESEARCH` rows in the isolated Forward PG namespace, with 28766 API and visible page readback. It remains NON_PIT. Lane L has no qualifying real first capture; UI and API continue to show `WAIT_REAL_FIRST_CAPTURE` / `WAIT_SOURCE_READY`. No synthetic sample was created. The historical live-capture failure remains `SOURCE_EXECUTION_FULL_OWNER_LIFECYCLE_CONSERVATION_FAILED`.
4. **Historical date context.** A read-only 21-check API matrix uses snapshot context token `f8c09d96…686430` (context date 10/21), while query dates and row dates are 10/19, 10/20, or 10/21 and dated Owner bindings resolve to the corresponding historical day. Context, stocks, sectors, focus, profile detail, daily/weekly/monthly charts, search, and pagination were checked. After changing to 10/21 and back, the same 10/20 list response was byte-identical (`7a7ce236…291b5c`), demonstrating no cross-date cache bleed in this read path.
5. **Visible UI.** On 28766, the 10/20 stock list, page 2, search `SH.688411`, stock detail, and D/W/M chart selectors loaded visibly. The daily/weekly/monthly series ended at 10/20; weekly/monthly final bars were explicitly marked `FORMING_AS_OF`. Forward history showed 73,115. No browser security warning was bypassed. The stock-list profile projection is 5,224; the separately published Core and D0 domains contain 5,226, and the two objects excluded from that profile projection are not represented as missing Core/D0 objects.

## Publication safety and test result

- R8 candidate receipts: 10/20 `283fec0e…ab7562`, 10/21 `f8c09d96…686430`; both candidate-only, PG readback matched, CAS rollback drill passed, `formal_head_modified=false`, `production_accepted=false`.
- D0 PG readback: 10/20 10,452 scenario facts and 5,226 predicate rows; 10/21 10,448 scenario facts and 5,224 predicate rows; both predicate digests passed.
- First 10/20 token attempt `695e1a…` aborted on missing ReadIndex response and rolled back. It is retained as an audit event; successful retry3 tokens are immutable successors.
- Regression suite: `52 passed` (`test_batch10_r3_successor_rebase.py`, `test_d0_owner_version_content_address_r2.py`, dated BFF/routes, and Lane L WAIT presentation).
- Runtime used only `127.0.0.1:28766` and `127.0.0.1:5432/market_research` (database OID 646711). `28765` was not listening or touched.
- No production Head or schedule was changed. The user-authorized operations were confined to development candidate publication and readback. No DROP/DELETE was issued.

Machine-readable API/PG/UI details are in `BATCH10_R3_FOUR_GAPS_REPAIR_EVIDENCE.json`; the live API matrix is embedded there as `api_matrix`.

## Remaining gated condition

Lane L remains `WAIT_REAL_FIRST_CAPTURE` until the actual source is READY and a real first capture passes full Owner lifecycle conservation. This WAIT is not a release failure for the completed historical candidate chain and must not be filled using retrospective Lane H data.
