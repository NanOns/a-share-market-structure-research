# V4-08 R5.2｜两项最终接线修复任务卡｜2026-09-30

**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**输入 HEAD**：`c853f0ce1980d338d67fe0afb29d4ccaa95db648`  
**任务性质**：R5.1 外部复验后的最终定点修复  
**禁止扩大范围**

## 0. 当前状态

```text
V4_08_R5_1_EXTERNAL_ACCEPTANCE_BLOCKED_R2
```

只修：

```text
R5.1-B04 DAILY_MOVING_ACCEPTED_HEAD_ROUTING_MISSING
R5.1-B05 LEGACY_VALID_MEMBER_ACCEPTED_PRODUCER_NOT_WIRED
```

---

## 1. 明确保留，不重做

保持不变：

```text
V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1
V4_08_ALGORITHM_PARAMETER_SET_R5
5 个 retention 参数
Sector Native 公式
common-member delta
§10A0 midrank
B0 AST/runtime
Rotation four-state logic
frozen basket semantics
raw amount calculation logic
price-basis comparison logic
B2 mixed-semantic rank algorithm
Amount A diagnostic isolation
migration 020
no-symbol guard
```

除非发现新的硬错误，否则禁止改阈值、重构状态机或重做 membership。

---

# 2. B04｜移除 static V4-02 head 硬编码

当前：

```text
src/sector/accepted_input_r5_1.py
```

内部固定读取：

```text
data/v4/V4_02_ACCEPTED_HEAD.json
data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json
```

必须改掉这种固定 production authority。

---

## 3. 尊重现有 three-head architecture

仓库已有：

```text
V4_STAGE_ACCEPTED_HEAD
= stage baseline

V4_DATA_ACCEPTED_HEAD
= daily moving data head

V4_DEV_BASELINE_HEAD
= development baseline
```

R5.2 禁止发明第四个 daily authority。

---

## 4. Adapter 改为 context-driven

建议接口：

```text
load_accepted_current(
    root,
    core_binding,
    *,
    target,
    cutoff,
    accepted_input_context
)
```

`accepted_input_context` 至少包含：

```text
context_id
accepted_trade_date

raw_daily:
  path
  sha256
  source/logical digest
  available_at
  capability
  revision semantics

adjusted_price:
  path
  sha256
  logical_digest
  available_at
  capability
  coordinate identity

governance:
  source_head_path
  source_head_digest
  parent identity
```

adapter 不得固定：

```text
具体日期
具体 V4_02 accepted-head 文件
```

---

## 5. Daily caller authority

未来 daily caller 必须能从：

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
```

或它引用的 immutable accepted publication manifest 解析 context。

如果当前 Data Head 仍只到：

```text
2026-09-24
```

而 target 是：

```text
2026-09-30
```

则正确行为：

```text
TARGET_ACCEPTED_DATA_UNAVAILABLE
```

而不是回退静态 V4-02 stage artifact。

---

## 6. Current engineering replay 允许 static context

当前 R5 stage replay 仍可传：

```text
STATIC_ENGINEERING_BASELINE_CONTEXT
```

但必须标：

```text
scope = ENGINEERING_REPLAY_ONLY
daily_production_authority = false
```

不能把它描述为未来 daily production authority。

---

## 7. 本轮不实现完整 Daily Lane

禁止扩成：

```text
DM-01 rewrite
new collector
new scheduler
V4-16 realtime pipeline
```

只做：

```text
accepted-input authority abstraction
context validation
```

---

## 8. B04 multi-context test

同一 adapter 源码必须运行：

```text
Context T
Context T+1
```

两套 binding：

```text
different target
different artifact path
different SHA
different amount
different price snapshot
```

并且：

```text
不修改固定 repository head
不覆盖 data/v4/V4_02_*.json
不修改 adapter source
```

即可得到对应结果。

---

## 9. B04 immutability test

先冻结：

```text
T result + digest
```

再改变：

```text
T+1 context/artifact
```

必须证明：

```text
T result unchanged
T digest unchanged
```

---

## 10. B04 negative vectors

至少：

```text
context.accepted_trade_date < target
→ UNKNOWN/unavailable

context.accepted_trade_date > target
→ future reject

artifact SHA mismatch
→ reject

logical digest mismatch
→ reject

capability BLOCKED
→ affected fields UNKNOWN/reject per contract
```

---

# 11. B05｜不要再假设 factor row 自带 legacy_valid_member

当前：

```text
build_current()
```

只会：

```text
if factor row has legacy_valid_member:
    copy it
