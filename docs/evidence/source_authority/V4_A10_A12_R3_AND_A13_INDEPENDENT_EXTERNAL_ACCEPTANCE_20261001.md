# V4 A10/A12-R3 + A13 独立外部验收审计｜2026-10-01

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计 HEAD：** `d85f815097a09ca2dceda00d0e29d6ff4fe331d4`  
**上一轮审计基线：** `a43d663a0cc62d48f65a1160fae9c50874d86548`

## 1. 唯一总状态

```text
A10_A12_R3_IMPLEMENTATION =
EXTERNAL_ACCEPTANCE_PASS_PRODUCER_SOURCE_INSTANCE_SCOPE

A12_HISTORICAL_PATH_B =
PASS_REAFFIRMED_RECONSTRUCTED_ONLY

A12_DAILY_TRADING_STATUS_PRODUCER_V4 =
EXTERNAL_ACCEPTANCE_PASS_PRODUCER_SCOPE

A12_DAILY_ISST_PRODUCER_V4 =
EXTERNAL_ACCEPTANCE_PASS_PRODUCER_SCOPE

A13_OFFICIAL_EVENT_SEMANTICS =
EXTERNAL_ACCEPTANCE_PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT

V4_08_ACCEPTED_HEAD = KEEP

CURRENT_REPOSITORY_FORMALIZATION =
BLOCKED_BY_INVALID_EXTERNAL_AUTHORITY_BINDING

DM01_FINAL_ALL_NINE =
BLOCKED_PENDING_CORRECT_FORMAL_REGISTRATION

V4_DATA_ACCEPTED_HEAD = KEEP_2026_09_24
V4_STAGE_ACCEPTED_RANGE = KEEP_V4_00_TO_V4_10_ACCEPTED

PRODUCTION = FALSE
SHADOW = FALSE
FOCUS = FALSE
```

关键区分：A10/A12-R3 与 A13 的技术实现和证据已经达到外部验收要求；当前不能直接宣布仓库正式闭环，是因为 Codex 把“修复任务卡”错误地登记成 `external_authority`。这属于正式治理链错误，不是算法、数据或业务结果失败。

## 2. Clean boundary

A10/A12-R3 实现测试 commit：

```text
0a5804b4b87301298a5a481c6b702e377ea03df1
```

其后 `2bc35884...` 只增加 clean regression / seal evidence，无业务代码变化。

A13 实现测试 commit：

```text
05099bd71fd469c3db5115550815697aef2ca843
```

其后最终 `d85f815...` 只增加 clean regression / seal evidence，无业务代码变化。

因此 clean regression 与最终实现边界一致。

## 3. A10/A12-R3 Producer / Source Instance 分层｜PASS

本轮已真实拆成：

```text
Layer A: Producer Authority Contract
Layer B: Per-Date Source Instance
```

Producer candidates：

```text
BAOSTOCK_DATED_TRADING_STATUS_PROVIDER_AUTHORITY_V4
BAOSTOCK_DATED_ISST_PROVIDER_AUTHORITY_V4
```

均声明：

```text
routine_daily_revision_requires_human_acceptance = false
substantive_change_requires_new_acceptance = true
historical_modes = TARGET_DATE_QUERYABLE_FACT
knowledge_lineage = RECONSTRUCTED_CORRECTED
local_TDX_actual_precedence = true
OHLC_authority = false
adjustment_authority = false
```

解决了此前“每个交易日重新做人为 owner acceptance”的错误模型。

## 4. Per-Date Source Instance｜PASS

新增：

```text
SOURCE_AUTHORITY_SOURCE_INSTANCE_POLICY_V1
```

真实 manifest：

```text
2026-09-28:
  TRADING_STATUS
  ISST

2026-09-30:
  TRADING_STATUS
  ISST

missing_target_dates:
  2026-09-29
```

9/28 和 9/30 均绑定 target_trade_date、provider_date、raw artifact/hash、observed_at、received_at、source_revision、schema、accepted identity 与 accepted calendar。

并明确：

```text
AS_RECORDED = false
first_available_at_target_proven = false
knowledge_lineage = RECONSTRUCTED_CORRECTED
```

## 5. Global Gate 已真正拒绝 9/29｜PASS

`evaluate_consumer_gate()` 在存在 `source_instance_policy_id` 时调用 `require_formal_source()`，继续执行：

```text
require_accepted_producer()
require_source_instance_for_target()
```

因此 Global Authority Gate 自身具备 target-date source instance 门，不再依赖 adapter 私有检查。

真实向量：

