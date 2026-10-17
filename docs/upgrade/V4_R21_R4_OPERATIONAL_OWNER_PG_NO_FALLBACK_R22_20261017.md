stage_id: V4_R21_R4_OPERATIONAL_OWNER_PG_NO_FALLBACK_R22_20261017
baseline_sha: cdf503f124dce2cd4fd1af42dd7833bfb36783d7
branch: codex/v4-workspace-cleanup
status: PARTIAL_OWNER_READER_CODE_WIRING_CURRENT_HEAD_MIGRATION_OPEN
callsite_ids: V4-BCA-R2-ce030238606ae3e34b44; V4-BCA-R2-5fc637717724bb649d31; V4-BCA-R2-cb66f2ca511317f7b881
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_catalog_or_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: move the current operational Head and owner facts into the accepted PG publication chain, then continue the daily and other-business consumer migrations
---

# V4 R21-R4 operational Owner PG no-fallback batch

Date: 2026-10-17 (Asia/Shanghai). This batch follows the official R21-R4 execution card and advances the current Owner reader path.

## Code change

- `OperationalSuccessorReaderV1` now requires a Head-embedded PG Owner authority manifest. A file-backed legacy `config/v4_operational_owner_pg_closeout_r1.json` can still enter only through the explicit one-time predecessor ingress used by successor preparation; it is no longer accepted as runtime Owner authority.
- Core Product BFF cache collection no longer treats an inline PG descriptor's `path` as a file to stat or open. It uses the descriptor embedded with the accepted Owner binding, including its database identity.
- Existing Owner manifest loader and descriptor reader remain connected to `forward_facts`; no new parallel authority is introduced.

## Exact callsite and accounting

- Matrix IDs: `V4-BCA-R2-ce030238606ae3e34b44` (current Owner Reader), `V4-BCA-R2-5fc637717724bb649d31` (PG authority manifest loader), and `V4-BCA-R2-cb66f2ca511317f7b881` (PG descriptor resolver).
- The manifest and descriptor rows remain pending inventory/live reconciliation. The current accepted operational Head in this checkout lacks `native_pg_owner_authority`, so the new runtime path deliberately fails closed until the Head/Owner migration is accepted.
- Original baseline: **266**. Formal closure: **0**. Formal remaining: **266**. No numeric reduction is claimed.

## Verification and limits

- **13 passed** across Owner manifest binding, Reader success/failure path and BFF inline-descriptor path regressions.
- `compileall` and `git diff --check` passed. Tests exercise isolated fixtures; they do not prove business acceptance or a live PG read.
- Neither `V4_NATIVE_PG_DSN` nor a compliant Reader DSN is configured in this task environment. No PG DDL/DML, Head write, service start or acquisition ran.
- The current Head and business Owner payloads have not been migrated into the canonical V4 publication chain. The full R4 target remains open.

## Next stage

Continue wiring exact source, Owner and publication callsites that can be implemented without live PG. Complete the operational Head/Owner migration and live readback once accepted PG identity and permissions are supplied. Keep baseline counts unchanged until row-level evidence supports reconciliation.
