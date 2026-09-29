# V4-00 ~ V4-03 基础链 FULL_PASS 最终闭环任务卡 R2

- 日期：2026-09-29
- 仓库：`NanOns/a-share-market-structure-research`
- 分支：`codex/v4-system-reform`
- 当前 HEAD：`e307892b138a3e5e1925546095d884e7900083d2`
- 最新提交：`[V4-01] Fix source fingerprint F6 and acceptance evidence`
- 任务目标：**停止 V4-01 无限样本研究，把当前已经完成的能力转成全 Required Scope 的实际完整性验证，并一次性关闭 V4-00 / V4-01 / V4-02 / V4-03 剩余基础链问题。**
- 最终目标：

```text
V4_00 = FULL_PASS
V4_01 = FULL_PASS_REQUIRED_SCOPE
V4_02 = FULL_PASS_REQUIRED_SCOPE
V4_03 = FULL_PASS_AMENDED_SCOPE

V4_00_01_02_03_FULL_CHAIN = FULL_PASS
V4_04_ENTRY = AUTHORIZED_FULL_CHAIN
```

---

# 0. 本轮最高原则

这不是新一轮“大改造”。

00–03 已经完成的大量代码和产物**不得无差别返工**。

本轮只处理：

1. V4-01 identity completeness / formal owner gate；
2. V4-00 authority 归一；
3. V4-02 current truth cleanup + upstream rebind；
4. V4-03 Sector membership-dependent materialization 的正式 stage ownership；
5. current-HEAD 的 00→03 一体化回归；
6. 最终 Accepted Head / Full-Chain Seal。

明确排除：

```text
Incremental Update / DM-01
V4-05 Full Replay Gate A
V4-06 Turnover
V4-08 Sector Qualification / Rotation
PREWATCH
Structure / Anchor / Support
Forward / Settlement
Scanner / Trading / Focus
```

这些不作为本轮 FULL_PASS blocker。

---

# 1. 当前状态冻结

## V4-00

当前判断：

```text
V4_00_FUNCTIONAL = FULL_PASS
V4_00_STAGE_OBLIGATIONS = FULL_PASS
```

只剩 authority / acceptance 表达统一，不允许重做 00A–00H。

---

## V4-01

当前真实状态：

```text
R7 canonical identity/universe = current downstream input

R8.3:
identity_discovery = PASS
independent_algorithm_postcheck = PASS
official_event_index_coverage = BLOCKED
owner_gate = BLOCKED

source fingerprint:
single sample diagnostic = corrected
candidate detector v1.0 = research PASS
2 positive + 2 negative bounded validation = PASS
synthetic contract tests = PASS
F6 semantic cleanup = PASS

source fingerprint calibration = OPEN_RESEARCH
```

最重要的新决策：

> **Source Fingerprint Calibration 不再作为 V4-01 owner-gate blocker。**

理由：

- 当前 detector 永不自动 merge；
- 每个 candidate 仍必须独立 evidence confirm；
- 因此其研究阈值不需要先达到 production classification accuracy；
- full-scope 扫描可以 fail-closed：多报 candidate 只增加 review，不能造成误合并；
- 真正必须做到的是**不要漏掉有强 source behavior 的 identity relation candidate，并让所有 candidate 最终 resolved / unresolved=0**。

所以：

```text
SOURCE_FINGERPRINT_CALIBRATION =
DEFERRED_NON_BLOCKING_RESEARCH
```

保留 audit item，不删除，不伪装 CLOSED。

---

## V4-02

当前：

```text
Required Scope functional = FULL_PASS
External Acceptance = ACCEPTED
BSE = OPTIONAL DEGRADED
```

剩余：

1. 仍有旧 mapping 把历史 R1 audit 写成 OPEN；
2. V4-01 final accepted head 尚不存在，因此需要最终 upstream rebind。

---

## V4-03

当前：

```text
STOCK_CORE = PASS
RELATIVE_RPS = PASS
MARKET_REFERENCE = PASS
MARKET_REGIME = PASS

SECTOR_NATIVE_ALGORITHM_CONTRACT = PASS
SECTOR_NATIVE_FULL_MARKET_MATERIALIZATION =
BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP
```

本轮不再尝试伪造历史 PIT membership。

需要正式解决 stage ownership。

---

# 2. P0-A｜V4-01 completeness gate 改造：停止“官方事件穷举唯一门”

当前最大的卡点：

```text
OFFICIAL_SECURITY_CODE_CHANGE_EVENT_INDEX_V1
coverage_complete = false
```

