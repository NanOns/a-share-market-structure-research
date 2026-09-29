# V4-05 Replay Gate A stage entry R1

Date: 2026-09-29. Authority: promoted V4-04 Accepted Head, promotion commit `6aa0bdd`, external acceptance R1, and the V4-05 Replay Gate A task R1. Source cutoff: 2026-09-24.

## Contract and scope

G01 through G08 and explicit temporal negatives govern Data / Factor replay. All inputs resolve through `data/v4/V4_STAGE_ACCEPTED_HEAD.json` to accepted source hashes. Target dates and entities are fixed in `V4_05_REPLAY_DATE_MATRIX_R1.json` before any replay evaluation. A gate passes only with independently checked evidence; tests alone do not establish acceptance. No later-stage business capability is authorized by this entry.

## Pre-execution risk

The accepted V4-02 final acceptance records historical adjusted lineage as `DIAGNOSTIC_NON_PIT_CURRENT_METADATA_SNAPSHOT`; its stage receipt records `AS_RECORDED_CONSUMED_SOURCE_HISTORY_UNAVAILABLE`. The accepted V4-03 full-history candidate receipt says historical daily first-availability replay remains pending. These statements are known before output evaluation and require G03 independent verification. V4-02's narrower acceptance remains in force; V4-05 must assess its own historical AS_RECORDED claim.

## Acceptance and next stage

Entry authorized; Replay Gate A is not accepted. On an upstream evidence blocker, issue a capability-scoped `V4_05_BLOCKED_UPSTREAM_DEFECT_<SCOPE>` result, halt downstream replay, and retain V4-06+ blocked pending a separately accepted repair and a new replay gate. V4-08 historical Sector PIT remains separately blocked.
