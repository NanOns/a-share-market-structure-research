---
stage_id: V4_R21_R4_DAILY_EXECUTOR_PG_ONLY_CONTRACTS_R83_20261017
branch: codex/v4-workspace-cleanup
status: DAILY_EXECUTOR_CONTRACTS_PG_ONLY_CODE_VERIFIED_LIVE_PG_PENDING
p1_baseline: 266
p1_formally_closed: 0
p1_formally_remaining: 266
code_level_pg_read_paths_implemented: 53
open_callsite_rows: 203
ingress_adapters_open: 10
remaining_open_or_ingress: 213
live_pg_read_or_write: NOT_RUN_NO_COMPLIANT_RUNTIME_ACCESS
---

# Daily executor approved-contract reads

The active daily executor no longer opens runtime contract files for the TDX read-only source contract or BaoStock runtime-receipt path contract. Both flow through the approved PostgreSQL contract registry and retain contract ID/version validation. `V4_DAILY_CONTRACT_SOURCE=FILE` now fails closed. The market-calendar `FILE` mode and the separate candidate-research reader are unchanged and remain open work.

The tests replace the registry result at the loader boundary, then exercise the real daily executor contract consumer. They also verify namespace and expected database identity are passed into the approved registry reader, and that FILE authority mode is rejected.

Verification: **34 passed** across the daily executor, old-identity preflight, pre-next-T0 executor chain, and contract-registry reader selections. The R8 broader integration module could not collect in this interpreter because `cryptography` is unavailable; no runtime package was installed. The added focused consumer test covers the PG registry handoff without that unrelated import.

This batch does not map to an exact original 266-row caller path because the contract-file access was introduced outside the baseline callsite row. Therefore no stable ID or formal count is changed: **0/266 formally complete; 266/266 remain**; **53** code-level PG paths pending live reconciliation; **203 OPEN**; **10 ingress-open**; **213 open or ingress**; **22 unmapped reference edges**. This code result does not claim live contract approval, PG identity, Head/T0 acceptance, or business acceptance.

Next: remove the remaining explicit FILE authority mode in the other daily contract consumers, map current callsites against the original stable inventory, and continue the 28 other-business and 200 Owner migration batches. No PG write or catalog access was available or attempted.
