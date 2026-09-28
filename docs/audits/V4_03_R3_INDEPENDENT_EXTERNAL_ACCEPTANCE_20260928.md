# V4-03 R3 独立外部增量验收报告

- 日期：2026-09-28
- 仓库：`NanOns/a-share-market-structure-research`
- 分支：`codex/v4-system-reform`
- 验收 HEAD：`fb4f43afffdfc6ae1a9fa3dc4361f994957cc4b3`
- 提交：`[V4-03] Close remaining stock market and native contract blockers`
- 前一验收基线：`c8c8f1287c913bebbe5e5d19eee01af7fbb96309`
- 治理任务：`docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md`
- 验收方式：远端源码、配置、合同、测试源码、staging receipts、independent postcheck 和 accepted-head 静态独立复核；未修改仓库。
- GitHub CI：当前 commit status 无 checks，Actions workflow run 为 0；因此仓库自报测试运行不能视为本轮外部亲自执行。

---

# 1. 最终裁决

```text
V4_03_EXTERNAL_ACCEPTANCE = BLOCKED

V4_03_FINAL_STAGE_ACCEPTANCE = NOT_GRANTED
V4_04_ENTRY = BLOCKED
```

R3 比 R2 有明显实质进展，但尚不能签发最终 V4-03 acceptance。

当前主要硬阻断已经从旧的 B01/C04/C05 全面缺失，收敛为：

1. **Market Regime 实现公式与 REV2 冻结合同不一致（P0）**；
2. **Market Regime native machine contract 只验证阈值映射，没有冻结/执行上游 primitive 的正式算法（P0）**；
3. **多个实际使用 PIT Universe 的候选仍自标 `DIAGNOSTIC_NON_PIT`，与正式接受语义冲突（P1 / acceptance metadata blocker）**；
4. **Determinism 回执的 contract-vector baseline SHA 与 replay SHA 不一致，但 verifier 没有把 baseline mismatch 纳入 FAIL 条件（P1 evidence blocker）**。

Sector membership 继续按 capability scope 阻断，不应重新升级为全局 V4-03 blocker。

---

# 2. 提交范围确认

`c8c8f12 -> fb4f43a` 只有 1 个实现提交：

`fb4f43afffdfc6ae1a9fa3dc4361f994957cc4b3`

新增/修改内容包括：

- R3 governing task；
- 30 个 AST golden edge cases；
- stage-owned prior RPS staging；
- 786-session market reference path；
- 786-session Market Regime candidate；
- native deterministic rule schema + interpreter；
- trend producer consistency verifier；
- independent postchecks；
- deterministic replay；
- R3 stage disposition。

这是实质实现更新，不是仅归档。

---

# 3. 上一轮 blocker 复验

## 3.1 B01 — AST 数值执行与 golden-vector gate

### 原始 AST numeric execution defect

**PASS**

现有 47 个 `RULE_AST_V2` 合同继续由独立数值执行器真实执行，不再只有 schema validation。

R2 原有 94 vectors 保留。

### R3 golden edge cases

**PASS_WITH_MINOR_LIMITATION**

`V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json`：

- 47 contracts
- R2 94 numeric vectors
- R3 30 named edge vectors
- total vectors = 124
- categories = 31
- failed = 0

覆盖包括：

- exact / one-short；
- suspension / resumed / T0；
- unexplained gap；
- adjustment/source mismatch；
- nonpositive / zero denominator；
- flat range；
- ranking tie / missing / n<2 / membership change / reorder；
- local UNKNOWN；
- cross-session endpoint / intermediate gap。

因此上一轮“只有 OBSERVED + 全输入清空 UNKNOWN”的主要缺口已经关闭。

### 小问题

`SOURCE_IDENTITY_DIGEST_CHANGE` 当前只是比较修改 fixture 前后的 fixture SHA，而不是直接断言某个正式 producer 的 `input_digest` 改变。

但 full-scope independent identity postcheck 已另行覆盖正式 `input_digest/window_identity`，所以不单独作为阻断。

**B01 当前整体可判 PASS。**

---

# 4. C04 — Prior RPS PIT lineage

## 4.1 Stage-owned prior artifact

