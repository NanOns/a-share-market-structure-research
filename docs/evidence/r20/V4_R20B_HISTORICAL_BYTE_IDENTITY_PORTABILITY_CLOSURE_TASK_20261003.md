# R20B｜Historical Byte Identity Portability Closure｜2026-10-03

## 0. Baseline
Execute from remote HEAD:

`2020234020e09020aca13fd84cdabde6fbb81f50`

This work is P1 governance hardening.

It may run in parallel with R20C/R20D after R20A permits runtime engineering.

R20E final seal requires R20B PASS_LOCAL.

## 1. Goal
Close `R19-AUDIT-01` without rewriting historical accepted business artifacts.

The project must distinguish:
- semantic accepted content identity;
- exact stored byte representation;
- Git blob representation;
- LFS/binary identity;
- explicitly allowed text representation equivalence.

No consumer may silently normalize arbitrary text.

## 2. Inventory Scope
Inventory every current accepted-source artifact reachable from:
- `V4_STAGE_ACCEPTED_HEAD`;
- `V4_DATA_ACCEPTED_HEAD`;
- V4-07..V4-14 Accepted Heads;
- V4-14 Accepted Entry Contract;
- V4-15 contract package;
- current calendar / membership / identity authorities.

For each file record:
```text
path
source kind
Git blob identity
worktree byte identity
accepted binding identity
LFS object identity if applicable
line-ending classification
portability mode
consumer list
```

## 3. Formal Portability Registry
Create a frozen registry, recommended:

```text
config/v4_exact_byte_portability_policy_v1.json
data/v4/V4_EXACT_BYTE_PORTABILITY_REGISTRY_R1.json
```

Allowed modes must be explicit, for example:
```text
LITERAL_EXACT_BYTES
GIT_BLOB_EXACT
LFS_OBJECT_EXACT
AUDITED_CRLF_LF_EQUIVALENT_TEXT
```

Do not use a generic “normalize text” mode.

## 4. CRLF/LF Equivalence Rule
`AUDITED_CRLF_LF_EQUIVALENT_TEXT` is allowed only if all are proven:

1. file is explicitly registered;
2. both accepted representation digest and Git blob digest are frozen;
3. the only byte difference is `CRLF <-> LF`;
4. decoded semantic JSON/text content is identical;
5. no BOM/encoding change;
6. no whitespace/content change beyond newline representation;
7. file is not binary/LFS.

Any additional byte difference must fail closed.

## 5. Binary / LFS
Never normalize:
- `.gz`;
- `.parquet`;
- `.zip`;
- `.bundle`;
- images/PDF;
- any LFS-managed object;
- any artifact registered as binary exact.

Verify LFS pointer SHA and object size where applicable.

## 6. Portable Exact Reader
Create one reusable representation-aware exact reader.

Recommended:
```text
src/workbench_analysis/v4_portable_exact.py
```

Rules:
- default mode is literal exact;
- a representation exception requires registry authority;
- return both:
  - parsed/usable bytes;
  - identity-resolution receipt;
- never hide which representation was accepted.

Receipt:
```text
path
requested_binding
observed_binding
authority_mode
git_blob_binding
accepted_representation_binding
normalization_applied
normalization_kind
semantic_digest
```

## 7. Integration Boundary
R20A current-stage reader may consume this portable exact reader once available.

Historical business logic must not be modified.

Do not rewrite accepted head files merely to normalize line endings.

## 8. Independent Oracle
The independent portability oracle must derive Git blob bytes from Git objects and compare them against:
- registry;
- current worktree representation;
- accepted refs.

Do not import the portable exact implementation to derive expected results.

## 9. Required Cross-Platform Simulation
At minimum simulate:
```text
Windows-style CRLF checkout
Linux-style LF checkout
literal exact JSON
registered CRLF/LF-equivalent JSON
binary/LFS file
```

For an explicitly equivalent text file:
```text
CRLF representation -> PASS with explicit receipt
LF representation   -> PASS with explicit receipt
content mutation     -> FAIL
space mutation       -> FAIL
key/value mutation   -> FAIL
encoding/BOM change  -> FAIL unless separately frozen
```

## 10. Tested Source Addressability
Close the R19 tested-source auditability issue for future rounds.

Required future policy:
- the clean-tested implementation source must be reachable through one immutable repository ref, tag, or branch ancestry visible to an external Git client;
- a binary `.bundle` may be retained as backup evidence but cannot be the only addressable identity.

For R19, record the limitation without rewriting history.

Create a policy rule such as:
```text
FUTURE_TESTED_SOURCE_REMOTE_ADDRESSABILITY = REQUIRED
R19_TESTED_SOURCE_BUNDLE_ONLY = HISTORICAL_DISCLOSED_LIMITATION
```

## 11. Negative Cases
Reject:
- unregistered CRLF/LF normalization;
- binary normalization;
- digest match only after changing non-newline whitespace;
- same parsed JSON but different unregistered bytes;
- missing Git blob;
- missing LFS object identity;
- path escape;
- registry duplicate path;
- two current portability modes for one path;
- tested source only present in opaque bundle for a new future seal.

## 12. Completion
Required:
```text
R20B_BYTE_IDENTITY_PORTABILITY = PASS_LOCAL
R19_AUDIT_01 = CLOSED_LOCAL
PORTABLE_EXACT_READER = PASS_LOCAL
BINARY_LFS_NORMALIZATION = FORBIDDEN
FUTURE_TESTED_SOURCE_REMOTE_ADDRESSABILITY = REQUIRED

V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_14_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

No Stage/Data promotion is allowed in this task.
