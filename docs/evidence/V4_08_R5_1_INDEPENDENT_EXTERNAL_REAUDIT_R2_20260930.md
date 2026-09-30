# V4-08 R5.1 独立外部复验审计 R2｜2026-09-30

**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**审计 HEAD**：`c853f0ce1980d338d67fe0afb29d4ccaa95db648`  
**上一轮 HEAD**：`10d500ce51a9a0914c0d812c1c1fee761c5a3af9`  
**R5.1 implementation commit**：`d4d2e861bf99ef2867a6579345a156fe18b6f5b5`

## 1. 唯一总状态

```text
V4_08_R5_1_EXTERNAL_ACCEPTANCE_BLOCKED_R2
```

上一轮三个 blocker 的**算法层修复基本完成**：

```text
R5-B01 B2 semantic/rank-universe hardcoded True   PASS_CORE_LOGIC
R5-B02 raw amount adapter missing                 PASS_CORE_LOGIC
R5-B03 price-basis adapter missing                PASS_CORE_LOGIC
```

但本轮发现两个新的真实生产接线问题：

```text
R5.1-B04 DAILY_MOVING_ACCEPTED_HEAD_ROUTING_MISSING
R5.1-B05 LEGACY_VALID_MEMBER_ACCEPTED_PRODUCER_NOT_WIRED
```

因此当前仍不能授权：

```text
data/v4/V4_08_ACCEPTED_HEAD.json
accepted_stage_range = V4_00_TO_V4_08_ACCEPTED
```

---

## 2. 增量提交

相对 `10d500ce...`：

```text
ahead_by = 4
behind_by = 0
```

提交：

```text
90cef3e1  repair R5.1 semantic/raw amount/price identity wiring
9bf666fb  seal LF-stable candidate input bindings
d4d2e861  reuse accepted canonical governance head identity
c853f0ce  seal clean regression and external reaudit handoff
```

GitHub combined status 仍为空：

```text
statuses = []
```

仅记录为 CI 外部状态缺失，不单独判失败。

---

## 3. Clean regression｜PASS

clean detached checkout：

```text
698 tests
696 passed
2 skipped
0 failed
0 errors
```

并且：

```text
config/.env absent
config/.env not read
disposable PostgreSQL used
temporary cluster destroyed
git clean before/after
```

结论：`PASS`。

---

## 4. Accepted Head boundary｜PASS

最新：

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

仍然：

```text
accepted_stage_range = V4_00_TO_V4_07_ACCEPTED
```

没有提前写 V4-08 final head。

---

## 5. B2 semantic/rank-universe 核心修复｜PASS_CORE_LOGIC

上一轮错误：

```text
normal_rank_eligible = True
```

已经删除。

现在：

```text
src/sector/semantic_input_r5_1.py
src/sector/legacy_b2_r5.py
```

会依据：

```text
sector_role
sector_valid
resolve_semantics()
```

决定：

```text
normal_rank_eligible
```

并且 rank pool 只包含：

```text
normal_rank_eligible is True
AND rel1 known
```

测试覆盖：

```text
NORMAL_ATTRIBUTE
EXCLUDE_FROM_THEME_RANK
sector_valid=false
UNKNOWN_TAG
missing semantic provenance
```

还验证 excluded 高 `rel1` sector 不进入 denominator、不改变其他 normal sector 的 `p1`。

这一部分可以保留。

---

## 6. raw amount 计算逻辑｜PASS_CORE_LOGIC

新增：

```text
src/sector/accepted_input_r5_1.py
```

已经做到：

```text
top1/top3 concentration
← canonical daily raw CNY amount
```

禁止：

```text
amount_ratio20 替代
missing amount -> 0
BaoStock 替代
```

并覆盖：

```text
normal
missing
zero denominator
invalid amount
date mismatch
future source
digest mismatch
missing payload
```

算法行为正确。

---

## 7. price-basis 计算逻辑｜PASS_CORE_LOGIC

现在提取：

```text
close = qfq_ohlc[3]

price_basis_id
=
coordinate_basis
+
adjustment_snapshot_id
```

并保留：

```text
adjustment_snapshot_digest
```

V4-02 的 `adjustment_snapshot_id` 来自冻结 GBBQ snapshot identity，当前正式值为 content-addressed `sha256-*`，因此当前 exact equality gate 可以接受。

测试覆盖：

```text
same basis -> pulse can form
different snapshot -> UNKNOWN
missing basis -> UNKNOWN
future revision -> reject
logical digest mismatch -> reject
```

这一部分也可以保留。

