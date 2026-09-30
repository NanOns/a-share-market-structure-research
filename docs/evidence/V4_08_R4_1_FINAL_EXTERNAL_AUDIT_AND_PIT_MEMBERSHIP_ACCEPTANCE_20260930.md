# V4-08 R4.1 最终独立审计 + PIT Membership Baseline 外部验收｜2026-09-30

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**审计 HEAD**：`75767711835207109927f2babfb547415f89d3fb`  
**实现提交**：`60a18f9ce265a36547217c48dca3f3c0b2cd50a7`  
**上一审计 HEAD**：`0d959b24a44528265aff4784d8c283902f0abd3e`  
**合同基线**：`A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md`

---

# 1. 唯一总状态

本轮必须拆成三个独立结论：

```text
V4_08_R4_1_GOVERNANCE_EXTERNAL_ACCEPTANCE_PASS
```

```text
V4_08_PIT_MEMBERSHIP_BASELINE_EXTERNAL_ACCEPTANCE_PASS_R1
```

但：

```text
V4_08_STAGE_EXTERNAL_ACCEPTANCE_BLOCKED_ALGORITHM_COMPLETION_REQUIRED
```

即：

- R4.1 的“禁止特定股票代码特判”全仓治理修复通过；
- 2026-09-30 第一张真实 Forward PIT sector membership baseline 正式通过；
- 但整个 V4-08 `Sector / Rotation Core` 不能 FULL PASS，因为 §78 要求的 B0/B1/B2、参数冻结和正式 producer 尚未全部完成。

当前全局阶段范围继续保持：

```text
V4_00_TO_V4_07_ACCEPTED
```

允许新增**仅限 membership baseline 的 scoped accepted head**，但不得创建最终：

```text
data/v4/V4_08_ACCEPTED_HEAD.json
```

---

# 2. R4.1 提交身份

从上一审计：

`0d959b24a44528265aff4784d8c283902f0abd3e`

到当前：

`75767711835207109927f2babfb547415f89d3fb`

实现提交：

`60a18f9ce265a36547217c48dca3f3c0b2cd50a7`

封存提交：

`75767711835207109927f2babfb547415f89d3fb`

封存提交只增加 R4.1 evidence/report，没有继续修改实现代码，因此对实现提交执行的 clean regression 可覆盖当前实现事实。

GitHub combined status 当前为空：

```text
statuses = []
```

作为证据限制记录，不单独构成 blocker。

---

# 3. R4.1 P0 股票代码特判治理｜PASS

上一轮硬问题：

1. `scripts/**/*.py` 被无条件归为 AUDIT_ONLY；
2. identity promotion 脚本写死两只股票；
3. promotion verifier 复制同一股票集合；
4. production 实际调用的 phase runner 被误标为 audit-only；
5. Phase1 QA 固定五只真实股票，并可影响 PASS/BLOCKED；
6. Phase0/TDX QA 中还存在多组固定真实股票。

R4.1 已完成实质修复。

---

# 4. 新治理分类模型

`config/runtime_path_policy_v1.json`

当前 hard-gated categories：

```text
PRODUCTION_RUNTIME
SYSTEM_PIPELINE
GOVERNANCE_MUTATION
RUNTIME_CONFIGURATION
```

允许 symbol 作为数据存在的范围：

```text
TEST_ONLY
EVIDENCE_ONLY
AUDIT_INPUT_ONLY
USER_DATA
IMMUTABLE_FACT_DATA
REFERENCE_DATA
```

未分类对象：

```text
UNCLASSIFIED_FAIL_CLOSED
```

这符合长期硬规则：

> 真实股票代码可以作为事实数据存在，但不能作为系统规则存在。

---

# 5. scripts 不再默认 AUDIT_ONLY

当前 scanner：

`scripts/scan_no_symbol_specific_runtime_logic.py`

已经移除：

```text
all scripts => AUDIT_ONLY
```

现在：

- 写 accepted/runtime artifact 的脚本优先识别为 `GOVERNANCE_MUTATION`；
- 未显式审计豁免的普通 scripts 默认进入 `SYSTEM_PIPELINE`；
- `promote_* / accept_* / materialize_* / apply_* / publication-related` 等进入 hard gate；
- writer detection 优先于 audit allowlist。

结论：

```text
R4_P0_SCRIPT_CLASSIFICATION = PASS
```

---

# 6. AUDIT_ONLY 不能靠文件名自我豁免

