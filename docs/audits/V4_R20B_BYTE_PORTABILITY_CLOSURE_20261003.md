# R20B byte identity portability closure

Baseline: `2020234020e09020aca13fd84cdabde6fbb81f50`.

Contract: explicit four-mode registry, default literal exact. Current accepted heads V4-07 through V4-14, Stage/Data, V4-14 entry, V4-15 package and current authority are graph roots. Authority/config/source JSON edges recurse; reports, audit documents, source code and machine-vector evidence are exact leaves. This avoids interpreting synthetic negative-vector references and historical test expectations as current authorities.

Inventory freezes 2,946 files. Each includes Git object identity where present, worktree byte identity, declared admitted binding identities, line ending classification, LFS identity, mode and consumers. Non-Git literal artifacts explicitly carry null Git identity and cannot claim a Git representation exception. Every exception freezes Git bytes plus both newline representations and verifies UTF-8 without BOM, identical bytes apart from CRLF/LF, and no binary or LFS normalization.

Independent Git-object oracle: PASS_LOCAL for all 2,946 entries. Current-stage reader integration: PASS_LOCAL, 45 exact required reads with explicit receipts. Cross-platform and negative tests: 15 passed, zero failed/skipped/deselected. Protected heads were not rewritten by R20B.

22 historical path-version mismatches are recorded as noncurrent declared bindings, never admitted by newline equivalence. The three unavailable historical leaf descriptors (`gbbq`, `gbbq.map`, removed R3 lifecycle config) are retained in diagnostics, not granted authority. Required current runtime edges all passed actual injected-reader consumption. These diagnostics do not authorize altering historical semantics or repairing arbitrary bytes. The untyped exploratory graph additionally demonstrates why nested archived reports and synthetic vectors cannot define current authority.

Future clean-tested source must be an immutable commit reachable through published remote ancestry/ref. Bundle-only future seals fail. R19 bundle-only tested identity remains a disclosed historical limitation.

Acceptance: R20B_BYTE_IDENTITY_PORTABILITY=PASS_LOCAL; R19_AUDIT_01=CLOSED_LOCAL. Stage remains V4-14, Data remains 2026-09-30. Next: R20E after R20C/R20D. Separate comprehensive historical-content audit scope: historical noncurrent bindings, exact Git version retrieval and archival completeness, evidence in inventory diagnostics; no current-stage algorithm change is authorized.
