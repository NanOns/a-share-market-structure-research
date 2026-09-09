# 工作台 M7–M15 升级方案：代码核对与审计修订版

> 实施入口已更新：[M7–M15完整实施方案v2.1](WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md)。2.1已经完整合并本文件的审计修正，并补齐40个接口、字段/迁移、开发工作包、UI与测试细节。开发只需以2.1为准；本文保留作审计记录。

版本：workbench-upgrade-plan-v2.0；审计日期：2026-09-09。
状态：设计修订完成，实施验收未开始。本文已被完整实施方案v2.1替代，保留作审计记录。
配套：[后续发展计划](WORKBENCH_POST_M15_ROADMAP.md)。
原稿保留在 [v1.1 方案](WORKBENCH_M7_M15_DETAILED_UPGRADE_PLAN.md)，便于核对修改原因。

## 1. 审计结论与可实现范围

大部分功能可以实现，但 v1.1 不适合直接照单开发。主要问题是历史数据的可用性判断过于乐观、发布身份与历史存储设计不完整、若干指标发生口径变化，以及阶段顺序遗漏了历史结构计算和板块语义基础。

六项会员功能可借鉴其研究流程和界面组织：天眼模式→个股透视；梯队周期→收盘梯队；智库→属性库与交叉筛选；主线周期→版本化分类；题材周期→板块矩阵；大盘周期→市场历史。原软件客户端的模块、文字和接口路径不能证明服务端算法已经被完整还原。本方案定义工作台自己的可解释实现，不宣称复制原软件算法。

| 功能 | 可行性 | 开发前必须落实的条件 |
|---|---|---|
| 首页、联动、属性库、交叉选股、证据弹窗 | 可实现 | 统一取数与范围，保留现有发布和运维入口 |
| MA、成交额、收盘新高、RPS、历史图表 | 可实现 | 区分原价与复权价，补算历史，冻结输入和公式版本 |
| 板块矩阵、留存、代表股更替、主线 | 可实现描述性版本 | 区分真实观测与当前成员回算；同口径比较；历史结构计算 |
| 历史时点真实板块组成及完整市场回测 | 目前不能完整实现 | 缺少历史成员/证券状态时，明确标为回算，不能补造事实 |
| 板块自身行情涨幅 | 有条件 | 本地板块指数数据及映射通过核验；否则显示成员统计及缺失状态 |
| 精确换手率 | 有条件 | 日期有效的流通股本、股份单位和股本口径 |
| 精确涨跌停/连板 | 有条件 | 日期有效的板别、风险警示、无涨跌幅限制期、除权参考价及交易规则 |
| 热榜、涨停原因、在线盘中报价 | 有条件 | 来源逐项验证；不能承诺同花顺/东财所有接口免费、稳定、有历史 |
| 龙虎榜 | 可选低优先级 | 免费来源与席位映射成熟后单独实现 |
| 盘中炸板时刻、会员后台黑盒评分 | 本轮不实现 | 用户无实时炸板需求；客户端静态证据不足 |

功能“可实现”不等于已有数据能够覆盖全部历史日期。缺失提示只是正确降级，不算相应数据能力完整交付。

## 2. 已核对的当前基线

本轮只读核对代码、合同、回执、Parquet元数据和正式库计数；未启动目标EXE、未测试第三方行情端点、未改业务代码或正式数据库。

| 证据 | 本轮结果及影响 |
|---|---|
| data/normalized/adjusted_daily.parquet | 19,622,350行、6,178个row group；含 raw/adj OHLC、raw_amount/volume、缺失与复权字段；无可靠流通股本和涨跌停参考价专用字段 |
| data/factors/factors_daily.parquet | 18,533行、1个row group；不能视为250日完整因子库 |
| 正式数据库 publication_heads | 2026-09-04、07、08，共3日；publications共6条 |
| membership_entries | 288,308条，包含多个快照，不能当作单日成员数做容量估算 |
| observations / outcomes | 5,777 / 2,030条；已有前向观察机制，历史重算不得写入这些正式观察 |
| src/normalize/phase1.py:normalize | 明确注明历史行是单个截止日快照；universe_status基于截止日，不能直接沿用为每个历史日范围 |
| src/sector/phase2.py:snapshot_guard | 明确禁止当前快照直接历史回填；应增加独立回算管线，不能移除原守卫 |
| src/workbench_service/app.py:_load_quotes | 从可变全局Parquet读adj_close，以前一次发布日期作比较日；可能错用复权价和跨日涨幅 |
| src/workbench_service/strength_association.py | 已有剔除目标股后的独立支撑校验；v1.1的新关联排序漏掉了它 |
| src/factors/registry.py / engine.py | AMOUNT_RATIO20含当日基准；RS是相对市场中位收益差，并不是RPS百分位 |
| src/sector/phase2.py:prepare | amount_ratio_5_20为重叠的5日均额/20日均额；v1.1改成不重叠窗口会改变含义 |
| src/workbench_db/repository.py:open | 运行schema.sql并登记固定版本；尚无顺序DDL迁移执行器 |
| src/workbench_ops/migration.py | 当前是数据库位置迁移/校验复制，不能直接当作schema迁移器 |
| src/workbench_publish/service.py | 单事务发布；成功重试分支仍调用成员绑定写入，升级须核对同身份不可变性 |
| src/workbench_service/static/index.html | 顶层壳通过iframe加载/view；只改index.html不会自动改内部工作台 |
| reports/upgrade_m6/M6_DEVELOPER_PREFLIGHT_RECEIPT.json | final_status=AWAITING_EXTERNAL_AUDIT；开发预检PASS不等于独立验收完成 |

以上是审计当时状态，实施M7前重新生成基线摘要与源码哈希；数据数量变化本身不构成错误。

## 3. 问题清单与修正责任

P0表示在正式切换前必须解决的数据/身份错误，P1表示相关模块开发前必须解决，P2表示交付完整性和体验问题。严重性是设计风险判断，不代表全部已在运行环境触发。

