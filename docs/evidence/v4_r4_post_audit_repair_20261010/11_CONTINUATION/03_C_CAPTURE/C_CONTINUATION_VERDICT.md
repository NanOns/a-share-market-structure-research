# FIX-C continuation: actual DD boundary connected, full producer still missing

Contract: targeted repair task FIX-C §4, formal REV2 independent complete cohort, REV4 authorization/source separation, DD R2.2 actual-source publication boundary. Engineering scope only; independent acceptance not granted.

The actual `operational_daily_executor_v1.derive_ready_sources` now inspects its exact sealed candidate before publication and includes `cohort_capture_readiness` in DERIVED_READY progress and the returned job receipt. This adapter performs no enrollment, issuance, Head update, or settlement. Missing cohort inputs do not block usable local daily domains.

Read-only replay of the existing 2026-10-09 SUCCESSOR_CANDIDATE (SHA 55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e) returns SOURCE_INCOMPLETE, independently naming the validation cohort Owner, complete as-recorded eligible/ineligible signal receipt, and separate write grant. observed/matured/settled counts remain null. No historical or future capture was created. Accepted operational Head remains the same SHA.

The adapter delegates complete-input validation to the existing SHA-bound prepare_capture function; synthetic input passing that function remains only ISOLATED_CAPTURE_CANDIDATE_READY. Wrong read/write capability, revision, revoked grant, Focus scope and reconstructed source are surfaced as CAPTURE_PREFLIGHT_REJECTED without production authority. Candidate digest/date errors remain integrity errors.

45 tests passed, exit 0: new boundary tests, existing capture preflight negatives and existing source orchestration tests. An integration test exercises actual derive_ready_sources and confirms missing source appears in its progress/result before any CAS; all injected bytes and artifacts are isolated under G:/codex_tmp/test_temp/c_capture_continuation_r1_final. These tests do not prove production enrollment.

Remaining boundary: the current daily owner builder produces corrected research outputs with AS_RECORDED=false/PIT_ELIGIBLE=false. It does not emit an independent, contemporaneously frozen full eligible/ineligible signal ledger. A real full-signal producer with first availability, immutable parameters/version, as-recorded membership and deduplication identity must first exist, then gain independent Owner and writer admission. Adding this observer does not connect that missing automatic capture chain or enable a future session early. The 2290 old events remain excluded.

Acceptance: ENGINEERING_BOUNDARY_READY_SCOPED / REAL_FULL_SIGNAL_PRODUCER_BLOCKED. Next stage: lawful real-source first-capture producer and independent Owner/grant admission, followed by DD R2.2 CAS and separate read/settlement grants. Existing RadarCohortRuntime, Forward v1.2 and validation-cohort reader are unchanged; existing historical evidence is reused without rerunning broad comparisons. Details and file hashes are in C_DAILY_CAPTURE_BOUNDARY_RECEIPT.json.
