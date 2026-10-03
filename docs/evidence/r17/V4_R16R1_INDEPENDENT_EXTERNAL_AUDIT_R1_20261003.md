# V4-13 R16R1 Independent External Audit R1｜2026-10-03

## 1. Audit Target

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- Audited remote HEAD: `f12315bf8e3142aa44e9068c5895004c35c4e23c`
- Tested implementation source: `d370788688c7e1be0fe2e3c9b0b160d93374b4ee`
- Seal/evidence commit: `f12315bf8e3142aa44e9068c5895004c35c4e23c`
- R16R1 baseline: `92bf5cdefe81da6e809a0dd05dcbd3f651dc35ff`

## 2. Unique Decision

```text
R16R1_EXTERNAL_AUDIT = PASS_SCOPED_ENGINEERING

G01_STRUCTURE_LOSSLESS_PROJECTION = PASS
G02_COMPONENT_SOURCE_PROVENANCE = PASS
G03_INDEPENDENT_ORACLE_O01_O10 = PASS
G04_NUMERIC_REVISION_ORDERING = PASS
G05_PUBLICATION_BOUNDARY_HARDENING = PASS

V4_13_RUNTIME = EXTERNALLY_ACCEPTED_SCOPED_ENGINEERING
V4_13_REAL_SIGNAL_CAPABILITY = DEGRADED_BY_ACCEPTED_UPSTREAM_CAPABILITY
V4_13_ACCEPTED_HEAD = NOT_CREATED

CROSS_STAGE_GOVERNANCE_REPAIR = REQUIRED_BEFORE_PROMOTION
V4_13_ACCEPTED_HEAD_PROMOTION = AUTHORIZED_AFTER_R17A_PASS
V4_14_CONTRACT_STAGE_ENTRY = AUTHORIZED_AFTER_V4_13_PROMOTION
```

R16R1 is accepted for its authorized scope. No R16/R16R1 runtime rewrite is required.

## 3. Accepted KEEP Scope

The following are externally accepted and must be preserved:

- accepted-only input binder;
- exact V4-08 PIT Membership binding;
- target-excluded LOO recomputation;
- no raw/provider fallback;
- capability-scoped fail-closed UNKNOWN;
- current membership relation projection independent from unavailable LOO history;
- minimal `PROFILE_ADVANCED_PROJECTION_V1` v1.2 amendment;
- exact Structure projection mapping for value/quality/reason/provenance with no recomputation;
- component-specific source provenance;
- independent O01-O10 oracle;
- numeric `rN` revision ordering;
- append-only publication and changed-byte rejection;
- strict namespace/revision/trade-date/write-path boundary;
- fresh-process readback;
- same-day revision predecessor isolation;
- full 2026-09-30 real scoped replay: 5224 profiles / 50162 contexts;
- immutable prior r5 and new r6 repair publication;
- protected Raw Qualification artifacts;
- clean detached source/evidence sealing.

## 4. Contract Amendment Decision

The R16R1 decision to create:

```text
config/v4_13_projection_v1_2.json
```

is accepted.

Reason:

- v1.1 froze value source paths but did not uniquely freeze machine-level quality/reason/provenance paths;
- v1.2 is limited to projection/provenance semantics;
- same contract family lineage is preserved;
- no threshold, Anchor selector, Structure owner, B0/B1/B2 or other business rule is changed.

The accepted R16R1 real candidate `r6` binds v1.2 in its exact contract refs.

Promotion must formalize v1.2 in the V4-13 Accepted Head. Future authority must not depend only on informal discovery of an evidence file.

## 5. Real Capability Result

The real 2026-09-30 replay remains correctly degraded:

```text
current_membership = AVAILABLE_EXACT_PIT

target_core_native = UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE
target_seed = UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE
loo_history = UNKNOWN_ACCEPTED_CAPABILITY_UNAVAILABLE
legacy_B2 = NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE

primary_industry = KNOWN
supporting_concepts = KNOWN / NOT_APPLICABLE

algorithmic_support_sector = UNKNOWN
relative_sector_state = UNKNOWN
sector_context_state = UNKNOWN

production = false
shadow = false
focus = false
```

This is a correct fail-closed result. Do not repair it by reading raw/provider data.

## 6. Cross-stage Governance Findings

R16R1 expanded regression reproduced the same 22 failures on the clean detached R16 baseline. Therefore they are not R16R1 regressions.

However, they must not be carried through the next Stage Head promotion without repair.

### CSG-01｜DM01 / V4-10 Historical Moving-Head Binding

Historical accepted objects bind earlier exact bytes of mutable namespace:

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

Current validation may resolve that historical ref against the current moving file and fail with:

```text
EXACT_BINDING_INVALID:data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

This is a publication-history reader/governance defect.

Historical accepted refs must resolve to their exact archived promotion-time bytes, not to the current moving Stage Head.

Do not rewrite historical accepted head bytes to the current SHA.

### CSG-02｜Obsolete Historical Stage Gates

Several V4-09 / V4-12 regression tests still assert old pre-promotion current-state conditions.

They must be converted into:

```text
historical artifact integrity / archived-baseline tests
+
separate current accepted-state tests
```

Do not change algorithm semantics merely to make an obsolete historical assertion pass.

## 7. Promotion Boundary

Before V4-13 Accepted Head creation:

```text
R17A_CROSS_STAGE_GOVERNANCE_REPAIR = PASS
```

must be obtained.

After R17A passes, the following are authorized:

```text
V4_13_ACCEPTED_HEAD promotion
Stage Head:
V4_00_TO_V4_12_ACCEPTED
→ V4_00_TO_V4_13_ACCEPTED

Data Head:
KEEP 2026-09-30
```

No Production / Shadow / Focus permission is implied.

## 8. Next Round

```text
R17A
Cross-stage Accepted-Chain / Historical Validator Repair

→ local + clean gate PASS

R17B
V4-13 Accepted Head Promotion
+ Stage Head advance to V4_00_TO_V4_13_ACCEPTED

→ promotion gate PASS

R17C
V4-14 Replay Gate B Contract Freeze / Stage Entry

→ contract freeze only
→ no ALGORITHM_STATE_REPLAY_PASS claim yet
→ STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT
```
