# R24R1 execution contract and audit disposition

User authorization: execute the supplied stage documents, commit related code and evidence, and push after this authorized stage. Document contents define stage scope and gates; they do not themselves grant real activation or next-stage acceptance.

Baseline: 0c9f59fbe723fe0fb0e9d1a6750c339894bc7a5b. Applicable upgrade: V4.2.2 REV4 FEP R2, sections 77B and 78, with the supplied R24R1 master/task and R24 external audit controlling this repair.

Scope: successor V3 dependencies and disabled authority; immutable algorithm/stage view plus an exact per-session daily input authority; COHORT_V1 identity repair; explicit candidate template versus realtime admission; independent persisted-state oracle. The frozen V2 authority and R24 runtime/evidence remain historical inputs. Default REAL_SHADOW routes to V3; explicit isolated R24 simulation routes retain their historical implementation for regression.

The future 2026-10-08 calendar, source, Universe, package, grant and database are deterministic isolated simulations. Their accepted-like records are NOT_REAL_EVIDENCE. They establish engineering reachability only. No actual daily source acceptance, real activation, real PIT enrollment, or real maturity is claimed.

Acceptance requires stage-specific machine gates, all prior regression suites without deselection, clean detached verification of an immutable tested source tag, and independent oracle readback. Tests and Git push do not establish external acceptance.

Separate audit items:
- R24_P0_FORWARD_AUTHORITY: exact daily head replaces frozen historical calendar/data as runtime input authority. Evidence: FORWARD_INPUT_AUTHORITY_GATE and DAILY_INPUT_NEGATIVE_MATRIX.
- R24_P0_COHORT_IDENTITY: persisted identity derives from actual logical_event_id and cohort_namespace values in COHORT_V1. Evidence: COHORT_IDENTITY_GATE.
- R24_P1_REALTIME_ADMISSION: owner artifacts are candidate templates; final enrollment requires exact owner event, internal receipts, accepted-on-time slot and atomic publication. Evidence: REALTIME_ADMISSION_GATE.

Local closure remains pending independent external audit. Actual runtime and real Shadow authorizations remain false; grant and external acceptance remain null. Stage remains V4_00_TO_V4_15_ACCEPTED, Data remains 2026-09-30, and V4_16_ACCEPTED_HEAD is absent. Real counters stay zero. TDX roots are read-only and are neither consumed nor changed by this repair.

Next: STOP_WAIT_R24R1_INDEPENDENT_EXTERNAL_AUDIT. Do not enter V4-17 or activate real Shadow.
