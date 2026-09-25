# BaoStock Supplemental Source Contract V1

- Contract ID: `BAOSTOCK_SUPPLEMENTAL_SOURCE_V1`
- Version: `1.0.0`
- Status: `FROZEN_SPEC_LIVE_CAPABILITY_UNVERIFIED`
- Stage: `V4-00F`
- Machine contract: `config/baostock_supplemental_contract_v1.json`

## Purpose and authority

BaoStock is a supplemental source for daily turnover (`turn`) and cross-checks of `tradestatus` and `isST`. TDX/local identity remains authoritative for security identity, OHLC, volume, amount, QFQ, and local trading status. BaoStock close, volume, and amount may only fingerprint a candidate row; they cannot overwrite TDX facts or alter Core publication identity, eligibility, sorting, or Focus activation. BaoStock adjusted OHLC is not a fallback price source.

## Field and unit rules

`turn` unit and denominator semantics remain unverified. Preserve the original value and declared unit. Do not infer percent-vs-fraction scaling or divide by 100 without an independently verified, versioned BaoStock field map. Normalize to the existing turnover factor's fraction representation (`0..1`) only after the source unit is proven. Semantic turnover states require a verified float-share or free-float-share denominator. `SOURCE_DEFINED`, `UNKNOWN`, or merely declared basis remains display/diagnostic-only and cannot produce semantic tiers or positive rank effects.

## Binding

`BOUND_STRICT` requires exact TDX security identity mapping, exact target trade date, a local `tradestatus` cross-check, normalized close/volume/amount fingerprint, and a source-specific versioned tolerance contract. Tolerance values are currently unfrozen. Existing Eastmoney/Tencent tolerances are not evidence for BaoStock and are not copied into this contract. `BOUND_SOFT` is diagnostic only. Unknown unit, identity, date, status, or fingerprint acceptance fails closed and cannot enter `TURNOVER_CONTEXT_V1`.

Each candidate row must retain source contract and field-map versions, query identity, security/date identity, provider date/time, UTC observed/received timestamps, raw value and unit, normalized value only when justified, source revision/digest, binding status, and failure reason. Provider timestamps must not be substituted for an absent source trade date.

## History and factor boundary

Per REV2 §9.4–§9.7, `TURNOVER_CONTEXT_V1` uses N=5/20/60 prior strict-bound actual sessions, requires at least 60 prior samples plus the target date, prefers 250, and looks back no more than 250 market sessions. Confirmed suspensions can be skipped; unknown missing sessions cannot. Insufficient history degrades only this supplemental metric. The factor remains outside Core eligibility, formal ranking, and Focus activation.

## Request safety

Network capability is disabled. Activation requires closure of the independent V4-00F audit and evidence that a worker enforces bounds. Candidate engineering values (one serial request at a time, 30-second per-request timeout, six-hour job timeout, one transient retry, assumed 50,000/day vendor ceiling with 40,000 soft stop and 45,000 hard stop) are explicitly unverified and inactive. Every login/query/retry/logout must count toward the eventual budget; retries count too. Work must be deterministic, checkpointable, idempotent, bounded to one instrument/range request, and must not block the Core flow. No unbounded probing, retry loop, or request-time enrichment is allowed.

The existing project note about a 50,000/day ceiling is treated as an unverified project assumption, not official vendor policy. Official field-unit/quota evidence was not established in this stage. The BaoStock package is not installed, and there are no BaoStock receipts to reuse.

## Failure states and acceptance

Capabilities remain `UNAVAILABLE`; `BOUND_STRICT` cannot be issued until the field map, unit, denominator basis (for semantic use), package hash, source-specific tolerances, bounded worker, and representative receipts pass independent acceptance. Failure only degrades this supplement and cannot invalidate an accepted Core publication. BaoStock supplements are stored as append-only revisions separate from Core snapshots. TDX roots and inputs remain read-only.