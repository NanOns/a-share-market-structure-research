# V4 R2 批次独立外部验收审计 R2｜2026-10-02

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**上一外部审计基线：** `66ef2e342dd339cc9795c2d1fd774b8edec4c345`  
**本轮已验证 implementation commit：** `d119c0526e44a819f85b4917159d3eeb5daadf2a`  
**当前分支相对基线：** ahead 3 commits / behind 0  
**Stage Head：** `V4_00_TO_V4_10_ACCEPTED`  
**Data Head：** `2026-09-30`

---

# 1. 唯一总状态

```text
R2_BATCH_EXTERNAL_ACCEPTANCE =
PARTIAL_PASS_V4_11_REAL_INPUT_CLOSURE_REQUIRED

V4_11_R2_SEMANTIC_REPAIR =
PASS

V4_11_OVERALL =
BLOCKED_R3_TARGET_FACT_PRODUCER_AND_REAL_DAG_CLOSURE

A02_RECONSTRUCTED_RPS_PRODUCER =
KEEP_ACCEPTED_SCOPED

A02_DOWNSTREAM_AMENDMENTS_V4_05_V4_07_V4_09 =
PASS_RECONSTRUCTED_CORRECTED_SCOPE
PROMOTION_AUTHORIZED_BY_SEPARATE_TASK

A05_EXACT_CURRENT_SNAPSHOT_PRODUCER =
KEEP_ACCEPTED_SCOPED

V4_08_B2_CURRENT_SNAPSHOT_AMENDMENT =
PASS_CURRENT_SNAPSHOT_ONLY
SCOPED_PROMOTION_AUTHORIZED
NO_20260930_ADOPTION

A04_AMOUNT_A_GO_FORWARD_PRODUCER =
PASS_ENGINEERING_GO_FORWARD_SCOPE
WARMUP_CONTINUES
FORMAL_CONSUMER_DISABLED

A03 =
PASS_SCOPED_FORMALIZATION
ACCUMULATION_CONTINUES

A06 =
PASS_SCOPED_FORMALIZATION
FAIL_CLOSED_NO_TOLERANCE

A07 =
PASS_SCOPED_FORMALIZATION
PERMANENT_PRECAPTURE_LIMITATION

OWNER_REGISTRY_BOOTSTRAP =
PASS_SCOPED_INACTIVE_METADATA

HISTORICAL_READER_DI =
PASS_SCOPED_HISTORY_ONLY

V4_DATA_ACCEPTED_HEAD =
KEEP_2026_09_30

V4_STAGE_ACCEPTED_HEAD =
KEEP_V4_00_TO_V4_10_ACCEPTED

V4_12_RUNTIME_ENTRY =
NOT_AUTHORIZED_YET
```

---

# 2. Clean regression

本轮工程回执：

```text
1803 passed
2 skipped
0 failures
0 errors
new_deselects = []
```

两项 skip 均为 Windows symlink 环境限制。  
历史 migration 001–027、No-Symbol、Data Head、V4-09/V4-10 保护头均未发现本轮新增回归。

结论：

```text
ENGINEERING_REGRESSION = PASS
```

但测试通过不等价于 V4-11 业务输入闭环。

---

# 3. V4-11 R2｜AMR20 / Amount-A 语义修复

## 3.1 串线问题已修复

R1 的 P0 问题是：

```text
stock amr20_mean_prior / amount_ratio20
```

被错误绑定到：

```text
sector Amount-A / AUD-AMOUNT-A-06
```

当前 R2 已明确冻结两个 namespace：

```text
STOCK_AMOUNT_VOLUME_STATE_V1
!=
SECTOR_AMOUNT_A
```

并删除 stock confirmation 对 A04 的错误 gate。

验证结果：

```text
AUD_AMOUNT_A_06_UNKNOWN_count = 0
sector Amount-A state mutation does not change identical stock facts
```

原阈值保持：

```text
LAUNCH >= 1.20
RECOVERY >= 1.05
TREND 0.80 <= x <= 2.50
```

独立 boundary/positive/negative/UNKNOWN oracle 均通过。

裁决：

```text
V4_11_R2_AMR20_AMOUNT_A_SEMANTIC_REPAIR = PASS
```

---

# 4. V4-11 仍不能正式接受的原因

当前 2026-09-30 全市场：

```text
eligible universe = 5224
confirmation rows = 5224
UNKNOWN = 5224
```

四场景：

```text
LAUNCH_CONFIRM   TRUE 0 / FALSE 0 / UNKNOWN 5224
RECOVERY_TURN    TRUE 0 / FALSE 0 / UNKNOWN 5224
STRONG_PULLBACK  TRUE 0 / FALSE 0 / UNKNOWN 5224
TREND_CONTINUE   TRUE 0 / FALSE 0 / UNKNOWN 5224
```

这不是“市场当天刚好没有确认”。

而是 required facts 尚未形成正式 target-date accepted producer publication。

当前缺口至少包括：

```text
amr20_mean_prior
window_valid
normal_universe
liquidity20
first_day_damage
severe_drop
structure_break
extended
breakout_v3
close_above_phc20
clv
ret1
r5/r20
rps5_delta3
pullback_episode_confirmed
ma5/ma20
slope20
prior_high
trend_background
current_with_loo_breadth_support
```

其中部分事实可以直接从当前 Accepted Data Head / 已接受上游纯函数重构；因此这不是“等待未来20个交易日”的问题，而是当前工程接线未闭环。

