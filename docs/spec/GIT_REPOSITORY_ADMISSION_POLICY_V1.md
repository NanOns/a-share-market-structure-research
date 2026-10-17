# Git repository admission policy v1

## Purpose and scope

This policy governs new and changed Git blobs. It is shared by the local pre-commit hook and CI; it does not rescan full Git history on every commit. The migration work package separately inventories reachable history and public secret exposure.

## Allowed content

The default allowlist is executable source and tools in `src/`, `scripts/`, `tools/`, root launchers matching `run_*.py`, `OPEN_*.cmd`, or `START_*.cmd`, migrations, tests, minimal fixtures, configuration, the formal requirements/design/specification/upgrade directories, and the root project guides named in `tools/git_repository_policy.py`. A `docs/upgrade/` task card, execution/continuation record, receipt, or evidence document is process material and is blocked when modified; formal specs and contracts remain admissible. Versioned configs may describe a candidate, but a file status never establishes runtime acceptance. `reports/` is denied except a versioned comprehensive report matching `reports/stage/V4_<stage>_COMPREHENSIVE_TEST_REPORT_<YYYYMMDD>_R#.md`. That report must use the front matter fields `stage_id`, `code_sha`, `test_scope`, `conclusion`, and `approval_status`.

Runtime data, logs, build products, evidence, audit/task outputs, database files, bulk CSV/TSV, archives, and unapproved file types are denied. Renaming such content does not make its payload admissible. A necessary test fixture belongs under `tests/fixtures/`, must be small, and must have a clear regression purpose.

## Blob and source checks

The maximum raw blob size is 1 MiB. A larger formal requirement or comprehensive report is blocked for explicit human review; it is not accepted by an LFS pointer. LFS pointers must resolve to a local object whose size and SHA-256 match the pointer. The admission tool does not download LFS objects.

Changed blobs are checked for credential patterns, machine-specific absolute paths, production references to historical evidence/report inputs, fixed security/sector branch candidates in `src/`, and dynamic SQL candidates. Findings report only a path and rule, never the detected secret value. Test code may name real securities and dates.

## Invocation and interpretation

- Local pre-commit: `python tools/git_repository_policy.py --staged` reads the staged index blobs.
- CI commit range: `python tools/git_repository_policy.py --diff-base <base> --diff-head <head>` reads the changed blobs from the head commit, including renamed paths and Chinese/space-containing names.
- A deletion has no new blob and is not scanned. For a rename, the destination path and its committed blob are checked.
- `MANUAL_REVIEW_REQUIRED` is a blocking result until the oversized formal text receives a separately reviewed, explicit policy change. This initial policy has no size exemptions.

The checker is a targeted guard, not a proof of production readiness, PG migration acceptance, history sanitization, or release approval. A passing policy check does not authorize history rewriting, production cutover, or physical cleanup.
