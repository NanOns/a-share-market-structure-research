# V4-08 R5.1｜三项定点修复任务卡：B2 Semantic Provenance + Raw Amount + Price Basis

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**输入 HEAD**：`10d500ce51a9a0914c0d812c1c1fee761c5a3af9`  
**日期**：2026-09-30  
**任务性质**：R5 外部验收定点修复，不重做已通过模块

## 0. Authority

外部审计状态：

```text
V4_08_R5_EXTERNAL_ACCEPTANCE_BLOCKED_R1
```

仅三个 blocker：

```text
R5-B01 B2 semantic / rank-universe provenance
R5-B02 Sector Native raw amount accepted-input wiring
R5-B03 Rotation price-basis accepted-input wiring
```

禁止扩大任务范围。

## 1. 明确保留，不重做

以下已经通过，禁止无理由重构：

```text
V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1
R4.1 no-symbol governance
V4_08_ALGORITHM_PARAMETER_SET_R5 五个 retention 值
§10A0 midrank
common-member intersection
four-state TRUE/FALSE/UNKNOWN/NOT_APPLICABLE
Prior-RPS UNKNOWN propagation
Amount A diagnostic isolation
migration 020
PostgreSQL append-only schema
```

如必须修改其中任一语义，先给出：

```text
necessity
affected accepted evidence
migration impact
replay impact
```

否则不要动。

---

## 2. R5-B01｜修复 B2 normal_rank_eligible provenance

当前错误：

```text
src/sector/legacy_b2_r5.py
build_b2_inputs()
```

把：

```text
normal_rank_eligible = True
```

写死。

必须删除该常量化。

## 3. B2 必须复刻 exact legacy semantic source

Legacy chain：

```text
src/workbench_analysis/sector_attention.py
→ _sector_semantics(...)
→ src/workbench_service/semantic.py
→ resolve_semantics(...)
```

依赖：

```text
sector_type
sector_name
semantic_bucket / semantic source
sector_role
sector_valid
```

`normal_rank_eligible` 必须是事实/规则计算结果，不是：

```text
INDUSTRY/THEME => True
```

## 4. 冻结 B2 semantic dependencies

B2 exact extraction 至少增加：

```text
config/sector_semantics.yaml
config/sector_roles.yaml
src/workbench_service/semantic.py
src/sector/roles.py
```

的：

```text
path
SHA256
version
role in legacy calculation
```

并纳入 adapter/model digest。

## 5. sector_valid 映射必须显式

Legacy semantic resolver 读取：

```text
sector_valid
```

不能假设：

```text
V4 PIT formal sector
=
legacy sector_valid true
```

必须：

1. 找到 legacy `sector_valid` exact producer；
2. 提取规则和输入；
3. 证明哪些 V4-08 accepted facts 可以等价重建；
4. 形成 mapping contract。

若无法精确重建：

```text
normal_rank_eligible = UNKNOWN
```

受影响 B2：

```text
confirmed_raw = UNKNOWN
```

不得默认 True。

## 6. normal rank pool 必须完全一致

Legacy：

```text
normal_mask = normal_rank_eligible == true

valid_mask =
normal_mask
AND finite(rel1)
```

必须用：

```text
total_normal
valid_count
```

计算：

```text
type_cross_section_coverage
p1
```

禁止对所有 INDUSTRY/THEME rel1-known sector 直接排名。

## 7. B2 新增反例测试

### S1 NORMAL vs EXCLUDE

同一 type：

```text
4 NORMAL
1 EXCLUDE_FROM_THEME_RANK
```

证明 excluded sector：

```text
不进 denominator
不获得 p1
不改变 normal sector p1
```

### S2 sector_valid=false

证明：

```text
normal_rank_eligible = false
```

### S3 semantic UNKNOWN

若 semantic provenance 不足：

```text
normal_rank_eligible = UNKNOWN
B2 = UNKNOWN
```

不得 False/True。

### S4 mixed rank denominator

构造一个 excluded sector 极高 `rel1`，证明它存在/删除都不改变 normal sectors 的 legacy p1。

## 8. Actual legacy parity test 必须升级

当前：

```text
test_actual_legacy_current_function_against_pit_adapter
```

只使用：

```text
NORMAL_ATTRIBUTE
sector_valid=True
```

覆盖不足。

修复后必须混合：

```text
NORMAL_ATTRIBUTE
EXCLUDE_FROM_THEME_RANK
sector_valid=false
semantic unknown
```

直接比较：

```text
legacy build_sector_current()
vs
R5 adapter
```

至少比较：

```text
normal_rank_eligible
type_cross_section_coverage
p1
current / confirmed_raw
```

---

## 9. R5-B02｜接入 accepted raw amount

合同 §15：

