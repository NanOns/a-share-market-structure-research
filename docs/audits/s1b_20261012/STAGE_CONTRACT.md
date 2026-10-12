# S1-B execution contract V1
Input: INPUT_EXTERNAL_AUDIT.md, sections 2.1, 4 and 5. Base 96b466a9694072e15928ca5d06c3cd4627d4a401. Prior S0 SUPPORTED_PASS reused; no scanner or S2 entry.
Scope: explicit action classification allowlist; fixed 34 securities / 101 observations / 49 outcome metric changes / 4 predicate changes; isolated default HTTP Focus read and PG Joint content verification, T0/token, CAS, failed health rollback and post-publish readback.
Acceptance: per-entry PASS/FAIL/OPEN with raw commands and hashes. Bounded frozen projection read cannot establish other producer admission. Any remaining cross-producer path => S1-B NOT_FULL_PASS, S2 NOT_ENTERED, production NOT_AUTHORIZED.
Independent audit AUDIT-FOCUS-SOURCE-IDENTITY-R4: all replay producers, Forward and settlement identity + numerical consumer acceptance remain separately tracked, beyond this bounded HTTP drill.
Storage: all new runtime/test/output/cache on G:. TDX inputs read-only; no Drive operations. Existing protected authority bytes remain unchanged. New isolated authorities only under G:/codex_tmp/s1b_http_20261012.
Next: close every cross-producer identity path under a separate explicit evidence matrix before considering S1 full exit. No automatic S2 execution.
