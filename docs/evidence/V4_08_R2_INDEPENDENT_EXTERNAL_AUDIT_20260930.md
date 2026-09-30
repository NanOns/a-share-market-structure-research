# V4-08 R2 独立外部验收审计｜2026-09-30

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**审计 HEAD**：`0581731c1284e82380fa115156f1dc0a16a38bd4`  
**上一审计基线**：`68276e4f48f7664827418a6095b3a0ddcc1fa0a8`  
**审计性质**：独立外部增量验收

---

# 1. 唯一总状态

```text
V4_08_R2_EXTERNAL_ACCEPTANCE_BLOCKED

MEMBERSHIP_CONTRACT_REPAIR_B01_B05 = PASS

FORWARD_PIT_BASELINE = BLOCKED

PRIMARY_REMAINING_BLOCKERS =
B06_IDENTITY_LIFECYCLE_RECLASSIFICATION
+ B07_SOURCE_REVISION_BASIS_BINDING
+ B08_ISOLATED_REGRESSION_EVIDENCE
+ ACCEPTED_FORWARD_CALENDAR_EXTENSION
```

当前全局 Accepted Head 保持：

```text
V4_00_TO_V4_07_ACCEPTED
```

不得创建 `V4_08_ACCEPTED_HEAD.json`。

# 2. 本轮提交身份

上一审计 HEAD：`68276e4f48f7664827418a6095b3a0ddcc1fa0a8`

当前远端 HEAD：`0581731c1284e82380fa115156f1dc0a16a38bd4`

```text
ahead_by = 2
behind_by = 0
```

新增提交：

1. `9389768ced67d86590ef0b8d5b5cb3d6e0b2226e` — `feat(v4-08): repair membership contract r2`
2. `0581731c1284e82380fa115156f1dc0a16a38bd4` — `docs(v4-08): seal r2 membership candidate evidence`

本轮代码、schema、测试和 candidate evidence 已真实 push 到目标分支。

# 3. B01｜Mixed Membership Basis

R2 已将 raw current 与 derived-parent 拆为独立 snapshot lineage。

Raw Current：

```text
snapshot_id =
24cc00f60de09e01627fd1fa2d13755888c91cc2a5c10bb1a1a21cad4719b4dc
basis = CURRENT_TDX_MEMBERSHIP
facts = 85,038
```

Derived Parent：

```text
snapshot_id =
7ec30281a92a85c5ff10b741216c46b2faf1a0f73933813bf972161f369e0dd4
basis = DERIVED_PARENT_MEMBERSHIP
facts = 2,899
parent_snapshot_id =
24cc00f60de09e01627fd1fa2d13755888c91cc2a5c10bb1a1a21cad4719b4dc
```

历史 replay 同样拆开，derived-parent replay 保留 `DERIVED_PARENT_MEMBERSHIP`。

Migration 018 已验证 raw snapshot 拒绝 parent-basis fact，derived parent 必须引用匹配 raw snapshot。

**结论：`B01 = PASS`。**

# 4. B02｜Formal SQL View Quality Gate

R2 formal view 当前要求：

```text
INDUSTRY / THEME
fact basis = PIT_OBSERVED
snapshot basis = PIT_OBSERVED
fact quality = PIT_OBSERVED_ACCEPTED
snapshot quality = PIT_OBSERVED_ACCEPTED
source revision quality = PIT_OBSERVED_ACCEPTED
pit_observed = true
historical_backtest_safe = true
identity_status = MAPPED
security_id IS NOT NULL
membership_asof_date = target_trade_date
provider availability <= cutoff
system availability <= cutoff
```

`PIT_OBSERVED + SOURCE_TIME_UNVERIFIED` negative vector 已被拒绝。

**结论：`B02 = PASS`。**

# 5. B03｜historical_backtest_safe

R1 的错误等价：

```text
historical_backtest_safe == (membership_basis == PIT_OBSERVED)
```

已经移除。

R2 允许保存：

```text
pit_observed = true
historical_backtest_safe = false
```

只有 accepted PIT quality、mapped identity、temporal evidence 等全部满足时才允许 history-safe。

**结论：`B03 = PASS`。**

# 6. B04｜Effective-Date / Staleness

R2 采用：

```text
DAILY_EXACT_SNAPSHOT
membership_asof_date == target_trade_date
carry_forward = false
```

stale-date negative vector：

```text
membership_asof_date = 2026-09-29
target_trade_date = 2026-09-30
=> REJECT
```

**结论：`B04 = PASS`。**

注意：代码合同通过不等于当前 source 已经证明 2026-09-30 的 source-state 可正式消费。

# 7. B05｜Same Bytes + New Temporal Evidence

R2 source revision identity 现在同时绑定：

```text
source_bytes_digest
temporal_evidence_digest
```