**PASS**

新增：

`reports/v4_03/staging/V4_03_PRIOR_RPS_STAGING_R3.json`

坐标：

- 2026-09-23 / rps5
- 2026-09-21 / rps5
- 2026-09-21 / rps20

receipt：

`V4_03_PRIOR_RPS_STAGING_RECEIPT_R3.json`

明确：

`evidence_origin = V4_03_STAGE_OWNED_HISTORICAL_STAGING`

artifact SHA：

`90d5998ba93b60f8061c759952a0f635e4e44fb0cd12fce73331e40d95ff7041`

## 4.2 Downstream binding

**PASS**

`run_v4_03_full_scope_candidate.py --r3`：

- 先验证 prior artifact SHA；
- 验证 row output digest；
- 验证 prior universe snapshot；
- current delta 通过 `[artifact_sha, row_output_digest]` 绑定 prior identity；
- R3 receipt 将 `prior_rps_origin` 改成：
  `V4_03_STAGE_OWNED_HISTORICAL_STAGING_R3`。

原来的：

`DIAGNOSTIC_NON_PIT_RECOMPUTED_NOT_PREVIOUSLY_ACCEPTED`

不再是 R3 prior source。

## 4.3 Independent postcheck

**PASS**

`V4_03_PRIOR_RPS_INDEPENDENT_POSTCHECK_R3.json`：

- prior_artifact_mismatch_count = 0
- delta_identity_mismatch_count = 0
- value_quality_mismatch_count = 0

因此上一轮 C04 的核心 prior-RPS lineage blocker 已关闭。

---

# 5. C05 — Historical Market Reference Path

## 5.1 物化

**PASS（算法/产物层）**

`V4_03_MARKET_REFERENCE_PATH_RECEIPT_R3.json`：

- sessions = 786
- daily_returns = 785
- first_session = 2023-07-04
- last_session = 2026-09-24
- policy = PIT_UNIVERSE_AT_START_SESSION
- unknown_daily_return_count = 0
- output SHA =
  `c325e98bd101e6951c436e010c99e00a0e1910436c811c9d6c69b31c54f73613`

producer 使用每一步 `start_session` 的历史 Universe snapshot，而不是当前存活证券回填。

## 5.2 Independent postcheck

**PASS（算法层）**

- 786 rows checked
- mismatch_rows = 0
- receipt SHA match = true
- 独立重算等权日收益与 path chain。

因此原先“只有 200 session path / R3 market_path=null”的 blocker 已关闭。

## 5.3 但 metadata 尚有问题

见本报告 §9：

market path row 和 independent receipt 仍使用：

`DIAGNOSTIC_NON_PIT`

这和它实际上消费历史 PIT Universe 的事实相冲突，最终 acceptance 前必须修正。

---

# 6. Market Regime — P0 FAIL

这是当前最重要的新发现。

R3 确实生成了：

- `V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz`
- 786 rows
- independent postcheck 0 mismatch

但 producer 与 independent checker **共同实现了错误的业务公式**。

“producer 与 checker 一致”只能证明实现互相一致，不能证明符合 REV2。

## 6.1 REV2 冻结公式

REV2 §27 明确：

### breadth_axis

```text
按全市场共同成员 breadth_delta3

> 0.05  -> IMPROVING
< -0.05 -> DETERIORATING
其余    -> STABLE
```

即核心输入不是当日涨跌家数，而是：

**同一共同成员集合上的 breadth(t) - breadth(t-3)**。

### participation_axis

REV2 明确：

```text
按全市场成员 amount_ratio20 中位数

>= 1.2 -> EXPANDING
< 0.8  -> THIN
其余   -> NORMAL
```

即输入是：

**每只股票自身 amount_ratio20 的横截面 median**。

### stress_change

REV2：

```text
按同成员比率日差
```

不是简单拿两个各自 Universe 的全市场 stress ratio 做日差。

## 6.2 R3 实际实现

`scripts/run_v4_03_market_regime_native_r3.py`：

### 当前 breadth

```python
breadth = (advance - decline) / ret_evaluable
```

其中 advance / decline 是：

**当日相对前一日涨跌家数。**