AUDIT_ONLY 现在必须显式登记并满足：

```text
runtime_authorized = false
does_not_write_accepted_heads = true
does_not_write_runtime_artifacts = true
not_called_by_production = true
attestation_basis != empty
reviewed_source_sha256 = exact current source SHA
```

scanner 会重新计算源码 SHA。

只要 audit script 被改动：

```text
reviewed_source_sha256 mismatch
→ UNCLASSIFIED_FAIL_CLOSED
```

这关闭了“先审核为 audit-only，之后偷偷改逻辑”的绕过路径。

---

# 7. Production Call Graph｜PASS

R4.1 不再仅按文件路径名称分类，而会从：

```text
src/production/daily.py
run_daily.py
```

建立 import 调用图。

正式证据：

`reports/v4_08/V4_08_R4_1_PRODUCTION_CALL_GRAPH_CLASSIFICATION.json`

状态：

```text
PASS
```

结果：

```text
reachable_node_count = 31
edge_count = 56
unresolved_required_paths = []
```

以下已明确归为 `PRODUCTION_RUNTIME`：

```text
src/phase1_runner.py
src/phase1_qa.py
src/phase2_runner.py
src/phase3_runner.py
src/phase4_runner.py
src/phase5_runner.py
```

已知真实链：

```text
run_daily
→ production.daily
→ phase1_runner
→ phase1_qa
```

上一轮“runner 名字导致误标 audit-only”的漏洞已经关闭。

---

# 8. R4 Identity Promotion 已完全泛化

`scripts/promote_v4_08_r4_inputs.py`

已经不存在：

```text
SZ.001246
SZ.301716
```

等证券 literal。

promotion set 当前根据：

```text
authorized candidate artifact
→ new_lifecycle_events
→ acceptance == CANDIDATE_PENDING_EXTERNAL_PROMOTION
→ security_id set
```

动态生成。

它不关心：

```text
证券代码是什么
新增证券有几只
```

只要求 lifecycle events 与 candidate records 一致。

允许变更字段仍严格限定：

```text
acceptance
```

---

# 9. Independent Promotion Verifier 已泛化

`scripts/verify_v4_08_r4_input_promotions.py`

也不再复制具体股票代码。

它独立使用：

```text
parent accepted artifact
candidate artifact
candidate head
external authority
generic replay
current accepted artifact
```

重算：

- parent set；
- candidate additions；
- pending lifecycle IDs；
- promoted set；
- field-level diff。

证据明确：

```text
producer_expectation_set_imported = false
```

结论：

```text
GENERIC_IDENTITY_PROMOTION = PASS
```

---

# 10. Generic Identity Promotion Equivalence

正式证据：

`reports/v4_08/V4_08_R4_1_GENERIC_IDENTITY_PROMOTION_EQUIVALENCE.json`

状态：

```text
PASS_CURRENT_IDENTITY_PROMOTION_DATA_SALVAGED
```

Generic replay SHA：

```text
4c3445f7b1337fee09e942ac854d0cefcecfc8c90c0b7432d991cadc58818ecd
```

Current accepted identity artifact SHA：

```text
4c3445f7b1337fee09e942ac854d0cefcecfc8c90c0b7432d991cadc58818ecd
```

完全一致。

这证明：

> 上一版 promotion 实现虽然用了特定股票 literal，但其数据结果没有因此被污染；泛化后的 producer 独立得到完全相同 accepted identity artifact。

因此旧 R4 identity 数据可保留，不需要因为治理实现缺陷推翻事实 artifact。

---

# 11. Generic PIT Equivalence Replay｜PASS

正式证据：

`reports/v4_08/V4_08_R4_1_GENERIC_PIT_EQUIVALENCE.json`

状态：

```text
PASS_GENERIC_PIT_EQUIVALENCE_REPLAY
```

泛化重放后仍精确得到：

## Source Revision

```text
sha256:190f9647cb8b6b610dd5336a76dc8b483e3a31439bdb0140bd95523c45905386
```

## Snapshot

```text
3dd77c68f3f29601b59d09853a70977bfab15f3fba3edeca6737f75ef9d7bcc0
```

## Fact Artifact SHA256

```text
164142652bf5b3032f4e1a8ee54fe2817a3f3b5130635cf04fb641a6e819211d
```

## Fact logical digest

```text
f29596cd59d401fc4fe8d728b3bd32324a46cc116020d64ffb70609f03a9fbc6
```

## Row count

```text
50,162
```

