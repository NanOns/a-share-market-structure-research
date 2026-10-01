# V4-11 R3C｜Real Full-Market D0→D2→Event Replay 任务卡｜2026-10-02

**优先级：** P0 Mainline  
**依赖：** R3A + R3B sealed candidate producer set  
**目标日期：** 2026-09-30 accepted Data Head  
**Stage Head：** KEEP until external acceptance

## 1. 目标

完成真正可审计的：

```text
accepted upstream facts
→ D0 Confirmation Fact
→ V4-10 D2 State Reducer bridge
→ STATE_EVENT_V1
```

真实全市场 replay。

## 2. D0

必须报告：

```text
eligible universe
TRUE/FALSE/UNKNOWN per scenario
overall confirmation counts
multi-scenario count
UNKNOWN reasons
diagnostic-only reasons
```

验收不要求 UNKNOWN=0。

但禁止以下 reason 继续存在：

```text
PRODUCER_NOT_IMPLEMENTED
GENERIC_COMMON_FACTS_MISSING
TEMP_STUB
FAKE_ACCEPTED
```

## 3. D2

必须消费已接受 V4-10 interface。

不得：

```text
D0直接写Final State
绕过 prior-state authenticity
裸 model_boundary
未接受 state-changing facts
```

若当前真实 D2 upstream 仍缺 accepted publication，必须建立 candidate publication，不得 synthetic 冒充。

## 4. Events

真实事件必须绑定：

```text
current D2 publication
frozen prior-session state publication
```

同日 revision：

```text
prior session predecessor invariant
NEW_CONFIRMED semantics invariant
```

## 5. Capability-Scoped Acceptance

允许最终形成：

```text
FORMAL scenario A/B
DIAGNOSTIC scenario C/D
```

前提是 scope 精确，不允许为了追求四场景全部 formal 而绕过时间边界。

## 6. Independent Oracle

至少对每个正式 scenario：

```text
1 TRUE
1 FALSE
1 boundary
1 UNKNOWN
```

若真实数据没有 TRUE，可使用 synthetic oracle 验公式，但不得伪造真实市场 TRUE。

## 7. Regression

必须完整跑：

```text
V4-09
V4-10
V4-11
R3A
R3B
DM01/Data Head
A02/A05 promoted amendment readback
no-symbol
migration registry
```

clean checkout。

## 8. 输出

至少：

```text
V4_11_R3_FULL_MARKET_SUMMARY.json
V4_11_R3_SCENARIO_CAPABILITY_MATRIX.json
V4_11_R3_D2_READBACK.json
V4_11_R3_EVENT_REPLAY.json
V4_11_R3_INDEPENDENT_ORACLE.json
V4_11_R3_CLEAN_CHECKOUT.json
V4_11_R3_EXTERNAL_REAUDIT_HANDOFF.json
```

## 9. 禁止

```text
自行创建正式 V4_11_ACCEPTED_HEAD
推进 Stage Head
实现 V4-12 runtime
production/shadow/focus enable
```

## 10. 完成状态

```text
V4_11_R3_REAL_DAG_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```
