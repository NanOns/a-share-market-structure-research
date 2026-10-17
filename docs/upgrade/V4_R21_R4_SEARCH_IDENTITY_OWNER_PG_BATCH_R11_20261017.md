---
stage_id: V4_R21_R4_SEARCH_IDENTITY_OWNER_PG_BATCH_R11_20261017
baseline_sha: 9b66a3c4ef7dd60c4e9eb208e44e7fbb1f74451d
branch: codex/v4-workspace-cleanup
status: SEARCH_IDENTITY_PREPARATION_USES_CANDIDATE_PG_OWNER_LIVE_APPEND_OPEN
callsite_id: V4-BCA-R2-cebee7277badb03eb82f
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
live_pg_append: NOT_RUN_NO_AUTHORIZED_WRITER
next_stage: migrate daily executor identity preflight and continue exact Owner/other-business IDs
---

# V4 R21-R4 search identity Owner read batch

Date: 2026-10-17 (Asia/Shanghai). This batch replaces a global file Head lookup with the candidate's existing PG identity Owner.

## Implemented

- `prepare_search_identity` now validates that the membership-reference authority is bound to the candidate T0, resolves its current identity source binding through `identity_source`, and reads the exact rows through `read_identity` from the PG Owner. It appends those same rows and source binding to the search-identity PG reference.
- Removed its `V4_DATA_ACCEPTED_HEAD.json` selection and file read. Missing PG authority fails closed. No T0 substitution or file fallback was introduced.
- Matrix ID `V4-BCA-R2-cebee7277badb03eb82f` has exact code/test evidence, but its formal status remains `ACTIVE_INGRESS_ADAPTER_OPEN`. Live source identity parity is still required.

## Verification and limits

- **69 passed** across membership-reference, Owner manifest, PG publication and BFF candidate tests. Module compile and `git diff --check` passed.
- Tests use controlled PG reader/Owner functions; they do not prove live identity rows or perform PG writes. The PG append call was not invoked.

## Accounting

Original P1 baseline **266**. Formal closed **0 / 266**; remaining **266**. Inventory totals remain OPEN 237, ingress-open 8, PG-code-pending-live-read/reconciliation 21; unmapped reference edges remain 22.

## Next stage

Continue replacing executor identity preflight with a publication-bound PG mapping that proves `source_security_key`, board scope and dates. Continue other Owner and business IDs while the live writer/reader gate remains open.
