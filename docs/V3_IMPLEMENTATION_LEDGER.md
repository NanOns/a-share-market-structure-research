# V3 实施台账

## 当前基线

| 字段 | 值 |
|---|---|
| 基线日期 | 2026-09-12（Asia/Shanghai） |
| 分支 | codex/v3-upgrade-analysis |
| 代码基线 | 6afd5c1 feat: complete m10-m15 workbench upgrade foundation |
| V3 复核文档 | docs/WORKBENCH_V2_REAUDIT_TO_V3_NOTES.md |
| V3 主实施文档 | docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md |
| 复核文档 SHA-256 | 9817D513C4A1EAB3FA3A30B3B928207F19CA01FC450781F3401EE9CF8CBFFCF9 |
| 主实施文档 SHA-256 | 912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24 |
| 工作区差异 | 主实施文档存在本轮之前的未提交修改；本轮未修改、未覆盖、未回退 |
| TDX 输入 | 未访问、未修改 |

本台账依据 V3 主实施文档第 2、13、17、18 章建立。V3 文档的工作区修改作为本次执行所使用的最新权威版本保留；其差异本身纳入基线证据，不把旧提交中的文档版本当作实施依据。

## 阶段记录

| task_id | status | input_revision | changed_files | test_evidence | product_or_data_evidence | open_issue | next_task |
|---|---|---|---|---|---|---|---|
| P00-01 | PASS | codex/v3-upgrade-analysis @ 6afd5c1；主实施文档为工作区最新版本 | 新增本台账；未修改业务代码、配置、数据库、TDX 输入 | 只读源代码检索、路由/页面/表读写映射、git 状态与文档哈希核对；未用测试替代阶段验收 | 已覆盖 V3 第 2 章全部 20 项旧能力，分类成员表和切片相关命中，解释当前生产/预览写入点 | 独立预览脚本的生命周期和后续退役边界尚需在后续阶段明确；当前已按“手工预览写入器”分类，不构成未解释写入点 | P00-02：只读容量基线与历史覆盖核验 |

### P00-01 阶段合同

本阶段只做只读基线审计：

1. 将 V3 第 2 章每项旧能力映射到当前页面、API、调用函数、读取表和写入表。
2. 检索 membership_entries、所有 *_daily 以及相关写入点。
3. 记录当前发布、导入、日任务、历史任务、分析物化、快照/切片和预览脚本的写入边界。
4. 固化代码版本、最新 V3 文档版本和工作区未提交差异。

本阶段没有启动 scanner，没有修改业务实现，没有修改数据库 schema，没有新增或变更 TDX 数据。

## 一、V3 第 2 章旧能力映射