---

# 8. Blocker R5.1-B04｜Daily moving accepted-head routing missing

R5.1 adapter 当前固定读取：

```text
data/v4/V4_02_ACCEPTED_HEAD.json
data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json
```

但真实仓库中：

```text
V4_02_ACCEPTED_HEAD.source_cutoff = 2026-09-24

V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD
first_accepted_target_trade_date = 2026-09-28
accepted_candidate = 固定 2026-09-28 artifact
```

这两个都不是每日向前移动的数据 authority。

仓库已经明确存在：

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
config/v4_data_accepted_head_v1.json
src/workbench_analysis/daily_data_head.py
```

既有架构定义：

```text
V4_STAGE_ACCEPTED_HEAD = 阶段验收基线
V4_DATA_ACCEPTED_HEAD  = 每日向前移动
V4_DEV_BASELINE_HEAD   = 开发验收冻结
```

因此 R5.1 用静态 V4-02 stage/amendment head 作为未来 daily amount/price authority，与既有 three-head architecture 不一致。

---

## 9. 为什么 TEST_ONLY fixture 没抓到 B04

fixture 会在临时目录直接创建：

```text
data/v4/V4_02_ACCEPTED_HEAD.json
data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json
```

并把目标日期数据塞进去。

这证明的是：

```text
adapter 能读“长得像 accepted head”的文件
```

不能证明：

```text
真实 V4_DATA_ACCEPTED_HEAD 前进后
adapter 会自动消费新 session
```

真实仓库里硬编码路径不会因为 Daily Data Head 推进而自动变化。

---

## 10. B04 的实际后果

即使未来：

```text
V4_DATA_ACCEPTED_HEAD -> 2026-10-xx
```

R5.1 不改代码仍会：

```text
raw amount
继续查 2026-09-24 artifact

price basis
继续查固定 2026-09-28 candidate
```

于是：

```text
top1/top3 concentration
Rotation pulse baseline
Rotation price retention
```

仍可能永久 UNKNOWN。

这不是“当前没数据”，而是：

```text
AUTHORITY ROUTING MISSING
```

结论：

```text
FAIL / BLOCKER
```

---

## 11. B04 正确修复边界

不要求重做 DM-01 或 V4-16。

只需把 adapter 改成 context-driven，例如：

```text
load_accepted_current(
  ...,
  accepted_input_context
)
```

context 显式绑定：

```text
accepted_trade_date
raw_daily path/sha/logical digest/available_at/capability
adjusted_price path/sha/logical digest/available_at/capability
governance head identity
```

未来 daily caller 从：

```text
V4_DATA_ACCEPTED_HEAD
```

解析 context。

当前 engineering replay 可继续使用：

```text
STATIC_ENGINEERING_BASELINE_CONTEXT
```

但必须明确：

```text
daily_production_authority = false
```

---

# 12. Blocker R5.1-B05｜legacy_valid_member accepted producer 未真正接入

R5.1 semantic mapping 要求：

```text
current[security_id].legacy_valid_member
```

且：

```text
quality = ACCEPTED
producer_contract = sector-factor-contract-v1.1-correctness
```

但真实 V4-03/V4-05 accepted factor contract 并没有这个字段。

V4-03 仍是正式 47 fields；
V4-04 registry 也没有 `legacy_valid_member`。

当前 `build_current()` 只是：

```text
factor row 已经带 legacy_valid_member
→ 原样搬入 current
```

它并没有生产这个事实。

---

## 13. TEST_ONLY fixture 掩盖了 B05

测试 fixture 主动向 synthetic factor row 注入：

```text
legacy_valid_member = {
  value,
  quality='ACCEPTED',
  producer_contract=VERSION
}
```

所以 parity test 可以 PASS。

但真实 accepted V4-05 artifact 没有该字段。

因此真实 pipeline 中，对非 EXCLUDE role：

```text
valid = None
sector_valid = None
normal_rank_eligible = None
```

整个 affected type rank pool 随后保持：

```text
UNKNOWN
```

这不是当前 9/30 Core 不存在才能解释的；即使未来同日 Core 到位，只要 exact producer 没接入，B2 仍不会真正启用。

---

## 14. Legacy exact producer 实际需要什么

Legacy：

```text
src/sector/phase2.py:prepare
```

定义：

```text
valid_member =
security_id 格式合法
AND missing_state 已知
AND missing_state not in {
  FILE_MISSING,
  DELISTED_OR_INACTIVE
}
```

随后：

```text
sector_valid =
phase2.validity(total, valid, role)
```

所以可以建立独立：

```text
V4_08_LEGACY_VALID_MEMBER_ADAPTER
```

从 accepted identity/lifecycle/data-availability facts 生产该布尔值；不需要把它假装成 V4-03 的第 48 个 factor。

---

## 15. B05 两种合规处理

### A｜正式接 exact producer

若 accepted facts 足够重建：

```text
phase2.prepare.valid_member
```

则直接接入。

### B｜明确降级能力

若目前不能精确生产：

```text
B2_NON_AMOUNT_A
=
NOT_IMPLEMENTED_LEGACY_VALID_MEMBER_PROVENANCE
```

并保持：

```text
confirmed_raw = UNKNOWN
```

同时：

```text
B2_AMOUNT_A = DIAGNOSTIC_AUDIT_OPEN
```

总合同 §17 已明确：

```text
legacy raw qualification 未就绪
→ NOT_IMPLEMENTED
```

不应阻塞其他独立路径。

---

## 16. 当前 capability claim 过强

`evaluate_b2()` 当前仍返回：

```text
B2_NON_AMOUNT_A = ENABLED_ENGINEERING
```

但真实 accepted chain 没有 exact valid-member producer。

所以这项声明当前属于：

```text
OVERCLAIMED
```

至少要：

```text
实现 producer
或
降级 capability
```

---

# 17. 其余项目继续 PASS

不回滚：

```text
Scoped PIT membership
exact-day/no-backdating
R5 parameter freeze
Sector Native
common-member logic
§10A0 midrank
B0
B1 Rotation
frozen basket
raw amount calculation
price-basis comparison
B2 algorithm when exact inputs exist
Amount A isolation
feedback isolation
migration 020
PostgreSQL readback
no-symbol
clean regression
global Accepted Head boundary
```

---

## 18. 当前真实 9/30 全 UNKNOWN 不构成失败

当前：

```text
B0       UNKNOWN = 378
ROTATION UNKNOWN = 378
B2       UNKNOWN = 378
```

不要通过：

```text
UNKNOWN -> FALSE
threshold relaxation
旧 R3 fallback
9/28 relabel 为 9/30
```

强行造非空信号。

---

## 19. 是否需要等待真实数据

不需要。

两个 blocker 都可以立即修：

```text
B04
→ context-driven accepted authority

