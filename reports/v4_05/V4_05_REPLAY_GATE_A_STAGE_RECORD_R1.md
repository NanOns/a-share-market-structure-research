# V4-05 Replay Gate A stage record R1

Date: 2026-09-29. Implementation commit: `30b0de6485c6b590bffd11fabcbd99cfd4af1fd3`. Frozen entry commit: `78f9f59`. Accepted V4-04 promotion commit: `6aa0bdd`.

## Governing contract

`docs/evidence/V4_04_ACCEPTED_HEAD_PROMOTION_AND_V4_05_REPLAY_GATE_A_ENTRY_TASK_R1_20260929.md` governs this stage. The V4-04 external acceptance is in `docs/evidence/V4_04_FINAL_EXTERNAL_ACCEPTANCE_R1_20260929.md`. The frozen source and sample contract is `V4_05_REPLAY_DATE_MATRIX_R1.json`. The audit is `V4_05_REPLAY_GATE_A_AUDIT_R1.json`.

## Evidence and result

G01 passed accepted TDX archive and input hash verification. G02 passed a bounded accepted-universe check for the four required boards and a later-listing boundary. Neither sampled result certifies all historical replay.

G03 blocked. All 4,026,611 rows of the accepted V4-02 daily parquet have `knowledge_lineage=DIAGNOSTIC_NON_PIT_CURRENT_METADATA_SNAPSHOT`. The V4-02 acceptance explicitly records this lineage, and its PIT stage receipt records `AS_RECORDED_CONSUMED_SOURCE_HISTORY_UNAVAILABLE`. A historical target T cannot establish when the adjustment metadata became available. Using these qfq coordinates as AS_RECORDED would risk future corporate-action knowledge. This is a V4-05 capability blocker; it does not retroactively change V4-02's accepted narrower contract.

Result: `V4_05_BLOCKED_UPSTREAM_DEFECT_HISTORICAL_ADJUSTED_PRICE_PIT_LINEAGE`. Capability `HISTORICAL_ADJUSTED_PRICE` is blocked. `STOCK_CORE`, `MARKET_REFERENCE`, `MARKET_REGIME`, `WEEKLY_PERIOD`, and `MONTHLY_PERIOD` historical replay remain blocked pending their gates. G04–G08 and temporal-negative business replay were not run after the G03 stop condition. `DATA_FACTOR_REPLAY_PASS` is false. Independent postcheck passed the accepted hash chain, row count/lineage, and truthful downstream halt.

## Separate audit item and next stage

Audit item `V4_05_AUDIT_HISTORICAL_ADJUSTED_PRICE_PIT_LINEAGE_R1` covers accepted V4-02 daily adjustment availability, all historical dates and entities, and the AS_RECORDED capability. Repair acceptance requires a versioned historical first-availability source/contract, no use of post-T metadata, exact accepted input identities, and independent replay/postcheck across frozen dates. The predecessor contract must be repaired and accepted separately before a new V4-05 replay gate run. No V4-06+ stage is promoted. V4-08 historical Sector PIT stays separately blocked.
