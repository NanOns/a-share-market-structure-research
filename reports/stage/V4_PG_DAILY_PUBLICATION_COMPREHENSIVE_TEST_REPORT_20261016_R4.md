---
stage_id: V4_PG_DAILY_PUBLICATION_R4_20261016
code_sha: 4fa5dd2bc8f4cf28668a66d65dd1095c61687c6e-base-plus-R4-worktree
test_scope: source-manifest-producer-candidate-reader-page-projection-minimum-publish-plan
conclusion: 46-focused-tests-pass; live-source-authority-page-parity-and-PG-unverified
approval_status: CODE_ONLY_REPAIR_AUTHORIZED
---

# V4 PG 日发布 R4 阶段报告

- Stage: `V4-PG-DAILY-PUBLICATION-EXTERNAL-REPAIR-20261016/R4`
- Audit baseline: `4fa5dd2bc8f4cf28668a66d65dd1095c61687c6e`
- Branch: `codex/v4-workspace-cleanup`
- Scope: source manifest producer/candidate/reader closure; current-page PG field mapping/parsing; minimum daily candidate planning.
- Upgrade documents consulted: R3 daily-publication repair/report; R2 repair; R8 unified-source repair; V4 runtime performance repair; production-data migration design; daily operations/rollback contract.

## Results

- `build_source_manifest()` is the shared versioned producer codec. Candidate recomputes the complete 13-field source set, checks the persisted consumed-source bindings, T0, tombstone, revision digest and clock rules, and rejects absent or mismatched evidence. Reader reuses the same codec and retains acceptance-time checks.
- Persisted-field map: `publication_consumed_sources` provides source key, revision id and recorded digest; joined `source_revisions` provides logical fact, revision, revision digest, effective window, provider/observed/ingested/system clocks and tombstone. The schema does not bind `source_packages.accepted_scope` to `source_revisions`; no active canonical daily producer writer/sample was verified. Therefore live source authority remains open.
- Summary reads active `event_observations` by exact publication id and parses only present declared payload keys. Entity reads lifecycle facts only when their source revision is in the publication consumed-source set. Radar, sector and health parse verified existing Owner supplements. Daily prices/names, sector membership, replay, cohort and settlement remain explicit gaps. No page can claim full parity or READY.
- `V4_DAILY_PUBLICATION_MINIMUM_R1` now gives the candidate planner a reachable, versioned READY path from validated source rows, computation/state identity, one database identity and the currently proven optional-owner contract. Head planning remains pure and reports no write execution.

## Validation

- Command: `python -m pytest -q -p no:cacheprovider --basetemp=G:/codex_tmp/test_temp/v4_daily_publication_r4 tests/test_v4_pg_publication_candidate.py tests/test_v4_pg_publication_owners.py tests/test_v4_pg_publication_contract_static.py tests/test_v4_pg_source_manifest.py`
- Result: **46 passed**.
- PG environment: `DB_READ_ENV_UNAVAILABLE`; both approved read DSN environment variables and the writer DSN were absent. No connection was attempted; no credentials were printed.
- PG/SQL transaction tests and GitHub Actions: pending; no live database or CI result is claimed here.

## Acceptance and next stage

- Code / focused deterministic tests: pass for this scoped implementation.
- Live PG read, source authority, page parity, SQL transaction, CI and production acceptance: not established.
- Blocked actions: production PG DDL/DML, accepted Head change, 28765 deployment/scheduling, history force-push, physical deletion.
- Next: commit and push this scope, record CI, then provide approved read-only catalog/source evidence and resolve the source package-to-revision producer binding. Preserve the open page gaps until publication-bound relations exist.
