---
stage_id: V4_PG_DAILY_PUBLICATION_R3_20261016
code_sha: c7e585239b20ef1bb1678adbef721bfb8af99e46-base-plus-R3-worktree
test_scope: owner-mapping-source-manifest-resolvers-focused-contract
conclusion: 43-focused-tests-pass; global-requiredness-and-live-PG-unverified
approval_status: CODE_ONLY_REPAIR_AUTHORIZED
---

# V4 PG 日发布 R3 综合阶段报告

- Contract: `V4-PG-DAILY-PUBLICATION-EXTERNAL-REPAIR-20261016/R3`
- Audit baseline: `c7e585239b20ef1bb1678adbef721bfb8af99e46`
- Branch: `codex/v4-workspace-cleanup`
- Scope: real existing Owner-family/page mapping, source-manifest canonicalization and rehash, fixed PG Owner resolvers, candidate status and focused tests.
- Upgrade basis reviewed: R2 daily-publication repair (2026-10-16), R8 unified-source contract (2026-10-15), V4 runtime performance repair (2026-10-13), production-data migration design, and V4 daily operations/rollback guide.

## Results

- Implemented the three PG Owner families already produced by V4: research-priority (`owner_payloads`), operational-risk (`owner_payloads`) and sector-lifecycle (`owner_rows`). No endpoint-specific Owner stores were created.
- Mapped the seven page projections to their consumed fields, available supplemental Owner paths and uncovered input groups. The present contracts do not establish global daily requiredness, so these Owner families are capability-optional; absence stays explicit.
- Added fixed resolver dispatch with owner contract/token/T0/sealed/count/database identity/role/payload digest checks. Page adapter returns `DEGRADED` or `PENDING`, `candidate_only=true`, and `NOT_VERIFIABLE_PAGE_PARITY`; the production reader remains unchanged.
- Candidate planner reports `CANDIDATE_REQUIREMENTS_UNVERIFIED` and blocks Head CAS planning until global daily Owner requiredness has an authoritative producer-contract basis.
- Added `V4_PG_CONSUMED_SOURCE_MANIFEST_R1` v1.0.0 and migration 010. New publications must declare the format and are rehashed over canonical ordered source-revision rows. Unmarked historical rows remain unknown and fail closed. Two deterministic synthetic vectors and a one-field mutation vector are covered; no real accepted PG sample is available.
- Focused command: `python -m pytest -q -p no:cacheprovider --basetemp=<G-drive test temp> tests/test_v4_pg_publication_candidate.py tests/test_v4_pg_publication_owners.py tests/test_v4_pg_publication_contract_static.py tests/test_v4_pg_source_manifest.py` — **43 passed**. Raw pytest output stays outside Git.
- Read-only PG env lookup: `V4_NATIVE_PG_READER_DSN` absent, `WORKBENCH_PG_DSN` absent, `V4_NATIVE_PG_DSN` absent. Result: `DB_READ_ENV_UNAVAILABLE`; no PG connection, catalog query, SQL execution, DDL/DML, service start, or Head operation was attempted.
- GitHub Actions for this R3 commit: pending until push.

## Acceptance

- Code implementation and focused tests: complete for the R3 code-only scope; **full audit `PASS_CODE` is not claimed** because real Owner/manifest rows and accepted publication bindings are unavailable.
- CI: pending.
- PG and page parity: not verified. All page projections explicitly retain uncovered inputs and degraded/pending status.
- Production: not in scope and unchanged. No 28765 deployment or production Head switch.

## Next stage

1. Push this code-only commit and record the matching focused CI result on Issue #2 and PR #3.
2. When the approved existing read-only PG config is available, inspect final schema, Head/source/Owner bytes and role without printing the DSN.
3. Resolve page field parity and global requiredness against live producer contracts; test draft DDL/CAS only in an authorized isolated PG environment.
4. Keep research-snapshot divergence and governance commit review separately tracked; do not merge or claim production acceptance.