| 编号 | 等级 | v1.1问题及后果 | 修正位置 |
|---|---|---|---|
| A01 | P0 | 当前归一化历史行被当作历史时点输入，范围与复权可能带入后来信息 | M7b，历史口径 |
| A02 | P0 | 每个发布复制250日全量成员历史，存储和写事务持续膨胀 | M7b，复用不可变日分片 |
| A03 | P0 | 快照要求先绑定成功发布，发布又要求先有快照；合同唯一键遗漏配置、输入变化 | M7b，两步准备、一次激活 |
| A04 | P0 | 历史结构从哪来未定义，M9依赖五类结构却没有生产者 | M8b |
| A05 | P0 | 原价/复权价混用；上一发布日期被当作上一交易日 | M7a/M8a |
| A06 | P1 | 无用户依据排除北交所；缺行情又可能被误认退市 | M7a，恢复沪深北A股 |
| A07 | P1 | 板块语义安排在M11，而M9/M10已经需要排除行情标签 | M7a前置语义基础 |
| A08 | P1 | 全快照单一成员口径无法表示不同日期的观测/回算覆盖；采集日不等于生效日 | M7b逐分片口径 |
| A09 | P1 | 120日预热不等于250日输出窗口；窗口长度与依赖树没有计算 | M7b/M8b |
| A10 | P1 | 强势留存混淆成员增删、行情缺失和状态变化；缺失误算退出 | M9 |
| A11 | P1 | 新关联规则删除剔除该股校验，并增加未经论证的行业优先 | M11 |
| A12 | P1 | 新高包括当日且用相等判断，横盘也会连续新高；多个窗口共用一个连续字段 | M8a |
| A13 | P1 | RS/RPS混同；成交额比改公式但仍要求旧结果不变 | M8a，新增字段与合同 |
| A14 | P1 | 主线可同时持续又高位收缩；未经历强势也可叫退潮；10日历史却用20/30日条件 | M10 |
| A15 | P1 | 除权日不能简单以前收乘涨跌停比例；缺失不能按未涨停归零 | M8c/M13 |
| A16 | P1 | 在线榜单没有批次主键；相同正文去重丢失多次观测；历史页可能看到后来原因 | M14 |
| A17 | P1 | 新增SQL文件没有迁移加载器，备份也未覆盖历史外部文件 | M7b |
| A18 | P1 | M6仍待外审，原方案却以全部完成为基线 | M7a/M15正式切换门 |
| A19 | P2 | 详情过晚集成、三栏挤压、iframe重复滚动、fixes.js继续膨胀 | M7a/M15 |
| A20 | P2 | “满100行”和矩阵多单元格混淆；性能指标无测试条件 | API与验收章 |
| A21 | P1 | 板块金额跨重叠板块相加会重复计算；成员数与有效行情数混为一数 | M9/M13 |
| A22 | P1 | 人工分类覆盖没有表、版本和生效范围；名称关键词误排概念 | M7a/M11 |
| A23 | P2 | 来源清单不等于已验证可用；原文自评PASS过强 | 本文可行性和最终门 |

## 4. 产品范围、数据口径与不变量

### 4.1 股票范围

默认CN_A_LISTED_V2覆盖沪深北已确认上市A股：主板、创业板、科创板、北交所；排除B股、新三板、已确认退市/退市整理和非股票品种。ST不等于退市，不自动全部排除，可设置显式筛选。

优先使用有来源的证券类型、交易所、上市状态及生效日期；前缀只用于校验，不能依赖一份永不更新的正则。现有BJ.92是当前实现证据，不是全部历史北交所代码的完整规则。

分开三种范围：展示股票范围、当日有效行情范围、结构计算合格范围。新上市股票可显示报价但结构不足；停牌股票仍是上市成员但不进入当日涨跌有效分母。长期无行情和UNKNOWN不得自动标记退市。当前名单回算历史必须注明幸存者偏差；只有历史身份可核实时才称历史当日市场范围。

### 4.2 三个时间与两个历史视图

每条历史输入记录trade_date（发生日期）、observed_at（本地获得时间）、effective_date/valid_from（来源明确的生效日期，可空）。

- 观测视图OBSERVED：引用当时已封存的数据版本。板块快照只证明当时采集内容，不自动证明交易所或供应商的真实生效日。
- 回算视图RECONSTRUCTED：固定一个输入包、成员快照和合同，重新计算旧日期；明显标示“按当前资料回算”。
- 复权分别记录output_date、adjustment_as_of、adjustment_identity。严格历史计算必须按目标日截断公司行为；不能只在当前前复权文件上按date过滤就宣称无未来信息。
- 技术字段、证券范围、成员、结构分别记录basis；页面响应可以报告MIXED，但每条曲线必须保持单一口径，交界处断线并提示。
- 按当前日为锚的复权图可用于浏览，但不得作为当时真实可见的历史结构证据。
- 本轮不填补不存在的observations/outcomes，不用回算制造“当时已经命中”。

### 4.3 不变量

TDX输入零写入；原Phase0守卫保留。旧成功发布的输入、成员、算法和结果不可偷偷替换。新指标不得修改封存V1/V2字段的公式。所有分母、缺失值、排序和阈值有版本。金额原值以元保存；原始float金额不能通过转DECIMAL被宣称精确到分。

统一三态逻辑：TRUE AND UNKNOWN=UNKNOWN、FALSE AND UNKNOWN=FALSE；TRUE OR UNKNOWN=TRUE、FALSE OR UNKNOWN=UNKNOWN。排序中NULL固定最后，显示名次用独立稳定序号、统计百分位保留并列；不得让证券代码参与经济评分。结构资格和字段可用性分别保存，避免一个缺失的可选指标使股票整行消失。

用户已明确允许经验证的免费在线增强。根AGENTS.md仍有禁止网络数据的旧文本，这是需同步的项目规则冲突，不应再次被解释为产品永久离线。本文不修改该文件、不发起联网采集；M14实施前按已有产品授权同步规则，保留禁止自动交易等其它限制。

## 5. 依赖和交付顺序

| 顺序 | 工作包 | 前置 | 可独立交付的结果 |
|---|---|---|---|
| 1 | M7a 基线修复、范围、语义、UI骨架 | 已有M0–M6代码和回执核对 | 当前页面正确报价/范围；新版预览骨架 |
| 2 | M7b 历史仓、身份、迁移、覆盖 | M7a | 不可变历史分片和快照；按日期取数 |
| 3 | M8a 技术历史 | M7b | MA/金额/新高/RPS页 |
| 4 | M8b 历史板块基础与五类结构回算 | M8a | M9所需结构、板块基础和历史队列 |
| 5 | M8c 参考价/股本能力分支 | M7b | 涨跌停/换手能力报告；缺失状态 |
| 6 | M9 板块周期与成员/代表股 | M8a、M8b、M7a语义 | 矩阵和时间线 |
| 7 | M10 主线 | M9 | 主线状态与证据 |
| 8 | M11 属性库/集合/关联加强 | M9；主线徽标额外依赖M10 | 联动和交叉筛选 |
| 9 | M12 个股透视 | M8–M11 | 统一抽屉与本地K线 |
| 并行支线 | M13a 市场技术历史 | M8a | 广度、成交、新高；队列数据依赖M8b |
| 并行支线 | M13b 收盘梯队 | M8c；关联列依赖M11 | 梯队、晋级；精确能力受元数据限制 |
| 可选支线 | M14 在线增强 | M7b接口协议和来源验证 | 热榜/原因/报价；不阻塞本地交付 |
| 全程＋最终 | M15 UI收口与正式验收 | 每模块先各自验收，最后整体验收 | 正式入口切换、恢复演练 |

