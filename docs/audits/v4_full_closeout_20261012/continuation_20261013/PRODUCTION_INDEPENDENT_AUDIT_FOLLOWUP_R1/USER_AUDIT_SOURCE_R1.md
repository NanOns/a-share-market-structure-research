# 大A研究系统 V4｜生产切换独立证据审计 R1

- 审计时间：2026-10-13，北京时间
- 仓库：`NanOns/a-share-market-structure-research`
- 验收分支：`codex/v4-full-closeout-20261012`
- 最终提交（HEAD）：`07d7f2fdd742013a3f278825c03a29f3637a968e`（18:15 北京时间）
- 编译冻结源码提交：`a789a9719440972c4813bdc7c27bf354b7937e1d`
- 安装包身份：`V4_PACKAGE_1.0.0_fe11c18cfdf7`；`SourceSHA=fe11c18cfdf75e9b0713b43a57139672792df8e11c5002fd67754a26af930744`
- 结论：**生产切换证据通过（限定当前带日期桌面运营研究范围）；V4 无条件全产品验收不通过；真实后续自动日更仍待观察。**

## 1. 身份与编译一致性

GitHub 分支 HEAD 及 2026-10-13 提交可读取；从冻结源码提交到最终 HEAD 的差异只有两个文档/审计证据提交，共 68 个 `docs/` 文件，没有后于安装包冻结源码的生产代码、配置或测试变更。因而“安装包源提交早于最终 HEAD”本身不构成旧包问题。

GitHub 默认分支 `main` 仍指向 `414b78c2995687dd8ee13e465711e1e5c2c10038`（2026-09-07）；本轮成果在指定 V4 分支中，不能以默认 `main` 代替当前生产验收源。

## 2. 验收矩阵

| 项目 | 证据层结论 | 核查情况 |
|---|---|---|
| 原 Windows 端口 28765 切换 | **PASS（提交证据）** | EXE 新包；PID `16516→34828` 的真实重启记录；生产工作空间 `G:\codex work\v4-production-20261012` |
| 发布/运行版本一致 | **PASS（提交证据）** | 完整编译 manifest、SourceSHA、workspace、Head/token 关联；原用户工作空间 Head 哈希保留 |
| PostgreSQL 现役消费链 | **PASS_CURRENT_SCOPE（提交证据）** | `market_research`，cluster `7688198230782699460`；独立 SELECT-only reader；131 条 PG 对象/主键/内容版本索引记录。不能由此推断所有历史兼容代码不存在。 |
| 生产业务 HTTP | **PASS（提交证据）** | 七条 GET：context、home、stocks、sectors、focus、market、diagnostics 均 200，T0/token 一致；5224 个股、400 板块、3025 Focus episodes；与冻结 staging 逐字段/值守恒 |
| 前端真实入口 | **PASS_CURRENT_UI_SCOPE（提交证据）** | 原端口浏览器十项检查，包括六入口、别名搜索、来源抽屉、历史日期跨页、历史对照；截图与 AX 导出随提交保存 |
| 合法范围最终回归 | **PASS_WITH_DECLARED_SKIPS（提交证据）** | 7288 节点：7225 PASS / 63 有理由 SKIP / 0 FAIL / 0 ERROR；native 4753+40，historical 2472+23；无源码漂移。63 跳过不是 63 通过。 |
| 原 56 项消费追踪 | **PASS_CURRENT_REACHABILITY_SCOPE（提交证据）** | 20 ACTIVE_REACHABLE、1 HISTORICAL_ONLY、35 NOT_REACHABLE_WITH_PROOF、0 未分类；活动链映射 PG 与字段、HTTP |
| Core47/Field 与 Focus 数值 | **PASS_CURRENT_SCOPED（复用带身份的独立证据）** | Core47 245528 次类型校验零错误；Focus 80034 次数值比对；原始字段投影曾有 10448 个差异，已分类并对相应 15672 项做针对性核验，不能把原始差异说成从未发生。 |
| 2026-10-12 当前发布 | **PASS_CURRENT_RECONSTRUCTED_SCOPE（提交证据）** | Snapshot/Joint/Operational Head 同业务 token，T0=2026-10-12；不构成历史首次可用/PIT 证明 |
| 自动日更新一日正式完成 | **NOT_YET_VERIFIED** | 截至已提交的 18:12 验收记录，自动日更已开启，但 2026-10-13 待 18:35 首次检查，BaoStock factor 未 ready，无新日 Head 发布；历史 job 留有 `SOURCE_EXECUTION_FileNotFoundError` 失败记录 |
| 通达信/BaoStock 金额完全一致 | **NOT_PASS_PROVIDER_PARITY** | 原生 TDX 口径守恒；BaoStock 有 136 个不同 float32、12 条没有对应原生 bar，已分类保留，没有放宽容差强判两源相同。当前生产使用有明确来源口径，可独立不阻断。 |
| 无条件全产品/预测/交易授权 | **NOT_GRANTED** | `full_product_release=false`、`PIT_ELIGIBLE=false`、`AS_RECORDED=false`，真实未来样本、Forward/OOS、模型权威/交易用途未获准 |
| 39 项最终机器明细 | **EVIDENCE_RECONCILIATION_PENDING** | Stage6 文字汇总称 33 当前 PASS、3 HISTORICAL_ONLY、3 FUTURE_DATA_WATCH；GitHub 尚能读到的 `AUDIT_MATRIX_R3/MATRIX.csv` 仍保留 10 项 `FIXED_NEEDS_FINAL_RUN`。需要一张最终 R4 每项证据绑定/状态表。 |
| G 盘唯一最终 ZIP | **NOT_VERIFIED** | Stage6 下一步仍写生成 G 盘最终交付目录/ZIP、校验 manifest/CRC；无可独立读取的已完成最终 ZIP 回执。此项是交付归档未完成，不反向否定 28765 切换事实。 |
| 性能、正式回滚、移动端 | **USER_DEFERRED（非本轮阻断）** | 2026-10-12 用户书面修订明确推迟这些项目，报告不得虚称通过 |

