# V4 R8 独立外部验收审计 R1｜2026-10-02

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**R8 基线 HEAD：** `b475002697bb3c5d91fab1ba44852b31d0d1da29`  
**tested source：** `79a0b25a6669d4629c8fc40feb08ad1ced3f6031`  
**当前远端 HEAD：** `5267c9e482268dfaaf06d1c752e1bb3d09e33b6f`

# 1. 总裁决

```text
V4_R8_EXTERNAL_AUDIT =
PARTIAL_PASS_R2_1_TIME_COUNTER_SEMANTICS_REPAIR_REQUIRED

R6R1 = PASS_KEEP
V4_12_R2_SOURCE_AUTHORITY_REPAIR = PASS_KEEP
V4_12_R2_PRODUCER_AUTHORITY_PARITY = PASS_KEEP
V4_12_R2_COORDINATE_AUTHORITY = PASS_KEEP
V4_12_R2_OWNER_UNIT_REPAIR = PASS_KEEP

V4_12_R1_BUSINESS_AST_BYTE_IDENTITY = PASS_FACT
V4_12_R1_69_VECTOR_EXECUTION = 69/69_MECHANICAL_PASS
V4_12_R1_VECTOR_NORMATIVE_VALIDITY = FAIL_P0_B03_MISSING_EXPECTATION

V4_12_CONTRACT_FREEZE = BLOCKED_R2_1
V4_12_RUNTIME = NOT_AUTHORIZED
```

R2 已成功修复上一轮 source/producer authority 主问题；当前唯一 P0 是 **时间计数语义被一个字段混用**，导致停牌/缺失路径下 Acceptance 状态错误。

# 2. R2 已通过并 KEEP 的内容

- generic `CORE_FACTOR_V1` fallback 已归零；
- `delta3 -> rps5_delta3 -> RPS_DELTA_V1 -> accepted RPS history` 正确；
- `near_high20_state -> POSITION_STATE_V1 / V4-04` 正确，目标日无正式 publication 时显式 block；
- V4-03 target-date factors 未拿 V4-11 candidate 偷渡正式 producer；
- `alpha/beta` 已从 Core Factor 移除并显式 block；
- `prior_range20_atr` 采用 Option B BLOCK；
- Pivot 未冒充 V4-03 factor；
- coordinate authority 已绑定 V4-02/Data Head adjustment lineage；
- `slope20` 与 `range_anchor_abs_slope20_max` 已修为 dimensionless；
- RANGE_UPPER 已去掉额外 `breakout_trigger`；
- Dynamic MA 无 source-event allowlist 时显式 block；
- 未修改 `src/v4` runtime、migration、Stage/Data Head、Production/Shadow/Focus。

# 3. 测试事实

```text
135 tests
0 failures
0 errors
0 skipped

R1 business vectors:
69 / 69 mechanical PASS

R2 authority vectors:
12 / 12 PASS
```

GitHub 当前没有额外 status/workflow，不能声称 CI 背书。

# 4. P0：post_creation_sessions 同时承担两个时间域

R2 source derivation 写：

```text
post_creation_sessions =
Market sessions strictly after available_date
```

但 Field Registry 写：

```text
unit = evaluable_sessions
```

Machine AST 又同时把它用于：

```text
old_anchor:
post_creation_sessions >= earliest_anchor_test_sessions
```

其中：

```text
earliest_anchor_test_sessions
unit = market_sessions_after_available_date
```

和：

```text
acceptance.PENDING:
post_creation_sessions < acceptance_consecutive_sessions
```

其中：

```text
acceptance_consecutive_sessions
unit = evaluable_sessions
```

所以同一个 counter 同时被要求表示：

```text
市场会话年龄
```

与：

```text
创建后可评估会话数量
```

停牌/缺失日一出现，两者就分叉。

# 5. 为什么会产生真实错误

最高合同 §41C：

```text
新 Anchor 今日 IDLE；
次一市场会话若 actual bar/换基/ATR 缺失
→ UNKNOWN observation
→ preserve prior state
→ stale
```

最高合同 §41D：

```text
PENDING =
事件后尚无 2 个可评估会话

ACCEPTED =
后 2 个连续会话 C >= anchor_upper
```

例：

```text
T0：创建 Anchor
T+1：市场开市，但个股停牌/不可评估
T+2：恢复交易，可评估，C >= anchor_upper
```

