# 工作台 M7–M15 完整实施方案 v2.1

版本：workbench-upgrade-plan-v2.1；修订日期：2026-09-09。
状态：可据此启动分阶段开发；运行验收尚未执行。本文完整替代v1.1及v2.0，不需要同时阅读旧方案才能实施。
配套：[后续发展计划](WORKBENCH_POST_M15_ROADMAP.md)。
旧稿只用于历史审计；本文已经完整保留v2.0的范围、23项审计发现、公式、依赖、发布/存储设计和24个验收场景，并补齐API、字段合同、迁移批次、开发任务及页面交互。

阅读路径：第1–5章确定范围和顺序，第6–17章定义处理逻辑，第19–20章是[接口与请求响应](#api-contract)，第21章是[数据库字段与迁移](#database-contract)，第22章是[开发任务清单](#implementation-tasks)，第23章是[页面设计](#ui-contract)，第24章是[测试与验收](#acceptance-contract)。第18、25章列明仍需实测的数据条件。

开发规则：先按第22章工作包实施；每包同时交付第20章对应接口、第21章对应存储、第23章页面切片和第24章测试。只在具体能力门通过后接入下一阶段。后文参数/DTO/DDL约定是对前文概述的展开，旧文中的简写不能覆盖这些具体约定。

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
| jobs / job_attempts / job_events（扩展） | job_id；request_identity、attempt、status、progress、error | 复用现有任务表，新增job_kind；不另建analysis_jobs |
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

下列新增规则实现版本为TECHNICAL_HISTORY_V2_1_PREVIEW；复用旧字段时保持旧合同，变更语义必须换字段名。缺有效样本按窗口质量规则返回NULL，不能偷偷跳过缺失延长窗口。

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

分类实现合同固定为MAINLINE_STATE_V2_1_PREVIEW，以下阈值可以直接编码并做测试，但不代表已验证的有效策略。先按本版配置执行对照和边界验收；改阈值必须产生新版本。调参不能选择未来涨幅最大的结果当理由。

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

<a id="api-contract"></a>
## 19. 公共接口合同：可以直接据此开发

接口版本workbench-api-v2.1；保留现有/api路径。旧接口在不传include_analysis时继续返回旧字段，新接口和新版预览使用本章统一结构。本文接口均是计划实现，表中“现有”表示路由目前存在，不表示新字段已经存在。

### 19.1 参数规范

| 参数 | 类型/默认值 | 校验和用途 |
|---|---|---|
| publication_id | string，数据接口必填 | 对应成功发布；不能由每条子查询自行取最新发布 |
| basis | AUTO / OBSERVED / RECONSTRUCTED；默认AUTO | AUTO只在一次请求开始时选择域；返回resolved_basis；后续分页由客户端传回具体basis |
| trade_date | YYYY-MM-DD；默认发布截止日 | 历史明细允许选择同snapshot中旧日；大于cutoff返回400；缺日期返回409能力不足 |
| days | integer，默认20 | 股票/成员时间线1–250；市场默认60；矩阵visible_days上限30 |
| window | integer，默认20 | 新高仅20/30/60/100；周期统计5/10/20/30 |
| page | integer，默认1 | 小于1拒绝；空结果page=1,total=0；超末页返回空items并回显页码 |
| page_size | integer，默认50 | 1–100；旧路由继续兼容原clamp，新路由越界返回400 |
| q | string，默认空 | 去首尾空白，最长80字符；字面子串搜索，%与_转义，不当SQL通配表达式 |
| sort | string，各端点有默认 | 仅白名单别名；末尾追加稳定ID；NULLS LAST；不接收SQL片段 |
| type / bucket | 枚举，默认正常属性范围 | type=INDUSTRY/THEME/STYLE；bucket按语义配置版本，不靠前端中文反查 |
| queue | STEADY/PULLBACK/BREAKOUT/LEADER/EARLY | 入参兼容_QUEUE和大小写；出参固定STEADY_QUEUE等规范值 |
| band | CORE_RESEARCH/SUPPORTED_RESEARCH/DIAGNOSTIC_ONLY | 可多个；队列默认前两项，显式空选择表示不选任何研究带 |
| price_basis | RAW / ADJUSTED；图表默认ADJUSTED | 返回adjustment_identity；原价图不附不同口径的MA曲线 |
| include | 有限字段集合 | insight默认overview,technical,sector_context；不允许include=all绕开历史分页 |
| batch_id | 在线分页必需的后续参数 | 首次解析批次返回batch_id；后续页固定批次，禁止每页取latest |

默认系统范围CN_A_LISTED_V2含沪深北A股；不提供不受合同管理的正则范围参数。未来增加范围时必须用具名配置版本。所有筛选参数进入缓存键；数组去重并排序后生成query_hash。

业务比例值均用0–1等小数表达，收益可以为负或超过1。价格、金额JSON输出有限number并附unit，精确计算仍在后端；ID一律string，数量不超过JS安全整数，否则以字符串声明。禁止输出NaN/Infinity或将NULL强转为0。

### 19.2 公共数据响应

以下为结构示例，demo标识仅用于说明，并不对应真实发布；字段间数值不用于验收市场表现。

~~~json
{
  "api_contract": "workbench-api-v2.1",
  "publication_id": "demo-publication",
  "analysis_snapshot_id": "demo-snapshot",
  "cutoff_date": "2026-09-08",
  "trade_date": "2026-09-08",
  "resolved_basis": "RECONSTRUCTED",
  "query_hash": "demo-query",
  "contracts": {
    "universe": "CN_A_LISTED_V2",
    "technical": "TECHNICAL_HISTORY_V2_1_PREVIEW"
  },
  "capabilities": {
    "technical": "AVAILABLE",
    "turnover": "UNAVAILABLE",
    "limit_state": "PARTIAL"
  },
  "data_quality": {
    "status": "PARTIAL",
    "codes": ["FLOAT_SHARES_UNAVAILABLE"],
    "field_coverage": {
      "raw_close": {"valid_count": 50, "eligible_count": 50}
    }
  },
  "page": 1,
  "page_size": 50,
  "total": 123,
  "items": []
}
~~~

列表响应使用items；单对象使用item；时间线使用points和returned_range；矩阵使用dates与items[].cells。元数据共用，不能为每个图表发明另一套basis名称。

capability枚举AVAILABLE/PARTIAL/UNAVAILABLE/NOT_BUILT；AVAILABLE不等于所有证券都有该字段，以field_coverage为准。NOT_BUILT表示尚未计算，UNAVAILABLE表示来源/历史条件不足，不能都显示“没有数据”。

若旧发布没有snapshot：旧接口仍可返回封存旧结果；新历史接口409 ANALYSIS_NOT_BUILT；新版overview可返回局部结果、analysis_snapshot_id=null和NOT_BUILT，不填造身份。

### 19.3 公共DTO字段定义

| DTO | 必需字段 | 可空或按能力提供的字段 |
|---|---|---|
| StockQuote | security_id,name,quote_date,quote_state | raw_close,quote_ret1,quote_prev_close,amount,volume,last_known_price,last_known_date |
| TechnicalState | security_id,trade_date,validity,quality_codes | ma5/10/20/60,ma_alignment,amount_vs_prior20,volume_vs_prior20,turnover_rate,ret5/10/20/60,rps5/10/20/60 |
| StructureSummary | security_id,queues[],research_band | primary_pattern,v1_grade；queues元素含queue_name,hit,tier,queue_rank,contract_id |
| StockRow | StockQuote＋TechnicalState的可见字段、StructureSummary | strength_sector、alternative_sectors、member_rank、rank_valid_count |
| SectorRow | sector_id,name,type,bucket,total_member_count | board_quote_ret1,member_ret1_median,member_amount_sum,quote_valid_count,factor_valid_count,rs20_pct,display_rank,mainline_class |
| NewHighState | security_id,window,valid_n,quality_codes | new_high,prior_max_close,dist_prior_high,streak,is_left_censored |
| Association | sector_id,name,eligible,reason_codes,contract_id | association_rank,member_rank,rank_valid_count,loo_ret20_median,loo_breadth20,loo_ret5_median,loo_breadth5 |
| EvidenceGroup | group_id,title,fields[] | summary,source_refs；field含field_id,label,value,unit,explanation,predicate_status |
| MemberChange | security_id,date,change_kind,quality_codes | previous_rank,current_rank,rank_delta；rank_delta=previous−current |
| RepresentativeEvent | date,sector_id,event_kind,confirmed_id | candidate_id,candidate_streak,confirmed_since,previous_confirmed_id |
| MarketPoint | date,universe_id,eligible_count,quality_codes | up/down/flat,quote_valid_count,amount_sum,high_counts,queue_counts,limit_counts |
| LimitRow | StockQuote＋limit_state,reference_basis,streak_known | limit_up_price,limit_down_price,streak,promotion_state,association,turnover_rate |
| SourceStatus | source_id,dataset,capability,status,last_attempt | last_success,source_as_of,cache_age_seconds,last_error |
| OnlineEvidence | evidence_id,source_id,security_id,first_seen_at,raw_ref | published_at,event_time,title,summary,source_url |
| JobStatus | job_id,job_kind,status,phase,attempt,progress | error,result_snapshot_ids,result_publication_id,resource_usage |

DTO所有缺失的可选数值显式NULL；结构不支持的字段可省略但要在field-catalog声明。identity/quality字段不藏在某个表格行的payload里。

EvidenceGroup中的源文本只当数据，前端以纯文本显示；推荐摘要由确定性模板生成。例：“近20日涨幅12.3%；20日最大回撤8.1%”，字段值仍保留带符号原值和单位，不能为了中文好看改掉原数学含义。

### 19.4 错误与兼容

~~~json
{
  "code": "ANALYSIS_NOT_BUILT",
  "message": "该发布尚未生成所选历史分析",
  "retryable": false,
  "next_action": "选择已有分析的版本，或在数据说明中提交历史分析任务",
  "details": {"required_capability": "sector_cycle", "publication_id": "demo-publication"}
}
~~~

400 INVALID_ARGUMENT/DATE_AFTER_CUTOFF；403 CSRF_REJECTED/ORIGIN_REJECTED；404 PUBLICATION_NOT_FOUND/ENTITY_NOT_FOUND；409 ANALYSIS_NOT_BUILT/BASIS_UNAVAILABLE/IDENTITY_CONFLICT/BATCH_CHANGED；413 REQUEST_TOO_LARGE；429 LOCAL_JOB_BUSY；500 INTERNAL_ERROR。旧路由原本将多种问题返回400，迁移时新错误行为在api_contract=v2.1启用，旧客户端无需依赖新的code。

POST查询也执行同源及会话校验；只读query不得写观察、配置或发布。JSON请求体最大64KB，集合运算节点有限；管理POST已有CSRF机制复用，不新建登录会员系统。日志记录request_id、参数摘要和耗时，不输出源凭据。

<a id="api-inventory"></a>
## 20. 完整接口目录与样例

表中通用参数P表示publication_id＋basis＋可选trade_date；L表示q,page,page_size,sort；W表示days或window。DTO引用第19.3章，因此接口实现无需翻看旧文。现有接口标“扩展”，新接口标“新增”。

### 20.1 基础、任务与技术接口

| ID/阶段 | 方法、完整路径、状态 | 参数/请求 | 响应与默认行为 | 后端读写 |
|---|---|---|---|---|
| API01 M7a | GET /api/publications，扩展 | include_analysis=0/1 | items含publication_id,trade_date,revision,analysis_capabilities；最新成功版本；不在GET中补算 | publications,heads,bindings |
| API02 M7a | GET /api/identity，扩展 | P | item含发布身份、snapshot各域、范围/公式版本、输入引用 | publication_artifacts,analysis_* |
| API03 M7b | GET /api/history/coverage，新增 | P,days=250 | item含各域区间、missing_dates、可观测/回算区间、预热与能力 | snapshot_entries,basis |
| API04 M7a | GET /api/universe/summary，新增 | P | item含display_count,quote_valid_count,structure_eligible_count,excluded_by_reason | universe_state_daily |
| API05 M7a | GET /api/metadata/field-catalog，新增 | api_contract,language=zh-CN | items含field_id,label,type,unit,nullable,description,sort_supported；不要求发布 | 本地字段合同注册表 |
| API06 M7b | POST /api/history/jobs，新增 | 见20.4创建样例 | 202 JobStatus；只准备分析结果，不改变默认发布头 | 现有jobs/attempts/events及分片 |
| API07 M7b | GET /api/history/jobs/{job_id}，新增 | job_id | item=JobStatus；任务不存在404 | jobs/进度缓存 |
| API08 M7b | POST /api/history/jobs/{job_id}/cancel，新增 | expected_attempt | 已提交任务不能撤销；运行任务在批次边界停止 | jobs事件，保留成功分片 |
| API09 M7b | POST /api/history/jobs/{job_id}/activate，新增 | expected_head_id,idempotency_key | 202；创建新发布修订，不覆盖旧绑定；最终publication_id由job状态返回 | 原发布编排新增分析manifest |
| API10 M8a | GET /api/stocks/technical，新增 | P,L；ma_state,rps_window,rps_min,amount_class,turnover_min | items=StockRow；默认rps20降序、ret20降序、security_id升序 | technical,rps,结构摘要 |
| API11 M8a | GET /api/stocks/new-highs，新增 | P,L,window；streak_min,include_ties=false,rps_min | items=StockRow＋NewHighState；默认streak降序、rps20降序、ID | high_daily,technical |
| API12 M8a | GET /api/stocks/{security_id}/technical-history，新增 | P,days=20,price_basis,fields | points=日期、同基准OHLC/MA、成交额、RPS；点数≤days；明确gap | quote/technical/rps分片 |
| API13 M8b | GET /api/stocks/{security_id}/structure-history，新增 | P,days=20,queue | points含hit,tier,transition,source_basis；最早已知日期不称首次历史命中 | historical_structure_daily |
| API14 M8b | GET /api/queues，扩展 | P,L,queue,band；include_analysis=1 | items=StockRow；始终按合同queue_rank升序，额外排序须显式另列显示排名 | 队列、排名、technical |
| API15 M7a/M12 | GET /api/evidence，扩展 | P,queue,security_id；format=groups | item含summary,groups,contracts；无证据返回item=null＋状态 | details/历史结构证据 |

API10筛选NULL字段时默认不命中数值比较，回包quality保留可用字段；可通过quality_filter=INCLUDE_UNKNOWN查看未知。未提供任何技术筛选时不能仅因MA60未知隐藏报价行。

API14旧参数别名继续支持；queue_rank与filtered_row_number分开，搜索或翻页不能重排合同名次；CORE/SUPPORTED映射来自现有MAPPINGS，DIAGNOSTIC不参与强势成员资格。

### 20.2 板块、主线、联动与个股接口

| ID/阶段 | 方法、完整路径、状态 | 参数/请求 | 响应与默认行为 | 后端读写 |
|---|---|---|---|---|
| API16 M9 | GET /api/sectors，扩展 | P,L,type；include_analysis=1 | items=SectorRow；正常属性默认，主列分别显示报价/金额/成员数 | sector_base,cycle,semantics |
| API17 M9 | GET /api/sectors/cycle，新增 | P,L,type,window=10,visible_days=10,metric=rank | dates＋items[].cells；默认当前rs20_pct降序、ID | sector_cycle分片 |
| API18 M9 | GET /api/sectors/{sector_id}/timeline，新增 | P,days=30 | points含rank/pct/breadth/amount/coverage；不拼观测与回算 | sector_cycle |
| API19 M9 | GET /api/sectors/{sector_id}/members/history，新增 | P,L,days=10；state=ALL/ENTERED/EXITED/RETAINED/UNKNOWN,security_id可选 | items=MemberChange；日期降序再ID；成员增删与强弱变化分开 | member_state,changes |
| API20 M9 | GET /api/sectors/{sector_id}/leader-history，新增 | P,days=30 | points=RepresentativeEvent和每日候选/确认；名称叫强势代表 | representative_state/events |
| API21 M10 | GET /api/mainlines，新增 | P,L,class,type,window=20 | items=SectorRow＋class/predicates摘要；默认同类P降序 | mainline_daily,cycle |
| API22 M10 | GET /api/mainlines/{sector_id}/evidence，新增 | P | item=EvidenceGroup[]＋classification_order＋missing_fields | mainline predicates |
| API23 M11 | GET /api/sector-library，新增 | P,L,type,bucket | items含语义、total/valid_count、source；默认名称、ID | semantics,membership |
| API24 M11 | POST /api/sector-intersection/query，新增 | P,L在JSON内；见20.4样例 | items=StockRow＋matched_sector_ids；先集合/筛选后分页；默认rps20降序 | membership＋技术/结构 |
| API25 M11 | GET /api/linkage，扩展 | P,L；sector_id或security_id至少一个 | items=StockRow＋Association/成员名次；板块内排名先于筛选 | membership,member_state,association |
| API26 M11 | GET /api/linkage/history，新增 | P,L,sector_id,days=10,security_id可选 | items为日期/个股名次与状态；默认日期降序、名次升序 | member_state,changes |
| API27 M11 | GET /api/stocks/{security_id}/memberships，新增 | P；bucket可选 | items=SectorRow分组；包含标签但不当强势关联 | membership,semantics |
| API28 M11 | GET /api/stocks/{security_id}/sector-associations，新增 | P,days=1；include_rejected=false；page/page_size用于拒绝明细 | items=Association；默认主选＋至多两备选；历史按日分组 | association分片 |
| API29 M12 | GET /api/stocks/{security_id}/insight，新增 | P,include,days=20 | item={overview,technical,structures,sector_context}；默认不含K线长序列 | 复用已有service聚合 |
| API30 M15 | GET /api/dashboard，扩展 | P；include_analysis=1 | item含market_summary,strong_sectors,mainline_counts,representatives；优先研究列表另分页 | market/cycle/mainline/association |
| API31 M8/M15 | GET /api/candidates，扩展 | P,L,grade,pattern；include_analysis=1 | items=StockRow；保留现有V1排序合同，新字段作附加 | candidates/technical/association |

API17仅对当前选定板块行取历史列，不每个日期独立取Top-N后拼成错位矩阵。cells按dates顺序，可空，含date,display_rank,rs20_pct,change_state,quality_codes；visible_days与window分开。最多100行×30列，默认20行；API17的page_size默认20覆盖公共默认50。

API19/26是分页事件/日期行而非全成员×全日笛卡尔积；针对完整成员状态单日下钻通过API25。API28 days>1时限制250天，每天至多3个已选关联；include_rejected=true只允许days=1且最多100条分页，避免拉取所有历史拒绝证据。

### 20.3 市场和在线接口

| ID/阶段 | 方法、完整路径、状态 | 参数/请求 | 响应 | 后端读写 |
|---|---|---|---|---|
| API32 M13a | GET /api/market/cycle，新增 | P,days=60,metrics | points=MarketPoint；metrics白名单；未知画缺口 | market_cycle |
| API33 M13a | GET /api/market/day-detail，新增 | P；trade_date必填 | item含计数/分母/coverage及下钻查询参数，不内嵌股票全集 | market聚合 |
| API34 M13b | GET /api/limit-ladder，新增 | P,L,level=ALL/1/2/3/4PLUS,state,promotion | items=LimitRow；层级降序、金额降序、ID；UNKNOWN独立筛选 | limit_ladder,reference |
| API35 M13b | GET /api/limit-ladder/promotion-history，新增 | P,days=30,previous_level | points含success_count,eligible_count,excluded_unknown/suspended/no_limit,rate | limit晋级聚合 |
| API36 M14 | GET /api/data-sources/status，新增 | source_id可选 | items=SourceStatus；全局状态无需publication | sources,fetch_runs |
| API37 M14 | GET /api/hot-rankings，新增 | P,source,list_type,batch_id,L；mode=AS_OF/LATEST,co_listed | items=StockQuote＋platform_rank/rank_change/batch；默认平台原名次 | online batches/rank entries |
| API38 M14 | GET /api/stocks/{security_id}/external-evidence，新增 | P,type,mode=AS_OF/LATEST,page/page_size | items=OnlineEvidence＋source_as_of；事后补充独立分组 | online_evidence |
| API39 M14可选 | GET /api/quotes/latest，新增 | security_ids≤50；source | item/报价数组＋batch_id/source_as_of；不要求本地publication | 独立在线报价批次 |
| API40 M14 | POST /api/data-sources/{source_id}/refresh，新增 | dataset,idempotency_key | 202 fetch job；受频率限制；不在GET访问时无限抓取 | fetch_runs/任务队列 |

API37初次mode=AS_OF按本地cutoff与观测时间选择合规批次；mode=LATEST须UI明确选择盘中视图。已固定batch的后续分页不重新解析。跨平台同时上榜返回两个batch_id组成batch_set_id，后续分页固定整个batch_set；超过15分钟不同步不称同时。

### 20.4 三个完整请求样例

示例ID为占位说明；body中的日期和source_snapshot必须由后端核验，不可照例直接提交真实任务。

历史分析准备（POST API06）：

~~~json
{
  "base_publication_id": "demo-publication",
  "basis": "RECONSTRUCTED",
  "output_days": 250,
  "domains": ["technical", "structure", "sector_cycle", "mainline", "market"],
  "membership_snapshot_id": "demo-membership",
  "contract_bundle_id": "workbench-contract-bundle-v2.1-preview",
  "idempotency_key": "demo-history-request"
}
~~~

后端先解析完整依赖（不能只算mainline不补sector_cycle），检查输入冻结状态和预热，返回job_id、planned_domains、required_range与estimated_work。没有可靠来源则返回missing_capabilities；客户端不能用ignore_validation跳过。取消只停止未完成计算；activate必须expected_head_id与实际一致，不一致409让调用方刷新版本信息。

交叉筛选（POST API24）：

~~~json
{
  "publication_id": "demo-publication",
  "basis": "RECONSTRUCTED",
  "trade_date": "2026-09-08",
  "include_sector_ids": ["THEME:demo-a", "INDUSTRY:demo-b"],
  "operator": "INTERSECTION",
  "exclude_sector_ids": [],
  "filters": {
    "queues_any": ["STEADY_QUEUE", "LEADER_QUEUE"],
    "bands": ["CORE_RESEARCH", "SUPPORTED_RESEARCH"],
    "new_high_window": 20,
    "ma_alignment": "BULL",
    "amount_vs_prior20_min": 1.5,
    "rps20_min": 0.8
  },
  "sort": "rps20.desc",
  "page": 1,
  "page_size": 50
}
~~~

filters内部不同字段AND，queues_any内OR；空数组语义在field-catalog声明：queues_any=[]为不施加队列筛选，bands=[]为显式无研究带则结果为空；UI清空筛选应删除字段，不发送歧义空数组。SQL参数绑定、排除集合优先级在第11章固定。

个股首屏（GET API29，省略URL编码展示）：

~~~text
/api/stocks/SH.600000/insight?publication_id=demo-publication&basis=RECONSTRUCTED&include=overview,technical,sector_context
~~~

~~~json
{
  "api_contract": "workbench-api-v2.1",
  "publication_id": "demo-publication",
  "analysis_snapshot_id": "demo-snapshot",
  "resolved_basis": "RECONSTRUCTED",
  "cutoff_date": "2026-09-08",
  "trade_date": "2026-09-08",
  "item": {
    "overview": {
      "security_id": "SH.600000",
      "name": "示例股票",
      "raw_close": 10.2,
      "quote_ret1": 0.02,
      "amount": 1620000000,
      "quote_state": "VALID"
    },
    "technical": {
      "ma20": 9.8,
      "rps20": 0.85,
      "turnover_rate": null,
      "quality_codes": ["FLOAT_SHARES_UNAVAILABLE"]
    },
    "sector_context": {
      "primary": null,
      "alternatives": [],
      "reason": "暂无可确认的强势关联板块"
    }
  }
}
~~~

金额格式化显示16.2亿；UI不能把NULL关联回退为“近期强势”。实际出参补公共contracts/capabilities/data_quality；此例仅省略重复元数据以展示嵌套。

### 20.5 旧接口与新页面兼容清单

现有/api/input/latest、/api/jobs、/api/operations/*和/operations继续保留，不更名以免破坏运维。API06–09使用独立history job类型但共用任务状态存储；不要把只生成分析误接到“下载并生成今日数据”。

所有扩展接口默认旧模式；include_analysis=1启用新字段/口径，并回显api_contract。新页面首屏先读API01/02确定能力，再请求API30/31；不能并行猜测快照ID。完成解析之后可并行取可见区块。

资源新增/static/v2/*白名单路由，需支持JS/CSS MIME与缓存版本；/v2加载完整新布局，旧/view保持薄壳回看。UI主入口切换属于M15，不以新增API成功自动切换。


<a id="database-contract"></a>
## 21. 数据库实施清单：字段、约束、迁移和兼容

本章是第6章的物理展开。新增表命名固定如下；不再留“可以长表也可以宽表”等二选一决定。高容量Parquet域使用相同字段合同，但不同时在DuckDB保存重复全量副本。少量可检索索引和聚合可以冗余，必须附同slice_id。

### 21.1 通用字段和类型

S=VARCHAR；D=DATE；TS=UTC TIMESTAMP；I=BIGINT；F=DOUBLE；B=BOOLEAN；J=JSON；P=DECIMAL(18,4)。金额保持F原始元值，聚合可采用Decimal降低累加误差但不提高原输入精度。带!表示NOT NULL，未带!可空。

所有slice日表含slice_id:S!、trade_date:D!、quality_codes:J!。成功分片只包含一种domain/trade_date/basis；批量校验实体trade_date等于slice元数据。缺失值可空，quality_codes默认[]，证据payload默认{}，不是用空字符串表示未知。

FK指现有DuckDB同库可建立的引用；跨Parquet/外部对象由清单校验执行器实现逻辑FK并记录回执。不得声称DuckDB会自动检查Parquet外键。

### 21.2 管理表与身份表

| 表 | 主键 | 完整核心字段（主键字段不再重复） | 验证/迁移 |
|---|---|---|---|
| schema_migration_checks | version:S | sql_sha256:S!,dependencies:J!,previous_manifest_hash:S!,applied_at:TS!,receipt_id:S! | 与现有schema_migrations同事务登记；依赖版本全部存在；已执行版本SQL改动拒绝 |
| analysis_slices | slice_id:S | domain:S!,trade_date:D!,contract_id:S!,input_hash:S!,dependency_hash:S!,basis_json:J!,row_count:I!,logical_hash:S!,storage_kind:S!,storage_object_id:S,created_at:TS! | PK内容确定；row_count≥0；storage_kind=DUCKDB/PARQUET；仅成功sealed对象进入此表 |
| analysis_slice_dependencies | slice_id:S,input_domain:S,input_date:D,input_slice_id:S | 无其它必需字段 | 逻辑无环；记录跨日窗口依赖便于失效传播 |
| analysis_snapshots | snapshot_id:S | cutoff_date:D!,query_start:D!,universe_contract:S!,config_hash:S!,manifest_hash:S!,status:S!,created_at:TS! | query_start≤cutoff；正式引用只接受SUCCESS |
| analysis_snapshot_entries | snapshot_id:S,domain:S,trade_date:D | slice_id:S! | FK snapshot/slice；date/domain一致；不得日期越界 |
| publication_analysis_snapshots | publication_id:S,domain:S | snapshot_id:S!,bound_at:TS! | domain=LOCAL_OBSERVED/LOCAL_RECONSTRUCTED；不可UPDATE成功绑定 |
| analysis_daily_basis | slice_id:S | universe_basis:S!,membership_snapshot_id:S,price_basis:S!,adjustment_as_of:D,source_observed_at:TS,coverage:F,capabilities_json:J! | coverage在[0,1]或NULL |
| membership_snapshot_metadata | membership_snapshot_id:S | observed_at:TS!,source_effective_date:D,source_freshness:S!,source_hash:S!,semantic_version:S! | 扩展旧表的旁表；不改旧logical_sha256 |
| sector_semantic_versions | version_id:S,sector_id:S | bucket:S!,rule_id:S!,reason:S!,valid_from:D,observed_at:TS!,override:B!,source_id:S! | 同version同ID唯一；旧版本不改 |
| security_metadata_versions | security_id:S,version_id:S | exchange:S!,board:S,security_kind:S!,listing_status:S!,valid_from:D,valid_to:D,observed_at:TS!,source_id:S!,source_ref:S! | UNKNOWN明示；不可重叠有效段仅对同一权威来源施加 |
| universe_state_daily | slice_id:S,security_id:S | exchange:S!,display_eligible:B!,quote_eligible:B!,structure_eligible:B!,listing_state:S!,exclusion_reason:S,metadata_version:S! | 加日表公共字段；不同资格分别记录 |
| market_reference_daily | slice_id:S,security_id:S | quote_prev_close:P,limit_up_price:P,limit_down_price:P,float_shares:F,shares_basis:S,status_known:B!,rule_id:S,source_ref:S,observed_at:TS | 加公共字段；缺来源不可标精确参考价 |
| limit_rule_versions | rule_id:S | exchange:S!,board:S!,risk_status:S!,valid_from:D!,valid_to:D,limit_ratio:F,tick:P!,rounding_mode:S!,special_period_policy:J!,source_ref:S! | 同适用条件有效期冲突拒绝；规则值有官方文件支持 |

不创建第二套analysis_jobs表：使用现有jobs、job_attempts、job_events，payload.job_kind=HISTORY_ANALYSIS/HISTORY_ACTIVATION/ONLINE_FETCH，增加稳定的parent_job_id、request_identity、contract_bundle_id、planned_domains、completed_slice_ids引用。大清单放对象，jobs JSON只存清单引用，避免写入数百万行进度。

### 21.3 行情、技术、新高和结构表

| 表/域 | 实体PK（均加slice_id） | 物理字段 |
|---|---|---|
| stock_quote_daily（DUCKDB） | security_id:S | name:S!,raw_open/high/low/close:P,raw_volume:I,raw_amount:F,quote_prev_close:P,quote_ret1:F,quote_ret1_basis:S!,has_actual_bar:B!,missing_state:S!,quote_date:D!,last_known_price:P,last_known_date:D,source_ref:S! |
| stock_technical_daily（DUCKDB） | security_id:S | adj_close:P,ma5/10/20/60:P,ma_alignment:S!,above_ma5/10/20/60:B,amount_ma5/10/20:F,amount_ratio20_legacy:F,amount_ratio_5_20_legacy:F,amount_vs_prior20:F,volume_vs_prior20:F,amount_class:S!,volume_class:S!,amount_streak:I,volume_streak:I,turnover_rate:F,turnover_basis:S,validity:J!,adjustment_identity:S! |
| stock_strength_daily（DUCKDB长表） | security_id:S,window:I | ret:F,rs:F,rps:F,valid_n:I!,eligible_n:I!,contract_id:S!；window=5/10/20/60 |
| stock_high_daily（DUCKDB长表） | security_id:S,window:I | prior_max_close:P,new_high:B,at_prior_high:B,dist_prior_high:F,streak:I,is_left_censored:B!,valid_n:I!,contract_id:S!；window=20/30/60/100 |
| historical_structure_daily（PARQUET） | security_id:S,queue_name:S | hit:B,tier:S,source_class:S,research_band:S,queue_rank:I,tier_rank:I,transition:S,structure_basis:S!,contract_id:S!,evidence:J! |
| stock_structure_summary_daily（DUCKDB） | security_id:S | queues_json:J!,research_band:S!,primary_pattern:S,v1_grade:S,unique_hit_count:I,queue_contract:S! |

MA列展开为真实四列；SQL中不得出现含斜杠的列名。表格中斜杠仅是多个同类型字段的紧凑声明。quote_date和trade_date通常相同，last_known_date另存；不可把最后已知价格移入当日raw_close。

stock_strength_daily补rps而不改原RS字段合同；summary.hit_count仅为展示计数，不用于加权评级。source_class保留细类（如STEADY_CORE）；tier限CORE/SUPPORTED/NULL；research_band使用第19章枚举。

历史K线需要同一图表锚：API12从已冻结raw_quote和公司行为输入，按所选adjustment_as_of统一变换整个显示区间并计算同基准MA，缓存键包含snapshot_id、security_id、price_basis、adjustment_as_of、days、fields、contract。不能直接拼接“各历史日各自锚”的adj_close与MA。这个按需单股变换不运行全市场scanner；历史结构证据仍引用各目标日计算身份。API12返回chart_basis与factor_evidence_basis说明，两种用途不能混淆。

### 21.4 板块与市场表

| 表/域 | 实体PK（均加slice_id） | 物理字段 |
|---|---|---|
| sector_base_daily（DUCKDB） | sector_id:S | name:S!,type:S!,bucket:S!,sector_valid:B!,total_member_count:I!,quote_valid_count:I!,factor_valid_count:I!,coverage:F,rs5/10/20/60:F,rs5_pct/rs20_pct:F,display_rank:I,base_pattern:S,base_predicates:J!,semantic_version:S!,membership_snapshot_id:S! |
| sector_cycle_daily（DUCKDB） | sector_id:S | board_quote_ret1:F,board_quote_source:S,member_ret1_median:F,member_amount_sum:F,amount_valid_count:I!,amount_vs_prior20:F,breadth_ret1:F,breadth_ma20:F,strong_count:I,high20/30/60/100_count:I,high20/30/60/100_valid_count:I,rank_change:I,comparable_count:I,previous_strong_total:I,comparable_previous_strong:I,retained_count:I,entered_count:I,exited_count:I,uncomparable_count:I,retention_rate:F,comparison_coverage:F,diffusion_state:S!,window_stats:J! |
| sector_member_state_daily（PARQUET） | sector_id:S,security_id:S | member_rank:I,rank_valid_count:I!,ret20_pct:F,strong_state:B,strong_predicates:J!,member_change_kind:S,strength_change_kind:S,previous_rank:I,rank_delta:I,queue_refs:J!,high_refs:J! |
| sector_membership_changes（PARQUET） | sector_id:S,security_id:S,change_type:S | previous_snapshot_id:S,current_snapshot_id:S!,observed_interval_start:TS,observed_interval_end:TS!,reason:S! |
| representative_state_daily（DUCKDB） | sector_id:S | ranked_first_id:S,ranked_second_id:S,rank_gap:F,confirmed_id:S,candidate_id:S,candidate_since:D,candidate_streak:I,confirmed_since:D,confirmation_event:S,previous_confirmed_id:S,stale:B! |
| stock_sector_associations_daily（PARQUET） | security_id:S,sector_id:S | eligible:B!,association_rank:I,bucket:S!,member_rank:I,rank_valid_count:I,member_percentile:F,loo_ret20_median:F,loo_breadth20:F,loo_ret5_median:F,loo_breadth5:F,reject_codes:J!,contract_id:S!,sort_tuple:J! |
| mainline_daily（DUCKDB） | sector_id:S | class:S!,previous_class:S,transition_reason:S!,predicates:J!,valid_windows:J!,missing_fields:J!,conflict_resolution:J!,contract_id:S!,config_hash:S! |
| market_cycle_daily（DUCKDB） | universe_id:S | display_count:I!,quote_valid_count:I!,up_count:I,down_count:I,flat_count:I,amount_sum:F,amount_valid_count:I!,ma20_above_count:I,ma20_valid_count:I,ma60_above_count:I,ma60_valid_count:I,new_high_counts:J!,queue_counts:J!,queue_unique_count:I,sector_state_counts:J!,limit_up_count:I,limit_down_count:I,unknown_limit_count:I,field_coverage:J! |
| limit_ladder_daily（DUCKDB） | security_id:S | limit_state:S!,reference_basis:S!,rule_id:S,limit_up_price:P,limit_down_price:P,streak:I,streak_known:B!,streak_min_known:I,previous_streak:I,ladder_level:S,promotion_state:S!,denominator_eligible:B!,exclusion_reason:S,association_ref:S |
| limit_promotion_daily（DUCKDB） | previous_level:I | success_count:I!,eligible_count:I!,excluded_unknown:I!,excluded_suspended:I!,excluded_no_limit:I!,rate:F |

cycle.window_stats固定JSON键5/10/20/30，每项包含valid_days,on_list_days,consecutive_on_list,rank_pct_mean,rank_pct_first,last,breadth_change,amount_change；常用查询的on_list_days5/10/20/30及consecutive_on_list在DDL中提升为实体列。禁止主线SQL全表解析JSON来筛选。high各窗口的宽度=相应count/valid_count；valid_count=0时NULL。

sector_member.rank_valid_count是该排序指标有效人数，total_member_count可更大；不能为了“第N名/共M只”显示一致而剔除用户应看到的无行情成员。unknown成员名次NULL，列表末尾可见。

联动排名默认复用板块成员已算rank。五类队列保持各自合同rank，不能拿联动RET20名次替代队内名次。代表股排名采用第9.3章合同独立产出，并附representative_rank_basis，不暗示两个排名必然相同。

### 21.5 在线表

| 表 | PK | 字段和约束 |
|---|---|---|
| data_sources | source_id:S | name:S!,source_class:S!,adapter_version:S!,enabled:B!,terms_state:S!,capabilities:J!,cache_policy:J!,documentation_ref:S |
| online_fetch_runs | fetch_id:S | source_id:S!,dataset:S!,requested_at/received_at:TS,status:S!,error_code:S,http_status:I,raw_hash:S,adapter_version:S! |
| online_payloads | raw_hash:S | storage_object_id:S!,schema_version:S!,byte_count:I!；raw_hash内容去重，不能替代fetch_id |
| online_batches | batch_id:S | fetch_id:S!,dataset:S!,trade_date:D,source_as_of:TS,first_seen_at:TS!,status:S!,row_count:I!,logical_hash:S!,adapter_version:S! |
| online_rank_entries | batch_id:S,list_type:S,security_id:S | platform_rank:I!,previous_rank:I,comparison_batch_id:S,rank_change_basis:S,source_code:S!,extra:J! |
| online_evidence | evidence_id:S | source_id:S!,security_id:S!,event_time:TS,published_at:TS,first_seen_at:TS!,title:S,summary:S,text_hash:S!,raw_ref:S!,source_url:S |
| online_security_map | source_id:S,source_code:S,valid_from:D | security_id:S!,exchange:S!,valid_to:D,mapping_version:S!,evidence_ref:S! |
| online_quote_entries | batch_id:S,security_id:S | quote_time:TS!,price:P,ret1:F,amount:F,volume:I,quote_state:S!,source_code:S! |

所有online数据表只由一个写入协调器登记。stock_external_evidence仅作为查询层聚合视图名称：由online_evidence与online_rank_entries形成只读DTO，不同时存一套重复正文表。

### 21.6 迁移批次与SQL骨架

迁移拆成007_history_identity、008_technical_history、009_sector_cycle、010_mainline、011_association_library、012_insight_support、013_market_ladder、014_online；015仅在验收发现必须索引/约束变更时新增。迁移按声明依赖拓扑排序，编号对应工作包，不强制数字连续；同一owner串行执行每批DDL。012无必要DDL时只登记已校验的兼容版本，不强行建表。

依赖固定为：007依赖现有workbench-schema-v1.0；008依赖007；009依赖008；010依赖009；011依赖009；012依赖008和011；013依赖008；014依赖007。015依赖最终启用的全部迁移集合。007完成管理表、universe、快照和reference/规则；008完成quote/technical/strength/high/structure；009完成cycle/代表/成员登记；013创建market_cycle_daily、limit_ladder_daily和limit_promotion_daily；014创建在线表。因此M13可在M8后应用013，M14可在M7后应用014，不被M9–M12无关DDL阻塞。schema版本清单按已应用节点集合哈希记录，不再用单个最大编号判断全部准备完成。表存在但尚未计算的能力仍为NOT_BUILT。

下面是007关键DDL样例，可直接转为迁移文件的一部分；全部其它表按21.2–21.5生成并在迁移测试中验证实际columns、PK、FK和NULL约束。样例不是已部署迁移：

~~~sql
CREATE TABLE analysis_snapshots (
    snapshot_id VARCHAR PRIMARY KEY,
    cutoff_date DATE NOT NULL,
    query_start DATE NOT NULL,
    universe_contract VARCHAR NOT NULL,
    config_hash VARCHAR NOT NULL,
    manifest_hash VARCHAR NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('PREPARED','SUCCESS','FAILED')),
    created_at TIMESTAMP NOT NULL,
    CHECK (query_start <= cutoff_date)
);
CREATE TABLE publication_analysis_snapshots (
    publication_id VARCHAR NOT NULL REFERENCES publications(publication_id),
    domain VARCHAR NOT NULL CHECK (domain IN ('LOCAL_OBSERVED','LOCAL_RECONSTRUCTED')),
    snapshot_id VARCHAR NOT NULL REFERENCES analysis_snapshots(snapshot_id),
    bound_at TIMESTAMP NOT NULL,
    PRIMARY KEY (publication_id, domain)
);
CREATE TABLE schema_migration_checks (
    version VARCHAR PRIMARY KEY,
    sql_sha256 VARCHAR NOT NULL,
    dependencies JSON NOT NULL,
    previous_manifest_hash VARCHAR NOT NULL,
    applied_at TIMESTAMP NOT NULL,
    receipt_id VARCHAR NOT NULL
);
~~~

SQL不能表达的条件由提交前校验器统一检查：snapshot SUCCESS、cutoff与publication一致、entries完整、domain/date与slice相符、输入哈希可验证、同identity内容相等。恢复旧版本时保留兼容schema读能力，或恢复备份；不自动运行破坏性DOWN迁移。

### 21.7 缓存、索引与容量的具体规则

- 服务缓存使用LRU与总字节预算（默认256MiB，可配置），大历史对象不要无限放入字典；首屏、矩阵、单股图分别统计命中。
- local cache key=(api_contract,snapshot_id,endpoint,query_hash)；online key含batch_id/batch_set_id；schema/公式版本在snapshot/config身份内。
- 初始DuckDB索引只建quote/technical按security_id+trade_date及sector_cycle按sector_id+trade_date等实测有效组合；unique约束本身的索引不重复创建。对于低选择性RPS范围不默认承诺索引加速。
- Parquet成员分片按trade_date/domain分目录，slice_id文件名。可增加同分片轻量sector_id/行组统计索引，不能建立遍历全部旧发布的glob查询。
- 物理GC只处理未被任一成功发布、准备中job或lease引用的对象；禁止以“旧于30日”直接删历史分片。
- 同包相同经济内容重试复用slice；不同source_bundle仅因封装变化不使全历史失效；输入历史修订记录依赖传播。


<a id="implementation-tasks"></a>
## 22. 按开发工作包拆解：输入、步骤、产物、通过条件

本章是执行清单，不是建议菜单。API编号引用第20章；具体字段引用第21章；算法引用第7–14章。每个工作包先完成后端与测试，再接可见页面切片。非依赖工作包可并行；不允许越过前置门消耗不存在的数据。

新增统一开发入口run_workbench_upgrade.py（计划新增，不是现有命令），参数：
--stage M7A/M7B/M8A/M8B/M8C/M9/M10/M11/M12/M13A/M13B/M14/M15；
--mode plan/build/verify/activate；--publication-id；--basis；--output-days；--root。
plan只读列依赖/能力；build产生未激活分片；verify生成回执；activate走新修订且检查expected-head-id。缺参数直接报错；不要把build默认等同activate。前端任务API和CLI共用service，不能两套计算。

### 22.1 M7A：先处理现有界面数据正确性

| 任务 | 输入/改动步骤 | 交付物 | 验收 |
|---|---|---|---|
| 7A-01 基线封存 | 读取M0–M6回执、源码/输入/合同哈希、当前发布头、已有页面截图；标示dirty工作区 | reports/upgrade_m7/baseline.json，M6状态字段 | 不以开发预检覆盖外审状态 |
| 7A-02 股票范围 | 新universe服务使用身份元数据＋前缀校验；拆显示/报价/结构资格；沪深北合并统一 | API04、universe合同、排除原因 | B股/新三板排除；BJ股票纳入；未知不当退市 |
| 7A-03 报价绑定 | 封存raw报价/参考前收来源；旧发布只读已验证输入；修复上一发布日期计算RET1 | API10/31所用QuoteService；旧字段兼容 | T01/T02/T04；无源旧报价显示未封存 |
| 7A-04 语义基础 | 读取现有semantic_bucket及roles；规则版本与ID精确覆盖；标签与属性分开 | semantic registry、007表内容准备 | 近期强势/昨日首板不进入正常强势板块 |
| 7A-05 UI公共层 | 创建/v2路由、api.js/format.js/table.js/modal.js；顶栏与导航骨架 | 新预览页、API05；旧/view仍可读 | 证据按钮不撑表；金额一致；无全量内嵌 |
| 7A-06 合同目录 | 固定dto与中文映射，扩展API01/02能力字段 | field-catalog、api-contract-v2.1 | 所有表头/枚举都有映射 |

M7A阶段的范围/报价服务先从所选发布已冻结输入和现有表读取，提供可测试的纯函数/预览响应；API04不能提前查询尚未创建的universe_state_daily。M7B完成007后切换到持久化查询；M8A完成008后QuoteService读取封存日表，两个后端适配必须通过同一组合同样例。

进入M7B门：核心价格/日期/范围没有已知错误；旧报价确实无证据的行允许明确缺失，不允许用猜测补齐。M6待外审不阻止预览开发，但阻止正式切换。

### 22.2 M7B：历史仓和发布身份

| 任务 | 输入/步骤 | 产物 | 验收 |
|---|---|---|---|
| 7B-01 schema执行器 | 在Repository前置执行有序迁移；将路径迁移服务与DDL迁移分开 | 007迁移、hash checks、备份回执 | 故意坏SQL整批回滚，版本不提前登记 |
| 7B-02 窗口规划器 | 读取因子/结构的window依赖，计算output_start与read_start；识别缺日 | WindowPlan、API03 | 250输出＋100新高/其它最大依赖预热覆盖 |
| 7B-03 输入冻结 | 将实际所需raw/事件/成员复制或引用已封存工作区对象；记录observed/effective | SourceManifest，不写TDX | 输入改变检测、哈希复核 |
| 7B-04 分片计算协调 | 证券批读取、内容hash、dependency hash、临时对象、校验后seal | analysis_slices及objects | 同内容重用；新增日不全量复制 |
| 7B-05 任务状态 | 共用jobs/attempts/events，增HISTORY_ANALYSIS任务与取消点 | API06–08及CLI | 中断可续、cancel不删成功分片 |
| 7B-06 快照激活 | 预计算snapshot清单；PublicationRequest与发布身份纳入manifest；新修订短事务 | API09，publication绑定 | T14；同身份不同内容拒绝 |
| 7B-07 恢复与清理 | DB＋引用对象备份、恢复校验、lease、未引用对象预览 | 新备份清单和恢复报告 | T15/T20/T21 |

进入M8门：至少一个短窗口完成分片读取/重算/重试/激活全链路；完整250日可在M8依赖齐备后完成，不要求M7用尚不存在的结构模块预先生成最终250日结构。

### 22.3 M8A/M8B/M8C：基础生产

| 任务 | 前置/步骤 | 交付物 | 验收 |
|---|---|---|---|
| 8A-01 技术因子 | M7B；复用旧MA/RET/金额公式，新增量额比独立字段 | 008、technical长/宽表、API10 | 旧值不变、新值有独立合同 |
| 8A-02 新高/RPS | 固定四新高窗及四RPS窗；并列平均rank/N；分窗streak | API11、high/strength表 | T06/T07/T24；横盘不新高 |
| 8A-03 图表变换 | 从冻结raw按同一锚生成OHLC/MA，有限窗口缓存 | API12 | 原价/复权选择、缺口、同锚一致 |
| 8A-04 技术页 | 新高窗筛选、RPS门槛、均线/量額状态、分页 | 个股研究/创新高-RPS | NULL筛选与排序正确 |
| 8B-01 历史基础板块 | technical→截面RS→sector_base→板块scanner；保留旧snapshot_guard | 独立history adapter | 无去守卫强行回填 |
| 8B-02 五类历史 | 调用现有纯函数，保存CORE/SUPPORTED/未知及队列rank | historical_structure、API13/14/15 | T19；observations/outcomes不改变 |
| 8B-03 日级覆盖 | 按日期记录结构/成员/价格basis和能力，输出历史队列数量 | 市场聚合输入 | 回算与真实观察分开 |
| 8C-01 参考价/股本 | 对字段源、日期、单位出能力清单，缺失NULL；登记规则版本 | 007参考表数据、能力回执 | 股数/手/金额单位验证 |
| 8C-02 涨跌停规则 | 完成官方规则生效表与边界fixture；Decimal计算 | LimitStateService | 除权/ST/新股特殊期/未知样本 |
| 8C-03 降级门 | 按证券/日期统计精确、近似、未知比例 | reference_capability_report.json | 未验证能力不标AVAILABLE |

M9依赖8B完成；M13A可在8A完成后开始，队列图等待8B。8C无可靠股本不阻断M9，但换手率功能不能算已完整交付。

### 22.4 M9：板块周期

| 任务 | 步骤 | 产物/API | 验收 |
|---|---|---|---|
| 9-01 板块日向量 | 同类排名、板块报价来源、成员金额/中位数/各类有效数；不跨板块重复求和 | 009、API16/18 | T08；报价与中位数分列 |
| 9-02 强势集合 | 从历史结构/新高/百分位生成三态强势状态，固定共同成员集合 | member_state/changes，API19/26输入 | T09；成员删除不误当转弱 |
| 9-03 代表状态机 | 候选/确认/旧确认stale，独立事件日期；首位与确认股分列 | representative_state、API20 | T10三种序列 |
| 9-04 窗口矩阵 | 固定当前选定20板块行，按dates关联历史cell；计算5/10/20/30统计 | API17 | 无日期错行；缺日空cell |
| 9-05 板块详情UI | 强度/宽度/量額、共同成员变化、代表时间线 | 板块研究二级页 | 热p95目标；200默认cell |

进入M10门：矩阵点值、留存集合和代表事件可独立复算；历史basis可识别；所有来源不足字段有明确状态。

### 22.5 M10：主线

| 任务 | 步骤 | 产物/API | 验收 |
|---|---|---|---|
| 10-01 合同配置 | 将第10章顺序、窗口、门槛写入mainline-v2.1-preview.yaml | config hash与predicate registry | 无隐藏权重/隐式默认门槛 |
| 10-02 三态分类 | 逐predicate求值、记录unknown/冲突；输出唯一class | 010、API21/22 | T11；从未强不能退潮 |
| 10-03 状态变化 | 对比同basis/同合同前日；版本切换为MODEL_CHANGE | mainline transition字段 | 合同更新不冒充市场变化 |
| 10-04 主线页 | 状态卡筛选、表格、分组证据弹窗；保留观察期 | 板块研究/主线 | 数量与筛选结果一致 |

首版参数可以直接实施；验收验证规则执行与解释一致，不承诺金融有效性。未来改参数须新contract_id。

### 22.6 M11：属性库、集合、关联

| 任务 | 步骤 | 产物/API | 验收 |
|---|---|---|---|
| 11-01 属性查询 | 使用M7A语义快照，搜索/筛选/成员数 | API23/27 | 类型与标签隔离，ID覆盖可追溯 |
| 11-02 集合执行器 | include交/并→exclude→同snapshot过滤→count→分页 | API24 | 两到四板块手算、空数组与NULL |
| 11-03 关联预计算 | 保留原leave-one-out门槛；拒绝原因、主选/备选结果分片 | 011、API28 | T12；不按行业固定优先 |
| 11-04 联动一致 | 正反查复用成员rank和总数，区分筛选行号 | API25/26 | 搜索股票不重排板块名次 |
| 11-05 联动UI | 可折叠选择栏、顶部条件、主结果；属性/关联分组 | 联动选股三子页 | 宽表容器滚动不冲出页面 |

人工覆盖走现有配置apply的版本流程，需要扩展配置schema接受semantic_overrides；只读查询POST不写覆盖。配置生效生成新分析版本，旧观测不改。

### 22.7 M12：统一个股透视

| 任务 | 步骤 | 产物/API | 验收 |
|---|---|---|---|
| 12-01 聚合服务 | Quote/Technical/Structure/Association复用，无重复计算 | API29；012只加必要支持索引 | 多入口结果一致 |
| 12-02 共用抽屉 | 路由publication/sid/tab、焦点管理、取消请求 | drawer.js、stock-insight.js | T17/T18 |
| 12-03 历史页签 | 懒加载API12/13，按图表锚绘制OHLC/MA/RPS/金额 | chart组件 | 不拼不同锚，图表缺口可见 |
| 12-04 证据通用化 | API15分组DTO，4–6摘要、详情折叠、中文枚举 | modal.js、evidence.js | 长文不撑行、原换行不直出 |
| 12-05 在线占位 | 能力不可用时折叠；M14后接API38 | external-evidence.js | 在线慢不阻塞首屏 |

### 22.8 M13A/M13B：市场与梯队

| 任务 | 步骤 | 产物/API | 验收 |
|---|---|---|---|
| 13A-01 市场聚合 | 按股去重求广度/金额，新高/MA分母各自统计 | API32/33 | up+down+flat恒等，未知不算0 |
| 13A-02 队列/板块补充 | 8B和M9/M10完成后增加队列去重数、板块状态数 | market字段能力升级 | 不改变旧snapshot |
| 13A-03 市场图 | 60默认/250可选、共享日期游标、单日明细 | 市场周期页 | 固定窗口、无全市场DOM |
| 13B-01 梯队递推 | M8C状态→按市场日递推；未知与停牌区别；左截断下界 | 013迁移（仅依赖008）、API34 | T13；未知非NONE |
| 13B-02 晋级集合 | 昨日确认涨停且今日可判断的分母，排除原因分别计数 | API35、promotion表 | 分母0→NULL，停牌不算失败 |
| 13B-03 梯队页 | 分层数量、分页成员、关联和量额；无炸板率 | 市场周期/收盘梯队 | 准确/近似/未知状态明确 |

### 22.9 M14：在线增强按能力交付

| 任务 | 步骤 | 产物/API | 验收 |
|---|---|---|---|
| 14-01 来源验证 | 按用户已有授权同步网络规则；逐dataset核查A级/B级能力 | sources registry及probe报告 | 不把静态URL当免费证明 |
| 14-02 批次基础 | fetch/payload/batch分离、映射与时间、owner协调、缓存 | 014、API36/40 | 重复正文仍保留每次抓取 |
| 14-03 热榜 | 平台原排名、比较批次、同时上榜时间门、固定分页批次 | API37及热榜页 | T16与分页不换批 |
| 14-04 原因 | 原文/摘要/来源/first_seen，多源与事后补充分开 | API38及个股证据页 | 历史不见未来，XSS文本安全 |
| 14-05 可选报价 | 仅当独立报价能力准入；source_as_of显著 | API39 | 与本地封存报价分开 |
| 14-06 低优先龙虎榜 | 来源成熟再为API38增加LH_LIST evidence_type | 独立合同与样本 | 不与主线/队列综合打分 |

热榜、原因、报价、龙虎榜分别签capability状态；只做API36健康页不能视为完成M14全部数据功能。

### 22.10 M15：整合与正式切换

| 任务 | 步骤 | 产物 | 验收 |
|---|---|---|---|
| 15-01 首页编排 | API30汇总＋API31优先研究分页，正常板块固定分组 | 完整研究总览 | 各卡点击对应筛选不丢日期 |
| 15-02 路由与版本 | 六导航、二级页、抽屉、后退/刷新恢复 | 完整/v2，无额外iframe滚动层 | T17/T18；旧/view仍可回看 |
| 15-03 性能回归 | 固定规模冷/热测、生成任务并发查询、LRU资源统计 | perf-report与录制操作记录 | 第16.3章全部可重复 |
| 15-04 数据/恢复审计 | 跑T01–T24、schema恢复、分片引用与旧观察不可变核查 | acceptance_receipt、风险清单 | 核心失败BLOCKED |
| 15-05 正式入口 | M6独立门与本版验收通过；通过配置切换入口并保留回退 | activation_receipt | 失败恢复旧入口；不删除旧发布 |

不要在全部工作包结束前标记M7–M15总FULL_PASS。各包可以先PREVIEW_PASS，最终结果必须逐能力列出，而不是一个绿色图标掩盖数据缺失。

<a id="ui-contract"></a>
## 23. 界面细化：位置、列、交互、加载和空状态

### 23.1 全局布局

以1440px桌面为基线：顶栏64px，内容区内边距24px；左侧一级导航200px（可收起到64px），剩余宽度给工作区；顶栏仅日期/口径、生成任务状态和操作入口。二级导航位于工作区上方一行。1920px不无限拉大文字，卡片与表格可扩展；1000px以下导航收起且选择栏移到顶部。

日期选择器先选发布日，版本详情里选修订；历史图点击旧日仅设置detail_trade_date，不偷偷切换publication_id。当前只提供回算时显示小型“回算”标签和解释；数据合同哈希不摆在主表。

全局loading：卡片骨架与表格短占位；失败显示重试按钮和中文原因，不把空表当报错。空筛选显示“没有符合当前条件的结果”并可清空。能力未生成显示“尚未生成该历史分析”；来源不存在显示“当前资料不支持此字段”。

### 23.2 六个一级页的具体设计

| 页面/子页 | 默认可见内容 | 次级内容与交互 | 首屏API |
|---|---|---|---|
| 研究总览 | 5–6市场卡；行业/概念各最多6板块；板块状态梯队；代表股；优先研究前50 | 点卡进入对应筛选；行情标签独立折叠；代表股去重但保留来源 | API30并行API31 |
| 板块研究/排行 | 板块、类型、板块涨幅、成员成交额、总数/有效数、强度名次、状态 | 名称开板块详情；列设置打开宽度/均线/新高 | API16 |
| 板块研究/周期矩阵 | 20板块×10日期；固定板块名列；统计窗口选择 | cell点开当天侧栏；行名打开曲线；左右日期滚动局限容器 | API17 |
| 板块研究/主线 | 类别筛选卡、板块、连续上榜、5/20次数、宽度/留存、状态 | 30日次数与金额细节折叠；点证据开模板分组弹窗 | API21 |
| 个股研究/优先研究 | 代码/名称、最新价、当日涨幅、成交额、主要结构、研究带、强势关联 | V1等级只做详细列；点股票统一抽屉 | API31 |
| 个股研究/五类结构 | 五队列分段、研究带、搜索；队内名次、代码、名称、价、幅、额、关联、证据 | 默认CORE/SUPPORTED；诊断显式打开；搜索不改合同名次 | API14 |
| 个股研究/创新高与RPS | 20/30/60/100切换；连续新高、RPS、MA、量额筛选 | 同时查看不同窗口在抽屉展开，不在首页铺四张大表 | API11 |
| 联动选股/板块个股 | 选择栏＋成员结果、总数/有效数、板块内名次 | 当前/昨日名次、共同成员进入退出；反查股票关联 | API25 |
| 联动选股/交叉筛选 | include板块chips、交/并、排除、折叠技术条件、结果表 | 明确显示选了几板块；清空选项移除字段；不自动强加核心行业 | API23＋API24 |
| 联动选股/属性库 | 类型/语义搜索、成员数量、来源 | 点板块进入成员；人工覆盖位于配置详情，生成新版本 | API23 |
| 市场周期/市场历史 | 三行图：广度、量额/MA、新高/结构/涨停 | 共享日期游标；缺数据不连线；点击开单日统计 | API32 |
| 市场周期/收盘梯队 | 首板/2板/3板/4+数量和晋级分子分母 | 每组独立加载和分页；未知/近似筛选；不显示炸板率 | API34/35 |
| 市场周期/平台热榜 | 来源分段、原平台排名、涨幅/金额、更新时间 | 无可用来源仍有说明入口；不把数据不可用做成空白页 | API36/37 |
| 数据说明 | 覆盖区间、能力缺失、来源状态、字段解释、后台任务 | 合同与哈希折叠；历史准备/激活入口受正常配置/版本校验 | API02/03/04/05/07/36 |

板块详情统一四tab：概览、曲线、成员变化、强势代表。个股抽屉五tab：概览、技术、板块环境、历史、在线证据。没有某项数据时tab显示原因，但不会影响其他tab。

### 23.3 股票表公共列与排序

默认最多10列：名次、代码、名称、最新价、当日涨幅、成交额、结构/研究带、强势关联、状态、证据。板块内名次/总数只在联动显示；其它页面不摆无意义空列。

金额使用元/万/亿/万亿，例16.2亿、80.9亿；去掉无意义尾0。跌幅用负号，涨幅有正负色和符号；百分比默认一位小数，抽屉可两位。内部布尔true/false→命中/未命中，UNKNOWN→数据不足；英文队列key只用于请求。

排序由列头提交后端；UI明确哪个排序生效。五队列默认rank不能悄悄被成交额排序替代；如果允许用户按金额临时排序，保留“合同名次”列并显示“当前按成交额排序”，服务端必须支持该白名单后再显示点击能力。

冻结列最多代码/名称；表格row-height约44px；证据不在td内部插入长块。空成员搜索不能把顶部总数变为0，分别显示“板块共M只，当前条件N只”。

### 23.4 弹窗与抽屉交互

- 证据弹窗宽min(880px,视口−48px)，高≤85vh，标题含股票和日期；摘要4–6项，下方分组折叠。
- 抽屉桌面宽min(720px,视口−48px)；窄屏全宽。body锁滚动，内部一个滚动区，关闭恢复原滚动位置。
- 遮罩只在event.target为遮罩本身时关闭；不能因为点内容冒泡而关。Esc关闭顶层；若抽屉中打开证据弹窗先关弹窗。
- loading、success、empty、error、unavailable五种状态独立；切换股票中断上个请求，返回迟到结果不渲染。
- focus trap、aria-modal、标题关联、关闭按钮中文标签；关闭焦点回到原触发按钮。返回按钮、刷新、书签恢复参数。
- 来源摘要中的URL用安全协议白名单，文字采用textContent；分页/股票名不使用危险innerHTML拼接。

### 23.5 组件和服务落点

新增static/v2/{app.js,api.js,router.js,format.js,table.js,modal.js,drawer.js,charts.js,styles.css}；
页面模块pages/{overview,sectors,mainlines,stocks,linkage,market,data-info}.js；
不引入新框架作为强制前置，使用项目已有前端方式拆模块即可。

后端新增services/{context,quotes,technical,history,sectors,mainlines,linkage,insight,market,online}.py，
路由层只解析与校验，计算在workbench_history/workbench_analysis，查询SQL集中repository/query层。API29复用这些service，避免十几个HTTP子请求。

模块资源版本进入render身份；生产workbench.py与/view资源路径同时调整。仅在旧fixes.js继续追加脚本不能满足本章的交付要求。


<a id="acceptance-contract"></a>
## 24. 测试实施明细和验收回执

第16章T01–T24继续完整适用；本章把它们落到测试文件、接口合同和交付流程。以下测试路径为待开发目标，尚未创建/执行；示例命令应在对应工作包实现之后运行，不能将本文当成测试通过记录。

### 24.1 样本夹具目录

统一tests/fixtures/workbench_v21/，包含：

- calendar_gap：三个真实相邻市场交易日，但只发布第一和第三日。
- corporate_action：除权前后raw/参考前收/复权输入，后续事件可独立扰动。
- universe_cases：沪深北A股、B股、新三板、ST、新上市、已确认退市、未知状态。
- constant_and_highs：恒价、持平前高、四窗口各自突破、历史左截断。
- membership_changes：共同成员、加入/删除、数据缺失、真正转弱分开。
- representative_sequences：A-B-B、A-B-A、A-UNKNOWN-B及边界日期。
- mainline_conflicts：持续＋收缩、低P＋低留存、从未上榜、缺30日但20日充分、上级predicate未知。
- association_independence：目标股强但其余5股弱、剔除后仍强、无合格板块、标签与行业并存。
- snapshot_failures：文件已seal未登记、清单准备未激活、事务提交后响应丢失、同identity不同内容。
- online_recordings：正常批次、429、空响应、结构漂移、跨市场同代码、后补原因、重复正文两次抓取。
- ui_long_evidence：长中文解释、缺值、英文枚举、超长板块名和大量来源。

夹具从小型手工构造和脱敏固定样本组成，注明expected_contract；不将实时网络结果作为单元测试稳定性前提。真实数据抽样核对另外执行并记录publication_id。

### 24.2 各阶段测试文件与不变量

| 阶段 | 计划测试文件 | 必须验证 |
|---|---|---|
| M7A | tests/upgrade_m7/test_quotes_universe.py | 原价显示、参考前收、缺发布日、BJ纳入、未知不退市 |
| M7A | tests/upgrade_m7/test_semantics_and_catalog.py | 标签隔离、ID覆盖、队列中文及字段单位 |
| M7B | tests/upgrade_m7/test_analysis_identity.py | slice复用、配置/input变化入身份、basis固定、旧发布不变 |
| M7B | tests/upgrade_m7/test_migration_recovery.py | SQL坏迁移回滚、对象孤儿、提交重试、恢复引用 |
| M8A | tests/upgrade_m8/test_technical_contracts.py | 旧AMOUNT比不变、新金额/量比、同锚MA和新高 |
| M8A | tests/upgrade_m8/test_rps_windows.py | n+1窗口、并列平均、分窗streak、valid_n不足 |
| M8B | tests/upgrade_m8/test_history_structures.py | 旧日期同输入对齐、未知非False、observations/outcomes不改 |
| M8C | tests/upgrade_m8/test_reference_rules.py | 除权/ST/新股/未知、生效日期和Decimal档位 |
| M9 | tests/upgrade_m9/test_member_sets.py | 集合恒等式、比较覆盖、缺失不退出、金额去重 |
| M9 | tests/upgrade_m9/test_representative_state.py | 候选/确认日、stale、无后验回写 |
| M9 | tests/upgrade_m9/test_matrix_api.py | 固定行列、窗口与visible_days独立、缺日 |
| M10 | tests/upgrade_m10/test_mainline_state.py | 完整类别表、优先冲突、三态、MODEL_CHANGE |
| M11 | tests/upgrade_m11/test_intersection_and_rank.py | 集合/排除优先级、排名先筛选、4板块限制 |
| M11 | tests/upgrade_m11/test_association_parity.py | 保留V1独立支撑，主备选、所有拒绝原因 |
| M12 | tests/upgrade_m12/test_insight_api.py | 首屏DTO、缓存键、图表basis与因素证据区别 |
| M13 | tests/upgrade_m13/test_market_ladder.py | 市场分母、队列去重、未知/停牌不误晋级 |
| M14 | tests/upgrade_m14/test_online_batches.py | source映射、时间门、batch分页、重复抓取/XSS文本 |
| M15 | tests/upgrade_m15/test_contract_coverage.py | API01–40有登记/状态；核心表字段与索引签发一致 |
| 跨阶段 | tests/upgrade_m15/test_ui_flows.py | 导航、两日期、两股票、modal关闭、iframe回退、空状态 |

API契约验证至少覆盖：缺publication、日期越界、负page、过大page_size、非法sort、乱码query、错误basis、未构建能力、POST超长body、空集合、batch变更、旧接口兼容。每个新增接口至少一个正常和一个失败/空状态样例；不是每个字段重复写相同测试。

### 24.3 可手工复核的确定结果

1. 金额1,620,000,000元→16.2亿；8,090,000,000元→80.9亿；未知→暂无；四舍五入后跨档应正规化。
2. 前20日金额均100，今日300：新amount_vs_prior20=3；旧含当日20日均额由19×100＋300计算得110，旧AMOUNT_RATIO20=300/110，两者不得覆盖同列。
3. 同日有效收益[0.01,0.01,0.03,0.04]，平均排名百分位为[0.375,0.375,0.75,1]；生产RPS的N≥100门应另外按真实规模测试，此4项仅用于rank核心函数。
4. 前20日收盘全10，今日10：new_high=false，at_prior_high=true；今日10.01：new_high=true；不能因横盘等于最高就连创新高。
5. 昨日强势{A,B,C}；今日成员缺C、A仍强、B变弱：共同可比留存1/2，previous_strong_total=3，comparable_previous_strong=2，C归成员移除，不能同时算共同成员转弱。
6. 代表A→B→B：第二个B日确认；A→B→A：不确认；未知日不得证明连续2日。
7. 昨日涨停10股，今日6续板、2确认未封、1停牌、1未知：晋级分母8、分子6、rate=0.75，排除停牌1和未知1；不是6/10。
8. 股票同时属于两个板块，金额100元：各板块可各显示100，市场股票去重只计100。
9. 主线P=0.85且满足持续条件，但共同宽度降0.12：按既定优先级输出HIGH_LEVEL_CONTRACTION；P=0.5仅留存低不触发高位收缩。

这些样例用于核对公式和条件实现；不表示市场模型已经证明有效。

### 24.4 运行与交付步骤

1. 开发包完成后运行定向测试：例如python -m pytest tests/upgrade_m7 -q；同时运行受到影响的旧模块测试，而不是只跑新代码。
2. 用测试数据库执行schema迁移、准备、取消、重试、激活、恢复；确认TDX目录和真实旧发布没有写入。
3. 在新版预览入口用至少两个正式日期核对当前数据；历史回算分别取30/250输出窗口，验证能力覆盖和延迟加载。
4. 录制桌面操作和截图：1440×900与1920×1080；选个股、打开证据、关闭、换日期、查交集、看矩阵、看缺失在线来源。
5. 记录固定规模冷5次/热30次性能、内存峰值和发布期间读取性能；不挑最快一次报通过。
6. M15前跑全量既有回归，检查旧V1/V2和前向观察不变量；M6外审门仍单独满足。
7. 输出本阶段receipt后才允许后继消费者使用该结果。receipt必须绑定当前源码和数据哈希，旧绿灯不能沿用到修改后的版本。

### 24.5 验收回执结构

~~~json
{
  "stage": "M9",
  "plan_version": "workbench-upgrade-plan-v2.1",
  "code_identity": "demo-code-hash",
  "contract_bundle_id": "workbench-contract-bundle-v2.1-preview",
  "publication_ids": ["demo-publication"],
  "analysis_snapshot_ids": ["demo-snapshot"],
  "status": "PREVIEW_PASS",
  "capabilities": {
    "sector_cycle": "AVAILABLE",
    "board_quote": "UNAVAILABLE"
  },
  "checks": [
    {"id": "T08", "status": "PASS", "evidence_path": "demo-evidence.json"},
    {"id": "T09", "status": "PASS", "evidence_path": "demo-evidence.json"}
  ],
  "unresolved": [
    {"capability": "board_quote", "reason": "NO_VERIFIED_BOARD_QUOTE_SOURCE", "impact": "板块自身涨幅显示暂无"}
  ],
  "performance": {"scenario": "20x10", "warm_samples": 30, "p95_ms": 500},
  "formal_activation_allowed": false
}
~~~

示例非真实回执。正式status沿用第16.4章，PREVIEW_PASS仅为工作包内部预览就绪，不替代M6外审。未执行的check写NOT_RUN，不能写PASS。UNAVAILABLE/NOT_BUILT能力不得被省略以凑齐“全部完成”。

## 25. 版本、配置与待实测能力

### 25.1 本版已确定、可以直接实施的决策

- 默认股票范围含沪深北A股；不再沿用1.1的北交所默认排除。
- 采用日分片＋快照清单＋新发布修订激活，按经济相关输入hash复用。
- M7先范围/语义/历史基础，M8补技术和历史结构；M13和M14按依赖并行。
- 新高采用“超过前N日最高收盘”，四窗口各自streak；旧DIST_HIGH不改。
- 旧金额公式保留，异常金额/股数量比用新字段；RS与RPS分开。
- 主线按第10章固定预览合同实现，强势关联保留既有leave-one-out门。
- API01–40为完整新增/扩展目录，数据DTO、参数与错误遵守第19章。
- 物理表采用第21章定义的长/宽形式；成员明细使用Parquet，不自行改为每发布全复制。
- UI遵守第23章布局；证据弹窗和统一抽屉在开发早期接入。
- 本地全量开发不依赖任何在线来源通过；功能交付状态逐项标明。

### 25.2 配置位置与变更规则

新增config/workbench_upgrade_v21.yaml作为本版实现配置；合并进现有OperationsConfig的校验范围。字段至少包括：

~~~yaml
plan_version: workbench-upgrade-plan-v2.1
contract_bundle: workbench-contract-bundle-v2.1-preview
universe_contract: CN_A_LISTED_V2
history:
  output_days: 250
  compute_workers: 2
  memory_fraction_limit: 0.5
  default_basis: AUTO
query:
  default_page_size: 50
  max_page_size: 100
  max_days: 250
  matrix_default_rows: 20
  matrix_default_days: 10
  matrix_max_days: 30
cache:
  local_max_mib: 256
ui:
  default_entry: legacy
  preview_path: /v2
online:
  enabled: false
  co_listed_max_skew_seconds: 900
~~~

compute_workers是资源上限提案，M7B基准后可调；规则配置和性能配置的hash身份分开：阈值、窗口、范围改变结果，纳入computation/config identity；线程数、缓存预算等不改变经济结果的设置不制造新经济修订。仍记录运行配置用于复现性能。

mainline-v2.1-preview.yaml与semantic-overrides配置单独版本化，不能修改默认yaml后原地替换旧snapshot。在线enabled=false表示能力尚未准入的默认状态，不是产品永久禁止联网。

### 25.3 不能凭文档保证的项目

| 条件 | 谁/何时完成 | 未满足时 |
|---|---|---|
| 历史证券/成员当时身份 | M7B来源能力审计 | 只提供明确回算，不宣称真实PIT |
| 股本与涨跌停参考价/规则 | M8C | 字段UNKNOWN/UNAVAILABLE，精确能力未完成 |
| 板块自身行情映射 | M9来源核对，必要时M14增强 | 只展示有名有口径的成员统计 |
| 免费热榜/原因/报价来源 | M14逐dataset验证 | 对应能力不启用，不影响本地 |
| 大窗口性能与存储预算 | M7B/M8/M15真实基准 | 调整批次/索引/查询，未达门不得切换 |
| M6独立验收 | 现有独立验收流程 | 可开发预览，不能擅自正式切换 |

这些是各工作包自带的具体任务，不要求开发前重新阅读旧1.1讨论取舍。遇实际数据不满足按表中分支实现并报告，不编造字段或降低核心正确性门。

## 26. 独立实施检查与最终交付定义

本版已将审计核心内容与接口/数据库/任务/界面/测试细节合并在一个文件。开发仍需查阅仓库当前源码和封存算法合同，因为它们定义旧行为；不需要再把1.1和2.0当作并列实施方案拼接。

完整交付时逐项勾选：
首页渐进式视图、技术与报价、四窗新高/RPS、历史五类结构、板块矩阵、成员留存/扩散、代表更替、主线、属性库、交叉筛选、强化关联、个股透视/K线、证据弹窗、市场历史、收盘梯队、已准入在线能力、备份恢复与正式验收。

开发顺序以第22章为操作入口；接口以第20章为目录；字段与迁移以第21章为准；界面以第23章为准；验收以第16与24章共同为准。尚未具备数据的能力在最终清单保留未完成/降级标识，不能删除对应项后声称全部实现。

本版文档自检记录（2026-09-09）：API01–40完整且编号唯一；6段JSON样例解析通过；本地文档链接和章内锚点检查通过；第21.6章三张表的DDL样例已与当前schema一起在DuckDB内存数据库中执行通过。该检查只验证文档样例和引用，不代表全部新表迁移、接口或T01–T24运行验收已通过，正式数据库未修改。
