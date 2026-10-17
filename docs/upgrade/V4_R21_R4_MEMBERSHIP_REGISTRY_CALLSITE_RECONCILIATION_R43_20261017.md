---
stage_id: V4_R21_R4_MEMBERSHIP_REGISTRY_CALLSITE_RECONCILIATION_R43_20261017
branch: codex/v4-workspace-cleanup
status: FOUR_OWNER_CALLSITES_RECONCILED_TO_EXISTING_PG_BRANCHES
p1_business_reads_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 27
ingress_adapters_open: 8
other_callsite_rows_open: 231
unmapped_reference_edges: 22
live_pg_readback: NOT_RUN_NO_COMPLIANT_READ_DSN
next_stage: continue actual daily QA and predecessor authority PG migrations; retain formal P1 count until Head readback
---

# V4 R21-R4 membership and registry callsite reconciliation

Date: 2026-10-17 (Asia/Shanghai). Reconciled exact baseline rows against R37 startup membership validation and R39 builder-registry PG wiring. The latest applicability documents reviewed were the R37 and R39 reports and their code contracts.

## Callsite reconciliation

- `V4-BCA-R2-47795b612d4ae4d06d1b`: membership snapshot/source validation now uses the Head-bound PG membership and identity authority when present.
- `V4-BCA-R2-ce030238606ae3e34b44`: Reader initialization obtains the Head-bound PG context snapshot when `native_membership_reference` is present.
- `V4-BCA-R2-8c8d9130fd8ad10bc41f`: HTTP context uses the cached PG context snapshot in that authority mode.
- `V4-BCA-R2-0a049f1b9db3690e759d`: successor registry validation uses the Head-bound PG operational-registry reader when its authority key is present.

Each is marked `IMPLEMENTED_PG_ONLY_READ_CODE_PENDING_INVENTORY_RECONCILIATION`, not formally complete. The legacy exact-file route remains only for a Head without the corresponding PG authority. The current accepted Head carries neither membership nor operational-registry authority.

## Verification and limits

- Focused code-path selection across Reader startup/context, membership context, BFF descriptor and registry authority tests: **10 passed, 10 deselected**.
- These tests establish the code branches and fail-closed behavior at controlled PG-reader boundaries. No live PG query, service, or current Head readback was performed.

## Accounting

Original P1 baseline: **266** (200 Owner, 28 other-business, 38 external-source). Formally complete **0 / 266**; remaining **266 / 266**. The four exact code-path rows move the matrix from 23 to **27** code-level PG paths awaiting live reconciliation; other open rows move from 235 to **231**. The 8 ingress adapters and 22 unmapped reference edges remain. No formal P1 row closes.

## Next stage

Continue migrating daily QA receipts/oracles and predecessor Head reads to exact Head-bound authorities where source identity and contracts are known. Formal acceptance still requires permitted same-T0 PG readback and full reference inventory reconciliation.
