# V4-06 / V4-07 Promotion + V4-08 Membership R1 独立外部审计

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**审计日期**：2026-09-30  
**审计 HEAD**：`68276e4f48f7664827418a6095b3a0ddcc1fa0a8`  
**上一审计基线**：`075163fd7bf3d4210004734f849cff9225bc6ecf`

---

# 1. 唯一总状态

```text
V4-06 Accepted Head Promotion:
PASS

V4-07 Accepted Head Promotion:
PASS_WITH_GOVERNANCE_NOTE

V4-08 PIT Sector Membership Baseline R1:
EXTERNAL_ACCEPTANCE_BLOCKED_R1
CONTRACT_PERSISTENCE_REPAIR_AND_TRUE_FORWARD_PIT_BASELINE_REQUIRED

Prior-RPS:
INVESTIGATION_PASS
REPAIR_OPEN_NON_BLOCKING_FOR_UNRELATED_ENGINEERING
```

当前正式 accepted range：

```text
V4_00_TO_V4_07_ACCEPTED
```

这一点已经真实落地。

V4-08 仍不能进入正式 full-market Sector / Rotation production。

---

# 2. 本轮增量提交

上一 HEAD：

`075163fd7bf3d4210004734f849cff9225bc6ecf`

当前 HEAD：

`68276e4f48f7664827418a6095b3a0ddcc1fa0a8`

状态：

```text
ahead_by = 7
behind_by = 0
```

提交：

1. `c479f187e397d0f814229f63f41e4d8bd9a2a833`
   `docs(data): promote v4-06 accepted head`

2. `6f2c1faf6ed0ad2bdb267bed32cb24fc1a31bf22`
   `docs(data): promote v4-07 accepted engineering head`

3. `d07287f370c896ee5a24152feecb393e3aaa122a`
   `feat(v4-08): freeze membership contract and schema`

4. `ed577569a3e3258d5fd4b5aa735e7411fc798258`
   `docs(audits): document open prior RPS bootstrap repair`

5. `ae27c3bdd170024eff3841a147fcce257d57b038`
   `fix(audits): clean prior RPS addendum formatting`

6. `47e0d72343594c697ff1a73c4daed853ea21e830`
   `feat(v4-08): build membership replay prerequisite`

7. `68276e4f48f7664827418a6095b3a0ddcc1fa0a8`
   `docs(v4-08): seal membership prerequisite evidence`

---

# 3. V4-06 Promotion

已创建：

`data/v4/V4_06_ACCEPTED_HEAD.json`

Accepted Head SHA：

`5aec962703aed40cab809e798edc5bfbe50c416809984db40bb679a172782f8e`

Global Head 已记录：

```text
v4_06_status = DEGRADED_PASS
v4_06_live_strict_binding = BLOCKED_DEGRADED
```

Open audit：

`V4-06-BAOSTOCK-BINDING-TOLERANCE-01`

继续保留。

Candidate manifest 22/22 文件全部 hash/byte-count 对齐。

结论：

```text
V4_06_ACCEPTED_HEAD_PROMOTION_PASS_R1
```

不需要回滚。

---

# 4. V4-07 Promotion

已创建：

`data/v4/V4_07_ACCEPTED_HEAD.json`

Accepted Head SHA：

`b22117b0d14c35167cba86cb7398d878d7112f9cf17c1a427fa92766e78f880f`

Global Head：

```text
accepted_stage_range = V4_00_TO_V4_07_ACCEPTED
```

能力仍正确分开：

```text
V4_07_ENGINEERING = EXTERNALLY_ACCEPTED

REAL_BASE_SEED_SIGNAL =
DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN
```

结论：

```text
V4_07_ACCEPTED_HEAD_PROMOTION_PASS_R1_ENGINEERING_SCOPE
```

不需要回滚。

---

# 5. V4-07 Promotion Governance Note

Promotion validation 发现旧 R2 manifest 中两份 receipt 后来被刷新：

