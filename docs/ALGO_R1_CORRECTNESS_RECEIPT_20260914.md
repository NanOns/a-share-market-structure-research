# 算法审计整改与 2026-09-11 本地重建回执（2026-09-14）

阶段合同：`R1_ALGORITHM_CORRECTNESS_AND_V3_LOCAL_REBUILD`。执行前已核对 `FULL_ALGORITHM_LOGIC_AUDIT_AND_OPTIMIZATION_20260914.md`、V3 主规格和最新整改文档。既有 Phase 0 结果为 `FULL_PASS`。`D:/new_tdx` 及配置的 TDX 来源全程只读。

## 代码整改

- 板块 MA20 宽度按同日有效成员的 `adj_close > ma20` 计算，周期合同升级为 `SECTOR_CYCLE_V1_5_QFQ_WIDTH_RS_ONLY`；RS5 缺失不再回退 RET5。
- 研究构建改用正式 strength 口径；真实价格基础、复权状态、版本、范围、宇宙及输入文件摘要纳入依赖身份，缺失或不一致时 fail closed。
- t-3 变化使用精确交易日对齐、共同成员和排名宇宙门槛；历史证据不足时保留 NULL/PARTIAL，不把未知伪装成 0。
- CURRENT/POTENTIAL 仅对合格板块排名；成员角色不再被预览行数提前截断；配置的覆盖、流动性、历史和监控字段均接入实际路径。
- 数值入库统一把 NaN/Inf/pd.NA 转为 SQL NULL，JSON 禁止 NaN；关注清单写入 `signal_date`、前态和变化原因。
- 旧 M14 热榜持久化入口已禁用，热榜仍保持请求时模式。
- V3 首页按钮改为完整本地流水线：自动输入、发布、M8/M9、M10 主线、V3 研究依次执行并轮询至终态。按钮不再沿用页面当前选择的旧发布日期，由最新官方输入包确定交易日；成功后自动刷新发布目录并切换到新发布。

## 删除与静态数据保留

执行合同 `V3_20260911_DYNAMIC_RESET_V1`，先把原数据库和生成文件原子移动到 `reports/reset_quarantine/20260914T013223Z`，再重建空动态库并复制批准保留的静态表。清理后所有动态表均为 0。保留计数包括：关系边 72,537、板块属性 553、板块语义 553、TDX 层级节点 553、来源包 1、来源文件 8；重建后这些记录仍存在。本次新发布追加 1 条关系观察审计记录，没有删除旧观察或改写静态关系。

## 页面触发与生产重建证据

通过 V3 首页“一键生成 V3 本地数据”按钮提交任务 `daily-d39dfaf4a16f4bef9bdbad89e35cc400`，任务依次经过 `COMPUTING`、`COMMITTING`、`ANALYSIS_BINDING`、`BUILDING_RESEARCH_V3`，终态为 `SUCCESS / COMMITTED`。生成发布 `m4-24145900a69e0d62330e91f965f680d4`，日期 `2026-09-11`，并绑定主线快照 `m10-mainline-preview-82655d23b38edde3`。

当前绑定快照有 553 个板块周期行，553 行全部使用新合同；546 行 MA20 宽度有效，532 行大于 0，范围为 0 到 1。主线 553 行。研究 run `research-c70cde7349e6417f90c454f195eba05d` 为 `COMPLETE`，算法版本 `RESEARCH_V3_PREVIEW_4_CORRECTNESS_PARTIAL`，参数摘要 `90aa8333a5b110681109d858add66f47e6b7ce5ee0269bbf073632fbfe66e081`；生成 531 个板块状态、6,182 个股票状态、9,335 个成员角色和 9 个 `CURRENT_FOCUS`，合格板块排名为 1 至 3，未合格行无排名，检查的研究数值无 NaN/Inf。在线热榜批次、排名、payload 和 pool 表均为 0。

V3 页面刷新后显示研究上下文“数据就绪”：当前强势 3 个、当前关注个股 9 条、旧版本地结构候选 1,071 股。提前观察为 0，并明确标注原因是当前只有一个派生交易日，缺少 3 日变化和先前强势状态，没有用旧候选填充。

## 验证与接受结果

最终针对性回归：`41 passed in 2.38s`。此前包含更多相关用例的回归为 `76 passed in 8.65s`。页面、REST API、数据库绑定及实际重建结果均已交叉核验。

接受结果：`DEGRADED_PASS`。当前日代码整改、动态数据清理、静态数据保留和 V3 页面一键全链重建均通过。依赖跨日证据的提前轨道仍不能 `FULL_PASS`：系统现在只有一个重新派生交易日，无法凭单日数据验收 t-3、episode 和效果稳定性；相关字段按合同保持 NULL/PARTIAL。下一阶段需用连续真实交易日累积 PIT 证据，再对提前轨道和效果稳定性单独放行。

独立审计项：`AUD-MA20-00`、`AUD-COV-02`、`AUD-RANK-03`、`AUD-PRICE-04`、`AUD-NULL-05`、`AUD-HOT-07` 的代码与本次重建验收已完成；`AUD-HIST-01`、`AUD-AMOUNT-A-06`、`AUD-MKT-08`、`AUD-EFFECT-09` 继续独立跟踪，不并入本次单日放行结论。