旧 Gate A 实际要求：

```text
完整 official event index
→ 再认为 identity completeness 有证据
```

这个目标在公开源上可能无法可靠证明“穷尽”。

继续无限扩关键词不是可收敛工程方案。

## 本轮要求

新增一个**versioned amendment candidate**：

```text
V4_01_IDENTITY_COMPLETENESS_GATE_V2
```

注意：

**这是 amendment candidate，不允许 Codex 自己宣布 accepted。**
最终需要外部验收。

---

# 3. V4_01_IDENTITY_COMPLETENESS_GATE_V2 核心语义

Completeness 不再依赖单一 exhaustive official registry。

改为以下联合门：

```text
FULL ATOMIC BOUNDARY INVENTORY
+
GENERIC RELATION CANDIDATE DISCOVERY
+
SOURCE FINGERPRINT CANDIDATE DISCOVERY
+
KNOWN OFFICIAL EVENT CROSS-CHECK
+
FAIL-CLOSED UNRESOLVED RELATIONS
+
INDEPENDENT POSTCHECK
```

## 3.1 Atomic Boundary Inventory

使用当前 R8.3 已有完整 Required Scope boundary inventory。

要求继续保持：

```text
all required entry boundaries enumerated
all required exit boundaries enumerated
unlinked boundary anomalies = 0
```

不得回到“人工已知股票列表”。

---

# 4. P0-B｜全 Required Scope Source-Fingerprint Scan

当前 `V4_01_SOURCE_FINGERPRINT_CANDIDATE_V1`：

```text
20 shared sessions
TDX volume exact >= 0.95
BaoStock active exact >= 0.99
```

继续冻结为 **research candidate threshold v1.0**。

本轮：

**禁止先调阈值。**

先在完整 Required Scope 上跑。

---

# 5. Candidate generation 必须避免 R8.2 的 Cartesian 错误

绝对禁止：

```text
all exits × all entries
```

必须使用 TDX-first 分层筛选。

## Step 1｜New-code anomaly discovery

对 Required Scope 每个 entry boundary：

```text
new_code first universe date = T
```

检查当前 TDX `.day`：

```text
day_file.first_date < T
```

即：

> 新出现的证券代码，本地历史文件却包含它“出现前”的多年历史。

这就是非常强的 alias-migration candidate trigger。

普通 IPO 通常不会满足。

记录：

```text
NEW_CODE_PRE_EFFECTIVE_HISTORY_ANOMALY
```

---

## Step 2｜只在相邻退出边界中寻找 old-code

只允许候选 old code 来自：

```text
same exchange
AND
exit at T or previous market session
```

禁止跨日期全表配对。

如果同日存在多个 exits：

逐个执行 source fingerprint semantic comparison。

---

## Step 3｜TDX semantic match

若 old/new `.day` 都存在：

比较 pre-effective history：

```text
OHLC
amount
volume
calendar overlap
```

规则继续：

- `reserved` 不进入 semantic equality；
- raw 32-byte prefix 仅描述；
- OHLC/amount 必须严格；
- volume 使用冻结 v1.0 research threshold；
- minimum shared sessions = 20。

输出：

```text
TDX_STRONG_SEMANTIC_ALIAS_CANDIDATE
TDX_NO_ALIAS_SIGNAL
TDX_UNRESOLVED
```

---

## Step 4｜BaoStock 只查询经过 TDX-first 缩小后的候选

不要对 5,000+ 股票全部发历史 API。

BaoStock 只用于 TDX-first / R8.3 generic candidates。

检查：

```text
stock_basic old/new
ipoDate
outDate
status
old/new long history
new-code pre-effective backfill
normalized history overlap
boundary-date status
provider returned code
```

请求 ledger 必须继续受控。

---

# 6. Old TDX file 缺失的 fallback

类似：

```text
000022 → 001872
```

当前 old `.day` 缺失。

允许 fallback，但必须更严格：

```text
new TDX contains pre-effective history
AND
new TDX first_date == shared IPO anchor
AND
BaoStock old/new long-history semantic overlap
AND
BaoStock lifecycle metadata continuity
AND
independent official / accepted evidence
```

没有 independent evidence：

```text
UNRESOLVED_IDENTITY_RELATION
```

不得自动 SAME_ENTITY。

---

# 7. Candidate Resolution Policy

全 Required Scope 扫描后，每个 candidate 只能落在：

