# R4 source policy migration

`v4_market_source_fallback_policy_v1.json` and its acquisition registry grant bounded public-source acquisition and corrected staging only. They do not modify V2 source freezes or accepted snapshots. RAW, provider QFQ and native affine QFQ retain separate coordinates. A successful query, empty factor list or matching close cannot grant an ATR/MA coordinate.

The normal `run_v4_current_daily.py` entry invokes DM01 with `--active-source-policy`. This executes local reads, official requests, independent BaoStock probes and membership observation capture before canonical owner admission. Direct DM01 callers can use the same flag. A blocked official download is `SOURCE_CAPTURE_BLOCKED`, not `NO_DATA_EXISTS` or an identical-input NOOP. The extended verified exchange calendar discovers completed dates beyond the accepted-data calendar cutoff.

`execute_source_acquisition_r4.py` runs the four-date historical/new-session acquisition. Successful query bytes are checkpointed by method/parameters. Resuming the same output directory preserves earlier receipts; a genuinely new observation run should use a different output directory. One shared Shanghai-day request ledger enforces serial sessions, soft/hard budgets and bounded calls. Provider errors and local persistence errors are distinct; successful provider calls are not repeated because checkpoint persistence fails.

Every DM01 active capture freezes current membership input bytes by digest and records time. Historical effective date and first availability remain unknown without provider proof. This pipeline hook is automatic on daily execution; no recurring OS/app scheduler has been installed.

Corrected fallback candidates require identity, session, status, OHLCVA, independent overlap, accepted source tolerances and an explicit native coordinate before derived-price arithmetic. Candidate staging is not production publication. Independent admission of new source/producer versions is required before successor CAS. See the separate R4 audit register for unresolved work.
