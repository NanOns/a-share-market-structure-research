# R8 第五批执行报告（2026-10-21）

## 阶段合同与范围

- 任务：`R8_BATCH05_PUBLICATION_REPAIR_AND_CONTINUOUS_INCREMENT`，依据 Drive 文档 `V4_R8_FOURTH_BATCH_EXTERNAL_AUDIT_AND_BATCH05_TASK_R1_20261021.md`。
- 最新适用技术升级合同：`docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`（R1）。开发数据库权限按用户给出的 2026-10-18 SOT R2 执行。
- 分支/起始基线：`codex/v4-unified-development` / `ab255ac6ec62b486bc9c7d66f102a5256d448ec5`。
- 阶段 0：沿用 `docs/V4_PHASE0_FINAL_ACCEPTANCE_R3_1_20260925.md` 的 `DEGRADED_PASS`。本批没有启动扫描器，也未改变阶段资格。
- 范围：开发候选发布桥、比较器、开发 PG 纠错和本批报告。28766 既有进程未启动/停止/重启；28765 未监听。
- 数据分类：保留 10/15 候选、源与历史证据。本轮没有声称 10/16、10/19 日更完成，也没有把 10/21 晚捕数据标作 PIT。

## 执行结论

| ID | 状态 | 证据与限制 |
|---|---|---|
| FR8-EA4-01 | PARTIAL | 发布入口已改为 PG pending 行提交后再做同 token 读回，事务文件最终落盘后追加 PG 事件。G4 正向真实 PG fixture 得到 `G4=PASS`；旧 `c40…` 行负例为 `FAIL_CLOSED`。正向 fixture 的整体 G1–G3 不在该夹具范围内，且尚无完整真实 `publish_candidate` 正向发布，故不报整体 PASS。 |
| FR8-EA4-02 | PARTIAL | 两个真实 PG 故障窗口通过隔离候选夹具验证：PG commit 后文件未最终确认时追加 `ABORTED` 并精确恢复 last-good；COMMITTED 文件落盘而最终 PG 事件缺失时追加 `FINALIZED`，重复恢复不重复追加。测试 schema 已精确清理。其它真实服务/28766故障窗口及完整业务候选未验收。 |
| FR8-EA4-03 | PARTIAL | 向 `v4_r8pub_fde08c597fc76d13.r8_publication_events` 追加 `CORRECTION_NO_PRODUCTION_ACCEPTANCE`，绑定旧错误行 SHA `471210c9…b3`。两条历史 ledger 行保留，未 UPDATE/DELETE。所有 28766 消费入口旧行拒绝矩阵未完成。 |
| FR8-EA4-04 | OPEN | G1/G2 仍依赖调用方给出的 `business_values` 与 identity 文件绑定；独立 accepted predecessor Head、全影响域 PG/Owner 数值、状态和历史闭包尚未核验。 |
| FR8-EA4-05 | OPEN | D0 正式场景尚无基于真实 PG Owner/Publication 的来源时钟、权限和 cutoff seal。10/15 历史可得时间待核原始 source ledger；不倒填。 |
| FR8-EA4-06 | OPEN | 未补齐同系列市场参考至 10/15+，没有真实 PG 权限链或独立 Close/MA20/MA20(-5) 重算。趋势来源不升级为已封存。 |
| FR8-EA4-07 | PARTIAL | 已按 10/16、10/19 顺序用现役 SourceAdapter 捕获真实 TDX/BaoStock 冻结，均为 `SOURCE_READY`、`AS_RECORDED=false`、`PIT_ELIGIBLE=false`。10/16 Owner 重算两次因 `BAOSTOCK_LOGIN_FAILED` 停在准备阶段；10/19 Owner 未运行。现有 PG SourceIngress 两日全字段读回为 5,567 / 5,564 行，但行早已存在且未插新收据。Owner→G1–G4→Priority→28766 顺序日更、性能及幂等证明仍未完成。 |
| FR8-EA4-08 | PARTIAL | 两处 Python 源通过 `py_compile`；`tests/test_v4_functional_r8_third_batch.py` 6 项通过；`git diff --check` 通过。故障矩阵、前端用户动作矩阵与远端 CI 证据未完成。 |

## 已冻结的真实状态

- PG 只读身份：`market_research`，OID `646711`，`127.0.0.1:5432`，PostgreSQL `180006`；只读核实事务 `transaction_read_only=on`。
- R8 schema：`v4_r8pub_fde08c597fc76d13`。执行前 ledger 两行；纠错后仍两行，纠错事件一行。两个故障测试 schema 与一个 G4 fixture schema 均由本轮创建，完成后通过限定 DROP TABLE/FUNCTION + `DROP SCHEMA ... RESTRICT` 清理并核验消失。
- 错误旧 token：`c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47c`。旧行中的 `production_accepted=true` 和 `USER_AUTHORIZED_OPERATIONAL_DAILY` 原样保留，只追加纠错事件。
- 仓库 `V4_OPERATIONAL_RESEARCH_HEAD.json` SHA-256：`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；`V4_DATA_ACCEPTED_HEAD.json` SHA-256：`38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`。正式 accepted predecessor 仍为 10/09，未切换。
- SourceIngress 现存读回：schema `v4_r8_batch04_source_ingress`，读前/读后均 5 receipts / 27,832 bars；10/16 为 5,567 行，10/19 为 5,564 行，逐字段相等，来源 SHA `0404bbaeb985b2409a99dfcfe2c67b00e5dd574378105c408486183e9e058ede`。回执保存在 `G:/codex_tmp/r8_batch05/PG_SOURCE_INGRESS_20261016_19.json`，SHA-256 `9f4869eb870eaa495b0ba7a729655b8bfd2c0fef587452e784495bca97f026b2`。两个交易日均是 10/21 09:35 UTC 才可得的重建数据，故不作为 PIT 或当时首捕证明。
- 代码修改：`src/workbench_db/v4_r8_publication_bridge_v1.py`、`src/workbench_analysis/r8_candidate_append_comparator.py`、`scripts/r8_batch04_ingest_tdx_source.py`。源码提交：`6bbb409894a6cd540e13a59f5eb854c9ea84e389`、`8163f7a7a37980a0d7f36eabd80cbc2496cbf7c2`、`3fc659ba491f779ae5d1766961a2d7790aa3841d`。

## 阶段结果与下一步

本批为 `PARTIAL / INDEPENDENT_ACCEPTANCE_OPEN / PRODUCTION_SWITCH_NOT_AUTHORIZED`。Compact PG fault recovery、G4 正/负 fixture 与 SourceAdapter 捕获/Owner 失败记录位于 `FIFTH_BATCH_ARTIFACTS/`，对应 SHA 与边界见 `FIFTH_BATCH_EVIDENCE.json`。先解决 BaoStock 登录/日期 universe 准备失败，顺序完成 10/16、10/19 Owner 与开发 Head，再续 10/20、10/21；重跑真实业务候选的完整 PG/Head/G1–G4/28766 读回。补齐其余 PG 故障窗口、旧凭据所有消费入口负例及 G1/G2 独立 PG/Owner 范围。D0/市场按真实来源时钟验收。D0/市场来源没有足够事实时保持 `OPEN`。正式消费 Head、生产调度、28765 与最终运行包未触碰。
## Git 交付

- 源码提交：`6bbb409894a6cd540e13a59f5eb854c9ea84e389`、`8163f7a7a37980a0d7f36eabd80cbc2496cbf7c2`、`3fc659ba491f779ae5d1766961a2d7790aa3841d`。
- 报告与证据随后一提交一并推送；推送不代表独立验收或下一门禁通过。
