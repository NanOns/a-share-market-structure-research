# A11｜V4-01 Security Identity Source Authority Reconciliation 任务卡 R1｜2026-10-01

**Work Package：** `WP-A11-V4-01-IDENTITY-AUTHORITY`  
**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**基线 HEAD：** `4e5284f74c5275e28d75985d1c3e60eaf96e4103`  
**优先级：** P1 Foundation Governance  
**性质：** audit-first；先核 source owner，再决定是否需要数据 Amendment。禁止直接重做 5,351 个 identity。

---

# 1. 发现背景

V4.2.2 REV2/REV4 Source Authority Matrix：

```text
股票代码 / 证券类型
正式 Authority = 本地 TDX metadata
BaoStock basic = supplemental
```

但历史：

```text
SECURITY_ENTITY_IDENTITY_V1
```

明确 source contracts：

```text
BAOSTOCK_LIFECYCLE_FACTS_R5_V1
BSE_SECURITY_LIFECYCLE_SOURCE_V1
```

SH/SZ identity 初始构建实际使用：

```text
BaoStock query_stock_basic
security_type_provider
listed_from / ipoDate
listed_to / outDate
```

生成 stable identity anchor。

后续又补入：

```text
TDX-first boundary scan
official code-change evidence
exchange active catalogue
go-forward official lifecycle source
```

因此当前不是简单“identity 一定错”，而是：

> 正式结果的数据值可能是对的，但 formal source ownership 与 master contract 没有完全 reconcile。

---

# 2. 本任务目标

逐字段回答：

```text
symbol authority 是谁？
security_type authority 是谁？
board authority 是谁？
listing anchor authority 是谁？
delist/lifecycle authority 是谁？
alias relation authority 是谁？
stable security_id derivation 的每个输入来自谁？
```

输出一份：

```text
V4_01_IDENTITY_FIELD_AUTHORITY_MATRIX_R1
```

不得再只写“identity source = BaoStock/TDX”这种粗粒度描述。

---

# 3. 必查正式对象

至少：

```text
data/v4/V4_01_ACCEPTED_HEAD.json
data/v4/V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1.json

security_entity_map_R7_20260927.json
historical_universe_required_R7_20260927.jsonl.gz

SECURITY_ENTITY_IDENTITY_V1
PROVIDER_LIFECYCLE_FACT_V1

TDX security master / TNF
TDX day-file boundary
exchange current catalogue
official code-change event evidence
BSE official lifecycle evidence
```

---

# 4. 历史 identity 不得用“本地存在”偷换“正式 authority”

例如：

```text
TDX .day 文件存在
```

只能直接证明：

```text
source key 在该日期有行情记录
```

不能自动证明：

```text
法律主体 lifecycle
原始上市日期
same-entity code change
证券类型在所有历史日期都确定
```

同理：

```text
BaoStock query_stock_basic
```

提供 listing/type/provider facts，
也不能因为方便就自动成为 master contract 未授权的 formal owner。

---

# 5. Authority Reconciliation 路径

每字段只能进入下列之一：

## A. LOCAL_TDX_AUTHORITY_CONFIRMED

有 TDX bytes / decoder / contract 明确支撑。

## B. OFFICIAL_EXCHANGE_AUTHORITY_CONFIRMED

有交易所/法定公告等 accepted source。

## C. PROVIDER_RECONSTRUCTED_FACT

BaoStock 等 provider 可作为：

```text
RECONSTRUCTED_CORRECTED
```

事实来源，但不能冒充 local authority / AS_RECORDED。

## D. MULTI_SOURCE_ADJUDICATED

必须给：

```text
primary owner
conflict policy
tie-break rule
```

## E. UNKNOWN

证据不足就 UNKNOWN，不得根据代码模式硬补 lifecycle truth。

---

# 6. 重点检查 SH.600018

已有：

```text
V4_01_OFFICIAL_LIST_DATE_ANCHOR_RECONCILIATION_01
```

accepted canonical listing anchor：

```text
2006-10-26
```

exchange catalogue first listing date：

```text
2000-07-19
```

本任务必须判断：

```text
是否 corporate reorganization / relisting / identity-anchor semantics 差异
还是 canonical anchor 真错误
```

不能仅因为两日期不同就 mass-rekey。

---

# 7. Stable security_id 保护

默认：

```text
DO_NOT_RENUMBER
```

只有同时满足：

```text
现有 anchor 被独立证伪
新 anchor 有正式 authority
identity relation 已独立确认
downstream migration plan 完整
```

才允许提出：

```text
security_id amendment
```

否则保留 stable id，并用：

```text
anchor semantics amendment
source authority amendment
```

修治理。

---

# 8. 全量字段审计

对 required scope 5,351 canonical identities 生成统计：

```text
security_type:
  local_tdx_confirmed
  official_confirmed
  provider_only
  conflicting
  unknown

listing_anchor:
  official_confirmed
  tdx_boundary_consistent
  provider_only
  discrepancy
  unknown

alias_relation:
  official
  bounded fingerprint research-only
  unresolved
```

至少按：

```text
SH_MAIN
SZ_MAIN
CHINEXT
STAR
```

分别统计。

---

# 9. Go-forward identity 单独处理

现有：

```text
V4_01_GO_FORWARD_IDENTITY_ACCEPTED_HEAD_R1
```

已经使用 target-day official exchange catalogue / statutory listing evidence。

不得因为历史 authority reconciliation 而回滚这套正确的 go-forward 模式。

要求：

```text
HISTORICAL_RECONSTRUCTED
和
GO_FORWARD_OBSERVED
```

明确分层。

---

# 10. 允许的最终结果

## Result A｜No business identity changes

如果全量核对证明：

```text
现有 stable ids / board / type / lifecycle interval
业务值无需改变
```

只需要：

```text
Accepted Head authority/provenance Amendment
```

不重跑所有下游业务算法。

## Result B｜Bounded corrections

若少量 identity 需要更正：

```text
版本化 amendment artifact
old identity preserved as superseded
affected-date bounded rebuild
downstream diff
```

## Result C｜Widespread authority unresolved

若大量 formal fields 只有 provider-only evidence：

不得假称 local TDX authority。

必须：

```text
Master Contract Amendment proposal
或 capability downgrade
```

等待独立外部决定。

---

# 11. 下游影响审计

至少扫描：

```text
V4-02 canonical rows
V4-03 factor identities
V4-04 profile identities
V4-05 replay
V4-07 Seed
V4-08 sector membership / rotation
V4-09 PREWATCH
```

只有 identity/business digest 真变化的下游才重建。

禁止：

```text
无差别重跑所有 stage
```

---

# 12. 验收门

```text
A11-G01 field authority matrix complete
A11-G02 all 5351 required-scope identities inventoried
A11-G03 TDX/local vs provider vs official ownership separated
A11-G04 SH.600018 independently adjudicated
A11-G05 go-forward official identity preserved
A11-G06 no silent security_id rewrite
A11-G07 downstream consumer graph complete
A11-G08 business-diff produced
A11-G09 amendment plan if needed
A11-G10 clean detached regression
A11-G11 independent external audit
```

---

# 13. Codex 允许的最终状态

```text
V4_01_IDENTITY_AUTHORITY_RECONCILIATION_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

不得自行声明：

```text
V4_01_REACCEPTED
ALL_IDENTITIES_CORRECT
```
