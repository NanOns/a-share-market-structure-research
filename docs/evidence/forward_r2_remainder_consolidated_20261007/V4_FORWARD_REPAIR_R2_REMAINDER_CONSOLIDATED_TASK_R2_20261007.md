# V4 Forward R2｜综合收尾修复任务卡 R2｜2026-10-07

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 执行基线: `433c3378d4bc4db572f95de20cadbf899c2a04ce`
- 前置结论: IA-01/02/03/04/09/10 已通过工程候选独立外审
- 性质: 一次性处理当前剩余全部可修复审计问题；不再拆 Round 3

## 0. 唯一任务范围

本轮必须处理：

```text
IA-05 = P1 / GLOBAL PYTEST COLLECTION + GLOBAL REGRESSION DEBT
IA-06 = P1 / CURRENT PG + FEP MODEL ENVIRONMENT VERIFICATION
IA-07 = P2 / CURRENT-SCALE PERFORMANCE VALIDATION
IA-08 = P2 / HISTORICAL PROVENANCE ROUTING
DM01-LEGACY-P2 =
AUDIT_DM01_R4_LEGACY_TEST_ACCEPTANCE_STATE_20261007
```

PASS_KEEP：

```text
IA-01
IA-02
IA-03
IA-04
IA-09
IA-10
```

禁止重新设计已经通过的 Forward V1.2 数值语义。

## 1. 执行顺序

```text
WP-A  IA-05 + DM01 legacy test governance
   ↓
WP-B  IA-08 historical/current version routing
   ↓
WP-C  IA-06 isolated PG + model environment verification
   ↓
WP-D  IA-07 current-scale performance
   ↓
WP-E  full safe regression + protected-state seal
```

---

# 2. WP-A｜IA-05 Global Pytest Collection

## 2.1 当前错误

旧：

```text
tests/upgrade_m14/test_online_batches.py
```

仍导入：

```text
workbench_online.collector._commit_raw_and_batch
```

但正式 collector 已冻结为：

```text
HOT_RANK_CAPTURE_DISABLED_REQUEST_TIME_ONLY
```

因此 collection ImportError 是测试语义过时，不是应该恢复旧写入口。

## 2.2 禁止方案

禁止：
- 重新实现 `_commit_raw_and_batch`；
- 恢复 hot-rank historical capture；
- silent skip；
- pytest ignore；
- 删除测试不留历史；
- 仅改 import 让旧断言“假绿”。

## 2.3 正式 supersession

必须：

1. 保存旧测试 historical identity：
   - path；
   - SHA；
   - source commit；
   - old assertions；
   - supersession reason。

2. 当前 test surface 改为验证现行合同：
   - `collect_ths_hot_rank()` 必须 disabled；
   - `collect_eastmoney_hot_rank()` 必须 disabled；
   - 调用不得产生 raw payload/batch/history；
   - request-time `fetch_ths_hot_rank` normalization 保持；
   - online migration/table存在不代表 capture enabled。

3. 输出：

```text
IA05_M14_TEST_SUPERSESSION_RECEIPT.json
```

明确：

```text
old persistence test = historical-only
current test = request-time-only
```

## 2.4 Collection closure

修复后运行：

```text
python -m pytest --collect-only -q
```

必须完整结束，无 collection error。

如果还有其它收集错误：
- 本卡继续逐个分类；
- stale/dead test debt 同轮正式 supersede；
- 如果出现真正新业务算法 blocker，必须登记 `NEW_BLOCKER`，不能 ignore。

---

# 3. WP-A2｜DM01 legacy acceptance-state P2

## 3.1 当前错误

旧测试：

```text
tests.v4_dm01_r4.test_runtime::
test_current_real_v2_parent_and_future_wait
```

仍期待：

```text
PENDING_DM01_R4_EXTERNAL_ACCEPTANCE
```

当前 accepted envelope 已经：

```text
EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME
```

所以旧 expectation 已过时。

## 3.2 禁止方案

禁止：
- 撤销 accepted head；
- 放宽 source/R25 gate；
- 改九组件数值核；
- 删除历史 test。

## 3.3 双 fixture

建立：

### HISTORICAL_PRE_ACCEPTANCE

exact bind 当时：
- acceptance predecessor；
- calendar；
- data head；
- runtime contract；
- old blocker。

要求：

```text
missing/unaccepted authority -> fail closed
```

### CURRENT_ACCEPTED_RUNTIME

exact bind 当前：
- DM01_R4_RUNTIME_ACCEPTANCE_HEAD_V1；
- R4R1/R4R2 independent acceptance；
- current data head；
- runtime contract。

要求：

```text
accepted envelope -> 不再抛旧 PENDING acceptance error
```

优先用 additive conftest/historical reader，不直接破坏 old test history。

输出：

```text
DM01_LEGACY_TEST_SUPERSESSION_PROOF.json
```

---

# 4. WP-B｜IA-08 Historical Provenance Routing

## 4.1 当前事实

历史 inventory：

```text
4797 bindings
4777 current literal match
20 mismatch
15 unique historical identities
```