- `V4_07_R2_ISOLATED_FULL_REGRESSION.json`
- `V4_07_R2_MIGRATION_ROLLBACK_VERIFICATION.json`

旧 manifest hash 与当前最终 receipt hash 不同。

开发方没有修改旧 manifest，而是：

1. 明确把旧 candidate receipt 定义为 `PRE_FINAL_GATE_CANDIDATE_SNAPSHOT`；
2. 明确列出仅这两个 mismatch；
3. 在 promotion Accepted Head 中单独绑定最新 final PASS receipt；
4. 验证 mismatch scope 与声明完全一致。

因此本轮不据此推翻 V4-07 promotion。

但以后要求：

> candidate seal 后若 evidence 发生更新，不再让一个 manifest 同时承担 pre-final 与 final 两种身份；创建新的 final promotion manifest / final evidence index。

状态：

```text
PASS_WITH_GOVERNANCE_NOTE
```

---

# 6. V4-08 R1 做对的部分

当前实现没有伪造 PIT。

`V4_08_GO_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json` 明确：

```text
first_go_forward_pit_baseline_trade_date = null
pit_observed = false
historical_backtest_safe = false
```

原因：

```text
provider availability / membership effective date 未被证明
```

这是正确的 fail-closed 行为。

当前 observation：

```text
source_observed_at = 2026-09-30T00:45:21.889920Z
```

TDX 文件 hash 已冻结。

没有把 filesystem mtime 当作 provider availability。

结论：

```text
PASS
```

---

# 7. Diagnostic Replay

当前 historical replay：

```text
membership_basis = CURRENT_MEMBERSHIP_REPLAY
pit_observed = false
historical_backtest_safe = false
```

总行数：

`87,937`

Raw：

`85,038`

Derived parent：

`2,899`

类型：

```text
INDUSTRY   8,484
THEME     46,591
STYLE     20,223
UNKNOWN   12,639
```

formal eligible replay rows：

`0`

因此当前没有把 later current membership 冒充历史 PIT。

结论：

```text
PASS_DIAGNOSTIC_ONLY
```

---

# 8. Type Policy

正式类型：

```text
INDUSTRY
THEME
```

STYLE：

```text
formal_radar_allowed = false
formal_sector_qualification_allowed = false
formal_rotation_qualification_allowed = false
```

UNKNOWN 同样禁止正式消费。

这符合 REV2。

结论：

```text
PASS
```

---

# 9. Migration / Regression / Clean Checkout

新增：

```text
016_v4_08_sector_membership.sql
017_v4_08_membership_fact_evidence_view.sql
```

Isolated PostgreSQL：

`18.6`

测试：

```text
旧 V4 matrix: 538 passed, 2 skipped
V4-08:        21 passed
Combined:     559 passed, 2 skipped
failed:       0
```

Clean checkout：

`47e0d72343594c697ff1a73c4daed853ea21e830`

通过。

当前 GitHub HEAD 没有 combined CI status，继续作为 CI limitation 披露，但不是单独失败理由。

---

# 10. Blocker B01 — Mixed Membership Basis Artifact 与 DB Snapshot 合同冲突

这是本轮独立发现的第一个硬问题。

`build_source_rows()`：

Raw source rows：

```text
membership_basis = CURRENT_TDX_MEMBERSHIP
```

Derived parent rows：

```text
membership_basis = DERIVED_PARENT_MEMBERSHIP
```

之后 current artifact：

```python
current_rows = rows
```

因此同一个 current artifact 中存在两种 membership basis。

但是数据库：

`v4.sector_membership_snapshots`

一个 snapshot header 只有一个：

```text
membership_basis
```

且 insert trigger 要求：

```text
fact.membership_basis == snapshot.membership_basis
```

所以：

> 当前 `V4_08_CURRENT_TDX_MEMBERSHIP_R1` artifact 如果按一个 snapshot 落库，2,899 条 derived-parent rows 会与 snapshot header 冲突。

