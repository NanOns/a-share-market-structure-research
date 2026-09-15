# V3 实施台账

## V3 全栈复核整改（2026-09-13）

| task_id | status | stage_contract | evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| V3-SINGLE-DAY-RESET-20260913 | FULL_PASS | `V3_SINGLE_DAY_CLEAN_REBUILD_V1_0`；V3 §0、§2.1、§3、§18；用户单日清库裁决 | `docs/V3_SINGLE_DAY_RESET_20260913.md`；publication `m4-5fd06398dde1d174114e253af4330825`；snapshot `m8-m9-local-reconstructed-preview-v2-fa7ae877fdb0ce0e`；run `research-5fbbc614e78a42e384f329048792353c` | 旧生成数据与重复静态结果永久删除；仅 2026-09-11 publication/run；553 层级节点、72,537 关系、531 READY、CURRENT 3、CURRENT_FOCUS 9；页面空库完整构建及成员下钻通过 | 后续交易日使用同一页面完整构建入口 |
| V3-RA-REMEDIATION-20260913 | DEGRADED_PASS | `V3_FULL_STACK_REMEDIATION_V1_0`；用户裁决 `V3-UC-20260913-01`；V3 §2、§5–§12、§18.13–14、§20–§22 | `docs/V3_FULL_STACK_REAUDIT_20260913.md`；`docs/V3_REAUDIT_REMEDIATION_20260913.md`；真实 run `research-5674cf88ba024738bf3dc066c2e57155` | V3 移除本地收盘梯队/晋级并只用在线入口；完整在线页显式可达；对象下钻修复；CURRENT 12、CURRENT_FOCUS 20、554/554 READY；POTENTIAL 当前日为 0，在线与效果仍诚实降级 | 多交易日 POTENTIAL/P10-03 观察；在线逐数据集复测 |

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
| P03-02-high | PASS | codex/v3-upgrade-analysis @ 1230bb3；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；备份 `backup-20260912T012602Z-9a4b46c91b4d` VERIFIED | 新增 `029_v3_high_result_rows.sql`、high V3 writer/迁移脚本、P03-02 high 测试与阶段报告；high production writer 切换 `insert_high_result_rows`；API/M13 reader 切换 `high_result_daily`；旧 high 表保留为兼容/审计来源 | high 定向 2 passed（含同输入三次重跑）；相关完整回归 189 passed；py_compile/diff check 通过；生产逐行 old↔new 双向差集均为 0；HTTP smoke READY/0 | 31 个 high slice 全部绑定；8 个 result objects、296544 个去重物理行、兼容视图回读 1112040 行；未绑定回退行 0；31/31 四窗口；迁移回执 `migration-029_v3_high_result_rows-306e6fa6dfad4ea1b67007ae32f48825`；SQL SHA `68c0b1af6b4cdd30cd36ce8d85a93cc327f3c8c30886a3b8b291edbefc3d611a` | 旧 metadata 存在 exact 与 x4 两种已核实历史口径，31 个均无 mismatch；旧表不删除、不再由生产 writer 写入；主实施文档既有未提交修改未触碰 | P03-03 尚未执行；按文档逐域迁移 member_state、structure、summary |
| P03-03-member_state | PASS | codex/v3-upgrade-analysis @ 0779bb5；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；备份 `backup-20260912T020156Z-638bdba5a42e` VERIFIED | 新增 `030_v3_member_state_result_rows.sql`、member_state V3 writer/迁移脚本、P03-03 member_state 测试与阶段报告；M8/M9 writer、M10/M11 reader、API 切换 `member_state_result_daily`；旧成员状态表保留为兼容/审计来源；`sector_membership_changes` 未扩大纳入 | member_state 定向 2 passed（含同输入三次重跑与 NaN canonical hash）；相关完整回归 264 passed；py_compile/diff check 通过；生产逐行 old↔new 双向差集均为 0；成员历史/股票成员关系/linkage history HTTP smoke READY/0 | 31 个 member_state slice 全部绑定；16 个 result objects、1783166 个去重物理行、兼容视图回读 3365740 行；未绑定回退行 0；重复业务键 0；NaN 物理值保留且 canonical policy 已登记；迁移回执 `migration-030_v3_member_state_result_rows-032e933362f745d7ae33ee65ac990c5b`；SQL SHA `1c4740ebe4ae4e9039973bdf4896731cc742324cec97d12fa395b7d18930cdd3` | 静态板块属性仍由 `sector_base_daily` 提供；`sector_membership_changes`、structure、summary 未迁移；主实施文档既有未提交修改未触碰 | P03-03-structure：按文档继续迁移 structure，member_state PASS 不扩大为整步 PASS |
| P03-03-structure | PASS | codex/v3-upgrade-analysis；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；备份 `backup-20260912T023322Z-46f5b9f95f44` VERIFIED | 新增 `031_v3_structure_result_rows.sql`、structure V3 writer/迁移脚本、P03-03 structure 测试与阶段报告；M8/M9 structure writer、M13 structure reader、API 结构历史/队列/evidence reader 切换 `historical_structure_result_daily`；旧结构明细表保留；summary 未扩大纳入 | structure 定向/关联测试 23 passed；审计后跨域回归 383 passed；py_compile/diff check 通过；生产 old↔new 双向差集 0；逐 slice 行数一致；HTTP smoke READY/0 | 15 个 structure slice 全部绑定；3 个 result objects、81905 个去重物理行、兼容视图回读 409510 行；未绑定回退行 0；重复结果业务键 0；迁移回执 `migration-031_v3_structure_result_rows-d8eced0d71c04d19afb21c787bbbd433`；SQL SHA `90746b7e7b1f262cd169eb68fb9817bffde1e3995a5b0d36d205fcd9d9cac0be`；summary 旧表 81902 行保持不变 | M12 旧 UI 断言已按 P01-03/V3 §12 静态 modal 合同修正；summary 尚未迁移；主实施文档既有未提交修改未触碰 | P03-03-summary：只迁移 summary，structure PASS 不扩大为整步 PASS |
| P03-03-summary | PASS | `0298dc9 feat: complete v3 p03-03 summary result rows`；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；备份 `backup-20260912T030620Z-5f80d367e3dc` VERIFIED | 新增 `032_v3_structure_summary_result_rows.sql`、summary V3 writer/迁移脚本、P03-03 summary 测试与阶段报告；M8/M9 preview summary writer 切到 V3；API intersection/new-high/stock insight summary reader 切到 `structure_summary_result_daily`；旧 summary 表保留 | summary 定向 2 passed；相关完整回归 385 passed；compileall、6 个 JS node check、diff check 通过；old→new/new→old 按业务字段及规范化 JSON 差集 0；HTTP smoke READY/0 | 15 个 summary slice 全部绑定；3 个 result objects、16381 个去重物理行、兼容视图回读 81902 行；未绑定回退 0；迁移回执 `migration-032_v3_structure_summary_result_rows-81d03235648b491e89114220a425c4fa`；SQL SHA `b8a7f6e7405acad562c1c1c6ee73fbb01c9c66ca929d013b14a14ce1350d3cef`；旧表未删除/未写入 | `queues_json` 仅做规范化 JSON 表示，业务语义未变；history-backup 外部对象路径校验仍是独立跨域问题，本阶段使用 VERIFIED offline backup；主实施文档既有未提交修改未触碰 | P04-01：规划每日最小失效范围 |
| P0-P3-internal-audit | FULL_PASS | `0298dc9 feat: complete v3 p03-03 summary result rows`；主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；审计报告 `docs/V3_P0_P3_INTERNAL_AUDIT.md` | 对已执行 P00-01～P03-03-summary 的源码、迁移、脚本、测试、阶段报告和生产证据做只读内部审计；summary JSON 规范化差异已按业务语义同步核对；主 V3 文档未触碰 | P0-P3 相关回归 `385 passed`；Python compileall、6 个 JS node check、diff check 通过；六个已迁移域按各自业务语义双向差集均为 0；关系/层级/迁移 hash/服务状态均 PASS | schema migrations 29、checks 28、latest 032；technical/strength/high/member_state/structure/summary fallback 均为 0；summary 15/15 binding；服务 READY/0；TDX 未访问/未修改 | history-backup 外部对象路径缺失仍为独立跨域问题；本阶段使用 VERIFIED offline backup，不绕过路径校验；主 V3 文档仍保留用户既有未提交修改 | P04-01：按文档规划每日最小失效范围 |

