# V4 R14 独立外部验收 R1｜2026-10-02

**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**R14 基线**：`33b1949a1c05b0fe6c9068e6db9f219a9f11378b`  
**R14 clean-checkout tested source**：`1356b27a8cf13a8dbbda34ce6f38432bca65fca9`  
**当前远端 HEAD**：`226270c3178736e9b52e0e3574339039ed191350`

# 1. 唯一总裁决

```text
R14_EXTERNAL_AUDIT =
PARTIAL_PASS_V4_13_CONTRACT_REPAIR_REQUIRED

R14A_V4_12_ACCEPTED_HEAD_PROMOTION =
PASS_KEEP

V4_12_ACCEPTED_HEAD =
PASS_KEEP_SCOPED_ENGINEERING

V4_STAGE_ACCEPTED_HEAD =
PASS_KEEP_V4_00_TO_V4_12_ACCEPTED

V4_DATA_ACCEPTED_HEAD =
PASS_KEEP_2026_09_30

R14B_V4_13_STAGE_ENTRY =
PASS_KEEP_CONTRACT_DESIGN_ONLY

R14B_SCOPE_NO_RUNTIME =
PASS

R14B_V4_13_CONTRACT_FREEZE =
BLOCKED_BY_C01_C02_C03_C04

V4_13_RUNTIME =
NOT_AUTHORIZED_YET

V4_14_REPLAY_GATE_B =
NOT_AUTHORIZED
```

本轮不回滚 V4-12，不重开 R8-R13。需要修复的仅是 V4-13 Contract Freeze 自身的字段语义、时点和 authority binding。

# 2. 远端提交链

R14 共 3 个提交：

```text
3df69b3b72e1574e7d34c1bdb3b93ecbb19b7f84
Promote V4-12 scoped engineering acceptance and freeze V4-13 projection contracts

1356b27a8cf13a8dbbda34ce6f38432bca65fca9
Include exact V4-12 scoped accepted head artifact

226270c3178736e9b52e0e3574339039ed191350
Seal R14 exact detached promotion replay and contract-only handoff
```

最终 HEAD 相对 tested source 仅变更：

```text
reports/v4_13_r1/R14_CLEAN_CHECKOUT_GATE.json
reports/v4_13_r1/R14_FINAL_HANDOFF.json
reports/v4_13_r1/R14_TEST_RESULTS.xml
```

不存在测试后继续修改 Runtime / Contract 的漂移。GitHub 当前没有 commit status / Actions run，本报告不声称 CI 背书。

# 3. R14A｜V4-12 Accepted Head Promotion

已创建：

```text
data/v4/V4_12_ACCEPTED_HEAD.json
```

当前：

```text
contract_id = V4_12_ACCEPTED_HEAD_V1
status = PASS_SCOPED_ENGINEERING
knowledge_lineage = RECONSTRUCTED_CORRECTED
AS_RECORDED = false
```

权限全部正确保持关闭：

```text
production_permission = false
shadow_production_permission = false
focus_cutover_permission = false
global_mandatory_adoption = false
```

Capability Map 精确保留 V4-12 已通过能力，并明确：

```text
REAL_TARGET_DATE_STRUCTURE_SIGNAL =
DEGRADED_BY_ACCEPTED_OWNER_CAPABILITY

HISTORICAL_AS_RECORDED_D1 =
NOT_PROVEN

FULL_D0_D1_D2_REPLAY =
NOT_YET_ACCEPTED_V4_14

V4_13_PROFILE_ADVANCED_PROJECTION =
NOT_IMPLEMENTED
```

Stage Head 仅从：

```text
V4_00_TO_V4_11_ACCEPTED
```

推进为：

```text
V4_00_TO_V4_12_ACCEPTED
```

未发现 V4-00～V4-11 accepted metadata 被重写。

Data Head 继续：

```text
accepted_trade_date = 2026-09-30
```

## 3.1 `mutations = 2` 不是幂等失败

首次 promotion 正常写入：

1. `V4_12_ACCEPTED_HEAD.json`
2. `V4_STAGE_ACCEPTED_HEAD.json`

clean detached replay 证明重复执行：

```text
fresh_promotion_replay =
EXACT_ACCEPTED_HEAD_AND_STAGE_BYTES

idempotence =
ZERO_MUTATIONS
```

因此：

