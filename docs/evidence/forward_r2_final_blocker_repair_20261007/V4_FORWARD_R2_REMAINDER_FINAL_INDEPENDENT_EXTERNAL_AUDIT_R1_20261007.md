# V4 Forward R2 Remainder｜独立外部验收审计 R1｜2026-10-07

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 执行基线: `433c3378d4bc4db572f95de20cadbf899c2a04ce`
- 当前远端 HEAD: `a775383eabb94e97a6022f34a30de7aa55e3a39c`
- 任务: `V4_FORWARD_REPAIR_R2_REMAINDER_CONSOLIDATED_TASK_R2_20261007.md`

## 1. 唯一总裁决

```text
V4_FORWARD_R2_REMAINDER_EXTERNAL_AUDIT =
BLOCKED_NOT_READY_FOR_EXTERNAL_ACCEPTANCE
```

当前状态：

```text
IA-01 = PASS_KEEP
IA-02 = PASS_KEEP
IA-03 = PASS_KEEP
IA-04 = PASS_KEEP
IA-09 = PASS_KEEP
IA-10 = PASS_KEEP

DM01_LEGACY_P2 = PASS_CANDIDATE
IA-06 = PASS_CANDIDATE_CURRENT_ENV_VERIFIED
IA-08 = PASS_CANDIDATE_HISTORICAL_ROUTING

IA-07 = PARTIAL_NOT_CLOSED
IA-05 = OPEN_P1

TDX_READ_ONLY_BOUNDARY = NEW_BLOCKER_P1
PREEXISTING_V1_CURRENT_RELEASE_IDENTITY_DRIFT = OPEN_RELEASE_GOVERNANCE
```

仍然：

```text
ACTIVE_FORWARD_RUNTIME_PROMOTION = NOT_GRANTED
FIRST_REAL_SHADOW = NOT_GRANTED
PRODUCTION = false
```

## 2. Global collection 与 full pytest

Collection 已修复：

```text
collected = 6148
collection errors = 0
ignore = []
deselect = []
GLOBAL_COLLECTION = PASS
```

但完整回归：

```text
6148 total
6085 passed
60 failed
3 skipped
0 errors
```

因此：

```text
GLOBAL_PYTEST_PASS = false
IA-05 = OPEN
```

这 60 个失败全部被归类为：

```text
HISTORICAL_ARTIFACT_UNAVAILABLE
```

不是 60 个新算法反例。

主要缺失历史产物包括：
- `reports/shadow/v2/20260904/*`
- `reports/releases/20260904/695c7ae5.../stocks.csv`
- `PRODUCTION_RECEIPT.json`
- `data/forward/observations/20260904/revision_3/OBSERVATION_IDENTITY.json`
- 多个 upgrade_m5/m6/m14/v3 历史 receipt。

执行方已经对全部当前本地 Git refs 做 exact path 查询，未找到这些原始产物，因此没有伪造同名文件。这一点处理正确。

但 60 个失败仍然真实存在，所以 IA-05 不能关闭。

## 3. IA-06｜通过候选外审

当前环境验证不是继续 skip。

### PostgreSQL

建立了 disposable fresh / upgrade 实例：
- PostgreSQL 18.6
- 独立 data directory
- 独立 system identifier
- production_access=false

迁移实际覆盖 001～033，且没有放松 constraints。

FEP DB negative / role / trigger / CAS / rollback 测试实际执行，之前大量 setup error 已修复为 PASS。

### E3 / E4

当前兼容环境：

```text
Python 3.13.14
numpy 2.2.6
scikit-learn 1.7.2
scipy 1.16.2
joblib 1.5.2
threadpoolctl 3.6.0
```

E3/E4 对 accepted rows 重新做 prediction/serialization parity：

```text
TRAIN exact
INTERNAL_TUNE exact
CALIBRATION exact
OUTER_TEST exact
tree sklearn delta = 0
```

且：

```text
CHAMPION = false
REAL_OOS = false
```

没有把环境验证包装成模型有效性。

结论：

```text
IA-06 = PASS_CANDIDATE_CURRENT_ENV_VERIFIED
```

## 4. IA-08｜通过候选外审

历史 binding 路由已经覆盖：

```text
20/20 mismatch occurrences
15/15 unique historical identities
```

Historical reader：
- exact Git blob；
- exact source commit；
- current_fallback=false；
- grants_current_permission=false。

Current reader：
- 绑定当前 `V4_00_TO_V4_15_ACCEPTED`
- 使用 current bytes；
- old V4-13 validator 仍保持 pinned historical semantics；
- 不通过放宽 old validator 来接收 stage15。

结论：

```text
IA-08 = PASS_CANDIDATE_HISTORICAL_ROUTING
```

## 5. DM01 Legacy P2｜通过候选外审

旧 pre-acceptance expectation 与 current accepted runtime 已拆开。

没有撤销：

```text
EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME
```

没有修改九组件数值核，也没有放松 R25/source gate。

结论：

```text
DM01_LEGACY_P2 = PASS_CANDIDATE
```

## 6. IA-07｜只能部分通过

当前性能证据有明显进展。

真实/accepted input：
- canonical daily：约 112 MB；
- full-market daily rows：4,026,611；
- entities：5,337；
- FEP model rows：4,553；
- current snapshot entities：5,037。

