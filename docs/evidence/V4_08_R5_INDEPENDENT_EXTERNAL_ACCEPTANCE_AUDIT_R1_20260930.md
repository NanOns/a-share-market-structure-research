# V4-08 R5 独立外部验收审计 R1｜2026-09-30

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**审计 HEAD**：`10d500ce51a9a0914c0d812c1c1fee761c5a3af9`  
**R5 实现提交**：`3adf4378a1dfa5e6eea60c2efb6e7e913db1cec1`  
**上一轮已审计 HEAD**：`75767711835207109927f2babfb547415f89d3fb`  
**权威合同**：`docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md`

## 1. 唯一总状态

```text
V4_08_R5_EXTERNAL_ACCEPTANCE_BLOCKED_R1
```

阻断原因限定为：

```text
B2_SEMANTIC_PROVENANCE_AND_RANK_UNIVERSE_MISMATCH
SECTOR_NATIVE_RAW_AMOUNT_ACCEPTED_INPUT_WIRING_MISSING
ROTATION_PRICE_BASIS_ACCEPTED_INPUT_WIRING_MISSING
```

既有结果保持有效：

```text
V4_08_R4_1_GOVERNANCE_EXTERNAL_ACCEPTANCE_PASS
V4_08_PIT_MEMBERSHIP_BASELINE_EXTERNAL_ACCEPTANCE_PASS_R1
```

R5 子项判定：

```text
PIT scoped accepted-head promotion                         PASS
R5 parameter-set engineering freeze                       PASS
Sector Native pure calculation primitives                 PASS_WITH_INPUT_WIRING_REPAIR_REQUIRED
B0 AST/runtime parameter binding                           PASS
B1 Rotation state semantics / 4-state handling             PASS_WITH_PRICE_INPUT_WIRING_REPAIR_REQUIRED
B2 source SHA / parameter SHA / AST digest binding         PASS
B2 exact legacy semantic/rank-universe reproduction        FAIL
Migration 020 / append-only persistence / readback         PASS
NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC                           PASS
Clean detached checkout regression                         PASS
Same-session 2026-09-30 Core absence fail-closed           PASS
```

当前不得创建或授权：

```text
data/v4/V4_08_ACCEPTED_HEAD.json
accepted_stage_range = V4_00_TO_V4_08_ACCEPTED
```

全局 stage head 继续：

```text
V4_00_TO_V4_07_ACCEPTED
```

## 2. 本轮增量提交

上一轮 `75767711835207109927f2babfb547415f89d3fb` 到当前
`10d500ce51a9a0914c0d812c1c1fee761c5a3af9`，ahead 7 commits。

主要实现提交依次处理：

1. R5 PIT sector primitives / rotation candidate runtime
2. frozen basket price basis / publication identity
3. 无 accepted target Core 时保持 UNKNOWN
4. B2 parameter bytes / deterministic materialization
5. field producer / time-role registration
6. §10A0 midrank / legacy rank provenance isolation
7. evidence / handoff seal

GitHub combined commit status 当前为空：

```text
statuses = []
```

记录为 CI 外部状态缺失，不单独构成失败。

## 3. Scoped PIT Membership Promotion｜PASS

新增：

```text
data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json
```

scope 正确限定为：

```text
FORWARD_PIT_MEMBERSHIP_ONLY
```

并明确：

```text
does_not_grant_sector_algorithm_acceptance = true
does_not_grant_rotation_production_permission = true
```

正式首日：

```text
2026-09-30
```

正式 rows：

```text
INDUSTRY = 5,224
THEME    = 44,938
TOTAL    = 50,162
```

结论：`PASS`。

## 4. Same-session 输入纪律｜PASS

当前 accepted Core / Seed 仍属于 `2026-09-28`，PIT membership target 为
`2026-09-30`。R5 没有把 9/28 Core 伪装成 9/30。

正式 evidence：

```text
target_accepted_core_count = 0
stale_core_relabelled = false
```

2026-09-30 工程物化：

```text
SECTOR_NATIVE rows = 378
B0 rows            = 378
ROTATION rows      = 378
B2 rows            = 378
```

状态：

```text
B0       UNKNOWN = 378
ROTATION UNKNOWN = 378
B2       UNKNOWN = 378
```

主要理由：

```text
NO_TARGET_ACCEPTED_CORE_FACTS
NO_PRIOR_ACCEPTED_PIT_HISTORY
DEGRADED_BY_UPSTREAM_BASE_SEED_SIGNAL
```

这是正确 fail-closed。结论：`PASS`。

## 5. R5 Retention 参数冻结｜工程 PASS

