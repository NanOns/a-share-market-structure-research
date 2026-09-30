# V4-08 R5 stage entry

Starting commit: `75767711835207109927f2babfb547415f89d3fb`.

Authority: R5 task SHA256 `3b774d82a0bf7ec777427e82da0799cc34be3fa97f2e9a230fb371335f8963b9`; R4.1 external acceptance SHA256 `4fd4938bbfdc7dde9aa2bf6193efc16621156bcc1abf04d8ccf241ece19c7d2b`.

Consulted REV4_FEP_R2_20260930, sections 15–18, 21A, 34, 72 and 78; source SHA256 `203ff46075b4039d1e2d45d54fd76ce09509535739cd6aaef4dc394de1015205`.

Scope: promote FORWARD_PIT_MEMBERSHIP_ONLY; implement Native, common-member primitives, B0, four-state B1 episode lifecycle, exact source-bound B2, new parameter instance and append-only persistence. Stage readiness requires separate evidence and independent external acceptance. Phase0 inherited FULL_PASS. TDX sources remain read-only.

Accepted PIT starts 2026-09-30. Accepted V4-05 Core and V4-07 Seed inputs target 2026-09-28: they cannot be relabeled as same-session 2026-09-30 facts. A target-date input gate must preserve this additional limitation explicitly. Prior-RPS, AUD-AMOUNT-A-06 and listing-anchor reconciliation remain independent open audit scopes.

Next stage: R5 independent external acceptance if all engineering gates pass; otherwise exact-scope blocked handoff, without final V4-08 accepted head.
