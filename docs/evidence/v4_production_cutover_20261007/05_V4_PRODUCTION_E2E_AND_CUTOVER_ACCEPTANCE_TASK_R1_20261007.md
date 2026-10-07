# P0-5｜V4 Production E2E + 原子切换验收任务卡 R1｜2026-10-07

- Priority: P0 FINAL
- Depends on: P0-1/P0-2/P0-3/P0-4
- 本卡完成后允许正式切换默认生产入口。

## 1. 原则

这不是“页面能打开”验收。

必须同时证明：

```text
真实 accepted data 可读
没有下一交易日时仍可读
全站 UNKNOWN 已消失
V4 是默认 UI
legacy 不再是默认依赖
Shadow 仍保持真实语义
TDX 零写
V4 regression 无回归
生产 authority 可回滚
```

---

## 2. Baseline

记录执行时最新：

```text
branch HEAD
working tree
accepted stage authority
accepted data head
production authority pre-state
TDX fingerprints
DB schema identity
```

---

## 3. Fresh V4-only full regression

本轮必须做一次**真实新鲜的单次 V4-only 全量执行**。

不得只做：

```text
prior accepted profile + additional nodes reconciliation
```

要求：

```text
scope selector 包含当前全部 V4 tests
test_r17a_historical_governance.py included
new production tests included
collection errors = 0
failed = 0
errors = 0
ignore = 0
deselect = 0
new xfail = 0
```

允许平台 symlink skip 仅在：

```text
已有 portable equivalent PASS
```

---

## 4. Production live E2E

启动正式 V4 默认工作台，不使用 test fixture：

```text
run_workbench_service.py --v4-default
```

若保留 `--v4-production` 兼容别名，其语义也必须是“V4 产品默认工作台”，不得自动提升 capability permission。

实际 HTTP 验证：

```text
/
 /v4
/api/operations/status
/api/v4/current/context
/api/v4/current/summary
/api/v4/current/radar
/api/v4/current/entity
/api/v4/current/sector
/api/v4/current/cohort
/api/v4/current/settlement
/api/v4/current/health
/v4/shadow
/api/v4/shadow/context
```

---

## 5. Current accepted data gate

当前 production 页面必须至少证明：

```text
accepted_trade_date = repository current accepted date
context != null
data head verified
stage head verified
source quality known/degraded by field
```

并对 source inventory 中“应有 accepted 数据”的模块验证：

```text
至少一个真实 KNOWN/DEGRADED 值
```

禁止整个模块全部：

```text
UNKNOWN / SOURCE_FIELD_UNAVAILABLE
```

仅因“没有下一 trade date”。

---

## 6. No-next-day gate

专门冻结：

```text
no newer accepted input
```

验证：

```text
root = 200
current context = 200
status = READY_CURRENT_ACCEPTED
freshness = WAIT_NEXT_ACCEPTED_INPUT
last accepted rows remain visible
```

---

## 7. Shadow separation gate

当前 real Shadow 如仍为 0：

```text
/v4/shadow
```

必须诚实显示：

```text
NO_REAL_SHADOW_DATA
```

同时：

```text
/ (production)
```

仍正常展示 current accepted data。

这是本轮最关键反例。

---

## 8. Screenshot acceptance

真实运行截图至少：

```text
01_HOME_CURRENT_ACCEPTED.png
02_WHY_NOW.png
03_RADAR.png
04_ENTITY_AND_SECTOR.png
05_FORWARD_STATE.png
06_HEALTH_AND_FRESHNESS.png
07_SHADOW_NO_REAL_DATA.png
```

不得用 mock / fixture 截图。

---

## 9. TDX zero-write

执行前后：

```text
path
size
sha256
mtime
```

必须完全一致。

所有写入只能进入：

```text
V4 production store
reports
accepted artifact staging
```

不得进入 TDX root。

---

## 10. Authority cutover

所有 gate PASS 后，原子执行：

```text
product_version -> V4
default_ui_shell -> V4
current_accepted_read_authority -> V4_CURRENT_ACCEPTED
legacy_shell_default -> false
```

同时必须证明：

```text
production_permission[*] 与 V4-19 exact receipts 一致
不存在因 UI cutover 被强制改为 true 的 capability
```

模块在 permission=false 但 V4 accepted data 可读时：

```text
source_mode = V4_ACCEPTED_RESEARCH_READONLY
```

然后重新启动一次正式服务，再做一遍 live smoke。

不得要求用户再确认一次才切换；本轮用户已经明确授权。

---

## 11. Rollback rehearsal

切换后做一次 disposable rollback rehearsal：

```text
V4 production pointer -> previous accepted V4 pointer -> current V4 pointer
```

要求：

```text
deterministic
digest exact
no V3 fallback
```

---

## 12. Required evidence

目录：

```text
reports/v4_production_cutover_20261007/
```

至少：

```text
ENTRY_BASELINE.json
CURRENT_COMPONENT_OWNER_INVENTORY.json
CURRENT_READER_RECEIPT.json
NO_NEW_DAY_RECEIPT.json
UI_E2E_RECEIPT.json
SERVICE_E2E_RECEIPT.json
SHADOW_SEPARATION_RECEIPT.json
PRODUCTION_AUTHORITY_PRE.json
PRODUCTION_AUTHORITY_POST.json
ROLLBACK_RECEIPT.json
TDX_PRE_FINGERPRINT.json
TDX_POST_FINGERPRINT.json
V4_ONLY_EXECUTION_SCOPE.json
V4_ONLY_FULL_REGRESSION_RECEIPT.json
LIVE_HTTP_RECEIPT.json
SCREENSHOT_MANIFEST.json
PROTECTED_STATE_READBACK.json
OPEN_ISSUES.json
CANDIDATE_SEAL.json
COMPLETION_REPORT.md
```

---

## 13. Final candidate status

只有全部通过才允许：

```text
V4_PRODUCT_VERSION_CUTOVER =
CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT

V4_DEFAULT_UI_SHELL =
ACTIVE

V4_CURRENT_ACCEPTED_READER =
ACTIVE

V4_ACCEPTED_RESEARCH_READONLY =
ACTIVE

V4_SHADOW_DIAGNOSTIC =
ACTIVE_SEPARATE_SCOPE

CAPABILITY_PRODUCTION_PERMISSION =
UNCHANGED_EXCEPT_BY_VALID_V4_19_RECEIPTS
```

仍不得写：

```text
FORWARD_EFFECTIVENESS_FULL_PASS
REAL_SHADOW_ACCEPTED
AUTO_TRADING_READY
```

除非对应证据独立存在。

---

## 14. Git delivery

完成后：

```text
commit
push codex/v4-system-reform
```

并明确给出：

```text
final commit SHA
changed files
test receipt path
live screenshot path
production authority path
```

然后停止，等待独立外部验收。

## 15. 已接受合同回归

必须重新执行并验证：

```text
tests/test_v4_19_focus_cutover_contract.py
tests/test_v4_20_default_ui_contract.py
```

同时新增 v2 tests，确保：

```text
V4_ACCEPTED_RESEARCH_READONLY != PRODUCTION_V4_PROVISIONAL
default V4 shell != GLOBAL_V4_PASS
UI visibility != Focus source cutover
UI visibility != Shadow Stable evidence
```
