# R18C｜V4-14 Independent Oracle / Real Scoped Replay / Clean Seal｜2026-10-03

## 0. Entry
Execute only after R18A and R18B local gates pass.

## 1. Goal
Independently validate the V4-14 runtime candidate, run capability-scoped real accepted-source replay, and seal a clean detached candidate for external audit.

## 2. Independent Oracle
Create a validator that does NOT call the V4-14 replay evaluator to derive expected results.

It may read:
- frozen V4-14 vector literals;
- accepted owner contract/AST/vector books;
- persisted replay artifacts.

It must independently check all 17 dimensions.

At minimum independently recompute/prove:
- temporal admission;
- previous market session;
- same-day revision predecessor;
- transition legality;
- hysteresis counter;
- expiry counter;
- logical event key;
- episode continuity/reentry;
- multi-sector dedup;
- append-only identity;
- deterministic digest equality;
- evidence-class/degradation classification.

## 3. Mandatory Perturbation Tests
At minimum:
- target source date -> T+1 => reject;
- availability after cutoff => reject/not-verifiable according to frozen rule;
- future membership => reject;
- current membership substituted for historical PIT => reject historical claim;
- previous state date != exact previous market session => reject;
- r2 points to r1 as prior => reject;
- prior digest changed => reject;
- producer PID == consumer PID for cross-process proof => reject;
- producer not exited => reject;
- event revision added to logical key => reject;
- persistent confirmation creates second actionable event => reject;
- duplicate episode on legal continuation => reject;
- UNKNOWN coerced to FALSE => reject;
- superseded contract-family ref used as current runtime authority => reject;
- old revision bytes changed => reject;
- identical replay input with different output digest => reject.

## 4. Real Accepted-source Replay
Run a real accepted-source Replay Gate B exercise using the strongest exact accepted dates available in the current formal chain.

Rules:
- use only accepted heads/publications;
- use exact market calendar;
- use exact available PIT membership;
- preserve `RECONSTRUCTED_CORRECTED` / `AS_RECORDED=false` limitations where applicable;
- no raw/provider fallback;
- do not claim historical PIT effectiveness when prerequisites are absent;
- unavailable owner capability remains UNKNOWN/DEGRADED/NOT_VERIFIABLE.

The real replay is for wiring, provenance, temporal integrity, and capability-scoped behavior—not for pretending historical signal effectiveness has been proven.

## 5. Evidence Class Accounting
Produce counts/results separated into:
- `ENGINEERING_SYNTHETIC`;
- `REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED`;
- `HISTORICAL_PIT_EFFECTIVENESS`.

If the third class is unavailable, record:
```text
HISTORICAL_PIT_EFFECTIVENESS = NOT_GRANTED
```

Do not merge classes into one overall “real pass”.

## 6. Clean Detached Regression
From a clean detached checkout of the final implementation source run:
- V4-08 through V4-13 accepted owner regressions relevant to Replay Gate B;
- R17A governance tests;
- R17R1 active-family closure tests;
- all V4-14 v1.1 contract tests;
- R18A runtime tests;
- R18B persisted E2E tests;
- R18C independent oracle and perturbation tests.

No broad deselection.

## 7. Protected State
Must remain byte-identical:
- `AGENTS.md`
- `data/v4/V4_DATA_ACCEPTED_HEAD.json`
- `data/v4/V4_12_ACCEPTED_HEAD.json`
- `data/v4/V4_13_ACCEPTED_HEAD.json`
- `data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json`
- `data/v4/V4_STAGE_ACCEPTED_HEAD.json`

No Stage promotion in R18.

## 8. Final Candidate
Seal:
- tested source SHA;
- clean git status before/after;
- contract package digest;
- replay publication refs;
- 17-dimension results;
- cross-process receipt;
- same-day revision receipt;
- real scoped replay receipt;
- independent oracle receipt;
- regression totals;
- protected-head digests;
- explicit forbidden permissions.

## 9. Allowed Final State
```text
R18C_INDEPENDENT_ORACLE = PASS_LOCAL
R18_REAL_ACCEPTED_SOURCE_REPLAY = PASS_CAPABILITY_SCOPED
V4_14_RUNTIME_CANDIDATE = READY_FOR_EXTERNAL_AUDIT

V4_14_ACCEPTED_HEAD = NOT_CREATED
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_13_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30

ALGORITHM_STATE_REPLAY_PASS =
NOT_GRANTED_PENDING_EXTERNAL_AUDIT

Production = false
Shadow = false
Focus = false

NEXT = STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```

Commit + push the unified R18 result and STOP.