```text
CONFIRMED_SAME_ENTITY_CODE_CHANGE

CONFIRMED_DISTINCT_MERGER_SUCCESSOR

CONFIRMED_DISTINCT_CODE_REUSE

UNRESOLVED_IDENTITY_RELATION
```

## SAME_ENTITY 最终确认

Source fingerprint **不能单独确认**。

至少还需要一个独立正式 evidence：

- exchange/company official code-change notice；
- accepted dated alias fact；
- issuer/company identity evidence；
- 或未来正式接受的独立 confirmation source。

## DISTINCT

可以来自：

- merger / absorption official evidence；
- issuer identity discontinuity；
- actual substantive dual trading；
- explicit code reuse；
- independent listing entity evidence。

---

# 8. V4-01 owner-gate acceptance criteria

`V4_01_IDENTITY_COMPLETENESS_GATE_V2` candidate 必须证明：

```text
all Required Scope atomic boundaries scanned

source-fingerprint-triggered entry boundaries scanned

all generated relation candidates resolved

UNRESOLVED_IDENTITY_RELATION = 0

unlinked boundary anomalies = 0

known official code-change events
are all present in the candidate/resolution set

R7 known relation 300114→302132 correctly recovered

000022→001872 correctly classified SAME_ENTITY

000024→001979 correctly classified DISTINCT merger successor

000562→000166 correctly classified DISTINCT merger successor

no canonical identity mutation without independent confirmation
```

如果 full-scope scan 发现新 candidate 无法确认：

```text
V4_01 remains BLOCKED
```

这是正确 fail-closed。

---

# 9. Official Event Index 的新身份

现有：

```text
OFFICIAL_SECURITY_CODE_CHANGE_EVENT_INDEX_V1
```

不得删除。

改为：

```text
KNOWN_EVENT_CROSS_CHECK / CONFIRMATION_SOURCE
```

而不是：

```text
SOLE_EXHAUSTIVE_COMPLETENESS_SOURCE
```

现有：

```text
official_index_coverage = BLOCKED
```

保留历史事实。

在 V2 gate 中它不再是“必须穷尽所有事件”的单一门。

必须在 amendment 文档中说明迁移原因：

> 公开检索接口无法可靠证明全窗口 exhaustive completeness；因此从“单一官方事件索引穷尽”迁移到“全量数据边界扫描 + source behavior discovery + independent evidence resolution”的可审计完整性门。

---

# 10. Source Fingerprint Calibration Audit 的处置

当前：

```text
AUDIT-V4-01-SOURCE-FINGERPRINT-CALIBRATION-20260929
= OPEN
```

不关闭。

改为明确：

```text
status =
DEFERRED_NON_BLOCKING_RESEARCH

owner_stage_blocker = false
production_confirmation_authority = false
```

保留未来：

- 更多 paired TDX；
- SH/STAR 样本；
- 更困难 negatives；
- 阈值 calibration。

但不再阻断 00–03 foundation closure。

---

# 11. P0-C｜V4-01 current canonical acceptance

full-scope V2 scan 完成后：

## 情况 A｜没有发现新的 SAME_ENTITY relation

如果：

```text
security_entity_map_R7 SHA unchanged
historical_universe_R7 SHA unchanged
```

则：

- 不重建 V4-02 / V4-03 大数据；
- 生成 V4-01 final acceptance candidate；
- 建立：

```text
data/v4/V4_01_ACCEPTED_HEAD.json
```

必须绑定：

- R7 identity map；
- R7 Historical Universe；
- V2 completeness gate receipt；
- candidate-resolution receipt；
- independent postcheck；
- known-event cross-check；
- Required Scope status；
- BSE optional degradation。

目标：

```text
V4_01_REQUIRED_SCOPE = FULL_PASS
V4_01_EXTERNAL_REVIEW_READY = TRUE
```

在外部验收之前：

```text
EXTERNALLY_ACCEPTED = false
```

不得自签。

---

## 情况 B｜发现新的 confirmed SAME_ENTITY relation

如果 R7 真的漏了代码变更：

1. 生成新的 R9 canonical identity / universe；
2. 不覆盖 R7；
3. 输出迁移差异；
4. downstream 可以：
   - 精确重建受影响链；
   - 或直接全量确定性重跑。

本项目当前**不要求实现增量更新**。

为了减少复杂度：

```text
FULL DETERMINISTIC REBUILD IS ALLOWED
```

只要：

- 不修改算法；
- source cutoff 一致；
- receipts/digests 全部重新绑定。

---

# 12. P0-D｜V4-00 authority normalization

