# R24 activation readiness implementation

Authority: the R24 master/task and R23R1 final external audit copied here with
original bytes. User authorization covers this single engineering work package,
its evidence, commit and push. It does not grant a real observation or V4-17.

The REAL_SHADOW entry now dispatches to a successor controller. It reads the
exact dependency manifest and authority first and rejects the committed disabled
authority before source acquisition or storage. An enabled authority requires
an exact external decision over the authority digest, complete grant identities,
explicit capabilities, storage/clock/slot/source bindings, rollback identity,
and activation head CAS. Environment variables are never authority.

The simulation explicitly selects a manifest under the isolated simulation root.
Its enabled decision is SIMULATION_ONLY_NOT_REAL_ACCEPTANCE; the controller,
database identity and every durable fact use ACTIVATION_SIMULATION and
NOT_REAL_EVIDENCE. That decision cannot authorize the default real entry. No
production authority file is enabled for tests.

Real and simulation databases have different roots, mutually exclusive immutable
storage origins and a successor migration. R23 storage/migration stays unchanged.
Sources are exact accepted local artifacts, admitted only through the grant's
source authority. Acquisition assigns all visibility times internally, after a
daily plan lock; no caller first-observed timestamp is accepted. Readiness facts
survive a failed publication transaction. Late completeness permanently records
a missed slot. Publication, cohort, outbox, health and heads commit atomically.

V4-15 continues owning event, eligibility, explanation, control, benchmark and
settlement semantics. The versioned owner projection successor has exactly one
AST change: remove the historical demonstration date ceiling, while retaining
accepted-calendar membership. Its code and contract are central dependencies;
the accepted original remains unchanged. R24's separate admission gate produces
one FIRST_OBSERVED original only from a timely complete source set. Corrections
append observations with a predecessor and retain the original frozen T0.

The first real date is deliberately not selected by R24: a later externally
accepted grant must give an exact accepted market session and exact reconstructed
accepted predecessor, with matching model/parameters/lineage. The separately
versioned boundary lists initialized and UNKNOWN fields, excludes the engineering
seed, and contributes zero prior real observations. Thereafter the predecessor
is the immediately previous accepted Shadow session. Same-day corrections reuse
the original publication's predecessor.

Future price reads reuse accepted V4-15 settlement, require a reached due date and
the bound adjusted endpoint of the accepted Data Head. Simulation-only vector
prices require an exact fixture binding. Stopping acceptance preserves observations
and pending settlement obligations. A future launch needs separately accepted
calendar/data/source authorities; R24 grants none of them.

The settlement-only controller can reopen an existing database through its
accepted activation history while the current launch authority remains disabled.
It cannot create storage or accept a publication. The E2E reopens this controller
after stop and verifies the pending obligation continues.

Independent validation imports neither controller nor writer. It reads persisted
SQLite facts and bindings, recomputes manifest and source digests, visibility,
all 18 slot fields, revisions, original cohorts, T0 freezes, controls/benchmark,
outbox, heads, rollback and zero real counters. Semantic corruption tests recompute
row checksums before rejection. A01–A20 exercise the activation denial matrix.

Protected Stage/Data/V4-15 heads and the old authority/migration are compared with
the execution baseline. No real database, V4_16_ACCEPTED_HEAD or real observation
is created. Local gates and clean regression establish an external audit candidate,
not external acceptance. Required next state:
STOP_WAIT_R24_INDEPENDENT_EXTERNAL_AUDIT.

Separate audit items: R23R1 dependency-manifest style (closed locally through the
successor manifest); R24 owner calendar successor (independent semantic-equivalence
evidence, pending external audit). Existing cross-stage capability audit gates
remain governed by V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3.

R24_ORACLE_BINDING_SCHEMA is tracked separately: the oracle compares the entire
persisted SQLite schema against the exact versioned migration and independently
recomputes activation dependency sets and slot/fact identities. Tests replace an
append-only trigger with a harmless trigger of the same name, and rebind an
authority to another model while preserving valid digests. Both are rejected.
Local closure is independent from the stage gate and remains pending external
audit. The strengthened source uses the R2 immutable tested-source tag; R1 stays
immutable as a previous local tested source.