M13a不用等M12；M14可先做来源可行性验证以尽早发现不可用项，不能等全部页面完成才查来源。M9强势成员不得依赖M10主线，避免循环。每个阶段带页面切片，UI骨架在M7a开始，M15负责收口。

## 6. 存储、发布和迁移设计

### 6.1 选择：不可变日分片＋快照清单

analysis_snapshot不物理复制全历史。每个分片表示某数据域某交易日的一次确定性计算；同样输入跨发布复用同一slice_id。日分片manifest固定引用输入哈希、依赖分片和合同。快照清单固定整个查询窗口的分片集合。

例如实际单日约10万条板块成员关系，250日约2,500万行；若250个发布各复制整个窗口，会膨胀至约62.5亿行。该例仅为量级说明，M7b必须测单日实际数。修订设计中日常只增加变更分片与清单，源修订才使相应依赖重算。

初版技术/板块聚合用DuckDB实体表；高容量成员状态用按slice_id存放的不可变Parquet，并登记storage_objects。API只能读取清单中的已验证文件，不接受客户端路径。查询先锁定slice列表，再推送证券/板块条件；避免扫描所有发布和所有分片。

日分片的input_hash计算其实际依赖的日期窗口、证券/成员集合、公司行为有效段及合同配置的规范化内容；source_bundle整包哈希作为出处保存，不单独决定所有旧分片失效。否则每日新增一根K线改变整包哈希，会使“复用日分片”失效。同内容不同物理文件可共用计算结果，来源引用仍分别保留。

### 6.2 元数据表

| 表 | 主键/主要字段 | 约束 |
|---|---|---|
| analysis_jobs | job_id；request_identity、attempt、status、progress、error | 复用现有jobs/attempts优先，避免重复状态机 |
| analysis_slices | slice_id；domain、trade_date、contract_id、input_hash、dependency_hash、basis_json、row_count、logical_hash、storage_object_id | slice_id按全部经济输入及合同哈希生成；成功内容不可改 |
| analysis_snapshots | snapshot_id；cutoff_date、query_start、universe_contract、config_hash、manifest_hash、status、created_at | ID基于内容清单；不依赖“已成功发布”形成环 |
| analysis_snapshot_entries | snapshot_id、domain、trade_date、slice_id | PK前三列；引用唯一成功分片；缺失日期不造零行 |
| publication_analysis_snapshots | publication_id、domain、snapshot_id | PK前两列；本地域成功绑定不可改；新修订才启用新绑定 |
| analysis_daily_basis | slice_id；universe_basis、membership_snapshot_id、price_basis、observed_at、coverage、capabilities_json | 每日各域口径和可用性 |
| sector_semantic_versions | version_id、sector_id；bucket、rule_id、reason、valid_from、observed_at | 人工覆盖生成新版本，历史语义不回写 |
| security_metadata_versions | security_id、version_id；exchange、board、status、valid_from/to、source_id、observed_at | 可扩展现有security_versions，迁移后建立有效日期约束 |
| market_reference_daily | slice_id、security_id；quote_prev_close、limit_up/down_price、float_shares、shares_basis、status_known、source_ref | 未知NULL；不是用模板填满的行情事实 |

publication绑定域显式区分LOCAL_OBSERVED和LOCAL_RECONSTRUCTED，两者可同时存在；API的basis只能解析到其中一个域，不静默跨域补齐。analysis_snapshot_entries中的domain表示technical/sector/structure等数据域。未提供basis时优先可用的观测域；只有回算域时允许选择回算并在首次响应与页面明确标识，不能只改底层查询而隐藏口径。

元数据保留原membership_snapshots/entries及publication_memberships；新增字段/旁表补充观测时间和语义版本，不能改写旧logical_sha256。sector_id须包含来源命名空间；别名映射显式维护，不自动合并同名异源板块。

### 6.3 分析实体

以下本地日表共同PK为(slice_id, 实体键)，日期来自分片，实体表可冗余trade_date用于裁剪，必须与分片相等。

| 表或分片域 | 实体键 | 必要字段 |
|---|---|---|
| stock_technical_daily | security_id | raw_close、adj_close、quote_ret1、price_change_basis、MA5/10/20/60、amount、volume、amount均值及两个新版比值、turnover、RS/RPS、quality |
| stock_high_daily | security_id、window | 20/30/60/100；prior_max_close、new_high、streak、is_left_censored、dist_prior_high、valid_n |
| historical_structure_daily | security_id、queue_name | hit、tier、rank、contract_id、evidence、OBSERVED/RECONSTRUCTED |
| sector_base_daily | sector_id | 成员身份/类型/语义、各周期RS与同类百分位、原有板块扫描条件、结构生产需要的基础字段 |
| sector_cycle_daily | sector_id | board_quote_ret1、member_ret1_median、member_amount_sum、total/valid_count、rank、breadth、coverage、retention、representative状态 |
| sector_member_state_daily | sector_id、security_id | member_rank、valid_rank_count、strong_state(TRUE/FALSE/UNKNOWN)、entry/exit_reason、新高和队列引用 |
| sector_membership_changes | sector_id、security_id、change_type | 前后快照ID、观察区间、成员增删和质量变化分别记录 |
| stock_sector_associations_daily | security_id、sector_id | rank、eligible、拒绝原因、leave-one-out指标、成员内名次/分母、合同 |
| mainline_daily | sector_id | class、predicates_json、valid_windows、previous_class、transition_reason、contract |
| market_cycle_daily | universe_id | 报价有效数、上涨/下跌/平盘、成交、新高/MA宽度、逐字段覆盖、unknown_limit_count、队列去重数 |
| limit_ladder_daily | security_id | limit_state、streak、streak_known、suspension_policy、promotion、denominator_eligible、reference_source |

RS/RPS按window长表或独立明确列存储均可，DDL签发时固定，不以不受校验的JSON替代筛选列。记录ret5/10/20/60及RET30若有明确消费者；M9的“30日”是观察统计窗口，不强制发明30日RS。

价格使用Decimal或整分参与参考价比较；复权精度遵守现有合同。收益/比例存小数、数量存整数、详情JSON存解释。索引由EXPLAIN和基准决定，不机械为每个字段建索引；DuckDB没有关系型B-tree式“复合前缀必然加速”承诺。