15 个旧 identities 都能从 Git 找回。

所以问题不是历史损坏，而是：

```text
historical exact reader
和
current checkout reader
```

边界未完整 formalize。

## 4.2 目标

建立明确双路由。

Historical：

```text
accepted binding
→ historical registry
→ exact Git blob/archive
→ exact SHA/bytes
```

Current：

```text
CurrentStageAuthority/current accepted head
→ current bytes
```

禁止：

```text
historical missing -> fallback current file
generic normalize
修改 historical SHA
old validator 自动授权 current runtime
```

## 4.3 Historical registry

建立/扩展版本化 registry，逐条覆盖 20 mismatch：

```text
historical_path
accepted_sha
accepted_bytes
source_commit
git_blob_oid
reader_mode
current_path_if_any
current_consumer_authority
```

必须 20/20、15/15 全覆盖。

## 4.4 V4-13 类旧 validator

类似：

```text
v4_13_accepted_contract_package.current_contracts()
```

只能服务其 pinned historical stage。

当前 stage 15 consumer 使用 current stage-aware successor。

禁止把 old validator 改成“任意 stage 都接受”。

## 4.5 Closure tests

至少：
- 20/20 historical mismatch exact read；
- 15/15 identity；
- wrong blob reject；
- wrong SHA reject；
- unknown binding reject；
- current consumer不读old bytes；
- historical reader不授current permission；
- clean checkout；
- Windows path / CRLF 仅按 portability registry处理。

成功：

```text
IA-08 = CANDIDATE_FIXED
```

---

# 5. WP-C｜IA-06 Current PG / FEP / Model Environment Verification

## 5.1 原则

只使用 disposable isolated environment。

禁止：
- production `market_research` destructive reset；
- 正式 FEP DB reset；
- 为过测试放松 FK/trigger/role；
- static SQL inspection 冒充实际执行。

## 5.2 PostgreSQL fresh / upgrade

建立两个 disposable databases：

```text
FRESH
UPGRADE
```

记录：
- PostgreSQL version；
- cluster/system identifier；
- migration list + SHA；
- role；
- search_path；
- redacted DSN。

Fresh：
- 空库按正式 migration 顺序安装。

Upgrade：
- 从 predecessor schema 状态升级。

至少覆盖 FEP 028～033 及其上游基础 schema。

## 5.3 运行当前 278 个 opt-in PG tests

现有：

```text
278 skipped PG cases
```

本轮不得继续 skip 结案。

配置隔离：

```text
FEP_E1_TEST_DSN
fresh/upgrade DSN
其它正式 test DSN
```

实际执行：
- fresh；
- upgrade；
- negative insert；
- FK；
- trigger；
- immutable guard；
- role；
- search_path；
- CAS；
- rollback；
- migration idempotency。

## 5.4 sklearn / E3 / E4

建立可复现 model verification environment。

优先从历史 accepted E3/E4 evidence 恢复 compatible versions。

若仓库没有 lock：
- 新增 additive test/runtime environment manifest；
- 不改模型公式/超参来适配环境。

记录：
- Python；
- numpy；
- sklearn；
- 相关依赖；
- lock/manifest digest。

实际执行：
- E3 fit；
- preprocessing parity；
- prediction parity；
- E4 challenger；
- serialized tree parity；
- accepted numeric tolerance。

不能把：

```text
model parity
```

写成：

```text
model effectiveness
```

## 5.5 TEMP / fixture roots

统一 TEMP/TMP/basetemp 到 IA-09 disposable root。

避免跨盘 tempfile 造成假失败。

成功：

```text
IA-06 = CANDIDATE_FIXED_CURRENT_ENV_VERIFIED
```

---

# 6. WP-D｜IA-07 Current-Scale Performance

## 6.1 不发明 SLA

旧 Phase0 baseline 自己明确：

```text
v4_runtime_row_count = 0
claims = diagnostic only
```

所以本轮不能凭空新增 SLA。

## 6.2 必测当前规模

至少：

```text
A. FEP E1 dataset construction
B. FEP E3 split/purge
C. V4-15 control freeze
D. Forward stock outcomes
E. Forward sector basket outcomes
F. current full-market daily/profile 或最接近正式 full-market path
```

输入必须来自：
- 当前 accepted/reconstructed engineering dataset；
- exact manifest；
- 不能只用 toy fixture 冒充 performance。

## 6.3 指标

记录：
- rows/entities/dates；
- wall time；
- CPU time；
- peak RSS；
- output bytes；
- artifact count；
- repeated-snapshot bytes；
- logical digest；
- correctness digest。

## 6.4 复杂度梯度

针对：

```text
E1 per-row population scan
E3 per-row later-row scan
V4-15 per-signal population controls
```

运行：

```text
small
medium
accepted/current scale
```

记录增长曲线。

## 6.5 需要优化时

允许：
- pre-aggregated population；
- partition boundary cache；
- immutable feature reuse；
- frozen control population index。

但必须证明：

```text
logical output equal
selection equal
weights equal
digests equal
```

禁止为了性能减少：
- universe；
- rows；
- horizons；
- controls；
- signals。

