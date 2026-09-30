# V4-08 R5.2 closure — 2026-09-30

Status `V4_08_R5_2_READY_FOR_EXTERNAL_REAUDIT`. Tested implementation `b7d904cbff4f1c4b877838bd129f3925f968d858`. Engineering candidate only, independent external reaudit pending; stop at this boundary. V4-08 global promotion and V4-09 integrated acceptance are not authorized.

## B04 — accepted input authority

PASS_ENGINEERING_CONTEXT_ROUTING. Contract `V4_08_ACCEPTED_INPUT_CONTEXT_R5_2`, adapter `V4_08_ACCEPTED_INPUT_ADAPTER_R5_2`. load_accepted_current requires an explicit accepted_input_context; it has no fixed V4-02 authority paths or fixed trade date. A deep-copied context freezes context_id, accepted_trade_date, raw_daily and adjusted_price byte/source/logical digests, availability, capability, revision/coordinate semantics, and governance head/parent/publication identities. Governance identities use accepted CANONICAL_JSON_SHA256_V1; binary artifacts use raw SHA256.

Daily caller route: existing `data/v4/V4_DATA_ACCEPTED_HEAD.json` -> SHA-bound immutable manifest.accepted_input_context. The loader validates exact manifest source bindings, permission gates, parent and revision identities. No fourth daily authority, scheduler, collector or DM-01 rewrite. A future accepted publication supplies this versioned context payload; the current bootstrap has no same-session pair at 9/30 and remains unavailable. Fixed V4-02 baseline reading exists only in the explicitly separate caller-only STATIC_ENGINEERING_BASELINE_CONTEXT factory: ENGINEERING_REPLAY_ONLY, daily_production_authority=false. It is not the daily caller route or a fallback.

Same adapter source runs T/T+1 with different targets, immutable paths, SHA, amounts and price snapshots. The multi-context test creates no data/v4 head or static V4-02 head and asserts source bytes unchanged. Separate Daily Head tests advance only a TEST_ONLY moving pointer. Frozen T result and digest survive T+1 artifact/context changes and T replays exactly. Negative vectors cover stale/future context, future availability, byte/logical mismatches, BLOCKED components and caller source override rejection. Independent Core values survive unavailable/blocked amount or price.

## B05 — source decision B, explicit capability downgrade

B2_NON_AMOUNT_A = NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE.
B2_AMOUNT_A = DIAGNOSTIC_AUDIT_OPEN.
Formal confirmed_raw = UNKNOWN; warm_raw = UNKNOWN.

Legacy exact producer remains phase2.prepare: symbol format AND missing_state known AND not FILE_MISSING/DELISTED_OR_INACTIVE, followed by phase2.validity(total, valid, role). Actual accepted factor inventory has 47 fields across 5222 rows, and 0 legacy_valid_member rows. Factor/profile/canonical/trading-status schemas do not provide exact legacy missing_state provenance. Actual bar presence, research universe, canonical identity, trading_status and PIT membership are not substituted for that rule. No new factor field or guessed equivalence producer is created.

The adapter ignores an injected final legacy_valid_member boolean and produces an explicit unavailable placeholder. evaluate_b2 removes ENABLED_ENGINEERING, returns formal UNKNOWN and an unavailable predicate reason. confirmed_diagnostic preserves the pure algorithm result for explicit diagnostics only; it grants no formal qualification. Mixed-semantic rank logic and AST are unchanged and still tested as pure algorithm units; those vectors are not evidence of an accepted producer. The B05 formal-chain test starts from SHA-bound source-shaped artifacts and proves final-boolean injection cannot enable B2.

V4-08 engineering candidate scope includes independent Sector Native/B0/B1 and EXCLUDES legacy B2 confirmed/warm. Choosing B resolves the capability overclaim for this gate; future exact missing-state provenance/producer implementation remains independently outstanding. Prior-RPS and AUD-AMOUNT-A-06 retain independent OPEN scope/evidence/acceptance; nothing here closes them.

## Real 9/30 and clean evidence

