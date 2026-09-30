# V4-08 R5.1 closure — 2026-09-30

Status: `V4_08_R5_1_READY_FOR_EXTERNAL_REAUDIT`. Tested implementation: `d4d2e861bf99ef2867a6579345a156fe18b6f5b5`. Engineering candidate only; independent external acceptance remains pending. Stop here for independent reaudit; V4-09 entry and Sector/Rotation production permission are not granted.

## Three repair results

R5-B01 PASS: normal_rank_eligible comes from exact legacy resolve_semantics, not a type constant. sector_valid producer is phase2.prepare -> sectors -> validity. Mapping uses exact accepted legacy_valid_member observations with producer version sector-factor-contract-v1.1-correctness; formal PIT membership never implies legacy validity. Missing exact observations remain UNKNOWN. EXCLUDED_ROLE independently proves false. Any unknown eligibility makes the affected type pool UNKNOWN. Known eligibility uses total_normal and finite-rel1 valid_count exactly as legacy; excluded high-rel1 sectors do not enter denominator or receive p1. The mixed direct build_sector_current comparison includes normal, excluded, invalid and explicit UNKNOWN_TAG records. Explicit UNKNOWN_TAG is a known legacy exclusion; missing provenance is separately verified as UNKNOWN.

- `config/sector_semantics.yaml`: `e0b133f2ff37c5480d3683ee283ccb976d8da69d1eca886ca8a4e9daf0f77303` (workbench-semantic-v2.1)
- `config/sector_roles.yaml`: `98cb07c5b2ec0e22f2ff5e788d8130319f672ef89df7fdef6f7614aa92ed2975` (sector-role-v0.1)
- `src/workbench_service/semantic.py`: `116e91557d403c37512d153506d40b6b0aedb9dca594769720345f7a87821cb0` (workbench-semantic-v2.1)
- `src/sector/roles.py`: `fd361e8b2410871505a5e48db250e9c0c31343b7c14ca34667d246d4d874b17a` (sector-role-v0.1)
- `src/sector/phase2.py`: `9455bae1578c4a785e034eb0ff852dcd98d7218a66027e0ea3f11489fd3727a1` (sector-factor-contract-v1.1-correctness)
- `src/workbench_service/strength_association.py`: `f9a39a9bc100e932fa04f32c46bf3aa62287b6a358382d4f6b01e4b02084be29` (semantic-keyword-dependency-r5.1)
- `src/sector/semantic_input_r5_1.py`: `f8760dd0420e803ff28915afd43a9ff54635dde6a16f1fa515a05c7b0193cde4` (V4_08_B2_SEMANTIC_MAPPING_R5_1)

Semantic dependency digest: `722bda6bfb247f7d7b4a0ce5de3928d2b3458393ff96e77fd8cedee53f37d828`. Adapter/model digest: `bb0ef9611c01db2cfd493a82037fb20f64aad15fba0c7e8e7433a0f5d28f11da`. YAML declarations and exact runtime producer dependencies are frozen together; no new semantic override behavior was introduced.

R5-B02 PASS: raw CNY amount is bound through `data/v4/V4_02_ACCEPTED_HEAD.json` -> accepted manifest DAILY_R7 -> `data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet`. Artifact SHA `d8e2202f00909ade115315aefe92c810ba5e96f0520472e799da21390ea0ad90`; source digest `d8e2202f00909ade115315aefe92c810ba5e96f0520472e799da21390ea0ad90`. Per-row revision, trading status and conservative accepted publication available_at are retained. amount_ratio20 is never an amount substitute. Target date mismatch/source payload unavailable -> UNKNOWN; future date/revision or digest mismatch -> reject. Actual zero stays zero; nonpositive sector sum produces UNKNOWN. Integration covers known amounts, one unknown, all zeros, actual zero, invalid amount, date mismatch, future source, digest mismatch and unavailable payload.

R5-B03 PASS: `data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json` -> `reports/v4_02/staging/V4_02_GO_FORWARD_ADJUSTED_T0_CANDIDATE_R3.jsonl.gz` (SHA `7d87f5164c11f791ad24ad7c05139dca949f1c891523616ece907cd0f28fd8c8`; logical digest `a5600d7f1416434bd54e778c2e7e847e309de1c21d71df5677f92daee1791400`). Close is qfq_ohlc[3]; price_basis_id is the existing V4_03 Bar identity `coordinate_basis:adjustment_snapshot_id`. adjustment_snapshot_digest and formal/system/adjustment availability are retained. Same per-member identity creates and stores pulse baseline; different/missing identity leaves UNKNOWN with MIXED_PRICE_BASIS/PULSE_BASELINE_UNAVAILABLE. Future revision rejected. Corporate-action transition has no accepted conversion applied and remains UNKNOWN. Head identities reuse accepted CANONICAL_JSON_SHA256_V1; binary identities remain raw-byte SHA256.

## Acceptance evidence

TEST_ONLY isolated accepted-source fixtures pass through the production loader/adapter to current and Native/B0/Rotation/B2. 55 targeted tests PASS; fixture heads never enter formal artifacts. Pulse tests supply separate prior-PIT trigger facts but never inject canonical amount, close or price basis into current.

Real 2026-09-30: target accepted Core count 0; each namespace has 378 rows; distributions `{"B0": {"UNKNOWN": 378}, "B2": {"UNKNOWN": 378}, "ROTATION": {"UNKNOWN": 378}}`. No stale Core relabel, no forced TRUE/FALSE.

