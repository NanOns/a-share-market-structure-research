# V4-08 R4.1 Closure

## Result

`V4_08_R4_1_GENERIC_GOVERNANCE_REPAIR_READY_FOR_FINAL_EXTERNAL_ACCEPTANCE`

Implementation commit: `60a18f9ce265a36547217c48dca3f3c0b2cd50a7` on `codex/v4-system-reform`. The implementation is ready for the independent external acceptance specified by the attached task. This is not the external acceptance decision.

## Governance scanner

The versioned `NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC` scanner (`1.2.1`) scanned 1882 paths. It reports `0` hard-gated hits and `0` unclassified paths, with status `PASS`. All 109136 hit records occur once in `all_symbol_literals`; 108969 permitted test/evidence/audit-input/user/fact/reference hits and 167 source-hash-attested audit-script hits index that list. Counts by category: `{"AUDIT_INPUT_ONLY": 42, "AUDIT_ONLY": 167, "EVIDENCE_ONLY": 28300, "IMMUTABLE_FACT_DATA": 79645, "REFERENCE_DATA": 6, "TEST_ONLY": 976}`.

Hard-gated categories are `PRODUCTION_RUNTIME`, `SYSTEM_PIPELINE`, `GOVERNANCE_MUTATION`, and `RUNTIME_CONFIGURATION`. The production call graph classifies `src/production/daily.py`, Phase1 runner/QA, and Phase2–5 runners as `PRODUCTION_RUNTIME`; the receipt contains 31 nodes and 56 edges. All injected violations and permitted-category scanner controls passed.

Generic removal covered Phase0 QFQ/TDX audit sample lists, Phase1 QA fixed identities, R4 promotion and verifier expected sets, the V4-01 blind-case gate, alias-repair input selection, and legacy finalizer/seal scanner literals. No literal remains in a hard-gated path. Typed market indexes remain `REFERENCE_DATA`; symbol-bearing test, evidence, audit-input, and immutable factual records are retained in their permitted categories.

## Generic identity promotion and PIT replay

- Generic identity promotion: `PASS_CURRENT_IDENTITY_PROMOTION_DATA_SALVAGED`; generic artifact SHA-256 `4c3445f7b1337fee09e942ac854d0cefcecfc8c90c0b7432d991cadc58818ecd` equals current accepted artifact SHA-256 `4c3445f7b1337fee09e942ac854d0cefcecfc8c90c0b7432d991cadc58818ecd`. Parent rows were preserved and only `acceptance` changed on authorized additions; the independent verifier did not import the producer expected set.
- Generic PIT replay: `PASS_GENERIC_PIT_EQUIVALENCE_REPLAY`. Source revision `sha256:190f9647cb8b6b610dd5336a76dc8b483e3a31439bdb0140bd95523c45905386`; snapshot `3dd77c68f3f29601b59d09853a70977bfab15f3fba3edeca6737f75ef9d7bcc0`; logical digest `f29596cd59d401fc4fe8d728b3bd32324a46cc116020d64ffb70609f03a9fbc6`; artifact SHA-256 `164142652bf5b3032f4e1a8ee54fe2817a3f3b5130635cf04fb641a6e819211d`; 50162 formal rows (INDUSTRY 5224, THEME 44938). Determinism, independent row/field verification, exclusion inventory, and R4 equivalence checks passed.
- Phase1 selector: `PASS`; 5464 eligible identities; selected five identities across the five board strata. Independent QA passed 145/145 checks; RS passed; factor-frame digest was unchanged before selector, after selector, and after QA; existing factor artifact SHA-256 `e5c1a5771aad89b87168c966b7c498cd22cb54bee8326d8077ff7278541a0572` stayed unchanged.

## Isolated regression

Detached implementation commit `60a18f9ce265a36547217c48dca3f3c0b2cd50a7` passed 643 tests: 641 passed, 2 skipped, 0 failures, 0 errors. Disposable PostgreSQL 18.6 migrations 001–019 passed; the DSN came only from process environment; `.env` was not present/read in the clean checkout; Git was clean before and after; the temporary cluster was destroyed.

## Scope and handoff

The global accepted range remains `V4_00_TO_V4_07_ACCEPTED`. No `data/v4/V4_08_ACCEPTED_HEAD.json` was created; V4-08 remains an engineering candidate pending final external acceptance. `AUD-AMOUNT-A-06` remains a separately tracked open audit item.

Next stage: independent external acceptance of R4.1. Stop implementation here until that review result arrives.

Evidence manifest: `reports/v4_08/V4_08_R4_1_STAGE_CANDIDATE_MANIFEST.json`. Scanner report: `reports/v4_08/V4_08_R4_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json`; it excludes its own output path to prevent self-reference and binds the other scanned inputs by source hash.

