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
