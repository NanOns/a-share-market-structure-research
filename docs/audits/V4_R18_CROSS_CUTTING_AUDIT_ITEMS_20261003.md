# R18 independent audit items

Execution baseline: `47b7f72f374c059f35a66bf2fe298a3ec5fe7efc`.

| Item | Scope / evidence | Acceptance and disposition |
|---|---|---|
| R18-AUD-01 | Historical first availability and membership coverage; real scoped receipt and capability boundary in `reports/r18c/` | OPEN. Historical PIT effectiveness is NOT_GRANTED. Forward PIT membership on 2026-09-30 cannot establish earlier membership or AS_RECORDED history. Separate external evidence is required. |
| R18-AUD-02 | Legacy Amount A / B2 / historical LOO gaps retained in exact r6 publications | OPEN, inherited accepted upstream capability. No algorithm change or raw fallback; UNKNOWN/NOT_IMPLEMENTED remains scoped to those components. Independent audit acceptance is separate from Replay Gate B engineering. |
| R18-AUD-03 | Early D0 interface is tied to one accepted data-head date; full synthetic replay uses the unchanged accepted scenario-scoped detector AST with an engineering-only transport validator | PASS_LOCAL adapter boundary; no real facts admitted through synthetic adapter. Exact owner business statements and frozen scanner/parameters unchanged. Real replay reads exact promoted publications. External candidate audit required. |
| R18-AUD-04 | R17 contract-era assertions assumed runtime absence | Historical assertion maintained using exact R17R1 external authorization. Five frozen V4-14 contracts unchanged. No V4-14 Accepted Head or runtime acceptance granted. |

Synthetic input availability timestamps are virtual fixture metadata. They are not historical source availability observations. PID and wait receipts prove actual process boundaries; business expectations come from the frozen books and the independent counter/identity oracle.

Earlier `full_dag` and `full_dag_r2` publication attempts remain immutable and superseded. Only `full_dag_r3/completion_gate.json` is the R18B candidate gate. The first attempt lacked persisted anchor lineage; the second retained it but the driver incorrectly required revision metadata to have identical output digests. Corrected r1/r2 checks require equal prior refs, state rows, logical events and counters. Determinism requires the same input and same revision in two fresh processes.

NEXT: clean detached validation, unified commit and push, then STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT.