V4_DATA_ACCEPTED_HEAD accepted_trade_date = 2026-09-24; target = 2026-09-30. Availability TARGET_ACCEPTED_DATA_UNAVAILABLE; static fallback false. Target accepted Core count 0. Each namespace has 378 rows; distributions `{"B0": {"UNKNOWN": 378}, "B2": {"UNKNOWN": 378}, "ROTATION": {"UNKNOWN": 378}}`. No 9/28 relabel, threshold relaxation, forced FALSE or fabricated signals.

Targeted tests 68 PASS. Clean detached checkout: 711 total, 709 passed, 2 skipped, 0 failures/errors. Candidate reproduction leaves tracked checkout clean. Disposable PostgreSQL 18.6; 1512 exact readback rows, idempotency and append-only guards PASS; process DSN; config/.env absent/not read; cluster destroyed. NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC PASS, hard_gated_equity_symbol_hits=0, unclassified_paths=[].

Protected stage/data/dev/PIT heads, retention parameters, Native formulas, Rotation state machine and migrations are unchanged relative to c853f0ce. No V4_08_ACCEPTED_HEAD; global range remains V4_00_TO_V4_07_ACCEPTED; production_permission=false. Existing unrelated FEP worktree artifacts excluded. Final seal is evidence-only and pushed HEAD is reported in the delivery message.

## Changed paths

- `config/v4_08_accepted_context_contract_r5_2.json`
- `data/v4/artifact_store/v4_08/V4_08_R5_B0_20260930_bb8d0c0929f531e8cddf.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_B2_20260930_bb8d0c0929f531e8cddf.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_ROTATION_20260930_bb8d0c0929f531e8cddf.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_SECTOR_NATIVE_20260930_bb8d0c0929f531e8cddf.jsonl.gz`
- `docs/evidence/V4_08_R5_1_INDEPENDENT_EXTERNAL_REAUDIT_R2_20260930.md`
- `docs/evidence/V4_08_R5_2_FINAL_INPUT_AUTHORITY_AND_LEGACY_VALID_MEMBER_REPAIR_TASK_20260930.md`
- `reports/v4_08/V4_08_R5_2_ACCEPTED_CONTEXT_CONTRACT.json`
- `reports/v4_08/V4_08_R5_2_B2_CAPABILITY_DOWNGRADE.json`
- `reports/v4_08/V4_08_R5_2_DAILY_HEAD_ROUTING.json`
- `reports/v4_08/V4_08_R5_2_FROZEN_CONTEXT_IMMUTABILITY.json`
- `reports/v4_08/V4_08_R5_2_LEGACY_VALID_MEMBER_SOURCE_DECISION.json`
- `reports/v4_08/V4_08_R5_2_MULTI_CONTEXT_GENERALIZATION.json`
- `reports/v4_08/V4_08_R5_2_STAGE_CANDIDATE_MANIFEST.json`
- `reports/v4_08/V4_08_R5_2_STAGE_ENTRY.md`
- `reports/v4_08/V4_08_R5_B0_FULL_MARKET.json`
- `reports/v4_08/V4_08_R5_B0_IMPLEMENTATION.json`
- `reports/v4_08/V4_08_R5_B2_FULL_MARKET.json`
- `reports/v4_08/V4_08_R5_ROTATION_FULL_MARKET.json`
- `reports/v4_08/V4_08_R5_ROTATION_IMPLEMENTATION.json`
- `reports/v4_08/V4_08_R5_SECTOR_NATIVE_FULL_MARKET.json`
- `reports/v4_08/V4_08_R5_SECTOR_NATIVE_IMPLEMENTATION.json`
- `reports/v4_08/V4_08_R5_STAGE_CANDIDATE_MANIFEST.json`
- `scripts/materialize_v4_08_r5.py`
- `scripts/run_v4_08_r5_2_isolated_verification.py`
- `scripts/verify_v4_08_r5_2.py`
- `scripts/verify_v4_08_r5_algorithms.py`
- `src/sector/accepted_context_r5_2.py`
- `src/sector/accepted_input_r5_1.py`
- `src/sector/legacy_b2_r5.py`
- `tests/v4_08/test_r5_1_accepted_adapter.py`
- `tests/v4_08/test_r5_2_context_authority.py`
- `tests/v4_08/test_r5_runtime.py`

Final evidence-only seal adds/updates R5.2 clean/schema/scan receipts, closure, stage entry, candidate manifest and external handoff.
