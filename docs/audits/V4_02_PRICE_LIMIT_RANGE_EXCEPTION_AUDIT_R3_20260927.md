# V4-02 Price Limit Range Exception Audit R3

## Scope

本审计独立跟踪 Required Scope 中 `CLOSE_OUTSIDE_LIMIT_RANGE` 工程异常，不随 V4-02 最终验收隐式关闭。输入为 R1 价格限制结果与 R3 重新计算的价格限制结果；范围为 2023-07-04 至 2026-09-24。

## Evidence and current result

- R1 audit: 23 rows.
- R3: 15 R1 rows were resolved after the dated alias and CHINEXT board repair for the continuing 300114/302132 identity.
- R1: 8 rows still appear outside their applicable range after R3 recomputation.
- R3: 53 current rows have `CLOSE_OUTSIDE_LIMIT_RANGE`; 8 overlap the remaining R1 rows and 45 are additional row/date findings.
- Current price artifact and per-row evidence references are recorded in [V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3.json](../../reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3.json).
- The official 302132 implementation announcement is captured at `data/v4/source_evidence/v4_02_r3/szse_2025_028_code_change_302132.pdf` and fixes the new symbol effective date at 2025-02-17.

The larger R3 count follows restoration of a previous-close reference across suspension/no-trade sessions. R1 had left many resume-day states unknown because the prior actual bar was not on the immediately preceding market session. Once those states became computable, more price-range findings surfaced. No inference is made that each finding represents an exchange-rule violation.

## Required disposition

Each row must be assigned one evidence-backed disposition: `RESOLVED_IDENTITY_BOARD`, `RESOLVED_ALIAS_INTERVAL`, `RESOLVED_LISTING_PHASE`, `RESOLVED_CORPORATE_ACTION_REFERENCE`, `RESOLVED_RULE_SELECTION`, or `OBJECTIVELY_UNRESOLVED_FAIL_CLOSED`. The last disposition requires a documented review showing credible official evidence is objectively unavailable, plus the exact fail-closed unknown reason.

Current R3 findings remain open because this pack does not bind row-specific official evidence sufficient to resolve their cause. They stay `UNKNOWN` with `CLOSE_OUTSIDE_LIMIT_RANGE`, and the final stage gate remains BLOCKED. V4-03 remains BLOCKED. A future closure must update this audit and pass the final gate that rejects open engineering exceptions.

## Stage contract, acceptance, next stage

- Stage contract: investigate and disposition each range exception independently from the final stage gate.
- Evidence: R1 and R3 price-limit artifacts, R1 audit, dated R7 identity repair, and official 302132 implementation capture.
- Acceptance: **BLOCKED**; 15/23 R1 rows resolved, 8 R1 rows remain open, 53 R3 rows require current disposition.
- Next stage: bind row-specific official identity, listing phase, corporate-action reference, or applicable rule evidence for every current finding; rerun independent postcheck before any accepted-head promotion.
