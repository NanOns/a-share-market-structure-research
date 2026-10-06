# 大A市场结构研究系统 V4｜Forward P1 修复批次 R1：IA-09 测试隔离 + IA-01 Stock Forward + IA-02 Sector Forward

> 日期：2026-10-06
> Repository：`NanOns/a-share-market-structure-research`
> Branch：`codex/v4-system-reform`
> 执行基线 HEAD：`0c78051c570bdd68ef98f1cb9fdcfcd315759ec2`
> 来源审计：
> - `V4_00_22_FEP_INDEPENDENT_FULL_SCOPE_AUDIT_R1_20261006.md`
> - `V4_00_22_FEP_COMPREHENSIVE_CROSS_MODEL_AUDIT_R1_20261006.md`
> 性质：P1 定点修复；不推进新阶段，不重开 00～14，不授予 Real Shadow / Production。

## 0. 唯一目标

本轮只关闭：

```text
IA-09 = P1 / TEST ISOLATION
IA-01 = P1 / STOCK FORWARD CONTRACT DEVIATION
IA-02 = P1 / SECTOR FORWARD INTEGRATION + FIELD SEMANTICS
```

以下全部保持 OPEN / PASS_KEEP，不在本轮顺手关闭：

```text
IA-03 / IA-04 / IA-05 / IA-06 / IA-07 / IA-08 / IA-10
A04_H21_CONSUMER
A04_HISTORICAL_AMOUNT_A
HISTORICAL_PIT_EFFECTIVENESS
R3C OPEN items
V4_12_REAL_OWNER_CAPABILITY
V4_13_REAL_OWNER_CAPABILITY
REALTIME_ACCEPTED_COHORT_MATURITY
REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT
```

## 1. 不可跨越的边界

保持：

```text
V4-00～V4-14 = PASS_KEEP / SCOPED_PASS_KEEP
V4-15 historical accepted artifacts = IMMUTABLE
FEP E1～E5 historical engineering acceptance = PASS_KEEP
P0-01/P0-02/P1-03/P1-04/P1-05/P1-06/P2-07 = PASS_KEEP
```

不得重写历史 accepted outcome，不得用改历史字节的方式让新测试通过。

本轮结束后仍必须：

```text
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
runtime_authorized = false
real_shadow_authorized = false
Production = false
Focus cutover = false
Default UI cutover = false
V4_16 formal Accepted Head = NOT_CREATED
V4_17G = NOT_GRANTED
V4_18 runtime = NOT_STARTED
V4_19 cutover = false
V4_20 cutover = false
V4_21 real observation = NOT_STARTED
V4_22 final = NOT_GRANTED
FEP_PRODUCTION = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
REAL_OOS = NOT_GRANTED
CHAMPION = NONE
```

A08 当前状态保持，不重新设计、不扩大 scope、不借本轮授予 runtime grant。

## 2. 执行顺序

必须：

```text
Step 1  IA-09 测试隔离安全
   ↓
Step 2  IA-01 Stock Forward
   ↓
Step 3  IA-02 Sector Forward
   ↓
Step 4  targeted regression
   ↓
Step 5  affected-stage regression
   ↓
Step 6  protected-state / exact-byte readback
   ↓
Candidate seal
```

IA-09 未关闭前，禁止运行会启动真实工作区服务/数据库恢复逻辑的全仓测试。

# 3. IA-09｜测试隔离安全

## 3.1 问题

独立审计确认旧浏览器测试可能用实际工作区 DB/ROOT 启动通用服务；服务 startup recovery 可能执行 job/attempt recovery 或后台重跑。

因此：

```text
浏览器断言只读
!=
服务启动过程只读
```

## 3.2 修复

建立统一 Test Isolation Guard（可新增 `tests/support/runtime_isolation.py` 或等价模块），至少提供：

```text
assert_disposable_root()
assert_disposable_database()
assert_not_configured_source_root()
assert_not_repo_working_database()
assert_test_recovery_mode()
```

