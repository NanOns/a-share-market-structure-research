# V4 Next Round Execution Master R22R1｜2026-10-04

## 0. Baseline

Repository: `NanOns/a-share-market-structure-research`

Branch: `codex/v4-system-reform`

Execution baseline:

`3fd69721fa8f61aa278b275cb9250bb6829c85a5`

---

# 1. External Decision

```text
R22_EXTERNAL_AUDIT =
PASS_FINAL_V4_16_CONTRACT_FREEZE_CAPABILITY_SCOPED

R22_CLOCK_AUTHORITY_REPAIR_01 =
OPEN_P0_AFFECTED_SCOPE

V4_16_RUNTIME =
BLOCKED_PENDING_CLOCK_AUTHORITY
```

---

# 2. Execute One Work Package

Execute:

`V4_16_R22R1_CLOCK_AUTHORITY_AND_GOVERNANCE_NORMALIZATION_TASK_20261004.md`

Do not start V4-16 runtime.

---

# 3. Topology

```text
A. bind R22 external contract-freeze acceptance
        ↓
B. create post-REV4 V4-16 clock contract
        ↓
C. freeze 21:00 cutoff / 22:30 deadline Asia/Shanghai
        ↓
D. freeze source visibility timestamp semantics
        ↓
E. create Observation Slot Contract V2 candidate
        ↓
F. create PRE16 Current Audit Authority V3 descriptive normalization
        ↓
G. independent clock/visibility oracle
        ↓
H. clock machine vectors
        ↓
I. protected-byte verification
        ↓
J. clean regression
        ↓
K. exact tested source + candidate seal
        ↓
commit + push
        ↓
STOP_WAIT_R22R1_INDEPENDENT_EXTERNAL_AUDIT
```

---

# 4. Hard Boundaries

Do not:

```text
rewrite historical V4-00C
modify Stage Head
modify Data Head
modify V4-10～15 Accepted Heads
modify V4-15 business runtime
start real Shadow
claim PIT_OBSERVED
create V4_16_ACCEPTED_HEAD
grant Production/Focus/UI cutover
```

---

# 5. Policy Values

```text
timezone = Asia/Shanghai
scheduled_source_cutoff = 21:00:00
observation_deadline = 22:30:00

UTC =
13:00:00Z
14:30:00Z
```

These are ex-ante project policy values, not historical source-availability claims.

---

# 6. Exit

```text
R22R1_CLOCK_AUTHORITY =
PASS_LOCAL_READY_FOR_EXTERNAL_AUDIT

R22 contract freeze =
PASS_KEEP

V4_16 runtime =
NOT_AUTHORIZED

REAL_SHADOW_OBSERVATIONS =
0

Stage =
V4_00_TO_V4_15_ACCEPTED

Data =
2026-09-30

Production = false
Shadow = false
Focus = false

NEXT =
STOP_WAIT_R22R1_INDEPENDENT_EXTERNAL_AUDIT
```
