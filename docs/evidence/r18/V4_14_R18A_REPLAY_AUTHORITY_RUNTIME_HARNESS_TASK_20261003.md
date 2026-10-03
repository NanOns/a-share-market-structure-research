# R18A｜V4-14 Replay Authority / Runtime Harness｜2026-10-03

## 0. Baseline
Use current remote HEAD:
`47b7f72f374c059f35a66bf2fe298a3ec5fe7efc`

Read:
- `V4_R17R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- `V4_14_R18A_REPLAY_AUTHORITY_RUNTIME_HARNESS_TASK_20261003.md`
- `V4_NEXT_ROUND_EXECUTION_MASTER_R18_20261003.md`

The only V4-14 contract authority is the R17R1 v1.1 package.

## 1. Goal
Implement a V4-14 replay runtime harness that executes the already accepted owner contracts without redefining their business algorithms.

Create a dedicated runtime namespace, recommended:
- `src/workbench_analysis/v4_14_replay_io.py`
- `src/workbench_analysis/v4_14_authority.py`
- `src/workbench_analysis/v4_14_replay_runtime.py`
- `src/workbench_analysis/v4_14_publication.py`

Exact filenames may follow repository conventions.

## 2. Authority Resolver
Runtime must bind exact:
- amended V4-13 Accepted Head;
- V4-14 v1.1 contract-freeze package;
- V4-07 through V4-13 accepted owners;
- Data Head;
- exact market calendar;
- exact accepted PIT membership where applicable.

The resolver must:
- reject superseded contract-family members in current/runtime roles;
- reuse `ACTIVE_CONTRACT_FAMILY_CLOSURE`;
- fail closed on path/hash/bytes mismatch;
- never directory-scan for “latest”;
- never use raw/provider fallback.

## 3. No Algorithm Duplication
V4-14 is an orchestration/replay gate.

Do not reimplement V4-08/V4-09/V4-10/V4-11/V4-12/V4-13 business rules inside V4-14.

Where owner runtime helpers exist, invoke them directly or through frozen adapters.

Where only accepted persisted publications exist, consume the exact accepted owner output.

Every replay record must identify:
- owner contract;
- owner source ref;
- target date;
- previous market session;
- input digest;
- output digest;
- quality/degradation result.

## 4. Canonical Replay Input
Create a frozen replay input envelope containing at minimum:
- target trade date;
- exact previous accepted market session;
- target revision;
- cutoff;
- accepted Data Head ref;
- accepted Stage Head ref;
- exact owner refs;
- exact previous-state publication refs;
- market calendar ref;
- PIT membership ref if applicable;
- evidence class;
- source availability metadata.

No implicit local state is allowed.

## 5. Execution Topology
Runtime must respect accepted DAG ordering.

At minimum:
```text
F0/Core
→ A Seed
→ B0/B1/B2 Sector/Rotation
→ C PREWATCH
→ D0 Confirmation
→ D1 Structure
→ D2 State Reducer
→ EVENT_DIFF
→ D3 Profile/Context readback
→ Gate-B observation
```

Use the actual accepted DAG names/edges from the v1.1 V4-14 package.

All forbidden same-day feedback paths remain blocked.

## 6. 17 Dimension Evaluators
Implement runtime checks for all frozen dimensions:
- same_day_feedback;
- state_transition_legality;
- hysteresis;
- expiry;
- direct_prewatch_confirmed;
- rotation_pulse_accepted_failed;
- support_reclaim_retest_break;
- confirmation_persistent_suppression;
- multi_sector_dedup;
- unknown_propagation;
- no_duplicate_event_episode;
- same_day_revision_predecessor;
- cross_process_previous_session;
- future_publication_leakage;
- revision_append_only;
- deterministic_replay;
- historical_pit_evidence.

Runtime expected values must come from the frozen hand-authored vectors/oracle books, not from the runtime implementation itself.

## 7. Synthetic Runtime Gate
Execute all frozen positive/negative V4-14 vectors.

Required:
```text
all positive vectors -> admitted with exact expected behavior
all negative vectors -> rejected with exact frozen reason
```

No vector may be silently skipped because a real upstream capability is unavailable.

Synthetic engineering evidence is independent from real capability evidence.

## 8. Output / Publication
Create append-only replay publications under a dedicated namespace.

Each revision must have:
- opaque replay publication ID;
- target date;
- revision;
- previous-session ref;
- exact contract-package digest;
- exact input digest;
- output digest;
- dimension results;
- source refs;
- evidence class;
- quality/degradation summary.

Changed-byte overwrite of an existing revision must fail closed.

## 9. Forbidden
- V4_14_ACCEPTED_HEAD
- Stage Head advance
- Data Head advance
- ALGORITHM_STATE_REPLAY_PASS
- Production / Shadow / Focus
- V4-15
- DB migration
- algorithm threshold changes
- raw/provider fallback

## 10. Completion
```text
R18A_V4_14_RUNTIME_HARNESS = PASS_LOCAL
V4_14_SYNTHETIC_VECTOR_RUNTIME = PASS_LOCAL
V4_14_RUNTIME_CANDIDATE = IMPLEMENTED_NOT_YET_EXTERNALLY_ACCEPTED
NEXT = R18B_CROSS_PROCESS_FULL_DAG_REPLAY
```

Continue directly to R18B.