### 6.4 提交、恢复和旧发布兼容

1. 在TDX外冻结输入，计算期间不持有正式库长事务；限制工作线程、内存和临时盘，记录进度。
2. 分片临时文件写完并校验，原子重命名到不可变对象路径；失败留下未引用对象，后续有审计的清理可回收。
3. 由现有单owner写入服务串行提交分片登记和清单；物理文件与DuckDB无法靠一个事务同时原子化，用“先对象、后引用”实现。
4. 准备新发布修订时，在最终短事务插入成功publication、snapshot引用、已有业务结果与head；既有引用/哈希必须一致，不一致拒绝。
5. publication身份增加分析manifest摘要，必须贯穿PublicationRequest.job_key、prepared结果、发布ID和重试校验；仅新增SQL表不会产生新修订。
6. 崩溃点覆盖对象写完未登记、清单已准备未激活、提交成功但响应丢失；重试核对全部清单，不能只看到publication成功就跳过分析检查。
7. 旧发布无分析绑定时现有功能仍可看；新历史组件显示“该发布未生成历史分析”。补算以新修订绑定，不后台修改旧发布。
   旧发布如没有可核实的冻结原始报价，也不能将今天全局文件的数据补上后称“旧发布原值”；该字段显示未封存，或在新修订回算视图补充。
8. 源历史修订使被影响日期及其窗口下游失效；递归状态如连板、代表股状态需重算到结果稳定或截止日。算法配置变化同样进入身份。
9. 在线批次独立于本地快照，刷新热榜不需要重新发布本地全部历史；禁止联网写入进程与正式DB争夺owner。

### 6.5 schema与备份

新增真正有顺序的schema迁移器：版本、SQL哈希、前置版本、执行回执；停写维护窗口中备份、事务DDL、校验再登记。现有路径迁移服务只用于复制验证，不承担DDL执行。迁移失败回滚；恢复旧备份时不能自动重新执行新schema。

备份必须含DuckDB、引用的Parquet对象、来源/合同清单；在新临时目录完整恢复并核对所有引用。旧发布引用对象不得清理，活跃job和读请求有lease保护。只清理已证明未引用的对象，调用现有清理预览/隔离流程，不新增自动删除承诺。

## 7. M7：开工基础与历史生产合同

### M7a：基线与公共能力

- 给现有API所有报价增加来源绑定，修正raw_close显示和quote_ret1取值。quote_ret1优先来自当天行情参考前收；没有参考价时原始收盘比仅在可确认普通交易日使用并标记，除权或未知时不能伪装精确当日涨幅。
- 交易日由market_calendar及受审计的主市场日历提供；缺一天发布不等于休市。个股停牌不改变主市场日期序列。
- 报价、成员列表、总数和聚合统一股票范围；各模块分别报告有效分母。
- 提前形成板块语义版本表。当前PRICE_WORDS是起点，不以任意子串直接定最终类别；按sector_id精确覆盖优先，未知分类可看但不参加强势主表。
- UI增加新版预览路由和共享表格/证据/抽屉组件；保留“生成今日数据”和运维入口。历史入口带日期、版本与口径。
- 重新读M6最终回执；目前仅找到等待外审记录。可开发预览，正式切换仍需M6合同规定的独立验收，不在本次文档中代签。

验收：跨两次发布相隔多个交易日仍显示正确单日涨幅；当前文件改变不改变旧发布报价；沪深北A股纳入、B股/新三板排除；状态不明不误退市；证据按钮不撑高表格。

### M7b：历史覆盖与分片生产

- 对每个目标日分别确定价格/事件/范围的cutoff；按批证券加载一次足够窗口，复用现有算法与缓存，不每天全扫近2千万行。
- 显示D天需要输入从首个显示日前再预热W天；W由最大因子/结构依赖推导，250天输出不能只读120天输入。连续统计输出窗口左边界还需状态种子，否则标“至少N天”。
- Parquet日期filter不保证高效：当前文件6,178组，需测row-group日期范围和实际扫描字节。必要时在工作区建立日期分区索引副本，不能修改TDX。
- 当前成员回算固定同一个成员快照；观测序列使用逐日封存快照。缺观测日不自动前填成真实成员；前值延用只允许单独标记STALE_ESTIMATE。
- 能力接口返回available_from/to、missing_dates、required_history、supported_basis、field_coverage，不只返回一个布尔值。
- 外部公司行为记录只有当前已知时间时，历史回算标示资料已修订；不能推定当年已经可见。

接口：GET /api/history/coverage；GET /api/universe/summary；GET /api/history/jobs/{job_id}。数据查询带publication_id；纯系统job状态带job_id。

验收：两次同输入计算逻辑哈希一致；新输入只重算受影响依赖；目标日期之后公司行为扰动不影响严格历史结果；当前成员回算与观测不可混线；恢复演练成功；内存/磁盘峰值有记录。

## 8. M8：技术、结构与规则能力

### M8a：逐项公式

下列新增规则标为TECHNICAL_HISTORY_V2提案；复用旧字段时保持旧合同，变更语义必须换字段名。缺有效样本按窗口质量规则返回NULL，不能偷偷跳过缺失延长窗口。

| 小功能 | 精确定义与输出 | 验收样本 |
|---|---|---|
| 最新价 | raw_close＋quote_date；停牌可另显示last_known_price及日期 | 除权日前后，停牌与缺行情 |
| 当日涨幅 | raw_close/quote_prev_close−1；无可靠参考时显示相应basis或暂无 | 发布间隔多日、除权日 |
| MA | 沿用现有MA5/10/20/60；比较使用同锚adj_close；原价与历史复权曲线分开 | 旧公式逐值一致 |
| MA排列 | 严格MA5>MA10>MA20>MA60为多头，反向为空头；其余显示混合及各不等式；缠绕仅在新增距离阈值合同后启用 | 相等、交叉、样本不足 |
| 成交额 | raw_amount元；AMOUNT_MA5/10/20沿用含当日公式 | 含停牌0与未知NULL |
| 旧成交额比 | AMOUNT_RATIO20=当日/含当日20日均額；旧amount_ratio_5_20=MA5/MA20 | 不改变封存scanner |
| 新异常成交额比 | amount_vs_prior20=当日/前20交易日均额；另建字段；不把金额变化称成交股数放量 | 前20日均100、今日300，输出3 |
| 成交量放大 | volume_vs_prior20=当日成交股数/前20日均量，先验证单位和公司行为影响 | 金额放大但股数没放大 |
| 异常级别 | 新比值[0,1.5)常态、[1.5,2)增加、[2,3)明显、[3,+∞)显著；质量优先 | 1.5/2/3边界；分母0 |
| 新高 | n∈20/30/60/100；adj_close[t]>max(adj_close[t−n:t−1])，完整n个比较日；另存“持平前高”，不计创新高 | 横盘不连创新高，n+1点 |
| 连续新高 | 各window独立streak；明确False归零，未知中断连续可确认区间；左截断标is_left_censored | 20日与60日不同序列 |
| 距前高 | adj_close[t]/prior_max_close−1，可正；旧DIST_HIGH含high且含当日，保留原含义 | 正值突破与旧字段差异 |
| RS | 沿用收益减同日市场收益中位数；RS与RPS分列 | 基准变动，不误百分位 |
| RPS | 对同日同范围有效RET_n平均并列排名/N；n=5/10/20/60；N<100则不足；展示样本数 | ties、单日样本突减 |
| 换手率 | 成交股数/生效流通股本；股份单位、股本范围和来源全存 | 股本变动、手/股错误 |

