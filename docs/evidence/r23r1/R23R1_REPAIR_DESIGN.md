# R23R1 repair contract and evidence

Baseline: 9724b0b2091b0d1e0ca55af17e1fc8c3948fdf42. Highest scheduler: V4_NEXT_ROUND_EXECUTION_MASTER_R23R1_20261004.md.

The runtime reads the exact accepted Slot V2 via its existing dependency binding. The additive repair policy is pinned by literal SHA256 and byte count in the disabled engineering controller. It leaves the accepted slot contract, clock, activation authority and accepted business modules unchanged.

All slot states persist the 18 fields, explicit field quality and receipt availability completeness. Unaccepted computation/publication facts remain null with NOT_YET_AVAILABLE. Known partial receipt aggregates are marked visibility_complete=false. Late timing facts remain visible in missed slots. Accepted revisions carry request evidence bound to the publication request digest, exact mandatory-receipt maxima, manifest digest, canonical evaluated scope and core_revision equal to the deterministic publication identity.

Only the Shadow observation wrapper adds supersedes lineage and Shadow publication/revision links. The accepted V4-15 projection artifact and business algorithm remain unchanged. A correction references the highest preceding observation revision for the same event and slot; first observations retain null. SQLite append-only constraints and strictly increasing revision identities prevent cycles.

The read-only independent oracle imports no writer or orchestration code. It retains the old R23 oracle scope and adds exact field, receipt chronology, request, aggregation, scope, manifest and observation-chain checks. N25–N32 copies intentionally remove test-copy triggers, mutate semantic payloads and recompute row digests, so rejection establishes semantic validation rather than merely checksum validation. Test-copy databases are not runtime outputs.

R23-SLOT-01 and the observation-lineage P1 are separately tracked in STAGE_CONTRACT_AND_AUDIT_ITEMS.json. Local closure is not external acceptance. Receipt chronology is first <= integrity <= system <= durable created. Existing late-receipt tests update created_at only to preserve their original late-source rejection family.

All existing baseline files outside the three explicitly scoped repair files (.gitattributes, scripts/v4_16_shadow_runtime.py, tests/test_r23_runtime.py) must remain unchanged. Old ATTEMPT_R1_DISPOSITION and all R23 proofs remain immutable. Full PRE16/R21/R22/R22R1/R23/R23R1 regression is required locally and in an exact detached checkout. Tested source gets a new immutable tag; final commit adds only regression/seal evidence.

No real Shadow, PIT samples, accepted Head16, Stage/Data advance, Production, Focus or V4-17. NEXT=STOP_WAIT_R23R1_INDEPENDENT_EXTERNAL_AUDIT.