所有 R4 business/PIT logical result 均未因代码泛化发生改变。

---

# 12. Phase1 固定五股票 QA 已删除

旧：

```text
SAMPLES = fixed five real securities
```

已经删除。

当前：

`PHASE1_QA_SAMPLE_SELECTION_V1`

使用：

```text
current universe
+ actual cutoff bar
+ sufficient history
+ recent coverage
+ board stratification
+ stable SHA256(security_id + frozen seed)
```

动态确定。

没有随机、当前时间或人工股票名单。

当前样本数仍为 5，但：

> 选 5 只是 QA 数量合同，具体是哪 5 只由当日数据决定。

---

# 13. Phase1 QA Selector Evidence

证据：

`V4_08_R4_1_PHASE1_QA_SAMPLE_SELECTOR.json`

状态：

```text
PASS
```

当前：

```text
eligible_count = 5464
selected_count = 5
sample_checks = 145
sample_pass = true
rs_pass = true
factor_outputs_unchanged = true
```

选出的具体证券可以出现在 evidence 中，这是合法事实输出，不是代码规则。

Factor dataset SHA 保持：

```text
e5c1a5771aad89b87168c966b7c498cd22cb54bee8326d8077ff7278541a0572
```

因此 QA selector 泛化没有改变因子业务结果。

## 一个非阻塞文字问题

该 evidence 写：

```text
IN_CURRENT_ACCEPTED_UNIVERSE
```

但 source 字段实际指向 TDX `tdxhy.cfg` current universe。

建议后续改名为：

```text
IN_CURRENT_TDX_A_STOCK_UNIVERSE
```

除非未来真的改绑 V4 accepted universe。

这是 provenance label 精确性问题，不影响本轮 hardcode 治理验收。

---

# 14. Phase0 / TDX 固定真实股票代码清理

独立复查最新 HEAD：

```text
src/phase0_2_runner.py
src/phase0_2a_runner.py
src/phase0_2b_runner.py
src/tdx/tdx_audit.py
src/phase1_runner.py
scripts/promote_v4_08_r4_inputs.py
scripts/verify_v4_08_r4_input_promotions.py
```

均未再发现上一轮那些具体股票 literal。

其中市场指数：

```text
SH.000001
SZ.399001
SZ.399006
```

已经抽为：

`config/v4_market_reference_instruments_v1.json`

并明确：

```text
instrument_type = MARKET_INDEX
```

只作为市场 session / benchmark reference，不作为 stock admission / scoring / signal exception。

允许保留。

---

# 15. Governance Negative Tests

升级后的治理测试覆盖：

- production Python 直接证券比较；
- numeric stock code；
- set membership；
- governance mutation script；
- runtime JSON symbol threshold；
- SQL security-code CASE/IN；
- production-called `qa.py`；
- production-called `runner.py`。

这些 synthetic violation 必须 FAIL。

同时验证：

- TEST_ONLY fixture；
- EVIDENCE_ONLY lifecycle；
- USER_DATA Focus；
- MARKET_INDEX reference；

可以 PASS。

所以当前 hard gate 已从“扫描当前仓库”升级为“带反例的规则系统”。

---

# 16. Clean Checkout R4.1

测试 implementation commit：

```text
60a18f9ce265a36547217c48dca3f3c0b2cd50a7
```

Clean detached checkout：

```text
git clean before = true
git clean after = true
config/.env present = false
config/.env read = false
```

PostgreSQL：

```text
18.6
disposable
PROCESS_ENVIRONMENT_DSN
temporary cluster destroyed
```

Regression：

```text
643 tests
641 passed
2 skipped
0 failed
0 errors
```

结论：

```text
R4_1_CLEAN_REGRESSION = PASS
```

---

# 17. R4.1 股票代码治理正式结论

```text
V4_08_R4_1_GOVERNANCE_EXTERNAL_ACCEPTANCE_PASS
```

从本轮开始，这条应作为整个项目永久 P0：

```text
NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC
```

不得因为后续阶段变化撤销。

---

# 18. 第一张 PIT Membership Baseline 正式验收

Candidate：

`data/v4/V4_08_PIT_MEMBERSHIP_CANDIDATE_HEAD_R1.json`

精确输入：

## Source Revision Artifact

```text
data/v4/artifact_store/v4_08/
V4_08_PIT_SOURCE_REVISION_20260930_R1.json

SHA256 =
bbc1089d86c1a191a902af3145068a8409604a7e1181f8e864cb12db35854eee
```