新参数集：

```text
config/v4_08_algorithm_parameter_set_r5.json
```

parameter_set_id：

```text
V4_08_ALGORITHM_PARAMETER_SET_R5
```

SHA256：

```text
0204d7c4fadf86871b6a079f755593b1a3f8ad18bb718f73ba33db0b70f67548
```

五个原 null 参数：

```text
V4_08_EARLY_SEED_RETENTION_MIN      = 0.6666666666666666
V4_08_EARLY_BREADTH_RETENTION_MIN   = 0.6
V4_08_EARLY_BREADTH_DELTA_MIN       = 0
V4_08_EARLY_TOP1_CONCENTRATION_MAX  = 0.3333333333333333
V4_08_MATURE_STRONG_RETENTION_MIN    = 0.75
```

参数决策包声明：

```text
future_outcome_data_used = false
market_candidate_counts_used_for_selection = false
```

并具备 monotonicity、sensitivity probes、parameter mutation、digest binding，未见 runtime literal fallback。

这些值只认可为：

```text
engineering-frozen candidate
```

不是最佳阈值或 production-supported 参数。

结论：

```text
PASS_ENGINEERING_PARAMETER_FREEZE
```

## 6. Sector Native 核心纯函数｜主体 PASS

`src/sector/native_r5.py` 已正确实现：

- PIT formal membership；
- 不用 CURRENT_MEMBERSHIP_REPLAY 代 prior；
- common-member delta 使用 `M_t ∩ M_(t-k)`；
- entered/exited 单独记录；
- UNKNOWN denominator 不删成员；
- no prior PIT -> UNKNOWN；
- strong retention 空分母 -> NOT_APPLICABLE；
- Seed dependent fields 在 Prior-RPS degraded 时 -> UNKNOWN；
- §10A0 0–100 midrank；
- ranking pool 按 type/member/coverage；
- producer/time_role 绑定 registry。

这些部分可以保留。

## 7. Blocker R5-B02｜Sector Native 缺 raw amount accepted-input 接线

合同 §15：

```text
top1/top3_concentration
=
同日可评估成员金额份额
```

要求 raw CNY amount。

`native_r5.py` synthetic runtime 也读取字段 `amount`。

但真正 accepted-input adapter：

```text
scripts/materialize_v4_08_r5.py
```

构造 `current` 时只从 V4-05 accepted full_scope_factors 复制 `row["fields"]`，
随后从 Core Profile 只补：

```text
close
close_minus_ma20
```

没有补：

```text
amount
```

V4-03 47-field registry 有 `amount_ratio20`，没有 raw `amount`，两者不能替代。

Raw amount 实际应来自 accepted canonical daily / V4-02 facts。

因此即使未来 9/30 accepted Core 到位：

```text
top1_concentration
top3_concentration
```

仍会因为 adapter 没有 `amount` 而 UNKNOWN。

这不是样本不足，而是 `ACCEPTED_INPUT_WIRING_MISSING`。

它继续影响：

```text
early_retained
diffusion
ROTATION_ACCEPTED
ROTATION_EXPANDING
```

结论：`FAIL / BLOCKER`。

## 8. Blocker R5-B03｜Rotation price_basis_id 未接入真实 accepted input

`src/sector/rotation_r5.py` 要求每个成员有 `price_basis_id`，用于保证 pulse 前基准、
pulse 日及后续路径处于同一可比较调整坐标；missing/mixed basis -> UNKNOWN，这个设计正确。

但：

```text
scripts/materialize_v4_08_r5.py
```

构建真实 `current` 时没有写入 `price_basis_id`。

现有 synthetic test 能过，是因为测试手工构造：

```text
price_basis_id = ACCEPTED_SYNTHETIC_COMMON_COORDINATE
```

这只证明 evaluator 会处理字段，不能证明真实 accepted-input adapter 已接线。

上游已有正式价格 identity：

- V4-03 `Bar.adjustment_basis_id`；
- canonical daily 的 `price_basis + adjustment_source_revision`；
- 已有 replay 中 `T0_CURRENT_COORDINATE:<gbbq_snapshot_identity>` 的 identity。

R5 应复用已接受 lineage，不应发明无来源常量。

当前缺口意味着，即使下一交易日具备真实 Core/B0 pulse，真实 Rotation 仍可能因为
`price_basis_id` 缺失而不能创建有效 pulse price path。

结论：`FAIL / BLOCKER`。

## 9. Pulse basket 使用 prior_members｜PASS

审计中检查了 `advance_rotation()` 冻结 `prior_members` 的做法。

最新版合同 §49A.3 明确：