| P04-01 | PASS | 当前主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；分支 `codex/v3-upgrade-analysis`；未访问或修改 TDX/生产数据库 | 新增 `build_planner.py`、`plan_v3_build.py`、P04-01 测试和阶段报告；依赖摘要分离为交易日/行情/关系/板块属性/树/参数/复权；输出版本化、可解释、可去重的 `build_plan` | `pytest -q tests/upgrade_v3 tests/upgrade_m7/test_window_planner.py`：52 passed；compileall、diff check 通过；改名/关系/价量/复权/新日/幂等边界均通过 | 改名只计划属性域；关系变化不进入无关技术域；价量修订覆盖受影响窗口的全市场 RPS，并传播 high/structure/summary 到 cutoff；相同输入 `NO_WORK` 且 `tasks=[]`；无 writer、无结果表/发布写入 | P04-02 writer 尚未实现，等待本阶段提交后单独执行；主实施文档既有工作区修改未触碰 | P04-02：让增量 writer 严格消费 build_plan |
| P04-01-R19-02-04 | PASS | 最新 V3 主实施文档 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`；P04-01 补项；未访问或修改 TDX/生产数据库 | 修正 `src/workbench_service/build_planner.py`；新增 R19-02/R19-03/R19-04 反例测试；更新 `docs/V3_P04_01_BUILD_PLAN.md` | P04-01 定向 11 passed；受影响 P04-02 定向 5 passed；V3/M7 window 62 passed；compileall、diff check 通过；实测 RET60 `d+60`、EMPTY/MISSING、价格/复权市场及板块/成员闭包、未知参数 fail-closed | R19-02/R19-03/R19-04 已关闭；本补项未写生产数据库或 TDX；P04-02 R19-05/R19-06 仍未关闭 | P04-02-R19-05-06：完整快照覆盖、frame 业务键核验、逐域执行器矩阵和真实 daily 入口 |
| P04-02 | PASS | 当前主实施文档 SHA `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`；分支 `codex/v3-upgrade-analysis`；真实验证只读实际 adjusted_daily，写入临时 DuckDB | 新增 `incremental_writer.py`、`run_v3_incremental_build.py`、P04-02 测试和阶段报告；复用 P03 result-row writer；同域同日多任务可合并为一个 slice；快照/发布绑定后置到同一事务完成点 | P04 定向 11 passed；全 V3/M7 window 回归 57 passed；P03 定向 15 passed；compileall、diff check 通过；实际 parquet 65 行/60 个技术任务/两个相邻日期三次重跑记录 2→0→0 新事实行 | 首次实测 `db_file_growth_bytes=7077888`；重跑增长 0；`reused_result_objects` 0→2→2；失败 writer 回滚 slice/result/snapshot/binding；计划外对象在写库前拒绝 | `quote`/`market` 未注册 writer 时 fail-closed，未伪造完成；P04-03 缓存与回收未执行；主实施文档既有工作区修改未触碰 | P04-03：管住解包缓存和全库副本 |
| P04-02-R19-05-06 | PASS (SCOPED) | 最新 V3 主实施文档 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`；分支 `codex/v3-upgrade-analysis`；未访问或修改 TDX/生产数据库 | 修复 `incremental_writer.py` 的完整目标快照门、业务键交叉核验、REUSE 来源核验和显式执行器矩阵；扩展 `build_planner.py` 的目标域上下文；更新 `run_v3_incremental_build.py` 的只读 `source_parquet` daily 入口；新增反例与 raw-input 链路测试 | P04-02/P04-01 定向 22 passed；`pytest -q tests/upgrade_v3 tests/upgrade_m7/test_window_planner.py`：68 passed；compileall、diff check 通过 | 仅目标域集合完整且每项由 CALCULATE 或显式 REUSE 覆盖时允许 snapshot/publication binding；partial technical-only 不能绑定未声明的全目标；错误股票/板块键和同日跨股票 REUSE 拒绝；quote/market 显式 UNSUPPORTED；technical raw input→calculate→write→bind 临时库闭环通过 | `P04-02-INTEGRATION` / C20-16 仍开放：当前新增入口是受控 V3 CLI，不等同于旧 `build_m8_m9_preview.py` 已完成生产调用链接入；P04-03 不提前开始；主实施文档用户未提交修改未触碰 | P04-02-INTEGRATION：接入实际每日生产调用链并验收新日、历史修订、关系变化、同输入重跑 |
| P04-02-INTEGRATION / C20-16 | PASS (SCOPED) | 最新 V3 主实施文档 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`；分支 `codex/v3-upgrade-analysis`；未访问或修改 TDX/生产数据库 | 新增 `v3_daily_entry.py`、P04-02-INTEGRATION 测试/阶段报告；修改 `app.py` 接入旧 daily 调用链；`incremental_writer.py` 增加 source snapshot 复用证据、同域同日批量对象及旧域保留条目；CLI provider 支持批量证券过滤 | 集成定向 `14 passed`；V3/M7 回归 `74 passed`；compileall、diff check 通过；覆盖新日、历史价量修订、关系变化、同输入重跑、结果写入、source snapshot/publication binding 和兼容条目保留 | V3 入口已从只读 normalized parquet→plan→CALCULATE/REUSE→P03 writer→snapshot/publication binding；目标完整性由 plan 驱动；旧域条目不满足目标门，仅保留兼容 reader；入口失败 fail-closed | `mainline` 未纳入默认目标，因为旧 `build_m8_m9_preview.py` 当前不产生该域；显式请求缺失域会失败；未执行生产 daily job，生产激活仍需独立运维窗口证据；P04-03 未执行 | P04-03：按最新 V3 文档执行缓存/源包引用与备份链审计，不做删除 |
| P04-03-01 | PASS (AUDIT ONLY) | 最新 V3 主实施文档 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`；只读数据库/文件盘点；未访问或修改 TDX | 新增 `docs/V3_P04_03_01_STORAGE_INVENTORY.md`；登记 5 bundle、4 ZIP、4 extracted roots、4 metadata snapshots、normalized/cache/backups/runtime 容量和现有 catalog 引用 | 5 bundle 的解包文件数/字节数与 manifest 一致；metadata 每 bundle 8 文件且尺寸一致；`.phase1_cache` 954,775,668 B，低于 2 GiB预算；未执行删除、移动、cleanup 写入或生产备份 | 唯一源与解包/metadata 均先保护；识别旧 bundle 缺显式 staged_path、`source_files=0`、backup catalog/物理对象未完全对照三个独立问题；不把结构一致冒充 resolver 恢复或回收可行 | `P04-03-01-A/B/C` 独立跟踪；P04-03-02 resolver 恢复验证未执行；P04-03 后续缓存预算、backup 调用链和回收预览均未执行 | P04-03-02：临时目录验证 resolver 从保留源包恢复文件，仍不修改生产源/库 |
| P04-03-02 | PASS (SCOPED) | 最新 V3 主实施文档 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`；`v3-p04-03-resolver-recovery-v1.0`；仅临时目录/合成 ZIP；未访问或修改 TDX、现有 input_staging、生产数据库 | 新增 `restore_source_bundle_extraction()` 及导出；新增 `docs/V3_P04_03_02_RESOLVER_RECOVERY.md` 和 resolver 反例/恢复测试；显式 staged path 优先、旧回执日期回退 | 定向 `pytest -q tests/upgrade_v3/test_p04_03_02_resolver.py tests/upgrade_m3/test_automatic_input.py`：15 passed；回执身份、包 SHA/大小、解包计数、所需成员、原子新目标和篡改包 fail-closed 均通过；`git diff --check` 通过 | 能从保留包恢复缺失解包目录；旧 `staged_path` 缺失时可解释回退；TDX/项目根外路径拒绝；不将恢复动作隐式并入发布校验 | 未做真实大包恢复或生产激活；未启用最近2 bundle/phase1_cache预算、未审查backup调用链、未执行删除；`P04-03-01-A/B/C`仍独立跟踪 | P04-03-03：按§17.8建立最近2 bundle与phase1_cache预算预览，先保护判断不删除 |
| P04-03-03 | PASS (SCOPED) | 最新 V3 主实施文档 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`；`v3-p04-03-input-storage-preview-v1.0`；只读数据库/文件预览；未访问或修改 TDX | 新增 `StorageGovernance.preview_v3_input_storage()`、原子 JSON 输出及 `docs/V3_P04_03_03_STORAGE_PREVIEW.md`；按交易日保留最近2个已使用 bundle；phase1_cache 2 GiB/90%告警/超预算 fail-closed | V3/M5 定向 `5 passed`；实际预览：物理回执8、数据库catalog5、已使用5、保留2026-09-09/10；解包2026-09-07/08仅预览可再生；cache 18,534 文件/954,775,668 B，占44.46%；无新 cleanup job；原子产物已写出 | 唯一源包全部保护；活动任务引用优先保护；不按mtime删除；metadata按内容hash输出复用组；旧解包没有执行回收；超预算无安全访问顺序时不选候选 | `P04-03-03-A`：3份物理回执不在数据库catalog；解包实际回收、source_files回填、backup对照/调用链仍未执行 | P04-03-04：只读审查backup调用链与现有证据，不执行备份/恢复/移动/删除 |
| P04-03-04 | PASS (SCOPED) | 最新 V3 主实施文档 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`；`v3-p04-03-backup-chain-audit-v1.0`；只读调用链/catalog/物理盘审计；未创建备份或恢复演练 | 修复 `scripts/build_m8_m9_preview.py`：移除每日无条件 `create_history_backup()`；结果声明 `backup_policy=MANUAL_ONLY`；新增 backup 审计测试和阶段报告 | 调用链审计定向 `11 passed`；daily builder 无 `BackupService`/`create_history_backup`；人工 maintenance/recovery/migration 路径仍有确认/维护窗口；只读证据：catalog43、物理文件82、objects目录34、物理数据库14、manifest34 | 已取消新增每日全库备份/演练设计；保留显式人工维护操作；未执行任何备份/恢复/移动/删除 | `P04-03-04-A`：30个catalog历史manifest/object对缺数据库文件；2个物理数据库、4个manifest/object对未登记；需独立逐ID完整性核对，不能自动补登记或删除 | P04-03-05：只读逐ID核对backup catalog与物理database/manifest/object，不执行修改 |
| P04-03-05 | PASS (AUDIT) | 最新 V3 主实施文档 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`；`v3-p04-03-backup-chain-audit-v1.0`；只读逐ID hash/manifest/object核对；未写数据库或文件链 | 新增 `BackupService.audit_catalog_physical_chain()`、`tests/upgrade_v3/test_p04_03_05_backup_chain_audit.py`、`docs/V3_P04_03_05_BACKUP_CHAIN_AUDIT.md`；实际证据 `reports/upgrade_v3/P04-03-05_BACKUP_CHAIN_AUDIT.json` | 定向 `4 passed`；catalog43；完整链12；不完整31；manifest/object catalog链30/30 hash/尺寸通过；物理数据库14、manifest34、objects目录34；孤立数据库2、孤立manifest/object4对 | 只读按 basename 兼容旧绝对路径，不改 catalog；不完整链和 orphan 全部保持原样；未把 `state=VERIFIED` 冒充恢复可用 | `P04-03-05-A`：31条catalog缺数据库文件；4组manifest/object未登记；2个数据库未登记；需分类决策，不得自动删除或补登记 | P04-03-06：只读形成不完整/orphan分类决策清单，不执行删除、补登记或新备份 |
| P04-03-06 | PASS (AUDIT ONLY) | 最新 V3 主实施文档 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`；`v3-p04-03-backup-chain-classification-v1.0`；只读消费 P04-03-05 审计 JSON；未访问或修改 TDX/备份链 | 新增 `BackupService.classify_catalog_physical_chain()`、`tests/upgrade_v3/test_p04_03_06_backup_chain_classification.py`、`docs/V3_P04_03_06_BACKUP_CHAIN_CLASSIFICATION.md`；实际分类 JSON 已生成 | 分类结果：`PROTECTED_EVIDENCE=31`、`MANUAL_RECOVERY_VALIDATION_CANDIDATE=12`、`USER_DECISION_REQUIRED=6`；自动动作 `NONE`；删除权限 `false`；定向 `3 passed` | 缺数据库 catalog 链保留证据；完整链仅可人工恢复验证；孤立对象待用户取舍；未补登记、未备份、未恢复、未移动、未删除 | P04-03-05-A 继续开放；分类清单不授予删除或恢复权限；6个孤立对象需后续来源/固定保留项核对 | 下一步：先对 `USER_DECISION_REQUIRED` 6项做来源/保留项核对；没有明确取舍前不做物理变更 |
| P04-03-07 | PASS (AUDIT ONLY) | 最新 V3 主实施文档 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`；`v3-p04-03-backup-orphan-provenance-v1.0`；只读核对 6 项孤立对象的文件 hash、manifest identity、catalog/storage 交叉关系；未访问或修改 TDX/备份链 | 新增 `BackupService.audit_orphan_provenance()`、`tests/upgrade_v3/test_p04_03_07_backup_orphan_provenance.py`、`docs/V3_P04_03_07_BACKUP_ORPHAN_PROVENANCE.md`；实际产物 `reports/upgrade_v3/P04-03-07_BACKUP_ORPHAN_PROVENANCE.json` | 6/6 覆盖；2 个孤立数据库实际 hash 自洽但 catalog 匹配 0；4 组 manifest identity/hash 与 object hash/尺寸均 PASS，且对象匹配 ACTIVE/referenced storage object；定向 5 passed；删除权限 false | 固定保留建议统一为 `RETAIN_UNTIL_OWNER_CONFIRMED`，不擅自设置天数；未补登记、未备份、未恢复、未移动、未删除；`P04-03-05-A` 与 P04-03-03-A 独立开放 | 6 项仍需 owner/固定保留取舍；P04-03-05-A 的 31 条缺数据库链不能并案；本轮不授予物理变更权限 | 下一步按最新 V3 台账处理未关闭的独立审计项，先读文档确认具体顺序 |

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

## C20-01 追加复验记录（2026-09-12）

| issue_id | old_clause | v3_clause | decision | affected_task | new_contract_id | evidence | status |
|---|---|---|---|---|---|---|---|
| C20-01 | P00-03 仅用日期正则、timestamp 包含 `T`/空格、number 类型判断 | date 必须是真实日历日期；timestamp 必须是带时区的 ISO8601 `T` 格式；number/scalar 数值必须有限 | 采用 V3 条款；不修改配置参数哈希，不批量改写旧数据库时间列 | P00-03 补项 | `research-v3-schema-v1.0` / runtime validation v1 | `src/workbench_service/research_v3_contracts.py`；`tests/upgrade_v3/test_p00_03_contracts.py`；非法日期、无时区/非法 timestamp、NaN/Infinity 反例及合法闰日/+08:00 正例 | PASS |

本补项只关闭 C20-01；P00-03 在最新主文档中涉及的其他复核项不因本次校验器修复而自动放行。下一项仍按台账执行 P04-02-INTEGRATION，未提前进入 P04-03。

## P00–P04 缺陷收口追加记录（2026-09-12）

本追加记录依据当前工作区最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`。不覆盖上方历史阶段行，不修改主实施文档，不启动 P05–P11。

| issue_id | affected_task | 修复/证据 | acceptance | status |
|---|---|---|---|---|
| R19-01 / C20-12 | P00-03 | `research_v3_schema.yaml`、`research_v3_contracts.py` 增加 Ready/NotBuilt/Online context；PageEnvelope 支持 `eligible_total`、旧 `total_eligible` 别名和 context 状态联合校验；P00-03 反例测试 | NOT_BUILT 不伪造 run/snapshot；分页别名不漂移 | PASS |
| P02-03-SCOPE-CACHE | P02-03 | `HierarchyMembershipResolver` cache key 加入 source_scope；不同 namespace 同 revision 隔离测试 | 不发生跨源父成员串读 | PASS |
| P02-04-SOURCE-AMBIGUITY | P02-04 | `publication_binding()` 多 source scope 且未指定 scope 时 fail-closed；多命名空间反例测试 | 不随机选择 source scope | PASS |
| R19-05 / C20-16-FULL-DAY | P04-02-INTEGRATION | `v3_daily_entry.py` 读取旧技术整日结果并重组；`incremental_writer.py` 校验重组键并记录 `reassembled_rows`；缺旧整日来源拒绝 | A 单股修订后新技术 slice 仍含 B；完整目标才能绑定 | PASS |
| P04-03-SOURCE-CATALOG-FUTURE | P04-03-03 | 新增 `source_catalog.py`，M3 输入验收幂等登记 source_files；新增 source catalog 测试 | 后续新 bundle 不再形成空 source_files 记录 | PASS |
| P00-02-STORAGE-AUDIT | P00-02/P04-03 | 新增 source catalog / storage reference 只读审计及原子 JSON 产物 | 物理链与 publication 引用差异可定位；不自动变更 | PASS (AUDIT ONLY) |

本轮回归：`pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7`，170 passed；compileall、diff check 通过。当前生产库只读审计仍保留 3 份未登记物理回执、`source_files=0` 历史存量、storage 引用旗标差异和既有 P04-03-05～07 备份链分类；这些属于需要 owner 决策的独立数据审计项，不以代码测试伪装成已物理修复。

## P04-03-08 旧 M0-M15 产物清理记录（2026-09-12）

本记录依据最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`。按用户授权，仅删除已确认不属于 V3 核心的旧 M0-M15 残留；未触碰 TDX 输入目录，未删除任何 V3 `result-obj-*`、已登记 source bundle、publication 绑定或完整备份链。

| 清理项 | 数量 | 验收 |
|---|---:|---|
| 未登记旧 source bundle 收据目录 | 3 | 已删除；登记源包/提取物保留 |
| `INCOMPLETE` 旧备份链 | 31 | 已删除；清理后 0 条 |
| 孤立旧备份对象组 | 6 | 已删除；数据库/manifest/object 孤立项均为 0 |
| 历史旧 analysis parquet | 1 | 物理文件删除；storage row 为 DELETED |
| V3 结果对象 | 51 | 全部保留 |

清理后 `backup_catalog=12` 且完整链 12/12，source bundle catalog/物理收据为 5/5，V3 fallback binding 为 0。历史 `source_files=0` 是元数据缺口，不是待删除文件，本次未做未经授权的历史回填。旧 analysis 对应的 2 条 `analysis_slices` 身份行保留为 tombstone，因为历史迁移外键仍指向已重命名表；物理对象已删除并完成删除标记。

本次回归 `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7` 为 170 passed，compileall 和 diff check 通过。清理子项验收通过，但 P04-03 整体仍为 scoped/audit 状态，P04 生产集成及独立审计项未全部关闭，下一阶段仍为 P04 剩余收口，不进入 P05。

## P00–P04-02 阶段验收收口（2026-09-12）

依据最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`，本轮完成 P00-01 至 P04-02 的阶段级补验和真实输入副本验证，形成独立记录：[V3_P00_P04_02_FULL_PASS.md](V3_P00_P04_02_FULL_PASS.md)。

修复 `v3_daily_entry.py` 的整文件 parquet 物化缺陷：改用 PyArrow row-group 读取，只把当前任务证券及当前日向前 60 个交易日物化为计算帧。默认 V3 daily target 收窄为已具备 result-object 绑定的 `technical/strength/high/structure/summary/member_state` 六域；旧 `sector_base/sector_cycle/mainline` 只保留兼容条目，显式缺绑定时 fail-closed。

真实 normalized parquet + 生产数据库副本的 P04-02 三次验证：

| run | planned | executed | new_fact_rows | reused_rows | calculated_rows | db_file_growth |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 105,918 | 105,918 | 6,178 | 138,678 | 6,178 | 0 |
| 2 | 105,918 | 105,918 | 0 | 144,856 | 0 | 0 |
| 3 | 105,918 | 105,918 | 0 | 144,856 | 0 | 0 |

本轮阶段级结论：**P00-01～P04-02 FULL_PASS**。这不提前放行 P05–P11，也不把 P08/P09 的后续 UI/在线故障注入、生产运维激活或算法效果验收计入本结论。下一阶段严格进入 P04-03。

最终回归：`pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7` 为 `173 passed`；compileall、diff check 通过。期间发现并修复既有 M7 取消/进度并发状态写入竞态，30 次取消边界压力复验全部通过。

## P04-03-01-B V3 source_files 目录回填（2026-09-12）

依据最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`，执行 P04-03 的首个未关闭 V3 核心缺口：`source_files=0` 历史元数据目录。该缺口属于 V3 源包可复现性，不属于 M0-M15 旧产物。

新增 `backfill_source_file_catalog()` 和 `scripts/backfill_v3_source_file_catalog.py`。脚本只读取已封存的 5 个 V3 source bundle receipt，校验 bundle 身份、package/metadata 目录和既有 catalog；通过原子事务新增 32 条 `source_files` 行，4 个 package 各 8 条；同 package 多 bundle 引用保留 `source_bundle_ids`。任一冲突会整批回滚，未修改源包、解包、metadata、TDX、normalized、cache 或 backup 文件。

