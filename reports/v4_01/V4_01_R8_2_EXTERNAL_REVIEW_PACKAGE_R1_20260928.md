# V4-01 R8.2 Identity Relation Policy — External Review Package

Prepared: 2026-09-28T01:13:53+00:00
Internal policy/postcheck result: **PASS**
Required Scope owner gate: **BLOCKED**
External acceptance: **PENDING_EXTERNAL_AUDIT**

## Scope and disposition

R8.2 binds identity resolution to `IDENTITY_RELATION_EVIDENCE_POLICY_V1`. Listing dates, source revisions, lifecycle adjacency, roster adjacency, names, and bar continuity remain candidate signals. SAME requires a verified official code-change notice or a versioned accepted alias; DISTINCT requires verified official distinct issuer identity or accepted lifecycle identity evidence.

The accepted-history backscan found **38** candidates: **1** SAME confirmation and **37** unresolved Required Scope candidates. No candidate was resolved DISTINCT without explicit distinct issuer or accepted lifecycle evidence. Under the zero-unresolved limit, Gate A is **BLOCKED** until evidence for those candidates is accepted.

The unresolved queue is open and contains only Required Scope unresolved events. It must not be interpreted as confirmed identity or confirmed distinction.

## Verification evidence

- Relation policy: `config/identity_relation_evidence_policy_v1.json` (SHA-256 `b8ab31d62ed27b1bd27ffe2d9af378dd1539765d66b7b7e0958325aa5808006c`).
- Discovery report: `reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_2.json` (SHA-256 `d033b370206137d2360f818a23a373d70ec1664eee16aec071332710b7ca13b6`). Candidate status counts: `{"CONFIRMED_SAME_ENTITY_CODE_CHANGE": 1, "UNRESOLVED": 37}`.
- Unresolved queue: `reports/v4_01/V4_01_R8_2_UNRESOLVED_AUDIT_QUEUE.json` (SHA-256 `1206128edbf72f28cfaa129aabf83e65a17bfb4481722de0c888ea8d0e9e3230`). Queue count: `37`.
- Independent postcheck: `reports/v4_01/V4_01_R8_2_INDEPENDENT_POSTCHECK_R1_20260928.json` (SHA-256 `152c56bdb316e91eb54ed4baf07c0d5e5850af3ec9ca1d8c0cb8e0fd302b1e63`); status `PASS`, owner gate `BLOCKED`.
- Regression receipt: `reports/v4_joint/V4_R8_2_DM01_TEST_RECEIPT_R1_20260928.json` (SHA-256 `e2d1d2a4ad5beb0e39af6af87cc6fbe100155fee500e3a72dac67a5499a18899`); status `PASS`, counts `{"error": 0, "errors": 0, "failed": 0, "passed": 71, "skipped": 0}`.
- R8.2 stage receipt: `reports/v4_01/v4_01_final_stage_receipt_R8_2_20260928.json` (SHA-256 `81a92d9e6e95b7df8dd7e9fcacc86bfa6b3e20cc2d2f2d4566b4821d8ec8f8c7`).
- R7 canonical identity map and required universe hashes are unchanged from the accepted R8 baseline.
- The discovery algorithm contains no fixture-specific security-code branches; known transition examples remain in test data.

## External review requested

Please review the evidence policy, the single confirmed SAME relation, the 37 unresolved candidates, and whether any independently accepted official issuer/lifecycle evidence exists for each candidate. An external FULL_PASS must not be issued while any required-scope candidate remains unresolved.

DM-01 remains framework-only. This package does not claim that incremental component builders are wired, that a completed-session E2E ran, or that Data Head advanced. V4-03 remains blocked.

## Next stage

Complete external R8.2 review and independently accepted evidence triage. Only after Gate A external acceptance should DM-01 complete its real incremental builder wiring and run a real completed-session E2E with a complete source freeze.
