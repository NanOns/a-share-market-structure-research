# V4-08 R3 独立外部验收审计｜2026-09-30

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**审计 HEAD**：`097a22f3fd8f7be405eab6e64a4f513d2ec64413`  
**上一外部审计 HEAD**：`0581731c1284e82380fa115156f1dc0a16a38bd4`  
**实现提交**：`1c60dae6fb7b6d35d3a22e43a63a6117d5d38bb0`  
**封存提交**：`097a22f3fd8f7be405eab6e64a4f513d2ec64413`

---

# 1. 唯一总状态

```text
V4_08_R3_EXTERNAL_ACCEPTANCE_BLOCKED_INPUT_PROMOTION_AUTHORIZED
```

解释：

- R3 的 **B07 source-revision basis guard：PASS**
- R3 的 **11-key target-day lifecycle adjudication：PASS**
- `V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1`：**允许外部 promotion**
- `V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1`：**允许外部 promotion**
- disposable PostgreSQL clean checkout：**PASS**
- Forward PIT source capture / temporal leakage / determinism：**PASS**
- 但当前 **真正 accepted PIT membership snapshot 尚未创建**
- 当前 formal membership rows 仍为 `INDUSTRY=0 / THEME=0`
- Sector/Rotation machine AST 仍有一个 `NOT_APPLICABLE` 语义缺口
- 五个 V4-00G retention 参数仍未冻结
- B2 Legacy Adapter / V4-10 production FSM 仍未实现

因此：

```text
V4-08 Accepted Head
=
NOT AUTHORIZED YET
```

但 R4 已允许直接执行 identity/calendar promotion 与第一张正式 PIT membership candidate materialization。

---

# 2. 提交链

从上一审计 HEAD：

`0581731c1284e82380fa115156f1dc0a16a38bd4`

到当前：

`097a22f3fd8f7be405eab6e64a4f513d2ec64413`

新增 2 个提交：

1. `1c60dae6fb7b6d35d3a22e43a63a6117d5d38bb0`
   - `feat(v4-08): add R3 basis guards and dated admission candidates`

2. `097a22f3fd8f7be405eab6e64a4f513d2ec64413`
   - `docs(v4-08): seal R3 isolated regression and external audit handoff`

第二个提交仅新增/修改验收报告、handoff 和 manifest，没有修改 R3 实现代码。

因此最终 clean-checkout 对 `1c60dae6...` 的测试可以覆盖当前 HEAD 的实际实现代码。

---

# 3. B07｜Source Revision → Snapshot → Fact Basis Guard

Migration：

`src/workbench_db/migrations/v4_postgres/019_v4_08_membership_source_basis_guard_r3.sql`

SHA-256：

`ec1fd08c6fef018ba0f92131e0e37de376372946ed935d9e5b2602ba024e6975`

Rollback SHA-256：

`a232b0e0aed3b493b4885ca875ac3e5b4bdfb9c89b1cc38fcf6f1a4c18efc711`

R3 已建立：

```text
revision.membership_basis
==
snapshot.membership_basis
==
fact.membership_basis
```

并冻结 basis ↔ quality compatibility：

```text
PIT_OBSERVED_ACCEPTED
→ PIT_OBSERVED

CURRENT_TDX_DIAGNOSTIC
→ CURRENT_TDX_MEMBERSHIP

CURRENT_REPLAY_DIAGNOSTIC
→ CURRENT_MEMBERSHIP_REPLAY

DERIVED_PARENT_DIAGNOSTIC
→ DERIVED_PARENT_MEMBERSHIP
```

formal view 也已显式要求：

```text
r.membership_basis = PIT_OBSERVED
s.membership_basis = PIT_OBSERVED
f.membership_basis = PIT_OBSERVED
```

并要求：

```text
revision chain valid
exact target-day asof
observed local date == target_trade_date
provider/system availability <= cutoff
mapped identity
PIT_OBSERVED_ACCEPTED quality
historical_backtest_safe
```

## B07 negative vectors

独立 disposable PostgreSQL verifier 已证明：

```text
B07_fact_trigger_rejects_mixed_source_basis = true
B07_snapshot_trigger_rejects_mixed_source_basis = true
B07_revision_insert_rejects_current_with_pit_quality = true
B07_formal_view_rejects_corrupt_mixed_basis = true
basis_quality_cross_pairs_rejected = true
positive_pit_formal_fact_visible = true
```

结论：

```text
B07 = PASS
```

---

# 4. Clean Checkout / Disposable PostgreSQL

