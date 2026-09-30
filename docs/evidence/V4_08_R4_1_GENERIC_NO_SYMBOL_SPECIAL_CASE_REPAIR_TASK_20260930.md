# V4-08 R4.1｜Repo-wide No-Symbol-Special-Case Repair + Generic Equivalence Replay

**Project:** 大A交易 / A-Share Market Structure Research  
**Repository:** `NanOns/a-share-market-structure-research`  
**Branch:** `codex/v4-system-reform`  
**Required Starting HEAD:** `0d959b24a44528265aff4784d8c283902f0abd3e`  
**Date:** 2026-09-30

# 0. External decision

```text
V4_08_R4_EXTERNAL_ACCEPTANCE_BLOCKED
P0_NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC_FALSE_PASS
```

Do not redo PIT source research, membership contract B01-B07, calendar research, 11-key lifecycle research, or four-state AST.

Primary objective:

```text
REMOVE STOCK-SPECIFIC CODE DEPENDENCY
+
FIX GOVERNANCE SCANNER
+
PROVE GENERIC REPLAY PRODUCES SAME R4 RESULT
```

# 1. Hard invariant

No project functional logic may alter behavior because of a specific stock code.

Forbidden in:

```text
PRODUCTION_RUNTIME
SYSTEM_PIPELINE
GOVERNANCE_MUTATION
RUNTIME_CONFIGURATION
```

Examples:

```python
if code == "600519":
if symbol in {"SZ.001246","SZ.301716"}:
special_threshold["300750"] = ...
```

This includes QA gates that influence PASS/BLOCKED.

# 2. Allowed symbol-bearing scopes

Specific equity identifiers may exist only as data in:

```text
TEST_ONLY
EVIDENCE_ONLY
AUDIT_INPUT_ONLY
USER_DATA
IMMUTABLE_FACT_DATA
```

Typed market-index reference data remains allowed as:

```text
REFERENCE_DATA / MARKET_INDEX
```

# 3. Scanner category model

Replace current path logic where all `scripts/**/*.py` become `AUDIT_ONLY`.

Required categories:

```text
PRODUCTION_RUNTIME
SYSTEM_PIPELINE
GOVERNANCE_MUTATION
RUNTIME_CONFIGURATION
REFERENCE_DATA
AUDIT_ONLY
TEST_ONLY
EVIDENCE_ONLY
USER_DATA
UNCLASSIFIED_FAIL_CLOSED
```

Hard-gated:

```text
PRODUCTION_RUNTIME
SYSTEM_PIPELINE
GOVERNANCE_MUTATION
RUNTIME_CONFIGURATION
```

Expected:

```text
specific_stock_literal_hits = 0
```

# 4. scripts default fail-closed

`scripts/**/*.py` must no longer default to AUDIT_ONLY.

Default should be:

```text
SYSTEM_PIPELINE
```

or:

```text
UNCLASSIFIED_FAIL_CLOSED
```

A script may become AUDIT_ONLY only through explicit policy proving:

```text
runtime_authorized = false
does_not_write_accepted_heads = true
does_not_write_runtime_artifacts = true
not_called_by_production = true
```

# 5. Governance mutation classification

At minimum classify as `GOVERNANCE_MUTATION`:

```text
scripts/promote_*.py
scripts/accept_*.py
scripts/materialize_*.py
scripts/apply_*.py
scripts/*accepted_head*.py
scripts/*publication*.py
```

Also detect scripts writing:
- `data/v4/*ACCEPTED*`
- `data/v4/artifact_store/`
- publication heads
- runtime state heads

Do not rely only on filename.

# 6. Production call graph

Explicitly classify:

```text
src/production/daily.py
→ src/phase1_runner.py
→ src/phase1_qa.py
→ phase2/3/4/5 runners
```

These cannot remain AUDIT_ONLY.

If a production/system module imports another project module, file naming cannot downgrade that dependency.

# 7. Fix R4 identity promotion

Current forbidden literals:

```text
SZ.001246
SZ.301716
```

Remove all symbol-specific expected sets.

Generic promotion set:

```text
authorized candidate artifact
→ new_lifecycle_events
→ records with acceptance=CANDIDATE_PENDING_EXTERNAL_PROMOTION
```

Promotion may change only:

```text
acceptance
```

No code literal.

# 8. Fix promotion verifier

Current verifier repeats the same two symbols.

Remove them.

Independent expected set must be recomputed from:

```text
parent accepted artifact
candidate artifact
candidate head
external authorization digest
```

Checks:
- new records = candidate - parent
- all new records promoted
- only acceptance changed
- no parent row changed
- no unauthorized row added

No producer expected-set import.

# 9. Phase1 sample refactor

Remove:

```python
SAMPLES=(
 'SH.600519',
 'SZ.000001',
 'SZ.000651',
 'SZ.300750',
 'SH.688001'
)
```

Introduce a versioned deterministic sample-selection contract.

Recommended eligibility:

```text
accepted current universe
AND actual bar at cutoff
AND sufficient history
AND required quality
```

Recommended selection:

```text
board-stratified
+
stable hash(security_id + contract_seed)
```

No random/time-dependent choice.

Sample count may remain five, but exact identities must be data-derived.

# 10. Phase1 QA invariance

Prove factor outputs are byte/logically unchanged before vs after sample-selector refactor.

Only allowed behavioral change:

```text
which securities are used for QA reproduction
```

Persist selected sample set as evidence with:
- selection_contract_id
- eligible_count
- selected IDs
- board
- selection reason
- stable seed/digest

# 11. Phase0 / TDX code cleanup

Review:

