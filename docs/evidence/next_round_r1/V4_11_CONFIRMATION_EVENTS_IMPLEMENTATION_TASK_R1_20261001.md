# V4-11 Confirmation / Events 正式实现任务卡 R1｜2026-10-01

**基线 HEAD：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`  
**父阶段：** V4-10 已外部接受  
**Stage Entry：** 已授权、仅设计冻结，runtime 尚未实现  
**优先级：** P0 Mainline

## 1. 目标

正式实现：

```text
LEGACY_ADAPTER_V1
CONFIRMATION_DETECTOR_V1
STATE_EVENT_V1
CONFIRMATION_FACT_V1
```

但本任务结束只形成 V4-11 candidate，不做 Stage Head promotion。

## 2. Authority

必须绑定：

```text
data/v4/V4_10_ACCEPTED_HEAD.json
config/v4_11_entry_contracts_r1.json
A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

任何输入不得绕过 Accepted Head / source publication identity。

## 3. Legacy V3.3 精确提取

场景：

```text
LAUNCH_CONFIRM
RECOVERY_TURN
STRONG_PULLBACK
TREND_CONTINUE
```

从冻结源码 `today_research_scanner_v3_3.py` 精确提取：

```text
branch AST
source path/symbol/SHA
parameters
input units
input time roles
UNKNOWN semantics
output semantics
call graph
```

禁止“按理解重写等价逻辑”。

如果依赖：

```text
Final State
Focus
same-day downstream
online supplemental
future outcome
```

必须拆为纯函数；无法拆则对应场景保持 `DIAGNOSTIC_ONLY`。

## 4. 参数合同

生成：

```text
V4_11_CONFIRMATION_PARAMETER_SET_V1
V4_11_CONFIRMATION_MACHINE_AST_V1
```

所有阈值必须来自精确旧逻辑/已注册参数，禁止偷偷调参。

## 5. D0 Confirmation Detector

输入仅允许当日 cutoff 已接受事实。

输出一行/股票：

```text
security_id
trade_date
confirmation_status
matched_scenarios[]
primary_scenario
scenario_evidence[]
raw_predicates
unknown_predicates
producer_contract_id
parameter_set_id
source_publication_ids[]
input_digest
```

canonical key：

```text
(publication_id, security_id)
```

同股票多场景只一行。

## 6. UNKNOWN

任何 required fact：

```text
missing
unavailable
conflicting
unaccepted
future
```

都必须：

```text
UNKNOWN
```

禁止 fallback `0/FALSE`。

UNKNOWN 不得自动视为“不确认”。

## 7. Amount A 隔离

`AUD-AMOUNT-A-06` 尚未外部接受前：

```text
Amount-A dependent formal branch = DISABLED
```

只允许：

```text
DIAGNOSTIC / UNKNOWN
```

即使 A04 同轮执行，也不得在未经独立验收前自动启用。

## 8. D2 State Reducer 边界

V4-11 D0 只产 Confirmation Fact：

```text
不得直接修改 Final State
```

最终 CONFIRMED 必须由已接受 V4-10 D2 reducer 消费。

必须有测试证明：

```text
D0 output change
不会绕过 D2 直接写 maturity/validity/tracking
```

## 9. STATE_EVENT_V1

只在：

```text
D2 final state
+
frozen prior_session_state_head
```

之后计算。

事件：

```text
FIRST_OBSERVED
CONFIRMATION_INVALIDATED
RECONFIRMED
NEW_CONFIRMED
SCENARIO_UPGRADED
CONFIRMATION_WEAKENED
PERSISTENT_CONFIRMED
SCENARIO_CHANGED
NONE
```

禁止使用 same-day revision parent 作为前驱。

同日 r1/r2/r3：

```text
相对上一交易日首次确认
→ 始终 NEW_CONFIRMED
```

## 10. Event priority

必须符合冻结 first-true/主事件语义：

```text
FIRST_OBSERVED
CONFIRMATION_INVALIDATED
RECONFIRMED
NEW_CONFIRMED
SCENARIO_UPGRADED
CONFIRMATION_WEAKENED
PERSISTENT_CONFIRMED
SCENARIO_CHANGED
NONE
```

多事件可并存，primary_event 仅展示，不得删反证。

## 11. Scenario priority

从 legacy extraction manifest 冻结旧 V3.3 场景优先级。

禁止重新发明新的 scenario score。

## 12. Security-level dedup

必须证明：

```text
same stock + multi scenario
→ one canonical row
matched_scenarios 保留全部
primary_scenario 唯一稳定
```

## 13. Input publication contract

必须拒绝：

```text
future timestamp
same-day feedback
producer mismatch
parameter mismatch
publication mismatch
unaccepted Data Head
source publication digest mismatch
```

输入必须绑定真实：

```text
V4_DATA_ACCEPTED_HEAD_V2 / 2026-09-30
```

但 V4-11 本身不得推进 Data Head。

## 14. Persistence

若需 DB migration：

```text
先从 migration allocator 分配
历史 migration 不改
```

建议对象：

```text
confirmation_fact
state_event
publication
producer/parameter/source bindings
```

必须 support retry idempotency、consumer identity、rollback。

## 15. Golden vectors

至少覆盖 entry contract 已冻结的 19 类：

```text
NONE_TO_CONFIRMED
SEED_TO_CONFIRMED
PREWATCH_TO_CONFIRMED
PERSISTENT_CONFIRMED
SAME_DAY_R1_R2_R3_NEW_CONFIRMED
RECONFIRMED
SCENARIO_UPGRADED
SCENARIO_CHANGED_NOT_UPGRADED
CONFIRMATION_WEAKENED
HARD_INVALIDATION_WINS
REQUIRED_FACT_UNKNOWN
AMOUNT_A_DISABLED
MULTI_SCENARIO_DEDUP
PRODUCER_MISMATCH
PARAMETER_MISMATCH
PUBLICATION_MISMATCH
FUTURE_TIMESTAMP_REJECTED
SAME_DAY_FEEDBACK_REJECTED
NO_SYMBOL
```

每个向量独立 expected，不允许用 producer 输出自己生成 expected。

## 16. Full-market candidate

使用 2026-09-30 accepted Data Head 做真实全市场 candidate。

至少报告：

```text
eligible universe
confirmation rows
scenario counts
UNKNOWN counts/reasons
multi-scenario count
event counts
hard invalidation conflicts
Amount-A disabled count
```

结果数量不是验收门，不允许为“数量好看”调阈值。

## 17. Independent oracle

至少对每个 scenario 抽：

```text
positive
negative
boundary
UNKNOWN
```

直接从 source facts/AST 独立重算。

## 18. Same-day revision replay

构造/使用 r1/r2/r3 revision：

证明：

```text
prior_session_state_head 不变
NEW_CONFIRMED 不因 same-day revision 变 PERSISTENT
publication lineage 正确
```

## 19. No symbol logic

全仓扫描禁止：

```text
security_id/code/name 特判
known case hardcode
case-list decision path
```

真实案例只能做测试输入。

## 20. Clean regression

至少覆盖：

```text
V4-09
V4-10
V4-11
DM01 historical publication readback
Data Head V2
A10/A12 source authority
no-symbol
```

## 21. Accepted Head

本任务不得创建正式 `V4_11_ACCEPTED_HEAD`。

只允许：

```text
V4_11_CONFIRMATION_EVENTS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

并生成完整 handoff。

## 22. 结束

禁止：

```text
V4_STAGE_ACCEPTED_HEAD → V4-11
V4-12 implementation
production/shadow/focus enable
```
