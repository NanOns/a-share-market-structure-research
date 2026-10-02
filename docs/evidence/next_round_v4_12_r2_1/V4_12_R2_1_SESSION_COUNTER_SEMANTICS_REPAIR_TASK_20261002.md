# V4-12 R2.1｜Session / Evaluable Counter Semantic Repair Task｜2026-10-02

**基线 HEAD：** `5267c9e482268dfaaf06d1c752e1bb3d09e33b6f`  
**任务性质：** P0 Contract Semantic Repair  
**R2 Source Authority：** PASS KEEP / DO NOT REOPEN  
**V4-12 Runtime：** FORBIDDEN

# 1. 唯一目标

修复当前：

```text
post_creation_sessions
```

同时承担：

```text
market-session age
```

和：

```text
post-event evaluable-session count
```

的双重语义。

禁止只改 unit 字符串。

# 2. 强制拆分两个 counter

## 2.1 post_creation_market_sessions

定义：

```text
accepted market calendar 中
available_date 之后到 observation_trade_date 的市场会话数量

creation day = 0
next market session = 1

security suspension / missing bar
不阻止 market age 前进

same-day revision
不增加

calendar unavailable
→ UNKNOWN
```

unit：

```text
market_sessions_after_available_date
```

producer：

```text
V4_12_SESSION_COUNTER_V2
```

用途仅限：

```text
old_anchor
earliest test
same-day self-confirmation prevention
```

## 2.2 post_creation_evaluable_sessions

定义：

```text
available_date 之后
已经产生可评估 D1 observation 的会话数
```

要求：

```text
missing / suspension / required coordinate unavailable
不增加

same-day revision
不增加

不是 consecutive counter
```

unit：

```text
evaluable_sessions
```

producer：

```text
V4_12_SESSION_COUNTER_V2
```

用途：

```text
acceptance.PENDING
```

不得用 market age 替代。

# 3. AST 修复

新增/更新：

```text
old_anchor =
post_creation_market_sessions
>= earliest_anchor_test_sessions
```

所有“旧 Anchor / 最早测试”判断必须引用 `old_anchor` 或 market-age counter：

```text
support
breakout
recovery
acceptance
```

Acceptance 必须冻结为：

```text
1 BROKEN / hard invalidated
2 UNKNOWN / required current observation unavailable
3 ACCEPTED:
    old_anchor
    AND held_count >= acceptance_consecutive_sessions
4 PENDING:
    post_creation_evaluable_sessions
    < acceptance_consecutive_sessions
5 otherwise:
    NOT_ACCEPTED
```

`held_count` 继续是：

```text
连续可评估会话 C >= anchor_upper
```

不要改成累计 count。

# 4. 缺失 / 停牌语义

必须证明：

```text
missing / suspended market session
→ market age 增加
→ evaluable count 不增加
→ held_count consecutive chain 断开
→ current support observation = UNKNOWN
→ stale = true
```

缺失不能：

```text
当作 FALSE
当作 hold
当作 recovery
当作一个 evaluable session
```

# 5. same-day revision

同一个 market date 的 r1/r2/r3：

```text
market-age counter
不增加

evaluable counter
不重复增加

held_count
不重复增加

breach_count
不重复增加
```

revision 只生成新 observation revision。

# 6. B03_missing 必须订正

现有：

```text
B03_missing
expected = NOT_ACCEPTED
```

不能原样保留。

应重新设计为明确 multi-step sequence vector：

```text
T0 created
T+1 missing
T+2 first evaluable hold
```

T+2：

```text
market_age = 2
evaluable_count = 1
held_count = 1
expected acceptance = PENDING
```

不能继续写：

```text
calendar age >= 2
→ NOT_ACCEPTED
```

# 7. 新增 sequence vectors

至少：

## C01 creation day

```text
market_age=0
evaluable_count=0
support=IDLE
no same-day acceptance
```

## C02 next market session suspended

```text
market_age=1
evaluable_count=0
evaluable=false
support=UNKNOWN
stale=true
```

## C03 resume

```text
market_age=2
evaluable_count=1
held_count=1
acceptance=PENDING
```

## C04 second adjacent evaluable hold

```text
market_age=3
evaluable_count=2
held_count=2
acceptance=ACCEPTED
```

## C05 enough evaluable observations, hold failed

```text
evaluable_count>=2
held_count<2
acceptance=NOT_ACCEPTED
```

## C06 same-day revision

两个 counter 均不因 revision 增量。

## C07 missing calendar authority

```text
market_age = UNKNOWN
no fabricated old_anchor
```

expected 必须由独立 oracle 构造。

# 8. 新增 Time Domain Compatibility Audit

新增：

```text
reports/v4_12_r2_1/V4_12_R2_1_TIME_DOMAIN_COMPATIBILITY_AUDIT.json
```

扫描所有：

```text
field <op> parameter
counter <op> threshold
```

每条记录：

```text
field
field_semantic_dimension
field_unit
parameter
parameter_semantic_dimension
parameter_unit
AST path
compatible
reason
```

最终：

```text
incompatible_edges = 0
```

禁止仅按字符串相等判定；必须识别：

```text
market-session age
evaluable-session count
consecutive evaluable count
actual-session separation count
ratio / ATR multiple
price / ATR price
percentage points
```

# 9. P1 unit metadata normalization

不改参数数值，只统一机器语义。

至少检查并按定义修正：

```text
pivot_left_count
pivot_right_count
breach_count
held_count
recovery_held_count
prior_* counterparts
support_break_consecutive_sessions
support_tentative_hold_sessions
support_separated_retest_sessions
impulse_body_atr_min
impulse_range_atr_min
range_anchor_range_atr_max
```

对：

```text
body_atr
range_atr
prior_range20_atr
```

这类“价格差 / ATR”结果，明确为：

```text
dimensionless_ATR_multiple
```

不要用裸 `"ATR"` 造成价格单位和倍数的歧义。

# 10. R2 Authority Repair 必须保持

不得重开或改变：

```text
delta3 -> RPS_DELTA_V1
prior_delta3 mapping
near_high20 -> POSITION_STATE_V1
V4-03 target-date blocked policy
coordinate authority
alpha/beta blocked
prior_range20_atr blocked
pivot source blocked
RANGE_UPPER REMOVE_EXTRA_TRIGGER
dynamic MA blocked
generic CORE_FACTOR fallback = 0
false accepted owner claim = 0
```

# 11. Source authority / heads 不得变化

保持：

```text
V4_STAGE_ACCEPTED_HEAD =
V4_00_TO_V4_11_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
2026-09-30
```

Protected artifacts 必须 byte-identical。

# 12. 禁止

```text
V4-12 runtime implementation
src/v4 structure engine
schema migration
D2 integration
V4-13
production
shadow
focus
global mandatory adoption
```

# 13. 验收

至少提供：

```text
R2 authority parity = PASS unchanged
coordinate authority = PASS unchanged
generic CORE_FACTOR fallback = 0
false accepted owner claim = 0

old_anchor only consumes market-age domain
PENDING only consumes evaluable-count domain

B03_missing corrected
new C01-C07 sequence vectors PASS
unaffected prior vectors PASS
time-domain audit incompatible_edges = 0

same-day revision counters unchanged
missing/suspension sequence semantics PASS
```

如 business AST 变化，只允许本任务明确授权的 counter/time-domain 修复；输出 exact AST diff。

# 14. 最终状态

只允许：

```text
V4_12_R2_1_TIME_COUNTER_SEMANTICS_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```

完成后：

```text
commit + push
STOP
```

等待独立外审。

不得自行授权 runtime。
