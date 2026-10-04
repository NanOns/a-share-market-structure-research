# PRE16 GOV R1.1 canonical issue and blocking-scope repair - 2026-10-04

Execution baseline: `0109d7f6c8b9f4cea6cde32b2342e4b6d4e0526b`, branch `codex/v4-system-reform`.
Highest dispatch card: `reports/pre16_governance/r1_1_inputs/V4_NEXT_ROUND_EXECUTION_MASTER_PRE16_GOV_R1_1_20261004.md`. Task and independent external audit are preserved literally in the same directory. Applicable architecture: V4.2.2 REV4 section 79, affected successor scope only.

## Problem and result

The externally audited PRE16 core remains PASS_KEEP. GOV_PRE16_02 found contradictory Shadow-blocking labels on two representations of one Amount-A H21 formal-consumer issue. The repair changes only PRE16 governance metadata, builder, reader, oracle, tests and evidence. Current audit head and config are version 1.1.0, with literal archived previous versions and exact supersession bindings. Prior R1 evidence is preserved.

`PRE16_GOV_R1_1 = PASS_LOCAL`.
`GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS = [GOV_PRE16_01]`.
`AMOUNT_A_H21 = ONE_CANONICAL_CURRENT_ISSUE`.

A04_H21_CONSUMER is canonical. AUD_A04_AMOUNT_A_FORWARD_CONSUMER is an explicit alias; its state, scope, limitations, dimensions, accumulation requirement and blocking semantics are identical to the canonical entry. Alias-specific historical evidence and original descriptive metadata remain provenance. There are 35 canonical issues and one alias reference.

Each issue independently specifies global contract-entry hold, declared global runtime-activation hold, affected-capability Shadow hold, scoped production-cutover hold, scope class and affected capabilities. Legacy blocks_shadow_entry is derived as global runtime hold OR affected-capability Shadow hold; it does not imply that all Shadow work is blocked. Legacy engineering and production flags are similarly derived.

Amount-A H21 and historical Amount-A are CAPABILITY_ONLY blocks. A08_CURRENT_RUNTIME does not block contract entry; its PREWATCH capability remains blocked in Shadow pending separate external acceptance. This round does not invent an unfrozen global V4-16 runtime dependency on A08: future contracts must bind required capabilities explicitly. GOV_PRE16_01 remains the only declared global contract-entry and activation hold. No reader query grants any permission.

## Independent verification and evidence

The independent oracle imports neither the builder nor business evaluators. It resolves and rejects alias cycles, missing targets, duplicate/conflicting canonical identity, inconsistent alias state/block semantics, incomplete schema and unjustified global blockers. It compares the complete audited core and exact scoped authority with the immutable audited baseline, and retains current-runtime open status, Amount-A consumer restrictions, PIT limitations and real-maturity debts.

CurrentAuditStatus exposes global_contract_entry_blockers(), runtime_activation_blockers(), capability_shadow_blockers(), production_cutover_blockers() and canonical_entry(). Queries return deterministic, deduplicated canonical IDs or copied entries. Contradictory aliases fail closed; stage_permission() remains false.

Consumer rescans cover both the pinned baseline and all tracked files at the tested source. No current runtime consumer of stale R1 or unresolved source reference was found. All business sources are unchanged.

Local and clean detached regression each passed 114 cases: all original PRE16 and R21 tests plus canonical identity, alias graph, blocker scope, missing schema, copy isolation and no-permission negative tests. Zero failures, errors, skips or deselections. The clean checkout verified 171 LFS objects and the existing path-specific R20B byte representations; it was clean before and after testing. No historical or binary normalization policy changed. The evidence namespace has its own exact-byte Git attributes.

Tested source: `dabb5eb2fcdd4b52cfa4d9d684f9d9a9786c42bf`.
Immutable ref: `refs/tags/codex/pre16-gov-r1-1-tested-source-20261004-r1`.
The final evidence-only commit follows this source; implementation, config and head bytes do not drift. Branch and tag remote identities are checked after the atomic push. Push is not external acceptance.

GOV_PRE16_02 is separately tracked as CLOSED_LOCAL_PENDING_INDEPENDENT_EXTERNAL_AUDIT in its repair-disposition artifact. This does not close GOV_PRE16_01 or reopen any accepted business stage.

## Frozen exit

V4_10_TO_V4_15=PASS_KEEP_NO_REOPEN. Stage remains V4_00_TO_V4_15_ACCEPTED; current stage authority remains V4_15; Data Head remains 2026-09-30. All 51 protected literal bindings remain unchanged, including Stage/Data, V4-10 through V4-15 heads, CurrentStageAuthority and historical registries. Production=false, Shadow=false, Focus=false, V4_16=false. No R22/V4-16, DB migration, TDX input modification or business runtime changes occurred.

NEXT=STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT.
