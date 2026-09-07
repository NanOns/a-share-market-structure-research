# R4 Forward Observation Contract V1

Versions: `r4-forward-observation-contract-v1.1`, `forward-observation-schema-v1.1`, `forward-outcome-schema-v1.1`.

`FORWARD_ONLY = TRUE`, `NO_HISTORICAL_BACKFILL = TRUE`, `NO_FUTURE_BACKWRITE = TRUE`, `OBSERVATION_IS_IMMUTABLE = TRUE`, `OUTCOME_IS_APPEND_ONLY = TRUE`.

States are `BASELINE`, `NEW`, `PERSISTENT`, `EXITED`, `REENTERED`, `STRUCTURE_CHANGED`, `DATA_UNAVAILABLE`, and `SOURCE_REVISED`. The sealed 20260904 board is the sole baseline seed and is not NEW. Same-date revisions never create cross-day transitions and never overwrite a prior revision. REENTERED takes precedence over NEW when prior forward history exists. EXITED rows remain in the current ledger with prior material and V1 context.

Material state fields, in deterministic order, are research band, steady tier, pullback tier, breakout tier, leader tier, and early tier. Context, warnings, counts, memberships, and display order do not trigger structure changes. Normal market transitions require the same integrated model identity; a model identity change is revision/version context, not market change.

Each immutable observation binds cutoff, source revision and identity, input snapshot manifest, V1 release/computation identity, R3 integrated identity, Priority Shadow identity, and schema version. Existing identical date+revision is verified idempotently; different identity/content is conflict-blocked.

Outcome horizons are T+1/T+5/T+10/T+20 effective trading observations. Entry reference is signal-date adjusted close and is `RESEARCH_REFERENCE_ONLY`, not an executable price. Outcome records are keyed by `(security_id, signal_observation_id, horizon, target_revision)`. Outcome statuses are PENDING, OBSERVED, DATA_UNAVAILABLE, SOURCE_REVISED. R4-00 defines schema only and produces zero outcome rows.

Comparison universe means the full V1 candidate board; V2 research candidate means CORE_RESEARCH or SUPPORTED_RESEARCH. Future V2 research-state names are `V2_ENTERED`, `V2_PERSISTENT`, `V2_EXITED`, `V2_REENTERED`, and `V2_BAND_CHANGED`; none is generated for the single baseline. Current membership is not PIT: `pit_membership = FALSE`, `historical_backtest_safe = FALSE`.