要求：

- 测试 DB 必须位于 pytest temp 或显式 disposable test root。
- 若 DB 位于正式 `data/database/`、正式开发/生产 DB root，启动前 fail closed。
- 服务 root 必须是 isolated fixture root，不能把真实 repository work root 当可写 runtime root。
- Recovery 只能：
  1. 专用 no-real-recovery mode；或
  2. disposable DB 上执行真实 recovery。
- 禁止“真实工作区 DB + 通用 recovery”。

## 3.3 前后指纹

测试前后记录：

```text
database path
database hash/mtime/size
current heads
jobs state summary
artifact directory digest
publication directory digest
```

正式 protected roots 必须 PRE == POST。

若无法完整 DB byte hash，必须明确 coverage，不得无证据宣称“零 DB 写”。

## 3.4 必测

```text
TISO-01 real work DB path -> reject before service startup
TISO-02 repo writable runtime root -> reject
TISO-03 configured TDX root as output -> reject
TISO-04 disposable DB + isolated root -> allow
TISO-05 disposable recovery mutates only disposable DB
TISO-06 protected real DB fingerprint unchanged
TISO-07 background recovery cannot escape disposable root
TISO-08 subprocess inherits explicit TEMP/TMP/PYTHONPATH/test root only
```

## 3.5 测试纪律

IA-09 定点通过前：

```text
禁止默认全仓 pytest
禁止 continue-on-collection-errors 全仓跑
```

只允许运行不启动真实服务/数据库的纯静态/单元测试。

成功状态：

```text
IA-09 = CANDIDATE_FIXED_TEST_ISOLATION
```

不得自报 `GLOBAL_PYTEST = PASS`；IA-05 继续 OPEN。

# 4. IA-01｜Stock Forward Endpoint Return 与 Path Quality 解耦

## 4.1 问题

当前 `src/workbench_analysis/v4_15_settlement_successor.py` 会先验证整条 path；任一 interior row 缺价格、缺 adjustment proof 或 identity 不完整，就返回：

```text
ADJUSTMENT_UNKNOWN
R_N = null
```

即使 T0 与 T+N endpoint 本身都已经有效。

冻结设计要求：

```text
ENDPOINT_RETURN_INDEPENDENT_IF_VERIFIED
```

因此 endpoint return quality 与 path metric quality 必须解耦。

## 4.2 正确语义

至少逻辑上拆成：

```text
ENDPOINT_QUALITY
PATH_QUALITY
```

不强制新增 DB 字段；优先兼容现有 schema。

### Endpoint

只有以下直接决定 `R_N`：

```text
T0 reference
T+N endpoint
evaluation basis
endpoint adjustment identity
terminal-state semantics
```

这些满足后：

```text
R_N = endpoint / P0 - 1
```

可计算。

### Path

`MFE / MAE / MDD` 需要完整可解释 path。

若 interior path 不完整：

```text
R_N 保留
path metrics = null / UNKNOWN
path reason = explicit
```

禁止 internal UNKNOWN 抹掉已验证 endpoint R_N。

## 4.3 仍须 fail closed

以下任一出现：

```text
T0 invalid
T0 basis invalid
endpoint missing
endpoint invalid
endpoint affine invalid
endpoint identity mismatch
basis mismatch
illegal terminal semantics
```

则：

```text
R_N = null
```

修 IA-01 不能降低 endpoint 严格性。

## 4.4 Suspension / Corporate Action

Confirmed suspension、unknown missing bar、data missing 必须按冻结合同区分，不得发明新估值规则。

跨除权/分红/送转时，T0 与 endpoint 都转换到同一 evaluation basis；endpoint 可独立有效，路径指标仍要求每个参与路径计算的点具备可验证坐标。

## 4.5 Relative Return

若：

```text
target R_N valid
benchmark endpoint return valid
```

