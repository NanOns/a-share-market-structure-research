# V4-00F-BaoStock-Supplemental-Gate-01 Audit

| Field | Record |
|---|---|
| audit_id | `V4-00F-BAOSTOCK-SUPPLEMENTAL-GATE-01` |
| status | `OPEN` |
| opened_at | `2026-09-25` |
| scope | Independent acceptance of BaoStock daily `turn` field/unit/denominator, exact identity/date/status binding, source-specific close/volume/amount fingerprint tolerances, SDK identity/hash, bounded request worker/quota, and representative immutable receipts. |
| current_capability | `UNAVAILABLE`; no BaoStock package, API request, or valid BaoStock receipt was present. |
| impact | BaoStock turnover outputs remain unavailable. TDX Core facts/publication continue independently. Do not reuse existing Tencent receipt or Eastmoney/Tencent tolerance settings as BaoStock evidence. |
| independent_from | V4-00F stage DEGRADED_PASS; V4-00D overlap gate; AUD-AMOUNT-A-06; other REV2 audits. |

## Evidence at opening

- Latest V4.2.2 REV2 was re-read for this stage. Its SHA-256 is `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`; contract re-audit SHA-256 is `8ae62a108262ddb63c42457c0920e0418b8df1013c26263edb3b3e34de8b4747`.
- REV2 §3A/§9.4–§9.7/§78/§87A establish BaoStock as supplemental, define strict binding prerequisites and 60/250 history windows, and exclude turnover from Core eligibility/ranking/Focus activation.
- `docs/BAOSTOCK_API_ANALYSIS_AND_INTEGRATION_PLAN_V1_20260916.md` (SHA-256 `fe54ebf493adbca0c18c8f270cd5bb8ddfdc4cc91ea39a52b6261f49e4a84175`) notes that official dynamic docs did not establish the project's quoted quota/blacklisting restrictions; the 50,000/day ceiling is not treated as verified policy.
- Official reference was identified as `https://www.baostock.com/mainContent?file=stockKData.md`; current browsing did not yield verifiable field-unit or quota text. No live API request was made.
- `docs/P12_15_TURNOVER_CONTEXT_ALGORITHM_DESIGN_20260916.md` (SHA-256 `f456779afa05f83ed116c77ec10dee1d859006e7093abb3da861926dad9eb8d6`) and `config/turnover_context_params_v1.json` define normalized fraction output and basis semantics, but do not validate BaoStock wire units.
- `reports/p12_15/P12_15_TURNOVER_CONTEXT_IMPLEMENTATION_RECEIPT.json` (SHA-256 `31292a354933f805be7eb58628df9a992cf7be89748a9a9cef1f8514229afb45`) is a Tencent-source receipt with zero comparable rows and bypassed semantics; it is not BaoStock evidence.
- `src/workbench_analysis/turnover_enrichment_v3_3.py` and `config/p12_14_turnover_source_contract_v1.json` belong to the Eastmoney/Tencent candidate path. Their fingerprint tolerances cannot establish BaoStock tolerance.
- BaoStock Python package was not installed; no BaoStock receipts were found. Current HEAD was `3ef5bf63455447dd605534dc4c1717eb238a86f5`.

## Closure evidence required

1. Provide authoritative source evidence for the `turn`, `tradestatus`, `isST`, close/volume/amount field meanings, date behavior, and unit/denominator basis. Freeze a versioned field map and SDK/package version plus artifact hash.
2. Independently determine source-specific normalized fingerprint tolerances using representative securities/dates and independently established expected values. Keep strict and soft outcomes distinct; soft remains diagnostic.
3. Demonstrate exact code/security mapping, date equality, local status cross-check, stale/missing behavior, stable digest, and append-only supplemental revision without modifying TDX or Core snapshot identities.
4. Implement and review request accounting and enforcement for login, queries, retries, logout, serial concurrency, per-call/job timeouts, daily budget, deterministic ordering, checkpoints, circuit breaker, and failure isolation. Verify actual vendor quota/terms before activating any assumed cap. Engineering candidates in the V1 contract are inactive until then.
5. Produce representative immutable receipts with source/field-map/contract versions, timestamps, raw-unit provenance, normalized values, binding results, and failure reasons. Establish semantic turnover basis before enabling turnover tiers; confirm history uses 60 minimum/250 maximum per §9.4–§9.6.
6. Independently accept this audit. Until then all BaoStock datasets remain `UNAVAILABLE`, and no `BOUND_STRICT` result is permitted.

Keep `OPEN` until every closure condition has evidence. This audit does not block accepted TDX Core publications or scanner work whose other gates have independently passed.