# TDX read-only boundary incident — 2026-10-07

Status: NEW_BLOCKER_EXTERNAL_REVIEW_REQUIRED. Scope: validation profile copier, independent of the Forward numeric contracts and the current stage gate.

An exploratory historical simulation profile builder resolved absolute binding paths with `out / path`. On Windows, an absolute second operand escaped the E-drive profile. The builder read and wrote back the same bytes for four unique TDX files, with five write calls because tdxhy.cfg had two path representations. One desktop source document was also rewritten with its existing bytes. This violated the explicit read-only input rule. Modification times changed. There is no pre-task TDX modification-time baseline, and no claim of zero TDX writes or independently proven pre/post TDX identity is made.

Evidence: reports/forward_r2_remainder_consolidated_20261007/TDX_INPUT_WRITE_INCIDENT.json. The original tool invocation remains in task history. The checked-in profile builder now resolves every source and excludes every reference outside the repository before reading or writing. The pytest guard independently rejects protected filesystem mutations before they occur.

No additional TDX write, metadata restoration, deletion, or concealment is authorized or attempted. Production database and accepted head protection remain separate checks. This incident prevents CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT and requires an independent decision about input provenance and recapture. A code push cannot close this incident or grant runtime permissions.

Acceptance: OPEN. Next: preserve evidence, finish safe verification, and request independent incident disposition through the normal external audit process.