这不是 `breadth_delta3`。

### 当前 participation

```python
baseline = mean(last 20 market total amounts)
participation = current_market_total_amount / baseline
```

这不是：

`median(member amount_ratio20)`。

这是两种完全不同的统计量：

- 当前实现：总市场成交额时间序列 ratio；
- REV2：证券级 amount_ratio20 的横截面中位数。

### 当前 stress_change

```python
previous_stress = previous day's stress
stress_change = stress[t] vs stress[t-1]
```

但没有按 REV2 “同成员”原则固定共同成员集合重算两端 stress ratio。

---

# 7. 为什么现有 independent postcheck 不能证明 Market Regime 正确

`independent_v4_03_market_regime_r3.py` 没有 import producer，这是好的。

但它独立复制的是同一套错误公式：

- advance/decline 当日 breadth；
- market total amount / 20-day total amount mean；
- prior-day raw stress。

所以：

```text
producer == independent checker
```

当前只能说明：

**两个程序实现了一样的算法。**

不能说明：

**该算法 == REV2 MARKET_REGIME_V1。**

因此：

```text
V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3 = implementation-consistency PASS
MARKET_REGIME contract-conformance = FAIL
```

Stage disposition 中：

`MARKET_REGIME.status = PASS_CANDIDATE`

必须撤销。

---

# 8. Native machine contract — PARTIAL FAIL

R3 新增：

`V4_03_NATIVE_DETERMINISTIC_RULE_SCHEMA_R3`

这个 amendment 的设计方向可以接受：

- 不强行把 set identity / stateful path 压进单字段 RULE_AST_V2；
- 使用独立 deterministic interpreter；
- 20 synthetic vectors；
- 不导入 production native/relative producer。

对：

- MARKET_RELATIVE_REFERENCE
- MARKET_REFERENCE_PATH
- SECTOR_FIELD_LOCAL_PRIMITIVES

这种 aggregate/stateful contract，这个方案具有合理性。

但是：

## MARKET_REGIME_V1_PRIMITIVES 仍不完整

当前 native rule：

```text
operator = MARKET_REGIME_AXES
```

输入直接是：

- breadth
- participation
- stress
- prior_stress
- limit_coverage
- index_close / ma20 / prior_ma20

它只机器验证：

**阈值映射 -> 枚举 axis**

却没有机器冻结：

- breadth 必须如何由共同成员 breadth_delta3 得到；
- participation 必须如何由 member amount_ratio20 median 得到；
- stress_change 的 same-member ratio 如何形成。

因此当前 machine contract 没有覆盖 Market Regime 的完整算法。

这是本次错误能同时通过：

`V4_03_NATIVE_CONTRACT_ACCEPTANCE_R3 = PASS`

和

`V4_03_MARKET_REGIME_NATIVE_INDEPENDENT_POSTCHECK_R3 = PASS`

的根本原因。

### 修复要求

不能只改 producer。

必须同步改 native machine contract。

建议拆成 machine primitives：

```text
MARKET_BREADTH_DELTA3_PRIMITIVE
MARKET_PARTICIPATION_AMOUNT_RATIO20_MEDIAN
MARKET_STRESS_SAME_MEMBER_CHANGE
MARKET_REGIME_AXIS_MAPPING
```

或在同一个 native deterministic schema 中明确表达以上 primitive derivation。

然后 vectors 必须覆盖：

- common-member membership change；
- t 与 t-3 新增/退出成员不污染 breadth delta；
- member amount_ratio20 横截面 median；
- amount_ratio20 部分 UNKNOWN；
- stress same-member t/t-1；
- threshold mapping。

---

# 9. PIT evidence label 仍然错误

这是 R3 中另一个不能直接签 final acceptance 的问题。

虽然实际代码已经明确消费历史 PIT Universe，但是：

## Full-scope candidate row

仍写：

```text
evidence_origin = DIAGNOSTIC_NON_PIT
```

## Market reference candidate

仍写：

```text
evidence_origin = DIAGNOSTIC_NON_PIT
```

## Market path rows

仍写：

```text
evidence_origin = DIAGNOSTIC_NON_PIT
```

## Independent reports

也仍出现：

