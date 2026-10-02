# V4 R3 批次独立外部验收审计 R1｜2026-10-02

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计远端 HEAD：** `65774de20108beafaa15c0b557b4cd2ee58edb29`  
**本轮 tested implementation：** `d1d87cabf7276bcac0a1c3f4b2ef08ac16d43649`  
**上一轮基线：** `d119c0526e44a819f85b4917159d3eeb5daadf2a`  
**Stage Head：** KEEP `V4_00_TO_V4_10_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`

---

# 1. 唯一总裁决

```text
V4_R3_EXTERNAL_ACCEPTANCE = BLOCKED_R4

PRIMARY_BLOCKER =
V4_11_ADJUSTMENT_BASIS_IDENTITY_MISMATCH

V4_11_R3A_TARGET_FACT_PRODUCERS =
BLOCKED_P0_ADJUSTMENT_BASIS_REBIND_REQUIRED

V4_11_R3B_EPISODE_SAFETY_LOO =
PASS_CAPABILITY_SCOPED

V4_11_R3C_REAL_DAG =
BLOCKED_BY_R3A_SOURCE_SEMANTICS

A02_SCOPED_AMENDMENT_PROMOTIONS =
PASS_KEEP

A05_V4_08_B2_SCOPED_AMENDMENT =
PASS_KEEP

A04_GO_FORWARD_PRODUCER_SCOPED_ACCEPTANCE =
PASS_KEEP

A03_A06_A07_OWNER_READER_CONSOLIDATION =
PASS_KEEP

V4_11_ACCEPTED_HEAD =
NOT_AUTHORIZED

V4_12_RUNTIME =
NOT_AUTHORIZED
```

---

# 2. 本轮实质进展

R3 已经把上一轮 2026-09-30 的：

```text
5224 / 5224 全 UNKNOWN
```

推进到：

```text
D0 overall:
TRUE     = 52
FALSE    = 1720
UNKNOWN  = 3452
```

场景：

```text
LAUNCH_CONFIRM:
TRUE 42 / FALSE 1730 / UNKNOWN 3452

RECOVERY_TURN:
TRUE 14 / FALSE 1758 / UNKNOWN 3452

STRONG_PULLBACK:
UNKNOWN 5224 / DIAGNOSTIC_ONLY

TREND_CONTINUE:
UNKNOWN 5224 / DIAGNOSTIC_ONLY
```

R3 没有为了减少 UNKNOWN 强行把 Pullback/Trend 升级成 formal，这一点正确。

R3B 对 episode/safety/LOO 的 capability scoping 可保留。

---

# 3. Clean regression

本轮 clean checkout 自报：

```text
2005 passed
2 skipped
0 failures
0 errors
no new deselections
```

两项 skip 为既有 Windows symlink 环境限制。

当前 GitHub：

```text
combined statuses = []
workflow runs = []
```

因此 clean receipt 可作为仓库证据，但不存在额外 CI 独立背书。

测试通过不覆盖本轮发现的 source semantic contract mismatch。

---

# 4. P0｜R3 把 adjustment basis identity 接错

## 4.1 已接受 V4-03 的正式语义

已经外部接受的 V4-03 Stock Core / Relative RPS runtime 使用：

```text
price_basis
+
adjustment_source_revision
```

作为 adjusted-price 可比身份。

真实 accepted producer：

```text
scripts/run_v4_03_full_scope_candidate.py
```

读取：

```text
qfq_open
qfq_high
qfq_low
qfq_close
price_basis
adjustment_source_revision
adjusted_quality
```

并构造：

```python
basis = f"{price_basis}:{adjustment_source_revision}"
```

技术窗口 / session return 在：

```text
basis identity 相同
```

时允许比较；不同则：

```text
MIXED_ADJUSTMENT_IDENTITY
```

V4-03 golden vectors 也明确包含：

```text
adjustment_basis_mismatch
→ UNKNOWN
```

