# Prior-RPS Accepted Input Bootstrap Audit

- Audit item: V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01
- Opened: 2026-09-30
- Status: OPEN
- Scope: accepted V4-05 Full Scope Factors lineage for rps5_delta3, rps5_delta1, and rps20_delta3; determine how a sufficiently initialized prior-RPS history can be produced, accepted, and bound without changing V4-07 thresholds or consuming unaccepted data.
- Independent gate: this issue is separate from V4-07 R2 producer correctness and has its own evidence and acceptance.

## Evidence

- The 2026-09-30 independent external audit reports each listed RPS delta as UNKNOWN for all 5,222 accepted identities due to BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY.
- The R1 independent postcheck bound to accepted V4-05 Full Scope Factors and preserved those UNKNOWN values; V4-07 must not fall back to earlier unaccepted R3 values.
- Accepted V4-05 Core also lacks accepted T-1 close and MA20 fields. No raw-bar reconstruction is authorized by this audit item.
- A fully UNKNOWN relative-change input means the RPS branches cannot be TRUE on the current accepted input. This is an input-capability limitation, not a claim that no market candidates exist.

## Scope exclusions

- Do not change V4-07 formal parameter values, treat UNKNOWN as FALSE, use turnover or later unaccepted values, read future Forward outcomes, or reconstruct raw history inside V4-07.
- Do not mutate accepted V4-05 artifacts or Accepted Head in this audit item.
- Do not unblock V4-08 or any real Base Seed consumer.

## Acceptance criteria

1. Identify the exact bootstrap history/window requirement in the applicable REV2 factor contract and accepted V4-05 lineage.
2. Produce a separately versioned RPS candidate with point-in-time date boundaries, complete source and calendar identities, auditable input/output digests, and explicit UNKNOWN reasons when coverage remains insufficient.
3. Independently recompute the RPS output and reconcile the full accepted identity scope, including first-available date and warm-up behavior.
4. Obtain the required independent acceptance and bind the accepted factor output through a new accepted publication; do not rewrite the old accepted artifact in place.
5. Re-run V4-07 on the newly accepted source context and report resulting capability without threshold changes.

## Next action

Open a dedicated prior-RPS lineage/bootstrap repair stage from the latest applicable factor contract. Keep this item OPEN and keep real Base Seed signal capability degraded until all acceptance criteria pass.