```text
top1/top3_concentration
=
同日可评估成员金额份额
```

禁止使用：

```text
amount_ratio20
turnover
BaoStock
V4-06 supplemental
```

替代 raw amount。

## 10. Raw amount source

必须从：

```text
accepted same-session V4-02 canonical daily
```

或已经被 V4 accepted lineage 正式绑定的等价 canonical source 读取：

```text
security_id
trade_date
raw CNY amount
trading_status
source revision
available_at
quality
```

禁止：

```text
本地未接受 TDX fallback
旧 staging fallback
9/28 amount relabel 为 9/30
```

## 11. Accepted-input source binding

R5 source manifest 增加：

```text
canonical_daily_head/path
artifact SHA
logical/source digest
target_trade_date
amount source revision
```

并保证：

```text
target date mismatch => UNKNOWN
future date => reject
digest mismatch => reject
```

## 12. amount adapter semantics

每个 target member：

```text
actual traded + amount known
=> ACCEPTED raw amount

missing / invalid / source unavailable
=> UNKNOWN / not evaluable
```

不得：

```text
missing amount = 0
```

如果源事实确为 0：

```text
保留 0
```

sector amount denominator：

```text
sum(amount)
```

若 `sum <= 0`：

```text
top1/top3_concentration = UNKNOWN
```

## 13. Raw amount integration tests

必须使用与 materializer **同一 adapter**，不能测试里手工给最终 `current` 塞 amount。

覆盖：

```text
正常 amount
一个成员 unknown
全部 0
target date mismatch
future source date
source digest mismatch
```

验证：

```text
top1_concentration
top3_concentration
quality
reason
```

---

## 14. R5-B03｜接入 accepted price_basis_id

`rotation_r5.py` 已正确要求：

```text
price_basis_id
```

现在必须让真实 accepted-input adapter 提供。

## 15. Price identity authority

禁止创造无来源字符串，例如：

```text
ACCEPTED_COMMON_COORDINATE
```

应使用 accepted canonical price lineage 中已存在的 identity。

当前仓库已有可用语义包括：

```text
price_basis
adjustment_source_revision
adjustment_basis_id
gbbq_snapshot_identity
```

精确采用哪一层，以 V4-02/V4-03 accepted contract 为准。

## 16. 不得只用 generic coordinate label

以下单独不足：

```text
T0_CURRENT_COORDINATE
QFQ
```

因为不能唯一证明同一证券跨观察日处于同一可比较 affine adjustment identity。

必须保留真正：

```text
source revision / adjustment identity
```

## 17. Current adapter output

每个 security target row 至少应提供：

```text
trade_date
price_basis_id
close
ret1
rps20
...
```

`close` 与 `price_basis_id` 必须来自同一 accepted coordinate/source revision。

## 18. Pulse baseline

建立 pulse 时：

```text
prior_core[member].price_basis_id
current_core[member].price_basis_id
```

必须一致才能进入 frozen path。

若不一致：

```text
MIXED_PRICE_BASIS
PULSE_BASELINE_UNAVAILABLE
```

保持 UNKNOWN。

## 19. Price-basis integration tests

必须通过 materializer 使用的同一 adapter。

### P1 same basis

```text
pulse created
baseline stored
```

### P2 different basis

```text
price path UNKNOWN
```

### P3 missing basis

```text
UNKNOWN
```

### P4 future revision

```text
reject
```

### P5 corporate-action transition

若有 accepted affine conversion contract：

```text
转换到统一 evaluation basis
```

否则：

```text
UNKNOWN
```

禁止直接比较原数值。

---

## 20. 禁止 synthetic-only 证明接线

现有 synthetic：

```text
price_basis_id='ACCEPTED_SYNTHETIC_COMMON_COORDINATE'
```

只证明 evaluator 能处理字段。

R5.1 必须新增：

```text
ACCEPTED_INPUT_ADAPTER_INTEGRATION_TEST
```

证明：

```text
accepted-source-shaped row
→ adapter
→ current
→ Sector Native / B0 / Rotation / B2
```

不是测试自己手工造最终对象。

## 21. 不等未来交易日

当前真实 2026-09-30 没有 same-session accepted Core。

不要等未来数据才测试。

建立：

```text
TEST_ONLY isolated accepted-source fixture
```

schema/digest/time semantics 与正式 accepted artifact 一致。

用它验证：

```text
raw amount wiring
price basis wiring
B2 semantic wiring
```

fixture 禁止进入正式 artifact/head。

## 22. 保持真实 2026-09-30 fail-closed

修复后重新 materialize 当前 9/30。

如果 target accepted Core 仍 unavailable：

```text
B0 = UNKNOWN
ROTATION = UNKNOWN
B2 = UNKNOWN
```

仍是正确结果。