V4-00 功能不改。

当前需要解决的只是：

```text
Phase0 final receipt = FULL_PASS
但 external authority 表达存在历史 PENDING/JOINED review 痕迹
```

要求：

- 不修改旧 receipt；
- 新增一个 current authority/seal receipt 或 current binding；
- 绑定当前有效 Phase0 final receipt + 已存在 external acceptance evidence；
- 明确：

```text
V4_00 = FULL_PASS
V4_00_EXTERNAL_ACCEPTANCE = ACCEPTED
```

如果当前架构无需单独 `V4_00_ACCEPTED_HEAD.json`，可以通过 global chain authority receipt完成。

重点：

**只能归一治理状态，不能重跑或修改 00A–00H。**

---

# 13. P0-E｜V4-02 current truth cleanup

当前功能不用重做。

## 13.1 清理 stale mapping

现有：

```text
config/v4_02_stage_acceptance_mapping_v2.json
```

仍把历史：

```text
V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R1 = OPEN
```

当成 current open item。

必须更新 current mapping：

```text
R1 = SUPERSEDED
R3 = HISTORICAL_BLOCKED
R4_RANGE_AUDIT = CLOSED
R6_EXTERNAL = EXTERNALLY_ACCEPTED

current_open_engineering_exception = 0
```

历史文件不删除。

---

## 13.2 绑定最终 V4-01 accepted head

V4-01 外部接受后：

### 若 upstream canonical hashes 未变

只做：

```text
cross-stage postcheck
upstream rebind
V4_02 reseal
```

不要重算 400 万行。

### 若 upstream hashes 变化

允许：

```text
full deterministic V4-02 rebuild
```

不要求增量更新。

最终：

```text
V4_02_REQUIRED_SCOPE = FULL_PASS
BSE = OPTIONAL_DEGRADED
V4_02_EXTERNAL_ACCEPTANCE = PRESERVED_OR_RESEALED
```

---

# 14. P0-F｜V4-03 Sector ownership 正式修订

当前事实：

```text
Sector Native machine algorithms = PASS
Synthetic/library vectors = PASS

Full-market Sector Native materialization =
BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP
```

而当前旧 TDX sector membership snapshot 明确：

```text
CURRENT_TDX_MEMBERSHIP
pit_membership = false
historical_backtest_safe = false
```

所以不能伪造 2026-09-24 PIT membership。

---

# 15. 本轮决定：membership-dependent materialization 迁移至 V4-08

为了让阶段所有者清晰，本轮提交一个 versioned amendment candidate：

```text
V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1
```

新边界：

## V4-03 保留

```text
Sector Native schemas
Sector Native machine contracts
field-local quality semantics
common-member semantics
native primitive formulas
library/synthetic vectors
```

这些已完成，记：

```text
V4_03_SECTOR_NATIVE_CONTRACT = PASS
```

## 迁移到 V4-08

任何依赖真实 accepted sector membership 的：

```text
full-market sector materialization
historical sector membership
PIT sector member snapshots
sector native full-market rows
sector/rotation production input
```

统一归：

```text
V4-08 Sector / Rotation owner stage
```

理由：

这些能力必须先建立正式 sector membership source contract，天然属于后续 Sector owner stage。

---

# 16. Amendment 的限制

不能写成：

> 因为做不出来，所以删掉。

必须明确：

- 不是降低算法要求；
- 是修正 owner-stage dependency；
- V4-03 已完整交付 membership-independent machine contract；
- V4-08 在使用任何 sector-dependent output 前必须先完成 membership baseline/PIT reconstruction；
- 当前 `CURRENT_TDX_MEMBERSHIP` 仍只能 diagnostic。

amendment 外部验收前：

```text
V4_03 = PASS_WITH_SECTOR_SCOPE_DEGRADED
```

外部接受 amendment 后：

```text
V4_03 = FULL_PASS_AMENDED_SCOPE
```

---

# 17. V4-03 reseal

如果 V4-01/V4-02 upstream hashes 未变化：

不重跑 47 fields / market path / Market Regime。

只：

```text
bind V4_01 accepted head
bind V4_02 reseal
bind accepted Sector ownership amendment
run V4_03 final validator
reseal
```

如果 upstream data hash 变化：

允许 V4-03 full deterministic rerun。

不实现 incremental pipeline。

---

# 18. P1｜00→03 current-HEAD 全链回归

最终 closure commit 上必须运行一次统一测试。

至少：

