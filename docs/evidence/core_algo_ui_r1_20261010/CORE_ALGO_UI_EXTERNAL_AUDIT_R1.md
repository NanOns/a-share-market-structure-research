# V4 核心算法与六入口定向修复 R1 外审交付

执行日期：2026-10-10，Asia/Shanghai。当前用户要求是执行任务文档全部工作包；文档作为执行合同，内部历史结论、举例和未来门均不替代本轮现场证据。

**唯一总状态：SCOPED_ENGINEERING_REPAIR_COMPLETE / FULL_PRODUCT_ACCEPTANCE_OPEN。** 已完成当前真实输入能够支持的定向修复及分域检查；本轮不授予 FULL_PRODUCT_PRODUCTION_RELEASE_PASS。ALG 独立算术为 ALGORITHM_SCOPED_PASS；六入口为真实冻结 Owner 的限定读域检查通过，不等于原 FP 全字段、所有算法边界或生产发布最终通过。用户原端口 28765 尚在运行旧代码，最终生产页面确认待用户正常退出并重启一次。本轮没有控制该进程，也没有建设热更新、托盘或 Windows 维护功能。

## 1. 合同、输入与身份冻结

- BASE_SHA：`64a0e31390765027f96b6a537bbf7f044abf6c83`，目标分支 `codex/v4-fp14-r2-repair`。
- 代码修复提交：`86c2ff8b`，完整 SHA 见谱系与浏览器索引的 `code_result_sha`。最终交付提交与远端精确匹配另见 DELIVERY_RECEIPT.json；证据提交不改变本节被验代码身份。
- 当前 T0：2026-10-09；周末 10/10 没有新交易日，不前移到 10/12，不用未来数据解释当期状态。
- 真实 accepted research head 字节 SHA：`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`。本轮开始和结束相同。所有 API 使用同一 publication/context token；错误旧 token 实际返回409，越界未来日期返回400。
- 成员模式：`TDX_LATEST_MEMBER_RETRO_V1`，分类 `TDX_INDUSTRY_CONCEPT`；成员采集 `2026-10-09T09:44:01.158745+08:00`。这是当期通达信最新成员回算，`AS_RECORDED=false`、`PIT_ELIGIBLE=false`、存在存续偏差，不冒充历史当日首次可用成员。
- 历史、RAW、Core、正式周期、板块、市场、Focus及诊断均来自 Head 已绑定 Owner。各文件 path/bytes/SHA 在矩阵、数值输入和本地物化收据中保留；显示名称另绑定既有显示权威，明确 display-only，不改变证券身份或 PIT。

已读取仓库 AGENTS.md、正式 REV2 §62A–§69/§81.2、最新 FP01–14 卡和 R43 R2 差距矩阵。Drive 合同回读见 CONTRACT_SYNC_RECEIPT.json；Drive 的“codex修改版”作为历史参考，不能越过仓库正式 REV2。最新主任务完整原文复制到 TASK_CONTRACT_R1.md，原桌面文档未修改。Phase0 沿用已有 accepted 输入门，未绕过 scanner/producer 顺序。

所有新增临时、测试和物化产物放 G。TDX 根保持只读；没有修改、重命名或删除 TDX 文件，没有改旧验收收据、冻结 capability 或严格 PIT head。没有重新计算4GB Owners，也没有采集热榜、调用外部复权、自动交易或生产预测。

## 2. 独立数值审计与复核方法

CORE_ALGO_UI_NUMERIC_MINIPACK.zip 约473KB，包含必要输入摘录、独立 stdlib oracle、expected/actual/delta、SHA和输出。脚本不导入业务计算器。外部解压后运行：`python -B oracle/independent_oracle.py oracle/INPUT.json`。退出码0；本轮840项比较无差异。ZIP 内 SHA 是交付字节基准，避免 Git 换行策略影响单个文本文件的字节哈希。

样本为29个真实证券、4个真实板块、2个真实 Episode。证券按真实涨跌/中段/缺当日行情分层选择；板块包括一强一弱、电气设备 INDUSTRY:T0706、通达信概念 THEME:880904。独立复算当期与 T-1 的 MA20、ATR20、ret1/5/20、量额比、前高前低，采用每字段自己的窗口起止和实际观察数；不以每个技术指标都固定20日代替合同。日周月价格、成交量和成交额按实际行情聚合，对应 RAW 与原生 QFQ 正式周期 Owner。

板块 median return 与上涨宽度按唯一真实 member_id 集合复算；当前电气设备正式源成员349，研究可映射322，未映射27。算法使用正确映射分母，展示此前混用了源数量。重叠采用交集/并集 Jaccard，不重复计算证券。价格限制抽样覆盖涨停、跌停、普通、停牌和 UNKNOWN；停牌不是伪造涨跌停0。

