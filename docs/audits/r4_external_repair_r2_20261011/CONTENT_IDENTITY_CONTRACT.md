# R4-EXT-R2-01 / candidate content identity contract

Version V4_PG_RESEARCH_SNAPSHOT_R2, V4_PG_SHADOW_READBACK_R2, V4_PG_DATED_SERIES_R2 and V4_JOINT_RELEASE_V2_PG_CONTENT. Old R1 descriptors/Head bytes retain their historical semantics and do not gain R2 acceptance.

Four snapshot tables use explicit column/type order, C collation and deterministic primary-key order. SQL NULL, text and JSON types differ; payload JSON numbers use exact rational typed trees, duplicate keys/nonfinite numbers fail closed, all value/unit/quality members are included. Metadata.value remains exact text. Rows are newline-framed canonical arrays. Each table denominator and SHA, full manifest/source binding, schema and cluster system_identifier/database name/OID are bound into the descriptor root. Series adds bars(security,day,payload), Journal adds days and day_inputs; all consumer descriptor fields are bound before sealing.

Seal rescans all contents before commit. Readers rescan inside REPEATABLE READ + READ ONLY. Joint V2 validates bound Snapshot/Series/Journal before CAS and after health before COMMITTED. A different instance/database needs a new versioned descriptor and fresh external admission; no in-place rewrite of accepted R1 identity. Exact-content restore on the same database may use its old descriptor only after independent verification. Database identity is not a PIT/Grant or protection proof.

Candidate least-privilege verifier grants are schema USAGE, selected table SELECT and pg_control_system EXECUTE only; elevated attributes/memberships rejected. Test roles are isolated NOLOGIN with no ownership or DML. Actual production roles remain unprovisioned, PENDING_PERMISSION. Superuser/owner can still replace a descriptor, trigger and data together; authenticated immutable external manifest/authority bindings remain necessary. No automatic authorization is derived from a SHA.

Rollback keeps predecessor pointer bytes and immutable versions. Generic historical Joint V1 remains readable with its prior contract; it is not upgraded to content admission. Continuous candidate promotion selects V2. Future sessions, Windows restart, production authority and all formal grants remain separate gates.

Cost: each R2 read verifies all bounded contents, prioritizing correctness. Full consumer throughput is an OPEN independent performance item; no capacity PASS is claimed. Snapshot/Series/Journal real complete consumer and restore admission gates remain OPEN despite scoped corruption/CAS vectors.