```text
R14A_V4_12_ACCEPTED_HEAD_PROMOTION = PASS_KEEP
```

# 4. R14B｜正确完成的部分

V4-13 Stage Entry：

```text
status = AUTHORIZED_CONTRACT_DESIGN_ONLY
runtime_implemented = false
```

新增了 V4-13 contract-only 文件组，没有新增 V4-13 Runtime、migration 或 V4_13_ACCEPTED_HEAD。

`LOO_CONTEXT_V1` 的核心方向正确：目标股必须在所有 sector context 计算前剔除，并重新计算 sector native、seed aggregates、B0/B2、rank/median、历史比较和 rotation lineage；禁止只减计数但保留 self-including 状态。

DAG 也正确冻结了核心禁边：

```text
D2[t] -> D1[t]            FORBIDDEN
D1[t] -> B0/B1/B2[t]      FORBIDDEN
CONTEXT[t] -> A/C[t]       FORBIDDEN
Focus/UI -> QUALIFICATION  FORBIDDEN
Supplemental -> Core       FORBIDDEN
Future Outcome -> Same-day State FORBIDDEN
```

V4-12 Structure 在 V4-13 只允许 read-only projection，不允许再计算第二套 Anchor/Breakout/Support/Acceptance。

当前 20 个 R14 tests 全部通过，12 个 independent vectors L01-L12 和 negative gates 有效，但仍不足以关闭下面 4 个合同级缺口。

# 5. C01｜TIME_ROLE_OVERCOUPLING

当前：

```text
primary_industry
supporting_concepts
```

都被注册为：

```text
T_WITH_EXACT_T_MINUS_1_LOO_HISTORY
```

并要求：

```text
EXACT_PREVIOUS_ACCEPTED_MARKET_SESSION_NOT_SAME_DAY_REVISION
```

这与最高合同 §20.1/20.2 不一致。

`PRIMARY_INDUSTRY` 来自当日确定性行业分类关系；`SUPPORTING_CONCEPTS` 保存当日符合关系合同的完整概念集合。它们需要 current T exact membership + cutoff/source authority，不应该因为 t-1 LOO history 缺失而一起 UNKNOWN。

当前合同会导致：

```text
current membership = KNOWN
LOO history = missing
→ primary_industry / supporting_concepts 被错误降级
```

违反“缺哪个能力，只降级依赖该能力的字段”。

修复应拆成：

```text
primary_industry:
T_EXACT_MEMBERSHIP_AT_CUTOFF

supporting_concepts:
T_EXACT_MEMBERSHIP_AT_CUTOFF
```

而 `algorithmic_support_sector / relative_sector_state / sector_context_state / sector_context_quality` 再各自声明真实的 LOO current/history 依赖。

必须新增独立向量：

```text
current membership KNOWN
loo_history MISSING
=> primary_industry KNOWN
=> supporting_concepts KNOWN
=> 只有历史依赖字段允许 UNKNOWN
```

# 6. C02｜SECTOR_CONTEXT_STATE_SEMANTICS_NOT_FROZEN

当前 field registry 只写：

```text
field = sector_context_state
data_type = enum_or_identity
source_field = loo_raw_context_state
producer_contract_id = LOO_CONTEXT_V1
```

但整个 V4-13 contract set 没有冻结：

```text
sector_context_state 的 enum
或 object schema
或 exact source projection
或 AST
或 deterministic mapping
```

因此 Runtime 开工后仍必须由实现者自行决定“sector_context_state 到底是什么”，违反 §81.4 Contract Completeness DoD。

不要为了修字段发明神秘综合分数或第二套状态机。建议冻结为**无损、结构化的 selected LOO sector context snapshot**，至少明确：

```text
selected_sector_id
sector_type
loo_b0_raw
loo_confirmed_raw
loo_warm_raw
emergence
adjusted_seed_width
rotation_core_state
relative_sector_state
membership_basis
context_quality
reasons[]
source_refs[]
```

如某 capability 尚未实现，必须保留 UNKNOWN / NOT_IMPLEMENTED / NOT_APPLICABLE，而不是伪造值。

# 7. C03｜MEMBERSHIP DAG SOURCE AUTHORITY MISBIND / AMBIGUOUS

当前 DAG 存在复合 edge：

