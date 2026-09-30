# V4-10 R1.1 external-audit repair stage entry — 2026-10-01

Authority: V4_10_R1_EXTERNAL_AUDIT_REPAIR_TASK_20261001.md and REV4 FEP R2 §§13A/30–33/34A.2A/78/80/87A. Starting HEAD 14db3ef521d34b366bf5a22bad2a3564838ce8bf; external result V4_10_EXTERNAL_ACCEPTANCE_BLOCKED_R1.

Contract: retain RESEARCH_STATE_V1 business rules and 2/10/3/3 thresholds. Repair only prior authenticity, structured authorized model-boundary manifests, unified state-changing input provenance, exact publication-list shape, frozen calendar lineage and DB identity. Add R1.1 contracts/vectors/evidence and migration 023; preserve original R1 contracts, 98-vector candidate, migration 022 and reports.

DB choice A: independent PostgreSQL canonical JSON/digest and state-publication identity guards, field-producer/manifest checks and important lineage column equality. Versioned numeric canonicalization is shared as a declared protocol, independently implemented in Python and SQL. Ordinary API callers supply no trusted resolver in serialized input. The engineering DB owner issues immutable manifests; ordinary result writers cannot register those manifests. This trust boundary does not authorize production, external data feeds or automated trading.

Acceptance requires G01–G17 of the task. Existing semantic vectors plus new adversarial interface vectors, direct SQL forgery tests, append-only/revision/rollback, no-symbol, and full required-family regression in a clean detached checkout. Only the previously authorized historical candidate-absence node may remain deselected.

V4-09 KEEP_ACCEPTED / NO_REOPEN. V4-09 N01/N02 remain OPEN; prior-RPS, Amount A, DM01 incremental builders, legacy valid-member, forward PIT, BaoStock binding tolerance and historical as-recorded adjusted-price capabilities keep their independent states. Protected heads and all production/shadow/Focus permissions remain unchanged.

Next: V4_10_R1_1_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT, commit and push relevant code and evidence, then STOP. V4-11 remains BLOCKED until independent repair acceptance and a separately authorized promotion/entry task.
