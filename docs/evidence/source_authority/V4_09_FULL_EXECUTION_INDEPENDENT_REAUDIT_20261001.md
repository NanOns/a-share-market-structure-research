# V4-09 全链路独立复审｜2026-10-01

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**当前审计 HEAD：** `4e5284f74c5275e28d75985d1c3e60eaf96e4103`

## 总结论

需要区分两个问题。

### V4-09 正式阶段合同范围

```text
V4_09_STAGE_ENGINEERING_ACCEPTANCE = KEEP_PASS_R1_1
```

### V4-09 截至今天的全部相关 hardening

```text
V4_09_ALL_RELATED_HARDENING_CLOSED = NO
```

也就是说：

> V4-09 正式阶段并不是“只发一两张任务卡就草率 PASS”；实际上经过初始任务卡 → R1 独立阻断 → R1.1 定点修复 → 独立复验 → Accepted Head promotion。

但外部验收后记录的 N01/N02 两项非阻断 hardening 仍 OPEN，不能把 V4-09 描述为 production-ready / fully hardened。

---

# 1. V4-09 正式任务链

## 初始入场/实现任务卡

```text
docs/evidence/
V4_08_ACCEPTED_HEAD_PROMOTION_AND_V4_09_STOCK_PREWATCH_ENTRY_TASK_20260930.md
```

该任务卡包含 B1–B18。

## 第一次独立外部审计

```text
docs/evidence/
V4_08_PROMOTION_AND_V4_09_R1_INDEPENDENT_EXTERNAL_AUDIT_20260930.md
```

结论：

```text
V4_09_EXTERNAL_ACCEPTANCE_BLOCKED_R1
```

Blockers：

```text
B01 V4-08 B0 producer lineage 错绑
B02 V4-09 priority producer contract 未 enforce
B03 V4-09 artifact 可覆盖旧 T
```

## R1.1 定点修复任务卡

```text
docs/evidence/
V4_08_PROMOTION_LINEAGE_REPAIR_AND_V4_09_R1_1_PROVENANCE_IMMUTABILITY_TASK_20260930.md
```

只修 B01–B03，冻结已经通过的算法。

## R1.1 独立外部复验

```text
docs/evidence/
V4_09_R1_1_INDEPENDENT_EXTERNAL_ACCEPTANCE_FINAL_20260930.md
```

结论：

```text
V4_09_EXTERNAL_ACCEPTANCE_PASS_R1_1_ENGINEERING_SCOPE
```

## Accepted Head Promotion

```text
data/v4/V4_09_ACCEPTED_HEAD.json
```

SHA256：

```text
641ef9e2e6fe8f461a9b765262e739791a6d3fdd220b0eff7947e2690de3a87d
```

Promotion validator：

```text
reports/v4_joint/
V4_09_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json
= PASS
```

---

# 2. 初始任务卡 B1–B18 复核

| Item | 内容 | 复核 |
|---|---|---|
| B1 | V4-09 authority/scope | PASS |
| B2 | same-session Pure-Core source boundary | PASS |
| B3 | Sector/Rotation 不作为 hard gate | PASS |
| B4 | mandatory_core_quality contract | PASS |
| B5 | Kleene tri-state raw qualification | PASS |
| B6 | emergence/structure/risk axes | PASS |
| B7 | A/B/C/D priority bucket | PASS |
| B8 | 禁止 total/weighted score | PASS |
| B9 | Prior-RPS UNKNOWN 不降阈值/不 fallback | PASS |
| B10 | contract/registry/AST/vectors | PASS |
| B11 | 3pp / 10pp parameter binding | PASS |
| B12 | 5222 full-market materialization | PASS |
| B13 | migration 021 append-only/readback/rollback | PASS |
| B14 | no same-day/downstream feedback | PASS |
| B15 | NO_SYMBOL P0 | PASS |
| B16 | determinism/generalization | PASS |
| B17 | required evidence package | PASS |
| B18 | Codex 不自我 external accept | PASS |

---

# 3. 算法与真实全市场 replay

正式 replay：

```text
trade_date = 2026-09-28
row_count = 5222

TRUE    = 0
FALSE   = 2443
UNKNOWN = 2779
```

Priority：

```text
A/B/C/D = 0/0/0/0
UNKNOWN_BUCKET = 2779
NOT_ELIGIBLE = 2443
```

这个“0 TRUE”没有被人为修正。

原因仍是：

```text
V4-07 accepted Prior-RPS bootstrap UNKNOWN
```

所以 V4-09：

```text
Engineering = PASS
Real Signal Capability = DEGRADED
```

不是算法通过就假称真实信号已完整可用。

---

# 4. R1 三个 blocker 修复状态

## B01 V4-08 B0 producer lineage

```text
PASS
```

旧错误 Accepted Head 保留，新建 amended head，并由 Global Stage 使用 amended binding。

## B02 Priority producer contract

```text
PASS
```

三项 state：

```text
compression_state
ma_structure_state
core_extension_risk
```

均校验 producer contract + parameter set。

15 个负向 vectors PASS。

## B03 immutable artifact

```text
PASS
```

正式 artifact 改为：

```text
V4_09_STOCK_PREWATCH_<trade_date>_<logical_digest>.jsonl.gz
```

并验证：

```text
T
T+1
same-day revision
idempotent retry
conflicting payload reject
```

---

# 5. 测试/数据库/治理

R1.1 clean detached：

```text
912 tests
910 passed
2 skipped
0 failed
0 errors
```

Migration 021：

```text
5222 exact readback
same publication retry
revision append
UPDATE/DELETE reject
rollback
```

PASS。

NO_SYMBOL：

```text
hard_gated_equity_symbol_hits = 0
unclassified_paths = []
```

PASS。

Promotion validation 全项 true。

---

# 6. 为什么仍不能说“V4-09 所有问题完全关闭”

外部验收 §19 明确留下两个非阻断 hardening：

## N01

```text
AUD-V4-09-REPAIR-FREEZE-SELF-VALIDATION-N01
```

目标：

```text
repair.status
repair.authority
exact binding set
consumer identity
```

当前：

```text
OPEN
```

已转成：

```text
WP-A08-V4-09-N01
```

目前只有 implementation entry，尚无 repair closure / external acceptance。

## N02

```text
AUD-V4-09-DB-CONSUMER-IDENTITY-N02
```

目标：

```text
migration 021
explicit consumer_contract_id governance
```

当前：

```text
OPEN
```

已转成：

```text
WP-A09-V4-09-N02
```

同样尚未完成。

---

# 7. 最终状态矩阵

```text
V4_09_CORE_CONTRACT_EXECUTION = PASS
V4_09_R1_1_EXTERNAL_ACCEPTANCE = PASS
V4_09_ACCEPTED_HEAD_PROMOTION = PASS

V4_09_PRODUCTION_PERMISSION = FALSE
V4_09_SHADOW_PERMISSION = FALSE
V4_09_REAL_SIGNAL_CAPABILITY = DEGRADED

V4_09_N01 = OPEN
V4_09_N02 = OPEN
```

因此正确表达是：

> V4-09 的正式 engineering stage 已完成并验收通过；不能重开核心阶段，也不需要重做 B1–B18。  
> 但 Production/Shadow 前的 N01/N02 hardening 仍需执行，不能说“阶段09相关工作全部 100% 关闭”。