R2 的 clean regression 隔离证据问题已关闭。

最终 receipt：

`reports/v4_08/V4_08_R3_CLEAN_CHECKOUT_RECEIPT.json`

测试提交：

`1c60dae6fb7b6d35d3a22e43a63a6117d5d38bb0`

状态：

```text
PASS_CLEAN_CHECKOUT_DISPOSABLE_DATABASE
```

关键证据：

```text
git_status_before = ""
git_status_after = ""

config_dot_env_read = false
configured_or_production_database_used = false

dsn_source =
PROCESS_ENVIRONMENT_DISPOSABLE_CLUSTER

server_address =
127.0.0.1/32

database =
market_research

PostgreSQL =
18.6

temporary_cluster_cleaned_up = true
password_persisted = false
```

完整 required regression：

```text
602 passed
2 skipped
0 failed
0 errors
```

覆盖：

```text
tests/v4_01
tests/v4_02
tests/v4_03
tests/v4_04
tests/v4_05
tests/v4_06
tests/v4_07
tests/v4_08
tests/v4_joint
tests/v4_phase0
```

结论：

```text
B08 = PASS
```

---

# 5. 11 个 required-board identity key 的生命周期裁决

R2：

```text
11 x AMBIGUOUS_IDENTITY
```

R3：

```text
FORMAL_IN_SCOPE_A_STOCK = 2
NOT_LISTED_AT_TARGET = 9
unresolved_remainder = 0
```

并明确：

```text
board_for(code)
NOT USED AS LIFECYCLE TRUTH
```

## 5.1 Target-active admissions

### SZ.001246 力勤资源

```text
classification =
FORMAL_IN_SCOPE_A_STOCK

board =
SZ_MAIN

listing_date =
2026-09-30

security_id =
SEC-9A2222852908DCC43E96059AFF5737DD
```

绑定目标日深交所 active query 与上市披露证据。

### SZ.301716 鸿富诚

```text
classification =
FORMAL_IN_SCOPE_A_STOCK

board =
CHINEXT

listing_date =
2026-09-29

security_id =
SEC-C7353CA6F8DE4D5EA38AC49E4AAC9CF3
```

绑定深交所目标日 active query 与上市证据。

## 5.2 NOT_LISTED_AT_TARGET

```text
SH.601206
SH.603302
SH.603361
SH.688688
SZ.001235
SZ.300728
SZ.301569
SZ.301660
SZ.301718
```

这些对象使用：

- target-day official active catalogue absence；
- 对能取得历史/发行证据的对象再补充历史 suspension / issuance evidence。

其中：

```text
301569
301660
301718
```

均没有被误纳入 2026-09-30 active formal universe。

结论：

```text
B06 = PASS_TARGET_DAY_SCOPE
```

注意：

> 本结论只接受 2026-09-30 target-day 11-key closure，不声称已经证明未来所有新增上市/退市对象的全市场增量 lifecycle 自动发现能力。

---

# 6. V4-01 Go-Forward Identity Candidate｜外部 Promotion 裁决

Candidate Head：

`data/v4/V4_01_GO_FORWARD_IDENTITY_CANDIDATE_HEAD_R1.json`

SHA-256：

`9ef49acc749daeb954cce0433363d0f28e54720db58c92fc20da77080049bb2c`

Identity Artifact：

`data/v4/artifact_store/v4_01/security_entity_map_GO_FORWARD_20260930_R1.json`

SHA-256：

`98c0d0c828c18d2dd012f5f2de27d420da49183c20116a790af91a33b7d12603`

Independent Postcheck：

`reports/v4_01/V4_01_GO_FORWARD_IDENTITY_INDEPENDENT_POSTCHECK_R1.json`

SHA-256：

`f5075537d55903910044c47d31197d46d42ad48c84f3caa787264e73ae9c8194`

已验证：

```text
all_11_terminal_dispositions = true
new_listing_dates_match_official_report = true
no_active_lifecycle_ambiguity = true
no_duplicate_new_canonical_ids = true
prior_records_exactly_preserved = true
candidate_not_self_promoted = true
```

## 外部裁决

```text
V4_01_GO_FORWARD_IDENTITY_INCREMENT_R1
=
EXTERNAL_ACCEPTANCE_PASS_TARGET_DAY_SCOPE
```

**允许 promotion。**

但 promotion 必须保持 append-only：

- candidate artifact 不修改；
- 生成新的 accepted promotion artifact/head；
- 两个新增 lifecycle record 的 acceptance 从 candidate 语义提升为 accepted；
- 不允许改变 security_id / board / list_date / source evidence；
- 9 个 NOT_LISTED_AT_TARGET disposition 不得被改成 active identity；
- 原 R7 accepted identity map 不覆盖。

