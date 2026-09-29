# V4-04 R2 Full-Market Core Profile candidate audit

## Stage contract and entry

Consulted `docs/evidence/V4_04_R2_FULL_MARKET_CORE_PROFILE_CLOSURE_TASK_20260929.md` and the governing REV2 executable contract (§§10B–10G, 10I, 72, 73, 78, 81.4, 87A). Input HEAD was `ca906884526e41a8cc8d4a47eabba3d5329f0a10`. The global Foundation Accepted Head authorizes V4-04 and preserves the V4-08 membership block. V4-00 through V4-03 accepted artifacts were not modified.

## Implementation and evidence

- Explicit V4-04 field registry, output schema, rule AST and parameter instance reside in `config/v4_04_*_v1.json`. The producer loads the named parameter instance; rule evidence includes relative dependency states and `minimum_liquidity`.
- `src/v4/accepted_input.py` resolves hash-bound accepted V4-01/02/03 inputs, formal QFQ closed weekly/monthly periods, canonical daily/status/calendar, cutoff Universe, full-scope factors and the market-regime path. Identity, hash, contract, cutoff and board gates fail closed.
- Missing primitives are derived separately in `src/v4/profile_primitives.py`. MA10 uses the current 10 valid adjusted bars; minimum liquidity uses **prior** 20 raw CNY amounts; pos250 checks the complete dated status/calendar span. The accepted V4-03 factor artifact remains unchanged.
- The builder produced 5,222 distinct cutoff stock rows across SH_MAIN 1,702, SZ_MAIN 1,494, CHINEXT 1,408 and STAR 618. Core state quality: 4,981 `COMPLETE`, 241 `PARTIAL_UNKNOWN`. Optional pos250 may remain independently UNKNOWN. No BSE Required Scope claim is made.
- The market regime UI projection uses accepted V4-03 axes with two evaluable-session hysteresis, immediate CAPITULATION, and UNKNOWN with last-known. Sector membership, BaoStock, turnover, scanners, trading and V4-05 were not used.
- The independent postcheck verifies all 5,222 row and state hashes, V4-03 primitive values and quality, machine AST results, market-regime hysteresis, required field schema and board identities. Its stratified source sample includes four boards, UNKNOWN/short history, high and low positions, suspended rows and a threshold-near row; it independently recomputes MA10, prior20 liquidity, pos250 and closed weekly/monthly values. Full production was rerun with identical artifact SHA256.
- Focused V4 regression: 354 passed, 2 skipped. Global pytest is not green; a separate cross-cutting audit item records its pre-existing M14 collection error and other unclassified failures.

## Acceptance result and next stage

`V4_04_FULL_PASS_CANDIDATE`, pending independent external review. Candidate staging and hash-bound receipts are under `reports/v4_04/`. This document does not grant `EXTERNALLY_ACCEPTED`, create `data/v4/V4_04_ACCEPTED_HEAD.json`, or promote the global Stage Accepted Head. V4-05 remains `NOT_STARTED` until V4-04 is externally accepted. If external review finds a defect, revise the candidate and repeat the production, independent postcheck and deterministic seal before resubmission.
