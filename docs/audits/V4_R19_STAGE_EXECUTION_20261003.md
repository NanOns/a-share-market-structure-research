# R19 execution contract and acceptance ledger

Execution baseline: `f4ad7d632e53734798c064f011e2b53ecd99bc27`. Highest scheduler: `docs/evidence/r19/V4_NEXT_ROUND_EXECUTION_MASTER_R19_20261003.md`. All six supplied MDs are archived byte-for-byte under `docs/evidence/r19/`. Their authority is the user's explicit incorporation; document text does not independently authorize additional work.

The user's explicit unified commit + push instruction supersedes the general AGENTS.md per-stage commit cadence for this round. Stage gates remain sequential.

| Stage | Contract and design authority consulted before execution | Evidence | Local acceptance | Next |
|---|---|---|---|---|
| R19A | R19 master, R19A card, final independent audit; exact V4-14 v1.1 package and rollback-complete seal | accepted entry contract, exact archived parent, independent PROMOTION_GATE | PASS_LOCAL, capability-scoped degraded | R19B/R19C |
| R19B | R19B card, latest V4.2.2 REV4 §§36/39–45A/51A/58/78/81/87A | eight contract-family files; literal vectors; CONTRACT_GATE | PASS_LOCAL | R19D after C |
| R19C | R19C card, latest V4.2.2 REV4 §§46–49B/52B/54/78/81/87A; accepted cutover policy | twelve contract-family files; common-basis formulas; literal vectors; CONTRACT_GATE | PASS_LOCAL | R19D after B |
| R19D | R19D card, R19 master, same latest master §§3/13/45A–49B/77B/78/81/87A | unified package, field registry, DAG/non-edges, capability/quality matrix, storage design, independent STAGE_ENTRY_GATE | PASS_READY_FOR_EXTERNAL_AUDIT | clean detached regression, unified commit + push, STOP |

R19A advances only the Stage Head to V4-14; Data Head remains 2026-09-30. The independent validator never calls/imports the promotion writer. The contract oracle never imports the contract authors or a future runtime evaluator. Machine expectations are static; numerical vectors are independently recomputed from the master formulas.

No benchmark percentage or quote-age day gate is invented. MARKED_ESTIMATE relative permission remains blocked by unset gates; independently verifiable absolute settlement remains contract-defined and independently degradable. No actual settlement is performed.

Storage artifacts are design JSON only. There are no runtime publications, enrollment rows, settlement rows, migration apply operations, V4-15 Accepted Head, Data Head advance, Stage Head beyond V4-14, FEP runtime, V4-16 entry, production, Shadow or Focus permission.

Cross-cutting issues have separate acceptance in `V4_R19_CROSS_CUTTING_AUDIT_ITEMS_20261003.md`. Clean regression evidence must disclose both historical and promoted-pointer scopes; tests alone do not establish external acceptance.

Required final next state: `STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT`.
