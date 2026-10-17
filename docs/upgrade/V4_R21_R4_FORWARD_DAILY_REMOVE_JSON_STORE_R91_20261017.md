# R91: remove the unused JSON Forward store

`src/workbench_service/forward_daily.py` no longer defines `HistoricalForwardStore`, which read and appended JSON facts in a workspace directory. Repository-wide Python reference search found no callers of that class. The same module retains `ForwardStore`, backed by the append-only PostgreSQL fact store.

The original matrix row `V4-BCA-R2-4e1ef2b5c60d80049430` is **not closed** in this batch. Its reference inventory still records a possible dynamic `v4_service` chain, so removing the unreferenced class alone does not prove that every runtime route has migrated. The exact row remains open until that runtime reachability is reconciled.

Original callsite accounting remains **0 / 266 formally completed; 266 / 266 remaining**. No live PG business read/write or acceptance is claimed.
