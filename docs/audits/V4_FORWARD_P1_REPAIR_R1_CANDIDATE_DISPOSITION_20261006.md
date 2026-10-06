# Forward P1 Repair R1 — candidate disposition

Task: `V4_FORWARD_P1_REPAIR_R1_IA09_IA01_IA02`. Entry commit:
`0c78051c570bdd68ef98f1cb9fdcfcd315759ec2`.

The archived task and both source audits are exact-bound in
`reports/forward_p1_repair_r1_20261006/ENTRY_BASELINE.json` and
`SOURCE_AUDIT_BINDINGS.json`. This disposition is a separate audit item register;
it does not update the Current Audit Head or grant external acceptance.

| Item | Independent scope and evidence | Candidate result / next gate |
|---|---|---|
| IA-09 | Disposable M12 service/API root, guarded DB, minimal child environment, no real recovery; explicit disposable recovery and protected-root fingerprints | CANDIDATE_FIXED; independent external audit |
| IA-01 | Stock endpoint admission independent of interior path quality; strict endpoint/T0 affine/basis/identity admission; STK-01–12 matrix | CANDIDATE_FIXED; independent external audit |
| IA-02 | Frozen sector membership, member source/adjustment identities, original weights, individual valuations; SEC-01–12 matrix | CANDIDATE_FIXED; independent external audit |
| IA-03 | Same-source PENDING → DUE revision-key collision | OPEN_AUDIT_ONLY / P2; unchanged regression sentinel |
| IA-04 | Negative actual prices, invalid OHLC envelopes, terminal delist zero | OPEN_AUDIT_ONLY / P2; unchanged regression sentinels |
| IA-05 | Retired M14 capture writer import during collection | OPEN; safe collect-only evidence; writer is not restored |
| IA-06 | Opt-in PostgreSQL fixture / model validation coverage | OPEN; skipped fixture cases are not accepted as PASS |
| IA-07, IA-08, IA-10 | Independent comprehensive-audit items outside this batch | OPEN; separate successor tasks and acceptance required |

## Additive contracts and consumer boundary

`workbench_analysis.v4_15_forward_p1` is a candidate successor. It appends
`FORWARD_PRICE_PATH_V1_1` outcomes and separate successor T0 freezes. The accepted
implementations, old freezes, old outcomes, controls, migrations 028–033, Shadow
migrations and historical FEP labels are not rewritten.

Stock `R_N` uses only admitted T0 and endpoint coordinates. Interior unknowns
retain that return and leave MFE/MAE/MDD unknown with explicit path reasons.
Confirmed interior suspension follows the frozen omission policy; no missing
bar is interpolated. Relative benchmarks retain their own endpoint validation.

Sector subject valuation has no synthetic stock OHLC or stock adjustment
identity. Its frozen identity includes subject, membership snapshot, member IDs,
initial weights/fixed shares, T0 basis and member source/adjustment identities.
Each member is valued independently on the requested common evaluation basis.
Any unvalued endpoint weight leaves the basket unknown; surviving members are
never reweighted. Complete endpoint valuation can survive an incomplete
interior path. Only `R_N`, `MFE_CLOSE` and `MAE_CLOSE` have numeric sector subject
semantics; shared stock extrema/MDD fields remain null / not applicable.
Unknown legacy basket identity is not fabricated or silently backfilled.

`scripts.v4_16_forward_p1_worker` preserves queue V2 keys, source admission,
fenced delivery, CAS, crash/restart and append/ack behavior, while evaluating the
candidate outcome contract. The V1 token in an immutable queue key remains its
queue family identity, distinct from the V1.1 outcome evaluation contract.
This worker rejects real delivery before a source factory is called. No accepted
runtime dependency selects it. Independent acceptance and an explicitly bound
consumer successor are required before real use.

FEP remains an exact outcome-revision copier. Candidate output has no new owner
time allocation and remains PENDING at the real owner gate. Engineering-only
receipt tests demonstrate endpoint/path quality separation. E5 never infers a
canonical identity from a new return. No historical label or permission changes.

## Test isolation boundary

The historical M12 test source files and assertions remain byte-identical.
The new local `conftest.py` binds them to a guarded disposable DB snapshot and a
bounded chart input projection. Legacy test materializations are populated only
in that snapshot from its existing current result rows; a complete publication
is selected only in the disposable publication head. This is fixture preparation,
not a production publication or acceptance change.

The original browser subprocess request is intercepted by the fixture adapter,
validated, and launched through the guarded test launcher. The child uses an
isolated working directory and an explicit minimal environment. NO_REAL_RECOVERY
suppresses production/background recovery inside the child only. Explicit
disposable recovery exercises the real HistoryJobService interruption marking
with `background=False`; copied production compute is never resumed. Production
recovery code remains byte-identical and retains its original behavior.

The first affected-stage fingerprint gate detected a physical change in the live
DuckDB file. This failed run is retained, not presented as a zero-write PASS.
Comparison of every row in 103 tables and all view/index definitions found no
logical changes. A checksum-identical original snapshot and the changed version
were retained; the original bytes/mtime were restored atomically after validation.
The incident/restoration receipt records this correction explicitly.

A new repository pytest plugin now guards all test consumers, including tests
outside M12: live input database connections are forced read-only, explicit live
writers are rejected, real workspace service/recovery roots are rejected, and
unguarded background recovery is rejected. Per-phase connection stack receipts
identify default connection requests. This does not modify production connectors
or recovery. Final acceptance must use a fresh post-guard regression and unchanged
protected fingerprints.

## Acceptance boundary

The only completion classification is
`FORWARD_P1_REPAIR_R1=CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT`.
Tests, commits and pushes do not grant real Shadow, Focus, Production, Default UI,
FEP training or later-stage acceptance. Required next stage:
`INDEPENDENT_EXTERNAL_AUDIT_REQUIRED`.

Storage checkpoint trigger: tests/upgrade_m2/test_api.py module-level WorkbenchRepository.open during collect-only executed schema initialization. The additive pytest plugin provides live-input metadata reads with a read-only handle, bypassing migrations and owner writes. A regression verifies metadata reads and rejected CREATE. Production repository code is unchanged; failed-run evidence is retained.