这说明当前 candidate artifact 与 persistence contract 并未真正闭环。

必须：

- raw current membership 与 derived-parent membership 拆成不同 snapshot/revision lineage；或
- derived parent 改为单独 enrichment/materialization 表。

不能继续混在一个正式 snapshot。

状态：

```text
FAIL / HARD BLOCKER
```

---

# 11. Blocker B02 — Formal SQL View 没有 Membership Quality Gate

Python：

`formal_membership_eligible()`

要求：

```text
membership_quality == PIT_OBSERVED_ACCEPTED
```

但 SQL：

`v4.formal_sector_membership`

只要求：

```text
membership_basis = PIT_OBSERVED
pit_observed = true
historical_backtest_safe = true
identity_status = MAPPED
sector type allowed
```

没有要求：

```text
f.membership_quality = PIT_OBSERVED_ACCEPTED
```

也没有要求 snapshot quality 为 accepted。

因此 Python contract 和数据库正式 read model 不一致。

未来一条 basis=PIT_OBSERVED 但 quality 不合格的 mapped INDUSTRY/THEME fact，理论上可能进入 formal view。

必须新增 migration 修复。

状态：

```text
FAIL / HARD BLOCKER
```

---

# 12. Blocker B03 — historical_backtest_safe 被错误等同于 PIT_OBSERVED

Migration 016：

```sql
CHECK (historical_backtest_safe = (membership_basis = 'PIT_OBSERVED'))
```

这意味着：

> 只要 basis=PIT_OBSERVED，就必须 historical_backtest_safe=true。

但正式质量合同同时允许 PIT capture 存在质量问题/identity 问题。

因此：

```text
PIT_OBSERVED
!= automatically historical_backtest_safe
```

正确关系应该至少是：

```text
historical_backtest_safe
=> PIT_OBSERVED
AND PIT_OBSERVED_ACCEPTED
AND identity/source/temporal gates pass
```

而不是反向等价。

否则数据库字段本身会把 degraded PIT fact 标成历史安全。

状态：

```text
FAIL / HARD BLOCKER
```

---

# 13. Blocker B04 — membership_asof_date 允许无限陈旧

当前 Python：

```text
asof_date <= target_date
```

SQL trigger 同样只拒绝：

```text
membership_asof_date > target_trade_date
```

但当前 schema 没有：

```text
effective_from
effective_to
```

所以一份 9 月 28 日 snapshot 在逻辑上可以直接被消费到 9 月 30 日、10 月甚至更晚，只要没有另一条显式阻止。

这不满足原 PIT membership 合同中的：

> effective interval covers target date

当前 daily snapshot 设计若没有有效区间，则第一版最安全规则应是：

```text
membership_asof_date == target_trade_date
```

或者正式引入：

```text
effective_from / effective_to
```

再用区间覆盖。

状态：

```text
FAIL / HARD BLOCKER
```

---

# 14. Blocker B05 — Source Revision ID 无法表示“同 bytes、补时间证据”的新 revision

当前 candidate：

```python
source_revision_id = "sha256:" + source_digest
```

而 `source_digest` 主要绑定：

- source file digests；
- parser version；
- parent contract；
- parent map digest。

它没有把：

- provider availability evidence；
- membership effective date evidence；
- source-time evidence revision

纳入 revision identity。

当前最需要做的下一步恰好是：

> 给已冻结 bytes 补一个可审计的 provider availability / membership effective-date 证据。

如果 bytes 不变：

```text
source_digest 不变
source_revision_id 不变
```

但表又是 append-only，不能 UPDATE。

因此当前 source revision identity 设计无法优雅表达：

```text
same bytes
+
new independently accepted availability/effective-date evidence
```

必须：

- 新增 `availability_evidence_digest / evidence_revision_id` 并进入 source revision identity；或
- 把 source byte revision 与 temporal-evidence revision 分表/分层。