相同 bytes 若补新的 temporal evidence，会得到新 revision id，旧 revision 不 UPDATE。

数据库同时验证 same-bytes/new-evidence 新 revision、append-only 和 fork rejection。

**结论：`B05 = PASS`。**

# 8. Source Availability Policy 外部裁决

R2 提出：

```text
provider_available_at_basis =
PROJECT_FIRST_OBSERVED_PROVIDER_BYTES
```

完整 source bundle 首次被项目观察的时间：

```text
2026-09-30T00:45:21.890265Z
```

该 policy 明确不声称这是 provider 原始发布时间，也不使用 filesystem mtime。

本次独立审计对该原则给出：

```text
EXTERNAL_DISPOSITION_ACCEPTED
FOR_CONSERVATIVE_GO_FORWARD_KNOWLEDGE_TIME_ONLY
```

原因：provider 实际可用时间只会早于或等于项目第一次真实观察完整 bytes 的时间。把项目 observation 当作系统最早允许消费的 conservative knowledge-time，只会向后延迟，不会产生前视。

正式使用必须满足：

1. exact source bytes hash frozen；
2. complete-bundle observed_at 可复核；
3. publication cutoff >= complete observation；
4. target date 不早于 observation date；
5. mtime 永远不能替代 availability；
6. 每日 source snapshot 独立冻结；
7. 当日 capture 缺失时不得 carry-forward；
8. lifecycle/active-universe gate 在 sector consumer 之前完成。

这个 disposition 接受知识时间原则，不等于接受当前 PIT baseline。

# 9. Membership-As-Of Policy 外部裁决

对于 §77C 的 go-forward membership，正式 PIT 可定义为：

> 项目在目标日 publication cutoff 前实际观察并冻结的 TDX 当前 membership source state。

它不是 provider 历史 effective-date 声明。

允许：

```text
membership_asof_basis =
PROJECT_FIRST_OBSERVED_SOURCE_STATE
membership_asof_date =
target_trade_date
```

但必须满足：

- security lifecycle 在目标日有效；
- pre-list security 即使提前出现在 TDX relation file 中，也不得进入正式 active membership；
- 每日 exact snapshot；
- 不跨日复用；
- 不可用于 2026-09-28 或更早历史回填。

本原则给出：

```text
EXTERNAL_DISPOSITION_ACCEPTED
FOR_GO_FORWARD_PROJECT_OBSERVED_STATE_ONLY
```

# 10. Forward PIT 仍未建立

当前 R2：

```text
candidate_trade_date = null
first_go_forward_pit_baseline_trade_date = null
pit_observed = false
historical_backtest_safe = false
```

这是正确的 fail-closed。

当前仍缺：

```text
accepted forward calendar
identity lifecycle closure
B07 source-revision basis guard
clean isolated regression evidence
```

# 11. Accepted Market Calendar 阻塞

正式 accepted calendar `V4_02_FORMAL_MARKET_CALENDAR_ACCEPTANCE_V2` 仅覆盖：

```text
2023-07-04 ~ 2026-09-24
```

而当前 membership source complete observation 是 2026-09-30。

需要 append-only go-forward calendar extension，至少覆盖 2026-09-25 到 first PIT target session。

不得修改旧 V4-02 accepted artifact。

**状态：`BLOCKED_ACCEPTED_FORWARD_CALENDAR_EXTENSION_REQUIRED`。**

# 12. B06｜Identity Scope 仍未关闭

R2 将 497 unresolved keys 分类为：

```text
ETF_OR_FUND       325
CONVERTIBLE_BOND   55
BSE_OPTIONAL      106
AMBIGUOUS_IDENTITY 11
```

将 486 个 non-core/optional 对象从 required four-board blocker 移出是正确方向。

但剩余 11 个全部通过 `board_for(code-pattern)` 判成 `AMBIGUOUS_IDENTITY`，仍不是 lifecycle-aware 判断。

11 个 key：

```text
SH.601206
SH.603302
SH.603361
SH.688688
SZ.001235
SZ.001246
SZ.300728
SZ.301569
SZ.301660
SZ.301716
SZ.301718
```

# 13. 独立外部核验暴露出的 B06 问题

至少存在三类不同 lifecycle truth：

## 已真实上市、需要 incremental admission

`SZ.001246 力勤资源`：

```text
上市日期 = 2026-09-30
board = SZ_MAIN
```

`SZ.301716 鸿富诚`：

```text
上市日期 = 2026-09-29
board = CHINEXT
```

二者晚于 accepted V4-01 identity cutoff 2026-09-24，需要新的 incremental identity/lifecycle revision，不能继续保留为 generic ambiguity。

## 截至 2026-09-30 尚未上市的例子

`SZ.301718 通则康威`：

```text
申购日 = 2026-10-09
```

