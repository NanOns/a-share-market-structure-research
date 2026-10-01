# A12-R2｜Real Dated Trading Status / ST Source Semantics & Authority Repair｜2026-10-01

**Work Package：** `WP-A12-R2-REAL-DATED-STATUS-ST-AUTHORITY`  
**基线：** `1655f84d1a47faca43c281d66e7704f2fa56b1b8`  
**优先级：** P0  
**性质：** 不重写 A12-R1 fail-closed 机制；补齐真实 source semantics 和 formal owner，避免全市场 ST/Price Limit 退化为 UNKNOWN。

---

# 1. 当前事实

A12-R1 已证明：

```text
BaoStock cross-check 不能偷偷当 formal owner
```

但当前：

```text
accepted_dated_authority_fact_count = 0
```

导致：

```text
9,118 suspension rows → UNKNOWN
4,035,729 ST rows → UNKNOWN
V4-04 5,222 / 5,222 → PARTIAL_UNKNOWN
```

因此 A12-R1 只能作为：

```text
DIAGNOSTIC_FAIL_CLOSED_CANDIDATE
```

不能 promotion。

---

# 2. 本轮目标

必须回答两个字段：

```text
TRADING_STATUS
ISST / risk-warning state
```

在：

```text
historical reconstructed replay
go-forward observed daily flow
```

分别由谁做正式 owner。

不得继续停留在：

```text
“没有 owner，所以全 UNKNOWN”
```

除非最终独立证明该能力确实无法恢复，并明确永久禁用。

---

# 3. 第一阶段：真实 Source Archaeology

先盘点仓库已存在 source，禁止默认重新联网。

至少检查：

```text
data/v4/source_evidence/v4_02_r3
data/v4/source_evidence/v4_02_r4
data/v4/source_evidence/v4_08_r3
official exchange notices
delisting-phase notices
suspension notices
TDX local metadata / TNF
accepted identity/lifecycle artifacts
BaoStock historical DailyUpdates
```

每一 source 写明：

```text
source family
field semantics
dated?
historical queryable?
mutable-current?
official/provider/local?
can prove
cannot prove
revision semantics
knowledge-time semantics
```

---

# 4. 真实样本矩阵｜禁止 synthetic-only

## Trading Status 至少包含

```text
正常交易日
真实停牌日
停牌 → 复牌
真实 data gap / local bar missing but should trade
BaoStock vs TDX local actual conflict
代码变更边界
新上市
长期停牌 / 退市阶段
```

至少覆盖：

```text
SH_MAIN
SZ_MAIN
CHINEXT
STAR
```

## ST / Risk Warning 至少包含

```text
NORMAL → ST
ST → *ST / risk-warning equivalent
ST removal
ST期间停牌
代码变更期间 ST
新上市
官方 vs BaoStock conflict
```

每个样本必须保存：

```text
security_id
source_security_key
effective date(s)
official/local evidence
provider value
expected interpretation
conflict disposition
```

---

# 5. 两条正式路径

## Path A｜Local / Official Dated Owner

如果能形成可持续：

```text
per-security
per-date
effective_from / effective_to
revision lineage
```

则建立：

```text
LOCAL_DATED_TRADING_STATUS_V2
LOCAL_DATED_ST_IDENTITY_V2
```

BaoStock 继续：

```text
SUPPLEMENTAL_CROSSCHECK
```

必须说明全历史覆盖方式，不能只拿几个样本作为全市场 owner。

---

## Path B｜Historical Reconstructed Provider Field Authority

如果 local/official 无法覆盖 2023-2026 全历史，
允许正式评估：

```text
BaoStock tradestatus
BaoStock isST
```

是否可成为：

```text
HISTORICAL_RECONSTRUCTED_FIELD_AUTHORITY
```

前提：

```text
真实官方样本验证通过
provider field semantics 明确
date semantics 明确
revision behavior 明确
identity/alias binding 明确
unknown/empty behavior 明确
```

允许 lineage：

```text
RECONSTRUCTED_CORRECTED
TARGET_DATE_QUERYABLE_FACT
```

禁止 lineage：

```text
AS_RECORDED
FIRST_AVAILABLE_AT_TARGET
LOCAL_TDX_AUTHORITY
```

Path B 必须产生：

```text
MASTER_SOURCE_AUTHORITY_AMENDMENT_CANDIDATE
```

等待独立外部接受。

---

# 6. BaoStock semantics 独立校验

若进入 Path B，至少验证：

```text
tradestatus=0/1 的准确含义
isST=0/1 的准确含义
ST / *ST / risk-warning 覆盖范围
停牌日字段行为
退市整理 / 风险警示阶段
代码变更前后 identity / alias 行为
新上市日
provider historical revision behavior
空返回与未知
```

不得只因为：

```text
historical query 能返回 4M 行
```