## Snapshot Artifact

```text
V4_08_PIT_SNAPSHOT_20260930_R1.json

SHA256 =
ff28518c4f530d39574258131436c92970ebf7761fd979e932fbb6499f435bf1
```

## Fact Artifact

```text
V4_08_PIT_MEMBERSHIP_FACTS_20260930_R1.jsonl.gz

SHA256 =
164142652bf5b3032f4e1a8ee54fe2817a3f3b5130635cf04fb641a6e819211d
```

---

# 19. PIT Membership Accepted Scope

Target：

```text
2026-09-30
```

正式 rows：

```text
INDUSTRY = 5,224
THEME    = 44,938
TOTAL    = 50,162
```

Unique sectors：

```text
INDUSTRY = 110
THEME    = 268
TOTAL distinct sector IDs = 378
```

Unique formal securities：

```text
5,224
```

Raw rows：

```text
85,038
```

Excluded：

```text
BSE_OPTIONAL                           438
NON_FORMAL_SECTOR_TYPE             32,862
NOT_LISTED_AT_TARGET                   11
OPTIONAL_BOARD_OUTSIDE_REQUIRED_SCOPE 1,565
TOTAL                              34,876
```

Conservation：

```text
50,162 + 34,876 = 85,038
```

---

# 20. PIT Membership Quality / Temporal

已经验证：

```text
membership_basis = PIT_OBSERVED
membership_quality = PIT_OBSERVED_ACCEPTED
source revision basis = PIT_OBSERVED
snapshot basis = PIT_OBSERVED
fact basis = PIT_OBSERVED
identity mapped
history-safe = true
exact target-day asof
provider/system availability <= cutoff
revision chain valid
```

独立 postcheck：

```text
logical mismatch = 0
```

PostgreSQL formal view：

```text
50,162 rows
```

Determinism：

```text
PASS_TWO_IDENTICAL_MATERIALIZATIONS
```

Temporal：

```text
PASS_NO_BACKDATING_NO_CARRY_FORWARD
```

没有把 9/30 bytes 倒推成：

```text
9/28 PIT
9/29 PIT
```

---

# 21. PIT Membership 外部结论

正式批准：

```text
V4_08_PIT_MEMBERSHIP_BASELINE_EXTERNAL_ACCEPTANCE_PASS_R1
```

允许创建：

```text
data/v4/V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1.json
```

并将：

```text
first accepted forward PIT membership date = 2026-09-30
```

正式登记。

但这个 scoped head 只能授权：

```text
V4_08 PIT membership input
```

不能等价成：

```text
V4_08 Sector / Rotation Core 整体完成
```

---

# 22. 为什么 V4-08 总阶段仍不能 PASS

最新版合同 §78：

```text
V4-08 | Sector / Rotation Core
交付：
共同成员、B0/B1/B2、纯Core legacy sector资格adapter
```

因此 V4-08 不等于：

```text
membership baseline only
```

当前仍有实质缺口。

---

# 23. Blocker A｜五个 V4-08 retention 参数仍为 null

`config/v4_08_algorithm_parameter_set_v1.json`

当前：

```text
status = FROZEN_ENGINEERING_CANDIDATE
formal_consumer_enabled = false
```

以下五个参数仍为 null：

```text
V4_08_EARLY_SEED_RETENTION_MIN
V4_08_EARLY_BREADTH_RETENTION_MIN
V4_08_EARLY_BREADTH_DELTA_MIN
V4_08_EARLY_TOP1_CONCENTRATION_MAX
V4_08_MATURE_STRONG_RETENTION_MIN
```

合同 §21A.4 / §72 明确：

```text
V4-08 阶段冻结后才正式消费
未赋值不能取得正式消费者权限
```

所以这是 V4-08 正式算法 completion blocker。

不能：

```text
继续偷用 0.5
```

也不能为了赶进度拍脑袋填值。

---

# 24. Blocker B｜B2 Legacy Adapter 尚未实现

`config/v4_08_sector_legacy_adapter_contract_v1.json`

当前明确：

```text
legacy_extraction.status =
NOT_IMPLEMENTED_PENDING_EXACT_SOURCE_AST_AND_GOLDEN_SAMPLES
```

且：

```text
formal_consumer_enabled = false
```

合同 §78 又明确要求 B2。

因此：

```text
B2 = REQUIRED_BUT_NOT_IMPLEMENTED
```

必须完成：

