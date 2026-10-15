# V4 R7 Forward Signal Specification R1

## Stage contract

- Stage: WP0 — migrate the four Forward display contracts and freeze the independent signal definitions.
- Task contract: `V4-R7-FOUR-MODULE-DATA-FIRST-20261014/R1` supplied by the user on 2026-10-14.
- Code base observed: `codex/v4-fp14-r2-repair`, HEAD `c9e49df720da58ecb3e90eae53b9fdd8e11aab07`.
- The task card's frozen SHA `e44a55609168344b820138efc01d53d76b7312df` is not an ancestor of this checkout. The histories share `fbd23a6ba08d0948fe7ad421d1765fe363648522`; HEAD adds later usability and shadow-preflight evidence. Work proceeds from current HEAD and preserves the existing local changes.
- Runtime observed at `127.0.0.1:28765`: package `V4_PACKAGE_1.1.6_44d446ed72bd`, accepted T0 `2026-10-13`, token `974c60e0095de0e37e2089edca710876d25f43de604fecafd115b675745375c3`.
- Runtime data lineage is `RECONSTRUCTED_LATEST_MEMBERSHIP`, with `AS_RECORDED=false` and `PIT_ELIGIBLE=false`; this limits Lane H claims to retrospective research.

## Frozen research rules

The machine-readable source of truth is [`config/v4_forward_signal_definitions_r7.json`](../../config/v4_forward_signal_definitions_r7.json). This document explains its scope and migration effects.

### STOCK_RIGHT_STRUCTURE_EVENT_R1 / 1.0.0

Enumerate every accepted stock identity, retaining `MATCH`, `NO_MATCH`, and `UNKNOWN` in the denominator. A breakout is a T0 close strictly above the accepted prior completed 20-session high. A pullback confirmation requires a prior-session breakout, a T0 low within 2% above the accepted prior high, a close at or above that level, and an observed false `core_price_damage`. A missing factor, fewer than 20 prior observations, unknown damage state, or invalid source identity yields `UNKNOWN`; it never yields `NO_MATCH`.

Board scope is carried as an identity dimension. This rule does not use model ranking, Focus membership, Radar rank, or a generated score. The prior high and T0 prices must share the same native T0 price coordinate. Sector links are annotations and do not determine stock inclusion.

### SECTOR_STRENGTH_TRANSITION_R1 / 1.0.0

Enumerate every accepted sector. A strengthening match requires positive RS5 and RS20, positive breadth returns over 5 and 20 sessions, quote coverage of at least 80%, and a comparable prior state that is weaker than the current state. Missing/unknown inputs, missing prior, or incomparable membership produces `UNKNOWN`. Historical rows based on the current member snapshot are `RECONSTRUCTED` with `MEMBERSHIP_RETRO`; only source-frozen live rows can be `AS_RECORDED`.

## Time and outcome semantics

- Lane H uses `RETROSPECTIVE_RESEARCH`; its `captured_at` is the actual reconstruction clock. It does not imply first availability, strict PIT, or out-of-sample status.
- Lane L uses the actual accepted Head and source capture times. A record after the official daily cutoff is retained as `LATE_OBSERVED_NOT_PIT`, never backdated into `LIVE_OOS`.
- T+1/T+3/T+5 are accepted exchange sessions. Historical settlement uses nominal raw close-to-close change and explicitly carries corporate-action limitations. Online outcomes remain pending until their official session arrives and the quote source verifies.
- The rules describe benchmark events for research. They do not produce orders, model probabilities, or Priority V1 changes.

## Legacy contract migration

For these four research read domains, prior `NO_AUTHORIZED_COHORT_OWNER`, `COHORT_READ_GRANT_MISSING`, `NO_AUTHORIZED_COHORT_SETTLEMENT_OWNER`, and `MODEL_OR_PERMISSION_NOT_READY` display gates are replaced by data availability, rule completeness, model support, and operational state. Legacy fields remain readable for compatibility and audit but do not gate Lane H descriptive research or model metadata display. Existing E5 training evidence, no-lookahead rules, ENTRY/DAILY separation, and the ban on automatic Priority V1 promotion remain active.

This change is scoped to research display and collection. It does not grant trading, historical PIT, algorithm upgrade, or external adjustment authority. It does not rewrite any sealed historical task or accepted Head.

## WP0 evidence and acceptance

- Evidence: current runtime context and source hashes are recorded in `docs/evidence/v4_r7_forward_20261014/STAGE_LEDGER.json`.
- Acceptance: both rule families, population, status vocabulary, timestamp semantics, source lineage, and prohibited uses are versioned in JSON; the task-card migration boundary is versioned here.
- Result: implementation-in-progress. The rules are frozen for this task; future changes require a new rule version and sequence.
- Next stage: WP1 — materialize Lane H from accepted historical inputs in PostgreSQL, then reconcile row counts, prices, calendar sessions, and source digests.
