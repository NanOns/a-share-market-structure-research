# V4 Forward R2｜最终剩余阻断修复任务卡 R3｜2026-10-07

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 执行基线: `a775383eabb94e97a6022f34a30de7aa55e3a39c`
- 性质: 只修当前外审未闭环项；禁止返工已通过 IA-01/02/03/04/06/08/09/10。

## 0. 唯一范围

必须处理：

```text
P1-A  TDX_READ_ONLY_BOUNDARY_INCIDENT
P1-B  IA-05 GLOBAL REGRESSION / 60 HISTORICAL ARTIFACT FAILURES

GOV-1 PREEXISTING_V1_CURRENT_RELEASE_IDENTITY_DRIFT

P2-A  IA-07 CONTROL_MATCHING_PERFORMANCE_NOT_VERIFIED

ENV-1 V3 isolated UI live test
ENV-2 Windows symlink/reparse validation x2
```

PASS_KEEP：

```text
IA-01
IA-02
IA-03
IA-04
IA-06
IA-08
IA-09
IA-10
DM01_LEGACY_P2
```

---

# 1. P1-A｜TDX Read-Only Boundary

## 1.1 永久保留事故

不得删除或改写：

```text
TDX_write_calls = 5
affected_unique_files = 4
FAILED_RUN_TDX_ZERO_WRITE = false
```

事故必须永久作为 historical incident。

## 1.2 修代码

所有：
- profile copier；
- historical fixture materializer；
- test artifact builder；
- path join helper

必须在任何 mkdir/open/write 前执行：

```text
reject absolute source path as destination
reject drive-letter path
reject UNC path
reject path traversal
reject resolved path outside disposable output root
reject configured TDX/source roots
```

不得依赖：

```python
out / absolute_path
```

的 Path 行为。

统一使用一套：

```text
resolve_destination_inside_root()
```

或等价 helper。

## 1.3 Negative matrix

至少：

```text
TDX-01 D:/new_tdx/... -> reject before write
TDX-02 D:\\new_tdx\\... -> reject
TDX-03 UNC -> reject
TDX-04 ../ escape -> reject
TDX-05 symlink/junction escape -> reject
TDX-06 normal relative path -> disposable root only
TDX-07 duplicate slash representation -> same rejection
TDX-08 child process -> same guard
```

## 1.4 新一轮 acceptance 必须先取 TDX fingerprint

在任何测试前，对 configured TDX roots 建：

```text
path
size
sha256
mtime
```

执行完整测试后再取一次。

要求：

```text
BEFORE == AFTER
write calls = 0
```

本轮不得再尝试修改 TDX mtime 或“恢复”文件。

## 1.5 内容完整性追溯

对事故 4 文件搜索：
- pre-task repository evidence；
- historical manifests；
- archived source snapshots；
- local approved backups。

若找到事故前独立 digest：
- exact compare。

若找不到：
- 明确保留 `PRE_INCIDENT_CONTENT_NOT_INDEPENDENTLY_VERIFIABLE`；
- 不能伪称内容零变化；
- 但可在修复后的 fresh run 证明未来 zero-write。

关闭状态只能：

```text
TDX_INCIDENT =
CLOSED_WITH_BOUNDARY_REPAIR_AND_FRESH_ZERO_WRITE_RUN
FAILED_RUN_ZERO_WRITE = false
```

---

# 2. P1-B｜IA-05 60 个历史产物失败

## 2.1 先做 active dependency classification

对全部 60 failure nodes 与缺失 artifact，逐项判：

```text
ACTIVE_CURRENT_AUTHORITY
HISTORICAL_ONLY_SUPERSEDED
UNKNOWN
```

必须有 consumer graph。

### ACTIVE_CURRENT_AUTHORITY
只能：
- exact recover original bytes；
- 或保持 blocker。

不得 supersede。

### HISTORICAL_ONLY_SUPERSEDED
允许正式 test supersession。