相对收益不得仅因 target interior path metric UNKNOWN 被清空。

benchmark 自身 endpoint 仍按独立合同验证。

## 4.6 FEP

不重写历史 FEP label。

要求：

```text
新修复 outcome
→ append successor/revision
→ FEP 只消费新 accepted revision
```

历史受影响 outcome 保持 immutable。

## 4.7 Required vectors

```text
STK-01 full valid path -> parity
STK-02 T0=10, endpoint=11, interior missing -> R_N=0.1; path metrics UNKNOWN
STK-03 interior affine proof missing, endpoint valid -> R_N preserved
STK-04 invalid endpoint affine -> R_N null
STK-05 invalid T0 affine -> R_N null
STK-06 endpoint identity mismatch -> R_N null
STK-07 basis mismatch -> R_N null
STK-08 confirmed suspension policy vector
STK-09 corporate action valid endpoint + incomplete interior -> endpoint return valid
STK-10 corrected source -> append outcome revision; historical outcome unchanged
STK-11 relative market return preserved when endpoints valid
STK-12 gap then recovery -> no silent interpolation unless contract permits
```

成功状态：

```text
IA-01 = CANDIDATE_FIXED
```

必须证明：

```text
Endpoint strictness unchanged
Path quality no longer over-blocks endpoint
No historical rewrite
No permission change
```

# 5. IA-02｜Sector Forward Dedicated Basket Path + Field Semantics

## 5.1 问题

当前 Sector Forward 有两层问题：

1. 新 successor 的 Stock-style validator 需要 `adjustment_identity`，Sector 聚合 synthetic row 没有该身份，导致合法篮子也可能 `ADJUSTMENT_UNKNOWN`。
2. 旧实现把 basket close 同时塞进 close/high/low，并输出 `MFE_N/MAE_N`，而设计对 Sector 只允许 `MFE_CLOSE/MAE_CLOSE`。

## 5.2 修复原则

禁止 Sector basket 继续伪装成 Stock price_path row。

建议建立专用：

```text
SectorBasketForwardPath
```

或等价独立函数 / contract。

## 5.3 Basket identity

T0 冻结：

```text
sector_benchmark_id / sector_subject_id
membership snapshot
member security_ids
initial weights / fixed shares
T0 evaluation basis
member source identities
member adjustment identities
constituent policy
```

生成独立：

```text
sector_basket_identity_digest
sector_basket_source_digest
```

名称可按现有 contract 体系确定。

关键要求：

```text
basket identity != stock adjustment identity
```

不得为通过 validator 给 aggregate row 伪造 stock adjustment_identity。

## 5.4 Member valuation

每个 member 独立验证：

```text
T0 coordinate
endpoint coordinate
same evaluation basis
source identity
adjustment proof
```

再聚合 basket。

## 5.5 Missing / partial member policy

严格使用冻结 Sector benchmark / constituent policy。

禁止：

```text
删除 missing member
然后对剩余成员重新归一化
```

若设计要求 fixed initial weights / no reweight，则 missing member 按 frozen policy 形成 unknown weight/quality。

若 coverage threshold 未冻结：

```text
保持 UNKNOWN
```

不得自行拍阈值。

## 5.6 输出字段

Sector subject 只输出设计允许语义：

```text
R_N
MFE_CLOSE
MAE_CLOSE
```

不得输出由 synthetic close 伪造的：

```text
MFE_N
MAE_N
```

如共享 schema 必须存在字段，则应 `null / NOT_APPLICABLE`，按现有 schema 能力实现。

不得伪造 high/low。

## 5.7 Relative-sector 与 Sector subject 分离

必须独立验收：

```text
A. stock relative-sector return
B. Sector subject basket absolute forward
```

不得让 `n < 2` 等 Sector basket 条件错误阻断 unrelated stock relative-sector 逻辑，反之亦然。

## 5.8 Required vectors

