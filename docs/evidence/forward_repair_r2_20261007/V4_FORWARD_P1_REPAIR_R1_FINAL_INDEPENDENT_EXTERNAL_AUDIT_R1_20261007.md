# V4 Forward P1 Repair R1｜最终独立外部验收审计 R1｜2026-10-07

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 任务基线: `0c78051c570bdd68ef98f1cb9fdcfcd315759ec2`
- 候选提交: `faa943dee063957bed8e3fe3599436cc18316249`
- 当前远端 HEAD: `15a4e1cc545f6c44d94ebb2b63e71fba6c69e63a`
- 任务卡: `V4_FORWARD_P1_REPAIR_R1_IA09_IA01_IA02_TASK_20261006.md`

## 1. 唯一结论

```text
FORWARD_P1_REPAIR_R1_EXTERNAL_AUDIT =
PASS_FINAL_ENGINEERING_CANDIDATE_SCOPED

IA-09 = PASS_WITH_CLOSED_EXECUTION_INCIDENT
IA-01 = PASS_ENGINEERING_CANDIDATE
IA-02 = PASS_ENGINEERING_CANDIDATE

ACTIVE_ACCEPTED_FORWARD_RUNTIME_SWITCHED_TO_V1_1 = false

IA-03 = OPEN_P2
IA-04 = OPEN_P2
IA-05 = OPEN_P1
IA-06 = OPEN_P1
IA-07 = OPEN_P2
IA-08 = OPEN_P2
IA-10 = OPEN_P2

FIRST_REAL_SHADOW_AUTHORIZED = false
PRODUCTION = false
```

本轮通过的是 additive Forward successor candidate，不是当前真实 runtime promotion。

## 2. Additive successor

没有覆盖旧 `v4_15_settlement.py / v4_15_settlement_successor.py / v4_16_settlement_worker_v2.py`。

新增：

```text
config/v4_15_forward_p1_candidate_contract_v1.json
src/workbench_analysis/v4_15_forward_p1.py
scripts/v4_16_forward_p1_worker.py
```

身份：

```text
FORWARD_PRICE_PATH_V1_1
SECTOR_BASKET_FORWARD_PATH_V1
```

且明确：

```text
SIMULATION_ONLY_CANDIDATE_WORKER
NO_ACCEPTED_DEPENDENCY_SELECTS_IT
runtime_authorized = false
real_shadow_authorized = false
production = false
```

因此 immutable/successor 边界合格。

## 3. IA-01｜PASS

原问题：合法 T0 + 合法 T+N endpoint 会因 interior gap/adjustment unknown 被整体清空 `R_N`。

V1.1 现在先独立验证 endpoint，再验证 path：

```text
endpoint valid
→ R_N 保留

interior invalid/unknown
→ MFE_N / MAE_N / PATH_MDD_CLOSE_N = null
→ path_quality = MATURED_DATA_MISSING
```

endpoint strictness仍保留：
- verified identity；
- verified adjustment；
- T0 basis；
- affine；
- adjustment identity；
- evaluation basis；
- terminal semantics。

12 个 STK 向量覆盖 full parity、interior gap、affine gap、invalid endpoint/T0、identity/basis mismatch、suspension、corporate action、revision、relative market、no interpolation。

核心反例已修正：

```text
T0=10
T+N=11
interior unavailable
=> R_N=0.1
=> path metrics UNKNOWN
```

历史 outcome 不覆盖，candidate 使用新 contract/revision identity。

裁决：

```text
IA-01 = PASS_ENGINEERING_CANDIDATE
```

## 4. IA-02｜PASS

新增 dedicated Sector basket，而不是继续把 sector aggregate 伪装成 stock OHLC。

冻结：
- sector subject；
- membership snapshot；
- member IDs；
- initial weights/fixed shares；
- T0 basis；
- member source identity；
- member adjustment identity；
- constituent policy。

并生成：

```text
sector_basket_identity_digest
sector_basket_source_digest
```

成员逐一验证后按 original weight 聚合；coverage 不完整时 UNKNOWN，不重权。

Sector subject 仅保留：

```text
R_N
MFE_CLOSE
MAE_CLOSE
```

并显式：

```text
MFE_N = null
MAE_N = null
PATH_MDD_CLOSE_N = null
stock_extrema_applicability = NOT_APPLICABLE_SECTOR
```

没有 synthetic high/low，也没有伪造 stock adjustment identity。

12 个 SEC 向量覆盖 2-member 10→11、partial coverage、corporate action、frozen membership、field semantics、n<2、relative-sector independence、market parity、immutable history、correction revision。

裁决：

```text
IA-02 = PASS_ENGINEERING_CANDIDATE
```