```text
9/28 + valid instance → PASS
9/30 + valid instance → PASS

9/29 + no instance
→ SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE
→ FAIL
```

Evidence 同时证明：

```text
candidate_fact_called = false
global_gate_independently_blocks_missing_day = true
```

上一轮 P0 核心 blocker 已关闭。

## 6. Source Instance 负向量｜PASS

覆盖 wrong provider_date、wrong target、wrong raw SHA、wrong schema、received<observed、naive time、wrong revision、wrong identity、wrong calendar、empty、duplicate/ambiguous、wrong row date、unbounded、malformed bit、AS_RECORDED mint、wrong field、partial roster，均 fail closed。

并验证：

```text
accepted input revision != producer semantics revision
```

普通 target-date source/input revision 不需要重新做人为 producer acceptance。

## 7. Complete accepted universe binding｜PASS

Source instance 重新从 accepted dated identity head 计算 eligible universe，并要求 provider rows exact set 等于 accepted dated eligible universe exact set，同时绑定 accepted calendar target session。避免 provider 少返回对象时被误当成 universe 不存在。

## 8. Historical Path B｜PASS_REAFFIRMED

历史 archive 对 `2023-07-04 ~ 2026-09-24` 逐 target date 建 source revision census。

严格限制：

```text
TARGET_DATE_QUERYABLE_FACT
RECONSTRUCTED_CORRECTED
AS_RECORDED = false
first_available_at_target_proven = false
```

`require_historical_instance()` 要求 target date 必须存在于 `source_revisions_by_target_date`，并再次绑定 full-row oracle、primary receipts、bounded recovery 和 source bytes。

因此上一轮历史 Path B 技术 acceptance 继续成立。

## 9. 当前 Repository Formalization 存在硬错误

当前：

```text
reports/audits/A10_A12_R3_EXTERNAL_DISPOSITION_R1.json
data/v4/V4_SOURCE_AUTHORITY_ACCEPTED_OWNER_REGISTRY_R2.json
```

把：

```text
docs/evidence/source_authority/
V4_A10_A12_R3_PRODUCER_SOURCE_INSTANCE_SCOPE_REPAIR_TASK_20261001.md
```

登记成 `external_authority`。

这是错误的：该文件是 **REPAIR TASK CARD**，不是 **INDEPENDENT EXTERNAL ACCEPTANCE**。

上一轮真正的独立审计 MD 又没有进入仓库。

所以：

```text
TECHNICAL_ACCEPTANCE = KEEP
FORMAL_REGISTRATION = REBUILD_REQUIRED
BUSINESS_HEAD_ROLLBACK = NO
```

Registry R2 的 `EXTERNALLY_ACCEPTED` 状态不能作为最终合法 provenance 继续继承，必须新增版本并重绑真正的独立审计文件。

## 10. Daily Producer V4 外部接受裁决

本轮接受：

```text
BAOSTOCK_DATED_TRADING_STATUS_PROVIDER_AUTHORITY_V4
BAOSTOCK_DATED_ISST_PROVIDER_AUTHORITY_V4
```

Scope：

```text
PRODUCER_SEMANTIC_AUTHORITY
TARGET_DATE_QUERYABLE_FACT
RECONSTRUCTED_CORRECTED
```

允许机器验证后消费 daily source instance，routine daily revision 不需要重新做人为 acceptance。

禁止：

```text
AS_RECORDED
FIRST_AVAILABLE_AT_TARGET
OHLC authority
QFQ/adjustment authority
missing target source
consumer outside scope
```

下一版正式 Registry 必须绑定本独立外部验收文件。

## 11. A10/A12-R3 Clean Regression

```text
1422 passed
2 skipped
0 failures
0 errors
```

未读取 config/.env，未使用 production DB，Accepted business heads unchanged。

## 12. A13 Event Semantics｜PASS

新增 `OFFICIAL_EVENT_SEMANTICS_V1`，区分：

```text
LISTED_STOCK_TRADING_SUSPENSION
LISTED_STOCK_RESUMPTION
IPO_ISSUANCE_POSTPONEMENT
IPO_LISTING_POSTPONEMENT
IPO_TERMINATION
DELISTING_PHASE
RISK_WARNING_CHANGE
LISTING
CODE_CHANGE
OTHER_OFFICIAL_NOTICE
UNKNOWN_EVENT_SEMANTICS
```

明确：

```text
filename_or_capture_id_grants_trading_authority = false
unknown_event_may_enter_trading_status = false
```

## 13. A13 全量 inventory｜PASS

扫描：

