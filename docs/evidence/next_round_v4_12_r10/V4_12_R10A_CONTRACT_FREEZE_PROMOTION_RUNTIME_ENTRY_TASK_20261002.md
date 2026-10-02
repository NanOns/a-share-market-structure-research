# V4-12 R10A｜Contract Freeze Promotion + Runtime Engineering Entry｜2026-10-02

**基线 HEAD：** `d99c242ff90180372df1055d5fff266a48f38102`  
**上游外审：** `V4_R9_EXTERNAL_AUDIT = PASS_V4_12_CONTRACT_FREEZE`  
**Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`  
**任务性质：** Governance Promotion / Runtime Entry Only  
**业务 Runtime 实现：** 本卡不实现

# 1. 目标

把已经通过独立外审的 V4-12 Contract Freeze 正式登记成仓库内可消费 authority，并创建：

```text
V4-12 scoped engineering runtime entry authorization
```

本卡是治理入口，不是 V4-12 Stage Accepted Head。

# 2. 必须创建的正式产物

至少：

```text
reports/v4_12/V4_12_CONTRACT_FREEZE_EXTERNAL_ACCEPTANCE_R1.json
reports/v4_12/V4_12_RUNTIME_ENGINEERING_ENTRY_R1.json
```

可增加对应 MD handoff，但 JSON 为机器 authority。

# 3. Contract Freeze Acceptance 必须绑定

必须 exact hash-bind：

```text
current accepted parent:
data/v4/V4_11_ACCEPTED_HEAD.json

V4-12 Stage Entry:
reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json

R8 Source Authority:
reports/v4_12_r2/R8_AUTHORITY_REPAIR_HANDOFF.json
reports/v4_12_r2/V4_12_R2_PRODUCER_AUTHORITY_PARITY.json
reports/v4_12_r2/V4_12_R2_COORDINATE_AUTHORITY_AUDIT.json

R9 Time Counter:
reports/v4_12_r2_1/R9_TIME_COUNTER_HANDOFF.json
reports/v4_12_r2_1/V4_12_R2_1_TIME_COUNTER_SEMANTICS.json
reports/v4_12_r2_1/V4_12_R2_1_TIME_DOMAIN_COMPATIBILITY_AUDIT.json

Frozen contract set:
config/v4_12_*.json
```

并记录：

```text
tested_source_sha = 11d8015d608670572bd57fc50fb6327e2b693a73
audited_remote_head = d99c242ff90180372df1055d5fff266a48f38102
external_audit_status = PASS_V4_12_CONTRACT_FREEZE
```

# 4. Runtime Entry 权限

只授权：

```text
scope =
V4_12_D1_ENGINEERING_RUNTIME_R1
```

允许：

```text
pure D1 engine
frozen AST evaluator
Anchor/Event candidate construction
Support/Acceptance evaluation
session/evaluable counters
candidate staging artifacts
synthetic/frozen replay
fail-closed capability handling
```

不允许：

```text
D2 integration
Final State
Radar
Focus
Validation enrollment
Production
Shadow production
Global mandatory adoption
V4-13
V4_12 Stage Accepted Head
Stage Head advance
Data Head advance
```

# 5. Capability Scope 必须继承

Runtime Entry 必须直接继承 R2/R2.1 capability matrix，不得自动升级任何 blocked input。

继续 blocked 的至少包括：

```text
target-date accepted V4-03 factors:
ATR20
CLV
MA20
MA60
prior_high20
amount_ratio20
rel_market_1
ret1
slope20

near_high20_state target publication
alpha / beta
prior_range20_atr
pivot history
dynamic MA source-event allowlist
previous-session accepted D1 state before runtime history exists
```

这些 capability 只能：

```text
UNKNOWN / BLOCKED_WITH_EXPLICIT_REASON
```

不得：

```text
raw fallback
V4-11 candidate output substitute
local recompute grants authority
```

# 6. Immutable contract rule

R10A 之后，R10B Runtime 必须读取被本 Entry digest-bind 的 frozen contracts。

禁止：

```text
runtime code hardcode另一套业务阈值
runtime code自定义 rule order
runtime code修改 R2/R2.1 contract files
```

如果实现发现合同缺口：

```text
STOP_WITH_CONTRACT_GAP
```

而不是实现者自行决定。

# 7. Readback validator

新增：

```text
scripts/validate_v4_12_runtime_entry_r1.py
```

至少验证：

```text
all frozen contract digests exact
R8/R9 external evidence exact
Stage/Data Heads unchanged
no V4_12_ACCEPTED_HEAD
permissions all false except scoped engineering implementation
blocked capabilities preserved
runtime namespace cannot read D2/Focus/UI
```

# 8. Protected artifacts

不得修改：

```text
AGENTS.md
data/v4/V4_11_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json

reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json

reports/v4_12_r2/*
reports/v4_12_r2_1/*
```

上一轮 evidence 必须 byte-identical。

# 9. 完成状态

只允许：

```text
V4_12_RUNTIME_ENGINEERING_ENTRY_R1_READY
```

R10A 本地 readback PASS 后，允许同一执行批次进入 R10B。

不得自行声明：

```text
V4_12 Stage Accepted
```