状态：

```text
FAIL / HARD BLOCKER
```

---

# 15. Blocker / Scope Issue B06 — 497 Unresolved Keys 不能全部当成同一种 Formal Identity Failure

当前：

```text
unresolved source keys = 497
membership facts = 1,176
```

清单中大量明显属于：

- BSE；
- ETF / fund；
- convertible bond；
- 非当前正式四板股票范围。

但也存在 SH/SZ A-stock-shaped keys。

当前脚本：

`load_accepted_identity_map()`

把 accepted map 中 `non_core_candidates` 也直接从 resolved map 排除，之后统一计为 UNKNOWN。

这使：

```text
OUT_OF_SCOPE_NON_CORE
```

与：

```text
TRUE_FORMAL_UNIVERSE_IDENTITY_GAP
```

混在一起。

结果是 formal snapshot 被整体标记：

`BLOCKED_UNKNOWN_SECURITY_IDENTITIES_RETAINED`

这可能过度阻塞。

R2 必须把 497 个 key 分类为至少：

```text
FORMAL_RESEARCH_UNIVERSE_RESOLVED
OUT_OF_SCOPE_NON_CORE
BSE_OPTIONAL
NOT_LISTED_AT_TARGET
TRUE_IDENTITY_GAP
AMBIGUOUS
```

非正式 universe 对象：

- 不得 silent drop；
- 保留 raw diagnostics；
- 但不应因为它们本身阻断主板/创业板/科创板 formal membership。

真正 formal-universe identity gap 才阻断受影响 scope。

状态：

```text
BLOCKING_SCOPE_REPAIR_REQUIRED
```

---

# 16. Go-Forward PIT 的正确推进方式

当前 source 已在：

`2026-09-30T00:45:21.889920Z`

被项目真实读取和 hash freeze。

不能倒推成：

`2026-09-28 PIT`

这一点当前实现做对了。

下一步不应该继续纠结“如何证明两年前 PIT”。

REV2 §77C 已经给了正确路线：

```text
历史 -> CURRENT_MEMBERSHIP_REPLAY diagnostic
从现在开始 -> PIT_OBSERVED append-only
```

因此下一轮应尝试建立：

```text
FIRST_GO_FORWARD_PIT_BASELINE
```

日期必须由 accepted market calendar / publication 决定。

不能仅凭墙上日期硬写。

对于 provider_available_at：

优先寻找来源本身可验证的 availability metadata。

如果 TDX 本地文件没有 provider timestamp，则可以提出一个**新的 source-specific conservative availability policy candidate**：

```text
PROVIDER_OBSERVED_AVAILABLE_AT
=
项目第一次实际读取并冻结到这些 provider bytes 的 observed_at
```

但必须明确：

- 它不是 provider 原始发布时间；
- 它只是“最晚到这个时间已经可获得”的保守证据；
- 必须形成版本化 source-contract amendment；
- 必须经过独立外部接受后才能写为 formal provider availability basis。

不能直接偷偷把 mtime 或 observed_at 改名成 provider timestamp。

---

# 17. First Formal Forward Date

若 accepted market calendar 确认 2026-09-30 是正式目标 session，且：

- 本次 source capture 在该 session publication cutoff 前；
- source-specific availability policy 获得接受；
- identity scope 修复；
- B01~B05 修复；
- publication later consumes exactly this frozen snapshot；

则：

```text
2026-09-30
```

可以作为 first go-forward PIT baseline candidate。

否则选择下一个实际可绑定 session。

绝不能回填到 2026-09-28。

---

# 18. Prior-RPS Audit

新增 gap assessment 正确解释了：

V4-03 R3：

```text
rps5_delta3 OBSERVED = 5023
UNKNOWN = 199
```

但该 prior artifact 是：

```text
STAGING_NOT_STAGE_ACCEPTANCE
```

V4-05 accepted：

```text
rps5_delta3 UNKNOWN = 5222
```

