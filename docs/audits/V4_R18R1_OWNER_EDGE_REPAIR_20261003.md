# R18R1 owner-edge repair disposition

Execution baseline: `70fc9b050497e798d077480d0ae4adf97e9824c6`.
Authority: the five exact imported documents under `docs/evidence/r18r1`, with the R18R1 master as scheduler. Execution order was A, B, C. No promotion is authorized.

## Separate cross-cutting audit items

| Item | Scope | Evidence | Local acceptance |
|---|---|---|---|
| G01 / P0 | Complete frozen owner and replay edge closure | A completion gate; r4 publications with 30 receipts each | All 24 owner edges and 6 required replay edges accounted for exactly once |
| G02 / P0 | Independent expected edges and adversarial verification | C `independent_edge_oracle_gate_r2.json`; edge tests and canonical tests | Expected sets constructed directly from frozen DAG; 10 new mandatory mutations plus inherited 16 checked |
| G03 / P1 | Unique current Full-DAG evidence authority | `reports/r18r1b/final_full_dag_gate.json` | Only r4 is current; all three old attempts are immutable and superseded |

These are local repairs awaiting independent external audit. Test success is not release acceptance.

## Execution and capability meaning

The harness calls accepted Seed, PREWATCH, B0, Rotation B1, legacy B2, Confirmation, Structure, State Reducer, Event Diff and Profile/Context owner implementations. It adds orchestration and receipts, without modifying accepted business algorithms or thresholds. The original 60-vector runtime and OS process launcher remain unchanged.

F0 engineering facts explicitly bind frozen owner books. C consumes the replayed A result. C to D0 is read-only PREWATCH lineage transported into the actual sealed confirmation input digest, without adding a detector predicate. Engineering confirmation facts are identified by the frozen fixture package, not claimed as market observations.

B0, B1 and B2 run their accepted owner logic with missing native/prior coverage and return UNKNOWN. Their edges are degraded. D1 to D2 uses the accepted V4-11 declared unavailable structure capability; it does not invent structure confirmation. D1 profile transport and Context dependencies retain degradation where full accepted projection, non-target native history or historical membership is unavailable. Generic receipt delivery records each producer and consumer binding; it does not upgrade a degraded business capability to KNOWN.

The 22-session r4 trajectory uses persisted publications and distinct OS processes. Each next process starts after producer exit and reads the exact previous market session. The final same-day r1/r2 and identical-input repeat all bind the same exact previous session. State counters, episode continuity, event suppression and deterministic output are checked independently.

## Canonical evidence and immutable history

`reports/r18r1b/final_full_dag_gate.json` is the sole Full-DAG authority consumed by C and the final seal. `full_dag`, `full_dag_r2`, and `full_dag_r3` retain their original bytes and are historical attempts. The first local C oracle gate is superseded by `independent_edge_oracle_gate_r2.json`, which includes the extended availability and canonical perturbation checks; it is not a final authority.

Real evidence is exact readback of the accepted r6 candidate and the retained real process/publication receipts. It remains REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED, AS_RECORDED=false, RECONSTRUCTED_CORRECTED. Synthetic closure grants no historical PIT effectiveness. HISTORICAL_PIT_EFFECTIVENESS remains NOT_GRANTED.

## Final gate

The final candidate seal binds tested detached source SHA, clean regression totals, canonical r4 gate, independent oracle, real readback, exact protected heads and permissions. AGENTS and all five protected heads remain byte-identical. No V4-14 Accepted Head is created, no Stage/Data head advances, and algorithm replay acceptance remains NOT_GRANTED_PENDING_EXTERNAL_AUDIT.

NEXT: STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT after unified commit and push.