正确应为：

```text
T+1:
market_age = 1
evaluable_count = 0
Support = UNKNOWN

T+2:
market_age = 2
evaluable_count = 1
held_count = 1
Acceptance = PENDING
```

若 `post_creation_sessions` 按 market sessions，则 T+2 会落到 `NOT_ACCEPTED`。  
若按 evaluable sessions，则 T+1 的 `old_anchor` 仍为 false，Support 会错误保持 `IDLE`，而不是 `UNKNOWN`。

因此必须拆分两个 counter。

# 6. B03_missing 的 expected 错了

当前 R1 向量：

```text
B03_missing
post_creation_sessions = 3
prior_adjacent_evaluable = false
prior_held_count = 1
expected = NOT_ACCEPTED
```

其 proof 说：

```text
missing intervening session resets count;
calendar age alone insufficient
```

但 §41D 明确 `PENDING = 尚无2个可评估会话`。

缺失日应当：

```text
打断 held_count 的连续性
```

不能等价于：

```text
已经拥有2个可评估 observation
```

所以 69/69 只能证明 implementation 与 current expected 一致，不能证明 current expected 正确。

# 7. 正确修复：拆成两个 counter

## post_creation_market_sessions

```text
accepted market calendar 中
available_date 之后到 observation_trade_date 的市场会话数

creation day = 0
next market session = 1

security suspension / missing bar
不阻止 market age 前进

same-day revision
不增加
```

用途：

```text
old_anchor
earliest test
same-day self-confirmation prevention
```

## post_creation_evaluable_sessions

```text
available_date 之后
已经形成可评估 D1 observation 的会话数量

missing / suspension / required coordinate unavailable
不增加

same-day revision
不增加

不是 consecutive counter
```

用途：

```text
acceptance.PENDING
```

`held_count` 继续表示连续可评估 hold，会被缺失打断。

# 8. 建议 AST

```text
old_anchor =
post_creation_market_sessions
>= earliest_anchor_test_sessions
```

Acceptance：

```text
1 BROKEN
2 UNKNOWN
3 ACCEPTED:
    old_anchor
    AND held_count >= acceptance_consecutive_sessions
4 PENDING:
    post_creation_evaluable_sessions
    < acceptance_consecutive_sessions
5 otherwise:
    NOT_ACCEPTED
```

# 9. 必测 sequence

```text
C01 creation day
C02 next market session suspended
C03 resume: first evaluable hold -> PENDING
C04 second adjacent evaluable hold -> ACCEPTED
C05 >=2 evaluable observations but held_count<2 -> NOT_ACCEPTED
C06 same-day revision no counter increment
C07 missing calendar -> market-age UNKNOWN
```

# 10. P1：补 Time Domain Compatibility Audit

新增机器 gate，逐条检查：

```text
field <op> parameter
counter <op> threshold
```

记录：

```text
semantic_dimension
unit
counter definition
increment/reset rule
missing rule
same-day revision rule
```

最终：

```text
incompatible_edges = 0
```

当前 unit parity 只核 external owner，无法发现这类内部时间域冲突。

# 11. P1 unit metadata 顺带规范

不改参数数值，只消歧：

```text
pivot_left/right_count -> actual_evaluable_sessions
breach/held/recovery held 与对应参数统一 semantic unit
impulse_body_atr_min -> dimensionless_ATR_multiple
impulse_range_atr_min -> dimensionless_ATR_multiple
range_anchor_range_atr_max -> dimensionless_ATR_multiple
```

# 12. 下一轮不重做

KEEP：

```text
R6R1
R2 source authority reconciliation
RPS delta authority
V4-04 near_high authority
coordinate authority
range/pivot blocks
RANGE_UPPER reconciliation
dynamic MA block
slope20 unit fix
12 authority vectors
producer authority parity framework
```

# 13. Heads / permissions

继续：

```text
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_11_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
V4_12_RUNTIME = NOT AUTHORIZED

production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

# 14. 最终状态

```text
R8 SOURCE AUTHORITY = PASS_KEEP

R8 CONTRACT FREEZE =
BLOCKED_R2_1_TIME_COUNTER_SEMANTICS

NEXT =
V4_12_R2_1_SESSION_COUNTER_SEMANTICS_REPAIR

AFTER R2.1 EXTERNAL PASS:
may authorize scoped V4-12 runtime implementation
```