```

真实 V4-03/V4-05 accepted contract 没有该字段。

必须处理这个真实 producer 缺口。

---

## 12. Exact legacy producer rule

Legacy：

```text
src/sector/phase2.py:prepare
```

核心：

```text
valid_member =
security_id matches accepted security format
AND missing_state known
AND missing_state not in {
  FILE_MISSING,
  DELISTED_OR_INACTIVE
}
```

之后：

```text
sector_valid =
phase2.validity(total, valid, role)
```

R5.2 必须选择 A 或 B。

---

# 13. 方案 A｜正式实现 accepted legacy-valid-member adapter

优先方案。

新增 contract，例如：

```text
V4_08_LEGACY_VALID_MEMBER_ADAPTER_V1
```

只消费 target-cutoff 已接受事实：

```text
security identity
lifecycle/activity state
missing/data-presence state
source availability
```

禁止消费：

```text
future state
Focus
Radar
B0/B1/B2 output
turnover supplemental
```

每 security 输出：

```text
value: true/false/null
quality
reason
producer_contract
input_digest
source_bindings
max_source_date
available_at
```

---

## 14. 禁止偷换 legacy 规则

不能直接写：

```text
PIT membership exists => true
actual_bar exists => true
research universe => true
```

除非独立证明和：

```text
phase2.prepare.valid_member
```

完全等价。

---

# 15. 方案 B｜能力正式降级

如果当前 accepted facts 不能精确重建：

```text
legacy_valid_member
```

则不要造假 producer。

正式改为：

```text
B2_NON_AMOUNT_A
=
NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE
```

同时：

```text
confirmed_raw = UNKNOWN
B2_AMOUNT_A = DIAGNOSTIC_AUDIT_OPEN
```

---

## 16. 方案 B 不阻断独立 V4-08 能力

总合同 §17 已明确：

```text
legacy qualification 未就绪
→ NOT_IMPLEMENTED
```

但以下仍独立：

```text
Sector Native
B0 sector PREWATCH raw
B1 Rotation
```

如果采用方案 B，closure 必须写清：

```text
V4-08 engineering accepted scope
EXCLUDES legacy B2 confirmed/warm capability
```

不要继续把整个阶段全局卡死。

---

## 17. 修 capability overclaim

当前：

```text
B2_NON_AMOUNT_A = ENABLED_ENGINEERING
```

如果方案 A 没真正落地：

必须删除这个声明。

Capability 必须和真实 accepted producer availability 一致。

---

# 18. B05 tests｜方案 A

必须从 producer 上游输入开始，不允许直接塞最终 boolean。

至少覆盖：

```text
valid member
FILE_MISSING
DELISTED_OR_INACTIVE
unknown missing_state
invalid security id
suspended but still valid
```

并和：

```text
phase2.prepare()
```

逐例 parity。

---

## 19. 禁止 TEST_ONLY 只注入 final boolean

以下不能再作为唯一证据：

```text
factor['legacy_valid_member'] = ...
```

TEST_ONLY fixture 应从：

```text
identity/lifecycle/missing-state facts
→ legacy valid-member adapter
→ semantic mapping
→ B2 rank universe
```

完整走一遍。

---

# 20. Formal evidence

至少输出：

```text
reports/v4_08/V4_08_R5_2_STAGE_ENTRY.md

reports/v4_08/V4_08_R5_2_ACCEPTED_CONTEXT_CONTRACT.json
reports/v4_08/V4_08_R5_2_MULTI_CONTEXT_GENERALIZATION.json
reports/v4_08/V4_08_R5_2_DAILY_HEAD_ROUTING.json
reports/v4_08/V4_08_R5_2_FROZEN_CONTEXT_IMMUTABILITY.json

reports/v4_08/V4_08_R5_2_LEGACY_VALID_MEMBER_SOURCE_DECISION.json
```

如果方案 A：

```text
reports/v4_08/V4_08_R5_2_LEGACY_VALID_MEMBER_PARITY.json
reports/v4_08/V4_08_R5_2_B2_REAL_PRODUCER_INTEGRATION.json
```

如果方案 B：

```text
reports/v4_08/V4_08_R5_2_B2_CAPABILITY_DOWNGRADE.json
```

统一还需要：

```text
reports/v4_08/V4_08_R5_2_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json
reports/v4_08/V4_08_R5_2_ISOLATED_REGRESSION.json
reports/v4_08/V4_08_R5_2_CLEAN_CHECKOUT_RECEIPT.json
reports/v4_08/V4_08_R5_2_STAGE_CANDIDATE_MANIFEST.json
reports/v4_08/V4_08_R5_2_CLOSURE.md
reports/v4_08/V4_08_R5_2_EXTERNAL_REAUDIT_HANDOFF.json
```

---

# 21. 当前真实 9/30 输出不要强行改变

如果：

```text
V4_DATA_ACCEPTED_HEAD < 2026-09-30
target Core unavailable
Prior-RPS degraded
prior PIT history insufficient
```

则：

```text
B0 UNKNOWN
Rotation UNKNOWN
B2 UNKNOWN
```

完全允许。

禁止：

```text
9/28 relabel -> 9/30
fallback
UNKNOWN -> FALSE
threshold relaxation
```

---

# 22. Regression

必须：

```text
clean detached checkout
all existing V4 required families
new multi-context tests
new producer/capability tests
no-symbol gate
disposable PostgreSQL
```

---

# 23. 不修改全局 Accepted Head

Codex 不得自行写：

```text
V4_08_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD -> V4_08
```

只提交 R5.2 candidate + evidence，等待外部审计。

---

# 24. 允许并行准备 V4-09

R5.2 修复期间可并行准备：

```text
V4-09 contract
AST
parameter registry
synthetic vectors
schema candidate
```

但：

```text
V4-09 final acceptance / integrated replay
```

仍等 V4-08 capability-scoped 外部结论。

---

# 25. Handoff 必须报告

```text
pushed HEAD

B04:
accepted_input_context contract
V4_DATA_ACCEPTED_HEAD-compatible route
multi-context no-source-edit proof
T result immutability proof

B05:
方案 A or B
if A: exact source + parity
if B: explicit capability downgrade

real 9/30 distribution
clean regression
no-symbol
global head unchanged
```

然后停止，等待独立复验。

**文档结束**