`TREND_CONTINUE` 的 same-day LOO 仍保持：

```text
DIAGNOSTIC_ONLY
```

这是正确的 fail-closed 行为，不允许为了让结果从 UNKNOWN 变 TRUE/FALSE 而绕过时间边界。

裁决：

```text
V4_11_REAL_INPUT_CAPABILITY = BLOCKED_R3
V4_11_FORMAL_ACCEPTED_HEAD = NOT_AUTHORIZED
```

---

# 5. A02｜下游 amendment

A02 reconstructed prior-RPS producer 已有 scoped external acceptance。

本轮从独立 RPS Head 重读实际 publications 后，使用原 accepted 算法重新执行：

```text
V4-05
V4-07 Base Seed
V4-09 Stock PREWATCH
```

业务变化：

```text
V4-05 changed identities = 5222
V4-07 changed identities = 5222
V4-09 changed identities = 2811
```

Seed：

```text
old: FALSE 2443 / UNKNOWN 2779
new: FALSE 3755 / TRUE 976 / UNKNOWN 491
```

关键边界保持：

```text
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
historical_first_availability_proven = false
```

因此本轮接受的是：

```text
修正后的 reconstructed business state
```

不是：

```text
证明历史当时已经知道这些数据
```

独立 readback、算法/参数 bytes、旧 Accepted Head 保护均满足。

裁决：

```text
A02_DOWNSTREAM_AMENDMENTS =
PASS_RECONSTRUCTED_CORRECTED_SCOPE
```

允许下一张任务卡做 versioned Amendment Head promotion；禁止覆盖旧 Head。

---

# 6. A05 / V4-08 B2

A05 exact producer：

```text
trade_date = 2026-09-24
scope = CURRENT_SNAPSHOT_ONLY
AS_RECORDED = false
historical_PIT_equivalent = false
```

R3 B2 replay：

```text
sector rows = 541
FALSE = 535
TRUE = 2
UNKNOWN = 4
restored semantic known = 537
```

R1 曾错误使用 6188 inventory 作为 quote universe；R2 修复 universe；R3 补齐 10 个 zero-member sectors。版本均保留。

最重要边界：

```text
不得把 2026-09-24 snapshot 注入 2026-09-30 accepted target
```

当前正式 9/30 rotation/context 变化仍应为 0。

裁决：

```text
V4_08_B2_CURRENT_SNAPSHOT_AMENDMENT =
PASS_CURRENT_SNAPSHOT_ONLY
```

允许创建 scoped capability amendment head；不允许替换 9/30 V4-08 formal result。

---

# 7. A04 Amount-A

当前：

```text
real sectors = 378
known Amount-A rows = 0
warmup UNKNOWN = 378
accepted membership sessions = 1
missing H21 sessions = 20
historical formal capability = BLOCKED
formal consumer = disabled
```

但 producer/source-admission/arithmetic/namespace 已形成完整 engineering contract，且 stock confirmation 与 Amount-A 已验证隔离。

因此：

```text
A04_GO_FORWARD_PRODUCER =
PASS_ENGINEERING_GO_FORWARD_SCOPE
```

注意：

```text
这不是 Amount-A 正式业务消费者 PASS
也不是历史 Amount-A 被重建
也不要求等待20日才继续其他工程
```

A04 后续只需真实 forward accumulation，达到 H21 后再进行 consumer acceptance。

---

# 8. A03 / A06 / A07 / Owner / Reader

当前 formalization 与独立 readback可接受：

```text
A03    PASS_FORWARD_PIT_BUILDER_SCOPE
A06    PASS_FAIL_CLOSED_NO_TOLERANCE
A07    PASS_LINEAGE_SCOPE_WITH_PERMANENT_PRECAPTURE_LIMIT
OWNER  PASS_SCOPED_INACTIVE_METADATA
READER PASS_HISTORY_ONLY_DI_HARDENING
```

这些项目不应继续占用主线修复轮次。

下一步只需要 versioned consolidation / registry disposition，不得借此启用 production consumer。

---

# 9. 下一轮主线

下一轮必须优先解决：

```text
V4-11 required target facts
→ accepted producer publications
→ real full-market D0
→ V4-10 D2 bridge
→ real event replay
→ scenario-by-scenario capability matrix
→ V4-11 external reacceptance candidate
```

不要求：

```text
UNKNOWN = 0
```

但必须要求：

```text
UNKNOWN 不能再来自“代码没实现 producer”
```

剩余 UNKNOWN 只能来自：

```text
真实缺失
source conflict
合法 capability limitation
时间边界
未达到 episode 前置条件
明确 diagnostic-only 场景
```

---

# 10. V4-12

当前仍不授权 V4-12 runtime implementation。

原因不是等待未来样本，而是：

```text
V4-11 尚未形成可消费的真实 D0/D2/Event contract
```

这属于直接工程依赖。

当 R3 real DAG 外部验收通过后，应立即：

```text
V4-11 Accepted Head promotion
+
V4-12 Stage Entry
```

不得再等待 Forward 样本数量。

---

# 11. 本轮外部审计唯一结论

```text
R2_BATCH_EXTERNAL_ACCEPTANCE =
PARTIAL_PASS_V4_11_REAL_INPUT_CLOSURE_REQUIRED
```

主线不回滚 V4-10，不重做 V4-11 R2 semantic repair。

下一轮执行 7 张任务卡，见 `V4_NEXT_ROUND_EXECUTION_MASTER_R3_20261002.md`。
