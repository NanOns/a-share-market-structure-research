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

| P00-02 | PASS | codex/v3-upgrade-analysis @ 5ae8de4；主库以 read_only=True 打开；采集时间 2026-09-12T00:15:38+08:00 | 新增 docs/V3_P00_02_CAPACITY_BASELINE.md；未修改数据库、data、runtime、TDX | DuckDB PRAGMA database_size、全表 COUNT、业务键/slice 键、hash 分组、目录字节/文件数、发布引用链；不以测试替代容量验收 | 75 表行数、数据库块占用、库外目录、关系边摘要、high window、内容摘要重复和当前发布引用均已固化 | storage_objects 标记 referenced=true 但当前 publication 链实际引用 0；backup catalog 与物理文件需后续对照；可回收大小均按证据标注 UNKNOWN | P00-03：冻结配置、DTO、合成夹具和 capability 状态 |

| P00-03 | PASS | codex/v3-upgrade-analysis @ 3815435；V3 主实施文档工作区版本 | 新增 V3 配置、DTO/schema、reason catalog、合成夹具、合同校验器和 P00-03 测试；未改数据库和旧业务路径 | tests/upgrade_v3/test_p00_03_contracts.py：5 passed；覆盖参数哈希、枚举、未知字段、NULL规则、reason 标签和合成夹具标记 | 冻结 RESEARCH_V3_PREVIEW_1、CURRENT/POTENTIAL/股票角色阈值、分页/排序/NULL策略、API01–15 核心 DTO；7 个夹具全部 synthetic | 生产 app 尚未消费 V3 合同资产，属于本阶段刻意边界；HOT_RANKINGS 继承旧 direct-ephemeral 状态，但 V3 在线能力仍等待 P09-01 复核 | P01-01：缩短数据库锁作用域 |
| P01-01 | PASS | codex/v3-upgrade-analysis @ 3f6f664；主实施文档工作区版本；未访问 TDX | 修改 `src/workbench_service/app.py`：热榜 GET 退出请求级锁、远程等待后批量补名称、响应写入处理客户端断开；新增 `docs/V3_P01_01_LOCK_SCOPE.md` 与阶段回归测试 | `tests/upgrade_v3/test_p01_01_lock_scope.py` 3 passed；P00-03 5 passed；M14 hot-rank 3 passed；py_compile 与 diff check 通过 | 注入最长 8 秒 direct 等待期间，同一 Api 的本地 publication 读 `<0.5s`；普通 GET 仍保留 request_scope；POST 写任务边界未扩大；无数据库/TDX/热榜持久化写入 | M15 既有资源版本断言 `m15-03` 与当前 `m15-04` 不一致，未纳入本阶段；HOT_RANKINGS V3 capability 仍等 P09-01 | P01-02：修复热榜分页与单源失败语义 |
| P01-02 | PASS | codex/v3-upgrade-analysis @ bc5882b；主实施文档工作区版本；未访问或修改 TDX/数据库 | 修改 `src/workbench_service/online_hot_rank.py` 及两个 hot-rank adapter；新增 `docs/V3_P01_02_HOT_RANK.md` 与合成分页/失败/超时回归 | `tests/upgrade_v3/test_p01_02_hot_rank.py` 5 passed；M14 hot-rank API/adapter 7 passed；py_compile 与 diff check 通过；未修改旧测试预期 | 第2页20条报价只请求本页；100条完整集合 `total=100`；上游页不二次偏移；源独立并发；源A失败源B显示；12秒总预算超时；`cache:false` 与零热榜持久化不变 | M15 既有资源版本断言继续独立跟踪；HOT_RANKINGS V3 capability 仍等 P09-01 | P01-03：修证据弹窗和返回路径 |
| P01-03 | PASS | codex/v3-upgrade-analysis @ c46ffb5；主实施文档工作区版本；未访问或修改 TDX/数据库 | 修改 `src/workbench_service/static/v2/app.js`、`api.js`、`index.html`；新增 P01-03 样式、契约测试和阶段报告 | `tests/upgrade_v3/test_p01_03_evidence_modal.py` 与 V3/M14 回归共 59 passed；4 个 JS `node --check` 通过；diff check 通过；1440×1000 与 390×844 真实页面交互记录通过 | 证据从 details 改为同 modal 静态分组；modal 为 `min(960px,100%)`/85vh；X/遮罩/Esc/焦点返回通过；技术历史、市场日明细、板块时间线、主线证据拒绝旧响应覆盖新对象；来源文本不执行 HTML | M15 既有资源版本断言继续独立跟踪；主实施文档既有工作区修改仍未触碰 | P02-01：双轨首个分析/展示切片的范围与合同复核 |
| P02-01 | PASS | codex/v3-upgrade-analysis @ 426525b；主实施文档工作区版本；未访问或修改 TDX/生产数据库 | 新增 `025_v3_relations.sql`、`relation_repository.py`、`membership_resolver.py`、P02-01 测试和阶段报告；更新迁移链断言 | `tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7`：122 passed；P02-01 合成覆盖稳定 scope、hash、source_kind、增3删2、A→B→A、无变化 observation、INVALID 空/不完整源；py_compile/diff check 通过 | 新关系/属性表与旧表并存；无变化不增 revision/edge；变化仅闭旧边/开新边；旧 revision 可查；属性改名不改关系 revision；无效源不关闭原关系；025 只在临时 DuckDB 验证 | P02-02 需实际旧快照和 payload 语义核对；正式迁移/旧导入不在本阶段；主实施文档既有工作区修改仍未触碰 | P02-02：导入旧关系并逐快照对照 |
| P02-02 | PASS | codex/v3-upgrade-analysis @ 5aa5ce2 起；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；生产备份 `backup-20260911T193112Z-7a931b0724e8` 已 VERIFIED | 新增 `legacy_relation_import.py`、导入脚本、P02-02 测试；生产应用 `025_v3_relations` 并绑定实际 6 个旧快照；旧表保留 | `tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7`：123 passed；生产逐快照 direct resolver/payload 对照 6/6 PASS；9/8/9/9 共享 revision 3、日期/observation 独立；旧 entries 435472 未变；服务恢复 READY | relation revisions 3、edge intervals 74086、observations/bindings 6；属性版本全部非 NULL；9/10 的 2892 DERIVED_PARENT 留在 legacy basis，未伪装成 direct edge；修复属性版本返回漏字段与 snapshot resolver scope 读取缺陷 | 旧表读路径、publication binding 和父行业树解释尚未切换；旧表新写仍保留；主实施文档既有工作区修改未触碰 | P02-03：树语义复用与父成员去重 |
| P02-03 | PASS | codex/v3-upgrade-analysis @ 9bbdb0c 起；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；生产备份 `backup-20260911T233048Z-45d7b3c1bed2` 已 VERIFIED | 修改 `src/workbench_analysis/hierarchy.py`；新增 `scripts/bind_v3_hierarchy.py`、P02-03 测试与阶段报告；复用 `tdx_sector_hierarchy_versions/nodes`；仅绑定 2026-09-10 的 relation observation/snapshot；旧树、旧表不变 | `tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7`：126 passed；py_compile、diff check 通过；生产绑定后父成员审计 PASS、mismatch 0；6/6 旧快照对照 PASS；服务 READY | V1.1 树语义摘要只依赖 contract/节点/父/level/relation_basis；554 节点不因无关 source hash/path/name 重存；22 父行业得到 2,892 个去重成员；9/10 的 75,028 行中仅 2,892 行作为 DERIVED_PARENT 证据解释；9/4、9/7、9/8、9/9 未被未来树回填 | `relation_publication_bindings`、旧 API/read path 和旧全量新写仍待接入/关闭；主实施文档既有工作区修改未触碰 | P02-04：接入旧读路径，再关闭旧全量新写 |
| P02-04 | PASS | codex/v3-upgrade-analysis @ a116d99 起；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；初始备份 `backup-20260911T233048Z-45d7b3c1bed2` VERIFIED；真实验证备份 `backup-20260912T002526Z-822de3d9b647` VERIFIED | 修改 `membership_resolver.py`、`app.py`、`relation_repository.py`、`analysis_activation.py`、`workbench_publish/service.py`、`workbench_db/repository.py`；新增 P02-04 测试与阶段报告；新发布改写 relation observation/binding，关闭 `membership_entries` 全量新写 | 原目标回归 159 passed；真实验证后 P02-04/M4 定向回归 16 passed；py_compile、diff check 通过；HTTP smoke READY/0；真实 production revision `m4-p02-04-real-validation-20260912` identity=`PUBLICATION` | 历史 publication→relation bridge；真实新 publication 成功写入 binding，relation revision 4、observation 7、binding 1；验证后恢复原 2026-09-07 active head；旧 entries 435472 未变；P02-03 9/10 树审计继续 PASS | 旧迁移器/备份兼容读取保留；独立 M15 资源版本断言已在提交 `277ebf4` 单独关闭；主实施文档既有工作区修改未触碰 | G02 → P03-01：建立共享结果对象与切片绑定层 |
| P03-01 | PASS | codex/v3-upgrade-analysis @ 236ff88 起；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；生产备份 `backup-20260912T000023Z-65432baaf1ee` VERIFIED | 新增 `026_v3_result_objects.sql`、`result_objects.py`、只读/应用迁移脚本、P03-01 测试与阶段报告；新增结果对象和切片绑定表；未迁移旧领域 writer | 定向迁移/P03 回归 10 passed；V3/M14/M7/M2/M4/M1 完整回归 162 passed；py_compile 通过；HTTP smoke READY/0；迁移回执 `migration-026_v3_result_objects-672e1f8df6094901a2fb20ff7f93496f` | 生产 `analysis_slices` 389 保持不变，result objects/bindings 均为 0；同内容不同 slice 一对象两身份；质量/语义/业务值差异不共享；精确回读校验通过；旧关系与 membership_entries 计数未变；TDX 未访问 | 旧域结果尚未导入 `*_result_rows`；用户主规格工作区修改仍保持未提交；独立 M15 资源版本断言仍单独跟踪 | P03-02：按 technical → strength → high 顺序逐域导入、对照、切读、停旧写和验收 |
| P03-02-technical | PASS | codex/v3-upgrade-analysis @ 236ff88 起；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；备份 `backup-20260912T004954Z-21dfb9a772b2` VERIFIED | 新增 `027_v3_technical_result_rows.sql`、technical V3 writer、迁移脚本、P03-02 technical 测试与阶段报告；服务 API、M8C/M11/M13 reader 切到 `technical_result_daily`；主 M8/M9 preview technical writer 停止写旧表 | P03-02 technical 定向 2 passed；相关完整回归 185 passed；py_compile/diff check 通过；生产逐行 old↔new 双向差集均为 0；HTTP smoke READY/0 | 31 个 technical slice 全部绑定；12 个 result objects、111203 个去重物理行、兼容视图回读 278009 行；未绑定回退行 0；迁移回执 `migration-027_v3_technical_result_rows-4f6afa01393d4f3a92df1b0fc972001b`；旧表保留但不再是主 reader/writer | `strength`、`high` 尚未执行；旧 M8 fixture adapter 与旧表审计/备份兼容读取保留；主实施文档既有未提交修改未触碰 | P03-02-strength：按同一合同迁移 strength，technical PASS 不扩大为整步 PASS |
| P03-02-strength | PASS | codex/v3-upgrade-analysis @ 91f57ac；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；备份 `backup-20260912T010834Z-02efee63a95c` VERIFIED | 新增 `028_v3_strength_result_rows.sql`、strength V3 writer、迁移脚本、P03-02 strength 测试与阶段报告；服务 API strength reader 切到 `strength_result_daily`；主 M8/M9 preview strength writer 停止写旧表 | strength 定向 2 passed；相关完整回归 187 passed；py_compile/diff check 通过；生产逐行 old↔new 双向差集均为 0；HTTP smoke READY/0 | 31 个 strength slice 全部绑定；9 个 result objects、92669 个去重物理行、兼容视图回读 278009 行；未绑定回退行 0；迁移回执 `migration-028_v3_strength_result_rows-0e14075c629f42c494ae100f6fd85600`；旧表保留但不再是主 reader/writer | `high` 尚未执行；high 结果表及 writer 保持旧路径；主实施文档既有未提交修改未触碰 | P03-02-high：按文档要求迁移 high，物理键必须保留 window，strength PASS 不扩大为整步 PASS |

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

