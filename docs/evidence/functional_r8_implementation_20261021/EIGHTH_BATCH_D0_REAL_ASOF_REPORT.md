# R8 第八批｜D0 正向 as-of 与真实增量修复报告

- **终态：`D0_PARTIAL`**。EA7-01 至 EA7-04 的源码/精确绑定/派生时钟/闭包幂等与真实 PG 负向封存已通过；EA7-05 连续真实交易日候选 Owner、R8 Publication 与 28766 同 token 增量未完成。没有用模拟正向数据替代真实来源证据。
- **基线：**`codex/v4-unified-development`，`df486e0017c78fb9e8bd8ed2f28a57959b022b67`。实现提交：`9788727ae`（已推送）。
- **适用计划：**`docs/plans/V4_FUNCTIONAL_R8_REPAIR_PLAN_R2_FINAL_20261021.md`；Phase 0 继承 `DEGRADED_PASS`，`scanner_permission=NOT_APPLICABLE_UNTIL_V4_05`，本批没有启动通用扫描阶段。
- **候选：**10/15 合法 successor token `c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47c`。历史 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`historical_PIT_permission=false` 保持不变。

## EA7 验收

| 条目 | 结果 | 证据与边界 |
|---|---|---|
| EA7-01 合法现役候选的 Dev as-of 与历史 PIT 合同冲突 | `CODE_PASS` | `DEV_ASOF_SOURCE_VERIFIED` 独立于历史 PIT / 正式准入；候选仍经 `OperationalSuccessorV1.validate`。拒绝错误 PIT 标记、晚时钟、错误身份。当前真实 10/15 输入被正确保留为 NON_PIT；本批没有真实同日输入，因此没有宣称正向 PG seal。 |
| EA7-02 SourceIngress 精确候选来源身份 | `REAL_PG_PASS` | publisher 按候选 `source_registry[trade_date].freeze`、R8 精确 `source_freeze_sha256`、包 SHA 与唯一 SourceIngress receipt 联结；对零/多匹配和字节不符 fail-closed。10/15 精确 receipt 一条、artifact bytes/SHA 重算通过；针对同日不同版本/重复 receipt 有回归覆盖。 |
| EA7-03 来源 cutoff 与 D0 派生时间分离 | `REAL_PG_PASS` | PG r15 读回完整五时钟，严格分开来源 snapshot cutoff 与后算/后发布 D0。派生 Owner/代码/参数不被回填成 cutoff 时已可用。 |
| EA7-04 全闭包幂等与独立数值核验 | `REAL_PG_PASS` | input/full closure fingerprints 重建一致；事实 10,452 行 digest PASS；重复执行回 `ALREADY_PUBLISHED`，仍是 r15。5 个真实证券样本由 SourceIngress 原始 OHLCV、raw Owner、TDX affine QFQ 和独立相邻日收益公式交叉核验，5/5 通过。 |
| EA7-05 10/16 及后续真实交易日增量 | `PARTIAL` | 已有真实来源字节，但来源捕获晚于目标交易日，且 PG 中 10/16–10/22 无 R8 candidate publication；没有这些日期的 exact candidate Owner/Publication/28766 token 可继续接链。不得把 10/15 token 或晚捕来源改标正向。 |

## 真实 PG 结果

数据库 `market_research`，`127.0.0.1:5432`（OID `646711`，PostgreSQL `18.6`）。独立读回以 `SET TRANSACTION READ ONLY` 和 `SET ROLE v4_r8_d0_seal_reader_r1` 执行；`session_user=postgres`、`current_user=v4_r8_d0_seal_reader_r1`，受限读事务为只读，所需 SELECT 权限全部通过。

