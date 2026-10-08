# R4.1 external audit handoff — 2026-10-09

Result: **NOT_COMPLETE / BLOCKED_SAFE_LAST_GOOD**. The bounded acquisition stage is DEGRADED_PASS. No new Owner or production successor has been accepted or published. This handoff requests independent review of the completed acquisition scope only; pushing is not external acceptance.

Actual execution: 12,246 local TDX files read; one stock (SZ.301486) contains target-date bars. Live official metadata says 10/08, but ZIP downloads return TencentEdgeOne HTML rather than a ZIP. Rejected bytes, headers and hashes are retained. The four-date run made 12 HTTP requests and 548 BaoStock SDK requests including login/logout (the shared day ledger also contains subsequent normal daily runs). There are 547 query receipt entries, including one local checkpoint PermissionError diagnostic that is **not** an additional provider request/error; see its append-only classification correction.

BaoStock daily responses contain 5,222 / 5,223 / 5,224 / 5,224 stock rows. All 176 historical gap securities were queried for raw and front-adjusted OHLC and factors; all 528 gap security-days and 35 historical suspensions have individual reconciliation rows. Oct08 has 15 suspended rows, 5,209 actual-traded rows, and independently measured GBBQ unsupported categories for 176 traded securities. Its 5,209 native-QFQ admissions remain unproved: 176 have unsupported events; the remainder still lack admitted canonical target source/coordinate. Do not equate observed BaoStock QFQ with the project's native affine coordinate.

The matrix has 20,893 stock-date rows and 17,042 independent Decimal comparisons/transform diagnostics. There are zero OHLC differences above 0.011 in raw overlap diagnostics; this diagnostic threshold is not an accepted cross-source tolerance. The provider QFQ/RAW ratios are recorded for O/H/L/C separately. Existing immutable source versions and published heads remain unchanged.

Implemented: versioned policy/registry, resumable per-query acquisition, bounded retries/shared budget, independent BaoStock retrieval even when TDX fails, explicit corrected staging candidates, daily membership byte freezing without backdating, calendar-based Oct08 discovery, proper SOURCE_CAPTURE_BLOCKED handling, CLI import/UTF-8 fixes, and local-persistence/provider-error separation. The normal daily entry actually ran the acquisition hook and ended blocked; it did not return no-new-session.

Membership API requests and current TDX classification snapshots are frozen. They do not prove all historical effective dates or concepts. No recurring scheduler was installed; capture runs automatically when DM01 active acquisition executes.

V4-13 implementation exists; the actual engineering entry rejects the current V4-15 stage. This is a versioned routing/binding debt, not source nonexistence. Original frozen routing also encounters moving-owner digests. V4-12/13 full corrected owner materialization, RPS predecessor binding, Focus/Forward new-day consumption, accepted cross-source tolerances and scoped CAS/IAB release validation remain incomplete. They are separately tracked in docs/audits/V4_R4_SOURCE_AND_OWNER_OPEN_ITEMS_20261009.md, not waived by acquisition tests.

The targeted suite has 61 passing tests; real receipt invariants pass. HTTP readback confirms the original 9/30 research context token and joint release digest. IAB page creation/binding timed out; no browser acceptance is claimed. Source/data limitations and owner admission prevent overall completion.

## Four-session reconciliation

Counts below separate observed provider records from accepted canonical TDX bars. Per-date request counts include shared range calls and must not be summed; authoritative actual request totals are the budget ledger and HTTP ledger. Existing 9/30 Owners remain ready; **new corrected** Owners do not. Historical membership/PIT evidence is not inferred from current observations.

| trade_date | official_session | canonical_tdx_raw_count | baostock_daily_count | gbbq_ready | qfq_capability_unknown | suspended_no_bar | identity_stock_count | industry_concept_membership_count | market_owner_ready | core_profile_ready | structure_known_count | rotation_known_count | accepted_head_before | accepted_head_after | live_context_token | real_request_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-09-28 | True | 5210 | 5222 | READ_PARSED_ADMISSION_PENDING | 176 | 12 | 5222 | NOT_VERIFIABLE | False | False | NOT_VERIFIABLE | NOT_VERIFIABLE | 2026-09-30 | 2026-09-30 | research-v4-d9d052fdf912c0975f5bfca0cd1067fe4a47fde99d804ce356c266da960e72f3 | 534 |
| 2026-09-29 | True | 5211 | 5223 | READ_PARSED_ADMISSION_PENDING | 176 | 12 | 5223 | NOT_VERIFIABLE | False | False | NOT_VERIFIABLE | NOT_VERIFIABLE | 2026-09-30 | 2026-09-30 | research-v4-d9d052fdf912c0975f5bfca0cd1067fe4a47fde99d804ce356c266da960e72f3 | 534 |
| 2026-09-30 | True | 5213 | 5224 | READ_PARSED_ADMISSION_PENDING | 176 | 11 | 5224 | 50162 | True | True | 7 fields: 0 each / 5213 | 0 | 2026-09-30 | 2026-09-30 | research-v4-d9d052fdf912c0975f5bfca0cd1067fe4a47fde99d804ce356c266da960e72f3 | 534 |
| 2026-10-08 | True | 0 | 5224 | READ_PARSED_ADMISSION_PENDING | 5209 | 15 | NOT_VERIFIABLE | NOT_VERIFIABLE | False | False | NOT_VERIFIABLE | NOT_VERIFIABLE | 2026-09-30 | 2026-09-30 | research-v4-d9d052fdf912c0975f5bfca0cd1067fe4a47fde99d804ce356c266da960e72f3 | 534 |

Next: resolve R4-A01 official capture, independently admit native price coordinates/field fallback, build corrected Owner successors through the separately versioned stage routing, then run real full-domain E2E and scoped CAS/readback. No old receipt or production pointer was rewritten.