因此 2026-09-30 不属于 active formal universe。

`SZ.301569 联亚药业`、`SZ.301660 粤芯半导体` 截至 2026-09-30 仍处发行/待上市流程，不能仅因代码形状进入 formal universe。

## 其余历史 IPO / 未上市 / 非 equity 对象

剩余老代码必须逐一作 dated lifecycle adjudication，不能由 code regex 代替 lifecycle fact。

**结论：`B06 = FAIL`。**

# 14. B06 正式修复标准

11 个 key 必须逐一落入：

```text
FORMAL_IN_SCOPE_A_STOCK
NOT_LISTED_AT_TARGET
NON_EQUITY
HISTORICAL_WITHDRAWN_OR_TERMINATED_IPO
TRUE_IDENTITY_GAP
AMBIGUOUS_IDENTITY
```

`FORMAL_IN_SCOPE_A_STOCK` 必须绑定 exchange、board、listing_date、source evidence、first system availability、canonical security_id 和 lifecycle revision。

# 15. 新 Blocker B07｜Source Revision Basis 没有强绑定

Migration 018 formal view 要求：

```text
fact basis = PIT_OBSERVED
snapshot basis = PIT_OBSERVED
```

但没有显式要求：

```text
source_revision.membership_basis = PIT_OBSERVED
```

`check_sector_membership_fact_temporal_binding()` 同样没有检查：

```text
revision_row.membership_basis == NEW.membership_basis
```

因此理论上可以构造：

```text
source revision basis = CURRENT_TDX_MEMBERSHIP
revision_quality = PIT_OBSERVED_ACCEPTED

snapshot basis = PIT_OBSERVED
fact basis = PIT_OBSERVED
```

并在其他字段伪装合格时进入 formal path。

这破坏 Source Revision → Snapshot → Fact 的 basis 一致性。

**结论：`B07 = FAIL / HARD BLOCKER`。**

# 16. B07 修复要求

新增 migration，不改写 018。

必须保证：

```text
revision.membership_basis
==
snapshot.membership_basis
==
fact.membership_basis
```

formal view 显式要求：

```text
r.membership_basis = 'PIT_OBSERVED'
```

并冻结 basis ↔ quality compatibility。

mandatory negative vector：

```text
CURRENT_TDX revision
+ accepted-looking PIT quality
+ PIT snapshot
+ PIT fact
=> REJECT
```

# 17. 新 Blocker B08｜Clean Checkout Full Regression 隔离不可验证

R2 clean receipt 明确：

```text
clean checkout initially had no config/.env
Phase0 DB tests could not start
then primary checkout config/.env was copied in
regression rerun
then file removed
```

而 Phase0 PostgreSQL tests 通过 `scripts.apply_v4_phase0_schema.dsn()` 连接数据库；`dsn()` 会在没有 `WORKBENCH_PG_DSN` 时读取 `config/.env`。

因此：

> `571 passed` 没有证明使用 disposable database，也没有记录实际 DSN source/database identity。

独立 Migration 018 verifier 明确使用 disposable localhost PostgreSQL，因此 migration receipt 本身可接受。

但是 full regression 的 clean DB isolation：

```text
B08 = NOT_VERIFIABLE / RERUN_REQUIRED
```

# 18. B08 修复要求

重跑完整 matrix：

- 不复制 primary `config/.env`；
- 创建 disposable PostgreSQL cluster；
- process-scoped `WORKBENCH_PG_DSN` 注入；
- receipt 保存 sanitized DB identity；
- `config_dot_env_read=false`；
- `configured_or_production_database_used=false`；
- cluster cleaned after run；
- working tree clean before/after。

# 19. Sector / Rotation Contract Engineering

R2 已新增 Sector Native、B0、B1、B2、field registry、parameter set、machine vectors。

所有正式 consumer 权限仍为 false，未越权做 full-market production。

**结论：`PASS_CONTRACT_DESIGN_CANDIDATE`。**

但还不能写 `ALGORITHM_CONTRACT_COMPLETE`。

# 20. 五个 V4-00G 参数仍未冻结

当前仍为 null：

```text
V4_08_EARLY_SEED_RETENTION_MIN
V4_08_EARLY_BREADTH_RETENTION_MIN
V4_08_EARLY_BREADTH_DELTA_MIN
V4_08_EARLY_TOP1_CONCENTRATION_MAX
V4_08_MATURE_STRONG_RETENTION_MIN
```

这符合 REV2 §72“未赋值不能取得正式消费者权限”。

因此：

```text
ROTATION_CORE_V1 formal consumer = BLOCKED
```

但 membership admission 不需要等待它们。

# 21. Mandatory Rotation R1 Vector 覆盖不完整

REV2 必测 R1 要求 strong_prev=0 时，在其他 early-retention 条件满足时允许 IN / ACCEPTED。

