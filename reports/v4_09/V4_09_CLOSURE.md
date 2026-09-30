# V4-09 Stock PREWATCH closure — 2026-09-30

Status: `V4_09_ENGINEERING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT`. Independent external acceptance remains pending.

Stage contract: supplied V4-08 promotion/V4-09 task card and latest REV4 FEP R2 §§22–24,78. V4-08 promoted under `V4_08_EXTERNAL_ACCEPTANCE_PASS_R5_2_ENGINEERING_SCOPE`; Stage range is V4_00_TO_V4_08_ACCEPTED. Data, Dev and accepted PIT Membership bytes remain unchanged.

Implementation tested in clean detached checkout: `36c987089fb2f79607b1fba6784c208bc2b01758`. Candidate reproduction changed no tracked bytes. No config/.env read, configured database use, TDX write, production/shadow/Focus authorization, or V4-09 accepted pointer.

Raw Stock eligibility consumes only resolved accepted Base Seed and minimal mandatory Core quality. Core price-damage observability is checked, without adding a new damage-value veto. Resolved FALSE Seed can remain evaluable despite unrelated missing Profile/priority fields. An UNKNOWN Seed or required quality yields raw UNKNOWN even alongside FALSE. Priority axes remain independent; missing eligible priority receives UNKNOWN_BUCKET.

Accepted engineering replay: 2026-09-28, 5222 identities. TRUE=0, FALSE=2443, UNKNOWN=2779. A/B/C/D=0/0/0/0; UNKNOWN_BUCKET=2779; NOT_ELIGIBLE=2443. No threshold relaxation or old prior-RPS fallback. All-market independent source-reading postcheck mismatch_count=0; 150 frozen vectors pass; 3/10 percentage-point parameter perturbations change the corresponding runtime axes.

Same-context replay bytes and logical digest match. Three synthetic contract contexts (explicitly not accepted market data) change dates, publications and identity counts without source edits. Forbidden Sector/Rotation/B2/D2/Confirmation/Anchor/Support/Radar/Focus/UI/outcome/forward-return/turnover perturbations preserve all result bytes. Future snapshot augmentation leaves the frozen T artifact unchanged.

PostgreSQL 18.6 disposable cluster: 5222 rows exact readback and retry; revision-2 appends 5222 rows. Existing row/publication UPDATE/DELETE rejected; same-publication changed payload rejected. Rollback removes only migration 021 tables/function, and the savepoint restores both revisions exactly. Temporary cluster destroyed.

Full required V4 families plus V4-09 and permanent governance: 890 tests, 888 passed, 2 skipped, 0 failures, 0 errors. No-symbol PASS, hard equity hits=0, unclassified paths=[]; policy explicitly covers new runtime and evidence roots.

V4-08 Accepted Head SHA256: `b9ba34374ce35eefab705469de1e005758b90fa1f58ea5bba96fac08571073bc`.
Global Stage Head SHA256: `3a8a3b01d3e556b86934139dacc58c941727060ac72f11f9a60de229f58ffcd2`.
V4-09 contract SHA256: `6c090ee9cbc5a7e3c5c86ca9023aa983db41d447388ea1776308a69ecbefadc8`.
V4-09 parameter SHA256: `3c9b0d658c6e8212c5a6239eecdeece99d54791b97cee45fe4df98de71086c24`.
V4-09 AST SHA256: `9035548e8e33ea66e1c448b63b017cfa9b1ab2bcf7c08ef0568063a2eac954c6`.
Candidate bytes SHA256: `ca88956bfedf38356c07a0c2a9b275c2e4d2bf4e5f6744cfd498abb9e35b8900`.
Candidate logical digest: `51ef988969c950faa4a0c0d96e1bec335b1c8727da0314aaa054793115457601`.

Separate OPEN audits remain: V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01, AUD-AMOUNT-A-06, DM01_REAL_INCREMENTAL_BUILDERS, LEGACY_VALID_MEMBER_EXACT_PRODUCER, FORWARD_PIT_HISTORY_ACCUMULATION. Their scopes, evidence and independent acceptance are tracked in reports/audits/V4_08_PROMOTION_OPEN_CAPABILITY_AUDITS_R1.json. B2 legacy remains NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE; Amount A is DIAGNOSTIC_AUDIT_OPEN; real signal capability remains degraded.

Next stage: independent external reaudit of this V4-09 engineering candidate. Stop here; no V4-09 Accepted Head, Stage advancement to V4-09, State Reducer, Confirmation, Structure/Anchor, Radar/Focus or UI cutover.
