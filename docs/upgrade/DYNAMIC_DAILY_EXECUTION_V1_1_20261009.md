# Dynamic daily execution V1.1

User request: execute the supplied V4-DYNAMIC-DAILY-R1.1 document. Scope DD01–DD07;
read-only operational research, AUTO default ON when the service runs. No minute
bars, new financial chain, external adjustment authority, BaoStock week/month calls,
or historical PIT escalation. Frozen R43 code and old Owners remain immutable.

Baseline Git: 6f0cf3c5a983eab481283d0436e050d70b77fe29. Clean worktree at entry.
Latest applicable Drive FP contracts read from 17tbCyE-gYhe2pwoy2gLFeoNNwq9NPKxu;
latest independent driver/audit read from 15GsPpj_0OiOAUd41b4TqjGs0Vi2TBJxn.
Local FP02/FP11/FP14 records and FP ingress gap matrix continue to apply.
Phase 0 FULL_PASS is inherited from the FP02 recorded receipt; no scanner scope is added.

## DD01 contract and acceptance

V4_OPERATIONAL_DAILY_CALENDAR_V2 enumerates every missing official SSE/SZSE
session, separates eligible and waiting dates, accepts timezone-aware clocks only,
and explicitly reports calendar coverage exhaustion. The frozen calendar head is
LOCAL_READY_FOR_EXTERNAL_AUDIT; reading its SHA-verified official bytes does not
promote its independent acceptance. Calendar admission must remain explicit downstream.

V4_DAILY_SOURCE_READINESS_V2 requires the 18:35 time gate and at least 30 minutes
after the factor publication baseline. Clock passage never creates source readiness.
Per-day verified proofs require digest, observed time, real TDX bar coverage,
BaoStock provider dates, daily identity reconciliation, and proof for zero factor changes.

Evidence: DD01_REAL_CALENDAR_READBACK.json (real official frozen bytes, explicitly
simulated clocks/downtime) and 13 targeted pytest cases. Protected operational and
strict PIT Head SHA values are checked before/after.

Acceptance: ENGINEERING_PASS_SCOPED for gap planning and source-proof gates;
EXTERNAL_ACCEPTANCE_NOT_GRANTED. No new session is published by DD01.
Next: DD02 latest-package extraction and genuine date-specific BaoStock runtime.

## Independent audit tracking

DD-A01: official calendar candidate admission scope; independent from DD01 tests.
DD-A02: full Rotation state-machine oracle, inherited VALIDATION_ONGOING.
DD-A03: request-ledger cross-midnight accounting and multi-process locking;
independent of source ingestion status, requires actual source-code and race evidence.
DD-A04: algorithm acceptance and affected-history recomputation must be bound before
successor production. No old one-time user cutover signature may be reused.

Overall DD01–DD07 delivery is IN_PROGRESS, not a final release acceptance.

## DD02 source execution

Real official metadata reports package date 2026-10-09 15:58:53. The 551,544,006
byte ZIP (SHA256 5e973fa2b8919635f7f5f10212ef4c4c33e7a05503c01e58650a2ac376d99ca4)
contains actual A-stock bars only through 2026-10-08 at this observation. Thus
package publication date cannot prove 10/09 bars. Historical extraction produced
5,557 native A-stock rows for 10/08, with later-snapshot reconstruction explicit.
This includes rows outside the canonical daily market and is NOT a coverage QA pass.

Initial extraction rejected a date-order defect in sh000833 (an index). The successor
now uses the existing typed A-stock classification before parsing market-specific
stock bars; index data is explicitly excluded, not silently repaired. Stock order
defects remain fatal. Source download used the existing R3 official challenge adapter;
rejected response bytes and actual ZIP receipt are preserved outside TDX.

10/08 real BaoStock smoke initially failed on factor header `adjustFacto`. Reused
the existing exact SDK SHA schema adapter (0.9.3, 32bd19de…8686bfe), retaining native
responses. Normalized provider dates are derived from actual returned daily/effective
dates, never request echoes. The actual dual-series runtime subsequently passed.
Schema independent external acceptance remains NOT_GRANTED; no QFQ authority change.

Evidence: DD02_REAL_TDX_EXTRACTION.json and DD02_BAOSTOCK_RUNTIME_READBACK.json,
actual smoke manifests/native rows, shared request ledger, latest capture receipt.
Acceptance: ENGINEERING_PASS_SCOPED for official latest-package historical extraction
and actual dated runtime smoke; complete source/identity reconciliation is pending.
Next gated dependency: DD03 dated identity/lifecycle/GBBQ QA and full numeric Owner
successor, alongside independent DD04 job/UI work. No 10/09 publication occurred.