不能直接复制旧 R3 staging 值。

当前 assessment 已明确：

- exact delta offsets；
- required calendar / universe / adjustment / source identities；
- 旧 staging 为什么不能直接复制；
- 新 accepted factor publication 必须 append-only 建立。

结论：

```text
INVESTIGATION_COMPLETE
REPAIR_OPEN
```

这个 repair：

```text
不阻塞 V4-08 非 Seed-dependent engineering
```

但 Seed Width / retention 等字段必须保持 UNKNOWN/degraded。

---

# 19. V4-08 当前外部结论

不能给：

```text
V4_08_PIT_SECTOR_MEMBERSHIP_BASELINE_ACCEPTED
```

也不能只写：

```text
WAIT_FOR_PROVIDER_TIME
```

因为 B01~B05 是代码/合同自身问题。

本轮唯一正式状态：

```text
V4_08_MEMBERSHIP_EXTERNAL_ACCEPTANCE_BLOCKED_R1
CONTRACT_PERSISTENCE_REPAIR_AND_TRUE_FORWARD_PIT_BASELINE_REQUIRED
```

可以保留：

```text
DIAGNOSTIC_CAPTURE = PASS
CURRENT_MEMBERSHIP_REPLAY = PASS_DIAGNOSTIC_ONLY
TYPE_REGISTRY = PASS
SOURCE_HASH_CAPTURE = PASS
MIGRATION_TEST_HARNESS = PASS
```

但正式 membership consumer 权限仍为：

```text
DENIED
```

---

# 20. V4-08 后续开发不应整体停工

根据用户既定开发原则：

> 正式 consumer gate 不等于全项目停工。

下一轮可以并行：

1. 修复 V4-08 membership persistence/contract；
2. 建立 first go-forward PIT baseline；
3. 分类/修复 identity gaps；
4. 冻结 Sector Native / B0 / B1 / B2 contracts；
5. 编写参数实例与 machine vectors；
6. synthetic sector/rotation tests；
7. Prior-RPS accepted lineage repair。

但是：

```text
real full-market Sector/Rotation materialization
```

仍必须等待 membership prerequisite 外部通过。

---

# 21. 当前项目状态

| Stage | Status |
|---|---|
| V4-00 ~ V4-05 | ACCEPTED |
| V4-06 | ACCEPTED / DEGRADED live strict binding |
| V4-07 | ACCEPTED / engineering scope |
| V4-07 real Base Seed signal | DEGRADED / prior-RPS open |
| V4-08 diagnostic membership capture | PASS |
| V4-08 historical replay | DIAGNOSTIC_ONLY |
| V4-08 PIT baseline | BLOCKED |
| V4-08 formal Sector/Rotation production | BLOCKED |
| V4-08 contract/vector parallel work | AUTHORIZED |

---

# 22. 下一任务

执行：

`V4_08_R2_MEMBERSHIP_CONTRACT_REPAIR_AND_FORWARD_PIT_BASELINE_TASK_20260930.md`

目标不是“再做一版 replay”。

目标是：

1. 关闭 B01~B05；
2. 对 B06 做 scope-aware identity classification；
3. 建立真正的 first go-forward PIT snapshot；
4. 同时开始 V4-08 B0/B1/B2 contract/vector 工作；
5. Prior-RPS repair 并行继续。

---

# 23. 最终状态

```text
V4_06_PROMOTION = PASS

V4_07_PROMOTION = PASS_WITH_GOVERNANCE_NOTE

V4_08_MEMBERSHIP_R1 =
EXTERNAL_ACCEPTANCE_BLOCKED_R1
CONTRACT_PERSISTENCE_REPAIR_AND_TRUE_FORWARD_PIT_BASELINE_REQUIRED

PRIOR_RPS =
INVESTIGATION_PASS
REPAIR_OPEN_NON_BLOCKING_FOR_UNRELATED_ENGINEERING
```
