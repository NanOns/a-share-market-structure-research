# V4-08 R4-P0｜禁止特定股票代码特判治理补丁任务

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**审计基线 HEAD**：`097a22f3fd8f7be405eab6e64a4f513d2ec64413`  
**性质**：R4 入场前 P0 治理补丁  
**日期**：2026-09-30

---

# 1. 背景

R3 为关闭 11 个 target-day identity ambiguity，新增了一批一次性审计/证据生产代码。

独立检查确认：

- 正式 `src/sector/membership_admission_r3.py` 中不存在针对上述 11 个证券代码的运行时特判；
- migration 019 不包含具体证券代码；
- Sector/Rotation 正式算法合同不包含针对上述 11 个证券的买卖/信号特判；
- 但是 R3 的 audit/evidence support 文件中确实存在证券代码硬编码。

按照项目长期原则：

> 正式系统不得对某个具体股票、某组具体股票建立代码级例外逻辑、阈值覆盖、白名单/黑名单、信号修正、生命周期手工分支或其他 hidden special case。

因此在 R4 第一张正式 PIT membership materialization 之前，必须增加治理门。

---

# 2. 当前发现

## 2.1 `scripts/build_v4_08_r3_admission_evidence.py`

存在：

```python
KEYS=[
  'SH.601206',
  'SH.603302',
  'SH.603361',
  'SH.688688',
  'SZ.001235',
  'SZ.001246',
  'SZ.300728',
  'SZ.301569',
  'SZ.301660',
  'SZ.301716',
  'SZ.301718'
]
```

并存在：

```python
if key in ['SZ.301569','SZ.301660','SZ.301718']
```

用于生成 reason 分类。

这属于 target-specific evidence builder，不应保留为可复用系统逻辑。

---

## 2.2 `scripts/postcheck_v4_08_r3_admission.py`

存在固定 11-key set：

```python
{
 'SH.601206',
 ...
 'SZ.301718'
}
```

Verifier 应从冻结输入 artifact 推导 expected scope，而不是自己写死证券代码。

---

## 2.3 `config/v4_08_r3_lifecycle_source_contract_v1.json`

该文件位于通用 `config/` 下，但内容是 R3 一次性审计 source manifest：

- 明确列出具体股票代码；
- 明确列出针对这些股票的公告 URL；
- 明确列出具体公司名称/代码 expected phrases。

该文件不应被视作 production configuration。

---

## 2.4 `scripts/capture_v4_08_r3_sources.py`

代码本身没有直接写上述证券代码，但会读取：

```text
config/v4_08_r3_lifecycle_source_contract_v1.json
```

因此它是 target-specific audit capture utility，不应进入日常 runtime pipeline。

---

## 2.5 Test fixture

`run_v4_08_r3_isolated_verification.py` 中存在：

```text
SH.600001
```

但它只用于 disposable PostgreSQL synthetic fixture。

允许测试 fixture 使用虚构/样本证券代码，但必须与 production runtime 隔离。

---

# 3. 当前风险判定

本轮未发现证据表明正式 Sector/Rotation/Member admission runtime 已按某只股票代码做特判。

所以：

```text
PRODUCTION_STOCK_SPECIFIC_SIGNAL_LOGIC_FOUND = NO
```

但：

```text
AUDIT_SUPPORT_HARDCODED_SYMBOLS_FOUND = YES
```

并且这些文件目前位于：

```text
scripts/
config/
```

存在未来被误接入正式流程的治理风险。

因此：

```text
R4_P0_GOVERNANCE_REPAIR_REQUIRED
```

---

# 4. 总原则

正式 runtime 的所有证券处理必须是：

```text
DATA_DRIVEN
CONTRACT_DRIVEN
IDENTITY_DRIVEN
LIFECYCLE_DRIVEN
```

严禁：

```text
if code == "xxxxxx"
if symbol in {"xxxxxx", ...}
special_thresholds["xxxxxx"]
manual_allowlist = [...]
manual_blocklist = [...]
security_id == "SEC-..."
```

来改变：

- universe；
- lifecycle；
- board；
- factor；
- state；
- signal；
- PREWATCH；
- Rotation；
- Focus；
- risk；
- ranking；
- explainability；
- acceptance。

---

# 5. 允许出现具体股票代码的区域

允许具体证券代码存在于以下**非生产语义**区域：

```text
reports/
docs/evidence/
data/.../source_evidence/
tests/fixtures/
tests/ golden cases
immutable audit artifacts
user-provided focus/watchlist data
```

条件：

- 仅作为事实样本、审计对象或回归 fixture；
- 不被 runtime 自动导入为规则；
- 不改变其他证券的算法；
- 不成为白名单/黑名单；
- 不成为默认参数覆盖。

---

# 6. P0-A｜R3 11-key scope 改为 artifact-driven

删除：

```python
KEYS=[...]
```

改为从 R2 冻结 artifact 中读取：

```text
required unresolved / ambiguous target keys
```

例如绑定：

```text
reports/v4_08/V4_08_R2_IDENTITY_SCOPE_CLASSIFICATION.json
```

或 R3 专用 immutable audit-input artifact。

必须校验：

```text
input artifact sha256
target date
scope definition
key count
```

任何新增/减少由输入数据决定，不由代码修改决定。

---

# 7. P0-B｜删除 symbol-specific classification branch

删除类似：

```python
if key in ['SZ.301569','SZ.301660','SZ.301718']:
    reason = ...
else:
    reason = ...
```

分类必须由通用 evidence fields 得出，例如：

```text
active_exchange_catalogue_present
listing_date
issuance_status
suspension/termination evidence
security_type
exchange
board
target_date
```