```text
candidate lineage remains DIAGNOSTIC_NON_PIT
```

这与实际 R3 事实冲突。

REV2 明确：

`relative/RPS non-PIT 只允许 diagnostic`

因此一个最终候选不能一边声明：

`PASS_CANDIDATE / PIT historical Universe`

另一边又自标：

`NON_PIT`。

### 当前判断

这更像 metadata / governance bug，而不是计算数据错误。

但在最终 stage acceptance 前必须关闭。

应使用项目已有/新增的明确枚举，例如：

```text
V4_03_PIT_STAGING_CANDIDATE
```

或其他正式冻结名称。

重点不是具体字符串，而是必须区分：

- PIT correctness；
- stage acceptance；
- publication permission。

不能拿 `NON_PIT` 来表达“尚未正式接受”。

“未接受”与“非 PIT”是两个维度。

---

# 10. Determinism receipt — FAIL / EVIDENCE BUG

`V4_03_DETERMINISM_REPLAY_R3.json` 对四个主要 artifact：

- prior_rps
- market_path
- full_scope
- market_regime

baseline SHA 与 replay SHA 一致。

但：

`contract_vectors`

记录：

```text
baseline_sha256 =
9c4021c300e5a7ee4ba038feac7c22b788ff7c84c3af4897738542f90cef37f4

replay_sha256[0] =
5709de54150acad206cd4b93387c35358f5ebacb6563cf6a2f0b30ec03a83df0

replay_sha256[1] =
5709de54150acad206cd4b93387c35358f5ebacb6563cf6a2f0b30ec03a83df0
```

即：

**baseline != replay**

但 verifier：

`scripts/verify_v4_03_determinism_r3.py`

只判断：

```python
deterministic = digests[0] == digests[1]
```

没有要求：

```python
baseline == replay1 == replay2
```

所以当前 `status=PASS` 与 R3 task 要求：

```text
same accepted inputs + same contract + same parameter set -> same SHA
```

不完全一致。

### 修复

修改 verifier：

```text
if baseline exists:
    deterministic =
        baseline == replay1 == replay2
else:
    deterministic =
        replay1 == replay2
```

然后在当前最终代码状态重新跑一次。

如果当前 committed artifact 已是最后 replay 版本，重跑后很可能自然三者一致；但必须形成新的可审计 receipt，不能靠推测。

---

# 11. trend_axis producer identity

**PASS**

当前已统一为：

`MARKET_REGIME_TREND_WEAK_ERRATUM_V1`

scope / native registry reference / runtime 一致。

`V4_03_CONTRACT_PRODUCER_CONSISTENCY_R3.json` 无 failures。

此项不要返工。

---

# 12. Sector capability-scoped degradation

**PASS**

当前仍未生产假 sector artifact。

明确：

```text
SECTOR_NATIVE =
BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP
```

并保持：

```text
V4_08 Sector / Rotation = BLOCKED
sector-dependent stock paths = BLOCKED_OR_SHADOW_ONLY
```

这一处理符合 REV2 capability-scope 原则。

不得重新把它升级成 global V4-03 blocker。

---

# 13. R3 Task Traceability

**PASS**

此前不存在的 R2 governing task 问题已通过实际提交：

`docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md`

解决。

R3 receipts 已改为引用真实存在的 governing task。

---

# 14. Accepted Head / 越权检查

**PASS**

当前：

- `V4_STAGE_ACCEPTED_HEAD.json` 未被 V4-03 修改；
- 不存在 `V4_03_ACCEPTED_HEAD.json`；
- V4-03 final acceptance 仍为 NOT_GRANTED；
- V4-04 execution 未启动；
- V4-05 Replay Gate A 未启动；
- scanner/trading/TDX writes 均未越权。

这一点处理正确。

---

# 15. 测试证据

R3 stage disposition 报告：

```text
python -m pytest -q tests/v4_03 tests/v4_phase0/test_algorithm_contracts.py

46 passed
0 failed
```

测试源码存在，新增 R3 tests 也存在。

但 GitHub 当前：

- commit status total_count = 0
- workflow_runs = 0

所以外部审计只能记：

