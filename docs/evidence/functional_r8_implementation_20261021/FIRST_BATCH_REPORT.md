# V4 Functional R8 R2 — first implementation batch report

- Task: `V4_FUNCTIONAL_R8_REPAIR_20261021/R2`
- Source task card: Google Drive `V4_FUNCTIONAL_R8_R2_FIRST_IMPLEMENTATION_BATCH_S00_S01_S03_20261021.md` (read 2026-10-21).
- Starting point: branch `codex/v4-unified-development`, initial HEAD `36b0f968502f91b46407985764ad2fbd7c5d71fb`; business-code baseline `6b02414cf5824e9e59a04c7decc3fc75713b083c`.
- Scope completed: S00, S01, S03; bounded preparation S06-P and S05-D. This report does not admit the next batch.

## Stage outcomes

| Stage | Outcome | Evidence / boundary |
|---|---|---|
| S00 | `PASS` | Baseline, formal Head, candidate identity, Phase 0, listener and PostgreSQL identity recorded in [S00/S06-P/S05-D preparation](S00_S06_P_S05_D_PREPARATION.md). Phase 0 is `DEGRADED_PASS`; scanner remains `NOT_APPLICABLE_UNTIL_V4_05`. |
| S01 | `PASS` | Stable business payload SHA on cold/hot API requests, version-aware cache keys, source binding recheck before cached Priority response, and cache/source negative tests. |
| S03 | `PASS` | 33 targeted tests pass; independent arithmetic over all 5,225 stocks and 400 sectors; actual paged 28766 responses match the independent semantic projection with zero mismatches. |
| S06-P | `PREPARED_ONLY` | G1–G4 dual-reference and revision plan recorded. No replay, accepted-history write or PG operation. |
| S05-D | `PREPARED_ONLY / BLOCK_CONTRACT` | Threshold provenance and exact-coordinate proposal recorded. No D2 threshold implementation; S05-I remains `BLOCK_CONTRACT`. |

## Implementation

S01 cache keys now include candidate revision, context identity and the applicable producer/parameter versions; Focus reason keys also bind T0 and the normalized Focus member set. Cache-hit diagnostics stay outside the business result hash. Before serving a cached Priority result, the reader revalidates the current T0 core, adjusted and sector Owner bindings. A same-size/hash-changing owner edit with an unchanged binding fails closed. The sector lifecycle PG-owner cache also keys on candidate revision.

S03 no longer substitutes `prior_low20` for a missing close. It rejects booleans, non-finite values, invalid quality/date/ranges, and close/prior-low coordinate mismatches with field-level explanations and a mutually exclusive primary reason. The stock projection now takes close from the candidate's bound `adjusted` Owner, whose exact TDX affine-QFQ target-coordinate readiness is recorded, so it is comparable with `prior_low20`. Ranking weights, caps and stable entity-ID tie-break remain unchanged. Sector `PROXY_RECONSTRUCTED` RS values are admitted as valid candidate facts; unknown maturity, health, rotation or RS inputs remain unrankable without imputation.

## Verification and readback

- Targeted command: `python -B -m pytest -p no:cacheprovider tests/test_v4_functional_r8_s01_s03.py tests/test_v4_r6_risk_priority.py tests/test_sector_lifecycle_reconstructed_v1.py -q --basetemp=G:\\codex_tmp\\test_temp\\functional_r8_s01_s03_r8` — **33 passed**. Temporary files and Python caches were directed to `G:\\codex_tmp`.
- Full independent source census and timing: [S03 census R5](S03_PRIORITY_CENSUS_R5.json). T0 `2026-10-14`, token `2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df`, evidence `NON_PIT`; 5,225 stocks (967 rankable / 4,258 excluded), 400 sectors (141 rankable / 259 excluded). No score was imputed for 11 rows with missing close; existing score and ranking rules remain intact.
- Independent output reconciliation: [S03 API reconciliation R7](S03_PRIORITY_API_RECONCILIATION_R7.json) compares every ranked and excluded object from the independent census with all bounded API pages after canonicalizing unordered reason sets. **0 mismatches** across all four sets; semantic digests match pairwise. Candidate remains `PIT_ELIGIBLE=false`, `production_accepted=false`.
- Cold/hot candidate Priority response hash: `e460af8a76f4468f321448abfc6343f2b52c909f4ee265c361d519633bf1b743` on both requests; diagnostics changed from `cache_hit=false` to `true` outside that business digest. First cold request measured ~108.3 s; hot first-page request ~0.8 s in this local run. These are observed timings, not service-level guarantees.
- Actual 28766 readback: `/api/v4/context`, `/v4/`, `/v4/assets/api.js` and `/v4/assets/app.js` returned HTTP 200. Context remained at candidate T0 10/14 and did not report production acceptance.
- PostgreSQL readback: existing `127.0.0.1:5432/market_research`, database OID `646711`, server `180006` (18.6), session `transaction_read_only=on`. No DDL, DML, migration, task runner or collector was launched. `127.0.0.1:28765` had no listener; only the 28766 development preview was used.
- Formal Head remains the 2026-10-09 object recorded in the preparation note; no Head, release tag, production service or TDX source root was modified.

The initial census iterations are retained as audit history: `S03_PRIORITY_CENSUS.json` and R2–R5. They exposed entity-order, quality-allowlist and unordered-reason normalization defects in the independent comparison harness; R7 reconciles unordered reason sets as sets and confirms the exact per-object results. The product score comparison itself had zero stock mismatches in the full censuses.

## Bounded preparation and stop line

S06-P names the accepted 2026-10-09 Head and the non-PIT 2026-10-14 candidate as distinct G1–G4 references. The candidate is not a valid way to skip accepted sessions. Range repair, full replay, database writes and formal acceptance remain out of scope.

S05-D records that R2 defines the comparator but has no approved level-generation rule. `V4_D2_FROZEN_INVALIDATION_LEVEL_R1` is only a proposal pending an explicit business rule and exact source/coordinate contract. The 875 prior episodes without a frozen level remain `UNKNOWN`; no threshold code or historical backfill was added.

## Next gate

All requested first-batch work is complete and committed/pushed on `codex/v4-unified-development`. **Wait for independent ChatGPT acceptance of this report and evidence before starting any next batch.** This push does not change formal acceptance or authorize a production Head update, PG write, D2 threshold implementation or 28765 switch.
