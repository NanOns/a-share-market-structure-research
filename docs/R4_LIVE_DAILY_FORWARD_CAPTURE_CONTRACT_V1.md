# R4 Live Daily Forward Capture Contract V1

Version: `r4-live-daily-forward-capture-v1.2-model-preflight`  
Parent contract: `r4-forward-observation-contract-v1.1`

The sole live entry is `python run_live_forward.py --date latest`. Before resolving or publishing V1, it verifies the approved V2 economic-model identity and fails closed with `MODEL_IDENTITY_PREFLIGHT` if any rule or contract changed. Its remaining fixed order is: resolve valid TDX cutoff; run/verify V1; invoke the approved five V2 structure entrypoints; invoke approved Priority V2; verify runtime identities; immutably append observation; compute state transitions over current/prior union; append only due outcomes; publish the daily receipt.

The natural date is never evidence of a new trading day. Equal cutoff and equal source identity is a clean `VERIFIED_NO_NEW_FORWARD_OBSERVATION` with no observation, outcome, or revision write. Equal cutoff with changed source is an independent `SOURCE_REVISED` revision and never a cross-day transition. A lower cutoff is blocked as historical backfill.

Normal states are `NEW`, `REENTERED`, `EXITED`, `PERSISTENT`, and `STRUCTURE_CHANGED`; unavailable data, source revision, and model-version change override normal comparison. Only the six frozen material fields may trigger structure change. The comparison universe is current V1 candidates union prior V1 candidates.

Outcomes use only sealed Forward sequence trading dates at T+1/T+5/T+10/T+20. Their reference is signal-date adjusted close and is research-only. Records are append-only under `(security_id, signal_observation_id, horizon, target_revision)`; exact replay is idempotent and conflicting replay is blocked. Exited signals remain eligible. Observation/outcome code cannot update model rules or thresholds.

TDX roots are read-only. No external data, network service, future backwrite, automated trading, performance/probability claim, historical PIT claim, or V2 promotion is permitted.
