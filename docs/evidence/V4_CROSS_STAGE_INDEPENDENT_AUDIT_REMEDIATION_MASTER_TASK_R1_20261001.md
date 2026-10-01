# V4 跨阶段独立审计遗留问题并行修复总任务卡｜2026-10-01

**文档编号：** DA-MSR-V4-CROSS-STAGE-INDEPENDENT-AUDIT-REMEDIATION-MASTER-R1-20261001  
**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**任务性质：** 跨阶段独立审计遗留项正式修复 / 并行能力补全  
**审计基线 HEAD：** `db6319856468c6788c9dd656da3992e569a64572`  
**当前 Stage Accepted Range：** `V4_00_TO_V4_09_ACCEPTED`  
**当前 Data Accepted Head：** `2026-09-24`  
**当前 V4-10：** 独立走 R1.2 interface authority 修复，不由本任务卡替代  
**总原则：** 工程主线继续推进；遗留能力并行修复；不得用长期真实样本积累阻塞后续开发

---

# 0. 为什么必须补这张任务卡

此前多轮独立外部审计已经识别出若干跨阶段 OPEN 问题，但其中一部分只被记录为：

```text
OPEN AUDIT
DEGRADED CAPABILITY
DIAGNOSTIC ONLY
BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
```

没有被正式转成可执行 Codex 任务。

这会产生一个项目治理问题：

> “知道有问题”不等于“问题进入正式修复流程”。

因此本任务卡将所有已经被独立审计确认、且截至本轮仍未正式关闭的遗留项统一纳入可执行修复队列。

---

# 1. 本任务卡覆盖范围

当前共覆盖 9 条正式遗留线：

```text
A01 DM01_REAL_INCREMENTAL_BUILDERS
A02 V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01
A03 FORWARD_PIT_HISTORY_ACCUMULATION
A04 AUD-AMOUNT-A-06
A05 LEGACY_VALID_MEMBER_EXACT_PRODUCER
A06 V4-06-BAOSTOCK-BINDING-TOLERANCE-01
A07 HISTORICAL_AS_RECORDED_ADJUSTED_PRICE
A08 AUD-V4-09-REPAIR-FREEZE-SELF-VALIDATION-N01
A09 AUD-V4-09-DB-CONSUMER-IDENTITY-N02
```

---

# 2. 与当前 V4-10 R1.2 的关系

本任务卡与：

```text
V4_10_R1_2_EXTERNAL_REAUDIT_REPAIR_TASK_20261001.md
```

是**两条并行线**。

## 主工程线

继续：

```text
V4-10 修复
→ V4-10 外部接受
→ V4-11
→ V4-12
→ V4-13
→ V4-14 Replay Gate B
→ V4-15 Settlement/Validation
→ 前端 / Focus / Production Cutover
```

## 遗留能力修复线

并行推进：

```text
A01-A09
```

### 硬规则

不得再次出现：

```text
“等 20 个交易日数据”
“等所有真实信号跑完”
“等 PIT 积累完成”
```

才允许后续工程开发的情况。

这些 OPEN 项：

- **不反向撤销已经通过的工程阶段；**
- **不阻塞不依赖它们的下一阶段编码；**
- 但到对应真实能力、Replay Gate B、Production Cutover 时必须按 scope 关闭。

---

# 3. 优先级总表

| 优先级 | Audit | 当前问题 | 当前影响 |
|---|---|---|---|
| P0 | A01 DM-01 | 9 个 accepted target-date builder adapter 未接通 | Data Head 卡在 2026-09-24 |
| P0 | A02 Prior-RPS | Accepted delta1/delta3 全量 bootstrap UNKNOWN | Base Seed / PREWATCH real signal 降级 |
| P1 | A03 Forward PIT | 只有首个 accepted PIT date，历史长度不足 | Temporal sector consumers 不完整 |
| P1 | A04 Amount A | 单位/分母/coverage/concentration 未独立接受 | Amount-A formal consumers 禁用 |
| P1 | A05 Legacy Valid Member | exact missing_state producer 不存在 | B2 non-Amount 未实现 |
| P2 | A06 BaoStock strict binding | amount 指纹/单位/分母/tolerance 未接受 | BaoStock strict bound 禁用 |
| P2 | A07 Historical AS_RECORDED | 缺 first-availability 证据 | 历史 adjusted replay 禁用 |
| P2 | A08 V4-09 N01 | repair freeze 自验证 authority 不足 | Production/shadow 前 hardening |
| P2 | A09 V4-09 N02 | migration 021 consumer identity 不显式 | 多 consumer 共存治理风险 |