最终同 token D0 publication：`D0B07:2026-10-15:c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47c:r15`，contract `V4_D0_SOURCE_SEAL_SUCCESSOR_R2` v2.1.0，状态 `DEV_RECONSTRUCTED_NON_PIT`；`dev_asof_source_verified=false`、`AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`production_admission=false`。Owner 为 5,226 行、2,892,297 bytes、SHA-256 `570f68d3cc90cb68ef6a1102d91d535795ea46920c4ded2a9c6f6b23b574fb99`。两正式场景 facts 共 10,452 行，digest PASS。

10/15 exact R8 cutoff 为 `2026-10-21T20:07:27.040317+08:00`。精确 SourceIngress artifact SHA-256 `6ad6620a5e0fdc0128976d8c1f58d77c68626dc59e44ea2a8fcb685c78e2c4c8`，2,179,581 bytes，5,565 bars，package date 10/21，available `2026-10-21T17:35:26+08:00`，time role `RECONSTRUCTED_FROM_LATER_PACKAGE`，class `RECONSTRUCTED_NON_PIT`。所以虽然它在 R8 replay snapshot cutoff 前到达，仍不能证明其 10/15 历史首捕。

五个 D0 时钟（Asia/Shanghai）：

- `source_snapshot_cutoff_at`: `2026-10-21T20:07:27.040317+08:00`
- `code_parameters_frozen_at`: `2026-10-22T03:22:14.045325+08:00`
- `d0_computed_at`: `2026-10-22T03:22:14.349618+08:00`
- `d0_published_at`: `2026-10-22T03:22:14.702443+08:00`
- `d0_usable_at`: `2026-10-22T03:22:14.702443+08:00`

两项 closure fingerprints：input `fb6ae0320b3d20a5cdf4105b695f75e92303b2dcbafe4f6b5c7c5eb4c530f2e7`；full `0019e80eb8bc03c10589169839d2b9e231e6c57fcb69236a516a650469597110`。相同输入第二次 runner 调用回 `ALREADY_PUBLISHED`，Publication 仍为 r15。批内 r10–r15 为实现期间生产者/读回源码 SHA 每次变化产生的 append-only 修订；均为开发 NON_PIT、无历史/正式准入，全部保留。未删除旧 r1–r9 或第七批证据。

原始 D0 三态仍为 **FALSE 5,111 / TRUE 64 / UNKNOWN 51**。LAUNCH_CONFIRM 为 5,127 / 48 / 51；RECOVERY_TURN 为 5,153 / 22 / 51。28766 独立读回仍把全部 10,452 Seal 计为 `POST_HOC_NON_PIT`，谓词没有被封存路径改写。

## 真实来源和日增量盘点

PG SourceIngress 对象的原始字节与全部栏值 readback PASS：

| 交易日 | PG SourceIngress 行数 | 包日期 / 时间角色 | R8 candidate publication | D0 candidate publication |
|---|---:|---|---:|---:|
| 10/15 | 5,565 | 10/21，`RECONSTRUCTED_FROM_LATER_PACKAGE` | 2 个 token（一个现役） | 15 个 append-only closure revision，最高 r15 |
| 10/16 | 5,567 | 10/21，`RECONSTRUCTED_FROM_LATER_PACKAGE` | 0 | 0 |
| 10/19 | 5,564 | 10/21，`RECONSTRUCTED_FROM_LATER_PACKAGE` | 0 | 0 |
| 10/20 | 5,568 | 10/21，`RECONSTRUCTED_FROM_LATER_PACKAGE` | 0 | 0 |
| 10/21 | 5,568 | 10/21，`POST_CLOSE_LATE_CAPTURE` | 0 | 0 |
| 10/22 | 0 | 检查时尚未收盘，无新交易日包 | 0 | 0 |

10/16 另有可核验的真实 TDX 官方包（10/18 下载，549,184,442 bytes，SHA `c0ea0dffad66e06351596fb3855ffde0d80536e3d962867a09f42ddf32448219`，目标 bar 5,567 行）；BaoStock 真实公开匿名响应为 5,226 日行情行和 48 因子行，10/18 观察。它们是晚采真实源，不能满足 10/16 同日 as-of；数据库也没有相应 R8 frozen candidate token。10/19–10/21 当前仅有 10/21 包回建/收盘后来源 receipt，没有连续候选 Owners/Publication。故没有假造交易日增量或正向样本，EA7-05 留为待真实捕获时钟与合法候选链。

## 28766 真实接口

开发服务重启后在 `127.0.0.1:28766`（PID `2968`）运行，只读候选预览，同 token / 10/15：`/api/operations/status` HTTP 200；`/api/v4/context` HTTP 200，状态 READY，计数 focus 404 / stocks 5,226 / sectors 400，3 个开放域 gap；带 `context_token` 的 `/api/v4/focus` HTTP 200，404 总数、首屏 30 行，D0 reader contract v2.1.0、PG binding present、cutoff resolved、`POST_HOC_NON_PIT`。Focus write=false、production_accepted=false、formal_head_modified=false。28765 无监听；PostgreSQL 仍在 5432。

## 代码、验证和边界

实现与精确输入/PG readback、版本时钟链写入配置、迁移、发布 runner 和回归测试一同提交；`python -m py_compile` 通过；定点测试 **20 passed**；`git diff --check` 通过。远程 CI 未运行、未宣称外部审计接受。推送不是生产验收。

本批没有 28765 切换、正式消费 Head 更新、生产调度或最终打包。下一步等待正常日收盘后产生真实 TDX/来源时钟与 exact SourceIngress 的 successor candidate，按 10/16→10/19→10/20→10/21 顺序补全真实 Owner / R8 PG / D0 PG / 28766 同 token 链，再由独立审计验收。

机器证据：`EIGHTH_BATCH_D0_REAL_ASOF_EVIDENCE.json`。
