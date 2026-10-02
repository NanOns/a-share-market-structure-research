# R10 scoped D1 runtime candidate

R10A first formalized the externally accepted Contract Freeze and created V4_12_D1_ENGINEERING_RUNTIME_R1 authorization. Exact local readback passed before runtime implementation. All 16 frozen contract files and R8/R9 evidence remain unchanged. This is engineering authorization, not Stage acceptance.

Runtime responsibilities are separated into an independent three-valued AST evaluator, exact contract/source loader, Field Registry binder, immutable Anchor/Event factory, session ledger and atomic candidate store. Runtime imports no tests, validator, FixtureExpressionVerifier or R8/R9 oracle. No business thresholds or alternative rule order are maintained in runtime code; calculations consume the frozen AST and counter/coordinate contracts.

Accepted source publications are indexed once. Blocked fields stay null/UNKNOWN with exact registry reason. Prior D1 must be the previous accepted calendar session with exact candidate manifest, entry and lineage binding; same-day or unsealed helper snapshots are rejected. Real replay deliberately bootstraps with NO_ACCEPTED_PRIOR_D1_PUBLICATION. It does not reconstruct 9/29 as accepted history.

Real replay covers all 5,224 identities in the accepted 2026-09-30 IDENTITY_UNIVERSE publication. Native price/basis fields have 5,037 KNOWN and 187 UNKNOWN (176 not adjustment-ready, 11 missing rows). Existing blocked factor/coordinate/prior capabilities result in all six output families UNKNOWN and zero new Anchor/Event candidates. This result preserves authority; it is not real capability closure.

The 69 amended independent business vectors, 12 R2 authority vectors, 33 sequence steps, 10 time-domain vectors, quality-correction membership 1→0→1, forbidden DAG and five coordinate-transition rejection cases pass. Same-date r1/r2/r3 share the previous-session baseline. The Anchor schema readback and immutable lifecycle receipts are synthetic engineering proof, with no synthetic input promoted to source authority.

A separately implemented historical fixture interpreter independently checks real output states after the runtime's own evaluation. The readback validator additionally checks source values, quality, publication/time ownership, UNKNOWN attribution, contract/parameter digests, output schemas, identities, transitions and immutable digests. Fresh subprocess replay regenerates every candidate artifact and yields exact digest equality.

Tests: 275 PASS, 0 FAIL/ERROR/SKIP, 4 deselected. The four historical R9 tests enforce its former no-runtime-diff gate and are not applicable after R10 authorization; their business/authority/counter/protected invariants are checked by the current scoped validators. No CI endorsement is claimed.

Primary machine handoff: reports/v4_12_runtime_r1/R10_RUNTIME_HANDOFF.json. Candidate manifest, independent readback, source bindings, capability matrix, schema manifest, synthetic parity and fresh rerun proof are separate artifacts. The initial synthetic constructor diagnostic is retained; the current Anchor schema-valid receipt explicitly supersedes it without rewriting the original diagnostic.

Stage remains V4_00_TO_V4_11_ACCEPTED; Data remains 2026-09-30. No formal V4_12_ACCEPTED_HEAD, migration, D2/Final State/Radar/Focus/Validation integration, V4-13 or operational cutover is authorized. After unified commit and push: STOP and wait for independent external runtime acceptance.