```text
9 capture manifests
462 capture reference objects
197 manifest candidates
134 semantic entries
```

分类：

```text
CODE_CHANGE                  4
DELISTING_PHASE             22
IPO_ISSUANCE_POSTPONEMENT   24
IPO_LISTING_POSTPONEMENT     6
LISTING                     12
OTHER_OFFICIAL_NOTICE       16
RISK_WARNING_CHANGE          3
UNKNOWN_EVENT_SEMANTICS     47
```

UNKNOWN 未自动升级成 trading truth。

## 14. A13 Consumer Inventory｜PASS

结论：

```text
V4-08 admission:
active catalogue/exchange query + accepted identity 决定

lifecycle notice:
supporting/diagnostic evidence

V4-02 status/ST:
dated structured facts + TDX actual precedence

DM01:
notice not consumed
```

新的 formal trading notice consumer `require_trading_event()` 必须绑定 accepted semantic head/sidecar、raw bytes、security key、effective date、identity evidence 与明确 dated statement。

## 15. A13 反事实｜PASS_NO_BUSINESS_IMPACT

对：

```text
SH.603302
SH.688688
SZ.300728
```

删除误命名 notice 后重新执行 admission：

```text
full_PIT_equal_to_accepted = true
full_PIT_fact_count = 50,162
```

下游变化：

```text
V4_07_BASE_SEED       changed rows = 0
V4_08_B0              changed rows = 0
V4_08_B2              changed rows = 0
V4_08_ROTATION        changed rows = 0
V4_08_SECTOR_NATIVE   changed rows = 0
V4_09_STOCK_PREWATCH  changed rows = 0
```

因此：

```text
BUSINESS_REBUILD_REQUIRED = false
EVIDENCE_SEMANTICS_AMENDMENT_REQUIRED = true
V4_08_ACCEPTED_HEAD = KEEP
```

成立。

## 16. A13 Clean Regression

```text
1444 passed
2 skipped
0 failures
0 errors
```

Accepted Heads unchanged。

## 17. Accepted Head 检查

最终 HEAD：

```text
V4_DATA_ACCEPTED_HEAD.accepted_trade_date = 2026-09-24
V4_STAGE_ACCEPTED_HEAD.accepted_stage_range = V4_00_TO_V4_10_ACCEPTED
```

V4-08、V4-10 Accepted Head 未移动。

权限仍：

```text
production = false
shadow = false
focus = false
```

## 18. 正式外部验收结论

```text
A10_A12_R3_CODE_AND_EVIDENCE = PASS

A10_A12_R3_DAILY_PRODUCER_ACCEPTANCE =
PASS_PRODUCER_SCOPE

A12_HISTORICAL_PATH_B =
PASS_REAFFIRMED_RECONSTRUCTED_ONLY

A13_EVENT_SEMANTICS =
PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT

V4_08_HEAD = KEEP

CURRENT_REGISTRY_R2_FORMAL_PROVENANCE =
INVALID_EXTERNAL_AUTHORITY_BINDING

FORMALIZATION_REPAIR = REQUIRED

DM01 = NOT_YET_ACCEPTED
```

## 19. 下一步授权

### P0

允许正式化 A10/A12-R3：

```text
加入本独立验收文件
新增 versioned governance/registry/head
历史 Path B 重新绑定真实 external audit
正式登记两个 daily producer V4
验证 9/28 PASS / 9/29 FAIL / 9/30 PASS
```

该 validation PASS 后，可以在**同一工作包**继续执行 DM01 A01-R3 candidate chain，无需再停下来等待人工确认。

### P1

允许正式化 A13：

```text
本独立验收作为 external authority
生成 accepted semantic sidecar/head
Registry audit entry 接受 evidence-governance scope
V4-08 business head 不移动
```

## 20. DM01 后续边界

P0 正式化通过后，Data Head 仍是 `2026-09-24`。

后续必须按 calendar 顺序：

```text
2026-09-28
2026-09-29
2026-09-30
```

不能跳 9/29。

当前 9/29 没有 source instance，所以必须真实查询 BaoStock `target=2026-09-29`，冻结 raw response，并标记：

```text
DELAYED_HISTORICAL_RETRIEVAL
RECONSTRUCTED_CORRECTED
AS_RECORDED = false
first_available_at_target_proven = false
```

此时不需要新的 human producer acceptance。

DM01 可以生成连续 candidate chain，但下一次独立外部验收前：

```text
不得移动 V4_DATA_ACCEPTED_HEAD
不得声明 DM01 accepted
```
