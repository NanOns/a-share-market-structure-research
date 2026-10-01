# A12｜V4-02 Trading Status / ST Source Authority + Downstream Cascade 修复任务卡 R1｜2026-10-01

**Work Package：** `WP-A12-V4-02-STATUS-ST-AUTHORITY`  
**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**基线 HEAD：** `4e5284f74c5275e28d75985d1c3e60eaf96e4103`  
**优先级：** P0 Source Authority Repair  
**性质：** 修正 V4-02 formal producer 与 Master Source Authority Matrix 的冲突；随后按 business digest 做最小下游级联复验。

---

# 1. 已确认问题

REV2/REV4 总合同均规定：

```text
Trade Status
formal authority = accepted local security master + TDX/calendar
BaoStock = cross-check

ST
formal authority = accepted local dated identity
BaoStock = cross-check
```

但当前 V4-02 实现：

```text
local bar missing + BaoStock tradestatus=0
→ formal SUSPENDED

local bar missing + BaoStock tradestatus=1
→ formal DATA_GAP

BaoStock isST
→ formal is_st
→ price-limit risk status
```

这是明确的：

```text
CONTRACT_RUNTIME_SOURCE_ROLE_DIVERGENCE
```

---

# 2. 已知影响规模

当前 Trading Status receipt：

```text
membership rows = 4,036,121
ACTUAL_TRADED   = 4,027,002
SUSPENDED       = 9,119
missing bar rows = 9,119
missing securities = 982
```

这 9,119 个无本地 bar 日期的 formal `SUSPENDED` 由 BaoStock `tradestatus` 决定。

另：

```text
V4_02_DATED_ST_STATUS
```

以 BaoStock date-level `isST` 为 formal output。

因此不能把本次修复当作 metadata-only。

---

# 3. 第一阶段必须先做 Source Archaeology，不得直接改公式

先建立：

```text
V4_02_STATUS_ST_AUTHORITY_INVENTORY_R1
```

检查所有潜在本地/官方 source：

```text
TDX .day actual bar
TDX TNF security master / names
TDX local metadata
calendar
accepted V4-01 identity/lifecycle
official exchange suspension/resumption evidence
official risk-warning/ST evidence
existing source evidence
BaoStock provider facts
```

逐字段说明：

```text
能证明什么
不能证明什么
是否 dated
是否 historical-queryable
是否 mutable-current-only
是否 accepted
```

---

# 4. Trading Status 正式语义

硬规则：

```text
local TDX actual bar present
→ ACTUAL_TRADED
```

BaoStock 冲突：

```text
只记录 conflict
不能推翻 local actual bar
```

对 local bar missing：

不得默认：

```text
BaoStock 0 → formal SUSPENDED
```

除非经过本任务独立 source-semantics acceptance 并正式修改 owner contract。

---

# 5. Trading Status 两条允许路径

## Path A｜Current Master Contract

建立：

```text
LOCAL_DATED_TRADING_STATUS_V2
```

例如：

```text
actual bar present
→ ACTUAL_TRADED

bar absent + accepted local/official dated suspension evidence
→ SUSPENDED

bar absent + accepted evidence explicitly proves should trade
→ DATA_GAP

otherwise
→ UNKNOWN
```

BaoStock：

```text
provider_tradestatus
→ crosscheck only
```

## Path B｜Field-Level Authority Amendment

如果证明历史 suspension 事实无法由本地/官方稳定生产，而 BaoStock `tradestatus`：

```text
字段语义明确
目标日期可重查
revision 行为明确
独立样本与官方 suspension 对照通过
```

则提交：

```text
TRADE_STATUS_FIELD_AUTHORITY_AMENDMENT_PROPOSAL
```

必须先独立外部接受后，才能让 BaoStock 成为该字段 owner。

禁止开发方自行改 Master Contract 后继续。

---

# 6. ST 正式语义

同样两条路径。

## Path A｜Local / Official dated ST authority

建立：

```text
LOCAL_DATED_ST_IDENTITY_V2
```

来源必须能证明：

```text
effective_from
effective_to
ST / *ST / risk-warning state
```

不能使用当前名称回填整个历史。

## Path B｜Explicit provider authority amendment

若只能依赖 BaoStock `isST`：

必须独立验证：

```text
field semantics
historical date semantics
provider revision
ST/*ST/risk-warning coverage
suspension days
code-change aliases
official sample reconciliation
```

再通过正式 contract amendment 授权。

在此之前：

```text
BaoStock isST = CROSSCHECK_ONLY
```

---

# 7. Price Limit 必须跟随 corrected ST producer

当前：

```text
is_st == 1 → RISK_WARNING
is_st == 0 → NORMAL
```

修复后：

```text
price-limit builder
```

只能读取 A12 外部接受后的 formal ST producer。

如果 ST UNKNOWN：

```text
risk status = UNKNOWN
price-limit result按现有 fail-closed contract UNKNOWN
```

不得 fallback 到 BaoStock。

---

# 8. 历史补抓与 knowledge-time

即使本任务允许后来查询：

```text
BaoStock date=T
official archived notice for T
```

必须记录：

```text
fact_effective_date = T
observed_at = actual later time
lineage = RECONSTRUCTED_CORRECTED
```

不得自动写：

```text
AS_RECORDED_AT_T
first_available_at = T
```