市场新增独立检查：5224资格证券，5199可判定价格限制覆盖；amount_ratio20 实际全市场输入中位数对应 NORMAL，真实跌停/共同成员前日分母对应 LOW/DECLINING。信号检查只证明已发布实际 D2 的失效保护、不用 STALE 当有效、有效资格必须 FRESH/VALID、availability 不越过 cutoff；**不证明全部 detector 公式或重入 reducer**。Focus 真实到期路径用绑定实际行情独立复算 return_close、MFE、MAE；仅在样本窗口 affine 坐标一致时比较，不把不可比窗口直接相除。

明确算法缺证据：市场 trend/breadth 完整路径桥接没有在此小包独立重建；完整信号阈值、留一法全部因子与锚点失效/再入、Rotation递归 reducer没有本轮全量裁决；没有可靠退市、真实终止后再入及全部新股/ST特殊边界样本。既有 R2.1 复权及 R2.2 源证据继续保留，只在原限定范围继承，不能把未重算模块一律叫本轮 PASS。矩阵对此逐行 NOT_VERIFIABLE 或 PASS_SCOPED。

## 3. 实证缺陷、修复结果与产品范围

### 个股

旧 `/chart` 对真实股票返回 SOURCE_INCOMPLETE，实际历史 Owner 已存在；现在从同一 hash-bound 真实历史只读索引提供 D/W/M、RAW/QFQ，附来源、坐标、金额/股数单位与截至日期。三一重能688349：当期最后收盘13.59；日线420根，页面分段显示120根，可查看更早行情再返回最新。周线91根，10/09正式 Owner 已确认 CLOSED_ONLY_READY；月线22根、AS_OF_PARTIAL_READY。没有用随机曲线、0或旧图填缺数。

代码和中文名查询命中同一 SEC 身份。画像将已有Core字段、迁移理由、未知谓词与检测器状态带到BFF，提供关键价格、窗口与F/R/H来源。搜索不只前6条。最终资格不能由页面替代 detector；H明确为研究假设，没有账户/持仓证明。历史别名、退市池外身份和完整竞争假设仍是精确债务，不能称任意历史证券已全部完成。

### 板块

旧日期时间线和重叠路由缺Owner适配，不能阻断完整成员。现在绑定5个实际发布日期的因子与轮动前态，显示当前成员重建/PITfalse，读取201条实际重叠，成员322条全部分页无重复。电气设备五日原始median路径从9/28的-0.0388878到10/09的-0.0091258；当前页面相对强度分位26.923是不同合同字段，API来源分别标明，不能将原始return与分位混同。

源349、映射322、未映射27分别展示。完整递归轮动、10/20会话扩散历史、overlap cluster和27条身份逐项原因尚未完成；不会因新页面有5点时间线就宣称全Rotation验证成功。生命周期缺失的字段保持来源不足，而不是补造确定状态。

### 首页

从真实 dated Focus 与Rotation读取变化和风险；排序先风险、再强度/稳定身份。板块显示10条、上限15；独立股票显示最多30。只让已展示板块覆盖其成员进行去重，未展示第16+板块不能吞掉股票名额。当前Owner变化456个唯一对象，独立集合365/显示30，无变化持续645。此范围叫“关注对象变化”，不伪装全部新进入PREWATCH或结构变化Owner。雷达/Validation Cohort没有正式来源时明确“来源未接入”，不显示空白或0。

### Focus 与 Forward

旧层级路由出现语义混用风险；现在 Episode、Anchor、Observation、Outcome分别展现。三一重能当前例：Episode1、Anchors2、Observations4、Outcomes10。到期项OBSERVED，未到期继续PENDING；路径是锚点收盘变化，不表示交易收益。源的高优先级未决谓词保留PARTIAL/UNKNOWN，不越权写入自动关注。

Focus重建读域不能替代Validation Cohort。现在 `/forward` 明确缺独立Cohort Owner；statistics/plans/settlement/fep按具体源不足局部降级。没有用Focus Episode个数填“合格信号样本量”，没有用未到期观察计算胜率，更没有生成FEP预测或概率。

### 市场与诊断、比较

此前市场四轴可用而四个子路由缺适配。新增来源绑定的breadth、5指数、价格限制和日线梯队：上涨2989、下跌2107、平113、未知15，资格分母5224，实际行情5210；通达信原始金额19003.65亿元。涨停72、跌停11、停牌14、未知11；梯队72只在既有连续价格限制绑定范围给精确值，否则给下界和PREFIX_NOT_BOUND。