## 3. 关键保留：页面数据能力不同于页面可打开

在生产首页 AX 证据中，研究雷达、Forward 样本显示“来源未接入”；在板块研究中，成熟度与健康度筛选显示来源未接入。此处记录的是带能力声明的真实显示，并非编造 UNKNOWN 或 HTTP 无响应，但不能把“六入口可以运行”翻译成“所有设计字段均有生产数据”。历史板块成员依据 2026-10-09 通达信最新成员重建，不是每个历史交易日真实存档的成员，存在幸存者偏差风险；界面已显示这些限制。

## 4. 后续最小操作（不要求重复六阶段工程）

1. 重点验收 2026-10-13 18:35 之后首次 **新 EXE 的真实调度**：Windows task 实际触发、BaoStock factor 是否 ready、受限 PostgreSQL worker 执行；若 source unavailable，正确行为是 WAIT、保留 10-12 last-good Head，不能发布假 T0；若源已 ready，需要完成原子发布、日期/token/七路 API 同版读回。保留成功及失败原始证据，不把历史失败误判为本轮新失败。
2. 从最终完整回归、原端口桌面重启收据，把 39 项矩阵的 10 条 `FIXED_NEEDS_FINAL_RUN` 逐项更新为明确最终结论与 SHA；不必重复已经冻结的大数值运行。
3. 生成 `G:\codex_tmp\V4_R4_R3_FINAL_DELIVERY\V4_FULL_CLOSEOUT_FINAL_20261013\V4_FULL_CLOSEOUT_FINAL_20261013.zip`（或按最新合同指定的同一唯一正式目录），将最终状态、39 项明细、合法全量 XML、数值/PG/56 项目录、真实日更记录及 SHA256 清单打包，再读回验 CRC/清单一致。不得因未来交易日客观样本未成熟否定已完成的桌面切换。
4. 如后续要求生产预测/严格历史回测或交易用途，必须另行补首次可用/PIT、观察集、Forward/OOS、模型授权等领域验收；不能自行把当前 `full_product_release=false` 改成 `true`。

## 5. 审计局限

本轮独立读取并交叉检查 **GitHub 提交中的源码、验收程序输出、机器记录、HTTP/BFF/AX 凭证与治理约束**，没有远程接入用户 Windows 本机进程、实际 PostgreSQL 或 G 盘目录，因此是“提交证据独立审计”，不是在用户电脑上重新执行 7288 项测试、访问 localhost 或现场确认 ZIP。鉴于运行记录和冻结身份较为完整，生产切换本身有充分证据支持，但后续真实日更必须用新的生产收据继续核对。

## 6. 核验出处

- [最终 GitHub 提交](https://github.com/NanOns/a-share-market-structure-research/commit/07d7f2fdd742013a3f278825c03a29f3637a968e)
- [生产最终验收 JSON](https://github.com/NanOns/a-share-market-structure-research/blob/07d7f2fdd742013a3f278825c03a29f3637a968e/docs/audits/v4_full_closeout_20261012/continuation_20261013/WINDOWS_PRODUCTION_CUTOVER_R4/FINAL_ACCEPTANCE_R4.json)
- [阶段六收尾](https://github.com/NanOns/a-share-market-structure-research/blob/07d7f2fdd742013a3f278825c03a29f3637a968e/docs/audits/v4_full_closeout_20261012/continuation_20261013/WINDOWS_PRODUCTION_CUTOVER_R4/STAGE6_ACCEPTANCE.md)
- [最终回归 7288 项](https://github.com/NanOns/a-share-market-structure-research/blob/07d7f2fdd742013a3f278825c03a29f3637a968e/docs/audits/v4_full_closeout_20261012/continuation_20261013/STAGE5_FINAL_REGRESSION_R4.md)
- [当前 PG 消费链](https://github.com/NanOns/a-share-market-structure-research/blob/07d7f2fdd742013a3f278825c03a29f3637a968e/docs/audits/v4_full_closeout_20261012/continuation_20261013/STAGE3_PG_CONSUMER_CLOSEOUT_R1.md)
- [39 项旧明细矩阵](https://github.com/NanOns/a-share-market-structure-research/blob/07d7f2fdd742013a3f278825c03a29f3637a968e/docs/audits/v4_full_closeout_20261012/continuation_20261013/AUDIT_MATRIX_R3/MATRIX.csv)
- [新包日更重启观测](https://github.com/NanOns/a-share-market-structure-research/blob/07d7f2fdd742013a3f278825c03a29f3637a968e/docs/audits/v4_full_closeout_20261012/continuation_20261013/WINDOWS_PRODUCTION_CUTOVER_R4/POST_RESTART_DAILY_R4.json)
- [金额跨源边界](https://github.com/NanOns/a-share-market-structure-research/blob/07d7f2fdd742013a3f278825c03a29f3637a968e/docs/audits/v4_full_closeout_20261012/continuation_20261013/AMOUNT_A_SOURCE_AUDIT_R2/RESULT.json)
