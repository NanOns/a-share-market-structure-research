# R22 REV2 PRE16 external acceptance and V4-16 contract freeze - 2026-10-04

Execution baseline: `b2c3dd81c4bfed2364b6ea2693860114421f990c`, branch `codex/v4-system-reform`.
Highest scheduler: `docs/evidence/r22/V4_NEXT_ROUND_EXECUTION_MASTER_R22_REV2_20261004.md`. All six supplied cards/audits are preserved literally. The older R22 master and original task baseline are historical inputs; REV2 supplies the sole execution baseline and Phase 0 sequencing.
Applicable architecture: V4.2.2 REV4 sections 4.6-4.8, 45-49/49A/49B, 51A, 52A, 77B/77C, 78-80.

## Phase 0: independently gated mechanical formalization

Exact external PRE16 final audit SHA256: `80f9d86e8eba67125cab4708256e0b0f6d3f14c1206db2650e616465e8e72fc5`.
Audited remote head: b2c3dd81c4bfed2364b6ea2693860114421f990c. Audited tested source: dabb5eb2fcdd4b52cfa4d9d684f9d9a9786c42bf. Immutable audited tag: refs/tags/codex/pre16-gov-r1-1-tested-source-20261004-r1. External decision: PASS_FINAL_CANONICAL_BLOCK_SCOPE_REPAIR.

Created V4_PRE16_GOVERNANCE_ACCEPTED_HEAD_R1, current audit head V2 and exact authority config V2. V1 files, R1.1 code/tests and historical evidence remain unchanged. V1 readers describe the immutable historical candidate; R22 explicitly binds V2 and FinalCurrentAuditStatus. There is no latest-file discovery or implicit business authority transition.

Only GOV_PRE16_01/GOV_PRE16_02 governance acceptance dispositions close, with derived global holds removed. No other canonical issue, alias, limitation or debt changed. Current global contract-entry blockers are empty. Capability-only blocks remain Amount-A H21, historical Amount-A and A08 current PREWATCH runtime. The reader grants no permission. Independent formalization validates exact audit/source/tag/ancestry, mechanical-only transition and all protected bytes. FINALIZATION_GATE PASS_LOCAL was persisted before writing any R22 contracts, as required by REV2. This purely mechanical acceptance does not need another external audit under the supplied final audit.

## Phase 1: contract-only freeze

Created the six required contracts: realtime Shadow, observation slot, namespace, capability health, settlement worker and independent machine vectors. A package exact-binds all contracts, the supplementary slot/health field registry, accepted V4-15 predecessor, Data/Stage/current-stage authority, accepted calendar/cohort/settlement/parameter policies, formalized governance authority, canonical issue map and blocker matrix. Existing V4-15 identity and settlement schemas/formulas are inherited, not reimplemented.

Frozen design covers origin/mode enums, source/provider/system/computation/acceptance timestamps, real input manifest freeze, first on-time slot enrollment, same-day correction, exact previous-market-session Shadow state, model/parameter identity boundaries, namespace/date locking, atomic publication/manifest/cohort/outbox/head CAS, outbox idempotency and retry, accepted-only due source, revision/readback, capability-scoped health, daily industry/concept/type membership capture, optional BaoStock/FEP isolation, Legacy isolation and stop/rollback preservation. Focus, UI caps, manual pin and visibility do not select the cohort or stop settlement. Original T0, controls, benchmark and FIRST_OBSERVED remain frozen.

Amount-A formal consumers and A08 current-runtime PREWATCH are not active in Shadow. Their capability debts do not block unrelated contract design. Marked benchmark numeric gates and sector/rotation provisional minima remain unassigned; no new business threshold was invented. The 20-real-session stability rule and 5 dates/30 positive stock events/T5 rule are inherited from accepted REV4 section 52A, are counters only, and are not declared passed. Engineering work does not wait for real accumulation.

## Explicit clock capability limitation

The accepted foundation receipt, Stage authority, V4-15 cohort/field registry and parameter registry do not contain a complete accepted daily scheduled cutoff and observation publication deadline. The accepted cohort delegates this to V4-00C and explicitly blocks realtime enrollment when unset. CUTOFF_AUTHORITY_INVENTORY records the pinned search and exact reviewed evidence.

V4_16_OBSERVATION_SLOT_CONTRACT=BLOCKED_AFFECTED_SCOPE. scheduled_cutoff_at, observation_deadline and accepted_clock_binding remain null. R22_CLOCK_AUTHORITY_REPAIR_01 is a separate versioned P0 affected-scope contract-repair item. It blocks actual observation slot/original realtime enrollment, without reviving the closed PRE16 global contract-engineering blocker. No convenient cutoff was chosen. The conditional on-time vector describes only a future authorized runtime with a separately accepted clock; it supplies no current PIT or maturity evidence.

## Validation and immutable source

Independent Phase 0 oracle does not call the writer. Independent R22 oracle does not import contract builder or runtime evaluators; its expected vectors are authored as literal policy requirements. Twenty-three frozen vectors cover all twenty requested families and additionally unset clock, retained governance capability debt and engineering-only maturity. None were executed as real Shadow observations.

Local regression: 199 passed; clean detached regression: 199 passed; zero failures/errors/skips/deselections. All original PRE16/R21 tests remain included, including explicit V4-14 replay compatibility, V4-15 current authority/promotion/rollback, plus new mechanical acceptance, contract, vector and protected-boundary tests. The clean checkout verified 171 LFS objects and only already registered R20B historical byte representations. Git status was clean before and after tests.

Tested source: 2456f6cdae99431bb475f077d4eaccd5f24c3b75. Immutable ref: refs/tags/codex/r22-contract-tested-source-20261004-r1. The final evidence-only commit follows this source; implementations/configs/heads remain identical. Branch and source-tag remote identities are checked after atomic push. A push does not accept the R22 contract externally or grant runtime permission.

## Protected exit

All 51 literal protected bindings remain unchanged. Every existing baseline artifact remains unchanged except additive exact-byte Git attributes for new evidence; all business src, R20/R20R1/R20R1R1/R20R1R2/R21 and historical registries remain intact. TDX inputs were not written. Unrelated FEP work is preserved.

PRE16_GOVERNANCE=EXTERNALLY_ACCEPTED_FORMALIZED.
GLOBAL_V4_16_CONTRACT_ENTRY_BLOCKERS=[].
R22_V4_16_CONTRACT_FREEZE_ENTRY=PASS_LOCAL.
V4_16_CONTRACT_COMPLETENESS=PASS_READY_FOR_EXTERNAL_AUDIT, with the clock capability expressly blocked.
V4_16_RUNTIME=NOT_AUTHORIZED. REAL_SHADOW_OBSERVATIONS=0. V4_16_ACCEPTED_HEAD=NOT_CREATED.
V4_10_TO_V4_15=PASS_KEEP_NO_REOPEN. Stage=V4_00_TO_V4_15_ACCEPTED. Data=2026-09-30.
Production=false, Shadow=false, Focus=false, V4_16=false; default UI and Legacy production remain unchanged.
Historical PIT, real matured settlement, realtime maturity, SHADOW_STABLE, PROVISIONAL_FORWARD_EVIDENCE and FORWARD_SUPPORTED are not granted. PROVED_HORIZONS=[], UNPROVED_HORIZONS=[1,3,5,10,20].

NEXT=STOP_WAIT_R22_INDEPENDENT_EXTERNAL_AUDIT.