上证3813.79、深证12641.86、创业板3043.33、沪深3004317.25、中证10007155.91，来源冻结TDX包；指数量的源单位尚未确认，没有擅自换算。首封/炸板/分钟/新闻源不存在，不用日线推造。

诊断sources/health/contracts读取dated来源和规则；raw row_count5210可与页面回读。健康未知计数是None字段覆盖代理，不等同全语义质量审计；legacy/jobs/shadow完整迁移Owner仍缺。corrected比较按股票/板块/市场同日或不同已发布日期分别读取真实对象，明确非严格历史PIT。严格Replay没有first-available证据，仍局部能力受限。

## 4. API、浏览器与安全验收

API_FIELD_CONTRACT_AUDIT.json记录38条实际HTTP的字段类型、coverage、来源、token、before/after、业务状态、耗时与原因。6种图表组合、完整322成员页、名称/代码同身份、旧token409、未来日期400、非法周期和分页界限均检查通过。HTTP200仅说明封装可读；SOURCE_INCOMPLETE明确记未完成，不能把API总体无异常误算所有域PASS。

17项定点pytest通过，命令/退出码见REGRESSION_RECEIPT.json；合成测试数据仅覆盖契约负例，不作为真实业务验收。本轮API与IAB用127.0.0.1:28767独立只读handler，接真实已接受Owner；没有mock业务数据，也没有称用户的28765网页已经更新。

IAB在1366×768和1920×1080逐页打开六入口和核心详情，使用最终代码提交记录source Head、日期、时间、图SHA。证据共8张关键JPG，另有DOM和操作记录。每域至少一条Owner→API→DOM实测对应：5224股票、322映射成员、13.59收盘、Focus10结果、19003.65亿元、5210RAW。两个宽度均无根节点横向溢出；12823字符诊断来源摘要抽屉也无横向溢出。实际操作包括代码/中文搜索、名称降序、第二页无交叠、真实空查询、日周月切换、历史图翻页、成员分页、跨页比较、返回和刷新。

显式QA传输代理28768只让breadth返回503，市场四轴、5指数、价格限制和梯队仍正常；只有失败区块重试。撤销故障并加入3秒受控延迟后，页面加载态、重试和真实宽度数值恢复已经观察。该证据是localhost单域传输故障与慢请求，不冒充真实操作系统断网。真实全站离线、10/12新日期切换串读、全部长中文/历史别名、所有浏览器下载边界没有本轮现场完整证据，仍NOT_VERIFIABLE。

## 5. 分域裁决、独立审计与后续

ALG-01矩阵完成结构化登记；算法范围不全的行不授予全量通过。ALG-02当前840项ALGORITHM_SCOPED_PASS；BFF-03定点38路由修复检查PASS_SCOPED；UI-04六入口实际读域PASS_SCOPED；QA-05双宽与关键故障隔离PASS_SCOPED，生产重启后的正式页面联合门仍OPEN。FP01–14每卡和V4-03～22/FEP全部状态见矩阵，未成熟旧门保留，不能向用户发明新的全站等待门。

综合审计另开独立项目：AUDIT-CORE-R1-01完整Rotation递归、AUDIT-CORE-R1-02信号/锚点/重入全路径、AUDIT-CORE-R1-03Amount A源口径、AUDIT-CORE-R1-04严格PIT与首次可用、AUDIT-CORE-R1-05Cohort/FEP合法成熟度。其范围、证据和验收与本轮BFF修复门分开，详见CROSS_CUTTING_AUDIT_ITEMS.md。AmountA既有问题不能因为本轮金额显示正确而被关闭。

下一轮最多5项：①外审复跑小包并随机对照API/DOM，用户正常重启后确认生产页面；②独立完成Rotation和信号/锚点/reentry真实连续反例审计；③补证券历史别名、池外解释及未映射成员逐条原因；④按独立权限链接Validation Cohort/Forward/FEP或继续精确缺源；⑤10/12真实新日DD R2.2闭环及日期切换检查。AmountA继续独立审计，不占用当前缺陷的“已修”结论。

本轮Git阶段提交均已push；Drive仅交轻量报告和复核包，不上传Owner、TDX包或426MB历史索引。Drive目的地沿用V4任务归档，新增文件不覆盖原文件。云端字节/SHA读回与预算、最终Git精确RESULT_SHA在DELIVERY_RECEIPT.json独立留存。外部审核者可以只拉小包复跑oracle，再抽查完整来源；最后的独立正式裁决仍由用户外审作出。