推荐执行顺序：

```text
A01
↓
A02

A03 从现在开始持续积累，不等待 A01 全部结束
A04 / A05 可与 A01-A02 并行
A08 / A09 属短平快 hardening，可穿插完成
A06 / A07 不阻塞主工程线，但必须在生产总验前关闭或维持明确 capability blocked
```

---

# 4. A01｜P0｜DM01_REAL_INCREMENTAL_BUILDERS

## 4.1 当前事实

当前：

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
accepted_trade_date = 2026-09-24
```

截至本任务卡，正式 Stage 已推进到 V4-09，但 Data Accepted Head 仍停留在 2026-09-24。

当前：

```text
config/v4_dm01_accepted_builder_registry_v1.json
status = BLOCKED_TARGET_DATE_ADAPTER_APIS_MISSING
```

9 个 required capabilities：

```text
RAW_DAILY
IDENTITY_UNIVERSE
TRADING_STATUS
ISST
ADJUSTED_DAILY
PERIOD_RAW
PERIOD_ADJUSTED
PRICE_LIMIT
SPECIAL_PHASE
```

全部缺正式 target-date incremental adapter。

---

# 5. A01 修复目标

不是重新实现 9 套算法。

目标是：

> 把已经接受的 V4-01 / V4-02 domain runtime 封装为严格 target-date adapter，并接入 DM-01 staging → postcheck → atomic Data Head promotion。

禁止：

```text
复制旧算法重新写一份
为了方便直接跑 frozen historical CLI
使用 test/fake/fallback builder
未经 accepted contract 重新发明公式
```

---

# 6. A01 每个 adapter 的统一接口

建议统一：

```python
build_<capability>(
    target_trade_date,
    parent_data_head,
    accepted_source_freeze,
    accepted_calendar,
    accepted_identity_lineage,
    output_dir
) -> ComponentCandidate
```

每个 candidate 至少返回：

```text
contract_id
trade_date
parent_head_digest
source_revision
input_publication_ids
runtime_bindings
artifact_path
artifact_sha256
logical_digest
row_count
quality_counts
unknown_reason_counts
postcheck_digest
```

---

# 7. A01 九个 builder 逐项要求

## RAW_DAILY

使用 accepted：

```text
date_identity
check_raw_quality
TDX_PACKAGE_DELTA_V1
CURRENT_LIFECYCLE_SNAPSHOT_V1
```

输出目标日 canonical raw rows。

不得重新扫整段历史替代 incremental contract。

## IDENTITY_UNIVERSE

绑定：

```text
parent accepted universe
BaoStock roster
official session bridge
dated identity records
build_current_lifecycle_snapshot()
```

absence 不能自动当 delisting。

## TRADING_STATUS

将历史 CLI 中 accepted domain logic 抽出 callable。

必须保留：

```text
local TDX bar precedence
explicit source
explicit unknown
```

## ISST

将 accepted dated ST logic 抽出 target-date callable。

不得把当前 ST 状态回填历史。

## ADJUSTED_DAILY

绑定：

```text
target raw row
accepted GBBQ snapshot
per-security adjustment disposition
build_affine_factors
adjust_ohlc
```

unsupported action 继续 fail-closed。

## PERIOD_RAW

实现：

```text
parent period state
+
target daily session
```

的增量 weekly/monthly aggregator。

## PERIOD_ADJUSTED

同上，但只消费 accepted adjusted daily。

## PRICE_LIMIT

target-date wrapper 必须调用 accepted：

```text
run_builder / apply_row_runtime
```

不得新写涨跌停公式。

## SPECIAL_PHASE

绑定：

```text
CURRENT_LIFECYCLE_SNAPSHOT
SPECIAL_PHASE_SOURCE_MANIFEST
accepted event store
accepted policy
```

无事件时必须产生可审计 no-event manifest。

---

# 8. A01 Data Head promotion

只有 9 个 component 全部：

```text
PASS / explicit DEGRADED_PASS
```

且 independent postcheck 完成后才允许：

```text
V4_DATA_ACCEPTED_HEAD
2026-09-24
→ target_trade_date
```

不得移动：

```text
V4_STAGE_ACCEPTED_HEAD
```

Data Head 与 Stage Head 必须继续独立。

---

# 9. A01 验收

至少：

```text
DM01_A01_G01 all 9 adapters exported
DM01_A01_G02 exact accepted runtime binding
DM01_A01_G03 parent head binding
DM01_A01_G04 target-only input
DM01_A01_G05 deterministic replay
DM01_A01_G06 overlap source check
DM01_A01_G07 failure leaves head unchanged
DM01_A01_G08 partial component failure atomic rollback
DM01_A01_G09 clean detached E2E
DM01_A01_G10 real next available completed session candidate
DM01_A01_G11 independent external acceptance
```

---

# 10. A02｜P0｜Prior-RPS Accepted Bootstrap

## 10.1 当前事实

Accepted V4-05 factors 对 5,222 identities：

```text
rps5_delta1
rps5_delta3
rps20_delta3
```

当前均因：

```text
BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY
```

大量/全量 UNKNOWN。

禁止使用旧 V4-03 staging RPS 值回填。

---

# 11. A02 修复目标

建立：

```text
Accepted PIT RPS History Chain
```

而不是在 V4-07 内部现场重算 prior history。

明确公式继续冻结：

```text
rps5_delta1  = rps5[t]  - rps5[t-1]
rps5_delta3  = rps5[t]  - rps5[t-3]
rps20_delta3 = rps20[t] - rps20[t-3]
```

---

# 12. A02 具体任务

新增 versioned publication，例如：

```text
V4_RPS_PIT_HISTORY_V1
```

每个 T 至少保存：

```text
security_id
trade_date
rps5
rps20
source_factor_publication_id
source_universe_id
calendar_id
publication_at
knowledge_cutoff
artifact_digest
```

delta producer 必须显式绑定：

```text
T
T-1
T-3
```

对应 accepted publication。

第一可用日期必须由真实 warm-up 计算得到。

---

# 13. A02 禁止项

禁止：

```text
把 UNKNOWN 当 FALSE
使用未 accepted R3 staging
使用未来 T+1/T+3 数据
在 V4-07 内部偷偷读 raw bars 重建 prior
修改 V4-07 thresholds
为了生成候选强行填 0
```

---

# 14. A02 验收

至少独立抽样重算：

```text
T
T-1
T-3
```

并覆盖：

```text
first available
missing prior
new listing
suspension gap
identity change
calendar gap
same-day revision
universe entry/exit
```

完成后：

1. 发布新 accepted RPS history publication；
2. 重新运行 V4-07；
3. 报告 real signal capability 改变；
4. 不修改 V4-07 已接受算法参数。

---

# 15. A03｜P1｜FORWARD_PIT_HISTORY_ACCUMULATION

## 15.1 当前事实

已 accepted：

```text
first_accepted_trade_date = 2026-09-30
V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1
```

这只证明首个 go-forward PIT snapshot 已建立。

不能伪造 2026-09-30 之前的 PIT knowledge history。

---

# 16. A03 修复目标

从首个 accepted PIT date 开始，每个完成交易日持续产生 immutable：

```text
source capture
source revision
snapshot
facts
accepted head
```

形成真实：

```text
T0
T1
T2
...
```

历史链。

---

# 17. A03 必须自动化

不得依赖人工每天提醒。

实现：

```text
forward_pit_daily_builder
gap detector
revision detector
late source detector
immutable append
daily acceptance candidate
```

注意：

Codex 可以完成自动化开发。

真实未来日期的数据只能自然积累，不得伪造。

---

# 18. A03 工程与样本分离

代码实现 / contract / replay / synthetic calendar：

```text
可以立即完成并验收
```

真实 N 日 PIT history：

```text
持续积累
```

不因为真实样本尚未达到 N 天阻塞 V4-11/V4-12 等工程阶段。

---

# 19. A04｜P1｜AUD-AMOUNT-A-06

当前：

```text
diagnostic use only
formal consumer authorization = false
```

必须解决四层问题：

```text
source
unit
denominator
coverage/concentration
```

---

# 20. A04 修复要求

## Source

明确 Amount A 的唯一 source field。

## Unit

独立验证：

```text
元 / 千元 / 万元
volume unit
amount unit
```

不得靠经验猜。

## Denominator

明确 20-session denominator：

```text
calendar sessions?
valid trading sessions?
common-member sessions?
security available sessions?
```

冻结为 contract。

## Coverage

必须输出：

```text
member_count
valid_member_count
coverage
missing_reason_counts
```

## Concentration

独立重算 concentration arithmetic。

---

# 21. A04 Consumer Audit

全仓扫描所有 Amount A consumer：

```text
qualification
ranking
sector
PREWATCH
Focus
homepage
future FEP
```

只要 audit 未通过：

```text
Amount-A-dependent formal path = disabled
```

不得通过 fallback value 间接启用。

---

# 22. A05｜P1｜LEGACY_VALID_MEMBER_EXACT_PRODUCER

当前：

```text
legacy_valid_member_rows = 0
producer_implemented = false
```

缺失的是 legacy exact：

```text
missing_state
```

producer。

不得使用：

```text
trading_status
bar exists
universe membership
PIT membership
```

简单替代。

---

# 23. A05 方案门

Codex 必须先做 source archaeology。

只有两种正式结果：

## Option A｜Exact Producer

找到 legacy source / formula，完整实现：

```text
missing_state
validity(total, valid, role)
```

并给 golden examples。

## Option B｜Formal Replacement Contract

如果 legacy missing_state 无法真实恢复：

必须明确发布：

```text
LEGACY_VALID_MEMBER_REPLACEMENT_V1
```

说明：

- 与 legacy 不等价；
- 哪些场景改变；
- 哪些旧 B2 能力永久废弃；
- 新 consumer 如何迁移。

禁止：

```text
“大概等价”
```

然后恢复 B2。

---

# 24. A06｜P2｜BaoStock Strict Binding

当前 live probe：

```text
target_rows_observed = 4
strict_bound_row_count = 0
```

主要问题：

```text
close match
volume match
amount mismatch
field semantics not independently accepted
denominator semantics not independently accepted
tolerance not frozen
```

---

# 25. A06 修复要求

至少建立 representative matrix：

```text
SH main
SZ main
ChiNext
STAR
不同成交规模
不同换手水平
多日期
```

每个样本独立对比：

```text
close
volume
amount
turn
tradestatus
isST
```

并确认：

```text
BaoStock official field unit
local field unit
normalization transform
circulating-share denominator semantics
```

只有在独立证据充分后才能 freeze：

```text
BAOSTOCK_STRICT_BINDING_TOLERANCE_V1
```

---

# 26. A06 禁止

禁止为了让 fingerprint 通过而：

```text
随便设 1%
0.1%
100 元
1000 元
```

容差。

Tolerance 必须从：

```text
单位/浮点/来源生成机制
```

导出，而不是拟合样本。

---

# 27. A07｜P2｜Historical AS_RECORDED Adjusted Price

当前：

```text
HISTORICAL_AS_RECORDED_ADJUSTED_PRICE
= BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE
```

这不是 adjustment formula 本身错误。

问题是：

> 不知道今天看到的 corporate-action / adjustment knowledge 在历史 T 当时是否已经可得。

---

# 28. A07 修复目标

需要建立：

```text
first_available_at
source_revision
knowledge_time
```

而不是只建立：

```text
effective_date
```

至少针对：

```text
GBBQ corporate action record
provider adjustment record
manual disposition
```

给出 first availability lineage。

---

# 29. A07 结果允许两种

## PASS

历史 first-availability evidence 足够：

```text
HISTORICAL_AS_RECORDED = ACCEPTED
```

## 保持 BLOCKED

证据无法恢复：

```text
HISTORICAL_AS_RECORDED = PERMANENTLY_UNVERIFIABLE_FOR_PRE_CAPTURE_HISTORY
```

这也是合法最终结论。

禁止事后根据 today-known corporate actions 回写成“历史当时已知”。

---

# 30. A08｜P2｜V4-09 N01 Repair Freeze Self Validation

Audit：

```text
AUD-V4-09-REPAIR-FREEZE-SELF-VALIDATION-N01
```

目标：

独立拒绝：

```text
self-consistent wrong repair identity
wrong authority
wrong binding set
wrong immutable writer consumer
```

---

# 31. A08 修复要求

对：

```text
src/v4/stock_prewatch.py::load_package
```

建立独立 negative vectors：

```text
wrong repair status
wrong accepted authority
missing binding
extra binding
same digest shape but wrong file
wrong consumer identity
wrong amended V4-08 parent
```

要求：

```text
V4-09 accepted replay output byte/logical digest 不变化
```

只做 hardening，不改算法。

---

# 32. A09｜P2｜V4-09 N02 DB Consumer Identity

Audit：

```text
AUD-V4-09-DB-CONSUMER-IDENTITY-N02
```

问题：

migration 021 publication identity 缺显式：

```text
consumer_contract_id
```

对未来多 consumer 共存不够强。

---

# 33. A09 修复要求

禁止修改 migration 021。

新增版本化 migration，例如：

```text
025/026_v4_09_consumer_identity_hardening.sql
```

具体编号按执行时未占用序号决定。

必须支持：

```text
old rows readable
append-only preserved
consumer A/B cannot collision
same publication different consumer rejected
revision identity preserved
rollback exact
```

---

# 34. 统一工程纪律

A01-A09 全部遵守：

```text
不重写 Accepted Head
不静默覆盖旧 artifact
不修改已接受历史 migration
不把旧 staging 提升成 accepted
不因测试 PASS 自动声称 external acceptance
不开放 production/shadow/Focus permission
```

---

# 35. 统一 OPEN Audit Registry

新增：

```text
reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json
```

建议字段：

```json
{
  "audit_id": "...",
  "priority": "P0",
  "status": "OPEN|IMPLEMENTED_PENDING_EXTERNAL_ACCEPTANCE|ACCEPTED|BLOCKED_PERMANENT",
  "owner_module": "...",
  "depends_on": [],
  "does_not_block_engineering_stage": true,
  "production_gate": true,
  "evidence": [],
  "external_acceptance": null
}
```

---

# 36. 不允许“一次提交全部宣告完成”

本任务卡是 Master Card。

Codex 应分 Work Package 提交：

```text
WP-A01-DM01
WP-A02-PRIOR-RPS
WP-A03-FORWARD-PIT
WP-A04-AMOUNT-A
WP-A05-LEGACY-VALID-MEMBER
WP-A06-BAOSTOCK
WP-A07-HIST-AS-RECORDED
WP-A08-V4-09-N01
WP-A09-V4-09-N02
```

每个 WP：

```text
实现
测试
evidence
clean regression
candidate closure
STOP for independent external audit
```

不得 Codex 自己关闭 external acceptance。

---

# 37. 推荐实际推进顺序

## Batch 1｜立即执行

```text
A01 DM01
A08 N01
A09 N02
```

原因：

- A01 是真实每日运行基础；
- N01/N02 体量较小，可顺手清技术债。

## Batch 2｜A01 主体完成后

```text
A02 Prior-RPS
```

但 contract / schema / tests 可以提前写。

## Batch 3｜并行持续

```text
A03 Forward PIT accumulation
```

从每个真实交易日自动积累。

## Batch 4｜并行算法能力

```text
A04 Amount A
A05 Legacy Valid Member
```

## Batch 5｜外部 source / 历史证据

```text
A06 BaoStock
A07 Historical AS_RECORDED
```

---

# 38. 与后续 Stage 的门关系

## V4-10 / V4-11 / V4-12

不要求 A01-A09 全部关闭后才能编码。

## V4-14 Replay Gate B

必须重新汇总：

```text
A01
A02
A03
A04
A05
```

对应能力状态。

如果未关闭：

```text
相应 capability fail-closed
```

不得假装 FULL PASS。

## Production Cutover

至少必须确认：

```text
A01 closed
A08 closed
A09 closed
```

并对：

```text
A02-A07
```

给出：

```text
ACCEPTED
或
明确 capability disabled / permanent blocked
```

生产不得隐式依赖未接受能力。

---

# 39. Master Card 完成标准

本 Master Card 本身不以：

```text
9/9 audit 全部 accepted
```

作为一次性完成条件。

Master Card 的治理完成条件是：

1. A01-A09 全部进入正式 registry；
2. 每个有 owner；
3. 每个有 task/evidence path；
4. 每个有 external acceptance gate；
5. 每个不再只是聊天结论；
6. 每个后续状态更新可追踪；
7. 任何未关闭项都不能被 production path 静默使用。

---

# 40. Codex 本轮首次执行要求

拿到本任务卡后，第一轮只做：

```text
1. 创建统一 remediation registry；
2. 为 A01-A09 建立正式 work package 目录/状态；
3. 对 A01 做 implementation entry；
4. 对 A08/A09 做 implementation entry；
5. 不得直接声称所有问题已修复。
```

然后优先开始：

```text
WP-A01-DM01
```

---

# 41. 首轮必须产出

```text
reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json