| # | 旧能力 | 当前入口/API | 当前实现与主要读取 | 当前写入/状态 |
|---:|---|---|---|---|
| 1 | 首页市场总览 | /v2 overview；/api/dashboard、/api/publications、/api/market/cycle、/api/market/day-detail | app.py 的 dashboard 读取 market_daily、market_cycle_daily、发布及分析快照元数据 | 日发布由 repository.py 与 publish/service.py 写入基础发布表；分析预览写入市场周期表 |
| 2 | 首页强势板块 | /api/dashboard；overview 的 strong sectors | dashboard 的 _overview_strong_sectors 读取 sector_cycle_daily，并按旧 rank 聚合 | sector_cycle.py 写入 sector_cycle_daily；当前仍是旧排序语义，不代表 V3 双轨 |
| 3 | 首页优先研究 | /api/candidates；overview 的 priority research | app.py candidates 读取 candidate_daily | publish/service.py 与 repository.py 写入 candidate_daily |
| 4 | 板块全集与板块库 | /api/sectors、/api/sector-library | 读取 sector_daily、sector_base_daily；前者是旧发布表，后者是属性/快照表 | 基础发布写入 sector_daily；history_adapter.py 等物化 sector_base_daily |
| 5 | 板块周期矩阵 | /api/sectors/cycle、/api/sectors/{id}/timeline | 读取 sector_cycle_daily 及时间线 | sector_cycle.py 写入 sector_cycle_daily |
| 6 | 主线周期 | /api/mainlines、/api/mainlines/{id}/evidence | 读取 mainline_daily 及证据关联 | mainline.py、build_m10_mainline_preview.py 写入 mainline_daily |
| 7 | 成员留存与龙头变化 | /api/sectors/{id}/members/history、/leader-history | 读取 sector_member_state_daily、representative_state_daily | member_state.py、representative_state.py 写入对应分析表 |
| 8 | 板块—个股联动 | /api/linkage、/api/linkage/history、/api/stocks/{id}/memberships、/sector-associations | 读取 membership_entries、publication_memberships、sector_member_state_daily、sector_base_daily、stock_sector_associations_daily | repository.py、publish/service.py 写入 membership_snapshots、membership_entries、publication_memberships；member_state.py 和 association 预览脚本写入分析表 |
| 9 | 板块属性库与交集查询 | /api/sector-library、POST /api/sector-intersection/query | 读取 sector_base_daily、sector_member_state_daily，并按快照约束查询 | history_adapter.py、member_state.py 及 M11 预览流程写入对应物化表 |
| 10 | 五大结构 | /api/queues、/api/evidence、结构历史接口 | 读取 queue_memberships、queue_rankings、structure_details、historical_structure_daily、stock_structure_summary_daily | publish/service.py 与 repository.py 写入旧结构表；structures.py 写入历史结构和摘要 |
| 11 | 新高、RPS、均线、成交额 | /api/stocks/technical、/api/stocks/new-highs、技术历史接口 | 读取 stock_technical_daily、stock_high_daily、stock_strength_daily，以及 normalized adjusted daily parquet | technical.py、highs.py、strength.py 写入分析表；TDX/normalized 输入只读 |
| 12 | 个股证据详情 | /api/stocks/{id}/insight、/api/evidence；股票详情 modal | 组合读取 stock_technical_daily、stock_structure_summary_daily、sector_associations 及旧 structure_details | 由各分析物化器写入，不在请求时创建业务结果 |
| 13 | 本地涨停梯队与晋级 | /api/limit-ladder、/api/limit-ladder/promotion-history | 读取 limit_ladder_daily、limit_promotion_daily、market_reference_daily | build_m13_preview.py 及相关分析流程写入；reference_capability.py 写入市场参考表 |
| 14 | 在线最强主题、涨停分布、图示和总览 | 当前 v2 页面无完整对应入口；online 能力位于 src/workbench_online | 当前仅发现在线适配器/能力模块和数据源配置，未发现已接入的完整事件 API 或 V3 产品页 | 不纳入当前主流程；后续必须按 V3 在线能力合同、能力门和失败关闭规则单独接入 |
| 15 | 热度排名 | /api/hot-rankings；前端请求 cache=false | online_hot_rank.py 及 Eastmoney/THS 适配器，按请求读取并返回 | 当前未发现热榜原始 payload、行、批次或历史快照的持久化；符合请求时直连边界 |
| 16 | 板块精选 | 首页 strong sectors 现有实现 | 当前实现基于 sector_cycle_daily 的旧 rank，不是 V3 CURRENT/POTENTIAL 双轨精选 | 只有旧分析结果写入；V3 新语义尚未实现 |
| 17 | 数据状态与维护 | /operations；/api/operations/*、/api/input/latest、/api/history/coverage | 读取配置、source_bundles、文件清单、覆盖率、备份和存储状态 | operations、backup、history job 和 storage 流程写入运维表及任务事件 |
| 18 | 日报导出 | 当前 v2 路由未发现独立日报导出入口 | 未形成 V3 首日产品合同；不能把现有内部 preview 当作对外日报导出 | 后续按 V3 报告/导出合同另行确认 |
| 19 | 登录、成员、投资日历、外部软件跳转 | 当前 app.py 和 v2 router 未发现对应入口 | 当前未实现或不属于现有工作台主路径 | 不纳入本轮 V3 首个任务 |
| 20 | 龙虎榜、新闻和原因证据（可选/后置） | 发现 lh_list_capability.py、external_evidence.py 能力模块；当前 app.py 未发现对应 API | 能力模块存在，但未接入当前 v2 产品路由 | 后续按 V3 可选项和证据合同决定是否接入 |

## 二、当前页面与路由边界

当前 v2 顶层页面为 overview、sectors、stocks、linkage、market、data-info；sectors 下有 sectors、mainlines 两个子页。路由状态主要由 page、subpage、publication_id、trade_date、basis 驱动。

当前前端仍以旧工作台为主，核心调用关系如下：

- overview：dashboard、candidates。
- market：limit-ladder、promotion-history、hot-rankings、market/cycle。
- stocks：stocks/technical、stocks/new-highs、stock insight、technical-history、structure-history。
- sectors：sectors/cycle、timeline、members/history、leader-history、mainlines。
- linkage：sector-library、sector-intersection/query、linkage。
- data-info/operations：identity、metadata/field-catalog、history/coverage、input/latest、operations 相关接口。

因此，V3 后续不能把现有页面字段名称直接视为新产品契约；尤其是强势板块、候选、代表股、优先研究等旧聚合需要在 P01/P02 之后按 V3 双轨和角色定义重建。

## 三、membership_entries 命中分类

| 位置 | 分类 | 读写说明 |
|---|---|---|
| src/workbench_db/repository.py | 生产导入写入 | 从 sector_membership_daily.parquet 导入并写入 membership_snapshots、membership_entries、publication_memberships |
| src/workbench_publish/service.py | 生产发布写入 | _write_memberships 读取已有 snapshot/entries 后幂等写入 membership_snapshots、membership_entries、publication_memberships |
| src/workbench_service/app.py | 生产请求读取 | dashboard、sectors、linkage、identity 等查询 membership_entries 或其快照关联 |
| src/workbench_service/analysis_activation.py | 历史激活/克隆写入 | 创建历史 publication 时复制 publication_memberships；不是新的成员事实来源 |
| src/workbench_ops/backup.py | 运维读取 | 统计、校验和备份 membership_entries，不创建分析结果 |
| src/upgrade_m1.py | 审计读取 | 旧版 publication 表审计和摘要，不是生产写入器 |
| src/workbench_service/static/operations-i18n.js | 文本命中 | 仅界面文案，不访问数据库 |
| schema/migration 文件 | 定义 | 定义表结构、约束和迁移，不是运行时业务写入 |

结论：所有 membership_entries 直接命中均已分类为生产导入写入、生产发布写入、请求读取、历史激活复制、运维读取、审计读取、界面文本或 schema 定义；没有未分类命中。

## 四、*_daily 与切片相关写入分类

### 4.1 基础发布与旧工作台事实表

| 写入位置 | 表或对象 | 角色 |
|---|---|---|
| src/workbench_db/repository.py | market_daily、sector_daily、stock_daily、candidate_daily、structure_details、queue_memberships、unified_board、queue_rankings，以及成员表 | 旧版 release artifact 导入器 |
| src/workbench_publish/service.py | 同上基础发布表及 observations/outcomes | 当前日发布器；对发布请求做幂等写入 |
| src/workbench_service/analysis_activation.py | 旧 publication 表及成员表复制 | 历史 publication 激活时的快照复制 |

### 4.2 分析物化器

| 写入位置 | 表或对象 | 角色 |
|---|---|---|
| src/workbench_analysis/technical.py | stock_technical_daily | 技术指标物化 |
| src/workbench_analysis/strength.py | stock_strength_daily | 强度物化 |
| src/workbench_analysis/highs.py | stock_high_daily | 新高物化 |
| src/workbench_analysis/structures.py | historical_structure_daily、stock_structure_summary_daily | 历史结构和摘要物化 |
| src/workbench_analysis/history_adapter.py | sector_base_daily | 板块属性/历史适配物化 |
| src/workbench_analysis/coverage.py | historical_coverage_daily | 历史覆盖物化 |
| src/workbench_analysis/member_state.py | sector_member_state_daily、sector_membership_changes | 成员状态和变更物化 |
| src/workbench_analysis/representative_state.py | representative_state_daily | 代表股状态物化 |
| src/workbench_analysis/sector_cycle.py | sector_cycle_daily | 板块周期物化 |
| src/workbench_analysis/mainline.py | mainline_daily | 主线物化 |
| src/workbench_analysis/reference_capability.py | market_reference_daily | 市场参考能力物化 |

### 4.3 快照、切片、历史任务和预览写入

| 写入位置 | 表或对象 | 角色 |
|---|---|---|
| src/workbench_analysis/slice_coordinator.py | storage_objects、analysis_slices、analysis_slice_dependencies、analysis_daily_basis | 受身份约束的切片与存储协调 |
| src/workbench_analysis/hierarchy.py | tdx_sector_hierarchy_versions、tdx_sector_hierarchy_nodes | 层级版本与节点绑定 |
| src/workbench_service/history_jobs.py | jobs、job_attempts、job_events | 历史任务状态和事件；通过 worker 委托实际处理 |
| src/workbench_service/analysis_activation.py | analysis_snapshots、analysis_snapshot_entries、analysis_snapshot_hierarchy、publication_analysis_snapshots 等 | 分析快照与 publication 绑定 |
| scripts/build_m8_m9_preview.py | M8/M9 分析表、snapshot/slice/entry/binding 表 | 当前日任务在 app.py 中明确调用的预览/分析构建流程 |
| scripts/build_m8c_local_reference_preview.py | 本地参考分析快照、切片、条目 | 独立预览脚本，手工入口 |
| scripts/register_m8c_public_rules_preview.py | 公共规则分析快照、切片、条目 | 独立预览脚本，手工入口 |
| scripts/build_m10_mainline_preview.py | mainline_daily 及分析快照 | 独立预览脚本，手工入口 |
| scripts/build_m11_association_preview.py | 关联结果及分析快照 | 独立预览脚本，手工入口 |
| scripts/build_m13_preview.py | market_cycle_daily、limit_ladder_daily、limit_promotion_daily 及绑定表 | 独立预览脚本，手工入口 |

独立预览脚本均已识别并解释为 preview writer，没有把它们误归类为未知生产写入；其运行时所有权、重复运行策略和后续退役边界留作后续阶段治理事项。

## 五、后台入口与写入顺序

app.py 的 handler 初始化 HistoryJobService、AnalysisActivationService、OneClickPublisher，执行 run_upgrade_m3.py、submit_one_click，等待发布完成后调用 scripts/build_m8_m9_preview.py。由此可确认当前主日流程的顺序是：

1. 读取 release/TDX 派生输入。
2. 通过 repository.py 或 publish/service.py 创建基础 publication 事实及旧工作台表。
3. 通过历史/分析流程创建分析快照、切片和 *_daily 物化。
4. 由 v2 API 读取旧事实表或分析表供页面展示。

当前生产请求仍能直接读取 candidate_daily、queue_memberships、sector_daily、market_daily 等旧表；这正是 V3 后续必须进行“旧能力保留”和“新主路径隔离”的边界。

## 六、证据与执行结论

本阶段执行的证据类型：

- 读取当前分支、HEAD、工作区状态和两份 V3 文档哈希。
- 枚举 src、scripts、tests 文件并阅读 app.py、v2 router/api/app、repository、publish、analysis、history、activation、production 入口。
- 检索 membership_entries、*_daily、表名写入调用、API route 和前端请求。
- 对每个命中按生产读取、生产写入、分析物化、快照/切片、预览、运维、测试/审计、废弃/文本进行分类。

验收结论：P00-01 PASS。V3 第 2 章 20 项旧能力均有映射；membership_entries 和切片相关命中均已分类；当前可见生产写入点均有来源和角色说明。按照 V3 阶段门，下一阶段为 P00-02；在 P00-02 完成前不启动 scanner。
