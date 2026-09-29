# V4-04 Full-Market Core Profile execution R1

- Date: 2026-09-29
- Entry authority: `data/v4/V4_STAGE_ACCEPTED_HEAD.json` at `481f2ac0a937992a0cab7c697022718be53ec4a2`, `v4_04_entry=AUTHORIZED_FULL_CHAIN`.
- Latest applicable upgrade contract: `docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md`, §§10B–10G, 10I, 87A; the 2026-09-29 Foundation Promotion Stage Audit authorizes entry.

## Stage contract

Deliver a full-market Core Profile for the four required boards from accepted, PIT V4-01/02/03 inputs, with versioned, explainable states for trend (daily and closed weekly/monthly), position, MA structure, relative market, compression, amount/volume and participation, and extension risk. Publish atomically with input identity, quality and independent recomputation evidence. Turnover, Sector PIT membership, advanced structure, scanners, and trading are outside this stage.

## Evidence at this revision

- `src/v4/profile_core.py` implements isolated `V4_04_CORE_PROFILE_RULES_V1` state rules with explicit contract IDs and input evidence.
- `tests/v4_04/test_profile_core_rules.py`: 2 passed. The vectors cover first-true priority, unknown inputs, and branch-specific CLV gating.
- The V4-03 full-scope R3 candidate has 47 factors, but does not itself supply `MA10`, closed weekly/monthly state, `pos250`, or the complete V4-04 publication quality envelope. These must be derived from hash-bound accepted V4-02 canonical inputs, not invented from missing V4-03 fields.

## Acceptance result and next stage

`IN_PROGRESS / NOT_V4_04_PASS`. No full-market V4-04 artifact, accepted head, or release claim has been issued. Next: implement the accepted-input join and missing state fields; run full-market production and an independent recomputation/identity check; only then evaluate the V4-04 stage gate and V4-05 entry. V4-08 membership path remains blocked. No TDX source writes, scanner, or trading runs are part of this revision.
