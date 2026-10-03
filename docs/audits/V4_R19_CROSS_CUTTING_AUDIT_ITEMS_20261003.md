# R19 cross-cutting audit items

These items have separate scope, evidence and acceptance from R19A–D. They do not grant runtime, production, Shadow or Focus permission.

## R19-AUDIT-01 — Historical byte identity portability

Scope: earlier accepted-head files can have CRLF worktree bytes while their Git blobs have LF. Scope is evidence portability, not business algorithm changes.

Evidence: `reports/r19a/PROTECTED_WORKTREE_BYTES.json`; independent promotion validator compares both exact current byte digests and canonical Git content. R19 never rewrites protected heads. The clean runner must hydrate matching baseline byte representations with explicit hash checks and must report clean Git status without index bypass flags.

Acceptance: OPEN for comprehensive upstream evidence portability review. R19 local verification does not close this audit. Next: independent external audit of historical byte representation governance.

## R19-AUDIT-02 — Historical validators and stage-specific readers

Scope: historical R17/R18 validators and V4-13/V4-14 replay entry readers assume Stage Head is exactly V4-13. R19 promotes the formal pointer to V4-14, so those old stage assertions are historical assertions. The frozen code, full_dag_r5, consumption mapping and rollback logic must remain untouched this round.

Evidence: `src/workbench_analysis/v4_13_accepted_contract_package.py` rejects stage ranges other than V4-13; `scripts/validate_r17r1_active_closure.py` checks the V4-13 Stage Head; `scripts/v4_14_rollback_oracle.py` requires no real V4-14 Accepted Head. These assertions cannot truthfully be run against a promoted pointer as though promotion never happened.

Acceptance: OPEN; require a separately authorized stage-aware reader/validation entry contract before future runtime consumption of the promoted pointer. R19 contract binding reads exact accepted owner artifacts without invoking these runtime readers. R19 regression uses two explicitly disclosed clean detached contexts: all 1168 retained upstream/replay/rollback tests on the audited baseline, and R19 promotion/contract tests on the new candidate source. The runner proves all retained test, business, replay and oracle blobs are unchanged. No test is skipped or deselected, no historical assertion is weakened, and no current-pointer runtime compatibility claim is made.

Next: independent external audit must decide the additive reader-governance work required for runtime entry. This round ends at contract completeness, and V4-15 runtime remains NOT_IMPLEMENTED.