---

# 7. V4-02 Go-Forward Calendar Extension｜外部 Promotion 裁决

Candidate Head：

`data/v4/V4_02_GO_FORWARD_CALENDAR_EXTENSION_CANDIDATE_HEAD_R1.json`

SHA-256：

`800a32d26b8a6089f67eda77e84c2364d4d0fd8a9879ed1b5c620be71202631b`

Calendar Artifact：

`data/v4/artifact_store/v4_02/market_calendar_GO_FORWARD_20260930_R1.json`

SHA-256：

`abb832c49e447996b33d7ebf4f233ccfbd4d7f4abc0722caa164d8e25a9ecfc3`

Independent Postcheck：

`reports/v4_02/V4_02_GO_FORWARD_CALENDAR_EXTENSION_POSTCHECK_R1.json`

SHA-256：

`75b2580d1daa1405ac701a3b5513deb339c294f1142f1dc1f1cd50737e3244a7`

Extension：

```text
2026-09-28
2026-09-29
2026-09-30
```

SSE / SZSE 均：

```text
session_no 787
session_no 788
session_no 789
```

原 accepted calendar 截止：

```text
2026-09-24
session_count = 786
```

中间：

```text
2026-09-25 ~ 2026-09-27
```

为中秋休市，因此 session chain 连续正确。

项目内 evidence 与独立官方公开信息均支持：

```text
9月25日至9月27日休市
9月28日起照常开市
```

## 外部裁决

```text
V4_02_GO_FORWARD_CALENDAR_EXTENSION_R1
=
EXTERNAL_ACCEPTANCE_PASS_THROUGH_2026_09_30
```

**允许 promotion。**

candidate extension artifact 本身保持不可变，由新的 accepted promotion head 绑定。

---

# 8. Source-Time / Membership-As-Of Policy

继承 R2 外部裁决：

```text
provider_available_at_basis =
PROJECT_FIRST_OBSERVED_PROVIDER_BYTES
```

以及：

```text
membership_asof_basis =
PROJECT_FIRST_OBSERVED_SOURCE_STATE
```

R3 已固化为：

`config/v4_08_tdx_source_availability_policy_v2.json`

状态：

```text
EXTERNALLY_ACCEPTED_GO_FORWARD_POLICY_ONLY
```

R3 source capture：

```text
complete_source_observed_at =
2026-09-30T06:32:59.707313Z

Asia/Shanghai =
2026-09-30 14:32:59
```

candidate engineering cutoff：

```text
2026-09-30T06:37:57.511101Z
```

满足：

```text
source observed before cutoff
same local target date
no filesystem mtime
no previous-day reuse
no backdating
```

结论：

```text
PASS
```

---

# 9. Forward PIT Candidate｜目前仍不能作为正式 baseline

当前：

`reports/v4_08/V4_08_R3_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json`

明确：

```text
snapshot_created = false
pit_observed = false
historical_backtest_safe = false
formal_consumers_enabled = false
first_accepted_forward_pit_target_date = null
```

formal rows：

```text
INDUSTRY = 0
THEME = 0
```

prospective diagnostic counts：

```text
INDUSTRY = 5224
THEME = 44938
```

其中 `5224` 与上一 accepted 5222 target identity scope + 本轮两只新上市 target-active identity 在数量关系上吻合。

但：

> prospective diagnostic count 不能替代真正 accepted source revision / snapshot / fact materialization。

所以：

```text
V4_08_PIT_MEMBERSHIP_BASELINE
=
NOT YET ACCEPTED
```

这是当前 R3 总阶段仍 BLOCKED 的主要原因。

---

# 10. Forward PIT Engineering Checks

R3 已通过：

```text
daily observation date matches target
frozen source hashes match
no excluded row prospectively admitted
no unauthorized PIT snapshot created
prelist/noncore preserved in diagnostics
unknown required remainder = 0
no backdating
no carry-forward
deterministic reparse
```

Determinism：

```text
first_digest =
d759007481cbee7a8eb7a71c9270d19aa93d9aa1a64dee57e5f1d166dc597d9c

second_digest =
d759007481cbee7a8eb7a71c9270d19aa93d9aa1a64dee57e5f1d166dc597d9c
```

所以 promotion 后可以直接进入正式 PIT materialization，不需要重做 R3 discovery。

---

# 11. Sector / Rotation Machine AST

