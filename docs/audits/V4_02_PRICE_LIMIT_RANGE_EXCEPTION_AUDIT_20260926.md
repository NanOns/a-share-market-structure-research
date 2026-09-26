# V4-02 Price Limit Range Exceptions — Separate Audit

- Status: OPEN; independent from the V4-02 final stage gate.
- Scope: `CLOSE_OUTSIDE_LIMIT_RANGE` rows in the accepted candidate price-limit artifact.
- Evidence count: 23 rows (CHINEXT=2, STAR=1, SZ_MAIN=20); the largest repeated identity is `SEC-EDEDE35FE66896ACCA0AC85EEB2F133B` with 15 rows.
- Current handling: every affected output remains `UNKNOWN` with an explicit reason. No price-limit state is inferred.
- Evidence receipt: `reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R1.json` binds the price artifact, rule contract, and dated isST receipt hashes.

Acceptance requires independent dated identity/board and lifecycle review, corporate-action review, and recalculation of every affected boundary. Unresolved records remain UNKNOWN. This separate audit does not widen or block the R2 stage disposition because the current artifact fails closed per security.