所以 A12 不会自动关闭：

```text
A07 HISTORICAL_AS_RECORDED
```

---

# 9. 重建 V4-02 受影响 artifacts

禁止覆盖旧文件。

至少版本化产生：

```text
V4_02_DATED_TRADING_STATUS_AUTHORITY_R1
V4_02_DATED_ST_STATUS_AUTHORITY_R1
V4_02_PRICE_LIMIT_AUTHORITY_R1
```

以及：

```text
old-vs-new row diff
reason transition counts
security/date samples
logical digests
```

必须单独统计：

```text
old SUSPENDED → new SUSPENDED
old SUSPENDED → UNKNOWN
old SUSPENDED → DATA_GAP

old ST 0/1 → same
old ST 0/1 → UNKNOWN
old ST conflict
```

---

# 10. V4-03 Impact Gate

先做 exact dependency scan。

已知 V4-03 core formula 未直接使用：

```text
is_st
risk_status
limit_status
```

但仍要验证：

```text
accepted daily input business rows
factor input digest
```

如果 corrected V4-02 没改变 V4-03 consumed business fields：

```text
V4_03 = NO_REBUILD
lineage revalidation only
```

否则才重跑 unchanged V4-03。

---

# 11. V4-04 必须真实重算

V4-04 明确消费 `trading_status`。

`technical_window_status()` 当前要求：

```text
窗口 calendar dates 全覆盖
actual bars == ACTUAL_TRADED dates
其余必须 SUSPENDED
```

因此 A12 必须用 corrected status 真正重跑 V4-04 unchanged algorithms。

输出：

```text
old COMPLETE/PARTIAL_UNKNOWN
new COMPLETE/PARTIAL_UNKNOWN

field-level change counts
state-level change counts
security-level change count
logical digest diff
```

不得仅做 schema test。

---

# 12. V4-05 必须按 V4-04 diff 决定处理

若 V4-04 business output 变化：

```text
重跑 V4-05 Replay Gate A unchanged
```

若只 lineage/digest 变化且业务 bytes 等价：

```text
做 lineage amendment / rebind
```

必须独立证明等价。

---

# 13. V4-07 / V4-08 / V4-09 Conditional Cascade

按依赖图：

```text
V4-04
↓
V4-05
↓
V4-07 Base Seed
↓
V4-08 sector/rotation context
↓
V4-09 PREWATCH
```

只有上游 accepted business/logical identity 变化时才继续 cascade。

硬规则：

```text
算法参数不变
阈值不变
不能借 repair 改信号数量
```

每一级都输出：

```text
INPUT_DIGEST_CHANGED?
BUSINESS_OUTPUT_CHANGED?
REBUILD_REQUIRED?
```

---

# 14. Accepted Head 治理

禁止覆盖：

```text
V4_02_ACCEPTED_HEAD
V4_04_ACCEPTED_HEAD
V4_05_ACCEPTED_HEAD
V4_07_ACCEPTED_HEAD
V4_08_ACCEPTED_HEAD_AMENDED_R1
V4_09_ACCEPTED_HEAD
```

如果结果改变：

```text
新建 *_ACCEPTED_HEAD_AMENDED_Rx
```

并由 Global Stage 在独立外部接受后显式 supersede。

如果结果不变：

```text
只追加 authority reconciliation evidence
```

不伪造 business revision。

---

# 15. 与 DM01 R2 的关系

**DM01 R2 暂时不要先执行 status/ST 部分。**

A12 必须先冻结：

```text
正式 Trading Status producer contract
正式 ST producer contract
```

之后 DM01：

```text
只封装 accepted producer
```

不得独立发明：

```text
BaoStock missing 时自己如何判断 suspension/ST
```

DM01 可并行修 runtime capability / historical catch-up，但最终 all-nine candidate 必须绑定 A12 的 accepted owner contract。

---

# 16. Required Independent Samples

Trading Status 至少：

```text
正常交易日
真实停牌日
停牌后复牌
无 bar 数据缺口
BaoStock/local conflict
代码变更边界
新上市
退市/长期停牌边界
```

ST 至少：

```text
NORMAL → ST
ST → *ST / risk warning equivalent mapping
ST removal
suspension during ST
code change while ST
new listing
official vs BaoStock conflict
```

---

# 17. Acceptance Gates

```text
A12-G01 authority inventory complete
A12-G02 current contract/runtime divergence proven and frozen
A12-G03 trading status owner resolved
A12-G04 ST owner resolved
A12-G05 BaoStock role machine-enforced
A12-G06 no historical knowledge backdating
A12-G07 corrected V4-02 artifacts built append-only
A12-G08 old/new independent diff complete
A12-G09 V4-03 dependency impact determined
A12-G10 V4-04 true replay complete
A12-G11 V4-05 conditional replay complete
A12-G12 V4-07/08/09 cascade matrix complete
A12-G13 accepted heads untouched before external acceptance
A12-G14 clean detached regression
A12-G15 independent external audit
```

---

# 18. Codex 最终允许状态

```text
V4_02_STATUS_ST_AUTHORITY_REPAIR_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

不得自行：

```text
V4_02_REACCEPTED
V4_04_REACCEPTED
V4_05_REACCEPTED
GLOBAL_STAGE_HEAD_MOVED
```
