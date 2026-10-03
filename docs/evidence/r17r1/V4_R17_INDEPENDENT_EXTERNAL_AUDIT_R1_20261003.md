# V4 R17 Independent External Audit R1｜2026-10-03

## 1. Audit Target
- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- Audited remote HEAD: `204d799f26a7badbce3d6b09d3ceed722c522c91`
- R17 execution baseline: `f12315bf8e3142aa44e9068c5895004c35c4e23c`

## 2. Unique Decision

```text
R17_EXTERNAL_AUDIT = PARTIAL_PASS_FORMAL_AUTHORITY_REPAIR_REQUIRED

R17A_CROSS_STAGE_GOVERNANCE_REPAIR = PASS_KEEP
R17B_PROMOTION_MECHANICS = PASS_KEEP
R17B_V4_13_ACCEPTED_PACKAGE_ACTIVE_BINDINGS = FAIL_P0
R17C_V4_14_CONTRACT_FREEZE = FAIL_P0_ACTIVE_AUTHORITY_CLOSURE

V4_STAGE_ACCEPTED_HEAD = KEEP_V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = KEEP_2026_09_30

V4_14_RUNTIME = NOT_AUTHORIZED
ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED
```

Do not roll the Stage Head back. Preserve the original V4-13 Accepted Head as historical promotion evidence, but amend the formal V4-13 contract package before any V4-14 runtime implementation.

## 3. PASS / KEEP
R17A is accepted: historical binding repair closed the 22 stale failures with 828 PASS / 0 FAIL / 0 DESELECT.

R17B promotion mechanics are accepted:
- r6 promoted;
- Data Head unchanged;
- parent Stage archived;
- Stage advanced to `V4_00_TO_V4_13_ACCEPTED`;
- Production / Shadow / Focus remain false;
- original `data/v4/V4_13_ACCEPTED_HEAD.json` remains immutable historical evidence.

## 4. P0 G01｜V4-13 DAG Registry Binds Superseded Projection v1.0

Formal V4-13 package accepts:
`config/v4_13_projection_v1_2.json`
SHA `567b498c9e0f828dc041d56ab56e79c8a4d34877fd09eef46a9c1f504396b19c`

But `config/v4_13_dag_edge_registry_v1_1.json` still binds:
`D1 -> PROFILE / structure_projection -> config/v4_13_projection_v1.json`
SHA `bd792cc6dfd0781e6b919b0d5cf39021167d82112b922b621f9de6d006f9043a`

This is an internal active-version inconsistency.

## 5. P0 G02｜Rotation/Structure Enrichment Also Binds Projection v1.0

`config/v4_13_rotation_structure_enrichment_schema_v1_1.json`
still binds its `structure_schema` to the same superseded projection v1.0.

## 6. P0 G03｜R17C Validator Does Not Prove Active-Contract Closure

`validate_r17c_contract_freeze.py` proves exact bytes/hashes, but does not prove that every current contract binding resolves to the latest same-family contract authorized by the V4-13 Accepted Package.

Therefore R17C copied the stale V4-13 projection binding into the V4-14 freeze and incorrectly declared contract completeness.

## 7. Repair Boundary
Do not overwrite or delete the original V4-13 Accepted Head or existing R17C v1.0 contracts.

Create same-family amendments:
- V4_13_DAG_INTEGRATION_INTERFACE_V1 v1.1 -> v1.2
- ROTATION_STRUCTURE_ENRICHMENT_V1 v1.1 -> v1.2

Then create a new formal V4-13 accepted package entry and amended V4-13 Accepted Head. Update the moving Stage Head binding while keeping `accepted_stage_range = V4_00_TO_V4_13_ACCEPTED`. Data Head remains unchanged.

## 8. V4-14 Re-freeze
Create V4-14 v1.1 contract-freeze files bound to the amended V4-13 authority.

Add independent `ACTIVE_CONTRACT_FAMILY_CLOSURE` validation. Exact old refs must be rejected when used as current runtime/consumer refs, even when path/hash/bytes are valid.

## 9. Authorized Next Round
```text
R17R1A
V4-13 Accepted Package Active-Binding Repair

R17R1B
V4-14 Replay Gate B Contract Re-freeze Against Active Authority

STOP
```

Only after R17R1 external audit may V4-14 Replay Runtime implementation begin.
