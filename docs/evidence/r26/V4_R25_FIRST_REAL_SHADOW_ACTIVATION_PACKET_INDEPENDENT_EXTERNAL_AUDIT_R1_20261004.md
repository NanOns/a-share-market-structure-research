# V4 R25｜First Real Shadow Activation Packet Independent External Audit R1｜2026-10-04

## 0. Audit Target
Repository: `NanOns/a-share-market-structure-research`  
Branch: `codex/v4-system-reform`  
Execution baseline: `31db7c17463d7a314c4dbfb10023f701c1a9387b`  
Audited remote HEAD: `60b17524596918b66456fdd48dbc1beb068ab28a`  
Exact tested source: `00c6168160860c29f77a570bee45578f915a4778`  
Immutable tag: `refs/tags/codex/r25-activation-packet-tested-source-20261004-r5`

## 1. Unique Decision
```text
R25_EXTERNAL_AUDIT = PASS_VALID_WAIT_ACCEPTED_DAILY_INPUT

R25_TARGET_SESSION_SELECTION = PASS_WAIT
R25_REAL_DAILY_INPUT_GATE = PASS_WAIT
R25_REAL_SOURCE_AUTHORITY_GATE = PASS_WAIT
R25_PREDECESSOR_GATE = PASS_WAIT
R25_STORAGE_IDENTITY_GATE = PASS_WAIT
R25_ACTIVATION_CANDIDATE = NOT_CONSTRUCTED_CORRECTLY
R25_ACTIVATION_PACKET_MANIFEST = NOT_CONSTRUCTED_CORRECTLY
R25_INDEPENDENT_PREFLIGHT_ORACLE = PASS_EXTERNAL
R25_NEGATIVE_MATRIX_R25_01_R25_16 = PASS_EXTERNAL
R25_F12_EXPLICIT_BINDING_GOVERNANCE = CLOSED_EXTERNALLY_ACCEPTED
R25_TEMPORARY_STORAGE_POLICY = PASS_OPERATIONAL_NON_STAGE
R25_TESTED_SOURCE_GOVERNANCE = PASS_EXTERNAL

R25_REAL_ACTIVATION_PACKET = WAIT_ACCEPTED_DAILY_INPUT
REAL_SHADOW_EXECUTION = NOT_STARTED
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
V4_16_ACCEPTED_HEAD = NOT_CREATED
Production = false
Shadow = false
Focus = false
V4_16 = false

V4_17_ENGINEERING_ENTRY = AUTHORIZED
V4_17_ACCEPTANCE = NOT_GRANTED
V4_17G = NOT_GRANTED
```

## 2. Why WAIT Is Correct
Current accepted historical Data Head remains `2026-09-30`.

The accepted go-forward contract marks that Data Head as historical-only. R25 has no exact accepted REAL target-session binding for calendar, identity/universe, `TDX_RAW_DAILY`, `ADJUSTED_DAILY`, `OWNER_OUTPUT` and `T0_SNAPSHOT`.

Committed REAL activation authority remains:
```text
grant = null
external_acceptance = null
runtime_authorized = false
real_shadow_authorized = false
```

Therefore a READY packet cannot be constructed without inventing authority.

## 3. External Market-Calendar Cross-Check
Official SSE and SZSE 2026 holiday notices state:
```text
2026-10-01 through 2026-10-07 = market closed
2026-10-08 = market reopens
```

Therefore on 2026-10-04 there has not yet been a post-2026-09-30 trading session from which a new accepted target-session package could legitimately exist.

## 4. WAIT Receipts Are Not Fake Candidates
`reports/r25/ACTIVATION_CANDIDATE.json` and `ACTIVATION_PACKET_MANIFEST.json` are explicit WAIT receipts.

They contain null candidate/packet/authority/daily/dependency digests and `execution_authorized=false`. No target date is invented and no candidate authority file is created under `reports/r25/activation_candidate/`.

## 5. Independent Selection Logic｜PASS
`selection()` performs no filename, mtime, wall-clock or directory discovery for a latest session. It accepts only explicitly bound, already accepted inputs.

Missing accepted target-session input returns:
```text
WAIT_ACCEPTED_DAILY_INPUT
```

R25 is not the upstream daily-data producer and must not promote unaccepted local data.

## 6. F12 Governance｜CLOSED
R25 supersedes the weak FileNotFoundError test with an existing valid `latest.json` decoy:
```text
decoy_exists = true
decoy_internally_valid = true
decoy_differs_from_exact_binding = true
exact_binding_wins = true
FileNotFoundError = false
rejection = GRANT_DAILY_INPUT_MISMATCH
```

Therefore:
```text
R25_F12_EXPLICIT_BINDING_GOVERNANCE = CLOSED_EXTERNALLY_ACCEPTED
```

## 7. R25-01 through R25-16｜PASS
Synthetic engineering-only vectors cover target readiness, stale package, calendar/prior mismatch, digest mismatch, nested future dates, model/parameter mismatch, capability expansion, storage collision, predecessor errors, runtime-readiness backfill, candidate pre-acceptance, committed authority mutation and implicit latest decoy.

They cannot yield a real READY result.

## 8. No Runtime First-Observed Backfill｜PASS
R25 correctly separates upstream source acceptance timestamps from future runtime `first_observed_at`. No runtime readiness receipts are created.

## 9. No Real Storage Side Effect｜PASS
```text
database_created = false
database_opened = false
database_path = null
```

No real Shadow database is created.

## 10. Protected State｜PASS
```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_15_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_16_ACCEPTED_HEAD = NOT_CREATED

runtime_authorized = false
real_shadow_authorized = false
grant = null
external_acceptance = null

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
```

## 11. Clean Regression / Tested Source｜PASS
Exact tested source: `00c6168160860c29f77a570bee45578f915a4778`

The immutable tag resolves exactly to it.

Final clean regression on E::
```text
426 passed
0 failed
0 errors
0 skipped
0 deselected
```

Final HEAD is one evidence-only commit ahead.

Earlier interrupted/failed attempts are preserved with explicit dispositions.

## 12. Temporary E/F Storage Governance
The round adds an operational policy:
```text
temporary checkout / regression / test temp = E: or F:
C: project temporary allocation = forbidden
existing TDX roots = read-only
future dedicated disk = not configured
```

Historical root `AGENTS.md` was restored byte-identical. The preference is isolated in `scripts/AGENTS.md` and `config/project_workspace_storage_policy_v1.json`.

No trading algorithm semantics or accepted Stage/Data state changed.

Classification:
```text
R25_TEMPORARY_STORAGE_POLICY = PASS_OPERATIONAL_NON_STAGE
```

## 13. Retry Boundary
R25 remains open for a future target session.

Retry only when an upstream accepted target-session package exists. Earliest market-calendar opportunity is the 2026-10-08 trading session, but calendar opening alone does not create authority.

## 14. Parallel Engineering
Per REV4 §78, real-sample accumulation must not block unrelated engineering.

Therefore:
```text
V4_17_ENGINEERING_ENTRY = AUTHORIZED
```

Still not granted:
```text
V4_17_FINAL_ACCEPTANCE
V4_17G_SHADOW_STABLE_GATE
V4_18_MIGRATION_REPLAY_ACCEPTANCE
production Focus cutover
```

## 15. Final
```text
R25_EXTERNAL_AUDIT = PASS_VALID_WAIT_ACCEPTED_DAILY_INPUT

R25_NEXT = RETRY_WHEN_EXACT_ACCEPTED_TARGET_SESSION_INPUT_EXISTS
PARALLEL_NEXT = V4_17_SHADOW_UI_ENGINEERING
```
