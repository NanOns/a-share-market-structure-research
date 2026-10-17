---
stage_id: R21-R4-contract-registry-xml-dtd-encoding-guard-r65
branch: codex/v4-workspace-cleanup
status: XML_DTD_ENTITY_GUARD_HANDLES_UTF16_UTF32_WITHOUT_CHANGING_REGISTRY_SCHEMA
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 48
open_callsite_rows: 210
ingress_adapters_open: 8
remaining_open_or_ingress: 218
unmapped_reference_edges: 22
---

# Contract registry XML encoding guard (R65)

Date: 2026-10-17 (Asia/Shanghai).

## Change

Both publication-pinned and current-approved contract readers now reject XML DTD and ENTITY declarations after checking raw bytes and decoding the standard UTF-8, UTF-16, and UTF-32 forms, including BOM and explicit byte order. The prior check inspected only ASCII byte sequences, so the NUL-interleaved UTF-16/32 forms could pass. This is a reader-side validation correction; registry SQL, approval ordering, publication bindings and database state were not changed.

## Verification and limits

- Registry and SQL focused regressions: **25 passed**, including UTF-8 DTD, UTF-16 DTD, and UTF-32 ENTITY negative cases.
- Repository selected V4 PG/consumer workflow suite: **309 passed**. Tests use controlled PG reader fixtures; no live PG catalog/read/write or full business acceptance was performed.
- R64 code/test CI remains green on current R64 head: Push [39024797612](https://github.com/NanOns/a-share-market-structure-research/actions/runs/39024797612), PR [39024801715](https://github.com/NanOns/a-share-market-structure-research/actions/runs/39024801715). R65 CI is pending its push.

## Original 266-item accounting

No baseline callsite ID changes status in this guard. Formal completion remains **0/266**, remaining **266/266**; matrix totals remain **48** code-level PG paths pending reconciliation, **210 OPEN**, **8 ingress adapters open**, **218 open or ingress**, and **22 unmapped reference edges**.

## Next

Continue the contract registry approval lifecycle/SQL compatibility work after an authorized read-only catalog reconciliation, then resume actual PG consumer migration. Do not treat grammar tests or reader fakes as live approval-state acceptance.
