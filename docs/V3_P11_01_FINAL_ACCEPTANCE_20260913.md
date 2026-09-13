# V3 P11-01 Final Functional and Growth Acceptance

Date: 2026-09-13

Stage contract: `V3_P11_FINAL_ACCEPTANCE_V1_0`

Authority: V3 implementation specification sections 15, 17.12, 18.14 P11-01, and 20.3-20.8.

Supporting performance contract consulted before execution: `M15_PERFORMANCE_V1_0` in `docs/M15_03_PERFORMANCE_CONTRACT_V1.md`, with the latest browser retest receipt retained as supporting evidence.

Specification SHA-256: `52536035f82d4754eda13241181f2aa8563b9d37e280e2ae39bfbd3a5a6c9d5b`

Machine receipt: [P11-01-FINAL-ACCEPTANCE.json](../reports/upgrade_v3/P11-01-FINAL-ACCEPTANCE.json)

## 1. Independent acceptance results

| Dimension | Result | Evidence |
|---|---|---|
| Functionality | `FULL_PASS` | All 23 section-15 counterexamples were registered and executed through the full regression command. Legacy matrix has 19 rows. |
| Data correctness | `FULL_PASS` | COMPLETE context resolves by run/publication/date; pagination and zero-result semantics are explicit; relation/date/identity regression passed; request-time hot-rank persistence remains zero. |
| Performance | `FULL_PASS` | Five local API categories each had 30 warm samples; all warm P95 values were below 1.5 seconds. First-screen JSON was 583 bytes. |
| Storage | `DEGRADED_PASS` | Same-input memory probe added zero business rows, identity/log rows, or duplicate physical content. P00-to-current growth is inventoried but not attributed or recovered in P11-01. |

Overall stage result: `DEGRADED_PASS`. The stage proceeds to P11-02. It does not switch the main entry.

## 2. Real local API and UI-path measurements

Measured against the current COMPLETE run `research-5369ba9e65074cf599bbea230e24ff7b`, publication `m4-8a99c99719061f4f1f166d0b9184506c`, trade date `2026-09-10`, context `ctx-a35b319549799802b94ef98844ffb319`.

| Category | Cold ms | Warm P50 ms | Warm P95 ms | Warm max ms | Samples | Bytes | Returned |
|---|---:|---:|---:|---:|---:|---:|---:|
| `/api/v3/home/local` | 555.520 | 532.275 | 564.472 | 586.569 | 30 | 583 | 0 eligible cards |
| V3 CURRENT sectors | 148.302 | 134.987 | 165.585 | 170.631 | 30 | 551 | 0 |
| V3 POTENTIAL sectors | 127.191 | 132.561 | 143.984 | 172.693 | 30 | 551 | 0 |
| CURRENT_FOCUS shortlist | 137.429 | 134.104 | 146.696 | 177.124 | 30 | 552 | 0 |
| EARLY_FOCUS shortlist | 126.167 | 131.076 | 139.888 | 147.701 | 30 | 552 | 0 |

The cold home sample is recorded separately as required; the V3 P11 budget gates the warm local P95 and first-screen JSON size. The real run has no eligible cards, so the 0 result is an explicit EMPTY state, not padded output or an effect claim.

Back-to-back CURRENT/POTENTIAL track switching took 270.246 ms. The UI track loader contains no research-build route. A bounded in-memory slow-source probe used the 12-second online contract and a 50 ms injected budget; it returned six `UNAVAILABLE` results in 1.104 ms with zero fetcher calls, while the local context remained READY.

## 3. Counterexample and regression evidence

The receipt contains CE-01 through CE-23, each with its required result and mapped test file. The executed command was:

```text
python -m pytest -q tests/upgrade_v3 tests/upgrade_m7 tests/upgrade_m14 tests/upgrade_m15
```

Result: `339 passed in 112.95s` on the latest verification run.

The test run also covers stale-response cancellation, evidence modal boundaries, page totals versus returned counts, legacy API reachability, source failure isolation, bounded online requests, and request-time-only hot-rank behavior.

## 4. Storage and growth facts

All production database measurements used `read_only=True`. No cleanup, VACUUM, backup, migration, or production research build was executed.

| Path | P00 baseline bytes | Current bytes | Delta bytes |
|---|---:|---:|---:|
| `data` | 13,160,481,049 | 32,764,131,844 | +19,603,650,795 |
| `data/backups` | 3,466,219,849 | 22,737,490,910 | +19,271,271,061 |
| `runtime` | 1,409,431,425 | 5,531,414,409 | +4,121,982,984 |
| `data/database` | 1,731,747,842 | 2,064,146,434 | +332,398,592 |
| `data/.phase1_cache` | 954,775,668 | 954,775,668 | 0 |
| `data/input_staging` | 6,106,503,079 | 6,106,503,079 | 0 |
| `data/normalized` | 876,179,188 | 876,179,188 | 0 |
| `logs` | 244,849,532 | 244,849,532 | 0 |

Current DuckDB physical facts: file size 2,060,988,416 bytes; `PRAGMA database_size` reports 1.9 GiB, 7,862 total blocks, 7,295 used blocks, 567 free blocks, and zero WAL.

Current content inventory: 389 analysis slices, 166 logical content hashes, 52 storage-object identities, 59 exact `(domain, date, contract, logical_hash)` duplicate candidate groups, excess 210 slice identities, and maximum group size 12. These are identity/content candidates for P11-02 review; they are not a deletion authorization and are not reported as recovered space.

The four required growth facts are distinct:

- Business facts added during this audit: `0`.
- Identity/log rows added during this audit: `0`.
- Duplicate physical content added during this audit: `0`.
- Regenerable cache net growth versus P00 for `data/.phase1_cache`: `0` bytes.

The same-input memory probe started and completed one synthetic run, then reused the same `input_key`. The second start added zero run rows, stock-state rows, sector-state rows, or duplicate physical content. A production repeat was intentionally not run because this stage is read-only.

## 5. Separate limits and migration decision

- PIT: `PARTIAL`. The real run uses `LOCAL_CLOSE_ONLY`; it is not represented as historical-member PIT.
- Source capability: `FULL_PASS` for the P09 G09 target chain, with synchronized per-stock live reranking and additional topic-to-local-sector mappings still explicitly deferred.
- Algorithm effect: `EFFECT_OBSERVATION_PENDING`. The real database has zero sealed episodes and does not meet the 20 signal-day / 50 independent-episode observation gate.
- Main entry: not switched. No serious date, relation, or identity error was found in this audit, but P11-02 and P11-03 remain prerequisites for P11-04.

Next stage: P11-02, to prove migrated domains have stopped old writes and to produce an exact, reference-protected recovery preview by relation copies, result copies, extraction caches, backups, and runtime artifacts.
