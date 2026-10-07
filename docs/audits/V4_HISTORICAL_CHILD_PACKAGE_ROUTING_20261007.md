# V4-HISTORICAL-CHILD-01

Scope: historical R18 fresh-process workers must resolve the same exact accepted checkout as the parent. This is separate from product visibility and capability permission gates.

Evidence: the fresh complete V4 execution exposed REPLAY_ENVELOPE_AUTHORITY_MISMATCH in tests/test_r18b_persisted.py::test_fresh_process_pair_revision_and_determinism. The profile loader had imported current scripts helpers, leaving current package paths cached in the child.

Repair: after installing the exact historical input profile, evict current scripts/workbench_analysis package caches and prioritize the historical root and src paths before run_module. Frozen historical source bytes and accepted authorities are untouched.

Acceptance: original cross-process determinism test plus the fresh complete V4 scope, with exact persisted envelope, revision and predecessor checks. Status: CLOSED_LOCAL; original persisted determinism test and fresh complete V4 regression passed. Independent external acceptance remains separate.
