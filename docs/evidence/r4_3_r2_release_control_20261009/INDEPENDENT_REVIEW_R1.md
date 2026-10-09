# 大A V4｜R4.3 R1 独立复审与未切换根因（2026-10-09）

## 0. 审计基线与唯一结论

- 仓库 `NanOns/a-share-market-structure-research`，分支 `codex/v4-fp14-r2-repair`，HEAD `4e344156564338cda185fd44505c1273cf8bfdca`；实际工程代码/证据主提交 `47a9c76797a1e80666976a188e9ddf19d9647d6a`，补充元数据提交 `4e344156...`。
- 对照 Driver R4.3 及 R4.3 R1 定点修复任务卡；用户目标为四交易日（2026-09-28、09-29、09-30、10-08）全面完成合法研究计算、10/08 上线，之后执行 FP01–FP14 前端缺陷验收。
- **唯一生产验收状态：`EXTERNAL_ACCEPTANCE_BLOCKED`；但 R4.3 R1 工程修复 `PASS_ENGINEERING_SCOPED`。** 当前生产仍停 `2026-09-30`，不是“10/08 已发布”。
- **最直接因果链**：最终候选 `9c42365c777df3facf13b31639102f11c4e8321536de33af965213f71e04c55e` → `SCOPED_ADMISSION_REQUEST_V2.json` `external_acceptance_granted=false` / `reviewer=null` / `signature=null` → `data/v4/R43_OPERATIONAL_EXTERNAL_ACCEPTANCE.json` 不存在 → 新 `data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json` 未创建 → `cas(...,staging=False)` 未执行 → `/api/v4/context` 回退读取旧 9/30 Head。
- 本次外审未直接触达用户 Windows 正式部署实例，线上事实依据为仓库封存真实 HTTP 收据及生产 Head 缺失；不伪称本审查者亲自操作了生产 CAS。

## 1. 逐项结果

| 事项 | 判定 | 复核依据与边界 |
|---|---|---|
| Git 修复真实推送 | PASS | HEAD `4e344156...`；R1 源修 `ad488763...`、工程主提交 `47a9c767...`；代码与证据可在 GitHub 按精确 SHA 读取 |
| R4.3 新 TDX S 关系及四日 RAW 数量 | PASS_SCOPED | 本审查者从 Drive `R4_3_REQUIRED_FORMAL_EVIDENCE_20261009.zip` 实际解压 `latest_member_S.jsonl.gz`，自行 SHA256 检验匹配；55,136 关系=52,912 已映射＋2,224 未映射，401 个源板块（133 行业源对象/268 概念），无 `(sector_id,source_security_key)` 重复；日 RAW＋停牌逐日守恒：5210+12=5222, 5211+12=5223, 5213+11=5224, 5209+15=5224。仅此 ZIP 中冻结证据已在本审查环境独立操作，不等于所有 2.39GB 原始数据外部完整重跑。 |
| P0-A 成员重解析纠偏 | PASS_ENGINEERING / 外部重跑部分覆盖 | 新代码和 V2 收据可查。旧冻结 S 实际只有 **10 列**；原审计由较新 12 列 `capture()` 与较早冻结 S 比对产生版本歧义，现版本采用新 12 列内部验证同时保留原 10 列不可变快照，实际复现了当前 12 列分支失败并修正。需要区别旧版本本就可运行的校验和新版本修正，不称“旧 S 来源不可信”。 |
| 板块行业标签订正 | PASS_DEFECT_FOUND | 实际为 **110 个可排名叶行业、22 个派生父行业、1 个 T00 占位、268 个概念**，旧版“23 个父行业”是分类报告硬错误，不是 55,136 条成员发生改变。401 源组、400 可计算组；占位不强制造价格。 |
| 数值工程 QA | PASS_REPORTED / EXTERNAL_FULL_NOT_VERIFIABLE | 开发方 R1 收据：四日全量 RAW/停牌、128 MA/ATR/QFQ 样本、41,786 RPS 排序、26,119 RPS 端点、512 Profile 分支、103,680 日涨跌幅检查，0 error；新增 400×4 板块原生数值、40 LOO 样本；**全量 Rotation 状态机独立再实现未完成**。本次仅独立验证冻结成员摘要与四日期基础对账，不把开发代理自跑 Oracle 冒充本外审者重算全部原始 2.39GB。 |
| P0-B 页面兼容 | PASS_ENGINEERING / 生产未实测 | `v4_server.py` 现将 `/v4/operational-preview` 与 `/v4` 分离；有新 Head 时使用 R1 BFF 和兼容 assets，测试收据 120 个 HTTP 查询无错误；该 120 次在本地隔离模拟，非发布后真实生产。 |
| 最终候选封存与 CAS | PASS_STAGING_ONLY | `R43_OPERATIONAL_SUCCESSOR_CANDIDATE_V2.json` 摘要 `9c42365c...`，隔离 E 盘覆盖 stale/NOOP/fault/bad_source/concurrent/rollback；实际 production_CAS_executed=false。 |
| 生产版本 / FP 顺序门 | FAIL | `R43_LIVE_1008_FINAL_READBACK.json` 显示 `operational_head_exists=false`、线上 `accepted_trade_date=2026-09-30`，W7 未完成；FP-01–FP-14 未启动符合前置顺序。 |
| 本轮增量 Drive 归档 | FAIL_DELIVERY | R1 `R43_R1_DELIVERY_RECEIPT.json` 显示本轮 964,009 字节、68 文件本地增量 ZIP 校验成功但网络无法上传；上轮 R4.3 正式证据 ZIP 与 17 个大分段已在 Drive。归档不等于生产 CAS 前置代码门，但项目正式交付需要补传与回读。 |

