# V4-08 R2 Closure

## Terminal state

`V4_08_R2_MEMBERSHIP_BLOCKED_ACCEPTED_CALENDAR_EXTENSION_REQUIRED_IDENTITY_SCOPE_AND_SOURCE_POLICY_REVIEW`

## Membership contract repair

- Starting HEAD: `68276e4f48f7664827418a6095b3a0ddcc1fa0a8`.
- Migration 018 SHA-256: `abaf9fa2ce432deca155292de9e6bb574ba7f1e4de7d5611ac56cc0106e3eb51`; migration 016/017 were not rewritten.
- Raw current snapshot: `24cc00f60de09e01627fd1fa2d13755888c91cc2a5c10bb1a1a21cad4719b4dc` (85,038 facts).
- Derived parent snapshot: `7ec30281a92a85c5ff10b741216c46b2faf1a0f73933813bf972161f369e0dd4` (2,899 facts), parent raw snapshot `24cc00f60de09e01627fd1fa2d13755888c91cc2a5c10bb1a1a21cad4719b4dc`.
- Raw and parent replay use separate snapshots; parent replay retains `DERIVED_PARENT_MEMBERSHIP`.
- SQL formal view quality and exact-date gates passed in isolated PostgreSQL postgres (PostgreSQL) 18.6.
- Source revision identity now binds source bytes digest and temporal-evidence digest; evidence-only revisions are append-only.

## Identity and go-forward PIT

- 497 unresolved keys / 1,176 facts classified: ETF/fund 325 keys, convertible bond 55, BSE optional 106, ambiguous required-board candidate 11.
- Required-board ambiguity by board: `{"CHINEXT": 5, "SH_MAIN": 3, "STAR": 1, "SZ_MAIN": 2}`. A versioned V4-01 identity/lifecycle update is required; V4-08 did not hand-map these keys.
- R1 frozen byte set was completely observed by `2026-09-30T00:45:21.890265Z`; source-specific provider-time policy remains a candidate and does not claim provider publication time. Filesystem mtime was not used.
- Accepted market calendar coverage ends `2026-09-24`; no formal target session or cutoff after that date is accepted here. Candidate PIT trade date remains null and no PIT snapshot was created.

## Sector / Rotation

- Sector Native, B0 PREWATCH, B1 ROTATION_CORE_V1, B2 Legacy Adapter, field registry, parameter set, and machine vectors are frozen as engineering candidates.
- Rotation synthetic R1/R2/R3: `{"R1_STRONG_PREV_ZERO_EARLY_PATH": "PASS", "R2_WEAKENING_OLD_STRONG_SECTOR": "PASS", "R3_SINGLE_LEADER_NO_DIFFUSION": "PASS"}`.
- Five V4-00G retention parameters remain unassigned and block affected formal consumers. Real full-market materialization remains disabled.

## Prior-RPS and regression

- Prior-RPS audit `V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01` remains `OPEN`; no accepted factor publication or thresholds changed; V4-03 R3 staging was not copied.
- Required regression status: `PASS` with observed summary `{"errors": 0, "failures": 0, "passed": 571, "skipped": 2, "suite_count": 1, "tests": 573}`.
- Clean checkout status: `PASS_CLEAN_CHECKOUT`.
- External acceptance: not requested or self-recorded. No V4-08 Accepted Head exists.

Next: complete the accepted calendar extension and V4-01 identity revision, then submit the PIT prerequisite and candidate contract evidence for independent external audit.