```text
producer = F0
consumer = CONTEXT
field = accepted_membership_and_non_target_primitives

source_owner_binding =
data/v4/V4_04_ACCEPTED_HEAD.json
```

但 Sector Membership 的 accepted authority 实际是：

```text
data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json
```

`LOO_CONTEXT_V1` 本身也正确引用了该 Membership Head。

这造成：

```text
LOO contract:
membership owner = V4_08 PIT Membership

DAG registry:
membership + primitives owner = V4_04
```

的冲突。

必须拆分：

```text
MEMBERSHIP -> CONTEXT
source = exact V4_08 PIT Membership Accepted Head
```

以及：

```text
CORE MEMBER PRIMITIVES -> CONTEXT
source = 对应 V4_04 / V4_05 accepted owner
```

若使用：

```text
base_seed_raw
```

必须显式绑定：

```text
V4_07 Accepted Head
```

不得再用一个复合字段把多个 owner 混成 V4_04 edge。

# 8. C04｜ROTATION_STRUCTURE_ENRICHMENT MULTI-SOURCE BINDING INCOMPLETE

当前 field registry：

```text
field = rotation_structure_enrichment
source_binding = V4_08_ACCEPTED_HEAD_AMENDED_R1
source_field = rotation_core_state_PLUS_READ_ONLY_D1
```

但该字段天然有两个独立来源：

```text
V4-08 rotation_core_state
+
V4-12 read-only Structure
```

Producer registry 虽然在更高层列出 V4_08 / V4_12，DAG 也有 D1→D3，但字段级 source identity 仍只绑定 V4_08，导致 field-level digest / source identity / quality propagation 无法无歧义实现。

必须冻结：

```text
rotation_source = V4_08 accepted owner
structure_source = V4_12 accepted owner
```

或等价 `source_bindings[]`，并冻结 object schema。

质量必须 component-wise：

```text
rotation known + D1 unavailable
=> rotation_core_state 保留
=> structure component UNKNOWN/NOT_IMPLEMENTED
=> enrichment overall 仅降级相应组件
```

D1 继续只允许 D3 enrichment，不能回写 B0/B1/B2。

# 9. V4-08 PIT Membership consumer-scope 注意项

`V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json` 中存在：

```text
formal_consumers_enabled = false
membership_acceptance_scope = FORWARD_PIT_MEMBERSHIP_ONLY
```

但后续 V4-08 Accepted Head 已完成 scoped engineering acceptance，并登记：

```text
ACCEPTED_CONTEXT_ROUTING = ENGINEERING_ACCEPTED
```

所以本报告**不直接把该 flag 判成当前 R14B P0**。

R15 必须显式证明工程消费路径：

```text
V4_13 engineering consumer
→ V4_08 Accepted Head
→ exact membership binding
→ V4_08 PIT Membership Accepted Head
```

并保持 production=false。

若无法证明，则 fail closed：

```text
BLOCKED_MEMBERSHIP_CONSUMER_SCOPE
```

禁止直接绕过 Accepted Head 读取 provider/raw membership。

# 10. 为什么现在不能直接实现 V4-13 Runtime

V4-13 主方向是正确的，但 Contract Freeze 仍留下 4 个需要实现者猜测的问题：

1. primary/supporting 是否依赖历史；
2. sector_context_state 的精确定义；
3. membership 到底由 V4_04 还是 V4_08 提供；
4. rotation_structure_enrichment 的第二个 source identity 如何绑定。

这些都属于合同层语义，不能留给 Runtime 编码阶段临场决定。

因此：

```text
V4_13_RUNTIME = NOT_AUTHORIZED_YET
```

# 11. KEEP

保持：

```text
V4_12_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_12_ACCEPTED
V4_DATA_ACCEPTED_HEAD = 2026-09-30
```

不得重开：

```text
R8/R9 source/time authority
R10 Runtime Entry
R11 persistence/output closure
R12 Multi-Anchor
R13 Breakout Episode Continuity
R14A V4-12 Promotion
```

# 12. 下一步

只执行一张修复卡：

```text
R15A
V4-13 R1.1 Contract Semantic / Authority Repair
```

顺序：

```text
fix C01-C04
→ independent contract vectors / negative gates
→ clean detached validation
→ commit + push
→ STOP
→ independent external audit
```

R15 仍禁止 V4-13 Runtime。只有 R15 外审通过后，才发布 V4-13 Runtime implementation task cards。
