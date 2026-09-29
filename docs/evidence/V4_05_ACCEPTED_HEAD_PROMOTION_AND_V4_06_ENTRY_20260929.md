# V4-05 Accepted Head Promotion and V4-06 Entry

Stage contract: `V4_05_ACCEPTED_HEAD_PROMOTION_V4_06_ENTRY_TASK_20260929`

Starting HEAD: `06f1c0fd4a60e4f37e5f93fe729c84a04205c16b`

External decision: `V4_05_EXTERNAL_ACCEPTANCE_PASS_R4_2`

Terminal state: `V4_05_ACCEPTED_HEAD_PROMOTION_PASS_R1`

## Promotion

- Accepted candidate: `V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_2`.
- V4-05 status: `DATA_FACTOR_REPLAY_DEGRADED_PASS` with the externally accepted current-forward capability scope.
- Historical as-recorded adjusted price remains `BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`.
- V4-05 Accepted Head SHA-256: `fc929d85553a900a6479ac9f50291d50cf750ad0e6c21fc58e4e05e92189f5cb` (8456 bytes).
- Global Accepted Head SHA-256: `6fd6e16b3769726f14e44b1d2062d087fd40ec1ede51956a5353631896547043` (3990 bytes); accepted range is `V4_00_TO_V4_05_ACCEPTED`.
- Exact R4.1 binding: `all_exact_bindings_match=true`; `old_r4_binding_count=0`; PostgreSQL state logical digest `d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`.

## Accepted capability scope

- `CURRENT_FORWARD_ADJUSTED_PRICE = FULL_PASS`
- `WEEKLY_PERIOD = DEGRADED_PASS`
- `MONTHLY_PERIOD = DEGRADED_PASS`
- `PURE_CORE_FACTORS = DEGRADED_PASS`
- `MARKET_REFERENCE = FULL_PASS`
- `MARKET_REGIME = DEGRADED_PASS`
- `CURRENT_FORWARD_STOCK_CORE = DEGRADED_PASS`
- `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE = BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`
- `DATA_FACTOR_REPLAY_PASS = DEGRADED_PASS` for the accepted current-forward scope.

## Independent validation and next-stage boundary

- Pre-entry promotion validation passed before V4-06 authorization.
- Final independent promotion validation: `f63c4bb5951d5b1f85be6aa22da398a442b4630b3f67d93e13ff298ceccddd5e`; all requested promotion, capability, hash, LFS, Global Head, and successor-gate checks passed.
- V4-06 entry: `AUTHORIZED_SUPPLEMENTAL_ENRICHMENT`; V4-06 implementation: `NOT_STARTED`.
- V4-07: `NOT_STARTED`.
- V4-08: `BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION`.
- No V4-06 business artifacts were created. The next stage awaits the next external audit.

See [`V4_05_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json`](../../reports/v4_joint/V4_05_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json) and [`V4_05_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json`](../../reports/v4_joint/V4_05_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json).
