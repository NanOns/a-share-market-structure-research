# R18B｜V4-14 Cross-process Persisted Full-DAG Replay E2E｜2026-10-03

## 0. Entry
Execute only after:
```text
R18A_V4_14_RUNTIME_HARNESS = PASS_LOCAL
```

## 1. Goal
Prove complete replay continuity across separate processes and same-day revisions using persisted artifacts, not in-memory continuity.

## 2. Mandatory Cross-process Sequence
For a chosen replay pair T-1 -> T:

```text
T-1 producer process
→ persist immutable owner/replay publication
→ record PID and exit
→ verify process exited
→ start fresh T process with different PID
→ exact T-1 publication readback
→ verify SHA/bytes/date/calendar
→ execute T replay
→ persist T revision
```

Must record:
- producer_pid;
- consumer_pid;
- producer_exit_at;
- consumer_start_at;
- previous_market_session;
- previous publication path/hash/bytes;
- readback path/hash/bytes;
- calendar binding;
- no in-memory prior use.

## 3. Same-day Revision E2E
For target T:

```text
T r1
T r2
```

Both must bind the same exact previous-market-session publication.

Forbidden:
```text
T r1 -> T r2 as previous-session state
```

Required:
- r1/r2 append-only;
- old revision unchanged;
- same previous date;
- same previous manifest digest;
- event classification stable under correction where frozen contract requires it;
- no fabricated extra market session;
- no duplicate logical episode/event caused by revision number.

## 4. Full-DAG Replay
The E2E must exercise:
- accepted source binding;
- Seed;
- Sector/Rotation;
- PREWATCH;
- Confirmation;
- Structure;
- State reducer;
- event diff;
- Profile/Context readback;
- Gate-B observation.

Where an accepted real owner capability is unavailable, preserve component-scoped UNKNOWN/DEGRADED and continue unrelated components.

Do not replace unavailable accepted data with raw/provider data.

## 5. State / Episode / Event Identity
Prove:
- legal continuation keeps episode ID;
- hard exit follows owner contract;
- reentry creates a new child episode only when owner rules authorize;
- persistent confirmation creates no duplicate actionable event;
- multi-sector context does not duplicate one logical stock event;
- same-day correction does not create a second logical event merely because revision changed.

## 6. Hysteresis / Expiry
Use accepted V4-10 state-reducer authority and parameters.

Replay must independently demonstrate at least:
- one-session downgrade is held by hysteresis;
- contract-defined second evaluable session permits downgrade;
- expiry advances only on evaluable sessions;
- same-day revision does not advance expiry counters;
- required UNKNOWN pauses the relevant counter per owner contract;
- stage upgrade/reset semantics match the accepted owner.

## 7. Structure Lifecycle
Use accepted V4-12 owner runtime/publications to demonstrate:
- support test;
- reclaim;
- retest;
- break;
- anchor identity retention;
- duplicate anchor/event protection;
- previous-session-only D1 lineage.

Do not recreate structure logic in V4-14.

## 8. Determinism
Run the same frozen replay input twice in fresh processes.

Required:
```text
same input digest
same owner refs
same previous-state ref
=> same replay output digest
```

No duplicate side effects.

## 9. Persisted Evidence
Produce immutable R18B evidence for:
- cross-process sequence;
- same-day revision chain;
- full DAG trace;
- event/episode identity;
- hysteresis/expiry;
- structure lifecycle;
- deterministic replay;
- source refs and capability degradations.

## 10. Forbidden
Same as R18A, plus:
- using one-process loops as proof of cross-process replay;
- replacing exact T-1 with “latest”;
- treating r1 as predecessor of r2;
- fabricating known values for unavailable accepted capabilities.

## 11. Completion
```text
R18B_CROSS_PROCESS_FULL_DAG_REPLAY = PASS_LOCAL
CROSS_PROCESS_PREVIOUS_SESSION = PASS
SAME_DAY_REVISION_ISOLATION = PASS
FULL_DAG_PERSISTED_REPLAY = PASS_LOCAL
NEXT = R18C_INDEPENDENT_ORACLE_REAL_SCOPED_SEAL
```

Continue directly to R18C.