因此正式规则是：

> 同一可比较 adjusted-price basis / source revision，不能混 basis。

它不是：

> 每一天的 qfq affine 数值系数必须与目标日字面相同。

---

# 5. R3A 当前错误实现

当前：

```text
scripts/build_v4_11_target_facts_r3a.py
```

历史数据读取了：

```text
qfq_mul
qfq_add
adjustment_source_revision
```

但实际 admission 使用的是：

```python
target_coordinate = [target.qfq_mul, target.qfq_add]
row_coordinate    = [row.qfq_mul, row.qfq_add]

ready =
row.quality == READY
and target_coordinate == row_coordinate
```

合同甚至冻结为：

```text
TARGET_AFFINE_IDENTITY_MUST_MATCH_EVERY_PRICE_SLOT
```

同时它没有把正式：

```text
price_basis + adjustment_source_revision
```

作为 V4-03 adjustment basis identity。

这改变了已接受合同的语义。

---

# 6. 上游并不缺正式 basis 字段

当前 DM-01 `ADJUSTED_DAILY` producer 已经明确输出：

```text
price_basis = TDX_NATIVE_AFFINE_QFQ
adjustment_source_revision = accepted GBBQ source SHA
qfq_mul
qfq_add
```

也就是说：

```text
price_basis
adjustment_source_revision
```

已经存在于正式上游。

R3 不需要、也不应自行用：

```text
digest(qfq_mul, qfq_add)
```

重新发明 adjustment identity。

`qfq_mul/qfq_add` 是具体 affine transform 参数，可以作为计算/审计证据；它们不等价于已经接受的 `adjustment_basis_id` 合同身份。

---

# 7. 当前错误已经实质污染 UNKNOWN

R3A 当前大量 UNKNOWN 原因集中为：

```text
MISSING_OR_MIXED_COORDINATE_MASTER_SESSION
```

例如 2026-09-30：

```text
break_high20:
known 4650 / unknown 574

rps20:
known 4650 / unknown 574

extended_v3:
known ~1780 / unknown ~3444

structure_break_v3:
known ~1780 / unknown ~3444

ma20_nondeclining_3:
known ~1775 / unknown ~3449
```

而已经接受的 V4-03 在 2026-09-24 的同类正式技术窗口覆盖为：

```text
ma20:
OBSERVED 5036 / UNKNOWN 186

ma60:
OBSERVED 5023 / UNKNOWN 199

rps20:
OBSERVED 5022 / UNKNOWN 200
```

日期不同本身不能要求数量相同，但结合代码可确认：

> R3 新增了一层未授权的 qfq coefficient equality gate。

因此当前 3000+ mixed-coordinate UNKNOWN 不能被直接当作合法市场/数据 UNKNOWN 接受。

---

# 8. R3C 受级联污染

R3C D2 当前：

```text
final_eligibility:
TRUE    = 170
FALSE   = 1195
UNKNOWN = 3859

state_freshness:
FRESH = 1365
STALE = 3859
```

这些结果消费 R3A target facts。

在 R3A adjustment-basis gate 修正并重放之前，不能判断其中：

```text
多少 UNKNOWN / STALE 是合法能力边界
多少是错误 admission 造成
```

所以：

```text
V4_11_R3C_REAL_DAG = BLOCKED_BY_R3A
```

不是要求 D2 UNKNOWN 清零，而是要求 UNKNOWN 来源真实。

---

# 9. Event Engine 审计

R3 内部 code review 曾发现：

```text
stale / UNKNOWN prior
可能被错误当作 false
从而产生伪 NEW_CONFIRMED
```

当前已修复为：

```text
current + prior freshness / validity / eligibility
共同参与 event-quality gate
```

并保留：

```text
UNKNOWN_PRIOR_D2_REQUIRED_FACTS
```

这一修复方向通过。

当前 9/30 event evidence 使用：