```text
SEC-01 two members 10->11, equal weights, all valid -> Sector R_N=0.1
SEC-02 valid endpoint basket + incomplete interior -> endpoint/path分别判定
SEC-03 one member endpoint UNKNOWN -> no reweight;按 frozen policy UNKNOWN
SEC-04 member corporate action + common evaluation basis -> valid basket endpoint
SEC-05 T0 membership frozen; later enter/leave不改写
SEC-06 no synthetic stock adjustment_identity on basket row
SEC-07 Sector only MFE_CLOSE/MAE_CLOSE; no fake MFE_N/MAE_N
SEC-08 n<2 Sector basket behavior
SEC-09 stock relative-sector independent from Sector subject eligibility
SEC-10 market benchmark unaffected parity
SEC-11 accepted historical Sector outcome immutable
SEC-12 corrected/new successor output append revision
```

## 5.9 Capability boundary

当前 `PURE_CORE_STOCK` 不等于 Sector permission。

修完 IA-02 后也不能自动授予：

```text
Sector Shadow
Sector Focus
Sector Production
```

成功状态：

```text
IA-02 = CANDIDATE_FIXED
```

必须证明：

```text
dedicated basket identity
valid basket endpoint return
no hidden reweight
correct field semantics
no fake high/low
no permission expansion
```

# 6. IA-03 / IA-04 本轮只做 Regression Sentinel

不修，保持：

```text
IA-03 = OPEN_AUDIT_ONLY / P2
IA-04 = OPEN_AUDIT_ONLY / P2
```

至少记录：

```text
IA-03: PENDING -> DUE same source 当前行为
IA-04: negative actual price / invalid OHLC / terminal delist zero 当前行为
```

若 IA-01/02 修改不可避免触碰 IA-03/04 语义，应停止扩大修改，另开 successor task。

# 7. IA-05 / IA-06 本轮不关闭

## IA-05

保持 OPEN。

不得为了全仓绿而：

```text
恢复 retired hot-rank capture writer
删测试
大范围 skip
ignore collection error
```

IA-09 PASS 后仅允许安全 `pytest --collect-only` 或等价收集探针。

## IA-06

保持 OPEN。

缺 PG fixture / sklearn 不阻止 IA-01/02 代码修复，但不能把未运行写成 PASS。

# 8. 允许修改区域

预期主要：

```text
tests/upgrade_m12/*
tests/support/* or equivalent isolation support

src/workbench_analysis/v4_15_settlement_successor.py
src/workbench_analysis/v4_15_settlement.py
Sector Forward dedicated successor/helper

scripts/v4_16_settlement_worker_v2.py
仅限适配新 accepted successor contract 所需范围

对应 config successor contracts
对应 tests
对应 evidence
```

若新增 contract，必须 additive successor，禁止原地覆盖已接受 bytes。

# 9. 禁止修改

禁止：

```text
V4-00～14 business algorithms
V4-09 PREWATCH rules
A08 business semantics
FEP models / target definitions
existing accepted historical outcome values
028～033 historical FEP migrations
已接受 Shadow migrations
production route
Focus route
Default UI route
TDX source files
```

禁止：

```text
UNKNOWN -> FALSE
unavailable -> 0
missing Sector member 后重权
close -> fake high/low
放松 adjustment identity
绕过 endpoint basis check
```

# 10. Test Strategy

## Phase A Isolation
先仅跑 IA-09 isolation tests。

## Phase B IA-01
至少覆盖：

```text
Stock Forward vectors
V4-15 stock settlement
V4-16 settlement-worker stock integration
FEP label adapter readback sentinel
```

## Phase C IA-02
至少覆盖：

```text
Sector Forward vectors
Sector benchmark/subject
stock relative-sector
V4-15 settlement
V4-16 integration
```

## Phase D affected regression

```text
V4-00E adjustment consumer
V4-08 Sector/Rotation
V4-15 Radar/Cohort/Settlement
V4-16 settlement worker
FEP E1 label owner
FEP E5 canonical input boundary
```