Clean detached checkout: 698 tests, 696 passed, 2 skipped, 0 failures, 0 errors. No config/.env present/read; process DSN and disposable PostgreSQL 18.6; 1512 exact readback rows; append-only result/publication checks pass; cluster destroyed. Candidate reproduction leaves tracked checkout clean. LFS objects restored from existing Git object store before verification.

NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC: PASS; hard_gated_equity_symbol_hits=0; unclassified_paths=[]. Parameter SHA remains `0204d7c4fadf86871b6a079f755593b1a3f8ad18bb718f73ba33db0b70f67548`; all five retention values unchanged. Migration 020 and accepted membership unchanged; no migration 021 or final V4-08 accepted head.

## Independent audit boundary

Prior-RPS bootstrap, AUD-AMOUNT-A-06, target Core availability and V4-01 dated-roster lineage remain independently OPEN with their existing evidence and acceptance scope. This repair closes only the three engineering wiring items as a candidate. Global stage range remains V4_00_TO_V4_07_ACCEPTED; production_permission=false.

## Changed paths

- `AGENTS.md`
- `config/v4_08_accepted_input_contract_r5_1.json`
- `config/v4_08_b2_machine_ast_r5.json`
- `data/v4/artifact_store/v4_08/V4_08_R5_B0_20260930_17fe0b83a55f52d66016.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_B0_20260930_87447ccd136d152b8372.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_B0_20260930_ce3b9ede6ec4d0e94ed6.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_B2_20260930_17fe0b83a55f52d66016.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_B2_20260930_87447ccd136d152b8372.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_B2_20260930_ce3b9ede6ec4d0e94ed6.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_ROTATION_20260930_17fe0b83a55f52d66016.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_ROTATION_20260930_87447ccd136d152b8372.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_ROTATION_20260930_ce3b9ede6ec4d0e94ed6.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_SECTOR_NATIVE_20260930_17fe0b83a55f52d66016.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_SECTOR_NATIVE_20260930_87447ccd136d152b8372.jsonl.gz`
- `data/v4/artifact_store/v4_08/V4_08_R5_SECTOR_NATIVE_20260930_ce3b9ede6ec4d0e94ed6.jsonl.gz`
- `docs/evidence/V4_08_R5_1_THREE_BLOCKER_TARGETED_REPAIR_TASK_20260930.md`
- `docs/evidence/V4_08_R5_INDEPENDENT_EXTERNAL_ACCEPTANCE_AUDIT_R1_20260930.md`
- `reports/v4_08/V4_08_R5_1_ACCEPTED_INPUT_ADAPTER_INTEGRATION.json`
- `reports/v4_08/V4_08_R5_1_B2_LEGACY_MIXED_SEMANTIC_GOLDEN.json`
- `reports/v4_08/V4_08_R5_1_B2_RANK_UNIVERSE_PARITY.json`
- `reports/v4_08/V4_08_R5_1_B2_SEMANTIC_PROVENANCE.json`
- `reports/v4_08/V4_08_R5_1_CONCENTRATION_INTEGRATION.json`
- `reports/v4_08/V4_08_R5_1_FEEDBACK_ISOLATION.json`
- `reports/v4_08/V4_08_R5_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json`
- `reports/v4_08/V4_08_R5_1_PRICE_BASIS_INPUT_BINDING.json`
- `reports/v4_08/V4_08_R5_1_RAW_AMOUNT_INPUT_BINDING.json`
- `reports/v4_08/V4_08_R5_1_ROTATION_PRICE_PATH_INTEGRATION.json`
- `reports/v4_08/V4_08_R5_1_STAGE_CANDIDATE_MANIFEST.json`
- `reports/v4_08/V4_08_R5_1_STAGE_ENTRY.md`
- `reports/v4_08/V4_08_R5_B0_FULL_MARKET.json`
- `reports/v4_08/V4_08_R5_B0_IMPLEMENTATION.json`
- `reports/v4_08/V4_08_R5_B2_FULL_MARKET.json`
- `reports/v4_08/V4_08_R5_ROTATION_FULL_MARKET.json`
- `reports/v4_08/V4_08_R5_ROTATION_IMPLEMENTATION.json`
- `reports/v4_08/V4_08_R5_SECTOR_NATIVE_FULL_MARKET.json`
- `reports/v4_08/V4_08_R5_SECTOR_NATIVE_IMPLEMENTATION.json`
- `reports/v4_08/V4_08_R5_STAGE_CANDIDATE_MANIFEST.json`
- `scripts/freeze_v4_08_r5_contracts.py`
- `scripts/materialize_v4_08_r5.py`
- `scripts/run_v4_08_r5_1_isolated_verification.py`
- `scripts/verify_v4_08_r5_1.py`
- `src/sector/accepted_input_r5_1.py`
- `src/sector/legacy_b2_r5.py`
- `src/sector/rotation_r5.py`
- `src/sector/semantic_input_r5_1.py`
- `tests/v4_08/test_r5_1_accepted_adapter.py`
- `tests/v4_08/test_r5_runtime.py`

Final evidence-only seal adds/updates R5.1 closure, handoff, clean receipts, stage entry and candidate manifest. Pushed HEAD is reported in the delivery message; the implementation above is the clean-tested commit.