### UNKNOWN
保持 blocker。

## 2.2 Bounded recovery search

对每个缺失 artifact：
- git all refs；
- checked-in LFS；
- approved local archive roots；
- project evidence archives。

记录 exact search scope。

不得造同名文件。

## 2.3 Formal test supersession

仅对 `HISTORICAL_ONLY_SUPERSEDED`：

必须同时保存：
- old test exact bytes；
- old artifact path；
- old expectation；
- historical stage/release identity；
- reason it is no longer a current release test；
- successor current authority；
- successor current test。

禁止：
- skip；
- ignore；
- deselect；
- xfail 冒充 closure。

正确做法是版本化 test profile / historical suite：
- historical profile 仍声明 `REQUIRES_ARCHIVED_ARTIFACT`；
- current default suite 只收 current-authority tests；
- profile selection 必须由版本化合同控制，不靠隐式 pytest config。

## 2.4 必须解决全部 60 nodes

最终 disposition：

```text
recovered_exact
or
formally_superseded_historical_only
```

不能存在：
- OPEN；
- UNKNOWN；
- unclassified failure。

---

# 3. GOV-1｜Current V1 Release Identity Drift

## 3.1 先查 active consumers

对：

```text
reports/current/CURRENT_RELEASE.json
```

建立 current consumer inventory：
- backend；
- UI；
- fallback；
- CLI；
- tests；
- migration/readers。

## 3.2 两种合法处置

### 如果仍是 active current authority

不得改旧 pointer。

创建正式 successor release：
- bind current `config/trading_calendar.yaml`；
- bind current `src/phase1_runner.py`；
- exact current computation identity；
- current accepted dependencies；
- parity / regression；
- independent release receipt。

### 如果已是 historical-only

把旧 `CURRENT_RELEASE.json` 明确冻结为 historical release：
- current readers 不再把它当 current bytes；
- current tests 改绑定 current successor authority；
- old release remains immutable。

## 3.3 禁止

```text
rewrite CURRENT_RELEASE.json
patch expected SHA in old release
pretend historical replay == current release acceptance
```

成功：

```text
V1_CURRENT_RELEASE_IDENTITY_DRIFT = CLOSED
```

---

# 4. P2-A｜IA-07 Controls Performance Closure

现有 evidence 不足，因为：

```text
controls_current_rank_complete = 0
```

必须找到或构造来自 accepted/reconstructed owner 的完整 feature population，至少具备当前 control matching 所需：

```text
prior20_mean_amount
vol20
RPS20
hard_safety
industry where applicable
```

禁止 synthetic row expansion。

## 4.1 必测

在接近 current full-market entity count 上：
- 对全部 eligible signals 做 `freeze_controls`；
- 真正运行 rank / distance / candidate matching；
- 记录候选池规模、signals、comparisons。

## 4.2 指标

```text
wall
CPU
peak RSS
output bytes
comparisons
signals
entities
dates
logical digest
```

small / medium / accepted-current 三档。

## 4.3 如果 accepted owner 当前确实没有完整 feature population

不得伪造。

状态必须：

```text
CONTROL_MATCHING_PERFORMANCE =
NOT_VERIFIABLE_BY_CURRENT_ACCEPTED_CAPABILITY
```

然后判断该能力是否 current runtime required：
- required -> blocker；
- not currently grantable -> capability-scoped debt，明确不阻断 unrelated stock-only runtime。

不能写 `IA-07 FULL PASS`。

---

# 5. ENV validation

## 5.1 V3 UI

不要依赖用户手工启动本地服务。

测试必须：
- isolated disposable service fixture；
- ephemeral port；
- read-only/disposable DB；
- start -> request -> stop；
- no production roots。

关闭：

```text
V3_UI_ENV_VALIDATION = PASS
```

## 5.2 Symlink / reparse

真实 symlink privilege 可用时继续跑原测试。