```bash
python -m pytest -q \
  tests/v4_phase0 \
  tests/v4_01 \
  tests/v4_02 \
  tests/v4_03
```

如果目录名实际不同，纳入所有对应 00–03 test modules。

必须记录：

```text
commit SHA
Python version
test file set
passed
failed
skipped
duration
```

生成：

```text
reports/v4_joint/
V4_00_01_02_03_FULL_CHAIN_TEST_RECEIPT_R1.json
```

---

# 19. 新增 FULL CHAIN validator

新增：

```text
scripts/validate_v4_00_01_02_03_full_chain.py
```

它必须独立验证：

## V4-00

```text
status = FULL_PASS
external authority = ACCEPTED
```

## V4-01

```text
V4_01_ACCEPTED_HEAD exists
Required Scope = FULL_PASS
external acceptance = ACCEPTED
unresolved identity relations = 0
identity/universe SHA valid
```

## V4-02

```text
external acceptance = ACCEPTED
current truth has no open required engineering exception
upstream V4-01 head hash exact
```

## V4-03

```text
Stock Core = PASS
Relative RPS = PASS
Market Reference = PASS
Market Regime = PASS
Sector Native Contract = PASS
accepted Sector ownership amendment bound
upstream V4-01/V4-02 identities exact
```

## 全链

```text
no required upstream stage PENDING
no required upstream capability BLOCKED
all file hashes valid
all receipts exist
all accepted-head pointers unique/current
scanner_run_count = 0
trading_run_count = 0
tdx_root_write_count = 0
```

---

# 20. 允许存在的非 blocker

FULL CHAIN validator 必须明确允许：

```text
BSE_OPTIONAL_DEGRADED

INCREMENTAL_UPDATE =
DEFERRED_NON_BLOCKING

SOURCE_FINGERPRINT_CALIBRATION =
DEFERRED_NON_BLOCKING_RESEARCH

V4_05 =
NOT_STARTED

V4_06 =
NOT_STARTED

V4_08_MEMBERSHIP_AND_ROTATION =
NOT_STARTED / BLOCKED_UNTIL_OWNER_STAGE

SCANNER / TRADING / FOCUS =
NOT_STARTED
```

这些不允许被误判成 00–03 failure。

---

# 21. 最终 Full-Chain Receipt

新增：

```text
reports/v4_joint/
V4_00_01_02_03_FULL_CHAIN_FINAL_RECEIPT_R1.json
```

至少包含：

```text
status = FULL_PASS_CANDIDATE

current_commit

V4_00 status / authority / hashes
V4_01 accepted head / hashes
V4_02 accepted head / hashes
V4_03 accepted head / hashes

deferred_non_blocking
future_owner_capabilities
test receipt
chain validator receipt

canonical artifact changes:
  V4_01 changed?
  V4_02 rebuilt?
  V4_03 rebuilt?

scanner/trading/tdx write counts
```

---

# 22. Global Accepted Head 更新规则

Codex 本轮**先不要自行把 global head 改成 FULL_PASS**。

先生成：

```text
FULL_PASS_CANDIDATE
EXTERNAL_REVIEW_READY
```

等待外部验收。

外部验收通过后才允许：

```text
V4_STAGE_ACCEPTED_HEAD.status =
FOUNDATION_FULL_PASS

V4_00 = FULL_PASS
V4_01 = FULL_PASS
V4_02 = FULL_PASS_REQUIRED_SCOPE
V4_03 = FULL_PASS_AMENDED_SCOPE

V4_04_ENTRY =
AUTHORIZED_FULL_CHAIN
```

---

# 23. 本轮禁止事项

禁止：

- 继续为了 owner gate 无限增加 source-fingerprint 样本；
- 改 candidate detector v1.0 阈值后再把同一批样本跑到全对；
- 用 source fingerprint 自动 SAME_ENTITY；
- 删除官方 event index；
- 伪造 exhaustive official coverage；
- 伪造历史 Sector PIT membership；
- 用 CURRENT_TDX_MEMBERSHIP 当历史 PIT；
- 重做已经通过的 47 factor algorithms；
- 重写 Market Regime；
- 重做 Price Limit；
- 实现 Incremental Update；
- 提前开发 V4-04 业务；
- 启动 V4-05+。

---

# 24. Codex 执行顺序

严格按顺序：