## 2. 两项应在真正发布前定点核对的产品边界

1. **控制面数据时间一致性（新增实码审查发现）**：`src/workbench_service/v4_server.py` 的 `/api/v4/context` 有运营 Head 时由 `OperationalResearchBFF` 出 10/08；`/api/operations/status` 路径仍调用旧 `CurrentAcceptedV4Reader` 的 `reader.read('context')`，且 `ResearchBFF.current()` 也取原 9/30。在新 Head 启用后，即使研究数据 API 正确，运营控制面的部分“当前日期”可能仍报告 9/30。必须版本化地区分 `operational_accepted_trade_date=10/08` 与 `legacy_strict_pit_date=9/30`，不允许暗中改写 9/30 旧 Head。
2. **兼容层的有意缺口**：`r43_operational_bff.py` 对 Forward enrollment/stats、图表、历史 replay/compare、某些 market/diagnostics 子页面等返回 `SOURCE_INCOMPLETE`，且 R1 `api.js` 会把该状态表现为明确错误提示。这是尚未执行 FP 的真实范围限制，不应称“完整六大产品页面交付”。若当前旧页面的已用路由受影响，需最小修正；如属尚未开发功能则明确记录而不阻止独立的已接受日 K/板块生产域。

## 3. 为什么不能仅靠“用户已授权/32 绿/120 绿”直接自签

- 用户已授权运营研究的 **最新 TDX 成员代理回算** 和尽快正式投用；但这不是 10/09 成员属于 9/28 T0 的授权，`AS_RECORDED=false`、`PIT_ELIGIBLE=false` 必须继续。
- `r43_operational_publication.cas()` 的正式分支必须收到 `data/v4/R43_OPERATIONAL_EXTERNAL_ACCEPTANCE.json`，其中状态 `EXTERNALLY_ACCEPTED_R43_OPERATIONAL`、候选摘要与 `historical_PIT_permission=false` 相等；文件校验是工程闸门，独立外审不可由同一个修复代理自行声称。
- 严格来说该 JSON **只校验声明字段，并未校验独立签署的密码学真实性**。应在外部验收流程里固定审查者、范围、证据清单/摘要、所认可的有条件领域和真实回放记录，而不能把只含字符串 status 的随意文件当成真实独立审计。
- 之前的外审已解除了重复数据补采的理由；下一轮应该是一次性的 **最终数据范围判定→最小切换修复→签收→执行 CAS→生产与 UI 实际读回**，不再以“工程报告仍有个 UNKNOWN”整体停摆。Rotation 的全量递归验证如未覆盖，必须有清晰的可发布/不可发布域和质量标签，绝不虚构结果。

## 4. 继续推进的唯一下一门

1. 冻结 R1 SHA `4e344156...` 和候选 digest `9c42365c...`。先用已有 R4.3 17 分段 Drive 归档及 Git LFS 对关键原始 SHA 做定向独立复核，审核证据实际字节、R1 变更代码和上述 `/api/operations/status` 控制面一致性；由**真正独立于 Codex 执行者的审查者**签署按域限定的审核记录。缺独立 Rotation oracle 的域仍真实降级，不能把未审状态机提升成“算法准确已独立通过”。
2. 完成操作发布 CLI/Runbook（仓库中已有 `cas()` 函数，但未发现面向 R4.3 的安全生产发布 CLI）；要求 dry-run、expected previous SHA、candidate SHA、外部验收记录读取、并发锁、失败原子回滚、签发者审计轨迹，禁止自动捏造审核文件。
3. 收到真实有效的外部接受记录后在当前授权范围执行唯一一次生产 CAS 到 `data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json`；原 `data/v4/V4_DATA_ACCEPTED_HEAD.json` 保留。真实本机服务 `/api/v4/context` 为 10/08，同 token 的 stocks/sectors/relative-sector/rotation/market/focus 分域与 `/v4` 仍为原页面；服务/状态控制面清楚区分运营最新与旧 PIT 日期；缺域真实降级。
4. 补传本轮 964,009 字节 R1 增量归档至 Drive，并做文件 SHA/size 回读；Drive 网络异常不能误报已完成，但也不应当作数据错误去重复计算行情。
5. 只在实际 `FOUR_SESSION_PRODUCTION_ACCEPTANCE_PASS` 且生产 HTTP、页面、回滚证据到手后，启动 FP-01～FP-14 后续产品完善。

## 5. 审计追踪文件

- `docs/evidence/r4_3_r1_targeted_repair_20261009/R43_R1_FORMAL_HANDOFF.md`
- `.../SCOPED_ADMISSION_REQUEST_V2.json`
- `.../R43_R1_DELIVERY_RECEIPT.json`
- `.../R43_R1_FINAL_TEST_RECEIPT.json`
- `.../R43_NEW_OPERATIONAL_CANDIDATE_AND_CAS_V2.json`
- `.../R43_LIVE_1008_FINAL_READBACK.json`
- `src/workbench_analysis/r43_operational_publication.py`（CAS/外部准入）
- `src/workbench_service/v4_server.py`（研究路由 vs 控制面状态）
- Driver 上轮正式 ZIP `R4_3_REQUIRED_FORMAL_EVIDENCE_20261009.zip`，本轮独立 SHA、关系统计与对账已实读，未声称 full LFS 2.39GB 外部全量复算。

**最终意见**：不批准把 `NOT_VERIFIABLE` 写成通过并盲目发布，但强烈建议不再安排“重做四日数据”的新任务。应该立即执行一次真正的审查/发布两段式收口，且发布后验证日期和页面；只有这才构成用户要求的闭环。
