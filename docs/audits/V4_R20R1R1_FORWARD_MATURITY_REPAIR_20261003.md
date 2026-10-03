# R20R1R1 R2 forward maturity debt repair

Execution baseline: `555409d79c58517761472531404f0ee5cccd81af`.
Authority: supplied R20R1R1 R2 master, repair task, and independent audit R2, preserved literally in `docs/evidence/r20r1r1/`.

## Independent audit items

P0 reachability: the previous debt mechanism conflated real-time cohort maturity with settlement runtime maturity. Versioned T0 lineage binds the real sealed V4-14 September 30 publication, enrollment, producer freeze receipt, and literal archived Data Head. A RECONSTRUCTED_ASOF T0 may prove settlement runtime only with exact future accepted Data ancestry, source endpoints, observed outcome, frozen evaluation basis and independently recomputed values. REALTIME_ACCEPTED_COHORT_MATURITY and HISTORICAL_PIT_EFFECTIVENESS remain NOT_GRANTED.

P1 horizon coverage: proofs are append-only per enrollment/horizon/due date. OPEN, PARTIAL_MATURITY_EVIDENCE, FULL_REQUIRED_HORIZONS_PROVEN are derived from exact receipts for required horizons 1/3/5/10/20. Partial proof cannot unblock unqualified maturity claims. Corrections append a next revision, preserving FIRST_OBSERVED and updating LATEST_VALIDATED. Existing evidence is revalidated through explicitly archived Data ancestry.

## Evidence and acceptance

`reports/r20r1r1/FORWARD_MATURITY_SCOPE_GATE.json` and `R20R1R1_INDEPENDENT_ORACLE.json` bind current facts and isolated persisted positive transitions. The independent oracle uses Decimal source recomputation and does not call the debt writer or Radar/Cohort/Settlement evaluators. Exact caller booleans, synthetic lineage, price-only history, unaccepted endpoints, premature reads, mixed basis, corrupt metrics, invented horizon coverage and historical-PIT upgrades fail closed.

Engineering fixtures exercise the real immutable T0 lineage with isolated future accepted-source representations. These are labeled ISOLATED_ENGINEERING_REACHABILITY_ONLY and never upgrade current real capability. Current real maturity remains NONE with proved horizons [] and unproved [1,3,5,10,20]. Unrelated development is not blocked by this debt.

The clean detached regression must run all current R20, all R20R1 and all new R20R1R1 suites with no skip/deselection. Its exact tested Git commit is published through an immutable tag; final evidence seal binds that source and regression.

Acceptance: PASS_LOCAL for the repair and isolated forward reachability, pending independent external audit. Prior R20 and R20R1 scope decomposition remain PASS_KEEP. No accepted algorithms, runtime formulas, identity semantics, historical evidence, Stage Head or Data Head change.

Next: STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT. V4-15 Accepted Head remains NOT_CREATED; Production, Shadow, Focus, V4-16 remain false.