```text
STEP 1
冻结当前 candidate detector v1.0
source-fingerprint calibration 改为 deferred non-blocking research

STEP 2
实现 V4_01_IDENTITY_COMPLETENESS_GATE_V2 candidate
进行 full Required Scope TDX-first candidate scan

STEP 3
只对缩小后的 candidates 使用 BaoStock / official evidence
完成 resolution
要求 unresolved = 0

STEP 4
生成 V4-01 final candidate / accepted-head candidate
不要自签 external acceptance

STEP 5
V4-00 authority normalization

STEP 6
V4-02 stale mapping cleanup + conditional upstream rebind

STEP 7
提交 V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1 candidate
将 membership-dependent materialization正式迁移 V4-08

STEP 8
V4-03 conditional reseal
hash未变就不重算；变了允许 full rerun

STEP 9
跑 current-HEAD 00–03 combined tests

STEP 10
跑 FULL CHAIN validator

STEP 11
生成 FULL_PASS_CANDIDATE receipt

STOP
等待独立外部验收
```

---

# 25. 必须交付的文件

至少：

## V4-01

```text
docs/audits/
V4_01_IDENTITY_COMPLETENESS_GATE_V2_AMENDMENT_20260929.md

config/
v4_01_identity_completeness_gate_v2.json

reports/v4_01/
V4_01_FULL_SCOPE_SOURCE_FINGERPRINT_SCAN_R1.json
V4_01_IDENTITY_RELATION_RESOLUTION_R1.json
V4_01_IDENTITY_COMPLETENESS_GATE_V2_POSTCHECK_R1.json
V4_01_FINAL_STAGE_CANDIDATE_R9.json

data/v4/
V4_01_ACCEPTED_HEAD_CANDIDATE.json
```

如果 canonical identity 发生变化，新增 R9 artifact，绝不覆盖 R7。

---

## V4-00

```text
reports/v4_phase0/
V4_00_CURRENT_AUTHORITY_NORMALIZATION_R1.json
```

或项目现有等价治理文件。

---

## V4-02

```text
config/
current V4-02 acceptance mapping

reports/v4_02/
V4_02_CURRENT_TRUTH_RECONCILIATION_R1.json
V4_02_V4_01_FINAL_REBIND_POSTCHECK_R1.json
```

如需 rebuild，再另产正式 manifest/receipt。

---

## V4-03

```text
docs/audits/
V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1_20260929.md

reports/v4_03/
V4_03_AMENDED_SCOPE_RESEAL_CANDIDATE_R1.json
```

---

## Joint

```text
reports/v4_joint/
V4_00_01_02_03_FULL_CHAIN_TEST_RECEIPT_R1.json
V4_00_01_02_03_FULL_CHAIN_VALIDATION_R1.json
V4_00_01_02_03_FULL_CHAIN_FINAL_RECEIPT_R1.json
```

---

# 26. 最终成功标准

本轮 Codex 执行完成后，不要求它自行宣布最终 PASS。

它应该停在：

```text
V4_00 = FULL_PASS_CANDIDATE
V4_01 = FULL_PASS_CANDIDATE
V4_02 = FULL_PASS_CANDIDATE
V4_03 = FULL_PASS_AMENDED_SCOPE_CANDIDATE

V4_00_01_02_03_FULL_CHAIN =
FULL_PASS_CANDIDATE

EXTERNAL_REVIEW_READY = TRUE

V4_04_ENTRY =
PENDING_FINAL_EXTERNAL_ACCEPTANCE
```

然后交给外部验收。

---

# 27. 如果 V4-01 full-scope scan 再发现新问题

不要继续自动扩任务。

只允许三种结果：

### 结果 A

```text
no new relation
R7 canonical unchanged
```

→ 最轻量 reseal。

### 结果 B

```text
new confirmed SAME_ENTITY / DISTINCT relations
```

→ 新 R9 canonical + downstream deterministic rebuild。

### 结果 C

```text
unresolved candidates > 0
```

→ 明确列出具体代码对、证据缺口和需要的最小确认动作。

**不得再把任务扩成“继续全市场搜更多案例”。**

---

# 28. 本轮为什么这样收口

Source fingerprint 当前已经证明：

- 数据源确实存在 alias migration fingerprint；
- 能区分至少两个 same-entity code renumbering 和两个 merger-successor；
- candidate detector 可以 fail-closed；
- 它不是 confirmation contract。

因此它现在最合理的角色不是：

```text
继续学术式扩大样本直到阈值“完美”
```

而是：

```text
把它投入完整 Required Scope candidate discovery
+
对真实 candidates逐个正式 resolve
```

这才是能让 V4-01 和整个 00–03 基础链收敛的工程路径。
