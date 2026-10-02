# R7 review handoff: governance cleanup and contract freeze only

Authority is the archived R6 external audit; execution order is the R7 master.
The two task cards authorize governance cleanup and design freeze. They do not
authorize runtime, promotion, database migration or operational cutover.

Starting remote HEAD: `2e3e811eb08d7e350e27c4c1e2767ba91160ef98`.
The final pushed SHA is reported with the delivery. Clean replay binds the tested
source commit; final sealing changes evidence only and checks those source bytes.

## Governance

G01 restores `AGENTS.md` to exact bytes from
`1c46d6681ba1d0540551bcc0f75b35c545ff2769:AGENTS.md`, removing rule 10 without a
replacement. SHA256: `fe3ca08043743023f23d5767bf8d3570e2dc4a72c7215056a2daba53a0ea7a77`;
1616 bytes. Existing rules 1–9 remain intact.

G02 validates the three accepted R6 audit/master/task byte identities in the
repository. Existing files are never overwritten. Missing files require the
explicit `--bundle-dir` argument; without it preparation fails with
`R6_EXTERNAL_BUNDLE_SOURCE_REQUIRED`. Source metadata is durably recorded before
bootstrap writes. Tests use temporary directories. No automatic discovery or
personal directory is part of the script.

Governance evidence: `reports/next_round_r6r1/R6R1_GOVERNANCE_REPLAY_CLEANUP.json`.
Read-only promotion replay covers P01–P33 and 20 R5 hard gates. No promotion is
executed. The Data Head deliberately retains its historical stage hash; chain
preflight reads the exact archived parent bytes and checks current Stage separately
with the accepted promotion validator. The actual Data Head is never repinned.

## Contract inventory

The thirteen versioned files are:

- `config/v4_12_structure_event_contract_v1.json`
- `config/v4_12_anchor_schema_v1.json`
- `config/v4_12_anchor_coordinate_contract_v1.json`
- `config/v4_12_support_state_contract_v1.json`
- `config/v4_12_retention_contract_v1.json`
- `config/v4_12_field_registry_v1.json`
- `config/v4_12_producer_registry_v1.json`
- `config/v4_12_time_role_registry_v1.json`
- `config/v4_12_input_schema_v1.json`
- `config/v4_12_output_schema_v1.json`
- `config/v4_12_parameter_set_v1.json`
- `config/v4_12_machine_ast_v1.json`
- `config/v4_12_machine_vectors_v1.json`

Field/producer/time registries are the three matching files above. The field
registry includes input facts, immutable Anchor metadata, internal AST derivations
and output fields. Producer bindings distinguish canonical OHLC, accepted Core,
calendar/window contracts and design-only D1 producers. JSON Schema validation is
contract validation, not a database migration.

Nine Anchor types have source, availability, identity, coordinate, invalidation
and earliest-test semantics. Original Anchors remain immutable; observation views
are separate. Basis identity is `price_basis + adjustment_source_revision`.
Authenticated affine transforms act on levels; ATR differences use positive scale
only, and returns are recomputed in the common coordinate. Coefficient equality is
never identity. Pivots become available after two actual right-side sessions and
are never backdated. New gap/impulse Anchors cannot test themselves on creation day.

Support freezes ordered rules, consecutive evaluable counters, actual separated
retest evidence and terminal states. Missing observations preserve prior state,
mark stale and break consecutive counters. Acceptance requires two post-event
evaluable held sessions; retention uses an exact denominator without epsilon.
UNKNOWN, NOT_APPLICABLE, PENDING and known absence remain distinct.

Every AST numeric value binds one of 24 parameters or an explained mathematical
constant. All parameters remain `ENGINEERING_CANDIDATE`; profitability validated,
statistically optimal and production proven are false. The literal audit lists
each binding and metadata parameter use.

Allowed DAG: `D1[t] = F0[t] + t-1 frozen Anchor/event`. D2, same-day Final State/Event,
Focus/UI, Supplemental feedback and future outcomes are prohibited inputs. An
internal Support expression is a D1 derivation, not a same-day published Event
input. Today’s new Anchor can emit an event but cannot self-support, accept or
confirm. Earliest normal test is the following market session.

## Explicit capability blocks

These rows are `BLOCKED_WITH_EXPLICIT_REASON`, not silently completed:

1. `close_t_minus_1` / `ma20_t_minus_1`: accepted owner unavailable;
   `FORMAL_BLOCKED_INPUT_CAPABILITY`, `DO_NOT_RECONSTRUCT_FROM_RAW_BARS`.
   Missing input yields `UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE` at the MA20
   branch before lower Recovery rules, even when today’s comparison is false.
   Independently resolvable earlier-priority Recovery rules retain their semantics.
2. Prior frozen Anchor/event publication: design-only producer; runtime is not
   authorized and no accepted D1 publication is claimed.
3. Explicit historical F0 authority for `atr_prior_view`, `prior_high_view`,
   `prior_delta3`, `pivot_low_strict`: unbound required input until an accepted
   producer explicitly publishes the field. Local raw bars do not grant authority.

These capability blocks do not prevent freezing rule design. They do prevent
claiming those formal consumers available at runtime.

## Evidence and verification

- Freeze: `reports/v4_12_r1/V4_12_R1_CONTRACT_FREEZE.json`
- Literals: `reports/v4_12_r1/V4_12_R1_PARAMETER_LITERAL_AUDIT.json`
- DAG: `reports/v4_12_r1/V4_12_R1_DAG_EDGE_AUDIT.json`
- Oracle: `reports/v4_12_r1/V4_12_R1_INDEPENDENT_VECTOR_ORACLE.json`
- Completeness: `reports/v4_12_r1/V4_12_R1_CONTRACT_COMPLETENESS_MATRIX.json`
- Test counts/JUnit, clean replay, source/evidence manifest and four before/after
  protected hashes: `reports/v4_12_r1/R7_FINAL_STOP_HANDOFF.json`

The independent oracle is a separate handwritten REV4 rule book with Decimal
arithmetic in `scripts/v4_12_independent_vector_oracle_r1.py`. It imports no AST
interpreter or future implementation helper. Actual results come from a generic
serialized-expression verifier on synthetic fixtures only. The 69 vectors cover
threshold equality, priority/UNKNOWN, session availability, corporate actions,
revision identity, original immutability and forbidden DAG perturbations. These
are design vectors, not real-market runtime or profitability evidence.

Tests cover governance, all independent vectors, rejected literals/parameters,
capability forgery, future sources, forbidden namespaces, schema types and the
existing Promotion boundary suite. The final JUnit receipt provides exact counts.
Clean detached replay also verifies AGENTS bytes, repo-first preparation and
promotion `post=true`. No full repository runtime pass is claimed; preexisting
M14/M2 audit classifications and unrelated local files are preserved.

Four protected artifacts remain byte-identical to starting remote HEAD:
V4-11 Accepted Head, Stage Head, Data Head and V4-12 Stage Entry. Source diff proves
no new `src/v4` runtime and no schema migration. Stage remains
`V4_00_TO_V4_11_ACCEPTED`; Data remains `2026-09-30`. Production, Shadow, Focus and
Global Mandatory Adoption permissions all remain false.

Final candidate states only:

`R6R1_GOVERNANCE_REPLAY_CLEANUP_CANDIDATE_READY_FOR_EXTERNAL_AUDIT`

`V4_12_R1_CONTRACT_FREEZE_CANDIDATE_READY_FOR_EXTERNAL_AUDIT`

After unified code/evidence delivery and push, STOP and wait for independent
external audit. Neither external acceptance nor V4-12 runtime entry is declared.