当前唯一 R1 vector：

```text
pulse_age_sessions = 1
```

实际：

```text
rotation_in_possible = true
rotation_accepted_possible = false
```

测试只验证 IN。

所以它没有真正证明 strong_prev=0 在 age>=2 时不阻断 ACCEPTED。

**结论：`R1_VECTOR = PARTIAL`。**

下一轮必须拆：

```text
R1A age=1 => IN
R1B age>=2 => ACCEPTED possible
```

# 22. Machine AST Completeness

B0 AST 目前仍包含诸如：

```text
"member_count>=V4_08_SECTOR_MIN_MEMBERS"
"dq5>=3"
```

的字符串叶节点；Rotation Core 也主要仍是文档化规则。

REV2 §10A0 / §73 / §81.4 要求正式实现前具备 serializable AST、parameter_id、producer、time semantics、quality semantics 和 machine vectors。

因此当前正确状态是：

```text
DESIGN_FROZEN_ENGINEERING_CANDIDATE
```

不是 formal algorithm contract accepted。

# 23. Legacy B2

B2 明确：

```text
NOT_IMPLEMENTED_PENDING_EXACT_SOURCE_AST_AND_GOLDEN_SAMPLES
```

状态诚实。

只阻塞 legacy WARM/CONFIRMED adapter，不阻塞 membership、Sector Native 和非 legacy primitives。

# 24. Prior-RPS

R2 继续保持：

```text
OPEN_REPAIR_CONTINUES_INDEPENDENTLY
```

没有改阈值、复制 V4-03 staging、重写 V4-05 accepted artifacts。

**结论：状态完整性 PASS，repair 继续 OPEN。**

# 25. Regression / Schema

Migration 018：

```text
PASS_ISOLATED_MIGRATION_AND_ROLLBACK
PostgreSQL 18.6
```

可接受。

pytest：

```text
571 passed
2 skipped
0 failed
```

只能认定 functional regression pass；不能认定 final isolated DB acceptance。

# 26. 逐项判定

| 项目 | 结论 |
|---|---|
| B01 Mixed Basis | PASS |
| B02 Formal View Quality | PASS |
| B03 history-safe semantics | PASS |
| B04 Exact Effective Date | PASS |
| B05 Temporal Revision Identity | PASS |
| Conservative observed-time policy | ACCEPTED, go-forward only |
| Project-observed source-state policy | ACCEPTED, go-forward only |
| B06 Identity Lifecycle Scope | FAIL |
| B07 Source Revision Basis Binding | FAIL |
| B08 Clean Regression DB Isolation | NOT_VERIFIABLE / RERUN |
| Accepted Calendar through target | BLOCKED |
| PIT baseline | BLOCKED |
| Sector Native design | DESIGN PASS |
| B0 design | DESIGN PASS |
| Rotation design | PARTIAL |
| Rotation mandatory R1 vector | PARTIAL |
| B2 Legacy adapter | NOT_IMPLEMENTED as declared |
| Prior-RPS | OPEN, non-blocking for unrelated engineering |
| V4-08 Accepted Head | NOT AUTHORIZED |

# 27. 外部验收结论

本轮可以正式认定：

```text
V4_08_R2_MEMBERSHIP_CONTRACT_REPAIR_B01_B05_PASS
```

并接受 observed-time / observed-source-state 的 conservative go-forward policy。

但整个阶段必须保持：

```text
V4_08_R2_EXTERNAL_ACCEPTANCE_BLOCKED
```

# 28. 下一阶段

执行：

`V4_08_R3_FORWARD_PIT_ADMISSION_IDENTITY_CALENDAR_AND_BASIS_GUARD_TASK_20260930.md`

R3 只处理真正剩余项：

1. B07 source revision basis guard；
2. lifecycle-aware 11-key adjudication；
3. V4-01 incremental identity revision；
4. accepted go-forward calendar extension；
5. 建 first forward PIT snapshot；
6. isolated PostgreSQL clean regression；
7. Rotation R1A/R1B vector；
8. machine AST completeness；
9. Prior-RPS 并行继续。

**不要重新做 B01–B05。**

# 29. 唯一最终状态

```text
V4_08_R2_EXTERNAL_ACCEPTANCE_BLOCKED

CONTRACT_REPAIR_B01_B05 = PASS

SOURCE_TIME_POLICY =
EXTERNALLY_ACCEPTED_FOR_CONSERVATIVE_GO_FORWARD_ONLY

PIT_BASELINE =
BLOCKED_BY
IDENTITY_LIFECYCLE
+ SOURCE_REVISION_BASIS
+ ACCEPTED_CALENDAR_EXTENSION
+ CLEAN_DB_ISOLATION_EVIDENCE
```