R3 相比 R2 有明显进展。

已新增真正结构化 AST：

- `V4_08_SECTOR_PREWATCH_B0_V2`
- `ROTATION_CORE_V1_R3`

并绑定：

```text
model_contract_id
parameter_set_id
AST digest
field_registry_digest
machine_vector_set_digest
producer
time_role
quality_requirement
UNKNOWN behavior
```

状态：

```text
PASS_STRUCTURED_BOUND_AST_ENGINEERING_ONLY
```

R1A / R1B / R2 / R3 vectors：

```text
PASS
```

R1B 已正式覆盖：

```text
strong_prev = 0
pulse_age >= 2
early_retained = TRUE
=> ROTATION_ACCEPTED possible
```

这关闭了 R2 的 R1 vector coverage 缺口。

---

# 12. 新发现：Canonical AST 缺失 NOT_APPLICABLE 语义

REV2 §21A.4 明确：

```text
strong_prev = 0
→ mature_retained = NOT_APPLICABLE
```

并且：

```text
NOT_APPLICABLE
!= FALSE
!= UNKNOWN
```

当前：

`src/sector/machine_ast_r3.py`

AST evaluator 只表达：

```text
True
False
None(UNKNOWN)
```

没有正式的：

```text
NOT_APPLICABLE
```

当前 contract：

```text
mature_retained =
early_retained
AND strong_prev > 0
AND strong_member_retention >= threshold
```

因此：

```text
strong_prev = 0
```

会得到：

```text
FALSE
```

而测试：

```python
assert evaluate_ast('mature_retained', ...) is False
```

也把这个错误语义固定住了。

虽然当前正式 consumer 关闭，而且对 EXPANDING / REACCELERATING 的“不能升级”结果暂时等价，但它会污染：

- 原因解释；
- mature branch quality；
- NOT_APPLICABLE 与真实失败的审计区别；
- 未来 ordered reducer/FSM 的语义。

所以：

```text
ROTATION_MACHINE_AST
=
PARTIAL_PASS_ENGINEERING_ONLY
```

不能升级成正式算法合同。

---

# 13. R4 对 NOT_APPLICABLE 的修复要求

Machine AST 必须支持四态：

```text
TRUE
FALSE
UNKNOWN
NOT_APPLICABLE
```

至少冻结以下行为：

```text
AND / OR / REF
对 NOT_APPLICABLE 的语义
```

与 REV2 一致：

- mature 专用路径 N/A 不传播成 early UNKNOWN；
- retention OR 中一个分支 N/A、另一个 TRUE → TRUE；
- 两个 retention 分支都 N/A → UNKNOWN / branch unavailable，按 REV2 明确行为；
- `strong_prev=0 → mature_retained=NOT_APPLICABLE`；
- N/A 不可作为 TRUE 通过 EXPANDING / REACCELERATING；
- N/A 也不能记录成“strong retention failed”。

必须增加 canonical AST tests，而不是只在旧 `evaluate_rotation_vector()` helper 中保留 N/A。

---

# 14. 五个 retention 参数

仍未赋值：

```text
V4_08_EARLY_SEED_RETENTION_MIN
V4_08_EARLY_BREADTH_RETENTION_MIN
V4_08_EARLY_BREADTH_DELTA_MIN
V4_08_EARLY_TOP1_CONCENTRATION_MAX
V4_08_MATURE_STRONG_RETENTION_MIN
```

当前做法正确：

```text
runtime_values_supplied = false
affected_rotation_formal_consumer_enabled = false
```

这些参数：

- 不阻塞 identity/calendar promotion；
- 不阻塞 PIT membership baseline；
- 不阻塞 non-seed Sector Native engineering；
- 继续阻塞 affected Rotation formal qualification。

---

# 15. B2 / V4-10 / Prior-RPS

当前：

```text
B2 Legacy Adapter =
NOT_IMPLEMENTED

V4-10 Production FSM =
NOT_IMPLEMENTED

Prior-RPS =
OPEN_REPAIR_CONTINUES_INDEPENDENTLY
```

这些均没有被伪装成 PASS。

Prior-RPS 继续只阻塞 true Seed / Seed Width dependent fields。

不应阻塞：

- identity promotion；
- calendar promotion；
- PIT membership baseline；
- non-seed Sector Native；
- AST infrastructure。

---

# 16. GitHub CI

当前 commit combined status：

```text
statuses = []
```

仓库没有提供 GitHub CI status 作为额外证据。

本轮已有 clean detached checkout + disposable PostgreSQL + 602-pass required regression，因此：