## Phase E safe collection probe

IA-09 PASS 后允许 `pytest --collect-only`。

若 IA-05 仍存在：

```text
如实记录
不宣称全仓 green
```

# 11. Required Evidence

建议目录：

```text
reports/forward_p1_repair_r1_20261006/
```

至少：

```text
ENTRY_BASELINE.json
SOURCE_AUDIT_BINDINGS.json

IA09_TEST_ISOLATION_PROOF.json
IA09_PROTECTED_ROOT_FINGERPRINT_BEFORE.json
IA09_PROTECTED_ROOT_FINGERPRINT_AFTER.json

IA01_ENDPOINT_PATH_SEPARATION_PROOF.json
IA01_VECTOR_MATRIX.json

IA02_SECTOR_BASKET_IDENTITY_PROOF.json
IA02_FIELD_SEMANTICS_PROOF.json
IA02_VECTOR_MATRIX.json

AFFECTED_REGRESSION_SUMMARY.json
OPEN_ISSUES_PRESERVED.json
PROTECTED_STATE_READBACK.json
CHANGED_FILE_LIST.json
CANDIDATE_SEAL.json
COMPLETION_REPORT.md
```

`ENTRY_BASELINE.json` 必须 exact-bind：

```text
0c78051c570bdd68ef98f1cb9fdcfcd315759ec2
```

以及两份 Codex 审计报告的路径与 SHA。

IA-01 / IA-02 proof 必须保存 input、contract expectation、old result、new result、why-contract-matches；不能只放 pytest PASS。

IA-09 proof 必须展示实际 attempted DB/root path、guard 决策、protected root 前后指纹、disposable DB 的变化。

# 12. Regression Acceptance

本轮成功要求：

```text
IA-09 targeted = 0 failed
IA-01 targeted = 0 failed
IA-02 targeted = 0 failed
affected-stage introduced failures = 0
protected-state drift = 0
```

历史 known debt 必须显式保留，不能通过删测/改名消失。

# 13. Protected State

至少证明：

```text
V4_STAGE_ACCEPTED_HEAD unchanged
V4_DATA_ACCEPTED_HEAD unchanged
V4_15_ACCEPTED_HEAD unchanged
Current Audit Head 默认不改
runtime authorization unchanged
real shadow authorization unchanged
Production false
Focus false
Default UI false
REAL_SHADOW_OBSERVATIONS 0
PIT_OBSERVED_REAL_SAMPLES 0
FEP permissions unchanged
```

# 14. Completion Status

Codex 完成本卡后唯一允许自报：

```text
FORWARD_P1_REPAIR_R1 =
CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

IA-09 = CANDIDATE_FIXED
IA-01 = CANDIDATE_FIXED
IA-02 = CANDIDATE_FIXED
```

不得自报：

```text
V4_15_FULL_PASS
V4_16_FULL_READY
FIRST_REAL_SHADOW_AUTHORIZED
GLOBAL_PYTEST_PASS
PRODUCTION_READY
V4_22_FINAL_PASS
```

# 15. 后续批次

本卡独立验收通过后，再进入：

```text
Round 2:
IA-03
IA-04
IA-10

Round 3:
IA-05
IA-06
IA-07
IA-08
```

是否合并 Round 2/3，由本卡后的真实回归结果决定。

# 16. Task Identity

```text
TASK_ID =
V4_FORWARD_P1_REPAIR_R1_IA09_IA01_IA02

PRIORITY =
P1

BLOCKS =
V4-15 affected Forward engineering acceptance
V4-16 affected Forward capability readiness
safe full-regression audit

DOES_NOT_REOPEN =
V4-00～14 historical accepted chain
FEP historical engineering acceptance

SUCCESSOR =
INDEPENDENT_EXTERNAL_AUDIT_REQUIRED
```

**文档结束**
