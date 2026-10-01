# A10/A12-R3｜Producer Authority 与 Daily Source Instance 分层修复任务卡｜2026-10-01

**Work Package：** `WP-A10-A12-R3-PRODUCER-SOURCE-INSTANCE`  
**基线 HEAD：** `a43d663a0cc62d48f65a1160fae9c50874d86548`  
**优先级：** P0

## 1. 前置外部裁决

已接受：

```text
A12 historical Path B
2023-07-04 ~ 2026-09-24
RECONSTRUCTED_CORRECTED
TARGET_DATE_QUERYABLE_FACT
```

未接受：

```text
A12 observed-daily owner registration
DM01 final all-nine
```

原因：

```text
captured dates = [2026-09-28, 2026-09-30]
effective_scope = [2026-09-28, 2026-09-30]
A10-R2 only checks continuous start/end scope
→ 2026-09-29 may be incorrectly authorized
```

## 2. 核心抽象必须改变

禁止继续：

```text
OWNER = 某几个日期的 source response 集合
```

改为两层。

### Layer A｜Producer Authority Contract

外部接受一次：

```text
field semantics
source family
parser/schema contract
local TDX precedence
empty/malformed behavior
historical mode
temporal lineage rules
allowed consumers
```

建议：

```text
BAOSTOCK_DATED_TRADING_STATUS_PROVIDER_AUTHORITY_V4
BAOSTOCK_DATED_ISST_PROVIDER_AUTHORITY_V4
```

Producer authority 不因为新增一个交易日而重新做人为 acceptance。

### Layer B｜Source Instance

每个 target date 独立冻结：

```text
target_trade_date
provider_date
raw artifact path
raw artifact sha256
observed_at
received_at
source revision
schema contract
identity/universe binding
query status
```

Source Instance 不进入人工 external owner acceptance，但必须由机器 gate 验证。

## 3. Owner Registry 新语义

Owner Registry 注册的是 accepted producer authority contract，不是某两个日期的 response。

Owner entry 至少：

```text
owner_contract_id
field_id
producer_contract artifact/hash
external_acceptance
formal_consumer_authorization
allowed_consumers
historical_modes
source_instance_policy_id
role_binding
accepted_at
```

## 4. Source Instance Policy

新增：

```text
SOURCE_AUTHORITY_SOURCE_INSTANCE_POLICY_V1
```

验证：

```text
field_id
source_family
target_trade_date
provider_date == target_trade_date
raw artifact exists
raw sha exact
schema valid
observed_at timezone-aware
received_at >= observed_at
source revision exact
identity binding exact
universe/calendar target exact
```

没有 source：

```text
SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE
```

不能因为 owner contract 已接受而放行。

## 5. Historical delayed retrieval

若：

```text
observed_at.date > target_trade_date
```

只允许：

```text
RECONSTRUCTED_CORRECTED
TARGET_DATE_QUERYABLE_FACT
```

强制：

```text
first_available_at_target_proven = false
AS_RECORDED = false
```

## 6. Same-day flow

同日 capture 仍必须记录真实 observed/received time。

本任务不自动把 same-day observed 升级为 `AS_RECORDED`；该能力仍受 first-availability/PIT contract 控制。

## 7. 9/28 / 9/29 / 9/30 硬向量

### 2026-09-28
已有 frozen raw response：

```text
accepted producer + valid source instance → PASS
```

### 2026-09-30
已有 frozen raw response：

```text
accepted producer + valid source instance → PASS
```

### 2026-09-29
当前没有 frozen response：

```text
accepted producer + missing source instance → FAIL
SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE
```

这是 P0 核心门。

## 8. Global Gate 必须独立安全

当前 `candidate_fact()` 的 `captured_dates_only` 检查可以保留，但只能作为 defense-in-depth。

正式：

```text
Global Source Authority Gate
```

自身就必须拒绝 9/29。

任何 formal consumer 不调用 `candidate_fact()` 也不能绕过。

## 9. Historical Path B 正式化