新高不从DIST_HIGH20/60直接复用推断。未知/确认停牌的处理与现有calendar质量一致；实际当日无交易不计创新高事件。成交金额原始精度来自TDX数据，金额转单位后至多两位小数，舍入跨万/亿/万亿边界时再次正规化。

界面：“个股研究/创新高与RPS”支持四个窗口、RPS门槛、连续天数、结构和量额过滤；默认8–10列，扩展字段进入详情。提供中文单位说明。
接口：/api/stocks/technical、/api/stocks/new-highs、/api/stocks/{id}/technical-history，全部按当前快照与显式窗口读取。

### M8b：历史五类结构与基础板块

生产顺序必须固定：按日价格和范围→基础因子→横截面RS/RPS→基础板块聚合/板块扫描→个股scanner→五类结构/队列排名→M9周期。禁止M9结果反过来作为同一日基础scanner输入。

创建独立history runner调用可复用纯函数，不能为回算调用旧正式发布runner逐日写observations。现有snapshot_guard保持不变；回算包装层使用显式RECONSTRUCTED合同并产出新的身份。

保存每股每队列的hit/tier/质量；未知不是未命中。板块强势成员门槛使用合格结构命中或任一指定新高，不能把诊断观察队列自动当强势证据。新高窗口必须含30日，与页面一致。

界面显示“历史回算命中”和“当时已发布命中”区别；市场历史各队列可重叠计数，另存去重股票总数。
验收：与已有正式日期同输入/合同重算对齐，差异归因到口径/算法；打乱行顺序结果不变；正式observations/outcomes行数和哈希不变。

### M8c：日期敏感规则/股本支线

新增limit_rule_versions(rule_id,exchange,board,status,valid_from/to,ratio,tick,rounding,source_ref)；上市特殊期、重新上市、风险警示、除权参考价、暂停/恢复交易等作为覆盖字段，不能硬编码“ST都一个比例”。

本轮未核验交易所最新规则，因此本文不发布当前法律/交易规则数值表。实施必须按官方生效文件建版本和样本；缺历史状态时limit_state=UNKNOWN并保留理由，不能退化到单一10%且标精确。

先用可信limit_up/down_price；否则用有依据的quote_prev_close和规则做Decimal整数报价单位计算。不是任意±一分钱容差，以免把差一档未封板算成涨停。volume单位用现有amount/volume价格一致性校验做辅证。

能力验收：精确、近似、未知分别计数；没有可靠股本则换手率模块能力为UNAVAILABLE，不以正常降级掩盖未完成的数据能力。

## 9. M9：板块矩阵、留存、扩散与代表股

### 9.1 板块行情与统计

报价区分board_quote_ret1（供应商/板块指数行情）与member_ret1_median（成员分布统计），来源不同不能连成一根趋势线。无板块报价时主列“暂无板块行情”，详情仍可显示成员中位数，不能用“涨幅”掩盖换口径。

member_amount_sum为同板块纳入范围去重股票金额；不可累加不同板块金额作为市场总额。未知金额不能算0。total_member_count为范围内成员总数；quote_valid_count、factor_valid_count、filtered_result_total各有名称。

同类板块百分位沿用平均并列rank/N，rank_change用旧名次−新名次（正值改善）。5/10/20/30日统计窗口表示观察天数；当日强度默认按20日RS百分位，短期辅助用5日；不把10/30日窗口解释成新公式。

### 9.2 强势成员与比较集合

- 资格：市场RPS20≥0.80、板块内RET20百分位≥0.80，且至少一项合格五类结构或20/30/60/100日新高；所有参与条件提供三态真值。
- M[d]为当日纳入成员；C=M[d−1]∩M[d]且两日状态都已知的共同可比成员。
- 留存率=两日在C中均强势的数量/昨日在C中强势数量；分母为0→NULL。
- 另列previous_strong_total、comparable_previous_strong、uncomparable_count与比较覆盖，避免移除成员使留存看似提高。
- 扩散进入/退出只在C内比较；成员新增/删除单独计算，未知标DATA_UNAVAILABLE。
- 扩散=进入数>退出数；收缩相反；相等为稳定。比较覆盖不达合同0.70则趋势UNKNOWN。
- 宽度变化使用共同有效成员分别计算，禁止两个不同分母的宽度相减后声称扩散。

### 9.3 代表股更替

产品默认称“板块强势代表”，说明是规则首位，不是事实龙头。保留“首位/候选/确认代表”字段。使用当前合格成员同一排序规则：板块内RET20排序，结构tier作为并列辅助，代码最终打破显示并列；RS20与RET20排序在共同基准下等价，不能当独立证据加权。

状态机保存confirmed_id、candidate_id、candidate_since、candidate_streak、event_date。A→B首日候选、次日B确认，确认事件记第二日，不回写首日。A→B→A不确认；停牌/缺失日按未知中断连续证据，旧confirmed保留但标stale。只从实际观察日算已知连续天数。

UI：默认20板块×10交易日，5/10/20/30统计窗与横向日期范围分开；点击单元格加载当天证据。板块金额/宽度趋势、共同成员进入退出、代表更替分为三个详情页签。
API：/api/sectors/cycle、/{id}/timeline、/{id}/members/history、/{id}/leader-history。
验收：共同集合手算、成员删除/缺失/改名、并列、更替三序列；首次观测不虚构昨日。无正常板块不能用行情标签凑足，显示实际数量。

## 10. M10：主线状态

