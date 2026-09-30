# V4-08 R5 closure

Terminal status: `V4_08_R5_READY_FOR_EXTERNAL_ACCEPTANCE_ENGINEERING_SCOPE`. Independent external acceptance is pending.

Final implementation commit: `3adf4378a1dfa5e6eea60c2efb6e7e913db1cec1`. This code commit was pushed and independently verified at the remote branch before the final evidence-only commit. The final evidence HEAD is reported in the session after pushing it.

Scoped PIT membership head: SHA256 `d6374a73b8084ccd383cbb4f75428ed91176e91cc09d87c3329041d57c5bd9ed`; FORWARD_PIT_MEMBERSHIP_ONLY; first date 2026-09-30; 50,162 facts (INDUSTRY 5,224 / THEME 44,938); 378 sectors (110 / 268). Immutable source revision, snapshot and fact artifacts remain unchanged.

Native / B0 / four-state B1 / exact source-bound B2 are implemented as separate candidate producers. Native ranks use section 10A0, whereas the legacy CURRENT P1 preserves its actual average-rank/N definition. The B2 frozen AST is extracted from build_sector_current/build_sector_potential, binds actual checked-out source and YAML parameter bytes, and preserves UNKNOWN. All three legacy WARM paths require Amount A and remain diagnostic; unavailable exact legacy cycle rank inputs are not replaced by V4 ranks or Base Seed. Rotation freezes prior-known membership, pulse baseline prices and coordinate identities; missing or mixed price bases stay UNKNOWN. Common-member deltas preserve membership changes separately. Mature strong-empty N/A does not block early IN/ACCEPTED.

The first-day candidate contains 378 rows per producer; B0, B1 and B2 confirmed_raw are each UNKNOWN for all 378 sectors. Core/Seed accepted artifacts target 2026-09-28, so no 2026-09-30 Core rows are admitted. Missing target publication coverage is NULL/UNKNOWN. No old staging, current-membership replay, final stock output, turnover or future outcome fills this gap. Seed fields remain degraded while Prior-RPS is open.

Five new R5 parameter values: early seed retention 2/3; early breadth retention 0.6; early breadth delta 0; early top1 concentration 1/3; mature strong retention 0.75. Parameter set SHA256 `0204d7c4fadf86871b6a079f755593b1a3f8ad18bb718f73ba33db0b70f67548`. Each has candidate ranges, monotonicity, boundary sensitivity and explicit semantic selection/rejection reasons. Five rebound temporary parameter fixtures change runtime predicates; no production literal fallback or future-return optimization is used. Ten independently expected B2 golden vectors and original V3 function comparisons cover positive, negative, unknown, boundary and Amount A cases. Seven feedback families leave raw B0/B1/B2 results invariant.

Append-only migration 020 is new; prior migrations are unchanged. PostgreSQL 18.6 disposable-cluster verification applied migrations 001–020, persisted and exactly read back 1,512 candidate rows, checked repeat insertion, and rejected publication/result mutation. No configured database or config/.env was used. The cluster was destroyed.

Final isolated regression: 677 tests; 675 passed, 2 skipped, zero failures and errors. Detached checkout was clean before/after; rebuilding the candidate changed no tracked bytes. Permanent governance hard gate passed with zero hard-gated symbol hits and no unclassified paths. Tests establish engineering behavior, not release acceptance.

Separate open audits: Prior-RPS; AUD-AMOUNT-A-06; V4-01 listing-anchor reconciliation; AUD-V4-08-TARGET-CORE-01. Per-capability degradation is retained in the candidate manifest. Historical intermediate candidate artifacts remain immutable; only the current manifest selects the final cohort.

Global accepted range stays V4_00_TO_V4_07_ACCEPTED. No V4_08_ACCEPTED_HEAD.json or rotation production permission was created. Next stage: independent R5 external acceptance. Stop after pushing code and evidence.