```text
Rotation 的 pulse 篮子为 Pulse 日前已知成员
```

所以此处正确，不是 blocker。

## 10. B0 Runtime / AST｜PASS

B0 已做到：

- 从 R5 parameter instance 取阈值；
- digest fail-closed；
- parameter perturbation 改变 predicate；
- required input 缺失传播 UNKNOWN；
- 无 same-day C/D feedback；
- 无阈值 literal fallback。

2026-09-30 因历史/Seed/Core不足而 UNKNOWN 是正确结果。

## 11. B1 Rotation 四态与冻结路径｜语义 PASS

R5 正确保留：

```text
TRUE
FALSE
UNKNOWN
NOT_APPLICABLE
```

并处理：

- strong_prev=0 -> mature N/A；
- early IN/ACCEPTED 不被 mature N/A 毒化；
- frozen denominator 不删除 UNKNOWN；
- accepted prior publication；
- session age；
- OUT/FAILED；
- mixed price basis -> UNKNOWN；
- future feedback isolation。

结论：

```text
PASS_CORE_LOGIC
BLOCKED_REAL_INPUT_INTEGRATION
```

## 12. B2 Source / AST binding｜部分 PASS

当前 B2 已做到：

- exact source path；
- source SHA；
- source parameter SHA；
- R5 parameter SHA；
- AST digest；
- independent predicate vectors；
- Amount A branch diagnostic；
- warm_raw 不冒充正式；
- q20/dq5_3 未偷换；
- source bytes mutation fail-closed。

这些可以保留。

## 13. Blocker R5-B01｜B2 normal_rank_eligible 被硬编码 True

Legacy source：

```text
src/workbench_analysis/sector_attention.py
```

通过：

```text
_sector_semantics(...)
→ src/workbench_service/semantic.py
→ resolve_semantics(...)
```

生成 `normal_rank_eligible`。

它还依赖：

```text
semantic_bucket
sector_role
sector_valid
```

其中 `EXCLUDE_FROM_THEME_RANK` 会禁止进入正常横截面排名。

现有配置明确存在：

```text
ST板块
含H股
含B股
通达信88
次新股
含可转债
```

R5 PIT membership 只排除 STYLE/UNKNOWN，没有证明所有剩余 INDUSTRY/THEME 均
`normal_rank_eligible=true`。

更关键的是，R5 extraction report 自己把 `normal_rank_eligible` 列为 legacy input dependency，
但：

```text
src/sector/legacy_b2_r5.py
build_b2_inputs()
```

当前直接写：

```text
normal_rank_eligible = True
```

这违反 exact legacy adapter。

## 14. 该错误会改变 p1，不只是 provenance

Legacy `build_sector_current`：

```text
normal_mask = normal_rank_eligible
valid_mask  = normal_mask AND finite(rel1)
total_normal = count(normal_mask)
valid_count  = count(valid_mask)
```

仅对 `valid_mask` 排 `p1`。

R5 当前因为全部常量 True，实质变成对所有 rel1-known INDUSTRY/THEME 排名，会改变：

```text
type_cross_section_coverage
p1 denominator
p1 percentile
confirmed_raw
```

所以属于算法结果错误风险。

## 15. 为什么现有 golden 没抓住

当前 `test_actual_legacy_current_function_against_pit_adapter` 的 synthetic sector 全是：

```text
sector_type = INDUSTRY
semantic_bucket = NORMAL_ATTRIBUTE
sector_valid = True
sector_name = GENERIC INDUSTRY
```

样本天然全 eligible，无法覆盖：

```text
EXCLUDE_FROM_THEME_RANK
sector_valid=false
semantic unknown
normal/excluded mixed denominator
```

因此 golden PASS 不能证明 exact rank universe。

结论：`FAIL / BLOCKER`。

## 16. B2 正确修复边界

不要求重写 B2。

只修 `normal_rank_eligible provenance`，并将：

```text
config/sector_semantics.yaml
config/sector_roles.yaml
src/workbench_service/semantic.py
src/sector/roles.py
```

纳入 exact adapter binding。

若某 legacy `sector_valid` / semantic 输入无法从 accepted V4 facts 精确构造：

```text
normal_rank_eligible = UNKNOWN
B2 affected branch = UNKNOWN / DIAGNOSTIC
```

不能继续默认 True。

## 17. Migration 020 / PostgreSQL｜PASS

Migration：

```text
020_v4_08_sector_rotation_r5.sql
```

在 disposable PostgreSQL 18.6 验证：

```text
R5 append-only publication = PASS
R5 append-only results = PASS
exact readback rows = 1512
```