定向测试 `pytest -q tests/upgrade_v3/test_p04_03_source_catalog.py` 为 `3 passed`；实际审计显示 `source_bundles=5/5`、物理回执未登记 `0`、catalog 无物理回执 `0`、`source_files=32`、`source_files_catalog_empty=false`。阶段记录见 [V3_P04_03_01_B_SOURCE_CATALOG_RECONCILIATION.md](V3_P04_03_01_B_SOURCE_CATALOG_RECONCILIATION.md)。

本任务只关闭 `P04-03-01-B`；不代表 P04-03 整体完成。下一任务仍按最新 V3 台账处理缓存预览/解包保护和备份链的独立未关闭项，不进入 P05。

历史报告 `V3_P04_03_01_STORAGE_INVENTORY.md` 与 `V3_P04_03_03_STORAGE_PREVIEW.md` 已增加状态说明：其中的 3 份未登记物理回执及 `source_files=0` 是回填前快照，不再代表当前数据库状态；原始数字和审计证据保持不变。

## P04-03-02 真实保留源包恢复复验（2026-09-12）

本条 supersede 原 `P04-03-02 PASS (SCOPED)` 的“仅合成 ZIP/临时目录”范围缺口。依据最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`，对实际保留的 2026-09-10 bundle `fc26948799b1...bb1120` 执行全量 `restore_source_bundle_extraction()`：package SHA/尺寸通过，恢复 `12,404` 个文件、`949,487,072` 字节，与 receipt 完全一致；实际 `sh/lday/sh600001.day`、`sz/lday/sz000001.day` 均存在并完成 SHA 核验。

恢复目标是新建临时目录，验证后只删除本轮新建目录；未修改原始 ZIP、既有 extracted、metadata、TDX、数据库或 backup。错误的合成成员路径先被 resolver 正确 fail-closed，未创建目标目录；改用真实包内成员后通过。阶段证据见 [V3_P04_03_02_REAL_RECOVERY.md](V3_P04_03_02_REAL_RECOVERY.md)。

本任务将 `P04-03-02` 提升为 **PASS（真实输入验证）**。下一任务严格进入 `P04-03-03`，只刷新最近 2 个 bundle 与 `.phase1_cache` 预算预览，不执行删除。

## P04-03-03 真实缓存与解包保留预览（2026-09-12）

本轮按最新 V3 主实施文档 §17.8/§18.7 刷新真实 input storage preview。5/5 source bundle 物理回执与 catalog 对齐，`source_files=32`，活动任务引用 bundle 为 0；按交易日保留 2026-09-09、2026-09-10 两个最近已使用 bundle，2026-09-07/08 解包仅标记 `PREVIEW_RECLAIMABLE_REBUILDABLE`。`.phase1_cache` 为 18,534 文件、954,775,668 B，使用率 44.46%，预算决策 `WITHIN_BUDGET`，无缓存回收候选。

执行前后 `cleanup_jobs` 均为 1，删除执行为 false；未写数据库清理计划，未删除、移动或隔离任何文件。定向测试 `tests/upgrade_v3/test_p04_03_03_storage_preview.py tests/upgrade_m5/test_storage_governance.py` 为 `7 passed`，实际证据见 [V3_P04_03_03_REAL_REFRESH.md](V3_P04_03_03_REAL_REFRESH.md)。

本任务将 `P04-03-03` 提升为 **PASS（只读预览）**。下一任务严格进入 `P04-03-04`：复核 backup 调用链和现有备份证据，仍不执行备份、恢复、移动或删除。

## P04-03-04～08 备份链与旧产物最终收口（2026-09-12）

按用户要求一次性完成 P04-03 剩余审计/收口任务，但每个 task 保留独立合同和结果：

| task_id | status | 实际证据 | 验收结论 | next_task |
|---|---|---|---|---|
| P04-03-04 | PASS | daily builder 无 `BackupService`/`create_history_backup`；人工 recovery/migration 仍有显式维护窗口；定向 2 passed | 不新增每日强制全库备份/恢复演练 | P04-03-05 |
| P04-03-05 | PASS | `backup_catalog=12`；12/12 完整；0 不完整；0 孤立数据库/manifest/object；实际 hash/尺寸审计通过 | catalog 与物理链当前一致 | P04-03-06 |
| P04-03-06 | PASS | `MANUAL_RECOVERY_VALIDATION_CANDIDATE=12`；`PROTECTED_EVIDENCE=0`；`USER_DECISION_REQUIRED=0`；自动动作 NONE | 分类完成，未授予删除或自动恢复权限 | P04-03-07 |
| P04-03-07 | PASS | 孤立来源核对 `items=0`；删除权限 false | 无孤立对象待 owner 决策 | P04-03-08 |
| P04-03-08 | PASS | 旧 M0-M15 残留清理复核：source bundle 5/5、backup chain 12/12、孤立 0；V3 source_files=32 | 仅旧产物清理通过，V3 核心产物保留 | P05-01 |

本轮全回归 `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7` 为 **175 passed**；compileall 与 diff check 通过。未新建备份、未恢复、未移动、未删除；P04-03 阶段结论为 **FULL_PASS**，下一阶段进入 P05，不把生产 daily 运维激活或算法效果验收提前计入。

## P00–P04 源码与产物独立复审（2026-09-12）

本次按最新 V3 主实施文档 SHA-256 `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851` 重新核对源码、当前生产库只读状态和已留存产物。旧 M0–M15 仅在 V3 明确保留兼容语义或作为 V3 基线时采信。

当前放行结论：**BLOCKED**。P00–P03 与 P04-01、P04-03 的现有范围通过；P04-02 不通过。`app.py::run_today` 仍先无条件执行旧 `build_m8_m9_preview.py`，该脚本仍按 domain/date 全量拆分、计算和写入，之后才调用 V3 增量入口。因此 build plan 没有真正控制正式 daily 的前置计算/写入，违反 V3 §18.7 与 C20-16；后置 result-object 复用不能证明已停止旧全量增长。

证据完整性同时未闭合：`V3_P04_02_INTEGRATION.md` 的原结论为 `PASS（SCOPED）` 且明确未执行生产 daily；当前仓库没有 `reports/v3/daily` 目录，三次真实副本运行的 plan/report 原始产物不可复核。历史台账行保留，不回写伪装为当时结论；本追加记录覆盖当前放行状态。

本轮回归 `pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7` 为 `175 passed in 50.54s`；compileall、diff check 通过。生产库只读核对 result objects 51、source bundles 5、source files 32、backup catalog 12。未访问或修改 TDX，未运行生产 daily，未写生产数据库。

详细报告：[V3_P00_P04_SOURCE_ARTIFACT_REAUDIT_20260912.md](V3_P00_P04_SOURCE_ARTIFACT_REAUDIT_20260912.md)。下一任务为 `P04-02-REMEDIATION`；关闭前不得进入 P05 或启动新的 scanner。

## P04-02-REMEDIATION（2026-09-12）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_task |
|---|---|---|---|---|---|---|
| P04-02-REMEDIATION | FULL_PASS（代码与非生产验证） | 最新 V3 §18.7、§20 C20-16；旧 M8/M9 仅作为兼容计算实现，不得先全窗构建 | `app.py`、`scripts/build_m8_m9_preview.py`、`tests/upgrade_v3/test_p04_02_remediation.py` | `run_today` 只启动一次 `--incremental-current`；当前日输入/输出；旧日期 entry 复用；同 snapshot 新 publication 原子重绑；运行时原子生成 daily plan/report；全回归 178 passed | A-P04-02-01/02 关闭；P00–P04 工程门恢复 FULL_PASS；首次生产 daily 仍按运维窗口留存实际产物 | P05-01 |

本修复未运行生产 daily、未写生产数据库、未访问或修改 TDX。真实项目输入的只读 current-day 计算核对成功；首次生产激活证据不冒充本轮已执行。

## P05-01 统一基础特征输入（2026-09-12）

| task_id | status | input_revision | changed_files | test_evidence | product_or_data_evidence | open_issue | next_task |
|---|---|---|---|---|---|---|---|
| P05-01 | FULL_PASS | V3 §4/§6.1/§18.8、C20-02/04/09；主规格 SHA `3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851` | 新增 `research_features.py` 和 P05-01 测试；配置升级为 `research-attention-config-v3.1`，SETUP/RECOVERY 显式要求 liquidity/position | P05-01 手算、NULL、停牌、除权、零波动、缺日、未来输入、turnover basis、high100 共 5 项测试；全回归 183 passed；compileall/diff check PASS | 真实 normalized 最近110主交易日只读核验：679,580 输入行、6,178 输出；READY 5,213、PARTIAL 965；未写生产库 | 未实现五类信号；板块聚合不在本阶段 | P05-02 |

阶段报告：`docs/V3_P05_01_RESEARCH_FEATURES.md`。本阶段未访问或修改 TDX，未启动 scanner，未写生产数据库。

## P05-02 五类独立股票信号（2026-09-12）

| task_id | status | input_revision | changed_files | test_evidence | product_or_data_evidence | open_issue | next_task |
|---|---|---|---|---|---|---|---|
| P05-02 | FULL_PASS | V3 §6.1/§18.8、C20-02；P05-01 PASS；配置 `research-attention-config-v3.1` | 新增 `stock_attention.py`、P05-02 测试；P05-01 增加 previous close/MA 与 prior high 字段 | 信号边界、三值逻辑、流动性、微跌 SETUP、过热、两日破坏、趋势非重点测试；全回归 189 passed；compileall/diff check PASS | 真实 6,178 股票：BREAKOUT 188、SETUP 643、RECOVERY 33、TREND 1,458、STRUCTURE_BREAK 1,514；正/反/缺失均存在 | 仅工程分布，不构成算法效果验收；未生成 P05-03 正式解释分布产物 | P05-03 |

阶段报告：`docs/V3_P05_02_STOCK_ATTENTION.md`。未访问或修改 TDX，未写生产数据库，未调用板块或 shortlist 服务。

## P05-03 信号固定解释与初始分布（2026-09-12）

| task_id | status | stage_contract | evidence | acceptance | next_task |
|---|---|---|---|---|---|
| P05-03 | FULL_PASS | V3 §6.1/§18.8、C20-02；`v3-p05-03-signal-distribution-v1.0`；参数哈希 `61d191…a7173f` | 定向三值/原因/样例测试；全回归 190 passed；最近 110 个主交易日 normalized 只读输入 679,580 行/6,178 证券；五类信号各有 true/false/unknown 计数、首要拒绝/缺失条件、每类三条带 checks 的样例；报告 JSON 原子写入 | 公式与阈值未变；参数重算哈希一致；liquidity/risk 缺失未被静默放行；无命中数量门槛、无效果结论 | P06-01 |

阶段报告：`docs/V3_P05_03_SIGNAL_DISTRIBUTION.md`，机器可复核产物：`reports/upgrade_v3/P05-03_SIGNAL_DISTRIBUTION.json`。未访问或修改 TDX，未写生产数据库，未启动 scanner。

## P06-01 聚合板块特征并计算 CURRENT（2026-09-12）

| task_id | status | stage_contract | evidence | acceptance | next_task |
|---|---|---|---|---|---|
| P06-01 | FULL_PASS | V3 §3.2/§4/§5.1/§18.9；`SECTOR_CURRENT_PREVIEW_1` | 同类型 `m1/b1/rel1/p1` 独立聚合；正式金额 A 仅在 `SECTOR_AMOUNT_COMMON_AGG_V1` 合同匹配时展示；定向 3 passed；真实绑定 publication 2026-09-10 读取成员 75,028 条、报价 6,178 条并原子生成分布报告 | 长期强今天弱不进入；单股集中不豁免；市场覆盖不足时 554 个板块均 UNKNOWN、未发布 CURRENT；无旧 rank/mainline 回接 | P06-02 |

阶段报告：`docs/V3_P06_01_SECTOR_CURRENT.md`，机器可复核产物：`reports/upgrade_v3/P06-01_CURRENT_DISTRIBUTION.json`。未访问或修改 TDX，未写生产数据库，未启动 scanner。

## P06-02 实现 POTENTIAL 三分支（2026-09-12）

| task_id | status | stage_contract | evidence | acceptance | next_task |
|---|---|---|---|---|---|
| P06-02 | FULL_PASS | V3 §5.2/§18.9、C20-15；`SECTOR_POTENTIAL_PREVIEW_1` | `aggregate_early_width` 与三分支纯函数；定向 5 passed；真实只读绑定成员 75,028 条、P05 信号 6,178 条，早期宽度 548/554 板块可计算；报告原子写入 | CURRENT/POTENTIAL 互斥；不读旧 candidate/最终清单；缺风险或共同历史不静默通过；真实分布 true 0、false 554、unknown 0，未调阈值 | P06-03 |

阶段报告：`docs/V3_P06_02_POTENTIAL.md`，机器可复核产物：`reports/upgrade_v3/P06-02_POTENTIAL_DISTRIBUTION.json`。未访问或修改 TDX，未写生产数据库，未启动 scanner。

## P06-03 推进潜在 episode 生命周期（2026-09-12）

| task_id | status | stage_contract | evidence | acceptance | next_task |
|---|---|---|---|---|---|
| P06-03 | FULL_PASS | V3 §5.3/§18.9；`SECTOR_SIGNAL_LIFECYCLE_PREVIEW_1` | `progress_potential_episode` 纯函数；10 主交易日合成序列；定向 4 passed | 5 日到期不滚动、1 日暂停、2 日重置、CURRENT 优先确认、硬失效优先、DATA_GAP 不转失败且未来不回写 | P07-01 |

阶段报告：`docs/V3_P06_03_EPISODE.md`。未访问或修改 TDX，未写生产数据库，未启动 scanner。

## P07-01 计算每个板块的四类成员（2026-09-12）

| task_id | status | stage_contract | evidence | acceptance | next_task |
|---|---|---|---|---|---|
| P07-01 | FULL_PASS | V3 §6.2/§18.10、C20-07；`SECTOR_MEMBER_ROLES_PREVIEW_1` | 角色纯函数；定向 3 passed；真实只读 75,028 成员、6,178 股票信号、554 板块；ALL 75,028、TODAY_LEADER 2,316/522 板块、研究角色 0 | 完整分母先算；TODAY_LEADER 不读 RET20；EXTENDED 事实榜保留但不进研究角色；不从旧龙头补 EARLY；缺失有解释、前三类每板块 cap=5 | P07-02 |

阶段报告：`docs/V3_P07_01_MEMBER_ROLES.md`，机器可复核产物：`reports/upgrade_v3/P07-01_MEMBER_ROLES_DISTRIBUTION.json`。未访问或修改 TDX，未写生产数据库，未启动 scanner。

## P07-02 计算主备选关联与两条短名单（2026-09-12）

| task_id | status | stage_contract | evidence | acceptance | next_task |
|---|---|---|---|---|---|
| P07-02 | FULL_PASS | V3 §6.3/§7/§18.10；`RESEARCH_ASSOCIATION_PREVIEW_1`、`RESEARCH_SHORTLIST_PREVIEW_1` | 关联/短名单纯函数；定向 3 passed；真实 P07-01 绑定输入候选角色 0，安全零候选报告 | LOO 分轨且不删除弱关系；1 主最多 2 备选；CURRENT/EARLY 独立 20 上限与每板块 3 上限；双命中不占提前名额；无旧 association/candidate 读取 | P07-03 |

阶段报告：`docs/V3_P07_02_ASSOCIATION.md`，机器可复核产物：`reports/upgrade_v3/P07-02_ASSOCIATION_DISTRIBUTION.json`。未访问或修改 TDX，未写生产数据库，未启动 scanner。

详细证据见 [V3_P04_03_BACKUP_CLOSURE.md](V3_P04_03_BACKUP_CLOSURE.md)。

## P07-03 研究 run 事务封存与任务合同（2026-09-12）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_task |
|---|---|---|---|---|---|---|
| P07-03 | FULL_PASS（事务封存与任务合同） | V3 §8/§10.4/§18.10；`RESEARCH_RUN_PREVIEW_1`；`BUILD_RESEARCH_V3`；迁移基线保留至 032 | 新增 `research_runs.py`、`research_runs_schema.sql`、P07-03 定向测试和阶段报告；schema 由 Store 显式幂等安装，不改旧迁移序列 | 定向 P07-03+M7 `7 passed`；同 input_key 复用；BUILDING/FAILED 不可见；子表写入与 COMPLETE 同一事务；中途失败回滚；全回归 `209 passed in 76.13s`；compileall/diff check PASS | 事务封存、输入幂等、失败隔离和任务输入合同通过；未写生产库、未访问或修改 TDX、未激活生产研究 worker | P08-01 |

阶段报告：[V3_P07_03_RESEARCH_RUN.md](V3_P07_03_RESEARCH_RUN.md)。本阶段不把未执行的生产 job、完整 builder 或正式 GET 研究 API 冒充为已完成证据；P08 读取端仍必须只消费 `COMPLETE` run。

## P08-01 本地研究 API 与上下文（2026-09-12）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_task |
|---|---|---|---|---|---|---|
| P08-01 | FULL_PASS（只读 API 与上下文合同） | V3 §10/§18.11；`RESEARCH_V3_API_PREVIEW_1`；只消费 COMPLETE run | 新增 `research_context.py`、`research_queries.py`、P08-01 测试与阶段报告；`app.py` 接入 `/api/v3` 本地 context/home/sectors/members/shortlist/stocks/evidence/signals/search 路由 | 定向 `4 passed`；NOT_BUILT HTTP smoke 不创建 run 表/不触发构建；合成 COMPLETE run 验证列表、成员、短名单、总数/分页和错误边界；全回归 `213 passed in 57.93s`；compileall/diff check PASS | GET 不启动构建；未完成 run 不可见；total 非页长；未知 context/非法参数 fail-closed；未访问或修改 TDX、未写生产数据库 | P08-02 |

阶段报告：[V3_P08_01_RESEARCH_API.md](V3_P08_01_RESEARCH_API.md)。生产环境尚无真实 COMPLETE run，NOT_BUILT/EMPTY 为当前真实安全状态；本阶段不提前宣称首页 UI 或真实效果验收。

## P08-02 首页双栏与板块详情成员（2026-09-12）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_task |
|---|---|---|---|---|---|---|
| P08-02 | FULL_PASS（双轨本地研究预览） | V3 §10/§18.11；`/v3` 独立本地预览；只读 P08-01 API | 新增 `static/research-v3.html`、`/v3` 路由和 P08-02 UI 测试；旧 `/`、`/v2`、旧 API 保留 | 定向 `2 passed`；CURRENT/POTENTIAL 各最多 6 卡、每卡最多 3 成员；卡片点击默认角色；成员分页/空态；AbortController+序列号防迟到覆盖；HTTP smoke 200；Node JS syntax PASS；全回归 `215 passed in 59.24s` | 双轨首页路径、板块右侧成员详情、窄屏布局、EMPTY/NOT_BUILT/UNAVAILABLE 和请求取消边界通过；未写生产库、未访问或修改 TDX | P08-03 |

阶段报告：[V3_P08_02_RESEARCH_UI.md](V3_P08_02_RESEARCH_UI.md)。当前真实环境无 COMPLETE research run，页面保持安全空态；本阶段未提前执行 P08-03。

## P08-03 全局双清单、个股详情与旧入口兼容（2026-09-12）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_task |
|---|---|---|---|---|---|---|
| P08-03 | FULL_PASS（清单、个股证据与兼容入口） | V3 §10/§18.11；`CURRENT_FOCUS`/`EARLY_FOCUS`；证据分节按需读取；旧 candidate 入口保留 | 扩展 `research_queries.py` 个股绑定详情；扩展 `research-v3.html` 全局双清单、个股 modal、证据分节；旧 v2 标题改为“全部结构候选”；新增 P08-03 测试 | 定向 `6 passed`；清单各 20/页、个股角色/清单绑定、selection/risk/sectors/technical 分节；旧 `/api/candidates` 保留；Node syntax PASS；全回归 `217 passed in 78.21s`；compileall/diff check PASS | 清单、个股详情、等待/失效信息、证据按需加载和旧入口兼容通过；未写生产库、未访问或修改 TDX | P09-01 |

阶段报告：[V3_P08_03_RESEARCH_DETAIL.md](V3_P08_03_RESEARCH_DETAIL.md)。P08 已完成；真实环境无 COMPLETE research run，NOT_BUILT/EMPTY 是当前安全结果，下一阶段只做 P09-01 公开来源能力核验。

## P05–P08 审计修复最终收口（2026-09-12）

| audit_item | status | stage_contract | evidence | acceptance | next_task |
|---|---|---|---|---|---|
| P05-P08-REMEDIATION | FULL_PASS | 最新 V3 §4–10、§18.8–11、§20；`RESEARCH_FEATURES_PREVIEW_1`→`RESEARCH_RUN_PREVIEW_1`→`RESEARCH_V3_API_PREVIEW_1` | 修正 dq5_3=q5[t]-q5[t-3]；完整 W 共同成员分支；完整 builder 与 `BUILD_RESEARCH_V3` job；正式库 COMPLETE run `research-5369ba9e65074cf599bbea230e24ff7b`；真实 `/v3` READY 页面；全库 998 passed | P05–P08 合同、源码、真实产物、API/UI 及回归门全部通过；零命中保持可解释空态，未调阈值凑数 | P09-01 |

本条 supersede P06-01/P06-02/P07-03/P08-02/P08-03 旧报告中已披露的范围缺口，但保留旧记录作为历史审计轨迹。详细证据：[V3_P05_P08_REMEDIATION_FULL_PASS_20260912.md](V3_P05_P08_REMEDIATION_FULL_PASS_20260912.md)。

## P09-01-A 公开来源静态登记（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_task |
|---|---|---|---|---|---|---|
| P09-01-A | FULL_PASS（静态登记范围） | 最新 V3 §19.3–§19.4、§20.6；`V3_ONLINE_SOURCE_REGISTRY_1`；最新主文档 SHA `3395AE28…137851` | 新增 `config/online_source_registry_v3.json`、`scripts/verify_p09_01_source_registry.py`、P09-01-A 定向测试、阶段报告和机器回执 | EXT01–EXT11 端点/字段线索登记；七池语义登记；请求边界与热榜零持久化策略校验；网络请求 0 次；未访问或修改 TDX、未写生产数据库 | 静态合同、已知 host、七池、字段待确认项和 fail-closed 状态全部通过；不把 STATIC 证据冒充当前可用能力 | P09-01-B |

阶段报告：[V3_P09_01_SOURCE_REGISTRY.md](V3_P09_01_SOURCE_REGISTRY.md)，机器回执：`reports/upgrade_v3/P09-01-A_SOURCE_REGISTRY.json`。P09-01-B 当前复测作为独立开放项，不由本小任务提前关闭。

## P09-01-B-EXT11 东方财富报价当前复测（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_task |
|---|---|---|---|---|---|---|
| P09-01-B-EXT11 | BLOCKED（当前复测源端断开） | V3 §19.3–§19.4、§20.6；`V3_ONLINE_SOURCE_REGISTRY_1`；EXT11 当前复测合同 | 新增 `scripts/probe_p09_01_b_ext11.py`、定向测试和阶段报告；复用既有 `eastmoney_quotes.py`，未修改适配器 | 有界请求 1 次；`RemoteDisconnected`；未形成当前响应；原始载荷/规范化行未持久化；未访问或修改 TDX、未写生产数据库 | EXT11 当前能力保持 `NOT_VERIFIED`；观察性展示和严格 `TIMESTAMPED_RANK` 均不放行；源端失败不转为空数据 | P09-01-B-EXT11-RETRY |

阶段报告：[V3_P09_01_B_EXT11_CURRENT_PROBE.md](V3_P09_01_B_EXT11_CURRENT_PROBE.md)，机器回执：`reports/upgrade_v3/P09-01-B-EXT11_CURRENT_PROBE.json`。EXT01–EXT10 当前复测仍未关闭；EXT11 需人工重试后才可继续逐源复测。

## P09-01-B-EXT11-RETRY 重试结果（2026-09-13）

| task_id | status | stage_contract | evidence | acceptance | next_task |
|---|---|---|---|---|---|
| P09-01-B-EXT11-RETRY | BLOCKED | 同一 `V3_ONLINE_SOURCE_REGISTRY_1`、V3 §19.3–§19.4/§20.6；单源 8 秒、零重试、2,000,000 bytes 上限 | 再次执行 `scripts/probe_p09_01_b_ext11.py`；源端仍 `RemoteDisconnected`，未取得 HTTP/JSON；回执原始载荷/规范化行均未落盘 | `CURRENT_PROBE` 仍未形成；EXT11 保持 `NOT_VERIFIED`，不放行观察性展示或 `TIMESTAMPED_RANK` | P09-01-B-EXT11-RETRY |

本次重试仍未进入 EXT01；下一次必须人工启动，不能通过重复失败自动推进阶段。

## P09 来源裁决：EXT11 目标版退役、前置解除（2026-09-13）

| task_id | source_id | contract_version | request_template | probe_time | coverage | normalized_fields | capability | page/API入口 | acceptance/failure | next_task |
|---|---|---|---|---|---|---|---|---|---|---|
| P09-SOURCE-DECISION-EXT11 | EXT11 | 历史 `V3_ONLINE_SOURCE_REGISTRY_1`；目标版裁决 `§22.1/§22.2` | 不再调用 `push2.eastmoney.com`；保留旧 URL 仅作历史解释 | 2026-09-13 | 不适用于龙字诀主链 | 不进入 EXT01–09 数据层 | `RETIRED_FROM_TARGET_CHAIN`；旧 BLOCKED 事实保留 | 不接入新 API/UI | EXT11 仅影响旧热榜报价附加/盘中报价候选，不是情绪、涨停、题材、简图或热榜名次输入；不再重试，不以其失败阻断 P09 | P09-01-B-LZ-EXT01 |

该裁决不改写旧 EXT11 BLOCKED 记录，只解除其对新龙字诀主链的前置依赖。

## P09-01-B-LZ-EXT01 同花顺涨停池当前复测（2026-09-13）

| task_id | source_id | contract_version | request_template | probe_time | coverage | normalized_fields | capability | page/API入口 | acceptance/failure | next_task |
|---|---|---|---|---|---|---|---|---|---|---|
| P09-01-B-LZ-EXT01 | EXT01 | `v3-lz-ext01-limit-up-v1.0` | `https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page={page}&limit={limit}&field={fields}&filter=HS,GEM2STAR&order_field=330323&order_type=0&date={YYYYMMDD}` | `2026-09-12T17:28:09.676051+00:00` | HTTP 200；`$.data.info` 当前页 40 行；`page=1/limit=50`，完整分页不宣称 | `code/name/latest/change_rate/amount/order_amount/currency_value/turnover_rate/open_num/reason_type/first_limit_up_time/last_limit_up_time`，另有 6 个附加字段；倍率/单位待重复样本 | `DEGRADED`；当前证据足以进入 EXT01 数据层准备，UI 仍禁用 | 本任务不接 API/UI；目标入口为后续 `/api/v3/limit-up/ladder` | `CURRENT_PROBE` 通过；金额单位、时间转换和完整分页仍未固定；raw/规范化行不落盘 | P09-02-EXT01-DATA-LAYER |

阶段报告：[V3_P09_01_B_LZ_EXT01_CURRENT_PROBE.md](V3_P09_01_B_LZ_EXT01_CURRENT_PROBE.md)，机器回执：`reports/upgrade_v3/P09-01-B-LZ-EXT01_CURRENT_PROBE.json`。本条不改写旧 EXT11 BLOCKED 记录。

## P09-02-A-EXT01 事件头与成员 DTO（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_task |
|---|---|---|---|---|---|---|
| P09-02-A-EXT01 | FULL_PASS（DTO/适配器范围） | 最新 V3 §8.3、§19.4、§22.3；`v3-online-event-dto-v1.0`；主文档 SHA `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` | 新增 `src/workbench_online/event_models.py`、定向测试、离线验证脚本、阶段报告；扩展在线包导出 | 合成合法响应验证 `EventHeader` 与 `EventPoolRow` 分离、EXT01 行路径、命名空间、0 时间转 NULL、未确认倍率留 NULL、封板率/炸板率分离；网络 0 次，raw/规范化行/生产表 0，未改 TDX/本地 run | DTO/适配器合同通过；源能力仍 `DEGRADED`，未放行分页完整性、字段倍率、生产存储或 API/UI | P09-02-B-EXT01-BATCH-READ |

阶段报告：[V3_P09_02_A_EXT01_EVENT_DTO.md](V3_P09_02_A_EXT01_EVENT_DTO.md)，机器回执：`reports/upgrade_v3/P09-02-A-EXT01_EVENT_DTO.json`。本条只关闭 DTO/适配器小范围，不提前关闭 P09-02 数据层。

## P09-02-B-EXT01 有界批次读取（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_task |
|---|---|---|---|---|---|---|
| P09-02-B-EXT01 | FULL_PASS（批次读取合同范围） | 最新 V3 §8.3、§19.4–§19.5、§22.3；`v3-lz-ext01-batch-read-v1.0`；主文档 SHA `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` | 新增 `src/workbench_online/event_batch.py`、定向测试、离线验证脚本、阶段报告；扩展在线包导出 | 合成多页响应验证 page size≤20、最多4页、同批去重、冲突质量码、完整分页、后页失败降级、首页失败 `UNAVAILABLE`；实际网络 0 次；仅内存 DTO/哈希证据，raw/body/数据库/本地 run/TDX 均未写 | 批次读取合同通过；源能力仍 `DEGRADED`，不放行生产存储、API/UI或全市场覆盖声明 | P09-02-C-EXT01-CLOSE-BATCH-STORE |

阶段报告：[V3_P09_02_B_EXT01_BATCH_READ.md](V3_P09_02_B_EXT01_BATCH_READ.md)，机器回执：`reports/upgrade_v3/P09-02-B-EXT01_BATCH_READ.json`。本条只关闭有界内存读取，不提前关闭 P09-02 生产数据层。

## P09-02-C-EXT01 收盘事件批次存储结构（2026-09-13）

| task_id | source_id | contract_version | request_template | probe_time | coverage | normalized_fields | capability | 页面/API入口 | 验收/失败 | next_task |
|---|---|---|---|---|---|---|---|---|---|---|
| P09-02-C-EXT01 | EXT01 | `v3-online-event-storage-v1.0`；迁移 `033_v3_online_events` | 不发网络请求；复用已验证 EXT01 batch_id 作为结构绑定 | 2026-09-13 | 临时内存 DuckDB；仅验证结构，不宣称线上覆盖 | `online_event_header` 独立保存 counts/rates/scope；`online_pool_entries` 含 price/amount/seal_amount/ret1/turnover/float_market_cap/open_count/last_break_time/source_reason/source_fields/quality_codes | `DEGRADED`；结构可供收盘事件归档，生产应用未放行 | 本任务无页面/API；后续事件 API 另行验收 | `FULL_PASS`：迁移和字段验收通过；真实生产库未应用，raw/热榜/本地 run/TDX均未写 | P09-02-D-EXT01-CLOSE-BATCH-WRITER |

阶段报告：[V3_P09_02_C_EXT01_CLOSE_BATCH_STORE.md](V3_P09_02_C_EXT01_CLOSE_BATCH_STORE.md)，机器回执：`reports/upgrade_v3/P09-02-C-EXT01_CLOSE_BATCH_STORE.json`。本条只关闭收盘事件结构，不提前关闭批次写入或 P09-03 产品切片。

## P09-02-D-EXT01 收盘批次事务写入（2026-09-13）

| task_id | source_id | contract_version | request_template | probe_time | coverage | normalized_fields | capability | 页面/API入口 | 验收/失败 | next_task |
|---|---|---|---|---|---|---|---|---|---|---|
| P09-02-D-EXT01 | EXT01 | `v3-online-event-storage-v1.0`；迁移 `033_v3_online_events` | 不发网络请求；接收已通过 `v3-lz-ext01-batch-read-v1.0` 的完整内存批次 | 2026-09-13 | 临时内存 DuckDB；完整分页批次 1 页、1 行；不宣称线上全市场覆盖 | `online_fetch_runs/online_batches` 元数据；`online_event_bundles`；独立 `online_event_header`；`online_pool_entries` 及来源字段/质量码；未知金额/倍率仍 NULL | `DEGRADED`；收盘批次可归档，UI/API 未放行 | 本任务无页面/API；后续 `P09-03-EXT01-LADDER-SLICE` | `FULL_PASS`：事务提交、重复幂等、部分批次拒绝、异常回滚均通过；raw/热榜/生产库/本地 run/TDX 未写 | P09-03-EXT01-LADDER-SLICE |

阶段报告：[V3_P09_02_D_EXT01_CLOSE_BATCH_WRITER.md](V3_P09_02_D_EXT01_CLOSE_BATCH_WRITER.md)，机器回执：`reports/upgrade_v3/P09-02-D-EXT01_CLOSE_BATCH_WRITER.json`。本条只关闭收盘批次写入，不提前关闭 P09-03 产品切片。

## P09-03-EXT01 在线涨停简图产品切片（2026-09-13）

| task_id | source_id | contract_version | request_template | probe_time | coverage | normalized_fields | capability | 页面/API入口 | 验收/失败 | next_task |
|---|---|---|---|---|---|---|---|---|---|---|
| P09-03-EXT01 | EXT01 | `v3-events-ladder-api-v1.0`；适配 `v3-online-event-dto-v1.0` | 只读已归档 batch；API 查询不发上游网络请求 | 2026-09-13 | 临时内存 DuckDB 合成完整批次；API 先 total 后分页；线上无批次时显式 `UNAVAILABLE` | header counts/rates/scope 独立；成员保留 security_id/source_code、price、amount、seal_amount、ret1、turnover、float_market_cap、open_count、首末封、source_reason、quality_codes；连续板与 M 天 N 板分列 | `DEGRADED`；产品切片代码/API/页面可预览，EXT01 未确认字段仍空态 | `GET /api/v3/events/ladder`；`/v3/events` | `FULL_PASS`：默认/首封排序、分页、9天5板不算5连板、空态和 HTTP 页面入口通过；网络/生产库/raw/本地 run/TDX 未写 | P09-03-EXT01-LADDER-EVIDENCE |

阶段报告：[V3_P09_03_EXT01_LADDER_SLICE.md](V3_P09_03_EXT01_LADDER_SLICE.md)，机器回执：`reports/upgrade_v3/P09-03-EXT01-LADDER-SLICE.json`。本条只关闭 EXT01 涨停简图切片，不提前关闭其它在线页面。

## P09-03-EXT01-LADDER-EVIDENCE 单股事件证据下钻（2026-09-13）

| task_id | source_id | contract_version | request_template | probe_time | coverage | normalized_fields | capability | 页面/API入口 | 验收/失败 | next_task |
|---|---|---|---|---|---|---|---|---|---|---|
| P09-03-EXT01-LADDER-EVIDENCE | EXT01 | `v3-events-ladder-evidence-v1.0` | 只读已归档 `event_bundle_id`；`GET /api/v3/events/ladder/{security_id}`；不发上游网络请求 | 2026-09-13 | 临时 DuckDB 合成已归档批次；按规范 security_id/source_code 单股查询；无批次/无成员显式空态 | 来源字段映射、字段状态、`observed_at`、`source_as_of`、`source_time.basis`、bundle/batch/pool 身份、质量码；未确认倍率保留 NULL/UNCONFIRMED | `DEGRADED`；单股证据 API 和列表证据弹窗可预览；不宣称逐股成交时间 | `GET /api/v3/events/ladder/{security_id}`；`/v3/events` 行级“证据”弹窗 | `FULL_PASS`：来源时间、字段映射、单股下钻、source_code 别名、缺失成员 `UNAVAILABLE`、raw 禁止和页面入口通过；网络/生产库/本地 run/TDX 未写 | P09-03-EXT01-EVIDENCE-UI-REGRESSION |

阶段报告：[V3_P09_03_EXT01_LADDER_EVIDENCE.md](V3_P09_03_EXT01_LADDER_EVIDENCE.md)，机器回执：`reports/upgrade_v3/P09-03-EXT01-LADDER-EVIDENCE.json`。本条只关闭来源证据与单股下钻合同，不提前关闭其它在线页面或 EXT02–09。

## P09-03-EXT01-EVIDENCE-UI-REGRESSION 来源证据弹窗回归（2026-09-13）

| task_id | source_id | contract_version | request_template | probe_time | coverage | normalized_fields | capability | 页面/API入口 | 验收/失败 | next_task |
|---|---|---|---|---|---|---|---|---|---|---|
| P09-03-EXT01-EVIDENCE-UI-REGRESSION | EXT01 | `v3-events-evidence-ui-regression-v1.0` | 临时 DuckDB 页面回归；证据详情沿用 `GET /api/v3/events/ladder/{security_id}`；无上游请求 | 2026-09-13 | 合成有批次/无批次页面；列表 20 条页上限和 API 分页状态；真实浏览器交互检查 | `observed_at/source_as_of/source_time`、字段证据映射、UNCONFIRMED、空态、modal identity/focus | `DEGRADED`；证据弹窗预览可用；源能力和生产放行不变 | `/v3/events`；行级“查看”；`GET /api/v3/events/ladder/{security_id}` | `FULL_PASS`：来源时间/字段证据可见，内容点击不关闭，Esc/X关闭并回焦，空批次显式 `UNAVAILABLE`，分页状态保留；网络/生产库/raw/本地 run/TDX 未写 | P09-03-EXT01-CLOSE-OUT |

阶段报告：[V3_P09_03_EXT01_EVIDENCE_UI_REGRESSION.md](V3_P09_03_EXT01_EVIDENCE_UI_REGRESSION.md)，机器回执：`reports/upgrade_v3/P09-03-EXT01-EVIDENCE-UI-REGRESSION.json`。本条只关闭 EXT01 证据弹窗回归，不提前关闭其它在线页面或整体 P09。

## P09-03-EXT01-CLOSE-OUT 简图/证据链阶段收口（2026-09-13）

| task_id | source_id | contract_version | request_template | probe_time | coverage | normalized_fields | capability | 页面/API入口 | 验收/失败 | next_task |
|---|---|---|---|---|---|---|---|---|---|---|
| P09-03-EXT01-CLOSE-OUT | EXT01 | `v3-p09-ext01-slice-close-out-v1.0`；汇总 `v3-events-ladder-v1.0` / `v3-events-ladder-evidence-v1.0` / `v3-events-evidence-ui-regression-v1.0` | 只读汇总已有阶段回执；不发上游请求 | 2026-09-13 | EXT01 `LIMIT_POOL_UP` 收盘批次；单页当前证据和临时合成覆盖；不宣称全市场 | 事件 DTO、批次身份、header counts/rates/scope、梯队高度、来源字段证据、观察时间/源截止时间、空态/质量码 | `DEGRADED_PASS`；工程链 `FULL_PASS`，产品仅预览，`release_ready=false` | `/v3/events`；`GET /api/v3/events/ladder`；`GET /api/v3/events/ladder/{security_id}` | `DEGRADED_PASS`：EXT01 简图/证据链独立闭环；单页、字段倍率、source_as_of缺失和其它 EXT02–09/页面/盘中报价缺口明确保留；网络/生产库/raw/本地 run/TDX 未写 | P09-01-B-LZ-EXT02-CURRENT-PROBE |

阶段报告：[V3_P09_03_EXT01_CLOSE_OUT.md](V3_P09_03_EXT01_CLOSE_OUT.md)，机器回执：`reports/upgrade_v3/P09-03-EXT01-CLOSE-OUT.json`。本条关闭 EXT01 切片边界记录，不关闭整体 P09、未完成在线源或生产放行。

## P09 剩余在线产品一次性推进（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_task |
|---|---|---|---|---|---|---|
| P09-REMAINING-PRODUCTS | FULL_PASS（工程链）；DEGRADED_PASS（真实源能力） | 最新 V3 §18.12、§19.3–§19.5、§20.8、§22.2；`v3-p09-online-products-v1.0`；主文档 SHA `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` | `src/workbench_online/p09_products.py`；`src/workbench_service/app.py`；`src/workbench_service/static/online-p09-v3.html`；P09 测试/探测/验证脚本 | `P09-01-B-REMAINING-CURRENT-PROBE.json`；`P09-REMAINING-PRODUCTS.json`；定向 9 passed；既有 P09/M14/M7 回归 47 passed；`git diff --check`；EXT02/03/04/05/07/08/09 当前可解析，EXT06 明确 UNAVAILABLE | EXT02–09 均有版本化适配器、独立状态、限时并发、API/页面入口和零 raw/row/batch 持久化；按 §22.2 不将 EXT06 失败伪称整体 FULL_PASS，本地链路不受阻断 | P09-INDEPENDENT-AUDIT |

阶段报告：[V3_P09_REMAINING_PRODUCTS.md](V3_P09_REMAINING_PRODUCTS.md)，机器回执：`reports/upgrade_v3/P09-REMAINING-PRODUCTS.json`。EXT11 按 V3 §22 退役，不作为剩余任务前置。

## P09 独立审计与直接修复（2026-09-13）

| audit_item | status | scope | findings_and_repairs | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P09-INDEPENDENT-AUDIT | FULL_PASS | 反查 V3 哈希、EXT02–09 路由/页面、预算、零持久化、EXT11 退役边界、探测/阶段回执和 TDX 只读 | 首轮发现在线总览页缺少自链接和分布显式入口；已直接补齐 `/v3/online` 自链接及“查看分布数据”入口，无其他高危发现 | `reports/upgrade_v3/P09-INDEPENDENT-AUDIT-20260913.json`；`docs/V3_P09_INDEPENDENT_AUDIT_20260913.md`；审计后路由/产品测试 9 passed；验证脚本与审计脚本均 FULL_PASS | 独立审计 0 findings；P09 工程链保持 FULL_PASS，真实源状态仍按数据集为 DEGRADED_PASS；未修改 TDX、生产库或本地 run | P09-CLOSE-OUT |

## P09 总收口（2026-09-13）

| task_id | status | stage_contract | evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| P09-CLOSE-OUT | DEGRADED_PASS（工程链 FULL_PASS） | `v3-p09-close-out-v1.0`；V3 §18.12、§19.5、§20.8、§22.2；主文档 SHA `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` | `reports/upgrade_v3/P09-CLOSE-OUT-20260913.json`；`docs/V3_P09_CLOSE_OUT_20260913.md`；51 项 P09/M14/M7 定向回归通过；独立审计 0 findings；`git diff --check` | P09 工程实现和审计达到 FULL_PASS；EXT02/03/04/05/07/08/09 当前可解析，EXT06 明确 UNAVAILABLE、EXT01 保持 DEGRADED，故按 §22.2 真实源总体 DEGRADED_PASS；未改 TDX、生产库和本地 run | P10-01 |

## P09 当前复审问题单（2026-09-13，保留以上历史结论）

| audit_item | scope | evidence | acceptance | next_stage |
|---|---|---|---|---|
| P09-AUD-01/02 | 逐数据集能力门；题材全量有界响应先聚合后分页 | `config/p09_runtime_capabilities_v1.json`；`src/workbench_online/p09_products.py`；P09 反例测试 | 已修复，禁用门零网络请求；47 行题材成员计数正确 | P09-REAUDIT-CURRENT |
| P09-AUD-03 | EXT03/04 题材到本地板块关系及成员交集 | `config/p09_topic_sector_mapping_v1.json`；`src/workbench_service/p09_context.py`；`tests/upgrade_v3/test_p09_context_mapping.py` | 工程路径已实现，当前无经审阅映射，真实交集保持 UNAVAILABLE；独立问题未关闭 | P09-MAPPING-EVIDENCE |
| P09-AUD-04 | 七池、四榜、题材成员、分布、板块与话题页面 | `src/workbench_service/static/online-p09-v3.html`；P09 路由测试；JS 语法检查 | 已补来源行、选择、分页与详情；页面当前能力仍按源覆盖降级 | P09-UI-REGRESSION |
| P09-AUD-05 | 来源截止时间、交易日及完整分页 | `reports/upgrade_v3/P09-SOURCE-METADATA-PROBE-20260913.json`；`src/workbench_online/p09_products.py` | EXT03 `manual_updated_at`、EXT02 日期已证实；EXT02/EXT09 后页探测为空。其它源截止时间和全市场分页仍 UNKNOWN；独立问题未关闭 | P09-SOURCE-COVERAGE |
| P09-AUD-06 | 复审合同与历史回执隔离 | `scripts/audit_p09_v3.py`；`reports/upgrade_v3/P09-REAUDIT-CURRENT-20260913.json` | 当前复审按证据门为 DEGRADED_PASS，不覆盖历史 0 findings 回执 | P09-MAPPING-COVERAGE-UI-REPAIR |

## P09 G09 当前受限通过（2026-09-13）

| task_id | contract | evidence | acceptance | next_stage |
|---|---|---|---|---|
| P09-G09-CURRENT-CLOSE-OUT | `v3-p09-g09-current-close-out-v1.0`；V3 §19.5、§20.8、§22.3 | `reports/upgrade_v3/P09-TOPIC-SECTOR-MAPPING-20260913.json`、`P09-REAUDIT-CURRENT-20260913.json`、`P09-G09-CURRENT-CLOSE-OUT-20260913.json`；`docs/V3_P09_G09_CURRENT_CLOSE_OUT_20260913.md`；155 P09/M14/M7 tests passed | `DEGRADED_PASS`，工程审计 0 findings；两条日期/run/哈希绑定 RELATED 关系验证通过，来源时间/完整分页/晋级分母/金额仍显式 UNKNOWN；旧回执不改写，`release_ready=false` | P10-01；P09 受限源切片继续跟踪 |

### 2026-09-13 P09 龙字诀反查修复与 G09 总收口

- 合同：V3 §18.12、§19.3–19.5、§20.8、§22.2–22.3、C20-10/C20-11；主文档 SHA-256 `52536035f82d4754eda13241181f2aa8563b9d37e280e2ae39bfbd3a5a6c9d5b`。
- 实现：按龙字诀字节码恢复 EXT01 数字字段码/200 行完整分页、高度语义，修复 EXT06 日期参数，接入题材金额估算和 EXT05 昨日涨停晋级转移；EXT02–09 当前有界复测全部 AVAILABLE。
- 验收：P09 复审 `FULL_PASS`/0 findings，G09 `FULL_PASS`/`release_ready=true`；V3+M14+M7 共 302 项通过，JS/Python/diff 检查通过。
- 产物：`docs/V3_P09_FULL_PASS_CLOSE_OUT_20260913.md`、`reports/upgrade_v3/P09-REAUDIT-CURRENT-20260913.json`、`reports/upgrade_v3/P09-G09-CURRENT-CLOSE-OUT-20260913.json`、`reports/upgrade_v3/P09-01-B-REMAINING-REPROBE-20260913.json`。
- 下一阶段：P10-01；严格同步逐股盘中报价和新增本地映射作为独立增强暂缓。

## P10-01 旧功能去留矩阵（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P10-01 | FULL_PASS | `v3-p10-legacy-feature-matrix-v1.0`；V3 §2、§18.13、§20.3–§20.8；主文档 SHA `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` | `src/workbench_service/legacy_feature_matrix.py`；`src/workbench_service/app.py`；`src/workbench_service/static/research-v3.html`；`src/workbench_service/static/v2/index.html`；`src/workbench_service/static/v2/app.js`；`tests/upgrade_v3/test_p10_01_legacy_matrix.py` | `reports/upgrade_v3/P10-01-LEGACY-MATRIX.json`；定向 `4 passed`；矩阵 API smoke 200/19 行；只读测试库未创建 `research_runs`；Node syntax/compileall/diff check PASS | §2 19 行均有明确处置、V3 新入口、旧兼容/API 查询或显式排除/后置证据；旧入口未删除；主线/代表/结构候选语义已显式改标；未写 TDX、生产库或本地研究 run；不宣称效果验证 | P10-02 |

## P10-02 集合筛选和跨页关联（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P10-02 | FULL_PASS | `V3_P10_SECTOR_SET_LINKAGE_V1_0`；旧 API14 `M11_SECTOR_INTERSECTION_V1_0`；V3 §12、§18.13、§20.3–§20.8；主文档 SHA 运行时读取并写入机器回执 | `src/workbench_service/intersection.py`；`src/workbench_service/app.py`；`src/workbench_service/static/v2/index.html`；`src/workbench_service/static/v2/app.js`；`src/workbench_service/static/v2/router.js`；`src/workbench_service/static/v2/api.js`；`src/workbench_service/static/research-v3.html`；`tests/upgrade_v3/test_p10_02_sector_set_linkage.py` | `reports/upgrade_v3/P10-02-SECTOR-SET-LINKAGE.json`；定向 `4 passed`；P10-02 验证脚本 `FULL_PASS`；M11/API 与 P08 定向 `11 passed`；Node syntax PASS；生产 DB size/mtime 不变 | 名称选择 2–4 板块、API14 集合→角色→分页、旧请求形状兼容、主/备板块 context 回返和证据关闭后选择保持均有实现/证据；没有 READY context 时不伪造角色；未写 TDX、生产数据库或 research run；不宣称前瞻效果 | P10-03 |

## P10-03 前瞻结果与简单基线（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P10-03 | FULL_PASS | `V3_P10_SIGNAL_EVALUATION_V1_0`；`EVAL_VERSION=V3_P10_SIGNAL_EVALUATION_V1_0`；V3 §8.2、§14.1–§14.2、§18.13、§20.3–§20.8；主文档 SHA 由机器回执运行时读取 | `src/workbench_service/research_signal_evaluation.py`；`src/workbench_service/research_builder.py`；`src/workbench_service/research_queries.py`；`src/workbench_service/app.py`；`src/workbench_db/research_runs_schema.sql`；`src/workbench_db/migrations/034_v3_signal_outcomes.sql`；`src/workbench_db/migrations.py`；`src/workbench_service/static/research-v3.html`；`tests/upgrade_v3/test_p10_03_signal_evaluation.py`；`scripts/verify_p10_03_signal_evaluation.py` | `reports/upgrade_v3/P10-03-SIGNAL-EVALUATION.json`；阶段脚本 `FULL_PASS`；定向 `9 passed`；V3 `217 passed`；M15/M14/M7 `122 passed`；Node/compileall/diff check PASS；生产 DB size/mtime 不变 | PENDING、OBSERVED、DATA_GAP、3/5 日 CURRENT 确认、固定成员复权收益、三组同日等量基线、未来字段不改信号 hash、重复 episode 不重复计样本、outcome 幂等且不更新信号行均有证据；真实库 1 个 COMPLETE run、0 个封存 episode，效果门槛未达到，页面保持“规则观察·效果验证中”，不声称效果通过 | P11-01 |

## P11-01 Overall acceptance and growth audit (2026-09-13)

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-01 | DEGRADED_PASS | `V3_P11_FINAL_ACCEPTANCE_V1_0`; V3 §15、§17.12、§18.14 P11-01、§20.3–§20.8; spec SHA `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` | `scripts/verify_p11_01_final_acceptance.py`; `docs/V3_P11_01_FINAL_ACCEPTANCE_20260913.md`; `reports/upgrade_v3/P11-01-FINAL-ACCEPTANCE.json`; `docs/V3_IMPLEMENTATION_LEDGER.md` | 23 section-15 counterexamples registered and executed; `tests/upgrade_v3 + tests/upgrade_m7 + tests/upgrade_m14 + tests/upgrade_m15`: `339 passed`; five local API categories each 30 warm samples; home JSON 583 bytes; latest back-to-back track switch 270.246ms; slow-source fail-closed probe; production DB read-only and size/mtime unchanged | Functionality `FULL_PASS`; data correctness `FULL_PASS`; performance `FULL_PASS`; storage `DEGRADED_PASS`; same-input memory repeat added 0 business facts, 0 identity/log rows, and 0 duplicate physical content; P00-to-current growth is inventoried, not attributed or recovered; PIT `PARTIAL`, source `FULL_PASS` with deferred enhancements, effect `EFFECT_OBSERVATION_PENDING`; main entry not switched | P11-02 |

## P11-02 停旧写证明与精确回收预览（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-02 | DEGRADED_PASS | `V3_P11_OLD_WRITE_RECOVERY_PREVIEW_V1_0`；V3 §17.8、§17.9、§18.14 P11-02；spec SHA `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` | `scripts/verify_p11_02_old_write_and_recovery_preview.py`; `tests/upgrade_v3/test_p11_02_old_write_recovery_preview.py`; `docs/V3_P11_02_OLD_WRITE_RECOVERY_PREVIEW_20260913.md`; `reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json`; `docs/V3_IMPLEMENTATION_LEDGER.md` | 六个首轮迁移域旧 writer 非定义调用点 0；逐 slice 等价全部通过；最新发布旧读 API、relation resolver、14/14 迁移域 binding 可读；backup 12/12 完整、孤立 0；extraction/cache/runtime 精确对象预览；生产 DB read-only size/mtime 不变 | 功能/旧读/六域数据等价/停旧写 `FULL_PASS`；存储 `DEGRADED_PASS`：17 个 stale referenced flags、1 个 deleted tombstone path 和 2 个辅助旧写点作为独立开放审计；当前回收 0 B，无删除/移动/备份/恢复 | P11-03 |

阶段报告：[V3_P11_02_OLD_WRITE_RECOVERY_PREVIEW_20260913.md](V3_P11_02_OLD_WRITE_RECOVERY_PREVIEW_20260913.md)，机器回执：`reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json`。独立问题 `P11-02-AUD-STORAGE-01` 与 `P11-02-AUD-AUXILIARY-WRITES-01` 保持开放；P11-03 执行前必须取得明确回收范围授权，否则仅登记 `WAITING_DECISION`。

## P11-03 精确回收范围等待决策登记（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-03 | DEGRADED_PASS（`WAITING_DECISION`） | `V3_P11_RECOVERY_WAITING_DECISION_V1_0`；V3 §18.14 P11-03；spec SHA `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` | `scripts/verify_p11_03_recovery_waiting_decision.py`；`tests/upgrade_v3/test_p11_03_recovery_waiting_decision.py`；`docs/V3_P11_03_RECOVERY_WAITING_DECISION_20260913.md`；`reports/upgrade_v3/P11-03-RECOVERY-WAITING-DECISION.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | 逐对象登记 4 关系旧副本表、6 首轮迁移旧结果表、7 辅助结果表、4 解包目录、4 metadata、4 source package、1 cache、16 backup 对象、77 runtime 文件；生产 DB read-only size/mtime 不变；TDX/cleanup/backup/restore 未访问 | 决策登记 `FULL_PASS`；物理回收 `NOT_AUTHORIZED`，实际回收 `0 B`；两个 P11-02 独立审计保持 OPEN；未删除、移动、VACUUM 或切换新主入口 | P11-04（等待存储审计、停增长门和明确范围授权） |