```text
NO_GITHUB_STATUS
```

作为证据限制记录，不单独构成 blocker。

---

# 17. 外部独立交叉验证

独立公开核验确认：

- 上海证券交易所 2026 年中秋节休市为 `9/25–9/27`，`9/28` 起照常开市；
- 深圳证券交易所发布相同休市安排；
- 鸿富诚 `301716` 上市时间为 `2026-09-29`，创业板；
- 力勤资源 `001246` 在 `2026-09-30` 已实际进入深交所主板交易；
- 联亚药业 `301569`、粤芯半导体 `301660` 截至本轮核验仍未显示已上市日期；
- 通则康威 `301718` 的申购日为 `2026-10-09`。

这些与 R3 target-day lifecycle disposition 一致。

---

# 18. 本轮逐项验收

| 项目 | R3 外部结论 |
|---|---|
| B07 source revision basis guard | PASS |
| B08 disposable clean regression | PASS |
| 11-key lifecycle adjudication | PASS_TARGET_DAY_SCOPE |
| V4-01 identity candidate | EXTERNAL_PROMOTION_AUTHORIZED |
| V4-02 calendar extension candidate | EXTERNAL_PROMOTION_AUTHORIZED |
| source-time policy | PASS / inherited |
| exact-day source capture | PASS |
| temporal leakage | PASS |
| deterministic reparse | PASS |
| first actual PIT snapshot | NOT_CREATED |
| formal membership rows | 0 / 0 |
| B0 structured AST | ENGINEERING PASS |
| Rotation R1A/R1B/R2/R3 | PASS |
| Rotation canonical NOT_APPLICABLE | FAIL / REPAIR REQUIRED |
| 5 retention parameters | PENDING |
| B2 legacy adapter | NOT_IMPLEMENTED |
| Prior-RPS | OPEN |
| V4-08 Accepted Head | NOT AUTHORIZED |

---

# 19. 外部 Promotion Authorization

本审计正式授权下一轮将以下两个**精确 candidate** 晋升为 accepted input：

## Identity

```text
candidate head sha256 =
9ef49acc749daeb954cce0433363d0f28e54720db58c92fc20da77080049bb2c

identity artifact sha256 =
98c0d0c828c18d2dd012f5f2de27d420da49183c20116a790af91a33b7d12603
```

Scope：

```text
2026-09-30 target-day incremental identity closure
```

## Calendar

```text
candidate head sha256 =
800a32d26b8a6089f67eda77e84c2364d4d0fd8a9879ed1b5c620be71202631b

calendar artifact sha256 =
abb832c49e447996b33d7ebf4f233ccfbd4d7f4abc0722caa164d8e25a9ecfc3
```

Scope：

```text
SSE / SZSE sessions through 2026-09-30
```

任何 digest 改变、身份日期改变、session 变化都必须重新审计。

---

# 20. R4 准入

下一轮直接执行：

```text
V4_08_R4_INPUT_PROMOTION_FIRST_PIT_MATERIALIZATION_AND_NA_AST_REPAIR
```

不要重新做：

```text
B01
B02
B03
B04
B05
B06
B07
B08
11-key source discovery
calendar holiday discovery
R1A/R1B vector discovery
```

R4 只做：

1. exact identity candidate promotion；
2. exact calendar candidate promotion；
3. materialize first actual 2026-09-30 PIT membership source revision / snapshot / facts；
4. independent recompute formal INDUSTRY/THEME rows；
5. PostgreSQL formal view readback；
6. acceptance head candidate；
7. canonical AST `NOT_APPLICABLE` repair；
8. keep five pending parameters / B2 / Prior-RPS truthfully degraded；
9. stop for final independent V4-08 membership acceptance.

---

# 21. 唯一最终结论

```text
V4_08_R3_EXTERNAL_ACCEPTANCE_BLOCKED_INPUT_PROMOTION_AUTHORIZED
```

当前不是“修复失败”。

更准确地说：

```text
R3 CONTRACT / IDENTITY / CALENDAR / DB ISOLATION
=
PASS

V4_01 + V4_02 GO-FORWARD INPUTS
=
EXTERNAL PROMOTION AUTHORIZED

V4_08 FIRST PIT BASELINE
=
WAITING FOR DETERMINISTIC MATERIALIZATION

ROTATION AST
=
WAITING FOR NOT_APPLICABLE SEMANTIC REPAIR
```

全局 accepted stage range 在实际 R4 promotion/materialization 前仍保持：

```text
V4_00_TO_V4_07_ACCEPTED
```
