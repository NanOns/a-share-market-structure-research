# V4-10 R1.1 repair closure — 2026-10-01

V4_10_R1_1_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT

Tested implementation: `6049973cd78e51cdeb2ba33461f20ce96b13c8d6`. Baseline: `14db3ef521d34b366bf5a22bad2a3564838ce8bf`.
Clean detached required-family regression: 1090 passed, 2 skipped, 0 failed, 0 errors. The sole authorized historical node remains deselected; no new deselect.
149 static vectors PASS, including the original 98 semantic vectors. B01–B06 repair checks, direct SQL attacks, append-only/revision/rollback and no-symbol PASS.

Business RESEARCH_STATE_V1 and 2/10/3/3 thresholds remain unchanged. R1.1 supersedes the R1 engineering candidate only. Original R1 configurations, reports, migration 022 and V4-09 accepted evidence remain byte-identical.

The immutable engineering ledger owner is the trusted issuer. Accepted-mode tests use disposable gate fixtures, not accepted market signals. Missing V4-11/V4-12/settlement producers yield NOT_IMPLEMENTED/UNKNOWN; stock WARM remains NOT_APPLICABLE. Sector adapters remain gated by owner and entity scope.

Production, shadow and Focus permissions remain false. V4-10 Accepted Head is absent. V4-09 KEEP_ACCEPTED / NO_REOPEN. N01/N02 and all historical capability audits retain independent OPEN states.

| Gate | Result |
| --- | --- |
| G01_V4_09_accepted_head_unchanged | PASS |
| G02_prior_full_schema_authenticity | PASS |
| G03_prior_content_address_identity | PASS |
| G04_prior_calendar_lineage | PASS |
| G05_model_boundary_authorized_manifest | PASS |
| G06_state_changing_field_provenance | PASS |
| G07_frozen_invalidation_fail_closed | PASS |
| G08_followup_completion_owner_gate | PASS |
| G09_input_manifest_canonical_shape | PASS |
| G10_DB_payload_publication_identity | PASS |
| G11_independent_negative_vectors | PASS |
| G12_original_semantic_vectors | PASS |
| G13_append_only_revision_rollback | PASS |
| G14_no_symbol | PASS |
| G15_clean_detached_full_regression | PASS |
| G16_production_shadow_focus_false | PASS |
| G17_V4_10_accepted_head_absent | PASS |

## Bound evidence

- `CONTRACT_FREEZE`: `21c1c57b4e8ae5d6f8739af9bc6cf09c2b3c9f91b61d70c4869dbf85d2a84d97`
- `PRIOR_LINEAGE_ACCEPTANCE`: `1e4bbbab6c50c9279bddadc6cdfd363f998c534724bb6fdb8dd4095d3bd10731`
- `MODEL_BOUNDARY_ACCEPTANCE`: `e0c982556d8e895982d13f1a29f216bcb99d46b5d9b6209cf8f62c46aa46b8e5`
- `INPUT_PROVENANCE_ACCEPTANCE`: `86b2695996c69929161b1f879bec336ee5b01934345353bde1053e4f41ed8ed3`
- `INPUT_MANIFEST_SHAPE_ACCEPTANCE`: `8f3a9a99271e0330643d1bf618563376010a39d7240d7492e215b8a8fdc1f6ea`
- `MACHINE_VECTOR_COVERAGE`: `4e889e853db49ed02e635803ad2a55052b02b3dfbbbf6b6796a0629ced0f89d8`
- `INDEPENDENT_POSTCHECK`: `4c49779b060dd2c5f4443e4cab6e93cfa0b0554a1927c4c946cfa1a2aaaed717`
- `SCHEMA_MIGRATION_RECEIPT`: `b03d8ca695b1f72d792b0c64d4bb362ec5ce42eaaa25b8bbbdf004538b3e8b0d`
- `ISOLATED_REGRESSION`: `057bca5211d7049b0de6758ddfc4a6eb840ae5f4356d36b3e4ed0f16a4f9e71f`
- `NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN`: `03ddeb5765c996299fecac4bca2934844cf72aee712ee59dfa070ff5782dccbf`
- `CLEAN_CHECKOUT_RECEIPT`: `f28eeb700fda732bd2e18b34afe05e0ca126957f77913a95258adcc306f71863`

## Next stage

STOP for independent external repair reaudit. A Git push does not establish external acceptance or authorize V4-11. After an explicit PASS, promotion/entry is a separate authorized stage.