B05
→ exact valid-member producer
   OR capability NOT_IMPLEMENTED
```

不需要等待 5/20 交易日、Forward outcome 或真实 Rotation Pulse。

---

## 20. 是否可以并行准备 V4-09

可以并行做：

```text
V4-09 contract
AST
parameter registry
synthetic vectors
schema candidate
```

但 V4-09 final acceptance / integrated replay 仍等待 V4-08 capability-scoped 外部结论。

---

# 21. 最终逐项判定

| 项目 | 结论 |
|---|---|
| R5-B01 semantic/rank logic | PASS_CORE_LOGIC |
| mixed-semantic parity | PASS_TEST_ONLY |
| R5-B02 raw amount calculation | PASS_CORE_LOGIC |
| R5-B03 price-basis calculation | PASS_CORE_LOGIC |
| accepted-input digest/future gates | PASS |
| Daily moving accepted authority | **FAIL** |
| V4_DATA_ACCEPTED_HEAD routing | **FAIL** |
| legacy valid-member algorithm understanding | PASS |
| legacy valid-member real producer | **FAIL** |
| B2_NON_AMOUNT_A ENABLED claim | **FAIL / OVERCLAIMED** |
| B0 | PASS |
| B1 | PASS |
| migration 020 | PASS |
| no-symbol | PASS |
| regression | PASS |
| V4-08 final head absent | PASS |

---

# 22. 唯一总裁决

```text
V4_08_R5_1_EXTERNAL_ACCEPTANCE_BLOCKED_R2
```

只剩两个 blocker：

```text
R5.1-B04
Daily accepted input authority routing

R5.1-B05
Legacy valid-member accepted producer / capability classification
```

---

# 23. 下一步

执行一轮最小：

```text
V4-08 R5.2
```

只修上述两项。

不修改：

```text
retention 参数
Sector Native 公式
B0
Rotation 状态机
§10A0 midrank
Amount A
Prior-RPS
membership
```

修完后，如果 B04 通过，且 B05 采用 A 或合规 B，可考虑：

```text
V4_08_EXTERNAL_ACCEPTANCE_PASS_ENGINEERING_SCOPE
```

并把真实 signal capability 单独标为 degraded。

**文档结束**
