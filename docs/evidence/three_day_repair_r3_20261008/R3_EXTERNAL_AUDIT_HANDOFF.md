# R3 external audit handoff — 2026-10-08

## Disposition

Scoped result: **DEGRADED_PASS** for the repair work that can be completed from the accepted local owners and frozen contracts. The R3 task is **not globally complete**. No new field or domain was published, Phase 0 remains `DEGRADED_PASS`, and scanner work did not start. The existing successful 9/30 release remains the immutable live predecessor.

## Completed and independently verifiable

- Core owners for 2026-09-28/29/30 contain 5222/5223/5224 rows in target-native coordinates. Independent MA20, ATR20 and ret5 oracles have zero mismatches; 30 anti-future checks pass.
- Isolated corrected V4-04 Profile owners now exist for 9/28 and 9/29. Their lineage is `RECONSTRUCTED_CORRECTED`, `AS_RECORDED=false`, and they are not production-bound. The prior 9/28 candidate was checked against corrected Core across 195,916 observed numeric values with zero mismatches. The 9/30 production Profile remains exactly consumed by 5,213 stock reads. The preserved source diff separates 176 actual-traded rows/day with unproved adjustment capability from 12/12/11 accepted suspensions without bars; the R3 Profile unknown totals for 9/28–29 reconcile to 176+12 and remain fail-closed.
- Sector same-day fields preserve the 2,646/2,646 independent numeric pass. All 378 historical rotation rows remain UNKNOWN where dated T-1 owners are not proven. The generic history reason is split into three explicit causes and 71 sector/runtime tests pass.
- Focus/Forward frozen state remains 117 enrollments, 585 PENDING plans, and zero due. The real two-day journal was replayed in isolation; the current completed-session check returned a zero-source-request NOOP.
- Existing API routes return one context token and authority digest. No production pointer changed.

## Blockers requiring an external source or a separately accepted owner

1. The bounded accepted V4-08 membership store has 50,162 facts for 2026-09-30 only. It has no accepted effective-dated member facts for 9/28 or 9/29. This local search does not prove that external official records do not exist. Minimum input: source revision plus sector/security identities, effective trade date, provider-available timestamp, system-available timestamp, source bytes/hash, and an accepted membership publication. Until then historical rotation/entry/exit/retention remains UNKNOWN; do not reverse-engineer 9/30 membership into earlier dates.
2. V4-12 structure semantics are mapped, but the live 9/30 snapshot still has 0 known of 5,213 for each of the seven structure fields. The real R13 candidate has no anchors because the target-date and exact T-1 Core/ATR/MA20/prior-high owner chain is not accepted into V4-12's registered source boundary. The runtime contract expressly denies production/shadow/cutover permission; a corrected isolated Core candidate does not itself grant owner admission. Minimum input: accepted target-coordinate Core and prior owner publications plus explicit runtime source admission.
3. V4-13 is freeze-only (`runtime_implemented=false`) and has no accepted consumer artifact for `relative_sector_state`. Minimum next work: implement the versioned read-only runtime against exact-date membership and accepted Base/Seed/sector context, validate real values, then request scoped admission.
4. Live 9/30 `relative_market_state` still lacks an accepted RPS `T-3` endpoint for 9/25. The 9/28 and 9/29 isolated Profiles use accepted corrected RPS endpoints, but first historical availability is unproven, so their lineage remains reconstructed and cannot be treated as historical PIT.
5. Focus/Forward has real two-day state comparison and fixture coverage, but the complete real exit/re-entry/Anchor/path/outcome and due settlement event matrix has not been demonstrated. All 585 live plans are correctly pending because none is due.
6. Future daily membership capture remains an operational follow-up. Existing capture tooling is scoped to a frozen 2026-09-30 audit source contract and is not a date-general accepted daily producer; no recurring production capture schedule or generalized accepted publication has been activated.

## Release boundary and next stage

Do not promote the isolated 9/28–9/29 Profile owners, structure candidates, or historical sector values. Keep the current seven-domain joint authority and snapshot hash unchanged. Continue with the minimum accepted source/owner prerequisites above, including a forward-only daily membership capture under a versioned source contract. Re-run the affected field-level real oracles, full real Focus/Forward E2E, same-token API readback, failure injection, stale-CAS and exact-predecessor rollback tests before requesting external audit acceptance.

## Evidence and commit

The detailed per-stage contract, before/after values, test results and evidence hashes are in [`R3_CONTINUOUS_EXECUTION_PROGRESS.json`](R3_CONTINUOUS_EXECUTION_PROGRESS.json). The 176/day adjustment capability crosswalk is [`R3_QFQ_CAPABILITY_CROSSWALK.json`](R3_QFQ_CAPABILITY_CROSSWALK.json). Main evidence directory: `docs/evidence/three_day_repair_r3_20261008/`.

Implementation/evidence commit: `0bb8df116da9d654dc70c2b0ee4620ffc831f8e3`. The handoff record is `633903fe2b80c460a218b4d21a358dd3c22cb348`. Both `codex/v4-system-reform` and `codex/v4-fp14-r2-repair` were verified at this SHA after push (frozen starting heads were `e85ce0fd177e7d8604bdb5f458cee387afbf03ae`). Push makes the evidence available for review; it is not external acceptance or authorization for another gated stage.