分类是描述性合同MAINLINE_STATE_V2_DRAFT，以下阈值是工程初稿，不是已验证的有效策略。先固定配置、做对照样本与边界审计，再签发V2.0；调参不能选择未来涨幅最大的结果当理由。

定义P为当前20日同类强度百分位；B为共同有效成员上涨宽度；A为板块成员金额/前20日均额；R为共同强势成员留存率。上榜=P≥0.8。所有输入来自M9固定口径，资金扩张不称净流入。

按以下顺序确定唯一class，同时返回全部predicate及冲突解释：

| 优先级 | 类别 | 初版硬条件 |
|---|---|---|
| 1 | DATA_INSUFFICIENT | 当前覆盖<0.8、所需成员比较不足、或当前状态必需窗口未知；另返回缺哪些字段 |
| 2 | FADING | 过去20日曾上榜；P<0.6且较3日前下降≥0.15；共同B和A均较3日前下降 |
| 3 | HIGH_LEVEL_CONTRACTION | P≥0.8且共同B较3日前下降≥0.10或R<0.5；括号固定为P条件 AND (宽度条件 OR 留存条件) |
| 4 | REACCELERATING | 20日上榜≥6次，P≥0.8且较3日前提高≥0.10，B提高≥0.10，A≥1.2 |
| 5 | SUSTAINED | 5日上榜≥3次、连续≥2日；P≥0.8、B≥0.5、R≥0.6；先经过高位收缩优先判断 |
| 6 | NEW | P≥0.8、此前5日上榜≤1次、B≥0.55、A≥1.1、共同进入>退出 |
| 7 | BROADENING | P≥0.7、共同进入>退出、共同B较前日提高≥0.10 |
| 8 | OBSERVING | 所需数据均有效但未满足任何状态 |

首版完整class使用至少20个有效观察日及3日差值所需数据，30日次数单独不足可NULL；不因一个非必需的30日字段缺失把全部判定封死。不足20日可展示各项已知证据和“观察期”，不偷用10日数据代替20日。

计数窗口按连续市场交易日定义，窗口中缺失必须影响valid_n，不能向更早日期滑动补满20个“有数据日”。覆盖门通过后才能执行上述类别顺序；若一个更高优先类别仍为UNKNOWN、较低类别为TRUE，首版保守输出DATA_INSUFFICIENT并列出该冲突，不偷跳过未知类别。

状态变化因数据口径/合同切换时记录MODEL_CHANGE或BASIS_CHANGE，不叫主线退潮。板块同名不合并，重复高度重叠的概念不累计为独立市场主线证据。

UI：分类筛选＋紧凑表；证据弹窗按持续/宽度/成交/成员分组，列实际值、门槛、通过/未知。
API：/api/mainlines、/api/mainlines/{id}/evidence。
验收：持续与收缩同时满足时显示收缩；从未强势不能退潮；低留存但P低不能误归高位；30日缺失不影响具备20日的类别；单日缺失不伪变化。

## 11. M11：属性库、交叉筛选与强势关联

M7a完成语义基础，本阶段补完整查询和配置界面。属性库对分析结果只读；人工覆盖通过本地配置新版本并重新分析生效，不能在只读查询POST里写库。保留industry/theme/normal_style及标签分组，不固定行业优先。

集合输入：2–4个不同include_sector_id、operator=INTERSECTION/UNION、exclude_sector_ids、结构/新高/量额筛选、sort、page。结果为(交集或并集)减排除集合，先集合再同快照筛选；重复ID去重，超过限制返回错误；总数在分页前计算。排除条件明确数量上限20。

关联沿用现有stock-strength-sector-association-v1.0的剔除目标股校验：
正常属性、板块有效、覆盖≥0.70、CURRENT_STRENGTH/REACCELERATION、至少5只其他有效成员、20日剔除后收益中位>0且上涨占比≥0.60、目标板块内百分位≥0.80；再加速还需5日独立支撑。保存eligible=false拒绝原因。

新周期信息先作说明，不未经版本对照就替换现有门槛。新增排序若启用则为V2独立配置和结果，不复用V1名称；不得添加核心行业固定优先。上榜数、多标签数、RS与RET重复排序不视为多重独立支撑。

UI使用左侧280px可折叠选择栏＋右侧结果表，条件在表格上方折叠，不默认三栏挤压。字段显示“板块内第N名/有效M只”及总成员/筛选后数。事件/行情标签可单独选作筛选，但永不替代强势关联。
API：/api/sector-library、/api/sector-intersection/query、/api/linkage/history、/api/stocks/{id}/memberships、/sector-associations。
验收：集合真值、NULL筛选、删除成员、4板块上限；单股拉高板块但其他股不强必须拒绝关联；同股正反查一致。

## 12. M12：个股研究透视

所有表格复用一个抽屉。概览含原价、当日涨幅、成交、研究带、主要结构、强势关联；技术页含MA、量额、换手质量、新高/RPS；板块页分强势关联/基础属性/行情标签；历史页含本地OHLC蜡烛、均线、金额柱、RPS和结构时间线；外部证据页异步加载。

历史图先用本地数据即可，在线不是自绘K线前提。图表查询带price_basis、window、as_of；不能把原价点绘在复权MA轴上。恢复路由用publication_id、security_id、tab、days；抽屉关闭后迟到请求不能重开。

API拆分/insight（首屏聚合）、/technical-history（按需图）、/structure-history（历史来源标示）、/external-evidence。缓存键含snapshot_id、股票、窗口、字段集、价格口径；不再只用snapshot＋股票覆盖所有请求。

证据弹窗：使用button、portal到页面根，固定最大高85vh，内部滚动；X/遮罩/Esc关闭；点击内容不关；焦点返回来源按钮。摘要默认4–6项关键依据，详细数据分组折叠，布尔翻译“命中/未命中”，数字百分比化，不渲染原始换行字符串。
验收：全部表格入口一致；键盘与遮罩关闭；两股快速切换不串图；长文本不变形；原价/复权标示；无在线时本地完整可用。

## 13. M13：市场历史与收盘梯队

市场广度基于quote_ret1有效股票；up+down+flat=有效分母，上市总数另列。新股报价与120日结构资格分开。成交额按股票去重求和，不能加板块金额；少部分缺失显示覆盖，不宣称完整全市场。

MA/新高/队列分别有valid_count。两队列同股可各算一次，total_unique单独去重。M13a先交付，强势板块和主线数量等待M9/M10后加入。

涨停状态分UP/DOWN/NONE/UNKNOWN/NO_LIMIT/SUSPENDED。本轮定义“连续市场交易日收盘封板”：确认停牌使该口径连续事件中断，标SUSPENSION_BREAK；行情缺失使streak_known=false，不能当作断板/未封板。下一次有效数据可给可确认最短连续数，直到找到已知边界。不要把此口径冒充所有行情软件的通用连板定义。

