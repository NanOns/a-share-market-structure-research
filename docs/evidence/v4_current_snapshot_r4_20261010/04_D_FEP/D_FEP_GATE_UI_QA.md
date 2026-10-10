# R4 D API/UI QA

/api/v4/forward/fep retains null prediction and existing capability fields. It adds admission_gate, six field statuses and Chinese reason_text. Production remains locally degraded; historical model existence is shown accurately. New focused tests: 14 passed. Broader historical E5 tests: 41 passed, 22 setup errors caused by disposable-DB isolation guard; no DB was accessed.

Current-code isolated API verification: 10 routes passed, FEP correctly returns missing-source and Chinese admission reasons. Evidence: ../05_E_RUNTIME/E_NEW_CODE_ISOLATED_READBACK.json.

Browser DOM: NOT_TESTED. IAB returned ERR_BLOCKED_BY_CLIENT; Chrome unavailable. API verification does not establish browser acceptance.
