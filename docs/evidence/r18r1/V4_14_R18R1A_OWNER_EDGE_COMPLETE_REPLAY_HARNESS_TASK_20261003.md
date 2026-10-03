# R18R1A｜V4-14 Owner-edge Complete Replay Harness｜2026-10-03

## 0. Baseline
Use current remote HEAD:
`70fc9b050497e798d077480d0ae4adf97e9824c6`

Read:
- `V4_R18_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md`
- this task card
- `V4_NEXT_ROUND_EXECUTION_MASTER_R18R1_20261003.md`

## 1. KEEP
Do not reopen:
- R18A ReplayRuntime vector evaluator;
- all 60 frozen vectors / 17 dimensions;
- R17R1 active-family closure;
- V4-14 v1.1 contracts;
- accepted V4-08..V4-13 business algorithms;
- existing cross-process launcher;
- append-only publication;
- current V4-13 / Stage / Data heads.

## 2. Goal
Repair the meaning of `FULL_DAG`.

A Full-DAG replay is complete only when every applicable edge in:
`config/v4_14_temporal_non_edge_registry_v1_1.json`
is represented by a machine-readable replay edge receipt.

Expected authority:
`owner_edges + replay_required_edges`
after canonical-node normalization.

## 3. Edge Receipt Contract
Add a frozen runtime edge-receipt schema.

Each receipt must include:
```text
edge_id
producer
consumer
field
time_role
owner_contract_id
owner_head_ref
owner_contract_ref
target_trade_date
previous_market_session
input_ref / input_digest
output_ref / output_digest
execution_mode
quality
status
reason
source_trade_date
available_at / knowledge-time metadata when applicable
```

Allowed status:
```text
EXECUTED
DEGRADED_ACCEPTED_CAPABILITY
NOT_APPLICABLE_BY_FROZEN_CONTRACT
```

Forbidden:
```text
SKIPPED_WITHOUT_REASON
HARDCODED_DOWNSTREAM_SUBSTITUTE
RAW_PROVIDER_FALLBACK
```

## 4. Explicit B0/B1/B2
The repaired replay must separately represent:
```text
F0 -> B0
A  -> B0
B0 -> B1
B0 -> B2
```

Do not use a single `Sector/Rotation` node as proof.

Where frozen owner vectors/AST exist, execute them.
Where accepted capability is unavailable, emit `DEGRADED_ACCEPTED_CAPABILITY` with exact accepted-head reason.
Do not manufacture KNOWN values.

## 5. C / D0
Prove:
```text
F0 -> C
A  -> C
C  -> D0
```

PREWATCH inputs must be traceable to frozen producer outputs or explicit frozen fixtures.
D0 must consume replayed C lineage or an explicit accepted frozen adapter mapping.
Do not call an unrelated positive fixture and merely label the trace `C -> D0`.

## 6. D1 / D2 / Event
Prove:
```text
F0 -> D1
D1(T-1) -> D1
D0 -> D2
D1 -> D2
C  -> D2
D2(T-1) -> D2
D0 -> EVENT_DIFF
D2 -> EVENT_DIFF
D2(T-1) -> EVENT_DIFF
```

Every edge needs a receipt.

## 7. Context / Profile
Explicitly cover:
```text
B0 -> CONTEXT
B1(T-1) -> CONTEXT
B2 -> CONTEXT
MEMBERSHIP -> CONTEXT
CORE_V4_04 -> CONTEXT
NATIVE_V4_05 -> CONTEXT
BASE_SEED_V4_07 -> CONTEXT
B1 -> CONTEXT
D1 -> PROFILE
CONTEXT -> PROFILE
D1 -> D3 enrichment
```

Unavailable historical/real capabilities may remain UNKNOWN/DEGRADED.
Missing evidence is not permission to omit the edge.

## 8. Downstream Input Rule
Every current downstream input must be one of:
1. exact replay producer output;
2. exact frozen owner vector output;
3. explicit accepted-capability degradation;
4. explicit NOT_APPLICABLE.

Hard-coded business input values are forbidden unless the frozen fixture itself is cited as producer evidence.

## 9. Full-DAG Completeness Gate
Produce:
```text
expected_active_edges
executed_edges
degraded_edges
not_applicable_edges
missing_edges
unexpected_edges
```

Required:
```text
missing_edges = []
unexpected_edges = []
EXPECTED_EDGE_SET == EXECUTED ∪ DEGRADED ∪ NOT_APPLICABLE
```

## 10. Forbidden
- V4_14_ACCEPTED_HEAD
- Stage/Data advance
- ALGORITHM_STATE_REPLAY_PASS
- owner algorithm redesign
- threshold redesign
- raw/provider fallback
- Production/Shadow/Focus
- V4-15

## 11. Completion
```text
R18R1A_OWNER_EDGE_COMPLETE_HARNESS = PASS_LOCAL
FULL_DAG_EDGE_SCHEMA = FROZEN
OWNER_EDGE_COMPLETENESS_LOCAL = PASS
NEXT = R18R1B_CROSS_PROCESS_R4
```

Continue directly to R18R1B.
