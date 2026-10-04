# R31R1 repair acceptance

CONTRACT_DESIGN_ONLY. Tested source: `1260284f27790f748fbfc684ed0fb83f716fe6ec`. Tag: `codex/r31r1-v4-22-audit-contract-repair-tested-source-20261005`.

Three narrow repairs passed local design vectors and exact clean regression: 427 tests, 424 passed; three inherited R26-A01 failures retained, zero new failures/errors/skips/deselections. Protected tracked and unrelated bytes unchanged. All current real open items remain open. No permissions or accepted head created.

Final formula requires independently bound explicit dispositions for OPEN-01..08 and OPEN-10; OPEN-09 remains nonblocking debt. Exact V4-21 required schemas are read from digest-bound authority; session parents bind publication/digest and event T0, with outcomes bound to processing publication rather than due date. Every item authority/evidence binding is checked against exact bytes and authorized domain membership.

{
  "R31R1_LOCAL_REPAIR": "PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT",
  "R31_FINAL_VERDICT_OPEN_ITEM_ENFORCEMENT": "PASS_LOCAL_REPAIRED",
  "R31_OPEN10_SESSION_REFERENTIAL_INTEGRITY": "PASS_LOCAL_REPAIRED",
  "R31_ITEM_LEVEL_AUTHORITY_VALIDATION": "PASS_LOCAL_REPAIRED",
  "V4_22_CONTRACT_DESIGN": "LOCAL_READY_FOR_EXTERNAL_AUDIT_AFTER_R31R1",
  "V4_22_FINAL_AUDIT_ENTRY": "BLOCKED_WAIT_REAL_GATES",
  "V4_22_FINAL_PASS": "NOT_GRANTED",
  "V4_22_ACCEPTED_HEAD": "NOT_CREATED",
  "NEXT": "STOP_WAIT_R31R1_INDEPENDENT_EXTERNAL_AUDIT",
  "tested_source": "1260284f27790f748fbfc684ed0fb83f716fe6ec"
}