不可用时增加 portable Windows path-escape proof：
- junction/reparse if available；
- otherwise unit-level resolver counterexample + child-process path check。

不得删除真实 symlink test。

最终 skip 若仍存在，必须是明确 platform capability skip，并有 portable equivalent PASS。

---

# 6. PASS_KEEP

必须重新跑：

```text
IA-01..04
IA-06
IA-08
IA-09
IA-10
DM01 legacy
FEP PG negative/CAS
E3/E4 parity
Forward V1.2
R25
A08 resolver
```

禁止 current fix 破坏这些已通过项。

---

# 7. 最终回归

修完后：

```text
pytest --collect-only
```

要求：

```text
collection errors = 0
ignore = 0
deselect = 0
```

然后 current default profile 全仓执行。

目标：

```text
failed = 0
errors = 0
```

允许少量明确 platform skip，但每个 skip 必须：
- exact node；
- capability reason；
- portable equivalent PASS；
- 不能覆盖业务失败。

另执行 historical profile：
- recovered artifact tests PASS；
- unrecoverable but formally superseded tests 输出 `HISTORICAL_ARTIFACT_UNAVAILABLE_FORMALLY_SUPERSEDED`，不作为 current release PASS 证据。

---

# 8. Required Evidence

目录：

```text
reports/forward_r2_final_blocker_repair_20261007/
```

至少：

```text
ENTRY_BASELINE.json

TDX_PRE_FINGERPRINT.json
TDX_POST_FINGERPRINT.json
TDX_PATH_GUARD_NEGATIVE_MATRIX.json
TDX_INCIDENT_FINAL_DISPOSITION.json

IA05_60_NODE_DEPENDENCY_CLASSIFICATION.json
IA05_ARTIFACT_RECOVERY_SEARCH.json
IA05_FORMAL_SUPERSESSION_REGISTRY.json
IA05_CURRENT_PROFILE_RECEIPT.json
IA05_HISTORICAL_PROFILE_RECEIPT.json

V1_CURRENT_RELEASE_CONSUMER_INVENTORY.json
V1_RELEASE_IDENTITY_FINAL_DISPOSITION.json

IA07_CONTROL_FEATURE_OWNER_BINDING.json
IA07_CONTROL_MATCHING_PERFORMANCE.json
IA07_FINAL_DISPOSITION.json

ENV_UI_SERVICE_RECEIPT.json
ENV_SYMLINK_PORTABLE_RECEIPT.json

GLOBAL_COLLECTION_RECEIPT.json
GLOBAL_CURRENT_PYTEST_RECEIPT.json
PASS_KEEP_REGRESSION.json
PROTECTED_STATE_READBACK.json
OPEN_ISSUES_FINAL.json
CANDIDATE_SEAL.json
COMPLETION_REPORT.md
```

---

# 9. Protected state

必须：

```text
accepted heads unchanged
Current Audit Head unchanged unless separately authorized
TDX ZERO WRITE in fresh acceptance run
REAL_SHADOW_OBSERVATIONS = 0
PIT_OBSERVED_REAL_SAMPLES = 0
runtime_authorized = false
real_shadow_authorized = false
production = false
focus = false
default_ui = false
FEP permissions unchanged
```

---

# 10. 完成条件

只有：

```text
TDX fresh run zero-write = PASS

IA-05 current profile =
0 failed / 0 errors

60 historical failures =
100% recovered or formally superseded

V1 current release identity =
CLOSED

IA-07 =
FULL PASS or explicitly capability-scoped NOT_VERIFIABLE with non-required runtime proof

environment validation =
closed with portable equivalents

PASS_KEEP =
all preserved
```

才允许：

```text
V4_FORWARD_R2_FINAL_BLOCKER_REPAIR =
CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT
```

仍不得自报：
- runtime promotion；
- First Real Shadow grant；
- production ready；
- V4-22 final pass。

本卡通过独立外审后，才讨论 Forward successor admission / runtime propagation。