## 6.6 Closure wording

无正式 SLA 时只允许：

```text
CURRENT_ACCEPTED_SCALE_MEASURED
NO_RESOURCE_FAILURE
```

如果存在正式 contract budget，再按 budget 判定。

成功：

```text
IA-07 = CANDIDATE_FIXED_PERFORMANCE_EVIDENCE
```

---

# 7. WP-E｜Global Safe Regression

WP-A～D 完成后：

```text
pytest --collect-only
```

必须成功。

然后在 IA-09 repository-wide guard 下执行：

```text
default full pytest
```

保存：
- full log；
- JUnit；
- collected/passed/failed/error/skipped；
- skip reasons；
- protected fingerprint before/after；
- live DB/root access log。

目标：

```text
collection errors = 0
introduced failures = 0
```

只有 0 failure 才能写：

```text
GLOBAL_PYTEST_PASS = true
```

如果还有 failure：
- 每个 node 单独分类；
- 不允许 unclassified failure；
- 不允许 skip/ignore 冒充 green。

---

# 8. PASS_KEEP Regression

必须重跑：

```text
IA-01 stock vectors
IA-02 sector vectors
IA-03 maturity-state vectors
IA-04 price-domain vectors
IA-09 isolation critical
IA-10 CLI critical

Forward worker CAS/restart
R25 preflight
A08 capability resolver
FEP signal DB guard
V4-15 settlement
```

不得因为修测试、环境或 historical reader 破坏业务逻辑。

---

# 9. Protected State

必须保持：

```text
V4_STAGE_ACCEPTED_HEAD unchanged
V4_DATA_ACCEPTED_HEAD unchanged
V4_15_ACCEPTED_HEAD unchanged
Current Audit Head unchanged unless separately authorized

REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0

runtime_authorized = false
real_shadow_authorized = false
Production = false
Focus = false
Default UI = false

FEP_PRODUCTION = UNGRANTED
MODEL_DISPLAY = UNGRANTED
PRIORITY_USE = UNGRANTED
REAL_OOS = NOT_GRANTED
CHAMPION = NONE

TDX = NO WRITE
```

---

# 10. Required Evidence

统一目录：

```text
reports/forward_r2_remainder_consolidated_20261007/
```

至少：

```text
ENTRY_BASELINE.json

IA05_M14_TEST_SUPERSESSION_RECEIPT.json
GLOBAL_COLLECTION_RECEIPT.json
GLOBAL_PYTEST_RECEIPT.json

DM01_LEGACY_TEST_SUPERSESSION_PROOF.json

IA08_HISTORICAL_BINDING_INVENTORY.json
IA08_HISTORICAL_READER_PROOF.json
IA08_CURRENT_READER_PROOF.json

IA06_ENVIRONMENT_MANIFEST.json
IA06_PG_FRESH_RECEIPT.json
IA06_PG_UPGRADE_RECEIPT.json
IA06_PG_NEGATIVE_MATRIX.json
IA06_MODEL_RUNTIME_MANIFEST.json
IA06_E3_E4_PARITY_RECEIPT.json

IA07_PERFORMANCE_INPUT_MANIFEST.json
IA07_PERFORMANCE_MEASUREMENTS.json
IA07_COMPLEXITY_GROWTH.json
IA07_BEFORE_AFTER_PARITY.json

PASS_KEEP_REGRESSION.json
PROTECTED_FINGERPRINT_BEFORE.json
PROTECTED_FINGERPRINT_AFTER.json
PROTECTED_STATE_READBACK.json
OPEN_ISSUES_FINAL_DISPOSITION.json
CHANGED_FILE_LIST.json
CANDIDATE_SEAL.json
COMPLETION_REPORT.md
```

---

# 11. 成功条件

必须全部满足：

```text
IA-05 = CANDIDATE_FIXED
IA-06 = CANDIDATE_FIXED_CURRENT_ENV_VERIFIED
IA-07 = CANDIDATE_FIXED_PERFORMANCE_EVIDENCE
IA-08 = CANDIDATE_FIXED
DM01_LEGACY_P2 = CANDIDATE_FIXED

IA-01/02/03/04/09/10 = PASS_KEEP
protected-state drift = 0
TDX writes = 0
```

总状态只能是：

```text
V4_FORWARD_R2_REMAINDER =
CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT
```

不得自报：

```text
FIRST_REAL_SHADOW_AUTHORIZED
FORWARD_ACTIVE_RUNTIME_PROMOTED
PRODUCTION_READY
V4_22_FINAL_PASS
```

---

# 12. 本卡之后

如果本卡独立外审通过，则 IA-01～IA-10 和新增 DM01 legacy test debt 均完成处置。

下一步才进入：

```text
FORWARD_SUCCESSOR_ADMISSION_AND_RUNTIME_PROPAGATION
```

届时：
- 选定最终 Forward successor；
- exact bind runtime dependencies；
- worker admission；
- R25 rebuild；
- 仍需独立 activation audit；
- 不自动 grant First Real Shadow。

**文档结束**
