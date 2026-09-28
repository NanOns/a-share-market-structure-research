# V4-03 Final Seal 与 V4-04 Stock Core 入场任务卡

- 日期：2026-09-28
- 分支：`codex/v4-system-reform`
- 外部验收基线：`e19bd4f376d9e47ae14610ad5c93247f3513c4bd`
- 外部结论：`PASS_WITH_CAPABILITY_SCOPE`
- 目标：只做 V4-03 最终封板和 V4-04 Stock Core 入场授权，不再继续开发 V4-03 算法。

## 1. 冻结结论

```text
STOCK_CORE = PASS
RELATIVE_RPS = PASS
MARKET_REFERENCE = PASS
MARKET_REGIME = PASS
SECTOR_NATIVE = BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP
V4_03 = PASS_WITH_SECTOR_SCOPE_DEGRADED
INCREMENTAL_UPDATE = DEFERRED_NON_BLOCKING
```

不得因为增量更新未实现而继续阻断 V4-03/V4-04。

## 2. Final Seal 禁止事项

禁止：

- 修改 47 个因子公式；
- 修改 Market Regime 算法；
- 修改 prior RPS 算法；
- 重建 AST framework；
- 修改 Market path 公式；
- 伪造 Sector membership；
- 实现 V4-05 full replay；
- 实现增量更新；
- 启动 V4-04 实际业务计算；
- 启动 scanner/trading/Focus；
- 修改 V4-01/V4-02 accepted artifacts。

本任务是治理封板，不是新开发。

## 3. 外部验收归档

把外部报告提交为类似：

`docs/evidence/V4_03_EXTERNAL_ACCEPTANCE_PASS_20260928.md`

必须记录：

```text
EXTERNAL_ACCEPTANCE_PASS_WITH_CAPABILITY_SCOPE
accepted_candidate_commit = e19bd4f376d9e47ae14610ad5c93247f3513c4bd
```

纯治理 commit 不得替代算法 candidate commit。

## 4. Final Stage Receipt

新增：

`reports/v4_03/V4_03_FINAL_STAGE_RECEIPT_R1_20260928.json`

至少包含：

- stage = V4-03
- status = PASS_WITH_SECTOR_SCOPE_DEGRADED
- external_acceptance = PASS_WITH_CAPABILITY_SCOPE
- accepted_candidate_commit = `e19bd4f...`
- source_cutoff = 2026-09-24
- STOCK_CORE / RELATIVE_RPS / MARKET_REFERENCE / MARKET_REGIME = PASS
- SECTOR_NATIVE = BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP
- deferred_non_blocking = INCREMENTAL_UPDATE
- authorized_successor = V4_04_STOCK_CORE
- blocked_successor = V4_08_SECTOR
- contract/source/artifact/evidence hashes
- scanner/trading/TDX writes = 0

## 5. V4_03_ACCEPTED_HEAD

新增：

`data/v4/V4_03_ACCEPTED_HEAD.json`

冻结：

- final receipt path + SHA；
- accepted candidate commit；
- capability statuses；
- source cutoff；
- V4-01/V4-02 upstream identities；
- V4-04 Stock Core authorization；
- V4-08 Sector block；
- incremental update deferred/non-blocking。

不得把 Sector 写成 PASS。

## 6. 更新全局 Accepted Head

更新：

`data/v4/V4_STAGE_ACCEPTED_HEAD.json`

只增加 V4-03 binding/status：

```text
V4_03_STATUS = PASS_WITH_SECTOR_SCOPE_DEGRADED
V4_04_STOCK_CORE_ENTRY = AUTHORIZED
V4_08_SECTOR_ENTRY = BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP
```

不得改变 V4-01/V4-02 identity 或 source cutoff。

## 7. Final Seal Validator

新增轻量 validator，只检查治理链：

1. receipt 引用文件存在；
2. SHA 与实际文件一致；
3. accepted candidate commit 精确为 `e19bd4f...`；
4. accepted head -> receipt SHA 一致；
5. global head -> V4_03 head SHA 一致；
6. Sector 仍 BLOCKED；
7. V4-04 Stock Core authorized；
8. V4-08 Sector blocked；
9. scanner/trading/TDX writes = 0；
10. 不存在 V4-04 业务 artifact。

这不是再次全量跑 47 字段。

## 8. 运行要求

只跑 Final Seal validator 和必要 smoke tests。

**不要再次全量重算 786 日 + 5222×47，除非 seal validator 发现当前 committed receipt SHA 与文件不一致。**

## 9. 提交

建议 commit：

`[V4-03] Seal scoped external acceptance and authorize V4-04 stock core`

提交后提供：

- final seal commit SHA；
- git status；
- final stage receipt；
- `V4_03_ACCEPTED_HEAD.json`；
- 更新后的 `V4_STAGE_ACCEPTED_HEAD.json`；
- validator result。

## 10. 完成状态

```text
V4_03 = CLOSED
V4_03_STATUS = PASS_WITH_SECTOR_SCOPE_DEGRADED
V4_04_STOCK_CORE_ENTRY = AUTHORIZED
V4_08_SECTOR_ENTRY = BLOCKED
INCREMENTAL_UPDATE = DEFERRED_NON_BLOCKING
```

随后立即进入 `V4-04 Full-Market Core Profile`，不要继续在 V4-03 内扩展功能。