阶段报告：[V3_P11_03_RECOVERY_WAITING_DECISION_20260913.md](V3_P11_03_RECOVERY_WAITING_DECISION_20260913.md)，机器回执：`reports/upgrade_v3/P11-03-RECOVERY-WAITING-DECISION.json`。本条只完成精确对象登记，不将预览估算写成已回收空间；P11-04 不得在前置门未满足时切换新主入口。

## P11-03 已授权回收执行（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-03-RECOVERY-EXECUTION | FULL_PASS（后置复核） | `V3_P11_AUTHORIZED_RECOVERY_EXECUTION_V1_0`；V3 §17.9、§18.14 P11-03；用户明确授权固定路径范围 | `scripts/execute_p11_03_authorized_recovery.py`；`scripts/verify_p11_03_recovery_execution.py`；`docs/V3_P11_03_RECOVERY_EXECUTION_20260913.md`；`reports/upgrade_v3/P11-03-RECOVERY-EXECUTION-20260913.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | 2 个可重建解包目录、`data/backups` 下 16 个对象、1 个 runtime restore-drill 备份，共 19 个精确对象；按对象字节 `25,295,015,262 B`；后置目标全不存在、source package 保留、生产 DB size/mtime 不变 | 授权范围已执行；数据库表、TDX、source、metadata、cache、其余 runtime 未动；未执行 VACUUM/新备份；首轮回执误报已由独立只读后置复核纠正 | P11-04（等待存储止增长门、独立审计及新备份策略） |