晋级分母：昨日确认涨停且今日状态可判断且有涨跌幅限制的股票；今日停牌、缺失、无涨跌幅限制者单独计数。按昨日层级group，今日继续封板为晋级。显示原始分子/分母及排除数，不只一个百分数。

UI三组图：广度、量额与MA覆盖、涨跌停/新高/队列；默认60日，可30/90/120/250。点击日期看当日数据，仍带固定snapshot。梯队分组独立分页，首板到高板不一次全部展开。
API：/api/market/cycle、/day-detail、/api/limit-ladder、/promotion-history。
验收：未知涨停不算NONE；停牌不计晋级失败；除权参考价样本；市场集合恒等式；250日无股票全量DOM。

## 14. M14：免费在线增强

本阶段分“来源验证”“热榜”“涨停原因”“可选盘中报价”“低优先龙虎榜”；每个能力独立状态，某站热榜成功不代表其原因/历史行情也成功。

### 14.1 来源准入与适配

只测A级正式开放/明确许可免费能力、B级公开网页能力；网页公开不自动等于许可。记录来源官方说明、入口、字段、时间语义、请求预算和实际样本。B级条款不明保持待验证；不使用龙字诀私有会员服务及凭据，不做签名/验证码绕过。

适配器能力声明supports_history、supports_quote、supports_rank、supports_reason；fetch_latest与fetch_history分开。不支持历史的端点不得接受日期却返回当天数据冒充历史。

观察10个交易日，每日最少一个目标场景样本；首版可用性目标成功≥95%、必要字段≥99%，代码误映射=0，日期错误不入库。样本报告保存分母；遇429尊重Retry-After；默认低频5–15分钟缓存并服从来源更严限制。没有稳定来源时记UNAVAILABLE，不用“页面可降级”算热榜交付完成。

### 14.2 数据库

| 表 | 主键与字段 | 用途 |
|---|---|---|
| online_fetch_runs | fetch_id；source、dataset、requested/received、status、error、raw_hash | 每次尝试都记录，同正文不丢观测时间 |
| online_payloads | raw_hash；storage_object_id、schema_version | 原正文内容去重复用 |
| online_batches | batch_id；fetch_id、source_as_of、trade_date、capability、status | 一次完整榜单/行情批次身份 |
| online_rank_entries | batch_id、list_type、security_id；rank、previous_rank | 同股跨时刻不覆盖，原平台名次不因A股过滤重排 |
| online_evidence | evidence_id；source、security_id、event_time、published_at、first_seen_at、text_hash、raw_ref | 原因/资讯时间与内容 |
| online_security_map | source、source_code、valid_from；security_id、exchange、mapping_version | 不靠去掉前缀模糊拼接 |

热榜“同时上榜”必须使用时间差≤配置阈值（首版15分钟）的有效批次，否则提示不可比较。原因多源并列；重复内容引用同一正文，来源分别保留。

排名变化同时返回comparison_batch_id与比较口径（上次抓取/前一交易日同时间段）；不存在可比批次就显示暂无，不能把平台提供的另一种名次差混用。过滤非A股仅影响展示行，不重编原平台排名。一次列表和分页请求固定batch_id，翻页期间不能悄悄换批。

历史观测页要求published_at与first_seen_at不晚于as_of；后补原因只可在“事后补充”单独展示。时间未知则不参加严格历史视图。实时页允许展示最新批次，但清楚标本地快照日期与在线截至时间。

### 14.3 接口、UI和测试

后端暴露/data-sources/status、/hot-rankings、/external-evidence、/quotes/latest（若准入）；在线接口返回batch_id和source_as_of，不伪装analysis_snapshot_id本地内容。HTTP客户端有连接/总超时、最大响应长度、重试总预算。

平台热榜在市场周期二级页；个股在线报价以独立小区块补充；“生成今日数据”不等待所有在线来源。前端渲染外部文字用textContent，链接协议白名单，不执行正文HTML。
验收：超时/429/空表/乱码/字段漂移/代码歧义/历史伪返回；重复抓取保留观测；相同本地snapshot在在线更新前后本地结果哈希不变；个人凭据不入日志。

## 15. 页面架构与统一API

六个一级入口：研究总览、板块研究、个股研究、联动选股、市场周期、数据说明。顶栏保留日期、口径、刷新状态、生成今日数据和运维入口。合同哈希进入详情，不占主表。

首页：市场卡片→强势板块→板块状态梯队→代表个股→分页优先研究。默认行业/概念分组，行情标签放独立折叠区，不顶替正常板块。代表股跨多个板块出现时显示关联来源，首页可按security_id去重展示。

M7a建立/v2预览路由，模块化复用format/table/modal/drawer/router/api/chart组件；M15切换默认入口，旧/view及原静态报告仍可用于历史回看。禁止把所有新功能继续塞入fixes.js。生产workbench.py负责生成薄壳，不再内嵌全量数据；静态脚本资源路由和render身份必须一并更新。

列表数据请求固定publication_id、可选trade_date（不得晚于cutoff）、basis、page/page_size、白名单sort；同一请求解析一次snapshot，查询总数和页面行使用同一事务视图。日期切换request epoch递增；缓存含全部筛选与口径并设容量上限。

统一错误：400参数、404发布/实体不存在、409缺分析能力或身份冲突；保留现有code/message/retryable/next_action。系统状态接口不强制publication_id。缺可选字段在data_quality说明，不使整个概览失败。

分页最多100行；矩阵是20个板块行×10日期单元格，不受“100个点”的错误约束；最大查询窗250，单矩阵最多100行×30列。成员明细另请求。图表只回聚合点。

布局以1440×900和1920×1080为主，1000px以下折叠选择栏。全局仅一处纵向主滚动，宽表在自己的容器横滚；最多固定名称/代码两列。颜色配文字/图标；弹窗与抽屉禁止同时形成不可逃离的焦点层。

## 16. 验收：如何判断真正完成

### 16.1 必须输出的证据

每阶段交付源码/配置版本、迁移记录、输入清单、字段覆盖报告、测试原始结果、API样本、两种桌面尺寸截图和失败恢复记录。审计人员能由sample_id复算指标。不把写了测试文件当成执行通过。

### 16.2 关键验收场景