reason 是事实组合的结果，不得由具体代码选择。

---

# 8. P0-C｜Postcheck 不得写死 expected symbols

`postcheck_v4_08_r3_admission.py` 必须：

```text
read frozen audit input scope
→ independently recompute dispositions
→ compare sets
```

禁止 verifier 自己再复制一份 literal symbol list。

否则 producer 与 verifier 可能共享同一个遗漏。

---

# 9. P0-D｜Lifecycle source manifest 移出 production config

将：

```text
config/v4_08_r3_lifecycle_source_contract_v1.json
```

重新分类为：

```text
AUDIT_ONLY / IMMUTABLE_EVIDENCE_INPUT
```

建议迁移至：

```text
reports/v4_08/audit_inputs/
```

或：

```text
data/v4/source_evidence/v4_08_r3/manifests/
```

并新增字段：

```json
{
  "runtime_authorized": false,
  "scope": "R3_IDENTITY_AUDIT_ONLY",
  "target_specific": true
}
```

正式 runtime config 不得引用它。

---

# 10. P0-E｜Source capture 泛化

正式未来 identity/lifecycle capture 应使用：

```text
unresolved identity artifact
+
provider query template
+
generic active catalogue
+
generic lifecycle source registry
```

动态生成 request。

允许人工补充某只股票历史公告，作为：

```text
supplemental audit evidence
```

但不得把 URL/代码加入 production rule config。

---

# 11. P0-F｜新增静态硬门

增加：

```text
NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC
```

建议测试：

```text
tests/governance/test_no_symbol_specific_runtime_logic.py
```

扫描至少：

```text
src/
src/workbench_db/migrations/
production runtime config
production pipeline scripts
```

检测：

```regex
(?:SH|SZ|BJ)\.\d{6}
(?<!\d)[03689]\d{5}(?!\d)
SEC-[A-F0-9]{16,}
```

但需要排除：

```text
hash/digest
date
test fixture
evidence path
schema examples
document strings
```

更可靠的方式是 AST + path policy：

- Python string literals；
- membership tests；
- comparisons；
- dict keys；
- lists/sets；
- config symbol arrays。

---

# 12. 禁止模式

以下出现在正式 runtime 即 FAIL：

```python
if code == '001246':
    ...

if symbol in {'SZ.001246','SZ.301716'}:
    ...

SPECIAL_CASES = {
    '600018': ...
}

threshold_by_symbol = {
    '300xxx': ...
}
```

以下 SQL 同样 FAIL：

```sql
WHERE security_code IN ('001246', ...)
CASE WHEN security_code='xxxxxx' THEN ...
```

---

# 13. 允许模式

测试 fixture：

```python
fixture_symbol = 'SH.600001'
```

允许，但文件必须位于 test/audit-only scope。

用户显式关注池：

```text
Focus / Watchlist
```

可以存具体代码，因为它是**用户输入数据**，不是算法 special case。

历史 identity event artifact 也可以记录真实代码，因为它是事实数据。

---

# 14. Runtime Boundary Registry

建议新增：

```text
config/runtime_path_policy_v1.json
```

明确：

```text
PRODUCTION_RUNTIME
AUDIT_ONLY
TEST_ONLY
EVIDENCE_ONLY
USER_DATA
```

每个可能包含 symbol 的 artifact/file family 必须归类。

静态门只允许 `AUDIT_ONLY / TEST_ONLY / EVIDENCE_ONLY / USER_DATA` 出现 specific symbol literals。

---

# 15. R4 入场门

R4 第一张正式 PIT snapshot 之前必须提供：

```text
V4_08_R4_P0_NO_SYMBOL_SPECIFIC_RUNTIME_SCAN.json
```

内容至少：

```text
scanned_paths
runtime_file_count
literal_symbol_hits
production_runtime_hits
audit_only_hits
test_only_hits
false_positive_hits
status
```

正式要求：

```text
production_runtime_hits = 0
```

---

# 16. 本轮已知文件处置

以下必须明确为 audit-only 或重构：

```text
scripts/build_v4_08_r3_admission_evidence.py
scripts/postcheck_v4_08_r3_admission.py
scripts/capture_v4_08_r3_sources.py
config/v4_08_r3_lifecycle_source_contract_v1.json
```

现有 R3 evidence 不删除、不覆盖。

它们可以保留作为历史审计可复现材料，但不能作为未来 production runtime entrypoint。

---

# 17. 对 R3 验收结论的影响

R3 已获得的以下事实结论不撤销：

```text
B07 = PASS
B08 = PASS
11-key target-day adjudication evidence = VALID
identity candidate evidence = VALID
calendar candidate evidence = VALID
```

但是在 R4 执行 external promotion 前增加治理门：

```text
R4-P0 NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC
```

只有：

```text
production_runtime_hits = 0
```

才允许进入：

```text
identity promotion
calendar promotion
first PIT materialization
```

---

# 18. 长期硬规则

从此阶段起：

> 任何正式算法、数据准入、信号、排序、状态机、风险、前端候选生成，不允许因某个具体证券代码或某个固定证券集合改变逻辑。

如果真实市场中出现特殊证券情况，应抽象成：

```text
security_type
board
listing status
special treatment status
corporate action
price phase
trading status
liquidity state
data quality
lifecycle event
```

等**可泛化属性**处理，而不是写股票代码。

---

# 19. 最终验收口径

```text
NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC = HARD_GATE
```

任何 production runtime hit：

```text
=> FAIL
=> V4-08 formal promotion blocked
```

Audit/test/evidence symbol literals：

```text
=> allowed only with explicit non-runtime classification
```
