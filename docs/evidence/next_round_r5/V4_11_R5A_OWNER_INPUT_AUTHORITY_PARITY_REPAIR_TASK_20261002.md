# V4-11 R5A｜V4-07 / V4-09 Owner Input Authority Parity Repair｜2026-10-02

**优先级：** P0 Mainline  
**基线 HEAD：** `1dee36ae83fb63b6a7fe57e05ccb63bb1e0c5099`  
**父阶段：** V4-10 Accepted  
**R4A：** KEEP PASS  
**Stage/Data Head：** KEEP

---

# 1. 目标

只修复：

```text
V4_11 D2 upstream
→ V4-07 BASE_SEED_V1
→ V4-09 STOCK_PREWATCH_V1
```

的 owner-input source authority。

不得返工 R4A、D0 Confirmation、V4-10 reducer、Event predicates、A02/A05/A04。

---

# 2. P0

禁止继续正式使用：

```python
close_t_minus_1 =
    raw/adjusted window reconstructed previous close

ma20_t_minus_1 =
    compute_core(observations[:-1]).ma20
```

作为 `BASE_SEED_V1` 的 accepted owner input。

正式 target-date candidate 必须保持：

```text
close_t_minus_1 =
UNKNOWN(ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE)

ma20_t_minus_1 =
UNKNOWN(ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE)
```

本 R5 不扩展新的 t-1 producer capability。

---

# 3. 必须绑定 accepted authority

至少绑定：

```text
data/v4/V4_07_ACCEPTED_HEAD.json
data/v4/V4_07_ACCEPTED_HEAD_AMENDMENT_A02_R1.json
data/v4/V4_09_ACCEPTED_HEAD.json
data/v4/V4_09_ACCEPTED_HEAD_AMENDMENT_A02_R1.json
data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json

src/v4/base_seed.py
src/v4/stock_prewatch.py

config/v4_07_base_seed_contract_v1.json
config/v4_07_parameter_set_v1.json
config/v4_09_parameter_set_v1.json
```

验证 hash 与 scoped accepted payload 一致。

---

# 4. Owner Input Authority Matrix

对进入 `BASE_SEED_V1._eval` 的每个 fact 生成机器可读矩阵：

```text
field
accepted owner
accepted source field/rule
target-date source binding
quality semantics
TRUE/FALSE/UNKNOWN semantics
time role
reconstruction allowed
formal in R5
UNKNOWN reason
```

至少覆盖：

```text
research_universe
actual_bar
price_identity_READY
minimum_liquidity
core_price_damage
severe_extension
bias20_atr
compression_state
delta3
ma_structure_state
close_t
ma20_t
close_t_minus_1
ma20_t_minus_1
core_participation_result
```

---

# 5. t-1 硬规则

禁止：

```text
从 raw bar 补值
从 adjusted bar 补值
从 previous compute_core 补值
把“技术上能算”包装成“正式可用”
```

可以在 diagnostic artifact 记录可算值，但：

```text
must_not_feed_formal_BASE_SEED
```

---

# 6. actual_bar exact semantics

恢复 accepted V4-07：

```text
accepted dated status == ACTUAL_TRADED
→ TRUE

accepted dated status == SUSPENDED
→ FALSE

other / missing / conflict
→ UNKNOWN
```

不得只用 raw bar present/absent。

---

# 7. price_identity_READY exact semantics

不得再用：

```text
has_actual_bar
```

近似 `price_identity_READY`。

必须建立 source-bound target identity fact，并至少验证：

```text
security_id canonical validity
source symbol binding
board scope
target trade_date
target candidate publication identity
historical_as_recorded_claim = false
```

不得伪称 target candidate 是旧 V4-05 accepted publication。

---

# 8. research_universe

允许保持 TRUE，但必须证明该 entity 属于 sealed target stock universe，并绑定：

```text
target identity publication
entity membership
board scope
```

不得对任意输入 entity 无条件写 TRUE。

---

# 9. 其余 owner inputs

可以从 R4 full source window 计算 target-date candidate：

```text
core factors
profile primitives
compression
ma structure
extension risk
participation
accepted RPS delta
```

但必须：

1. 只复用 accepted owner 算法/参数；
2. 不新增 accepted owner 没有的正式字段能力；
3. UNKNOWN 传播保持 exact；
4. 不因原始数据存在自动提升 source authority。

---

# 10. 9/28 Exact Owner Parity Gate｜P0

使用 R5 target owner adapter 在：

```text
target = 2026-09-28
```

重放 accepted owner chain。

## 10.1 V4-07 parity

与 A02 scoped accepted V4-07 amendment artifact 比较：

```text
security_id
BASE_SEED state
quality
waiting reasons
domain states
input UNKNOWN semantics
```

要求：

```text
exact accepted row scope
business mismatch = 0
quality mismatch = 0
UNKNOWN reason mismatch = 0
```

## 10.2 V4-09 parity

把重放 Seed 输给 accepted V4-09 pure owner，与 A02 scoped accepted V4-09 amendment artifact 比较：

```text
raw qualification
PREWATCH result
quality
reason
```

要求：

```text
business mismatch = 0
```

---

# 11. Independent oracle

独立 verifier 不得调用 R5 target owner-input adapter helper 来生成 expected owner facts。

至少验证：

```text
formal t-1 known count = 0
actual_bar tri-state authority
identity fact validity
accepted RPS binding
owner parameter digest
Seed output
PREWATCH output
```

Tamper cases：

```text
raw bar exists + accepted status UNKNOWN
→ actual_bar UNKNOWN

raw bar absent + accepted status SUSPENDED
→ actual_bar FALSE

invalid identity binding
→ price_identity_READY UNKNOWN

raw t-1 exists
→ formal close_t_minus_1 UNKNOWN

raw t-1 MA20 computable
→ formal ma20_t_minus_1 UNKNOWN
```

---

# 12. 9/29 / 9/30 sealed owner publications

9/28 parity PASS 后生成：

```text
2026-09-29 target owner facts
2026-09-30 target owner facts
```

必须标记：

```text
accepted = false
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
formal_consumer_enabled = false
```

本任务不做 D2/Event final sealing；交给 R5B。

---

# 13. R4A / D0 冻结

不得改变：

```text
R4A target fact publications
LAUNCH_CONFIRM detector
RECOVERY_TURN detector
Pullback/Trend diagnostic scope
legacy thresholds
scenario priority
```

---

# 14. 禁止

```text
创建 V4_11_ACCEPTED_HEAD
推进 Stage Head
修改 Data Head
执行 V4-12
修改 V4-07/V4-09 accepted owner contract
增加 t-1 producer capability
开启 production/shadow/focus
```

---

# 15. 完成状态

```text
V4_11_R5A_OWNER_INPUT_AUTHORITY_PARITY_CANDIDATE_READY
```