验收结论：P00-01、P00-02 均 PASS。P00-02 已完成只读容量与历史覆盖基线，未执行任何清理或数据库写入；下一阶段为 P00-03。在 P00-03 完成前不启动 scanner。

P00-02 详细报告：[V3_P00_02_CAPACITY_BASELINE.md](V3_P00_02_CAPACITY_BASELINE.md)。

P00-03 验收结论：PASS。V3 配置参数已用单一参数哈希冻结；schema 的 required、nullable、枚举和 unknown-key 规则已固化；reason 中文标签有目录校验；7 个合成夹具明确不是行情样本；现有 capability 状态已登记且未把 NOT_VERIFIED 自动打开。下一阶段进入 P01-01，仍不启动 scanner。

P00-03 合同资产 SHA-256：

- config/research_attention_v3.yaml：2217E478EC326219DC8F698D1F6E5C8532CB713C2479C46C48CCF48F87239D06
- config/research_v3_schema.yaml：008EBCFD4405D3485BCDCD363C8432665483533B042C0364B9F992CCFC8FFADC
- config/research_v3_reasons.yaml：2E9DF59A1FFEFE8A97C2F0E9C1CCE88F90636499671F8A8B7EEB3A754B1D24FE
- tests/fixtures/research_v3_p00_03.json：9FE4EB4FAF1E113B09EC279C83FAD604413121FC83F360EB003D81CCE49A3CC8
