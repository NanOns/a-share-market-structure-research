# R94：Producer dependency archive runtime readback

## Scope and change

The producer dependency freezer now stores immutable `src/` and `config/` bytes under `data/v4/artifact_store/producer_dependency_archive_v1/<sha256>.bin`, outside the evidence tree. The historical candidate reader resolves those code/config bindings from the content-addressed archive and verifies the digest before returning bytes. Missing or mutated archive bytes fail closed with `HISTORICAL_COMPUTATION_BYTES_NOT_CAPTURED`. Non-code dataset bindings continue to use their original checked source path and are not redirected into the code archive.

The exact-daily policy test fixture now supplies the configured TDX source root required by the active resolver. This also repairs the R93 focused CI failures caused by a disposable fixture lacking `config/paths.yaml`.

## Verification

- Focused historical HTTP, exact-daily policy, and immutable binding tests: **15 passed**.
- R91/R93 CI command test selection, after installing `cryptography` and `pglast` under `G:/codex_tmp/pydeps_r21_r4`: **318 passed**. Dependencies and pytest temporary output remain outside the repository on G:.
- No live PostgreSQL read, write, migration, publication, or business acceptance was performed.

## Original callsite accounting and remaining work

No original stable callsite ID in the 266-row R20/R21 baseline is closed by this batch. Formal status remains **0 / 266 complete; 266 / 266 remaining**. This change fixes historical computation dependency restoration used by candidate consumers; it does not claim the candidate's original business callsites are migrated to the live PG chain.

## Next stage

Continue contract-registry and current business-consumer migrations, including PG Head/Authority/descriptor/daily/BFF read paths. Keep live database publication blocked pending explicit write authorization and retain the distinction between test evidence and business acceptance.