```text
SOURCE TESTS PRESENT = PASS
DEVELOPER REPORTED 46 PASS = EVIDENCE_PRESENT
INDEPENDENT EXTERNAL TEST EXECUTION = NOT_VERIFIABLE
```

这不是当前主要 blocker，因为已有确定的 Market Regime contract failure。

---

# 16. 当前能力裁决

| Capability | R3 自报 | 本次独立裁决 | 原因 |
|---|---|---|---|
| STOCK_CORE | PASS_CANDIDATE | **PASS_CANDIDATE** | 47-field + independent identity/value closure 保持通过 |
| RELATIVE_RPS | PASS_CANDIDATE | **PASS_CANDIDATE_WITH_METADATA_FIX_REQUIRED** | prior PIT staging 已闭环，但 candidate 仍错误标 NON_PIT |
| MARKET_REFERENCE | PASS_CANDIDATE | **PASS_CANDIDATE_WITH_METADATA_FIX_REQUIRED** | 786-session PIT path 正确方向，NON_PIT 标签需修 |
| MARKET_REGIME | PASS_CANDIDATE | **FAIL / BLOCKED** | breadth / participation / stress_change 不符合 REV2 |
| SECTOR_NATIVE | BLOCKED | **BLOCKED_CAPABILITY_SCOPED** | 缺 accepted PIT sector membership，处理正确 |

---

# 17. 必须修改的最小集合

下一轮不要重做 prior RPS、Market path、47 fields、trend producer 或 Sector decision。

只处理：

## P0-1 Market Regime contract conformance

重写 Market Regime raw primitive producer：

### breadth

严格实现：

`全市场共同成员 breadth_delta3`

不得使用单日 adv-decline ratio 替代。

### participation

严格实现：

`median(member amount_ratio20)`

不得使用 market total amount / 20d mean 替代。

### stress_change

严格实现：

`同成员比率日差`

不得直接比较两个不同 Universe 下的全市场 ratio。

trend 规则保持现状。

## P0-2 Native machine contract 同步

Machine contract 必须冻结上面三项 primitive derivation，而不是只接收预计算 `breadth/participation/stress` 后测阈值。

重新生成 native vectors + acceptance receipt。

## P1-1 Evidence origin 修正

把实际 PIT candidate 的：

`DIAGNOSTIC_NON_PIT`

改成明确 PIT + unaccepted staging 语义。

不要把“尚未 acceptance”错误表达成“NON_PIT”。

重新生成受影响 receipts / hashes。

## P1-2 Determinism verifier 修正

要求：

`baseline == replay1 == replay2`

重新生成 determinism receipt。

## P1-3 Stage disposition

Market Regime 修好前：

```text
MARKET_REGIME = BLOCKED
external_review_ready = FALSE
```

修复全部通过后再恢复：

`PASS_CANDIDATE / TRUE_WITH_CAPABILITY_SCOPE`

---

# 18. 不需要再做的内容

不要重做：

- B01 AST interpreter；
- 30 golden edge cases（除 Market Regime native primitive vectors 外）；
- C01 / C02 / C03 / C06 / C07；
- prior RPS staging；
- 786-session market reference path；
- 47-field full-scope candidate formula；
- trend producer identity；
- Sector membership fake repair；
- V4-05 full historical 47-field replay。

---

# 19. 最终状态

```text
REMOTE_HEAD = fb4f43afffdfc6ae1a9fa3dc4361f994957cc4b3

V4_03_EXTERNAL_ACCEPTANCE = BLOCKED

PRIMARY_BLOCKER =
MARKET_REGIME_CONTRACT_FORMULA_MISMATCH

SECONDARY_BLOCKERS =
PIT_EVIDENCE_ORIGIN_METADATA_INCONSISTENCY
DETERMINISM_BASELINE_NOT_ENFORCED

SECTOR_NATIVE =
BLOCKED_CAPABILITY_SCOPED
NOT_GLOBAL_BLOCKER

V4_03_FINAL_ACCEPTANCE = NOT_GRANTED
V4_04_ENTRY = BLOCKED
```

当前提交不能生成 `V4_03_ACCEPTED_HEAD`，也不能启动 V4-04。
