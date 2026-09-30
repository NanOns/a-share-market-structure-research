# V4-10 historical candidate guard supersession

Audit ID: AUD-V4-09-CANDIDATE-GUARD-SUPERSESSION-01. Scope: exactly `tests/v4_09/test_stock_prewatch.py::test_production_and_v4_09_acceptance_stay_disabled`.

Evidence: the historical R1 test asserts absence of V4_09_ACCEPTED_HEAD and calls the V4-08 promotion validator that requires the old global range. The externally accepted R1.1 decision and current task expressly authorize writing that head and advancing the global range. This old candidate gate cannot remain a current-stage assertion.

Disposition: CONTRACT_SUPERSEDED_FOR_CURRENT_STAGE. Preserve the historical file bytes because they are bound in the V4-09 audited implementation evidence. The V4-10 isolated runner deselects exactly this node, records its identity and reason in regression evidence, and runs the replacement tests in tests/v4_10/test_promotion.py. No algorithm test or producer test is excluded. The replacement requires exact V4-09 accepted authority, amended upstream, artifact, protected heads, scoped capabilities, false permissions and idempotence; negative vectors reject wrong authority, upstream, implementation, artifact and overclaim.

Acceptance independent from reducer semantics: source_checks verifies the original test SHA unchanged; current promotion tests must all pass. This is not a full-repository pytest collection closure; the existing global collection audit retains its separate scope.
