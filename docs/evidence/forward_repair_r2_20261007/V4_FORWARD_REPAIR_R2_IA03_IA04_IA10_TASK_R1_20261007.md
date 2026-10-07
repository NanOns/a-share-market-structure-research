# V4 Forward Repair R2｜IA-03 + IA-04 + IA-10 定点修复任务卡 R1｜2026-10-07

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 执行基线: `15a4e1cc545f6c44d94ebb2b63e71fba6c69e63a`
- 前置外审: `V4_FORWARD_P1_REPAIR_R1_FINAL_INDEPENDENT_EXTERNAL_AUDIT_R1_20261007.md`
- 性质: 第二批定点修复；V1.1继续保持 simulation-only，不做 Real Shadow / Production promotion。

## 1. 唯一范围

只修：

```text
IA-03 = P2 / same-source PENDING→DUE state collision
IA-04 = P2 / actual price + OHLC boundary hardening
IA-10 = P2 / standalone CLI bootstrap
```

保持：

```text
IA-09 = PASS_KEEP
IA-01 = PASS_KEEP
IA-02 = PASS_KEEP

IA-05 = OPEN_P1
IA-06 = OPEN_P1
IA-07 = OPEN_P2
IA-08 = OPEN_P2
```

禁止扩大成全仓清债。

## 2. IA-03｜PENDING→DUE 幂等状态碰撞

### 问题

当前 engineering SettlementRuntime 的 outcome identity 主要由：

```text
enrollment_id
horizon
outcome contract
evaluation_source_digest
```

组成。

同一 evaluation source 下：

```text
pre-due PENDING
→ due 后 OBSERVED/DUE
```

可能命中同一 immutable outcome reference，导致 due 状态不能合法追加。

### 修复原则

优先确认正式设计是否本来就要求：

```text
PENDING 不进入 outcome revision ledger
```

若允许，优先把 PENDING 保留在：

```text
due_plan / planner / obligation
```

只有真正可评估/终止结果进入 immutable outcome ledger。

如果必须持久化 PENDING outcome，则建立冻结、可复现的 state-revision identity，例如基于：
- due-state role；
- maturity state；
- accepted market-session identity。

禁止：

```text
now()
random UUID
process/run id
```

进入 identity。

### Required vectors

```text
I3-01 pre-due -> PENDING
I3-02 same source after due -> OBSERVED/DUE succeeds
I3-03 repeated pre-due -> idempotent
I3-04 repeated due -> idempotent
I3-05 corrected source -> append new evaluation revision
I3-06 first_observed/latest_corrected intact
I3-07 restart between pre-due and due
I3-08 PENDING cannot overwrite accepted OBSERVED
I3-09 due cannot overwrite historical PENDING bytes
I3-10 no wall-clock/random identity
```

历史 accepted outcome 不得改写。

成功：

```text
IA-03 = CANDIDATE_FIXED
```

## 3. IA-04｜Actual Price / OHLC Boundary Hardening

### 已确认问题

当前 sentinel 已证明：

```text
negative ordinary price
invalid OHLC envelope
```

仍可能被标记：

```text
OBSERVED
```

但合法 delisting：

```text
terminal_value = 0
```

必须继续允许。

所以不能简单全局写 `price <= 0 reject`。

### 先冻结 owner authority

修代码前先生成：

```text
PRICE_DOMAIN_AUTHORITY_READBACK.json
```

从当前正式设计 / canonical daily / adjustment owner contract 中明确：
- ordinary actual close/high/low 合法域；
- OHLC envelope；
- suspension；
- delisted terminal；
- adjusted-price 例外。

主设计不够时，建立 additive successor contract；不得凭常识静默改定义。

### 最低原则

对 ordinary actual price：
- 非法有限值不得继续 OBSERVED；
- transformed price 也必须落在正式合法域；
- invalid OHLC envelope 必须 fail closed / quality unknown。

Terminal delist 单独走：

```text
status=DELISTED
terminal_verified=true
terminal_evidence exists
terminal_value
```

不能和 ordinary OHLC 共用普通价格规则。

如果 owner contract支持，至少验证：

```text
low <= close <= high
```

有 open 时再按正式 schema 扩展，不 invent 字段。

### Required vectors

```text
I4-01 ordinary negative close -> not OBSERVED
I4-02 zero ordinary close -> contract-defined reject/unknown
I4-03 high < close -> reject/unknown
I4-04 low > close -> reject/unknown
I4-05 low > high -> reject/unknown
I4-06 transformed negative actual price -> reject/unknown
I4-07 NaN/Inf -> fail closed
I4-08 valid positive OHLC -> parity
I4-09 DELISTED terminal_value=0 + verified evidence -> R_N=-1 allowed
I4-10 terminal zero without verified evidence -> not accepted
I4-11 confirmed suspension -> no synthetic bar
I4-12 IA-01 endpoint/path separation remains valid
```

