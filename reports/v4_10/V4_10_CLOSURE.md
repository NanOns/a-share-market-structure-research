# V4-10 interface engineering closure — 2026-10-01

V4_10_REDUCER_INTERFACE_ENGINEERING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT

External acceptance: PENDING_INDEPENDENT_EXTERNAL_REAUDIT. No V4-10 accepted head is written.
V4-09 promotion PASS. Official upstream remains amended V4-08; protected heads unchanged. Real signal DEGRADED.
V4-10 implements the five-axis D2 interface and independent synthetic vectors. No full detector DAG or live market materialization is claimed.
Full integration awaits V4-11 Confirmation and V4-12 Structure/Anchor/Support; complete acceptance belongs to V4-14 Replay Gate B.
Stock WARM NOT_APPLICABLE; sector legacy WARM extraction and full frozen episode invalidation NOT_IMPLEMENTED.
UNKNOWN retains maturity/tracking, marks STALE and eligibility UNKNOWN. Hysteresis requires two consecutive evaluable market sessions. Expiry freezes improvement baseline and pauses on UNKNOWN/suspension. Reentry creates a child episode only after the exit session and preserves old follow-up/outcomes.
Migration 022 is an append-only engineering sidecar with explicit consumer identity; original migration 021 remains unchanged.
Existing OPEN capability audits and N01/N02 separate hardening audits remain OPEN. Production/shadow/Focus permissions remain false. TDX roots were not written.
The historical candidate-only accepted-head-absence node is explicitly superseded; its original bytes are preserved. Exact current promotion tests replace it. This regression is the required V4 family set, not a claim that the unrelated global pytest collection audit is closed.

Tested implementation commit: `e3b29a434c57a94cc5fe68edc3de647862da4ec4`.
Independent vectors: 98; mismatch_count=0.
Clean detached regression: {"errors": 0, "failures": 0, "passed": 1021, "skipped": 2, "tests": 1023}.
Schema exact readback / revision / conflicts / UPDATE / DELETE / rollback 022: PASS. Disposable database destroyed; config/.env absent and forbidden to read.
No-symbol: PASS, hard_gated_equity_symbol_hits=0, unclassified_paths=[].

## Exact handoff bindings

- V4-09 accepted head: `data/v4/V4_09_ACCEPTED_HEAD.json` SHA256 `641ef9e2e6fe8f461a9b765262e739791a6d3fdd220b0eff7947e2690de3a87d`
- Global stage: `data/v4/V4_STAGE_ACCEPTED_HEAD.json` SHA256 `f7607601de402f2b2bdada84dffdefbacad7f9f66e252c57dfdf045060e90e99`
- input_schema: `config/v4_10_input_schema_v1.json` SHA256 `6e9c65f80e18e5f0ec4b2b75f1c75a73ddbbf989bf84b3b17cb7cbac3a6a8668`
- machine_ast: `config/v4_10_machine_ast_v1.json` SHA256 `194d8b7e9733816e1048b6e08d29e18ea092641f8ab5281558562b41051d3ebc`
- machine_vectors: `config/v4_10_machine_vectors_v1.json` SHA256 `79d1ee4048f7bc032273760402f051706917b75d3012fcf09894563a65dd0266`
- output_schema: `config/v4_10_output_schema_v1.json` SHA256 `5199b07beb81d417fbcb86c8961162ce6ac5ad79cc0bceb6d164286096be02b2`
- parameter_set: `config/v4_10_parameter_set_v1.json` SHA256 `20b66f9f2d2d4fe6ba8c3dd0583d6fa3d5408daebda09fae7ff27548e800ffd7`
- research_state_contract: `config/v4_10_research_state_contract_v1.json` SHA256 `bf0ba733785b5fe0e481b2abc7df1323d0ed05276fa4dad3751942df67c4c0ae`
- src/v4/research_state.py: `src/v4/research_state.py` SHA256 `dbc98bb7f91d0851aeac2bdd45a29290982f3e6d35eb02009668d0fa79bbd381`
- src/v4/research_state_persistence.py: `src/v4/research_state_persistence.py` SHA256 `f5ee9cc090b0b2f506c6302882f9de2b999d33b3a05f913afda05ae9d54f747d`
- src/workbench_db/migrations/v4_postgres/022_v4_10_research_state_interface.sql: `src/workbench_db/migrations/v4_postgres/022_v4_10_research_state_interface.sql` SHA256 `cfa37902a75b100e05813e3fb0b63e3884bf369d4c1913067e5714eb9004a732`
- src/workbench_db/migrations/v4_postgres/rollback/022_v4_10_research_state_interface.sql: `src/workbench_db/migrations/v4_postgres/rollback/022_v4_10_research_state_interface.sql` SHA256 `3e1a8c934c57f34d159110bde5555759ad6fa852847529981d8df4687c920823`
- scripts/freeze_v4_10_contract.py: `scripts/freeze_v4_10_contract.py` SHA256 `ee11d5311701ae76dd25390582da1d6bf4a286bfec3db1c80d67d770a8b57e6d`
- scripts/verify_v4_10_state_reducer.py: `scripts/verify_v4_10_state_reducer.py` SHA256 `33b0789301db73685a336405276b29689d8826c8cd58545c816225b6612ccd18`
- scripts/run_v4_10_isolated_verification.py: `scripts/run_v4_10_isolated_verification.py` SHA256 `49010a9dcb0297852d77e8d9d334e47b50841f8b5e52a544db52c589a2580f3a`
- tests/v4_10/test_research_state.py: `tests/v4_10/test_research_state.py` SHA256 `93394ec0fa8d95ae7b6c5880b9d19015f0aa3d6287a0d73a26bd283b02d04235`
- tests/v4_10/test_promotion.py: `tests/v4_10/test_promotion.py` SHA256 `fac6292a7970229d4baa1f26085690e67e0c0dd4c68e9364c44b0516d1ab393d`
- Protected: `data/v4/V4_DATA_ACCEPTED_HEAD.json` SHA256 `186b1c88512a5a92e7c4fbd954e5dcd005a0ad03ecbac9c334b05939d9e12de0`
- Protected: `data/v4/V4_DEV_BASELINE_HEAD.json` SHA256 `45695460b0147c6ada12e0ebd8e5070ac0a45eebea26603ff5a3daddc4dd5094`
- Protected: `data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json` SHA256 `d6374a73b8084ccd383cbb4f75428ed91176e91cc09d87c3329041d57c5bd9ed`

V4-09 artifact SHA256 `8b92cbd96a8145005bad89374349582c075cf367722b956a75243d59aa64d18d`; logical digest `edb35a7b7aa382add631d80d105575c00274b638cef112b58e7e2687510e9a6e`.
V4-09 decision: V4_09_EXTERNAL_ACCEPTANCE_PASS_R1_1_ENGINEERING_SCOPE. Engineering/raw PREWATCH/Priority V1 accepted; real signal DEGRADED.
After committing and pushing this seal, report the actual pushed HEAD. A push grants no external acceptance or later stage entry.
