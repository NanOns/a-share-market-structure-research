# V4 R24R1｜Go-Forward Input Authority + Cohort Identity Repair Independent External Audit R1｜2026-10-04

## 0. Audit Target

Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `0c9f59fbe723fe0fb0e9d1a6750c339894bc7a5b`  
Audited remote HEAD: `31db7c17463d7a314c4dbfb10023f701c1a9387b`  
Exact tested source: `3eb148c3c19ca079fd5986aeb3a1922b9bf43075`  
Immutable tested tag: `refs/tags/codex/r24r1-go-forward-tested-source-20261004-r3`

## 1. Unique External Decision

```text
R24R1_EXTERNAL_AUDIT =
PASS_FINAL_FUTURE_SESSION_ACTIVATION_CAPABLE_DISABLED_CANDIDATE

R24_FORWARD_DAILY_INPUT_AUTHORITY = CLOSED_EXTERNALLY_ACCEPTED
R24_COHORT_ENROLLMENT_IDENTITY = CLOSED_EXTERNALLY_ACCEPTED
R24_REALTIME_ADMISSION_WRAPPER_SEMANTICS = CLOSED_EXTERNALLY_ACCEPTED

R24R1_GO_FORWARD_INPUT_AUTHORITY = PASS_EXTERNAL
R24R1_RUNTIME_DEPENDENCIES_V3 = PASS_EXTERNAL
R24R1_REALTIME_ADMISSION_CONTRACT = PASS_EXTERNAL
R24R1_FUTURE_SESSION_REACHABILITY = PASS_EXTERNAL_ENGINEERING_SIMULATION
R24R1_DAILY_INPUT_NEGATIVE_MATRIX_F01_F14 = PASS_EXTERNAL
R24R1_COHORT_NEGATIVE_MATRIX_C01_C04 = PASS_EXTERNAL
R24_A01_A20_REGRESSION = PASS_EXTERNAL
R24R1_INDEPENDENT_ORACLE = PASS_EXTERNAL
R24R1_TESTED_SOURCE_GOVERNANCE = PASS_EXTERNAL

V4_16_REAL_SHADOW_RUNTIME =
FUTURE_SESSION_ACTIVATION_CAPABLE_DISABLED_CANDIDATE

V4_16_FIRST_REAL_SHADOW_ACTIVATION_PACKET_ENTRY = AUTHORIZED
V4_16_REAL_SHADOW_EXECUTION = NOT_YET_AUTHORIZED

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
V4_16_ACCEPTED_HEAD = NOT_CREATED

Production = false
Shadow = false
Focus = false
V4_16 = false
```

## 2. Tested Source / Regression

Tag resolves exactly to `3eb148c3c19ca079fd5986aeb3a1922b9bf43075`.

Clean detached regression:

```text
403 passed
0 failed
0 errors
0 skipped
0 deselected
```

Final HEAD is one evidence-only commit ahead of the tested source. No runtime implementation changed after testing.

The first clean attempt was correctly dispositioned and the final clean retest passed.

## 3. Go-Forward Daily Input Authority｜PASS

R24R1 introduces `V4_16_GO_FORWARD_INPUT_AUTHORITY_V1` and separates:

```text
IMMUTABLE_ALGORITHM_STAGE
+
EXACT_ACCEPTED_SESSION_INPUT
```

The historical Stage/V4-15/model/parameter authority stays immutable. Future target-session acceptance comes only from an exact `daily_input_authority` binding carried by the activation grant.

`GoForwardInputAuthority` uses `CurrentStageAuthority` only as the immutable algorithm/governance view, then replaces runtime calendar/data/identity/universe/source interfaces from the exact target-date authority.

Therefore the old `accepted_trade_date == 2026-09-30` condition no longer authorizes or blocks the future target session.

## 4. Future Session Reachability｜PASS

Persisted positive simulation uses:

```text
trade_date = 2026-10-08
```

The test proves the target is absent from old `CurrentStageAuthority.sessions`, while the new go-forward authority accepts the isolated exact daily input package.

The persisted E2E completes slot/publication/original enrollment/correction/due/settlement/stop under:

