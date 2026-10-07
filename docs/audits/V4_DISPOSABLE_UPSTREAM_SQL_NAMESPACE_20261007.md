# V4-TEST-SQL-ALIAS-01

Scope: the new disposable current-schema clone must preserve Phase 0 upstream migration namespace verification independently from product cutover.

Evidence: two original Phase 0 schema tests failed because the template stored identical actually executed SQL only under FEP canonical names. Tables and constraints existed; required upstream ledger names were absent.

Repair: use the already accepted scripts/forward_remainder_pg.py upstream alias contract. For every alias require the actual canonical migration row checksum to equal the current exact SQL file checksum; add only a verification alias on the newly cloned owned test database. No SQL reexecution, schema relaxation, production mutation or test assertion changes.

Acceptance: both original failing Phase 0 tests passed. Status: CLOSED_LOCAL; fresh complete V4 regression passed.