- exact legacy source path；
- function/symbol；
- source SHA；
- call graph；
- parameters；
- input units/time；
- UNKNOWN semantics；
- pure-Core AST；
- golden samples；
- independent expected outputs。

---

# 25. Blocker C｜Sector Native 仍只是合同候选

`config/v4_08_sector_native_contract_v1.json`

当前：

```text
status = FROZEN_ENGINEERING_CANDIDATE
formal_consumer_enabled = false
full_market_materialization_enabled = false
```

目前 `src/sector/` 主要存在：

```text
membership primitives
machine_ast_r3
old phase2 current-membership aggregates
synthetic rotation-vector helper
```

尚未看到完成正式：

```text
V4_08_SECTOR_NATIVE_V1
```

全市场 producer 的实现。

旧：

`src/sector/phase2.py`

仍明确：

```text
BASIS = CURRENT_TDX_MEMBERSHIP
```

不能直接冒充 V4-08 PIT producer。

---

# 26. Blocker D｜B0/B1 仍以 AST / synthetic engineering 为主

B0：

`V4_08_SECTOR_PREWATCH_B0_V2`

已经拥有结构化 AST，这是好事。

B1：

`ROTATION_CORE_V1_R3`

四态语义也已经正确。

但当前：

```text
formal_consumer_enabled = false
```

并且：

`v4_08_rotation_vectors.py`

仍是：

```text
synthetic vectors
production_authorized = false
```

所以目前是：

```text
contract/AST engineering complete enough
```

但不是：

```text
formal full-market algorithm producer complete
```

---

# 27. Prior-RPS 继续是独立上游降级，不应阻塞全部 R5

V4-07 Prior-RPS repair 仍 OPEN。

这意味着：

```text
Base Seed real signal
Seed Width
seed-dependent sector fields
```

现实输入仍可能：

```text
UNKNOWN / DEGRADED_BY_UPSTREAM_BASE_SEED_SIGNAL
```

但不能因此停止 V4-08 开发。

R5 应继续实现：

- membership-driven sector primitives；
- non-seed primitives；
- common-member calculations；
- B0/B1 evaluator；
- B2 adapter；
- parameter binding；
- persistence。

对 Seed-dependent field：

```text
UNKNOWN
```

即可，禁止造值。

---

# 28. V4-08 当前唯一总状态

```text
PIT MEMBERSHIP BASELINE
=
EXTERNALLY ACCEPTED

NO-SYMBOL-SPECIAL-CASE GOVERNANCE
=
EXTERNALLY ACCEPTED

SECTOR / ROTATION CORE ALGORITHM
=
INCOMPLETE

V4_08 FINAL STAGE ACCEPTANCE
=
BLOCKED
```

正式状态：

```text
V4_08_STAGE_EXTERNAL_ACCEPTANCE_BLOCKED_ALGORITHM_COMPLETION_REQUIRED
```

---

# 29. 下一步

直接进入：

```text
V4_08_R5
Sector / Rotation Core
Implementation + Parameter Freeze + B2 Extraction
```

不要回头重做：

- PIT membership；
- R4.1 symbol governance；
- source-time policy；
- identity/calendar；
- 11-key lifecycle；
- migration 019；
- four-state N/A semantics。

---

# 30. R5 完成后的可接受模式

如果 R5 工程、参数、B2、producer 全部完成，但真实数据仍因为：

- Prior-RPS；
- 第一张 PIT membership 尚无 t-1 PIT history；
- forward accumulation 不足；

导致部分 real signal 为 UNKNOWN，这不应无限阻塞工程升级。

可以采用：

```text
V4_08_EXTERNAL_ACCEPTANCE_PASS_ENGINEERING_SCOPE_DEGRADED_REAL_SIGNAL
```

前提：

> UNKNOWN 是被正式数据能力声明造成，而不是代码/合同/参数尚未实现。

然后可以继续 V4-09，同时真实 Forward 数据继续积累。

---

# 31. 最终结论

```text
V4_08_R4_1_GOVERNANCE_EXTERNAL_ACCEPTANCE_PASS
```

```text
V4_08_PIT_MEMBERSHIP_BASELINE_EXTERNAL_ACCEPTANCE_PASS_R1
```

```text
V4_08_STAGE_EXTERNAL_ACCEPTANCE_BLOCKED_ALGORITHM_COMPLETION_REQUIRED
```

**可以接受第一张真实 PIT membership，但不能提前宣布整个 V4-08 已完成。**