不要为了证明修复而把真实输出强行变成 TRUE/FALSE。

修复证明来自：

```text
contract parity
adapter integration tests
TEST_ONLY accepted-source fixture
```

---

## 23. Parameter set 不变

除非发现独立机制硬错误，否则保持：

```text
V4_08_ALGORITHM_PARAMETER_SET_R5
```

和五个 retention values 不变。

禁止：

```text
重新寻参
改阈值
根据候选数量校准
根据未来收益校准
```

---

## 24. No-symbol gate 继续

所有新增 adapter / semantic binding 必须通过：

```text
NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC
```

要求：

```text
hard_gated_equity_symbol_hits = 0
unclassified_paths = []
```

synthetic identifiers 仅可放 TEST_ONLY。

---

## 25. Persistence / migration

优先不新增 migration。

如果只是：

```text
input manifest metadata
input identities
adapter evidence
```

现有 schema 可容纳，则不要新增 migration 021。

只有 database schema 确实无法保存必要 identity 时才新增 append-only migration。

---

## 26. Required evidence

至少：

```text
reports/v4_08/V4_08_R5_1_STAGE_ENTRY.md

reports/v4_08/V4_08_R5_1_B2_SEMANTIC_PROVENANCE.json
reports/v4_08/V4_08_R5_1_B2_RANK_UNIVERSE_PARITY.json
reports/v4_08/V4_08_R5_1_B2_LEGACY_MIXED_SEMANTIC_GOLDEN.json

reports/v4_08/V4_08_R5_1_RAW_AMOUNT_INPUT_BINDING.json
reports/v4_08/V4_08_R5_1_CONCENTRATION_INTEGRATION.json

reports/v4_08/V4_08_R5_1_PRICE_BASIS_INPUT_BINDING.json
reports/v4_08/V4_08_R5_1_ROTATION_PRICE_PATH_INTEGRATION.json

reports/v4_08/V4_08_R5_1_ACCEPTED_INPUT_ADAPTER_INTEGRATION.json
reports/v4_08/V4_08_R5_1_FEEDBACK_ISOLATION.json
reports/v4_08/V4_08_R5_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json

reports/v4_08/V4_08_R5_1_ISOLATED_REGRESSION.json
reports/v4_08/V4_08_R5_1_CLEAN_CHECKOUT_RECEIPT.json
reports/v4_08/V4_08_R5_1_STAGE_CANDIDATE_MANIFEST.json
reports/v4_08/V4_08_R5_1_CLOSURE.md
reports/v4_08/V4_08_R5_1_EXTERNAL_REAUDIT_HANDOFF.json
```

---

## 27. R5.1 必须回答的审计问题

### B2

```text
normal_rank_eligible 从哪里来？
source SHA 是什么？
sector_valid 如何等价重建？
excluded sector 是否完全不进 p1 denominator？
```

### Amount

```text
raw amount 的 accepted authority 是哪一个 artifact/head？
为什么不是 amount_ratio20？
target-date mismatch 如何 fail closed？
```

### Price

```text
price_basis_id 的 accepted authority 是哪个字段/identity？
跨日如何证明 same basis？
corporate-action revision mismatch 如何处理？
```

---

## 28. Clean checkout

最终 implementation commit 必须：

```text
clean detached checkout
disposable PostgreSQL
no config/.env
process DSN
all V4-01..08 required regression
no-symbol gate
B2 mixed-semantic parity
raw amount adapter integration
price-basis adapter integration
```

记录实际 test count。

---

## 29. 不等待真实 Forward

本轮验收标准是：

```text
ENGINEERING CORRECTNESS
```

不是：

```text
真实 Rotation 已发生
真实 sector signal 已非 UNKNOWN
未来 T+5 outcome 已完成
```

修完接线即可复验。

---

## 30. 修复后的预期状态

如果三项通过：

```text
V4_08_R5_1_READY_FOR_EXTERNAL_REAUDIT
```

外部复验可考虑：

```text
V4_08_EXTERNAL_ACCEPTANCE_PASS_ENGINEERING_SCOPE_DEGRADED_REAL_SIGNAL
```

然后进入 V4-09。

仍保持：

```text
Sector/Rotation production permission = false
```

直到后续 Shadow / Forward / Migration gates 满足。

---

## 31. Handoff

Codex 提交后必须报告：

```text
pushed HEAD
changed paths

B2 semantic source bindings + SHA
normal_rank_eligible mapping
mixed-semantic legacy parity result

accepted raw amount source binding
concentration adapter integration result

accepted price_basis source binding
rotation price-path integration result

real 2026-09-30 output distribution
(no requirement that UNKNOWN disappear)

no-symbol scan
clean regression
```

然后停止，等待独立外部复验。