```text
reconstructed 2026-09-29 prior candidate
AS_RECORDED = false
LEFT_CENSORED
```

因此它可以用于：

```text
engineering replay
```

但不能证明：

```text
2026-09-29 当时已经冻结并发布该 prior
```

这属于 capability limitation，不要求等待未来20天才能继续工程。

未来 V4-11 若通过，必须把 real event evidence 明确标为：

```text
RECONSTRUCTED_LEFT_CENSORED
NOT_AS_RECORDED_FORWARD_EVIDENCE
```

而不是阻塞全部 Stage。

---

# 10. R3B 裁决

当前 capability matrix：

```text
LAUNCH_CONFIRM   = FORMAL_CANDIDATE
RECOVERY_TURN    = FORMAL_CANDIDATE
STRONG_PULLBACK  = DIAGNOSTIC_ONLY
TREND_CONTINUE   = DIAGNOSTIC_ONLY
```

Pullback 的 frozen prior episode 尚不可证明，Trend 的 same-day LOO formal role 尚未被安全接受。

当前保持 diagnostic-only 是正确行为。

裁决：

```text
V4_11_R3B = PASS_CAPABILITY_SCOPED
```

R4 不允许为了“凑齐四个场景”绕过时间边界。

---

# 11. 并行包裁决

## A02

已创建 versioned：

```text
V4_05_ACCEPTED_HEAD_AMENDMENT_A02_R1
V4_07_ACCEPTED_HEAD_AMENDMENT_A02_R1
V4_09_ACCEPTED_HEAD_AMENDMENT_A02_R1
```

继续明确：

```text
RECONSTRUCTED_CORRECTED
AS_RECORDED = false
historical first availability = not proven
```

裁决：

```text
PASS_KEEP
```

## A05

V4-08 B2 amendment 保持：

```text
2026-09-24
CURRENT_SNAPSHOT_ONLY
```

没有注入 9/30。

裁决：

```text
PASS_KEEP
```

## A04

只接受：

```text
go-forward producer capability
```

仍：

```text
formal consumer disabled
H21 warmup continues
historical formal capability blocked
```

裁决：

```text
PASS_KEEP
```

## A03/A06/A07/Owner/Reader

scoped consolidation 边界保持正确：

```text
A03 accumulation continues
A06 fail-closed
A07 permanent pre-capture limitation
Owner inactive metadata
Reader history-only
```

裁决：

```text
PASS_KEEP
```

这些项目下一轮不得重复返工。

---

# 12. 下一轮唯一主线

下一轮只做两张主线卡：

```text
R4A
Adjustment Basis Identity Rebinding
+ V4-03 9/24 exact parity proof

R4B
9/29 + 9/30 real D0/D2/Event rebuild
+ residual UNKNOWN attribution
+ V4-11 external acceptance handoff
```

R4A 必须先 PASS，R4B 才能最终封存。

---

# 13. V4-11 / V4-12

当前：

```text
V4_11_ACCEPTED_HEAD = NOT_AUTHORIZED
V4_STAGE_ACCEPTED_HEAD = KEEP V4_00_TO_V4_10_ACCEPTED
V4_DATA_ACCEPTED_HEAD = KEEP 2026-09-30
V4_12_RUNTIME = NOT_AUTHORIZED
```

R4 外部验收通过以后，再单独执行：

```text
V4-11 Accepted Head Promotion
→ Stage Head to V4-11
→ V4-12 Stage Entry
```

不需要等待 A03/A04 的未来样本积累。

---

# 14. 最终结论

```text
V4_R3_EXTERNAL_ACCEPTANCE = BLOCKED_R4

BLOCKER =
R3 adjustment basis identity
does not match accepted V4-03 semantics

NO_REOPEN:
V4-10
A02 promotion
A05 scoped amendment
A04 producer scoped acceptance
A03/A06/A07/Owner/Reader consolidation
R3B capability scoping
```