```text
ACTIVATION_SIMULATION
NOT_REAL_EVIDENCE
```

No real counters change.

## 5. Daily Input Contract｜PASS

Required target-session bindings include calendar, previous session, identity/universe, membership scope, mandatory Pure-Core sources, day package, snapshot identity, source manifest, model/parameter identity, immutable algorithm bindings and daily input digest.

Mandatory Pure-Core sources:

```text
TDX_RAW_DAILY
ADJUSTED_DAILY
OWNER_OUTPUT
T0_SNAPSHOT
```

The authority validates target date, nested source trade dates, UTC acceptance boundaries, source quality/capability, exact bytes and manifest digests.

Membership is capability-scoped: missing membership does not globally block `PURE_CORE_STOCK`.

## 6. F01-F14｜PASS

The daily-input negative matrix covers target/calendar/prior mismatch, digest mismatch, stale or future source data, late acceptance, missing source, universe/membership scope, revision rollback and model/parameter mismatch.

### P2 Nonblocking Note — F12

F12 currently points the grant to a nonexistent `latest.json`, so it fails via exact-read `FileNotFoundError`.

Production runtime itself contains no glob/latest/mtime/max-filename discovery path, therefore this is not an authorization vulnerability.

Classification:

```text
F12_TEST_EXPRESSION = P2_NONBLOCKING
```

Next round should improve F12 by creating a valid decoy `latest.json` and proving it is ignored/rejected because it is not the exact bound authority.

Do not reopen R24R1.

## 7. COHORT_V1 Identity｜PASS

The final realtime enrollment now follows the accepted contract:

```text
enrollment_key =
[logical_event_id, cohort_namespace]

cohort_namespace =
FIRST_OBSERVED

enrollment_id =
SHA256(canonical([logical_event_id, cohort_namespace]))
```

`SHADOW_V4` is only runtime/storage namespace.

The independent oracle loads the accepted COHORT_V1 contract and recomputes the persisted ID from the actual key fields.

The R24 identity mismatch is closed.

## 8. Realtime Admission Semantics｜PASS

R24R1 formalizes `V4_16_REALTIME_ADMISSION_V1`:

```text
owner projection =
CANDIDATE_ENROLLMENT_TEMPLATE
NOT_COHORT_ACCEPTANCE

V4-16 realtime admission =
FIRST_OBSERVED cohort authority
```

The same transaction computes the slot, persists `ACCEPTED_ON_TIME`, writes the final enrollment, verifies owner logical event + source manifest + receipt set + COHORT_V1 identity, persists realtime admission, then commits publication/state/head.

Any failure rolls back the accepted publication/enrollment/admission/daily-input writes.

## 9. Independent Oracle｜PASS

The independent validator does not import the runtime writer and independently validates daily input, prior session, source dates/timestamps, Observation Slot V2, manifest, owner-event identity, COHORT identity, realtime admission, publication CAS, storage origin and protected state.

It also verifies projected owner enrollments remain candidate-only.

## 10. UTC Boundary Regression｜PASS

UTC timestamps are parsed as instants rather than compared lexicographically.

Regression covers source accepted 1ms late, daily input accepted 1ms late and late second mandatory source.

Writer and oracle both reject these cases.

## 11. R24 A01-A20 Regression｜PASS

All prior activation fail-closed tests remain passing.

## 12. Protected State｜PASS

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED

runtime_authorized = false
real_shadow_authorized = false
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

Production = false
Shadow = false
Focus = false
V4_16 = false
```

Direct lookup confirms `data/v4/V4_16_ACCEPTED_HEAD.json` does not exist.

## 13. Next

R24R1 proves a future-session-capable runtime but does not authorize a particular live target date/source/storage/activation digest.

Next:

```text
R25_FIRST_REAL_SHADOW_ACTIVATION_PACKET
```

Freeze a target-session-specific, non-executable activation packet and submit its exact digest for external audit.

If no eligible target-date accepted source exists:

```text
WAIT_ACCEPTED_DAILY_INPUT
```

is a correct non-failure exit.

Do not fabricate a future source and do not backdate runtime source observation.
