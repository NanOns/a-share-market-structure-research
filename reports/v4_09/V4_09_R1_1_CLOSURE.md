# V4-08 amendment + V4-09 R1.1 targeted repair closure

Status: `V4_09_R1_1_ENGINEERING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT`. External R1 acceptance was blocked; R1.1 remains pending independent external reaudit.

Stage authority: supplied lineage/immutability repair task and external R1 audit. Latest REV4 FEP R2 raw/priority rules remain frozen. Only B01/B02/B03 repaired; no V4-10 implementation.

B01: original V4-08 Accepted Head preserved byte-for-byte as historical erroneous lineage. Old SHA256 `b9ba34374ce35eefab705469de1e005758b90fa1f58ea5bba96fac08571073bc`. New amended head SHA256 `f2a35cebd18e8caf723e7900133333ce4b8df1a8314cb190dade7b0ea7624a3f`; supersedes binds the old exact path/SHA. B0 producer `src/sector/rotation_r5.py`, SHA256 `93c73b431a0fa8af1cf2e0c65a706dc78e390b1d5a2cd821f85e89ec5323968b`, callable `evaluate_b0`; both contract and producer are compared with V4_08_R5_B0_IMPLEMENTATION.json and the actual exported callable. Semantic negative tests reject self-consistent wrong bindings. Global Stage SHA256 `6620089e9a1ca550e89c2c0bb177887528c8e7d160a44c584664f04b91a1c48e` points to amended head and preserves the superseded binding. Range remains V4_00_TO_V4_08_ACCEPTED. Data/Dev/PIT bytes, capabilities, OPEN audits and false production/shadow/Focus permissions unchanged. Amendment retry is idempotent.

B02: compression/MA/risk producer contracts and V4_04_CORE_PROFILE_PARAMETER_SET_V1 now enforced. Missing/wrong producer or parameters produce STATE_PRODUCER_CONTRACT_MISMATCH / STATE_PARAMETER_SET_MISMATCH. Structure identity failure degrades only its priority axis; valid producer with UNKNOWN value retains the original short-circuit axis rules. Mandatory quality and raw remain unchanged; synthetic TRUE cases preserve TRUE and receive UNKNOWN_BUCKET when identity fails. Fifteen correct/wrong/missing contract and wrong/missing parameter vectors pass with an independent envelope reader. Original 150 algorithm vectors and parameter perturbations also pass.

B03: formal artifact uses trade-date/logical-digest path and exclusive atomic create via fsynced temp + hard link. Existing identical bytes are idempotent; existing different bytes raise APPEND_ONLY_ARTIFACT_CONFLICT, with old bytes preserved. Concurrent conflicting writer test preserves one complete payload. Old fixed R1 artifact stays intact and is no longer the materializer output.

Actual filesystem materialization through the same production candidate factory covers synthetic T, T+1 and same-day source revision-2, with distinct immutable identities and T path/SHA/bytes unchanged after both later materializations. These are explicitly contract-vector fixtures, not real accepted future-market revisions; no unavailable next-day accepted market data is fabricated. The actual accepted same-session 9/28 full-market candidate is separately materialized and byte-identical on clean replay.

Accepted replay: 2026-09-28; 5222 identities. TRUE=0, FALSE=2443, UNKNOWN=2779. A/B/C/D=0/0/0/0; UNKNOWN_BUCKET=2779, NOT_ELIGIBLE=2443. Counts unchanged. No Seed/Prior-RPS fallback or threshold/quality/AST/bucket change. Migration 021 semantic SQL SHA unchanged.

Runtime SHA256 `9c8a5d11219199e1b93ab5efccc34b1b586624aadd3b58348fd48274aa7f84a4`.
Contract SHA256 `6c090ee9cbc5a7e3c5c86ca9023aa983db41d447388ea1776308a69ecbefadc8`.
AST SHA256 `9035548e8e33ea66e1c448b63b017cfa9b1ab2bcf7c08ef0568063a2eac954c6`.
Parameter SHA256 `3c9b0d658c6e8212c5a6239eecdeece99d54791b97cee45fe4df98de71086c24`.
Immutable artifact `data/v4/artifact_store/v4_09/V4_09_STOCK_PREWATCH_2026-09-28_edb35a7b7aa382add631d80d105575c00274b638cef112b58e7e2687510e9a6e.jsonl.gz`.
Artifact SHA256 `8b92cbd96a8145005bad89374349582c075cf367722b956a75243d59aa64d18d`.
Logical digest `edb35a7b7aa382add631d80d105575c00274b638cef112b58e7e2687510e9a6e`.
Publication `V4_09:e38b5feb1696e283334692f21d7e99b1869a22552a50e0144b71c07acf4386c1`; trade date `2026-09-28`.

Independent full-market source-reading and producer/parameter postcheck mismatch_count=0. Determinism/feedback isolation PASS. Disposable PostgreSQL full-market exact readback 5222 rows, retry, additional 5222 revision rows, publication conflict rejection, UPDATE/DELETE rejection and rollback-only-021 boundaries PASS; cluster destroyed. Clean detached implementation `5eca56d3555a826c4cca94d6e3d7ae9d11628be6` reproduced every tracked artifact/receipt without changes, no config/.env read or configured database use. Required regression: 912 tests, 910 passed, 2 skipped, 0 failures, 0 errors. Permanent no-symbol PASS, hard hits=0, unclassified=[]; V4-09 targeted tests=201.

Next: independent external reaudit of R1.1. No V4-09 Accepted Head or Stage range advancement; production/shadow/Focus permissions remain false. Existing independent capability audits stay OPEN. Stop at this handoff.