## 5. IA-09｜PASS_WITH_CLOSED_EXECUTION_INCIDENT

新增 repository-wide pytest safety guard：

```text
conftest.py
tests/runtime_isolation.py
tests/runtime_isolation_plugin.py
```

实现：
- live/repo DuckDB input 强制 read-only；
- explicit writer reject；
- migration-capable metadata read 改为 read-only handle；
- service/recovery root 必须 disposable；
- repo/TDX protected roots reject；
- recovery mode必须显式；
- background recovery escape reject；
- child env 最小化；
- M12 使用 disposable DB/root。

TISO-01～08 有执行证据。

最终 accepted regression 的 protected fingerprint：

```text
BEFORE SHA256 =
0102de2ee502617cd3992d913edfc1f7cad20fde3f6b82311d37367fb63bebdd

AFTER SHA256 =
0102de2ee502617cd3992d913edfc1f7cad20fde3f6b82311d37367fb63bebdd

protected drift = 0
```

### 执行事故必须永久保留

在全局 guard 完成前的一次回归中：

```text
data/database/market_research.duckdb
```

发生过 physical byte drift。

该失败执行不能宣称 zero-write。

现有 evidence 显示：
- changed SHA 与 original SHA 不同；
- 103 个 base tables rows 一致；
- views/indexes 一致；
- 未见 logical data loss；
- changed snapshot 留存；
- original exact snapshot 恢复；
- mtime 恢复；
- 随后增加 repository-wide guard；
- fresh regression 再跑；
- final protected fingerprint exact equal。

所以正式记录：

```text
IA09_EXECUTION_INCIDENT_20261006 =
CLOSED_WITH_RESTORATION_EVIDENCE
```

不能在未来改写成“从未触碰 live DB”。

裁决：

```text
IA-09 = PASS_WITH_CLOSED_EXECUTION_INCIDENT
```

## 6. Regression

```text
IA-09 targeted = 30 passed
IA-01 vectors = 12 passed
IA-02 vectors = 12 passed

affected regression =
283 passed
0 failed
0 errors
0 introduced failures

opt-in PG cases unexecuted = 278
IA-06 = OPEN

safe collection exit = 2
IA-05 = OPEN
```

所以：

```text
AFFECTED_REGRESSION = PASS_SCOPED
GLOBAL_REPOSITORY_GREEN = false
```

## 7. Protected State

保持：
- V4_STAGE_ACCEPTED_HEAD unchanged；
- V4_DATA_ACCEPTED_HEAD unchanged；
- V4_15_ACCEPTED_HEAD unchanged；
- Current Audit Head unchanged；
- REAL_SHADOW_OBSERVATIONS=0；
- PIT_OBSERVED_REAL_SAMPLES=0；
- runtime/real shadow authorization=false；
- Production/Focus/Default UI=false；
- FEP permissions unchanged；
- V4_16～22 formal Accepted Heads absent。

## 8. Active runtime边界

当前 candidate contract 明确：

```text
SIMULATION_ONLY
NO_ACCEPTED_DEPENDENCY_SELECTS_IT
```

worker 对非 simulation：

```text
FORWARD_P1_INDEPENDENT_ACCEPTANCE_REQUIRED
```

因此本外审通过后：

```text
FORWARD V1.1 ENGINEERING CANDIDATE = EXTERNALLY_ACCEPTED
ACTIVE REAL RUNTIME CONSUMER = NOT PROMOTED
```

考虑 IA-03 / IA-04 仍在同一 Forward 语义链开放，不建议现在推广 V1.1；应先完成 R2，再统一 successor admission，避免 V1.1→V1.2 连续 authority churn。

## 9. 保持 OPEN

```text
IA-03 P2 same-source PENDING/DUE collision
IA-04 P2 invalid actual price/OHLC boundary
IA-05 P1 global pytest collection debt
IA-06 P1 PG/sklearn environment verification gap
IA-07 P2 performance validation debt
IA-08 P2 historical provenance routing debt
IA-10 P2 standalone CLI bootstrap
```

## 10. 状态更新

```text
V4-15 Forward V1.1 candidate =
ENGINEERING_REPAIR_ACCEPTED_SCOPED

V4-15 active accepted Forward runtime =
UNCHANGED

V4-16 Forward candidate worker =
ENGINEERING_ACCEPTED_SIMULATION_ONLY

V4-16 real Forward consumer =
NOT_PROMOTED
```

## 11. 下一步

```text
V4_FORWARD_REPAIR_R2 =
IA-03 + IA-04 + IA-10
```

R2 通过后再决定最终 successor admission / runtime dependency propagation。

**最终状态：PASS_FINAL_ENGINEERING_CANDIDATE_SCOPED**
