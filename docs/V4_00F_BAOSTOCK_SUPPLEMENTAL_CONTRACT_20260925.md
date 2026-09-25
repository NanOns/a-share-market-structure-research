# V4-00F BaoStock Supplemental Contract Stage Receipt (2026-09-25)

| Field | Record |
|---|---|
| stage | `V4-00F / BAOSTOCK_SUPPLEMENTAL_CONTRACT` |
| stage_contract | V4.2.2 REV2 §3A, §9.4–§9.7, §78, §87A: freeze BaoStock supplement fields/units, strict binding, bounded request policy, reusable receipt qualification, and non-blocking Core boundary. |
| consulted_upgrade | Latest REV2 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`; contract re-audit SHA-256 `8ae62a108262ddb63c42457c0920e0418b8df1013c26263edb3b3e34de8b4747`. |
| input_identity | HEAD `3ef5bf63455447dd605534dc4c1717eb238a86f5`; existing turnover algorithm `TURNOVER_CONTEXT_V1`; supplemental contract `BAOSTOCK_SUPPLEMENTAL_SOURCE_V1`. |
| execution_boundary | Contract/spec/evidence review only. No TDX data changed, no SDK installed, no BaoStock API called, no application implementation or database/head changed, no tests/scanner/history reconstruction run. New project documents/config written atomically outside TDX roots. |

## Evidence and contract

- REV2 requires at least 60 prior strict-bound actual sessions plus target date, prefers 250, caps lookback at 250 market sessions, allows skipping confirmed suspensions only, and degrades only turnover when history is insufficient.
- `BOUND_STRICT` requires security identity, exact trade date, `tradestatus`, unit-normalized fingerprint, and versioned tolerance. `BOUND_SOFT` is diagnostic only. Turnover remains supplemental and cannot affect Core eligibility, formal ranking, or Focus activation.
- Existing project turnover config specifies fraction output `0..1`; this does not prove BaoStock source unit or denominator. BaoStock `turn` unit is therefore frozen as `UNVERIFIED`; no scaling is guessed. BaoStock source-specific fingerprint tolerances remain `UNFROZEN`.
- No BaoStock SDK or valid BaoStock receipt was found. Existing Tencent receipt has zero comparable rows and is not reusable; existing Eastmoney/Tencent tolerances are not BaoStock evidence. The official dynamic reference did not yield verifiable unit/quota details during this stage.
- Request bounds are documented as inactive engineering candidates; network capability remains disabled until enforcement and independent audit acceptance.

Added artifacts:

- `config/baostock_supplemental_contract_v1.json`
- `docs/BAOSTOCK_SUPPLEMENTAL_CONTRACT_V1.md`
- `docs/audits/V4_00F_BAOSTOCK_GATE_AUDIT_20260925.md` (`OPEN`)

## Acceptance result

**`DEGRADED_PASS / CONTRACT_FROZEN_LIVE_CAPABILITY_UNVERIFIED`** — contract boundary and evidence requirements are frozen; all BaoStock datasets remain `UNAVAILABLE`, and no `BOUND_STRICT` receipt may be issued. No external capability is asserted as accepted. Independent audit `V4-00F-BAOSTOCK-SUPPLEMENTAL-GATE-01` remains open for unit/field map, denominator, source-specific tolerance, quota/terms, package hash, worker enforcement, and representative receipts.

## Next stage

`V4-00G / ALGORITHM_CONTRACT_FRAMEWORK`. V4-01/bootstrap remains gated by V4-00D and V4-00H. Scanner work must wait for the final Phase 0 receipt in V4-00H; any blocked capability remains scoped to its dependency.
# Repair addendum (2026-09-25): `DEGRADED_PASS / CONTRACT_COMPLETE_LIVE_CAPABILITY_OPTIONAL`

BaoStock remains `UNAVAILABLE`; no network/API was called. Its supplemental contract is complete for this phase and does not gate the accepted A_STOCK TDX Core package, RAW history bootstrap, Core eligibility, ranking, state, or Focus. Any future live capability requires bounded-request enforcement and its own source-specific receipts.