```text
src/phase0_2_runner.py
src/phase0_2a_runner.py
src/phase0_2b_runner.py
src/tdx/tdx_audit.py
```

Every literal equity symbol must be handled by one of:

## A. System gate
Refactor to deterministic data-driven sampling.

## B. Historical acceptance fixture
Move to TEST_ONLY / EVIDENCE_ONLY with:

```text
runtime_authorized = false
```

No literal equity symbol may remain in SYSTEM_PIPELINE.

# 12. Market index exception

Market indices may remain typed reference data:

```text
SH.000001
SZ.399001
SZ.399006
```

Prefer registry access via:

```text
config/v4_market_reference_instruments_v1.json
src/common/market_reference.py
```

Do not use them as stock-specific branches.

# 13. Runtime configuration rule

All runtime-influencing config JSON/YAML must be scanned.

Specific equity literal in runtime config:

```text
FAIL
```

unless explicitly classified:
- REFERENCE_DATA
- IMMUTABLE_FACT_DATA
- USER_DATA
- AUDIT_INPUT_ONLY

and schema prevents rule override use.

# 14. Required scanner negative tests

Inject violations and prove FAIL:

1. production Python equality;
2. production Python set membership;
3. governance mutation script;
4. runtime JSON `threshold_by_symbol`;
5. SQL CASE/IN on security code;
6. production-called `qa.py`;
7. production-called `runner.py`.

Prove PASS for:
1. TEST_ONLY fixture;
2. EVIDENCE_ONLY lifecycle fact;
3. USER_DATA Focus symbol;
4. MARKET_INDEX reference row.

# 15. Required scan receipt

Create:

```text
reports/v4_08/V4_08_R4_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json
```

Must include:
- scanned paths
- category per file
- production call graph
- governance mutation paths
- runtime config paths
- all symbol literals
- allowed evidence/test/reference hits
- hard-gated hits
- unclassified paths

Terminal:

```text
hard_gated_equity_symbol_hits = 0
unclassified_paths = 0
status = PASS
```

# 16. Generic identity promotion equivalence

Re-run identity promotion generically from exact R3 candidate.

Compare against current accepted identity artifact.

Preferred result:

```text
generic accepted identity SHA256
==
4c3445f7b1337fee09e942ac854d0cefcecfc8c90c0b7432d991cadc58818ecd
```

Do not encode this digest into business logic; it is an acceptance expectation only.

If identical:

```text
CURRENT_IDENTITY_PROMOTION_DATA_SALVAGED
```

If not:
- create R4.1 accepted identity revision
- explain every logical difference
- do not hide mismatch

# 17. Generic PIT equivalence replay

Using generic promotion result, rematerialize PIT.

Acceptance expectations only:

```text
source_revision_id =
sha256:190f9647cb8b6b610dd5336a76dc8b483e3a31439bdb0140bd95523c45905386

snapshot_id =
3dd77c68f3f29601b59d09853a70977bfab15f3fba3edeca6737f75ef9d7bcc0

fact artifact SHA256 =
164142652bf5b3032f4e1a8ee54fe2817a3f3b5130635cf04fb641a6e819211d

row_count =
50162
```

If mismatch:

```text
FAIL_EQUIVALENCE_REPLAY
```

and explain independently.

# 18. PIT / AST do not need redesign

Do not alter unless regression fails:
- membership contract
- source-time policy
- migration 019
- four-state AST
- retention N/A semantics
- sector-type admission
- calendar sessions
- lifecycle facts

R4.1 is governance/generalization repair.

# 19. Clean regression

Run clean detached implementation commit:
- disposable PostgreSQL
- no config/.env
- process-only DSN
- git clean before/after
- cluster destroyed

Run existing required families plus upgraded governance suite.

Record actual test count.

# 20. Accepted-head rule

Do not create:

```text
V4_08_ACCEPTED_HEAD.json
```

until independent re-audit accepts R4.1.

Keep global range:

```text
V4_00_TO_V4_07_ACCEPTED
```

# 21. Required evidence

At minimum:

```text
reports/v4_08/V4_08_R4_1_STAGE_ENTRY.md
reports/v4_08/V4_08_R4_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json
reports/v4_08/V4_08_R4_1_PRODUCTION_CALL_GRAPH_CLASSIFICATION.json
reports/v4_08/V4_08_R4_1_GENERIC_IDENTITY_PROMOTION_EQUIVALENCE.json
reports/v4_08/V4_08_R4_1_GENERIC_PIT_EQUIVALENCE.json
reports/v4_08/V4_08_R4_1_PHASE1_QA_SAMPLE_SELECTOR.json
reports/v4_08/V4_08_R4_1_ISOLATED_REGRESSION.json
reports/v4_08/V4_08_R4_1_CLEAN_CHECKOUT_RECEIPT.json
reports/v4_08/V4_08_R4_1_STAGE_CANDIDATE_MANIFEST.json
reports/v4_08/V4_08_R4_1_CLOSURE.md
```

# 22. Terminal state

Success:

```text
V4_08_R4_1_GENERIC_GOVERNANCE_REPAIR_READY_FOR_FINAL_EXTERNAL_ACCEPTANCE
```

Failure:

```text
V4_08_R4_1_BLOCKED_<EXACT_SCOPE>
```

# 23. Final handoff

Report:
- pushed HEAD
- scanner policy changes
- hard-gated path categories
- removed stock literals by file
- remaining allowed stock literals by evidence/test/user-data/reference category
- production call graph
- Phase1 dynamic sample set
- generic promotion artifact digest
- generic PIT replay digests
- regression
- no final V4-08 Accepted Head assertion

Then stop for independent audit.