阶段报告：[V3_P11_03_RECOVERY_EXECUTION_20260913.md](V3_P11_03_RECOVERY_EXECUTION_20260913.md)，机器回执：`reports/upgrade_v3/P11-03-RECOVERY-EXECUTION-20260913.json`。本条记录实际删除对象；P11-02 两项独立审计不因回收自动关闭。

## P11-03 旧表保留决策（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-03-OLD-TABLE-RETENTION | FULL_PASS | `V3_P11_OLD_TABLE_RETENTION_DECISION_V1_0`；V3 §17.9、§18.14 P11-03；用户明确要求 V3 和旧页面迁移完成前保留旧表 | `scripts/record_p11_03_old_table_retention_decision.py`；`docs/V3_P11_03_OLD_TABLE_RETENTION_DECISION_20260913.md`；`reports/upgrade_v3/P11-03-OLD-TABLE-RETENTION-DECISION-20260913.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | 17 张旧/关系/辅助表逐表登记保留；生产 DB size/mtime 不变；未删除表、未 VACUUM、未访问或修改 TDX | `RETAIN_ALL_LEGACY_TABLES`；仅在 V3 开发完成、旧页面功能迁移完成、逐表引用/兼容回归和新授权完成后重新判断 | V3_COMPLETION_AND_UI_MIGRATION_GATE |

