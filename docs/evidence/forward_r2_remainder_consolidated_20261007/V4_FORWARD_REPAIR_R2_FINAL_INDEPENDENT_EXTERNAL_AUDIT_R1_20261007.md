# V4 Forward Repair R2｜最终独立外部验收审计 R1｜2026-10-07

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- R2 执行基线: `15a4e1cc545f6c44d94ebb2b63e71fba6c69e63a`
- R2 当前远端 HEAD: `433c3378d4bc4db572f95de20cadbf899c2a04ce`

## 1. 唯一总裁决

```text
FORWARD_REPAIR_R2_EXTERNAL_AUDIT =
PASS_FINAL_ENGINEERING_CANDIDATE_SCOPED

IA-03 = PASS_ENGINEERING_CANDIDATE
IA-04 = PASS_ENGINEERING_CANDIDATE
IA-10 = PASS_ENGINEERING_CANDIDATE

IA-01 = PASS_KEEP
IA-02 = PASS_KEEP
IA-09 = PASS_KEEP_WITH_INCIDENT_RECORD

IA-05 = OPEN_P1
IA-06 = OPEN_P1
IA-07 = OPEN_P2
IA-08 = OPEN_P2

AUDIT_DM01_R4_LEGACY_TEST_ACCEPTANCE_STATE_20261007 =
OPEN_P2

ACTIVE_FORWARD_RUNTIME_PROMOTION = NOT_GRANTED
FIRST_REAL_SHADOW = NOT_GRANTED
PRODUCTION = false
```

R2 修复本身通过；当前剩余未关闭问题已经收敛为 IA-05～IA-08 加 1 个 DM01 legacy test governance P2。

## 2. R2 successor 边界

R2 新增：

```text
FORWARD_PRICE_PATH_V1_2
SECTOR_BASKET_FORWARD_PATH_V2
scripts/_bootstrap.py
scripts/v4_16_forward_r2_worker.py
```

旧 V1.1、历史 accepted heads、历史 outcome bytes 均未原地改写。

Candidate 明确：

```text
simulation_only = true
no_accepted_dependency_selects_it = true
runtime_authorized = false
real_shadow_authorized = false
production = false
```

因此 immutable / successor 边界通过。

## 3. IA-03｜PASS

原问题是同一 source 下 PENDING → DUE/OBSERVED 可能复用同一 immutable outcome reference。

V1.2 identity 加入：

```text
enrollment_id
horizon
FORWARD_PRICE_PATH_V1_2
source_digest
PENDING_OR_DUE
due_date
accepted_session_list_digest
```

不使用 wall clock、UUID、run id。

PENDING 保留为 planner-state observation，但 FIRST_OBSERVED / LATEST_CORRECTED 只从 matured/non-PENDING revision 中选择。

向量覆盖：
- pre-due；
- due；
- repeated pre-due；
- repeated due；
- corrected source；
- restart；
- historical pending immutable；
- first/latest；
- deterministic identity。

结论：

```text
IA-03 = PASS_ENGINEERING_CANDIDATE
```

## 4. IA-04｜PASS

R2 在实现前冻结了：
- master design；
- V4-02 canonical daily PIT contract；
- Forward price path contract；
- Outcome status contract；
- Settlement revision contract。

V1.2 ordinary actual price 要求：
- finite；
- positive；
- low <= close <= high；
- 有 open 时 low <= open <= high；
- affine 后价格也必须 finite + positive。

Confirmed suspension 不伪造 bar。

Delisted terminal 走独立分支：
- terminal_verified=true；
- evidence存在；
- terminal finite、nonnegative；
- terminal=0 合法，可得到 R_N=-1。

IA-01 endpoint/path separation 继续保持。

结论：

```text
IA-04 = PASS_ENGINEERING_CANDIDATE
```

## 5. IA-10｜PASS

新增统一 `scripts/_bootstrap.py` 和 bootstrap contract。

已验证：
- repo 外 cwd；
- PYTHONPATH 空；
- user-site disabled；
- repo root + src 自行建立；
- preflight；
- isolated fixture；
- TDX protected root fail closed；
- module launcher parity；
- 不改 DM01 九组件；
- 不改 R25；
- 无 TDX 写。

结论：

```text
IA-10 = PASS_ENGINEERING_CANDIDATE
```

## 6. Regression

R2 evidence：

```text
IA09: 30 passed
FORWARD: 54 passed
CLI: 10 passed

AFFECTED:
625 selected
1 failure
278 skipped
0 introduced failures
```

唯一 failure：

```text
tests.v4_dm01_r4.test_runtime::
test_current_real_v2_parent_and_future_wait
```

该节点在 R2 baseline 单独复现同样失败，R2 modules 未参与，因此不是 R2 introduced regression。

所以：

```text
R2_TARGETED_GATES = PASS
R2_INTRODUCED_FAILURES = 0
FULL_SCOPE_GREEN = false
```

## 7. DM01 legacy test OPEN_P2

当前 authoritative acceptance 已是：

```text
EXTERNALLY_ACCEPTED_DM01_R4_RUNTIME
```

旧测试仍期待：

```text
PENDING_DM01_R4_EXTERNAL_ACCEPTANCE
```

这是 stale pre-acceptance expectation，不是当前 runtime 算法失败。

不能通过撤销 accepted head 来让测试通过。

正式状态：

```text
AUDIT_DM01_R4_LEGACY_TEST_ACCEPTANCE_STATE_20261007 =
OPEN_P2
```

关闭要求：
- historical pre-acceptance fixture；
- current accepted-runtime fixture；
- exact authority bindings；
- old history保留；
- current behavior新增正式测试；
- 不改数值核。

## 8. 当前剩余 IA-05～IA-08

### IA-05 P1
默认 pytest collection 仍会被旧 M14 test 导入已退役 `_commit_raw_and_batch` 阻断。当前 collector 已是 request-time-only，不得恢复历史写入口。

### IA-06 P1
当前环境仍未完整执行 isolated PostgreSQL fresh/upgrade、role/trigger/CAS/rollback 和 FEP model sklearn parity。278 PG opt-in cases 仍未运行。

### IA-07 P2
没有 current accepted-scale full-market/FEP/Forward elapsed、peak RSS、output bytes、复杂度增长实测。旧 Phase0 baseline 自己声明 runtime row count=0，不能外推今天性能。

### IA-08 P2
历史 exact bytes 与 current checkout bytes 必须显式版本路由。此前 20 mismatch 对应 15 个 old identities 都可从 Git 找回，因此不是历史损坏，而是 historical/current reader 边界未完整 formalize。

## 9. Protected State

保持：
- V4 accepted heads unchanged；
- Current Audit Head unchanged；
- REAL_SHADOW_OBSERVATIONS=0；
- PIT_OBSERVED_REAL_SAMPLES=0；
- runtime/real-shadow authorization=false；
- Production/Focus/Default UI=false；
- FEP permissions unchanged；
- TDX no write。

## 10. 下一步

不再拆 Round 3。

直接执行综合收尾任务：

```text
IA-05
IA-06
IA-07
IA-08
DM01 legacy test OPEN_P2
```

全部关闭后，再做 Forward successor admission / runtime propagation 的独立决策。

**最终：R2 PASS_FINAL_ENGINEERING_CANDIDATE_SCOPED**