就授权 formal owner。

---

# 7. TDX actual bar 的权限保持

无论 Path A/B：

```text
TDX actual bar present
→ ACTUAL_TRADED
```

仍是最高直接事实。

Provider 如果说：

```text
tradestatus=0
```

但本地 accepted TDX 有真实 bar：

```text
ACTUAL_TRADED 保留
provider conflict 记录
```

不得覆盖。

---

# 8. Authority 选择结果必须唯一

最终只能输出之一：

```text
PATH_A_ACCEPTANCE_CANDIDATE

PATH_B_HISTORICAL_RECONSTRUCTED_AUTHORITY_AMENDMENT_CANDIDATE

CAPABILITY_PERMANENTLY_BLOCKED
```

禁止：

```text
“Path A/B 都可”
```

不做责任归属。

---

# 9. A10-R2 Entry Gate

最终 owner promotion 前必须满足：

```text
A10-R2 accepted-owner registry / external acceptance gate
```

A12 owner 只有：

```text
external accepted
formal consumer authorized
hash-bound
写入 accepted owner registry
```

后，才能被 formal consumer 使用。

---

# 10. 重建策略

Owner candidate 冻结后，复用 A12-R1 已验证 replay machinery：

```text
V4-02 Trading Status
V4-02 ST
V4-02 Price Limit
V4-03
V4-04
V4-05
V4-07
V4-08
V4-09
```

全部算法参数保持不变。

---

# 11. 质量统计

必须报告：

```text
Trading Status:
  ACTUAL_TRADED
  SUSPENDED
  DATA_GAP
  UNKNOWN

ST:
  NORMAL
  RISK_WARNING/ST
  UNKNOWN

Price Limit:
  known
  unknown + reason

V4-04:
  COMPLETE
  PARTIAL_UNKNOWN

V4-07:
  Base Seed transitions

V4-08:
  B0/B2/ROTATION/SECTOR_NATIVE business diff

V4-09:
  qualification / priority / quality transitions
```

不要求为了“恢复旧数量”强行拟合。

但如果仍：

```text
V4-04 5222/5222 PARTIAL_UNKNOWN
```

必须明确证明这是真实证据极限，
不能直接称“业务修复完成”。

---

# 12. A12-R1 不返工项

直接复用：

```text
fail-closed producer mechanics
full-row oracle
formal period replay
unchanged algorithm AST proofs
cascade diff framework
accepted-head protection
```

只替换：

```text
accepted dated authority pool
owner contract
source semantics evidence
```

及必要的 owner-aware adapter。

---

# 13. Independent Oracle

新 oracle 不能只验证：

```text
没有 formal owner → UNKNOWN
```

还必须独立验证：

```text
real dated evidence / accepted provider authority
→ expected status/ST
```

至少随机抽样：

```text
正常
停牌
ST
非ST
代码变更
新上市
退市/特殊阶段
```

并从 source bytes 独立重算。

---

# 14. Accepted Head 纪律

本轮结束只允许：

```text
A12_R2_*_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

禁止：

```text
覆盖 V4-02 Accepted Head
覆盖 V4-04/V4-05 Accepted Head
移动 V4_STAGE_ACCEPTED_HEAD
移动 V4_DATA_ACCEPTED_HEAD
```

外部验收通过后另发 promotion/amendment card。

---

# 15. 与 DM01 的关系

A12-R2 未 external accepted：

```text
DM01 final all-nine = BLOCKED
```

A12-R2 external accepted 后：

```text
DM01 只能消费 accepted owner
不得自己重新定义 suspension/ST fallback
```

DM01 9/28 已完成的 BaoStock capture 不要求重复抓取，
除非 revision audit 证明必须新增 source revision。

---

# 16. 验收门

```text
A12R2-G01 real Trading Status sample matrix complete
A12R2-G02 real ST sample matrix complete
A12R2-G03 four required boards represented
A12R2-G04 provider/local/official conflicts explicit
A12R2-G05 one authority path selected
A12R2-G06 temporal lineage correct
A12R2-G07 no AS_RECORDED backdating
A12R2-G08 owner contract machine-readable
A12R2-G09 A10-R2 owner-registry compatibility
A12R2-G10 V4-02 full historical rebuild
A12R2-G11 independent real-source oracle
A12R2-G12 V4-04 true replay
A12R2-G13 V4-03/05/07/08/09 cascade
A12R2-G14 no algorithm parameter change
A12R2-G15 accepted heads unchanged
A12R2-G16 clean detached regression
A12R2-G17 independent external audit
```

Codex 最终不得自行声明：

```text
A12_ACCEPTED
V4_02_REACCEPTED
A12_OWNER_REGISTERED_AS_ACCEPTED
```

只允许：

```text
A12_R2_REAL_DATED_OWNER_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```