阶段报告：[V3_P11_03_OLD_TABLE_RETENTION_DECISION_20260913.md](V3_P11_03_OLD_TABLE_RETENTION_DECISION_20260913.md)，机器回执：`reports/upgrade_v3/P11-03-OLD-TABLE-RETENTION-DECISION-20260913.json`。本条冻结旧表清理，后续必须逐表重新裁决。

## P11-02-AUD-AUXILIARY-WRITES-01 辅助旧写入边界关闭（2026-09-13）

| audit_item | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-02-AUD-AUXILIARY-WRITES-01 | FULL_PASS（有界保留） | `V3_P11_AUXILIARY_LEGACY_WRITER_BOUNDARY_V1_0`；V3 §17.8、§18.14 P11-02；旧表按用户决定保留 | `scripts/audit_p11_auxiliary_legacy_writer_boundary.py`；`tests/upgrade_v3/test_p11_auxiliary_writer_boundary.py`；`docs/V3_P11_02_AUXILIARY_WRITER_BOUNDARY_20260913.md`；`reports/upgrade_v3/P11-02-AUD-AUXILIARY-WRITES-BOUNDARY-20260913.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | 两个辅助 writer 各 1 个明确调用点；membership changes 有 slice immutable guard；association 为手工 snapshot 事务 builder；当前 daily 入口不调用手工 association builder；生产 DB read-only | `RESOLVED_WITH_BOUNDED_LEGACY_WRITER_BOUNDARY`；未迁移/未删除旧表；writer 不执行目标表 update/delete/drop/truncate；旧表清理仍等待 V3 和旧页面迁移完成 | P11-04（仍等待 P11-02-AUD-STORAGE-01 与 P11-01 存储门） |

阶段报告：[V3_P11_02_AUXILIARY_WRITER_BOUNDARY_20260913.md](V3_P11_02_AUXILIARY_WRITER_BOUNDARY_20260913.md)，机器回执：`reports/upgrade_v3/P11-02-AUD-AUXILIARY-WRITES-BOUNDARY-20260913.json`。本条只关闭辅助 writer 边界审计，不关闭旧表保留决策或 storage reference audit。

## P11-02-AUD-STORAGE-01 存储引用图独立审计关闭（2026-09-13）

| audit_item | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-02-AUD-STORAGE-01 | FULL_PASS（只读对账，无自动动作） | `V3_P11_STORAGE_REFERENCE_GRAPH_AUDIT_V1_0`；V3 §17.8、§17.9、§18.14 P11-02；主文档 SHA 由机器回执记录 | `scripts/audit_p11_storage_reference_graph.py`；`tests/upgrade_v3/test_p11_storage_reference_graph.py`；`docs/V3_P11_02_STORAGE_REFERENCE_GRAPH_AUDIT_20260913.md`；`reports/upgrade_v3/P11-02-AUD-STORAGE-REFERENCE-GRAPH-20260913.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | 52/52 catalog rows 完成逐对象分类；34 个当前 publication 引用、17 个 stale flag 全部有历史 analysis slice provenance；active job/lease 与 online payload 引用均为 0；deleted tombstone 缺失物理文件证据闭合；生产 DB read-only size/mtime 不变 | `RESOLVED_AS_CURRENT_OR_HISTORICAL_REFERENCE_NO_AUTO_ACTION`；不清标、不删 `storage_objects`、不删物理文件；P11-01 存储止增长门仍独立存在 | P11-01 存储止增长门；满足后 P11-04 |