| 编号 | 场景 | 通过标准 |
|---|---|---|
| T01 | 发布相隔多交易日 | 当日涨幅来自真实参考前收，不是前发布日 |
| T02 | 当前原始/复权文件被替换 | 旧发布查询完全不变或因缺不可变输入明确失败 |
| T03 | 给目标日后增加分红资料 | 严格历史不变；资料修订回算另出新身份 |
| T04 | 北交所/新股/ST/未知状态/B股 | 正确分开展示范围与结构资格；未知不误退市 |
| T05 | 250日图与100日新高 | 输入预热足够；左截断连续天数明示 |
| T06 | 恒价、相等前高、持续新高 | 恒价不创新高；各window独立streak |
| T07 | 对照AMOUNT_RATIO20与新版比值 | 旧公式不变，新公式字段不同；1.5/2/3边界明确 |
| T08 | 交叉板块金额和成员数量 | 市场不重复加金额；总成员/有效/筛选计数正确 |
| T09 | 成员删除、缺数据、变弱 | 三种事件分开；留存共同集合手算一致 |
| T10 | 代表A→B→B与A→B→A | 第二日确认或不确认，不回写首日 |
| T11 | 同时满足持续与收缩 | 输出收缩，保留所有条件证据 |
| T12 | 只有目标股强、其它成员弱 | 剔除目标股校验拒绝关联 |
| T13 | 涨停参考价不明/停牌/缺行情 | UNKNOWN独立；晋级分母不误计 |
| T14 | 各次提交崩溃/同身份不同内容 | 前者安全续算，后者拒绝；无半完成head |
| T15 | 备份恢复 | DB及全部分片可查询，文件哈希匹配 |
| T16 | 在线重复/过期/后补原因 | batch独立、旧榜不冒充当日、历史不看未来 |
| T17 | 切日期后旧请求迟到/连续开两股 | 无串数据；关闭不被迟到响应重开 |
| T18 | 证据长文/X/遮罩/Esc | 表格行高不变、内容滚动、焦点恢复 |
| T19 | 历史结构回算 | 同条件样本对齐；旧observations/outcomes不增不改 |
| T20 | schema失败与代码回退 | 旧入口恢复，未成功迁移无版本登记 |
| T21 | 新快照存储增量 | 未变日分片ID复用；日更不复制全窗口 |
| T22 | 单元测试之外的真实页面 | 至少两个正式日、30/250日回算窗实测；未支持的显示能力不足 |
| T23 | 语义关键词误排和人工覆盖 | 以明确sector_id覆盖保留正常概念；新版本不改旧快照 |
| T24 | 三态布尔、并列与NULL排序 | OR的已知命中不被可选缺失否定；经济百分位并列，显示排序稳定 |

### 16.3 性能与规模门

记录本机CPU/RAM/磁盘、数据日数、有效股票/成员数、浏览器版本。固定50行列表/20×10矩阵，冷缓存5次、热缓存30次，报p50/p95与最大值，不仅均值。

初版交付目标：列表热p95≤800ms；个股首屏热p95≤500ms；矩阵热p95≤800ms；首页可操作冷≤3s、热≤1s。250日图返回聚合数据；未访问模块无后台全量拉取。单次持续主线程任务>200ms须定位并优化。发布计算同时查看旧版本，读取p95退化不超过2倍。

M7b先测30日/250日回算与单日增量的CPU、扫描字节、峰值内存、临时盘和总耗时；按本机资源冻结预算后才能排上线时长。内存默认上限取可用内存的50%且可配置；任务不得因OOM留下半成品。默认列表传输≤500KB，超出则裁剪详情字段；该目标不套用所有图表/证据。

### 16.4 放行条件

- DOCUMENT_REVIEWED：本方案完成审计修订，不等于运行FULL_PASS。
- READY_FOR_PREVIEW：M7基础正确，可在新入口展示已验收模块。
- FULL_PASS：全部承诺的本地能力通过；明确纳入本次交付的在线能力及字段真实可用，且M6正式切换门已满足。
- DEGRADED_PASS：核心本地通过，列明换手/板块报价/精确涨停/在线源等未覆盖能力、缺失比例及影响；不能宣传全部功能实现。
- BLOCKED：身份混用、伪历史、错误核心计算、数据丢失或页面主流程错误。

本轮不签发EXTERNAL_AUDIT_PASS；现有M6独立验收要求继续保留。文档“无遗漏”只能理解为本轮已识别问题有处理路径，不能代替实施阶段发现新问题。

## 17. 代码改动位置与回归范围

| 现有位置 | 计划改动 |
|---|---|
| src/workbench_service/app.py | 修正报价来源/日期；快照解析、统一范围、分域查询、缓存上限与新路由 |
| src/workbench_service/strength_association.py | 保留V1独立支撑条件，增加拒绝原因/历史输入适配，V2显式版本 |
| src/workbench_db/repository.py、schema.sql | 引入schema迁移执行/校验，元数据表，保持旧字段兼容 |
| src/workbench_publish/service.py、orchestrator.py | 分片准备与发布manifest身份贯通，成功重试一致性验证 |
| src/workbench_ops/backup.py、storage.py | 外部对象引用备份/恢复、lease和未引用清理 |
| src/normalize/phase1.py、sector/phase2.py | 复用纯计算函数，保留旧快照守卫；新history wrapper显式口径 |
| src/factors/registry.py、engine.py | 旧合同冻结；新增历史技术合同独立注册 |
| 新src/workbench_history/ | 覆盖、分片、依赖失效、回算包装、三态状态 |
| 新src/workbench_analysis/ | technical、structures、sector_cycle、mainline、limit_ladder模块 |
| 新src/workbench_online/ | source能力、批次、映射、缓存及录制样本解析 |
| src/production/workbench.py和static/ | 同时处理iframe内部页面与壳；模块化JS/CSS及资源版本 |

回归重点：tests/phase1、phase2、r2、r3_*、r4_*、upgrade_m1–m6中的公式、无未来、共同成员、不可变观察、发布原子性和现有关联测试。新增upgrade_m7–m15只测试可观察行为和上述反例，避免逐行照抄实现。每包先定向跑；正式切换前再全量回归和浏览器验收。

## 18. 本轮审计交付与未验证事项

已完成只读证据核对和文档一致性复查，将A01–A23落实到工作包和T01–T24；旧方案的无依据北交所排除、过强PASS结论、历史和公式冲突不再适用。

尚未验证：第三方来源可用性、历史股本/参考价完整性、全量回算性能、迁移运行、浏览器新版布局和M6独立验收。以上均有前置门，不再以“预计可做”当成已完成。

实施优先交付M7a＋M7b：先使现有价格、日期、范围和历史身份可信，再开发技术历史与板块周期。后续想做的功能见配套计划，避免当前升级被额外需求无限扩张。