根据外部审计，可正式生成 historical authority amendment，接受：

```text
BAOSTOCK_DATED_TRADING_STATUS_RECONSTRUCTED_V3
BAOSTOCK_DATED_ST_STATUS_RECONSTRUCTED_V3
```

历史 scope：

```text
2023-07-04 ~ 2026-09-24
TARGET_DATE_QUERYABLE_FACT
RECONSTRUCTED_CORRECTED
```

必须绑定：

```text
BaoStock official field docs
historical query receipts / revisions
bounded recovery
historical normalized source artifacts
independent full-row oracle
```

禁止把 R7 output 单独当唯一 raw trust root。

## 10. G01/G02 外部 disposition 正式化

可以将：

```text
A12_R2_INTERIOR_DATA_GAP_SCOPE
→ ACCEPTED_NEGATIVE_SCOPE_CENSUS

A12_R2_POSITIVE_ST_CODE_CHANGE_SCOPE
→ ACCEPTED_NEGATIVE_SCOPE_CENSUS
```

含义仅为：

```text
required historical scope 中不存在正例
不允许伪造
不阻塞 historical Path B
```

未来真实案例继续追加。

## 11. Governance config 版本化

新增例如：

```text
source_authority_governance_r3.json
```

不得覆盖 R2。

Role binding 指向 accepted producer contract，不指向某个日期 source file。

Source instance 通过独立 manifest/binding 输入。

## 12. Registry / Governance Head 版本化

不要覆盖：

```text
V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY.json
V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R1.json
```

建议：

```text
V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R2.json
V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R2.json
```

保留 R1 lineage。

## 13. Daily 自动化

目标：

```text
daily capture source
→ validate source instance
→ run accepted producer
```

普通每日 source revision 不需要人工 external owner acceptance。

只有：

```text
provider semantics / parser / authority policy 发生实质变化
```

才需要新 producer contract 外部接受。

## 14. DM01 接口

DM01 最终应调用：

```text
require_accepted_producer(...)
require_source_instance_for_target(...)
```

对 `TRADING_STATUS` / `ISST` 分别验证。

9/28 可形成 candidate。

9/29 当前必须 block；以后补抓 9/29 source 后，不需要新人工 owner acceptance即可继续。

## 15. Supplemental Boundary

即使 BaoStock `tradestatus/isST` 获得 field authority：

```text
BaoStock OHLC
BaoStock adjustment factor
```

仍为 supplemental/cross-check。

Canonical：

```text
TDX price/bar
GBBQ QFQ
```

不变。

## 16. Accepted Head

本任务禁止：

```text
V4_DATA_ACCEPTED_HEAD movement
V4_STAGE_ACCEPTED_HEAD movement
V4-02/04/05/07/08/09 Accepted Head overwrite
DM01 final all-nine
```

结束只允许：

```text
A10_A12_R3_PRODUCER_SOURCE_INSTANCE_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

## 17. 必测负向量

至少：

```text
valid 9/28 source → PASS
missing 9/29 source → FAIL
valid 9/30 source → PASS

wrong provider_date → FAIL
wrong source SHA → FAIL
wrong target date → FAIL
schema mismatch → FAIL
received_at < observed_at → FAIL
unbounded/ambiguous response → FAIL
empty response → UNKNOWN/BLOCK per field contract
delayed response cannot mint AS_RECORDED
consumer out of scope → FAIL
BaoStock OHLC cannot inherit status/ST authority
```

## 18. Clean Regression

复跑：

```text
A10-R2/R3
A12-R2/R3
DM01 source gate
V4-02
V4-04
V4-09
global regression
```

证明旧业务 Accepted Heads 不变、historical Path B replay 不变。

## 19. Codex 最大允许结论

```text
A10_A12_R3_PRODUCER_SOURCE_INSTANCE_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

禁止自行：

```text
A12_FULL_ACCEPTED
DM01_ACCEPTED
DATA_HEAD_PROMOTED
PRODUCTION_READY
```