阶段报告：[V3_P11_02_STORAGE_REFERENCE_GRAPH_AUDIT_20260913.md](V3_P11_02_STORAGE_REFERENCE_GRAPH_AUDIT_20260913.md)，机器回执：`reports/upgrade_v3/P11-02-AUD-STORAGE-REFERENCE-GRAPH-20260913.json`。本条关闭的是逐对象引用解释审计，不授权清除保护标志或删除旧表。

## P11-01 存储止增长门（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-01-STORAGE-STOP-GROWTH-GATE | FULL_PASS | `V3_P11_STORAGE_STOP_GROWTH_GATE_V1_0`；V3 §17.8、§17.9、§18.14 P11-01/P11-04；主文档 SHA 由机器回执记录 | `scripts/verify_p11_01_storage_stop_growth.py`；`tests/upgrade_v3/test_p11_storage_stop_growth.py`；`docs/V3_P11_01_STORAGE_STOP_GROWTH_GATE_20260913.md`；`reports/upgrade_v3/P11-01-STORAGE-STOP-GROWTH-GATE-20260913.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | 同输入幂等、六域停旧写、辅助 writer 有界、52/52 storage 引用对账、P11-03 回收/旧表保留回执和当前入口均交叉核对通过；生产 DB size/mtime 不变 | 存储止增长门 `FULL_PASS`；无物理回收、无旧表删除；当前 `/v2` 未切换，P11-04 入口变更仍为独立动作 | P11-04 |

阶段报告：[V3_P11_01_STORAGE_STOP_GROWTH_GATE_20260913.md](V3_P11_01_STORAGE_STOP_GROWTH_GATE_20260913.md)，机器回执：`reports/upgrade_v3/P11-01-STORAGE-STOP-GROWTH-GATE-20260913.json`。本条只关闭止增长门，不改变 P11-01 初始联合验收状态，也不自动执行 P11-04 入口切换。

## P11-04 主入口交接预检（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-04-PREFLIGHT | FULL_PASS | `V3_P11_HANDOFF_PREFLIGHT_V1_0`；V3 §18.14 P11-04、§20.3–§20.8；主文档 SHA 由机器回执记录 | `scripts/verify_p11_04_handoff_preflight.py`；`tests/upgrade_v3/test_p11_04_handoff_preflight.py`；`docs/V3_P11_04_HANDOFF_PREFLIGHT_20260913.md`；`reports/upgrade_v3/P11-04-HANDOFF-PREFLIGHT-20260913.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | P11-01 存储门、P10-01/P10-02、P10-03 诚实状态、P09 在线卡片、V3/在线/旧回退路由及启动脚本全部核对；入口 JSON 前后字节不变 | `READY_FOR_EXPLICIT_P11_04_SWITCH`；当前默认仍 `/v2`，目标 `/v3`；未修改 runtime entry、启动脚本、生产库或 TDX | P11-04 独立入口切换与 post-switch smoke（需明确确认） |

阶段报告：[V3_P11_04_HANDOFF_PREFLIGHT_20260913.md](V3_P11_04_HANDOFF_PREFLIGHT_20260913.md)，机器回执：`reports/upgrade_v3/P11-04-HANDOFF-PREFLIGHT-20260913.json`。预检不等于入口已切换；需独立确认后才执行默认入口变更。

## P11-04 V3 主入口交接（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-04 | FULL_PASS | `V3_P11_ENTRY_HANDOFF_V1_0`；V3 §18.14 P11-04、§20.3–§20.8；主文档 SHA 由机器回执记录 | `OPEN_UNIFIED_WORKBENCH.cmd`；`runtime/workbench_entry.json`；`docs/DAILY_OPERATION_GUIDE.md`；`scripts/verify_p11_04_entry_handoff.py`；`tests/upgrade_v3/test_p11_04_entry_handoff.py`；`docs/V3_P11_04_ENTRY_HANDOFF_20260913.md`；`reports/upgrade_v3/P11-04-ENTRY-HANDOFF-20260913.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | 默认入口从 `/v2` 切至 `/v3`；V3、在线页、旧 `/view` 回退、context READY、home 及生产发布日 GET smoke 通过；生产 DB size/mtime 不变 | `switch_executed=true`；V3 本地双轨+已验证在线页成为默认入口；旧回退保留；未写生产 DB、未访问/修改 TDX、未删旧表 | V3 日常运行与 P10-03 效果观察；旧表迁移完成后逐表再裁决 |

阶段报告：[V3_P11_04_ENTRY_HANDOFF_20260913.md](V3_P11_04_ENTRY_HANDOFF_20260913.md)，机器回执：`reports/upgrade_v3/P11-04-ENTRY-HANDOFF-20260913.json`。P11-04 关闭本版工程入口交接，不改变 P10-03 效果观察和旧表保留门槛。

## P11 交接后日常预检（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-POST-HANDOFF-DAILY-PREFLIGHT | FULL_PASS | `V3_P11_POST_HANDOFF_DAILY_PREFLIGHT_V1_0`；V3 §18.14 P11-04、§20.3–§20.8；主文档 SHA 由机器回执记录 | `scripts/record_p11_post_handoff_daily_preflight.py`；`tests/upgrade_v3/test_p11_post_handoff_daily_preflight.py`；`docs/V3_P11_POST_HANDOFF_DAILY_PREFLIGHT_20260913.md`；`reports/upgrade_v3/P11-POST-HANDOFF-DAILY-PREFLIGHT-20260913.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | P11-04 默认入口 `/v3`、`/view` 回退、dry-run 输入、截止日、本地文件计数、锁释放和生产 DB size/mtime 均核对通过 | `DRY_RUN_READY`；只证明本地输入可用于日常运行，不等于真实生产发布；未写生产 DB/TDX、未提交 job、未发在线请求 | `V3_DAILY_OPERATION_AND_P10_03_EFFECT_OBSERVATION` |

阶段报告：[V3_P11_POST_HANDOFF_DAILY_PREFLIGHT_20260913.md](V3_P11_POST_HANDOFF_DAILY_PREFLIGHT_20260913.md)，机器回执：`reports/upgrade_v3/P11-POST-HANDOFF-DAILY-PREFLIGHT-20260913.json`。本条不把 dry-run 记为发布成功；P10-03 效果观察和旧表保留门槛不变。

## P11 首次真实日常运行（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-DAILY-OPERATION | FULL_PASS | `V3_P11_DAILY_OPERATION_V1_0`；V3 §18.14 P11-04、§20.3–§20.8；主文档 SHA 由机器回执记录 | `scripts/verify_p11_daily_operation.py`；`tests/upgrade_v3/test_p11_daily_operation.py`；`docs/V3_P11_DAILY_OPERATION_20260913.md`；`reports/upgrade_v3/P11-DAILY-OPERATION-20260913.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | 真实 `latest` 运行 `NEW_DAILY_FORWARD_CAPTURE`；V1 release `fd6a4cbce2fb43e7b722b30f70b3989f` 成功；2026-09-10 observation/release 绑定；940 条新增 outcome；TDX 只读；描述性评估 3 个封存日且明确 `DATA_INSUFFICIENT` | 真实日常发布链 9/9 完成；不把 forward 描述性评估当作 P10-03 效果通过；未做概率声明、未使用合成日期、未删旧表 | `V3_DAILY_OPERATION_AND_P10_03_EFFECT_OBSERVATION` |

阶段报告：[V3_P11_DAILY_OPERATION_20260913.md](V3_P11_DAILY_OPERATION_20260913.md)，机器回执：`reports/upgrade_v3/P11-DAILY-OPERATION-20260913.json`。本条关闭首次真实日常运行记录，不关闭 P10-03 效果门或旧表保留门。

## P11 V3 日增量激活（2026-09-13）

| task_id | status | stage_contract | changed_files | evidence | acceptance | next_stage |
|---|---|---|---|---|---|---|
| P11-V3-DAILY-ACTIVATION | FULL_PASS（独立后置复核） | `V3_P11_DAILY_ACTIVATION_POSTCONDITION_V1_0`；V3 §18.7 P04-02、§18.14 P11-04、§20.3–§20.8；主文档 SHA 由阶段环境读取 | `scripts/run_p11_v3_daily_activation.py`；`scripts/verify_p11_v3_daily_activation_postcondition.py`；`tests/upgrade_v3/test_p11_v3_daily_activation.py`；`docs/V3_P11_V3_DAILY_ACTIVATION_20260913.md`；`reports/upgrade_v3/P11-V3-DAILY-ACTIVATION-20260913.json`；`docs/V3_IMPLEMENTATION_LEDGER.md` | 外层回执初报由排序/字段回填断言造成；独立只读复核确认 writer `BUILT`；104579 个逻辑 task 合并为 6 个执行对象；technical 5932 行计算；其它五域显式复用；当前 publication 已绑定 `v3-daily-be2675d7622085d213ab9984`；DB growth 0 | V3 日增量入口真实闭环，后置复核 FULL_PASS；不重复执行 writer、不创造新交易日、不宣称 P10-03 效果通过、不删旧表 | `V3_DAILY_OPERATION_AND_P10_03_EFFECT_OBSERVATION` |

阶段报告：[V3_P11_V3_DAILY_ACTIVATION_20260913.md](V3_P11_V3_DAILY_ACTIVATION_20260913.md)，机器回执：`reports/upgrade_v3/P11-V3-DAILY-ACTIVATION-20260913.json`。本条关闭 V3 日增量激活，不改变效果观察和旧表保留门槛。

## P11 V3 snapshot 历史引用兼容修复（2026-09-13）

| audit_item | status | stage_contract | scope/evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| P11-V3-SNAPSHOT-COMPATIBILITY-REPAIR | FULL_PASS | `V3_P11_SNAPSHOT_COMPATIBILITY_REPAIR_V1_0`；V3 §18.7、§18.14、§20.3–§20.8 | 新激活 snapshot 初始 32 条 target-domain 引用、source snapshot 40 条；发现 technical/strength/high/member_state 旧日期共 8 条缺口；只读校验冲突 0，补入既有 immutable slice 引用 8 条，当前绑定恢复 40 条 | 旧日期 V3 查询引用完整；不重算业务行、不删旧 snapshot、不删旧表、不访问/修改 TDX；外层初报问题与修复独立留痕 | `V3_DAILY_OPERATION_AND_P10_03_EFFECT_OBSERVATION` |

阶段报告：`docs/V3_P11_V3_DAILY_ACTIVATION_20260913.md`，机器回执：`reports/upgrade_v3/P11-V3-SNAPSHOT-COMPATIBILITY-REPAIR-20260913.json`。本条为跨切换兼容审计项，不改变 P10-03 效果门和旧表保留决定。

## V3 最终研究清单与板块阶段展示（2026-09-14）

| audit_item | status | stage_contract | scope/evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| V3-FINAL-CANDIDATES-AND-PHASE-VISIBILITY | DEGRADED_PASS | `FINAL_LOCAL_RESEARCH_CANDIDATES_V1`；`sector_daily`既有版本化结构阶段合同 | 最终清单只纳入A+/A且主板块为INDUSTRY/THEME，按本地综合分排序并硬限100；页面改为25行分页列表，增加价格、涨幅、成交额、RPS20、综合分、结构和板块；板块卡片显示企稳/再加速/主升强势 | 2026-09-11原结构候选1071只，合格且最终入选69只，STYLE主板块0只；玻璃当前强势卡同步显示`STABILIZATION/企稳`；单日重建后的多日主线553条保持`DATA_INSUFFICIENT` | 连续真实交易日积累后验收退潮、持续、扩散等多日生命周期 |

首页后续复核曾增加“板块生命周期 · 前瞻与风险”区域；产品复核确认其直接复用`/api/mainlines`，与“板块研究/中期主线背景”重复，现已删除首页副本。“提前观察”入口保留并明确为早期启动/结构突破观察，因为它来自V3潜在转强合同，并列出板块扩散/蓄势/回暖与个股SETUP/BREAKOUT/RECOVERY证据。

阶段报告：[V3_FINAL_CANDIDATE_AND_PHASE_REVIEW_20260914.md](V3_FINAL_CANDIDATE_AND_PHASE_REVIEW_20260914.md)。本条不以单日数据伪造多日主线阶段。

## V3 本地服务托盘与控制入口（2026-09-14）