已测：
- E1 dataset assemble；
- E3 split/purge；
- full-market canonical scan；
- stock outcomes；
- sector outcomes；
- V4-15 control freeze。

资源没有失败。

但 evidence 同时明确：

```text
controls_current_rank_complete = 0
```

并写明：

```text
RESEARCH_MEMBERSHIP_AND_HARD_SAFETY_NOT_PROJECTED
BENCHMARK_CONTROLS_UNAVAILABLE
```

因此最初 IA-07 指出的高风险路径：

```text
V4-15 per-signal full population matching controls
```

并没有在真正 rank-complete/full-feature 当前输入上走到完整 expensive branch。

所以外部裁决：

```text
IA-07 =
PARTIAL_PASS_CURRENT_INPUT_SCOPE
CONTROL_MATCHING_PERFORMANCE_NOT_VERIFIED
```

## 7. 新 P1：TDX Read-Only Boundary Incident

这是本轮最严重的新问题。

实际发生：

```text
TDX_write_calls = 5
affected_unique_TDX_files = 4
TDX_ZERO_WRITE = false
```

涉及：

```text
D:/new_tdx/T0002/hq_cache/szs.tnf
D:/new_tdx/T0002/hq_cache/tdxhy.cfg
D:/new_tdx/vipdoc/sz/lday/sz302132.day
D:/new_tdx/vipdoc/sz/lday/sz300114.day
```

原因：historical simulation profile copier 接受 absolute binding path；`out / absolute_path` 发生路径逃逸，最终对 TDX 源文件做了 `read -> write_bytes(same bytes)`。

执行方记录为：
- byte-preserving write-back；
- mtime 被改变；
- 没有 pre-task TDX fingerprint；
- 没有再次写入尝试“恢复”mtime。

这比伪造“零写”更诚实，但依然违反项目硬规则：

```text
TDX = READ ONLY
```

仓库当前也找不到这 4 个事故后 SHA 的本轮前独立记录，因此本轮不能独立证明事故前后内容身份。

正确结论：

```text
TDX_READ_ONLY_BOUNDARY = NEW_BLOCKER_P1
FAILED_RUN_TDX_ZERO_WRITE = false
```

## 8. IA-05｜仍 OPEN

60 个失败不是业务新 bug，但仍是真失败。

正确处理只有两类：

### A. 历史产物仍属于 current/active authority

必须找回 exact original bytes / accepted identity，不得 supersede。

### B. 仅属于 superseded historical test

允许正式 test supersession，但必须：
- 原测试 bytes 归档；
- 原断言/原 artifact path 保留；
- 明确 successor authority；
- 新 current test 验证同一业务不变量；
- 不 silent skip；
- 不 pytest ignore；
- 不伪造旧 artifact。

当前尚未完成对 60 nodes 的全部正式 supersession，因此：

```text
IA-05 = OPEN_P1
```

## 9. Current V1 release computation identity drift

历史 V1 computation identity 可 exact replay：

```text
status = PASS_HISTORICAL_ONLY
```

但 current checkout 与旧 `CURRENT_RELEASE.json` 的 identity 至少有两个差异：

```text
config/trading_calendar.yaml
src/phase1_runner.py
```

当前实际 computation identity：

```text
9d4ee6acabf913d5e1a83329f02aeba0bb9129c85cad24fa09a691c821dd5af3
```

旧 release identity：

```text
41f4030eaff55b041bcbb05ce0bc39ed3d8736f438d5aa24eb4c14cdac5db51b
```

不能：
- 改写旧 CURRENT_RELEASE；
- 用历史 replay 自动授权 current release；
- 把 current drift 当作历史测试已修复。

必须先确认 `reports/current/CURRENT_RELEASE.json` 是否仍被任何 current runtime/UI/fallback consumer 使用。

外部状态：

```text
PREEXISTING_V1_CURRENT_RELEASE_IDENTITY_DRIFT =
OPEN_RELEASE_GOVERNANCE
```

## 10. 3 个 environment validation 项

仍有：

```text
V3 local UI service not running
Windows symlink creation unavailable x2
```

它们不是业务算法错误，但也不是 PASS。

下一轮应：
- UI test 使用 isolated local service fixture；
- symlink tests 保留真实 symlink 分支，同时增加 Windows 无 symlink privilege 的 portable path/reparse negative proof。

## 11. Protected state

除 TDX incident 外：
- accepted heads 无 drift；
- migrations 无 drift；
- runtime roots final bytes/mtime 一致；
- 权限未提升。

所以：

```text
ACCEPTED_HEADS_PROTECTED = PASS
PERMISSIONS_UNCHANGED = PASS
TDX_ZERO_WRITE = FAIL
```

## 12. 最终状态

```text
V4_FORWARD_R2_REMAINDER_EXTERNAL_AUDIT =
BLOCKED_NOT_READY_FOR_EXTERNAL_ACCEPTANCE

PASS:
IA-06
IA-08
DM01 legacy P2
IA-01/02/03/04/09/10 PASS_KEEP

PARTIAL:
IA-07

OPEN:
IA-05
V1 current release identity governance
3 environment validation items

NEW BLOCKER:
TDX_READ_ONLY_BOUNDARY_P1
```

下一步只能是定点修复这些剩余项；仍不得做 Forward runtime promotion。
