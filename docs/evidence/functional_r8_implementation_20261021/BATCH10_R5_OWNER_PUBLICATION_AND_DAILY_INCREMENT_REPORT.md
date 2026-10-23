# BATCH10-R5 Owner Publication and Daily Increment Report

- Contract: `BATCH10_R5_OWNER_PUBLICATION_AND_DAILY_INCREMENT_R1`
- Date: 2026-10-23 (Asia/Shanghai)
- Branch: `codex/v4-unified-development`
- Audited starting HEAD and remote HEAD: `e5b499fc23faaf21a6c819d8f0bd18fa611952e6`
- Disposition: **PARTIAL — implementation and scoped evidence completed; publication and 10/22 increment gates remain closed**.

## S00 baseline and operation boundary

The latest applicable plan and source-repair contract were read before work: `V4_FUNCTIONAL_R8_REPAIR_PLAN_R2_FINAL_20261021.md` and `V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`. The applicable Phase 0 record is `DEGRADED_PASS`; this task did not start a constrained scanner. Candidate research remains NON_PIT. The current formal Head and production service were not changed.

At execution, the branch and `origin/codex/v4-unified-development` both resolved to the requested starting SHA. The existing service listened on `127.0.0.1:28766`, PostgreSQL on `127.0.0.1:5432` (`market_research`, OID `646711`, server `18.6`), and `28765` had no listener. Existing unrelated untracked `.githooks/`, `config_back/`, and `script_back/` paths were preserved.

## Gate results

| Work item | Status | Evidence and disposition | Next stage |
|---|---|---|---|
| P0-A exact 10/20 and 10/21 R8/D0/ReadIndex/Priority token publication | **FAIL / PARTIAL — exact-token gap only** | **The 10/21 date-level data is present and connected.** SourceIngress has a 10/21 receipt (5,568 rows, `CAPTURED_AFTER_CLOSE_NON_PIT`); 28766 serves the 10/21 Focus page (3,975 rows); ReadIndex is sealed for requested token `14ee0c…ad378`; and PG has 10/21 R8/D0 rows under other tokens. The gap is that R8/D0 rows for the specific task tokens `a5b169…70b70` (10/20) and `14ee0c…ad378` (10/21) were not found. 10/20 ReadIndex is also absent. Focus/stock/sector Priority Owner rows in `v4.owner_versions_priority_r1` extend through 10/15 (not 10/14). The R4 descriptors reference 20 Owner payload files per requested token; none is present in this checkout. That local absence prevents rebuilding the exact bound chain here, but does not mean 10/21 market data or all 10/21 candidate publications are absent from PG. Existing PG rows were preserved. | Reconcile the exact R4 candidate binding to its available dated source and Owner payloads, then publish/read back only the missing exact-token chain. Preserve the existing 10/21 data and other-token candidate rows. |
| P0-B lifecycle-only bar fact | **CODE_PASS; REAL_PG_TEMP_FIXTURE_PASS** | `conserve_lifecycle_status_rows` now binds bar presence to same-date/same-security RAW rows. Missing RAW does not erase lifecycle status and records `RAW_BAR_RECEIPT_NOT_FOUND_FOR_DATE_AND_SECURITY`; mismatched status/bar evidence marks `status_conflict`. Nine focused tests pass. A session-local PG fixture covered actual status with no bar, same-day same-security bar, wrong-day bar, suspended without bar, and suspended with a bar. Temporary tables were `ON COMMIT DROP`; no permanent schema or rows changed. This PG fixture is engineering evidence, not a live candidate-source sample. | Re-run the corrected projection and actual PG reader against the restored dated candidate source rows. |
| P0-C Focus Priority and Forward validation cohort | **CONTRACT_BLOCKED; WAIT_TRUE_FIRST_CAPTURE** | 28766 returned 3,975 dated Focus rows for 10/21. `/focus/priority` returned `NO_OPERATIONAL_FOCUS_SUBPAGE_OWNER`; `/forward` returned `NO_AUTHORIZED_COHORT_OWNER`. The current Focus authority and Priority contracts do not define a dated Focus ranking rule/producer, so no new ranking semantics were invented. Lane H history remains retrospective and is not used as a cohort or first capture. | Bind a versioned Focus Priority rule and dated Owner, then wire its PG reader/BFF/page. Keep Forward cohort waiting until a genuinely authorized first capture exists. |
| P0-D 10/22 real-source increment | **FAIL — source unavailable** | SourceIngress has no 10/22 receipt; its latest receipt is 10/21 and the captured package target folders end at 10/21. Read-only inspection of 11,884 configured `D:/new_tdx` daily files found latest last-record date 2026-10-08. No source capture, synthetic bar, or 10/22 Owner was created. | Acquire an authorized, complete 10/22 TDX source package with its actual source clock, then run the existing minimal SourceIngress and full candidate daily chain. |
| P1-E/F, D2 | **DEFERRED / CONTRACT_BLOCKED** | R6 date restriction, S02 source/performance work, and D2 frozen-level business-rule implementation remain for later as requested. No MA, prior-low, percentage, or alternative D2 level was selected. | Continue only under their respective contracts and business decisions. |

