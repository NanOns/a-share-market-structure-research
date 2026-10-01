# A03 / A06 / A07 / Owner / Historical Reader scoped acceptance formalization

The independent external ten-card audit at `66ef2e342dd339cc9795c2d1fd774b8edec4c345` is the sole acceptance authority. Its original 8,244 bytes are frozen at `docs/evidence/next_round_r2/V4_NEXT_ROUND_10_CARD_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R1_20261001.md`, SHA-256 `7d6c8d3faf64a948d206a318d122d41baf757613d0beb88e6d5bd54fcff96bb3`. The master R2 and parallel formalization task define execution scope; they are not external acceptance evidence.

Five separate acceptance records bind that exact authority and the previously audited immutable code/evidence in `reports/next_round_r2/scoped_acceptance/`. New formalization output does not claim an independent external review of its own implementation.

| Package | Accepted disposition | Current boundary |
|---|---|---|
| A03 | `PASS_FORWARD_PIT_BUILDER_SCOPE` | `ACCUMULATION_CONTINUES`. Daily immutable append and detectors are accepted engineering. Future observation count is not an engineering blocker; no retroactive AS_RECORDED fabrication. |
| A06 | `PASS_FAIL_CLOSED_NO_TOLERANCE_AUTHORIZED` | All undocumented numeric tolerances remain null. Strict binding remains false, BaoStock supplemental only, TDX core unaffected by mismatch. No further empirical threshold fitting. |
| A07 | `PASS_LINEAGE_CAPTURE_SCOPE_WITH_PERMANENT_PRECAPTURE_BLOCK` | Pre-capture AS_RECORDED stays permanently blocked. Go-forward lineage starts at a real immutable capture time; adjusted-price consumer authorization remains separate. |
| Owner | `SCOPED_ACCEPTED_OWNER_BOOTSTRAP_R1` | Accepted inactive metadata preserves all seven exact field declarations and limitations. Active Registry R3 stays unchanged; no global consumer cutover. |
| Reader | `PASS_HISTORY_ONLY_DI_HARDENING` | Version 2 is selected by a new accepted history-only manifest. Version 1 and original validator source bytes remain immutable. No business reacceptance or production authorization. |

The Owner record formalizes the already reviewed candidate at `data/v4/SCOPED_ACCEPTED_OWNER_BOOTSTRAP_R1.json`. Its original pending candidate declarations are explicitly preserved as historical declarations; separately bound field dispositions record the new scoped acceptance. This does not replace the active registry or grant any consumer an expanded date, historical mode, authority field, or limitation.

The accepted history-only selector is `config/historical_publication_reader_accepted_history_only_r1.json`; the versioned wrapper is `src/workbench_analysis/parallel_scoped_acceptance_r1.py`. It validates the audit and exact original runtime bindings before dispatching to the immutable v2 reader. Original current publication validation still fails its historical Data Head comparison, as intended.

Independent readback replays the actual existing A03 capture into a separate immutable ledger. The publication is byte-for-byte identical to the original accepted observation; its duplicate retry is idempotent. This is explicitly a readback of one existing observation, not a new market observation. The original ledger and publication are untouched. The actual A07 GBBQ capture remains reconstructed for knowledge before capture and AS_RECORDED for the captured source version at capture; neither result grants formal adjusted-price consumption.

Two accepted historical reader replays plus an original current validator run concurrently in three distinct threads. V4-09/V4-10 full outputs match the immutable v1 history reader exactly; the current validator retains `P19_protected = FAIL`, the current Data Head remains 2026-09-30, and no module ROOT is switched. Wrong hash, path traversal and absolute path attempts fail. Original candidate acceptance scope, inactive Owner root, and production/global permission boundaries are independently rejected when altered.

Targeted regression, including unchanged A03/A07 and previous Owner/A06/DI suites: **164 passed**, zero failures/errors/skips. Proof: `reports/next_round_r2/scoped_acceptance/TARGETED_TESTS_R2.xml`; stable independent readback: `INDEPENDENT_READBACK_R2.json`; final closure: `SCOPED_FORMALIZATION_CLOSURE_R1.json`. The prior readback and first targeted run are retained as earlier evidence. The parent batch owns the fresh checkout joint regression, No-Symbol scan, unified commit/push and STOP for independent external review.

Stage Head, Data Head, V4-06/V4-09/V4-10 heads and Registry R3 are unchanged. Production, Shadow, Focus and global mandatory adoption remain false. No migration and no V4-12 work were needed.
