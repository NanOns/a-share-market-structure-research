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
| FR8-EA4-01 | PARTIAL | 发布入口已改为 PG pending 行提交后再做同 token 读回，事务文件最终落盘后追加 PG 事件；独立 G4 查询真实数据库身份、行、行 SHA、事件、事务文件及 Head SHA。真实 PG 上旧 `c40…` 回执被 `FAIL_CLOSED` 拒绝。未做新候选正向发布。 |
| FR8-EA4-02 | PARTIAL | 新增重启恢复入口，检查 CAS/PG 状态，追加 `FINALIZED/ABORTED` 或恢复 predecessor；发布前自动恢复。任务卡要求的四类真实故障注入未完成。 |
| FR8-EA4-03 | PARTIAL | 向 `v4_r8pub_fde08c597fc76d13.r8_publication_events` 追加 `CORRECTION_NO_PRODUCTION_ACCEPTANCE`，绑定旧错误行 SHA `471210c9…b3`。两条历史 ledger 行保留，未 UPDATE/DELETE。所有 28766 消费入口旧行拒绝矩阵未完成。 |
| FR8-EA4-04 | OPEN | G1/G2 仍依赖调用方给出的 `business_values` 与 identity 文件绑定；独立 accepted predecessor Head、全影响域 PG/Owner 数值、状态和历史闭包尚未核验。 |
| FR8-EA4-05 | OPEN | D0 正式场景尚无基于真实 PG Owner/Publication 的来源时钟、权限和 cutoff seal。10/15 历史可得时间待核原始 source ledger；不倒填。 |
| FR8-EA4-06 | OPEN | 未补齐同系列市场参考至 10/15+，没有真实 PG 权限链或独立 Close/MA20/MA20(-5) 重算。趋势来源不升级为已封存。 |
| FR8-EA4-07 | OPEN | 未完整执行 10/16、10/19 的 SourceIngress→Owner→PG→G1–G4→Priority→28766 顺序日更；对象分母、性能样本、幂等增量证明缺失。 |
| FR8-EA4-08 | PARTIAL | 两处 Python 源通过 `py_compile`；`tests/test_v4_functional_r8_third_batch.py` 6 项通过；`git diff --check` 通过。故障矩阵、前端用户动作矩阵与远端 CI 证据未完成。 |

## 已冻结的真实状态

- PG 只读身份：`market_research`，OID `646711`，`127.0.0.1:5432`，PostgreSQL `180006`；只读核实事务 `transaction_read_only=on`。
- R8 schema：`v4_r8pub_fde08c597fc76d13`。执行前 ledger 两行；纠错后仍两行，纠错事件一行。
- 错误旧 token：`c40e07216d40d28dd2be20c0b2d2bbe59c5006b0405649e26ea8e3f4f586a47c`。旧行中的 `production_accepted=true` 和 `USER_AUTHORIZED_OPERATIONAL_DAILY` 原样保留，只追加纠错事件。
- 仓库 `V4_OPERATIONAL_RESEARCH_HEAD.json` SHA-256：`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；`V4_DATA_ACCEPTED_HEAD.json` SHA-256：`38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`。正式 accepted predecessor 仍为 10/09，未切换。
- 端口：5432 PG 监听；28766 既有服务监听；28765 未监听。本轮未对 28766 做同版 HTTP 读回。
- 代码修改：`src/workbench_db/v4_r8_publication_bridge_v1.py`、`src/workbench_analysis/r8_candidate_append_comparator.py`。

## 阶段结果与下一步

本批为 `PARTIAL / INDEPENDENT_ACCEPTANCE_OPEN / PRODUCTION_SWITCH_NOT_AUTHORIZED`。先补真实 PG 四类故障注入、恢复和幂等验证；再完成旧凭据所有消费入口负例及 G1/G2 独立 PG/Owner 范围；之后按顺序推进 10/16、10/19、10/20、10/21 并以真实时钟分类来源。D0/市场来源没有足够事实时保持 `OPEN`。正式消费 Head、生产调度、28765 与最终运行包未触碰。