| audit_item | status | stage_contract | scope/evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| V3-LOCAL-SERVICE-TRAY-CONTROL | FULL_PASS | `WORKBENCH_LOCAL_SERVICE_CONTROL_V1` | 新增Windows通知区托盘、单实例、3秒状态刷新、启动/停止/受控重启/打开页面/退出；运维中心顶部增加服务控制；状态接口返回PID；停止接口复用CSRF和维护门 | PowerShell语法、Python编译、7项定向测试与diff check通过；未访问或修改TDX，未改生产数据 | 日常由`OPEN_UNIFIED_WORKBENCH.cmd`统一启动托盘与服务 |

阶段报告：[V3_LOCAL_SERVICE_TRAY_AND_CONTROL_20260914.md](V3_LOCAL_SERVICE_TRAY_AND_CONTROL_20260914.md)。

## V3 在线最近交易日与实时热榜修复（2026-09-14）

| audit_item | status | stage_contract | scope/evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| V3-ONLINE-LATEST-TRADE-DATE-AND-REALTIME-RANK | DEGRADED_PASS | `V3_ONLINE_LATEST_TRADE_DATE_V1` | 日期型在线模块由 EXT03/EXT02 确认最近交易日，与本地发布日解耦；个股热度四榜保持无日期参数的请求时实时模式；删除页面“龙字诀/龙字决”可见命名 | 2026-09-14 两来源确认当天；V3 页面显示在线14日、本地11日；四榜AVAILABLE；服务重启后PID 58216；定向测试通过 | 独立补齐 EXT01 当日在线涨停来源能力 |

阶段报告：[V3_ONLINE_LATEST_TRADE_DATE_20260914.md](V3_ONLINE_LATEST_TRADE_DATE_20260914.md)。EXT01 当日归档不可用时保持空态，因此本阶段为 `DEGRADED_PASS`，没有用旧交易日冒充。

## V3 当前强势类型与成员展示修复（2026-09-14）

| audit_item | status | stage_contract | scope/evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| V3-CURRENT-TYPE-MEMBER-DISPLAY | DEGRADED_PASS | `SECTOR_CURRENT_PREVIEW_2_TYPE_SCOPED`；`RESEARCH_SHORTLIST_PREVIEW_2_CONFIGURED_CAP`；`RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE` | CURRENT 增加 INDUSTRY/THEME 硬门；成员接口绑定 technical/strength 快照并按 ret1、amount、security_id 排序；页面表格显示价格、涨幅、成交额、20日涨幅、研究角色及三档表现标签；清单每板块上限从硬编码3改为合同配置；相关测试通过 | 2026-09-11 新 run `research-465514ce8678405a8e1e36a328cf05cc` COMPLETE；CURRENT 从玻璃/昨日较强/昨成交20 修正为仅玻璃；玻璃6只 CURRENT_RESEARCH 全部进入当前关注；V1/V3 候选均来自 `/api/candidates`，总池1071、分页展示 | 连续真实交易日继续验收 CURRENT/POTENTIAL 稳定性 |

## P12-02 因子与历史输入阶段验收（2026-09-15）

| task_id | status | stage_contract | evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| P12-02 | DEGRADED_PASS | `P12-02_FACTOR_V3_3_ACCEPTANCE_V1`；V3 v2.1 §5、§7、§9.2、§19；候选实现 `TODAY_RESEARCH_FACTOR_V3_3_CANDIDATE_01`、`PULLBACK_EPISODE_V1_CANDIDATE_01` | `docs/P12_02_FACTOR_V3_3_ACCEPTANCE_20260915.md`；`reports/p12_02/p12_02_stage_gate.json`；三日期各6,182股因子重放、风险分组、31项相关回归、真实换锚、RPS可比门、源码可恢复与依赖锁探针 | 候选因子/事件公式及边界通过；旧P05配置未消费项已列明；历史GBBQ/universe只可重构诊断，正式历史RPS及生产bundle未通过；170日未物化 | P12-03_SCANNER_V3_3 |

## P12-03 扫描器阶段验收（2026-09-15）

| task_id | status | stage_contract | evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| P12-03 | DEGRADED_PASS | `P12-03_SCANNER_V3_3_ACCEPTANCE_V1`；候选实现`TODAY_RESEARCH_SCANNER_V3_3_CANDIDATE_01`；V3 v2.1 §8、§9、§19 | `docs/P12_03_SCANNER_V3_3_ACCEPTANCE_20260915.md`；`reports/p12_03/current_funnel.json`；`reports/p12_03/p12_03_stage_gate.json`；33项P12-02/03相关回归 | 四类三值资格、逐谓词解释、延续STOCK_ONLY及SETUP_WATCH通过；6,182股漏斗回合；历史种子、正式RPS变化和P12-04 LOO缺口未补TRUE；未发布、未物化 | P12-04_RANK_AND_LOO_V3_3 |

## P12-04 排名与LOO阶段验收（2026-09-15）

| task_id | status | stage_contract | evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| P12-04 | DEGRADED_PASS | `P12-04_RANK_AND_LOO_V3_3_ACCEPTANCE_V1`；`TODAY_RESEARCH_RANK_AND_LOO_V3_3_CANDIDATE_01`；V3 v2.1 §10–§12、§19 | `docs/P12_04_RANK_AND_LOO_V3_3_ACCEPTANCE_20260915.md`；`reports/p12_04/current_loo_probe.json`、`current_rank_probe.json`、`p12_04_stage_gate.json`；7项定向反例 | 52,028关系边、5,578股今日LOO；113只唯一合格、9已评分、104未评分保留；延续140 STOCK_ONLY/9正式；简单排序同样本；历史变化LOO保持UNKNOWN | P12-05_REPLAY_V3_3 |

## P12-05 诊断回放进行中（2026-09-15）

| task_id | status | stage_contract | evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| P12-05-REPLAY-PILOT | DEGRADED_PASS_PARTIAL | `P12-05_REPLAY_V3_3_DIAGNOSTIC_V1`；`HORIZON_END_TDX_AFFINE_QFQ_V1` | `docs/P12_05_REPLAY_PROGRESS_20260915.md`；`reports/p12_05/replay_evaluation.json`；3日472个诊断信号、1,888个期限行、逻辑重跑哈希一致 | 3月/6月共1,460条OBSERVED；9月428条NOT_DUE；当前成员重构身份明确；四组等量基线与消融未完成，P12-05未验收 | P12-05_BASELINES_AND_ABLATION |

## P12-05 回放阶段验收（2026-09-15）

| task_id | status | stage_contract | evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| P12-05 | DEGRADED_PASS | `P12-05_REPLAY_V3_3_ACCEPTANCE_V1`；`HORIZON_END_TDX_AFFINE_QFQ_V1` | `docs/P12_05_REPLAY_V3_3_ACCEPTANCE_20260915.md`；`reports/p12_05/replay_evaluation.json`、`p12_05_stage_gate.json` | 三日期四组等量基线；3,736期限行；e锚、DATA_GAP/NOT_DUE、LOO/位置/Freshness消融通过；当前成员重构；效果保持PENDING | P12-06_BUNDLE_V3_3 |

## P12-06 完整候选包阶段验收（2026-09-15）

| task_id | status | stage_contract | evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| P12-06 | DEGRADED_PASS | `P12-06_BUNDLE_V3_3_ACCEPTANCE_V1`；`TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_01` | `docs/P12_06_BUNDLE_V3_3_ACCEPTANCE_20260915.md`；`reports/p12_06/candidate_bundle_receipt.json`、`p12_06_stage_gate.json`；4项bundle反例 | 113行不可变包、完整身份、摘要验证、同输入复用、失败前旧指针保留、生产DB不变；独立指针未切UI；P12逻辑run未冒充旧DB run | P12-07_UI_V3_3 |
| P12-07 | DEGRADED_PASS（V3.3 首页与只读包 API） | `TODAY_RESEARCH_V3_3_API_01`；P12-06 完整包；V3 今日研究升级文档 §15–§17、P12-07 | `src/workbench_service/today_research_bundle.py`；`src/workbench_service/app.py`；`src/workbench_service/static/v2/index.html`；`src/workbench_service/static/v2/v3-unified.js`；`src/workbench_service/static/research-v3.html`；`tests/upgrade_v3/test_p12_07_today_research_ui.py` | `reports/p12_07/p12_07_stage_gate.json`；定向 8 passed；桌面与 390×844 实查；API 113 条、25/页、详情同 digest；V3 全量 268 passed/17 failed（16 个既有回执缺失，1 个外部旧服务） | 首页只展示通过完整性校验的 P12-06 活动包，缺失/篡改 fail closed，不回退旧候选；日期和效果待验明确；未写生产库或 TDX；文件运行尚未进入新版数据库注册表 | P12-08 |
| P12-08 | DEGRADED_PASS（工程完成，效果待验） | `TODAY_RESEARCH_FORWARD_V3_3_CANDIDATE_02`；V3 今日研究升级文档 §10.4、§17、P12-08 | `src/workbench_analysis/forward_v3_3.py`；`scripts/run_p12_08_forward_observation.py`；`tests/upgrade_v3/test_p12_08_forward_v3_3.py`；`docs/P12_08_FORWARD_V3_3_ACCEPTANCE_20260915.md` | 首轮不可变日观测；P12-07/08 定向 9 passed；compileall、diff check通过 | 首轮1/20真实信号日且episode身份缺失；该缺口由P12-08A新合同补全，旧观测未覆盖；历史回放不计数；效果审计保持开启 | P12-08A episode身份补全 |
| P12-08A | DEGRADED_PASS（episode身份补全，效果待验） | `TODAY_RESEARCH_FORWARD_V3_3_CANDIDATE_03`；升级文档 §9.5、§17.1、§17.2 | `docs/P12_08A_EPISODE_IDENTITY_ACCEPTANCE_20260915.md`；`src/workbench_analysis/forward_v3_3.py`；`scripts/run_p12_08_forward_observation.py`；`tests/upgrade_v3/test_p12_08_forward_v3_3.py` | `reports/p12_08/p12_08_stage_gate.json`、`forward_report.json`；P12-07/08定向10 passed；同输入摘要复用 | 113/113候选具稳定episode身份；连续复用、类别变化/重入换号；1/20真实日仍不足；同日相关性保留按日期分组；盘中无新收盘数据，不伪造第二日 | 新收盘bundle后封存下一真实日；满20日后独立评价 |
| P12-08B | DEGRADED_PASS（后验计划完成，结果未到期） | `TODAY_RESEARCH_FORWARD_OUTCOME_V3_3_CANDIDATE_01`；`HORIZON_END_TDX_AFFINE_QFQ_V1`；升级文档 §17.1 | `docs/P12_08B_FORWARD_OUTCOME_PLAN_ACCEPTANCE_20260915.md`；`src/workbench_analysis/forward_outcome_v3_3.py`；`scripts/run_p12_08b_outcome_plan.py`；`tests/upgrade_v3/test_p12_08b_forward_outcome.py` | `reports/p12_08/outcome_plan.json`、`p12_08b_stage_gate.json`；P12-07/08/08B定向14 passed；compileall、diff check通过 | 113 episode×4期限=452；全部NOT_DUE；到期未物化显式DUE_UNMATERIALIZED；不生成盘中收益、不填0、不写生产DB/TDX | 新真实收盘日先封存观测；期限到期后按e锚物化评价revision |
| P12-08C | DEGRADED_PASS（物化引擎完成，真实结果未到期） | `TODAY_RESEARCH_FORWARD_OUTCOME_MATERIALIZED_V3_3_CANDIDATE_01`；`HORIZON_END_TDX_AFFINE_QFQ_V1`；升级文档 §17.1 | `docs/P12_08C_OUTCOME_MATERIALIZATION_ACCEPTANCE_20260915.md`；`src/workbench_analysis/forward_outcome_materializer_v3_3.py`；`scripts/run_p12_08c_outcome_materialization.py`；`tests/upgrade_v3/test_p12_08c_outcome_materializer.py` | `reports/p12_08/outcome_results.json`、`p12_08c_stage_gate.json`；P12定向17 passed；送股e锚和缺数反例；compileall、diff check通过 | 真实452 NOT_DUE、0 OBSERVED；合成送股FRET=0/MFE=10%/MAE=-10%；缺数DATA_GAP不填0；未消费真实评价源或写DB/TDX | 新收盘日封存；到期后冻结源并物化新revision |
| P12-08D | DEGRADED_PASS（报告维度补全，可用项冻结） | `TODAY_RESEARCH_FORWARD_V3_3_CANDIDATE_04`；`FORWARD_EPISODE_ID_V1`；升级文档 §17.2 | `docs/P12_08D_REPORTING_DIMENSIONS_ACCEPTANCE_20260915.md`；`src/workbench_analysis/forward_v3_3.py`；`tests/upgrade_v3/test_p12_08_forward_v3_3.py` | `reports/p12_08/forward_report.json`及下游计划/结果；P12定向18 passed；compileall、diff check通过 | LIQ20及行业/概念关系113/113；重叠107单类/6双类；持续期已记录；市场强弱、波动0/113明确UNAVAILABLE；旧观测不覆盖 | 新收盘日按同合同封存；上游缺失维度另立bundle版本 |
| P12-08E | DEGRADED_PASS（上游报告维度完整） | `TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_02`；`TODAY_RESEARCH_REPORTING_DIMENSIONS_V3_3_CANDIDATE_01`；`MARKET_RET20_MEDIAN_V1`；`FACTOR_VOLATILITY20_V1` | `docs/P12_08E_REPORTING_BUNDLE_ACCEPTANCE_20260915.md`；`src/workbench_analysis/bundle_reporting_dimensions_v3_3.py`；`scripts/build_p12_08e_enriched_bundle.py`；`tests/upgrade_v3/test_p12_08e_reporting_bundle.py` | `reports/p12_08/p12_08e_stage_gate.json`；活动bundle `dc8ca188...f0d66`；P12定向24 passed；compileall、diff check通过 | 同日市场强弱与波动113/113；来源摘要、run和参数版本绑定；旧bundle/观测不覆盖；1/20真实日、452结果仍NOT_DUE | 下一真实收盘构建同合同bundle并封存第二日 |

## P12 日常一键生成输入修复（2026-09-15）

| task_id | status | stage_contract | evidence | acceptance | next_stage |
|---|---|---|---|---|---|
| P12-DAILY-ONE-CLICK-INPUT-REPAIR | FULL_PASS | `P12_DAILY_ONE_CLICK_INPUT_REPAIR_V1`；P12-06完整发布要求；一键生成保留决定 | `docs/P12_DAILY_ONE_CLICK_INPUT_REPAIR_20260915.md`；`reports/p12_daily/p12_daily_one_click_input_repair.json`；真实任务`daily-f3b9a357fcc04d8683cd8eceaef2839c` | 上传日与包内经济交易日分离；staging路径恢复；同包多元数据快照不可变版本化；真实链发布、M8/M9、M10和研究运行全部READY；定向32 passed | 恢复日常一键生成；新真实收盘后再封存P12第二个信号日 |
