# R9 counter semantics candidate

Source authority R2 and governance R6R1 remain externally PASS KEEP. Only R9's authorized counter/time-domain AST edges and related metadata are amended. The exact leaf diff records every change; the retention formula and business rule ordering remain unchanged.

V4_12_SESSION_COUNTER_V2 defines two independent, unavailable-at-runtime design capabilities. post_creation_market_sessions counts unique accepted calendar sessions after available_date, including suspended or missing sessions. It serves old_anchor / earliest test only. post_creation_evaluable_sessions counts qualifying unique D1 observation dates after available_date, excludes missing/suspended/coordinate-unavailable observations, is cumulative rather than consecutive, and serves Acceptance.PENDING only.

Every revision uses the same frozen previous-market-date baseline. Revision replaces date membership and observation, never accumulates r1/r2/r3. Missing observations reset consecutive held/breach chains, preserve prior support meaning and emit UNKNOWN with stale. Calendar unavailable cannot fabricate old_anchor.

B03_missing is normatively corrected from NOT_ACCEPTED to PENDING: creation, missing next session, first evaluable resume gives market age 2, evaluable count 1 and held count 1. All other 68 prior expected results remain unchanged. The original historical R1 oracle and R2 evidence bytes are preserved; a separately versioned independent R2.1 oracle supplies the amended book and literal sequence expectations.

Independent sequences cover C01-C07, suspension, missing bar, unavailable coordinate, hold-then-missing chain reset, resume, and hold/breach r1/r2/r3 revisions. Time Domain Compatibility covers every AST comparison with definition-derived dimensions and expression algebra, plus independently authored positive and rejection vectors. A session threshold is not accepted merely because unit strings match.

Primary evidence: reports/v4_12_r2_1/R9_TIME_COUNTER_HANDOFF.json. Protected hashes, exact AST diff, amended vectors, sequence oracle, authority KEEP vectors, literal/DAG audits, time-domain audit, completeness and clean replay are separate records.

Unified commit and push are candidate delivery only. STOP and await external acceptance. No V4-12 runtime, src engine, migration, D2, V4-13, Stage/Data advance or operational permissions are authorized.