成功：

```text
IA-04 = CANDIDATE_FIXED
```

## 4. IA-10｜DM01 Standalone CLI Bootstrap

### 问题

部分 DM01 R4/R4R1/daily scripts 在 clean child process 中直接：

```text
python script.py
```

只加入 `src`，但还 import `scripts.*`，repo root 不在 sys.path 时启动失败。

这不是九组件算法错误，只是 launcher/bootstrap 缺口。

### 修复

冻结一种或两种正式支持方式：

```text
A. python -m scripts.<module>
B. 统一 scripts/_bootstrap.py（或等价 helper）
```

不要每个脚本复制不同 sys.path hack。

统一 bootstrap 必须：
- resolve repo root；
- prepend root；
- prepend src；
- no cwd dependency；
- no user-site implicit dependency；
- clean child env 可执行。

### Required vectors

```text
CLI-01 clean child --help
CLI-02 cwd outside repo
CLI-03 PYTHONPATH empty
CLI-04 future session -> WAIT / no capture
CLI-05 no accepted target session -> fail closed / no data mutation
CLI-06 dry/preflight -> no TDX write
CLI-07 authorized isolated fixture session executes bootstrap
CLI-08 direct supported launcher vs module launcher contract一致
```

禁止修改 DM01 九组件数值语义、Accepted Data Head promotion、source authority、TDX read-only、R25 business gate。

成功：

```text
IA-10 = CANDIDATE_FIXED
```

## 5. Successor policy

IA-03/04 会改变 Forward candidate 语义。

禁止原地覆盖已外审通过的 V1.1 bytes。

如需业务语义变化：

```text
建立 FORWARD_PRICE_PATH_V1_2
```

或等价 successor。

IA-01 / IA-02 语义必须全部继承。

Sector 若受 IA-04 影响，同样建立对应 successor identity。

## 6. Runtime promotion继续禁止

即使 R2 全过：

```text
active accepted runtime
```

也不能自动选择新 successor。

继续保持：

```text
simulation-only
no accepted runtime dependency selects candidate
```

后续另发：

```text
FORWARD_SUCCESSOR_ADMISSION_AND_RUNTIME_PROPAGATION
```

完成 dependency / worker / R25 exact propagation。

## 7. Tests

必须重跑：

```text
IA-03 vectors
IA-04 vectors
IA-10 clean child vectors

IA-01 12 vectors PASS_KEEP
IA-02 12 vectors PASS_KEEP
IA-09 critical isolation vectors PASS_KEEP
settlement worker targeted
protected-state/fingerprint
```

本轮不要求关闭 IA-05 / IA-06。

## 8. Required evidence

建议：

```text
reports/forward_repair_r2_20261007/
```

至少：

```text
ENTRY_BASELINE.json
PRICE_DOMAIN_AUTHORITY_READBACK.json

IA03_STATE_REVISION_PROOF.json
IA03_VECTOR_MATRIX.json

IA04_PRICE_DOMAIN_PROOF.json
IA04_VECTOR_MATRIX.json

IA10_BOOTSTRAP_PROOF.json
IA10_CHILD_PROCESS_MATRIX.json

PASS_KEEP_IA01_IA02_IA09.json
AFFECTED_REGRESSION_SUMMARY.json
OPEN_ISSUES_PRESERVED.json
PROTECTED_STATE_READBACK.json
CHANGED_FILE_LIST.json
CANDIDATE_SEAL.json
COMPLETION_REPORT.md
```

## 9. Protected State

必须保持：

```text
V4 accepted heads unchanged
Current Audit Head unchanged unless separately authorized

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

runtime_authorized = false
real_shadow_authorized = false
production = false
focus = false
default_ui = false

FEP permissions unchanged

IA-05 = OPEN
IA-06 = OPEN
IA-07 = OPEN
IA-08 = OPEN
```

## 10. Completion Status

唯一允许：

```text
FORWARD_REPAIR_R2 =
CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

IA-03 = CANDIDATE_FIXED
IA-04 = CANDIDATE_FIXED
IA-10 = CANDIDATE_FIXED
```

不得自报：

```text
GLOBAL_PYTEST_PASS
FORWARD_ACTIVE_RUNTIME_PROMOTED
FIRST_REAL_SHADOW_AUTHORIZED
V4_15_FULL_PASS
V4_16_FULL_PASS
PRODUCTION_READY
```

## 11. 后续

R2 外审通过后，再决定：
1. Round 3：IA-05 / IA-06 / IA-07 / IA-08；
2. 或先做 `FORWARD_SUCCESSOR_ADMISSION_AND_RUNTIME_PROPAGATION`。

具体顺序以 R2 的实际回归结果为准。

**文档结束**
