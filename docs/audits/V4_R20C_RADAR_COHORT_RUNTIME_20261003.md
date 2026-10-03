# V4 R20C Radar / Cohort engineering acceptance

Baseline: `2020234020e09020aca13fd84cdabde6fbb81f50`.
Entry: `reports/r20a/CURRENT_AUTHORITY_GATE.json` PASS_LOCAL. Applicable dispatch authority is `docs/evidence/r20/V4_NEXT_ROUND_EXECUTION_MASTER_R20_20261003.md`; stage contract is the R20C task and exact R19 V4-15 package.

The current V4-14 authority admits only publications bound by its accepted runtime seal. Runtime copies accepted D2 state, explicit state events and accepted ENROLLED PREWATCH transitions without recomputing owners. It persists all eligible ledger rows, risk events, stable logical-event keys, per-publication observations and immutable enrollments in a dedicated engineering namespace. Persistent state adds ledger only. Multi-sector annotations, display and Focus have no enrollment role. Stock WARM lacks a formal owner and is NOT_APPLICABLE. Invalidated, retracted and corrected observations preserve the existing enrollment for settlement.

Exact accepted Data Head ADJUSTED_DAILY T0 rows supply reference closes and local affine adjustment identities for reconstructed real source enrollments. Missing references remain null. Parameter digests bind the exact accepted V4-10 parameter package when the owner's parameter identity matches; unsupported fixture parameter identities remain null/UNKNOWN. No future source is read to establish T0. Why Now and conflict items bind source evidence; absent competing hypotheses retain HYPOTHESIS_SET_INCOMPLETE.

Independent oracle `scripts/validate_r20c_runtime.py` imports neither evaluator nor producer and reconstructs identities, complete expected eligible population, exact provenance and T0 prices directly from accepted inputs and frozen contracts. Receipt `reports/r20c/RADAR_COHORT_PERSISTED_RUN.json` and oracle `reports/r20c/INDEPENDENT_RADAR_COHORT_GATE.json` bind 24 publications and 119 unique enrollments. Real capability source covers 5,224 owner rows, 117 eligible ledger/event rows and RECONSTRUCTED_ASOF enrollment. Historical PIT effectiveness remains NOT_GRANTED. Earlier engineering namespace is retained append-only; the final receipt uses radar_cohort_r2 after adding verified T0 price and parameter provenance.

Validation: 25 tests passed. They exercise event families, persistent state, same-day revision, correction and retraction, controls/T0 preservation, formal reentry, stock WARM, SEED/Near-Miss diagnostic exclusion, multi-sector annotations, Focus/display independence and forbidden future/FEP/filter/reset/overwrite paths.

R20C_V4_15_RADAR_COHORT_RUNTIME = PASS_LOCAL
RADAR_COHORT_PERSISTED_E2E = PASS_LOCAL
V4_15_ACCEPTED_HEAD = NOT_CREATED
Production = false
Shadow = false
Focus = false
NEXT = R20E_AFTER_R20D_AND_R20B
