# V4-06 BaoStock Binding Tolerance Audit R1

| Field | Record |
|---|---|
| audit_id | `V4-06-BAOSTOCK-BINDING-TOLERANCE-01` |
| status | `OPEN` |
| opened_at | `2026-09-29` |
| scope | BaoStock-specific independent expected samples and normalized close/volume/amount tolerances for exact security/date/status binding; denominator semantics remain separately gated. |
| independent_from | V4-06 supplemental pipeline acceptance, TURNOVER_CONTEXT_V1 engine acceptance, and V4-05 Accepted Head. |
| capability_impact | BaoStock strict binding remains disabled; any live rows without independent acceptance are diagnostic only. |

## Entry evidence

- V4-00F source contract `config/baostock_supplemental_contract_v1.json` remains the authority (`BAOSTOCK_SUPPLEMENTAL_SOURCE_V1`, SDK `baostock==0.9.3`, percent-points to fraction, provider-defined circulating-shares denominator).
- The contract's `strict_fingerprint_tolerance_contract.status` is `UNFROZEN`; all BaoStock datasets remain disabled.
- Existing B6 receipt `reports/v4_baostock/public_b6_fingerprint_sample_receipt.json` recorded zero date pairs, zero successful security queries, and no tolerance acceptance.
- Existing B5 receipt has source rows but zero matched local fingerprint rows and explicitly leaves field/unit and strict tolerance acceptance pending. It cannot establish V4-06 strict binding.
- The official API reference URLs are already recorded in the source contract. The live reference pages could not be fetched by the web renderer during this stage; no new field semantics or tolerances are inferred from that failure.

## Acceptance criteria

1. Obtain representative source rows for multiple securities and dates, with independently anchored local expected close/volume/amount, exact identity and trade date, and status cross-check.
2. Freeze a BaoStock-only, normalized, versioned tolerance contract with sample coverage, boundary evidence, and independent acceptance.
3. Demonstrate tolerance boundaries including ±epsilon and prove conflicts return diagnostic/unbound states.
4. Keep `BOUND_STRICT` unavailable until all preceding criteria and denominator semantics are independently accepted.

## Current disposition

`OPEN / NOT_ACCEPTED`. No tolerance values are frozen by this audit. V4-06 may finish its supplemental pipeline and history engine with strict-bound inputs represented by fixtures, while the live capability remains `UNAVAILABLE` or diagnostic-only. This audit does not block or change the accepted V4-05 Core publication.

## V4-06 bounded probe evidence

- Receipt: `reports/v4_06/V4_06_LIVE_PROBE_RECEIPT.json` (`V4_06_BAOSTOCK_TARGET_BINDING_PROBE_V1`), observed `2026-09-29T14:49:10Z`.
- The accepted target `2026-09-28` returned a row for all four representative identities (Shanghai main board, Shenzhen main board, ChiNext, STAR); each request returned 245 daily rows over `2025-09-23` through `2026-09-28`.
- The SDK login/logout succeeded and the target-date fingerprints were not exact for any representative sample. Across common dates the exact close/volume/amount count was zero for all four identities. Close and volume matched in the sampled records, but local amount differed; the maximum absolute amount deltas per security are retained in the receipt.
- Result: `target_rows_observed=4`, `strict_bound_row_count=0`, and no provider error code. This is a binding/acceptance blocker, not an endpoint outage. The shared request ledger advanced by 12 operations over the stage (two bounded jobs, four history queries each plus login/logout accounting); the final job receipt records six operations.
- The receipt contains only minimized comparison samples, source digests, and summaries; it does not persist the full provider payload or credentials. The actual accepted PostgreSQL publication ID is taken from the V4-05 accepted revision ledger and its digest is checked against the accepted Core profile digest.
- The official API reference still returned no readable API body in the web renderer. Consequently this probe does not independently establish field semantics, the percent-points unit, or the provider-defined circulating-shares denominator.

## Next action

An independent reviewer must accept the official field/unit evidence, source-specific fingerprint tolerance and representative expected samples, and denominator semantics before this audit can close or any strict-bound capability can be enabled.
