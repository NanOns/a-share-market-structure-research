# P0-1｜V4 Current Accepted Reader + No-Data 语义修复任务卡 R1｜2026-10-07

- Baseline: `411c8d35bf3e3e84c766dd3e59e2824f3cfd7d2b`
- Priority: P0
- Parent: `00_V4_PRODUCTION_CUTOVER_MASTER_R1_20261007.md`

## 1. 目标

新增一个与 `ShadowContextReader` 完全分离的：

```text
CurrentAcceptedV4Reader
```

它负责正式生产研究工作台读取“最近一次已接受 V4 状态”。

不得再让生产首页使用：

```text
accepted Shadow readback exists?
```

作为“能不能展示任何数据”的总开关。

---

## 1A. 与 V4-19 / V4-20 已接受合同的关系

本卡不得修改旧的 externally accepted v1 合同 bytes。

必须新增 successor：

```text
config/v4_20_default_ui_cutover_contract_v2.json
```

v2 只新增一个**展示级、只读** source mode：

```text
V4_ACCEPTED_RESEARCH_READONLY
```

建议解析优先级：

```text
if exact active V4-19 production_permission for required capability:
    PRODUCTION_V4_PROVISIONAL
elif exact current accepted V4 owner/data is readable:
    V4_ACCEPTED_RESEARCH_READONLY
else:
    LEGACY_PRODUCTION / NO_PERMISSION
```

其中第二分支：

```text
MUST NOT grant Focus algorithm write
MUST NOT create V4-19 permission receipt
MUST NOT count as Shadow Stable / Forward Gate / Migration Gate
MUST NOT use global V4 production label
```

必须新增 v2 contract vectors，证明 read-only display 不会提升 capability permission。

---

## 2. 当前问题

当前：

```text
ShadowContextReader._real()
```

只读取：

```text
config/v4_17_shadow_ui_source_v1.json
```

而该文件：

```text
accepted_readback = null
```

所以返回：

```text
NO_REAL_SHADOW_DATA
```

这是 Shadow 语义正确，但生产页面使用它作为总数据源是错误架构。

---

## 3. 新 authority

创建：

```text
config/v4_current_accepted_read_contract_v1.json
```

至少绑定：

```text
config/v4_current_stage_authority_v2.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_15_ACCEPTED_HEAD.json
```

以及每个生产展示组件实际读取的 accepted owner artifact。

每个 binding 必须包含：

```text
path
sha256
bytes
owner_stage
contract_id
```

不得：

```text
directory scan
mtime
latest filename
latest DB
unbound environment variable
implicit V3 fallback
```

---

## 4. Reader 输出

新增：

```text
src/workbench_service/current_v4_context.py
```

建议 API：

```python
CurrentAcceptedV4Reader.load_context()
CurrentAcceptedV4Reader.read_summary()
CurrentAcceptedV4Reader.read_radar()
CurrentAcceptedV4Reader.read_entities()
CurrentAcceptedV4Reader.read_sectors()
CurrentAcceptedV4Reader.read_forward()
CurrentAcceptedV4Reader.read_health()
```

统一 context 至少包含：

```text
source_mode = V4_ACCEPTED_RESEARCH_READONLY
namespace = V4_CURRENT_ACCEPTED
accepted_trade_date
data_head_digest
stage_head_digest
stage
stage_contract_id
source_revision
canonical_data_revision
read_contract_digest
freshness_state
```

---

## 5. Latest accepted ≠ today

如果：

```text
today > accepted_trade_date
```

不能返回：

```text
UNKNOWN
NO_DATA
BLOCKED
```

只要当前 accepted head 仍然有效，应该：

```text
status = READY_CURRENT_ACCEPTED
freshness_state = WAIT_NEXT_ACCEPTED_INPUT
last_accepted_trade_date = <accepted_trade_date>
```

页面继续显示已有 accepted 状态。

只有出现：

```text
accepted head digest mismatch
bound artifact missing
invalid lineage
current authority inconsistency
```

才允许对应 scope：

```text
BLOCKED / SOURCE_INVALID
```

---

## 6. 状态语义重构

必须新增并冻结：

```text
READY_CURRENT_ACCEPTED
WAIT_NEXT_ACCEPTED_INPUT
EMPTY_VALID
NO_ELIGIBLE_OBJECTS
PENDING
RIGHT_CENSORED
NOT_AUTHORIZED
UNKNOWN
```

要求：

### WAIT_NEXT_ACCEPTED_INPUT

用于：

```text
最新 accepted trade date 存在
但下一交易日尚无 accepted input
```

此状态**不清空当前 accepted 数据**。

### EMPTY_VALID / NO_ELIGIBLE_OBJECTS

用于：

```text
源读取正常
结果合法为 0 行
```

不能显示 UNKNOWN。

### PENDING

用于：

```text
Forward horizon 未到期
当天结果尚不可观察
```

### UNKNOWN

只允许：

```text
字段理论上应该存在
但 accepted source 无法提供或无法验证
```

---

## 7. 组件 owner inventory

必须生成机器可读：

```text
reports/v4_production_cutover_20261007/CURRENT_COMPONENT_OWNER_INVENTORY.json
```

至少对：

```text
summary / why_now
radar
stock_state
sector_state
relative_state
cohort
settlement
health
```

逐字段记录：

```text
field
owner_stage
source_artifact
field_path
availability
quality_semantics
fallback = NONE
```

不允许“先写 UI，再猜字段”。

---

## 8. 已接受数据验证

至少验证当前仓库：

```text
V4_DATA_ACCEPTED_HEAD.accepted_trade_date = 2026-09-30
```

并验证至少：

```text
RAW_DAILY row_count > 0
IDENTITY_UNIVERSE row_count > 0
ADJUSTED_DAILY row_count > 0
TRADING_STATUS row_count > 0
```

生产 reader 必须能够读出真实 known 值。

---

## 9. Shadow 保持独立

不得修改：

```text
ShadowContextReader
```

使其偷偷 fallback 到 Current Accepted。

正确关系：

```text
CurrentAcceptedV4Reader -> production workbench
ShadowContextReader -> /v4/shadow diagnostics
```

---

## 10. 测试

至少新增：

```text
test_current_reader_uses_exact_accepted_heads
test_current_reader_no_latest_discovery
test_current_reader_wait_next_input_keeps_data
test_current_reader_missing_future_date_not_unknown
test_current_reader_digest_mismatch_blocks_scope
test_current_reader_valid_empty_is_not_unknown
test_current_reader_never_falls_back_to_v3
test_shadow_reader_behavior_unchanged
```

---

## 11. 退出条件

必须满足：

```text
CURRENT_ACCEPTED_READER = PASS
LAST_ACCEPTED_STATE_READABLE = PASS
NO_NEXT_DAY_INPUT_DOES_NOT_CLEAR_STATE = PASS
SHADOW_READER_ISOLATION = PASS
```

然后进入 P0-2 / P0-3。

## 12. V4-20 v2 兼容性门

必须证明：

```text
old v1 design vectors remain semantically preserved
production_permission false + accepted V4 data present
-> V4_ACCEPTED_RESEARCH_READONLY
-> display allowed
-> writes forbidden

production_permission true
-> PRODUCTION_V4_PROVISIONAL

accepted V4 unreadable
-> LEGACY_PRODUCTION / NO_PERMISSION
```

禁止把 `V4_ACCEPTED_RESEARCH_READONLY` 计为 `PRODUCTION_V4_PROVISIONAL`。