docs/evidence/V4_CROSS_STAGE_REMEDIATION_MASTER_ENTRY_20261001.md

reports/dm01/DM01_INCREMENTAL_BUILDERS_REPAIR_ENTRY_R1.json

reports/v4_09/V4_09_N01_HARDENING_ENTRY_R1.json
reports/v4_09/V4_09_N02_CONSUMER_IDENTITY_ENTRY_R1.json
```

并给：

```text
当前实现状态
代码修改计划
dependency graph
预计需要真实时间积累的项
可以立即完成工程验收的项
```

注意：

禁止给时间估算天数。

---

# 42. 一句话总纲

```text
之前独立审计发现的 OPEN 问题不能只留在 audit register。

从现在开始：
主工程线继续推进，
A01-A09 正式进入并行修复线。

优先先把 DM-01 真正接通，让 Data Accepted Head 能按交易日推进；
随后建立 accepted prior-RPS 历史；
Forward PIT 自动持续积累；
Amount A / Legacy Valid Member 独立修复；
BaoStock / Historical AS_RECORDED 保持严格证据门；
V4-09 N01/N02 在 Production 前完成 hardening。

任何 OPEN capability 都不得偷偷进入正式生产路径。
```

---

# 43. 当前正式状态

```text
CROSS_STAGE_REMEDIATION_MASTER = AUTHORIZED_TO_START
OPEN_AUDIT_COUNT = 9

MAIN_ENGINEERING_LANE = CONTINUE
REAL_DATA_ACCUMULATION = PARALLEL
WAIT_FOR_20_TRADING_DAYS_BEFORE_DEVELOPMENT = FORBIDDEN

FIRST_WORK_PACKAGE = WP-A01-DM01
PARALLEL_QUICK_HARDENING = WP-A08 + WP-A09
```