即 `378 × 4` namespaces。旧 membership integrity guard 仍通过。

## 18. Clean Regression｜PASS

测试 implementation commit：

```text
3adf4378a1dfa5e6eea60c2efb6e7e913db1cec1
```

最新 `10d500ce...` 仅增加 evidence/closure。

Clean checkout：

```text
git clean before = true
git clean after = true
config/.env present = false
config/.env read = false
temporary PostgreSQL cluster destroyed = true
```

测试：

```text
677 total
675 passed
2 skipped
0 failed
0 errors
```

## 19. NO_SYMBOL governance｜PASS

R4.1 永久 P0 继续有效：

```text
hard-gated equity symbol hits = 0
unclassified paths = []
```

未发现重新引入个股特判。

## 20. Accepted Head 边界｜PASS

最新 global head 仍：

```text
accepted_stage_range = V4_00_TO_V4_07_ACCEPTED
```

没有提前写 final V4-08 Accepted Head，正确。

其中旧文字：

```text
v4_08_production_status
v4_08_sector_entry
```

仍停留在 membership baseline 之前，已陈旧，但不建议现在为文案单独改 pointer。
待 R5.1 外部验收后随 V4-08 promotion 一次更新。

## 21. Prior-RPS / Amount A / Target Core 的定位

以下仍 OPEN：

```text
V4-07 Prior-RPS accepted-input bootstrap
AUD-AMOUNT-A-06
2026-09-30 target accepted Core availability
```

这些属于真实 signal capability degradation，不是三个工程 blocker 的替代解释。

正确区分：

### 合理 UNKNOWN

```text
没有同日 accepted Core
没有 prior accepted PIT
Prior-RPS 未恢复
Amount A 未关闭
```

### 必须现在修的永久工程缺口

```text
adapter 没有 raw amount
adapter 没有 price_basis_id
B2 semantic eligibility 写死 True
```

## 22. 逐项判定

| 项目 | 结论 |
|---|---|
| Scoped PIT membership promotion | PASS |
| First accepted PIT date 2026-09-30 | PASS |
| No stale 9/28 Core relabel | PASS |
| R5 parameter freeze | PASS_ENGINEERING |
| Parameter digest / perturbation | PASS |
| Sector Native common-member logic | PASS |
| §10A0 sector midrank | PASS |
| Raw amount accepted-input adapter | **FAIL** |
| B0 evaluator | PASS |
| B1 four-state semantics | PASS |
| Rotation prior-member pulse basket | PASS |
| Rotation real price-basis adapter | **FAIL** |
| B2 source/parameter/AST digest binding | PASS |
| B2 Amount A isolation | PASS |
| B2 normal_rank_eligible provenance | **FAIL** |
| B2 exact p1 rank universe | **FAIL（同一根因）** |
| Feedback isolation | PASS |
| Migration 020 | PASS |
| PostgreSQL exact readback | PASS |
| No-symbol P0 | PASS |
| Clean regression | PASS |
| Final V4-08 Accepted Head | correctly absent |

## 23. 外部验收总裁决

```text
V4_08_R5_EXTERNAL_ACCEPTANCE_BLOCKED_R1
```

只阻断：

```text
R5-B01 B2 semantic/rank-universe provenance
R5-B02 Sector Native raw amount accepted-input wiring
R5-B03 Rotation price-basis accepted-input wiring
```

不是：

```text
membership 重做
参数重做
PIT 重做
等待 5/20 个交易日
Prior-RPS 必须先解决
Amount A 必须先解决
```

## 24. 修复后预期

R5.1 修完三个 blocker 并重新 clean regression 后，即使：

- 同日真实 Core 仍未发布；
- Prior-RPS 仍 UNKNOWN；
- 第一张 PIT 尚无多日 history；

依然可以考虑：

```text
V4_08_EXTERNAL_ACCEPTANCE_PASS_ENGINEERING_SCOPE_DEGRADED_REAL_SIGNAL
```

然后继续 V4-09。

因为那时剩下的是真实输入能力/Forward 积累，而不是代码尚未接线。

## 25. 最终结论

```text
R4.1 Governance       = ACCEPTED
PIT Membership        = ACCEPTED
R5 Parameter Freeze   = ACCEPTABLE
R5 Schema/Persistence = ACCEPTABLE
R5 Core Logic         = MOSTLY ACCEPTABLE
V4-08 R5              = BLOCKED_R1
```

唯一下一动作：

```text
执行 V4-08 R5.1 三项定点修复
→ 独立复验
→ 决定 V4-08 engineering-scope promotion
```