## Lifecycle code change

`conserve_lifecycle_status_rows` now accepts RAW rows and builds a dated identity receipt set. It rejects duplicate, empty, or wrong-date RAW receipts. For both existing status rows and lifecycle-only rows, `actual_bar_present` reflects whether that exact security has a RAW row on the target date. Lifecycle status remains visible when no bar exists; a claimed `ACTUAL_TRADED` without a matching RAW row receives an explicit missing-bar reason. When RAW presence and lifecycle status disagree, the projection preserves both facts and raises `status_conflict`.

Verification: `pytest -q tests/test_forward_lane_lifecycle_conservation.py` — **9 passed**; `git diff --check` passed before report/evidence generation. The live PG fixture readback is in `supporting/BATCH10_R5_LIFECYCLE_PG_TEMP_FIXTURE.json`.

## Page and database evidence

The visible 28766 route `/v4/research/focus` rendered under title `大 A · V4 研究工作台`, selected date 2026-10-21. This confirms the 10/21 date-level data was connected and served. The page showed the historical NON_PIT notice, 5,224 D0 rows, 99 TRUE / 5,125 UNKNOWN, 144 D0 Focus triggers, and 3,975 Focus rows with 3,975 D0 and D2 mappings. The page remained read-only. The `/api/v4/focus/priority` and `/api/v4/forward` routes returned the explicit missing-Owner states above. Response hashes and exact-token PG checks are recorded in `BATCH10_R5_OWNER_PUBLICATION_AND_DAILY_INCREMENT_EVIDENCE.json`. All DB inspection used a read-only transaction; the only PG write in this task was the scoped temporary-table fixture.

## Release and next work

This report records **partial execution**, not R8 completion, production acceptance, or authorization to advance a release gate. `28765`, formal Head, production scheduling, and historical NON_PIT classifications remain unchanged. The next useful stage is to make the exact R4 candidate payloads available in the checkout or authorized candidate storage and to freeze the Focus Priority rule. After those dependencies are restored, perform exact-token R8 → D0 → ReadIndex/Priority/Forward/Focus publication and restricted PG/28766 readback, then proceed with 10/22 only when its real source package is present.

### Clarification added 2026-10-23

The original gate summary was too easy to read as “10/21 data/publications do not exist.” That was not the finding. The confirmed state is: 10/21 data is in SourceIngress and served through 28766; several 10/21 R8/D0 candidate rows exist under other tokens; the requested 10/21 R8/D0 token is not among them, while its ReadIndex row does exist. The 10/20 date also has SourceIngress and other-token R8/D0 rows, but lacks the requested-token R8/D0 and ReadIndex rows. This distinction is represented explicitly in the evidence JSON.
