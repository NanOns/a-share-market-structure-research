# V3「今日重点研究」设计全面审计与修改说明

> 日期：2026-09-14（Asia/Shanghai）  
> 审计合同：`V3_TODAY_RESEARCH_DESIGN_AUDIT_V2`  
> 修改源文档：[详细升级方案](V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md)  
> 版本：`v1.0` → `v2.0-AUDITED`  
> 接受结果：`DEGRADED_PASS`，限设计与当前数据能力核查；业务实现、PIT完整回放、参数效果和生产发布均未在本轮执行。

## 1. 总体判断

原设计正确识别了核心产品问题：V1到V3一直把历史结构强度与今日研究优先程度混用，首页又从旧候选池取高等级结果。其“先资格、后排序、分场景、可解释”的方向应保留。但原文不是可直接实施的完整算法合同：部分引用旧数据，部分公式与当前代码不同，有些产品规则又会复发刚修好的缺陷。

本次不是给SOL方案润色，而是按实际项目重新闭合输入、时间、公式、资格、评分、板块证据、状态、发布与验证。源文件直接替换为审计升级版，保持V3及既有能力；本说明独立保留问题证据与修改理由。

**关于本地数据的判断**：用户提出OHLC、成交额、板块基本都有，得到当日只读查询支持。当前parquet包含RAW和ADJ四价、原始成交额和量，9月14日有5,553条实际完整bar。日线足够实现本方案的大部分个股研究功能，不需要分时。尚未证实的是时点流通股本/换手率，以及历史成员、历史universe和历史源事件可获知性；这些不是“缺少日线”的同一种缺口。换手率保持关闭，不作为核心收盘功能的等待条件。

## 2. 审计范围、方法与证据级别

- 阅读原方案全文、AGENTS.md、V3实施台账/主规格、20260914综合算法方案、R1整改回执、当前强势复核、最终清单及页面修复说明；新回执用于避免把已修复故障再说成当前故障。
- 直接核对因子注册、日线归一化、P05特征/股票信号、正式强度计算、研究构建、LOO关联、旧候选API、首页JS和一键构建链。所有“当前代码”指审计时未提交工作区，不等于Git HEAD。
- 对生产DuckDB使用 `duckdb.connect(..., read_only=True)`；parquet通过独立内存DuckDB读取，未启动writer、日常重建、扫描或API变更。
- 查询当前发布日期、run、输入依赖、股票/板块状态、短名单与旧候选；检查9月14日实际bar的OHLC次序、非正价与额量，不把这称为全历史独立复算。
- 外部仅核对pandas标准差的ddof定义、上交所换手率的分母口径；外部源未作为本地算法输入，未请求实时行情、热榜或交易服务。

证据分层：**直接复核**为本次源码/查询事实；**既有回执**为历史验收引用；**候选设计**为新增公式/阈值，尚待验证；**未验证能力**须保持UNKNOWN/OFF/PENDING。源文档所有首轮数值阈值均属于候选设计，不宣称回放最优。

## 3. 逐项修改登记

级别：P0为可能错误准入、未来数据或发布身份问题；P1为核心功能遗漏/语义偏差；P2为可解释性、效率和交付完整性问题。此级别针对设计风险，不表示本轮发现了同等范围的生产事故。

| ID / 级别 | 原方案问题及证据 | 源文档修改位置与决定 | 验收影响 |
|---|---|---|---|
| TR-01 / P1 | 原文叙述易让人以为是V3才有的缺陷 | §1重新定义为V1—V3结构候选缺今日决策闭环 | 不以换UI标题替代核心建设 |
| TR-02 / P1 | 仍引用9月11日和单个发布日旧事实 | §2更新9月14日数据、2个发布日、5个run及具体身份 | run数不得冒充交易日数 |
| TR-03 / P0 | §7/9把既有BREAKOUT的收盘平台与H最高价混用 | §7/9拆PHC20/PHH20与双标签，冻结平台来源 | 10/11/10.5反例区分突破类型 |
| TR-04 / P0 | 原AMOUNT_RATIO20_PRIOR用median，却声称复用既有mean | §7统一准入用AMR20_MEAN_PRIOR；median另名诊断 | 均值/中位数各有字段、合同、样本 |
| TR-05 / P1 | 现有liquidity实际是prior20中位，原文未交代窗口 | §5/7明确单位元、20日中位和2千万元门 | 不用当日额把自己推过流动性门 |
| TR-06 / P0 | 原VOLATILITY20未区分V1 ddof=1与V3 ddof=0 | §7保留两字段，extension沿V3定义 | 不直接替换波动导致风险漂移 |
| TR-07 / P0 | EXTENDED真实是双条件AND，不能凭模糊名更改 | §3/8明确继承AND并另加风险门 | 阈值和布尔逻辑都入版本 |
| TR-08 / P0 | 严重大跌负数max未明确含义，含当日波动可稀释冲击 | §7改用prior波动和精确4%跌幅对应对数底线 | 不把高波动制度硬猜成10/20/30 |
| TR-09 / P0 | 两日结构破坏挡不住首日重破；原方案允许大跌回踩例外 | §8四类统一排除严重跌与C/MA20<0.97 | 首日破位不能靠高RPS补回来 |
| TR-10 / P1 | 强势回踩只看当前RPS/趋势和滚动回撤，没有先后顺序 | §9增加历史高点h、h时强势、后续回调和今日收复 | 缩量阴跌不叫回踩完成 |
| TR-11 / P1 | “近3日金额比”被当作完整回踩期间缩量 | §7/9准确命名并结合事件序列 | 公式不声称不具备的形态含义 |
| TR-12 / P1 | RECOVERY==TRUE外再加MA5 OR MA20未扩展能力 | §9独立R5/R20分支 | MA20修复可不依赖今日MA5上穿 |
| TR-13 / P1 | 延续仍只用历史趋势，RET1>-3%可长期霸榜 | §9新增今日越昨日高点、正收益、CLV与金额区间 | 无事件只能趋势观察 |
| TR-14 / P1 | 全部四类等确认后显示，缺提前研究观察对象 | §4/9补SETUP_WATCH及未满足确认条件 | 观察与确认清楚分开，保留提前用途 |
| TR-15 / P0 | 历史不足时允许独立启动，又要求未知板块不可当不弱 | §8改独立资格+明确支持矩阵 | UNKNOWN不是“不弱”，独立组仍可研究 |
| TR-16 / P0 | 已知false与NULL的组合没明确，容易把所有缺项都改UNKNOWN | §8三值真值表、失败项/未知项分别保存 | 与现有三值规则一致 |
| TR-17 / P0 | 原文“已有LOO可直接复用”过度乐观 | §3/10指出最终hard filter、覆盖和EARLY变化问题 | SUPPORTED必须最终track+LOO都TRUE |
| TR-18 / P0 | EARLY改善取全板块且选首非空值，未真正去掉目标股 | §10定义两日共同成员再剔除s，三值OR | 单股制造改善反例必须通过 |
| TR-19 / P1 | 多板块任一弱就否决或任一热就加分可能任意实现 | §8/10明确支持选择、全弱观察、关联兜底 | 保存全量证据，不能挑标签绕门 |
| TR-20 / P1 | 板块不CURRENT容易被当退潮 | §10分W_NOW/W_HISTORY/FADING | 今日弱不等20日，历史退潮不凭空生成 |
| TR-21 / P0 | 评分只有子项名字，风险扣20～30等无确定公式 | §11全子项函数、权重、尺度和上限可计算 | 人工复算到最终分，取消任意扣分 |
| TR-22 / P0 | 缺板块不加分又重分配权重，可能奖励数据缺失 | §11股票分与支持分组分离；缺评分项保留未评分资格 | 不因缺失飙到榜首，也不消失 |
| TR-23 / P1 | 主类别、跨类合并分数与“分数不可比”冲突 | §12固定主类别+轮询展示，不跨类按总分排 | 合并榜只称展示顺序 |
| TR-24 / P1 | 每类20/每板块3只会复发刚修好的截断缺陷 | §12全量资格不限；分页与预览分开，预览沿用10 | 6只合格全部可查，超额不是失效 |
| TR-25 / P0 | 从已有角色/短名单消费会漏回踩、延续和独立触发 | §1/3/12全量股票先算资格 | 旧候选及TopN不能当候选全集 |
| TR-26 / P0 | 只限制日期≤t不足以排除最新仿射QFQ的未来事件 | §5历史t重建A/B并验证事件可获知时点 | 加项、换锚、事后补录要隔离 |
| TR-27 / P0 | 当前universe历史标签当历史全集产生存活/时点偏差 | §5/14要求历史as-of证据和RPS跨日比较门 | current-membership仅诊断 |
| TR-28 / P1 | “3/5/10/20个有效日逐级开放”混淆原始预热与派生日期 | §14按因子DAG规划；t与t-3至少4个对应状态 | 不等研究run才能重算个股因子 |
| TR-29 / P0 | 首次观察、真正NEW、缺日、同日重跑/参数变化未拆分 | §11/13新增左截断、VERSION_RESET、HISTORY_GAP | 年龄不可伪造或因重跑递增 |
| TR-30 / P0 | 后续滚动平台与调整锚可悄悄改变失效标准 | §9/13冻结episode参考并要求同价基准 | 不重写历史触发，失效可验证 |
| TR-31 / P0 | 全链“原子发布”是目标，现代码先M4再研究 | §16增加完整研究包指针、固定目标与并发门 | 基础发布失败处理与研究可见性分离 |
| TR-32 / P1 | Phase0有BLOCKED终态也可能被误解为可继续扫描 | §16显式BLOCKED不能继续；DEGRADED按能力放行 | 保留项目guardrails实际含义 |
| TR-33 / P1 | 回放只是“不得未来”与指标名单，无标签/样本隔离合同 | §17收益、MFE/MAE、缺日、时序切分、基线、隔离 | 不随机股票日切分，不借未来收益改标签 |
| TR-34 / P1 | UI切换放在发布门之前，工程与效果门混在一起 | §19先完整包后页面切换，研究预览与效果分开 | 不等证明最优才能用，也不把可用叫有效 |
| TR-35 / P2 | “不读取TDX”与实际本地输入链矛盾，分时扩展偏离需求 | §4只读消费TDX；明确不做分时 | 只读不等于禁止使用本地源 |
| TR-36 / P2 | 量比、换手率、资金流/均价等语义边界不完整 | §5明确股数/元、A/V诊断和换手分母 | 不把金额比冒充真实换手或资金流 |
| TR-37 / P2 | 未说明高成本日线重算、LOO中位、存储增长 | §14/16受控窗口、按列批量、预算与旧保留政策 | 不每股扫描全历史、不擅自保存全部历史表 |
| TR-38 / P1 | 独立审计项仅列名称，容易被本阶段测试一起关闭 | §20逐项范围、证据、状态与关闭条件 | 复用旧AUD编号，新跨域缺口单独开项 |

## 4. 当前事实与历史故障的区别

本轮确认的当前静态路径缺口包括LOO最终过滤、EARLY变化LOO不完整和基础发布先于研究；不代表已观测到今日20条清单发生LOO泄漏——本次查询恰好20条均带LOO_COMMON_SUPPORT。文档已保持这个证据边界。

20260914早先审计中的MA20宽度量纲错误、布尔排名、NaN写库等已有R1整改回执；本次没有将它们再次列为当前未修故障。PIT历史、金额A专项和效果仍继续独立跟踪。当前72个CURRENT与9月11日仅1个CURRENT属于不同交易日，不是代码互相矛盾。

当前配置 `research-attention-config-v3.3`、算法 `RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE`、`focus_max=20`、`focus_per_sector_max=10` 均未改。新方案的全量资格/预览分离属于拟实施行为，不能解释为当前已无20条上限。

## 5. 本次只读数据复核结果

| 查询对象 | 结果 |
|---|---|
| parquet总行/日期 | 19,646,885 / 8,786，1990-12-19～2026-09-14 |
| 当日行/实际bar/完整RAW-OHLC/完整ADJ-OHLC | 6,182 / 5,553 / 5,553 / 5,553 |
| 当日正额/正量/正常universe标记 | 5,553 / 5,553 / 5,458 |
| 当日真实bar RAW/ADJ高低开收次序错误 | 0 / 0 |
| 当日真实bar非正额量 / 非正adj_low | 0 / 0 |
| publications / COMPLETE runs | 2个成功publication、5个COMPLETE run、2个交易日 |
| 最新publication | `m4-f787bac7863fa3409d45f75a8b7b5c30`，2026-09-14 |
| 最新COMPLETE run / snapshot | `research-59677a66206c4314b0b2b4b9e88046d0` / `m10-mainline-preview-4067dec5315150dc` |
| 最新run调整输入摘要（run内记录） | `88bb40ca3ecabab5eb16db6c1bda616d94e41d07522ee87df9a493670ac9223c` |
| 最新run股票信号 | 总6,182；BREAKOUT163、SETUP405、RECOVERY87、TREND_BACKGROUND1,113、STRUCTURE_BREAK2,622 |
| 最新run板块 | 总531；CURRENT72、POTENTIAL0；dq5_3/b_delta3/ma20_delta3均各531个NULL |
| 历史成员能力 | `historical_membership=UNAVAILABLE`；三日变化不可评 |
| 最新run短名单 | CURRENT_FOCUS20；无EARLY_FOCUS；LOO_COMMON_SUPPORT20 |
| 最新publication旧候选/旧final合格 | 1,045 / 52 |
| 关系区间/周期 | 72,537条；周期共1,659行，553在9月11日，1,106在9月14日两slice |

生产run内记录的调整输入摘要不等于本轮重新计算整份parquet哈希；本轮为查询核查，未将它误称重新逐字节核验通过。多条只读查询也不是冻结整台运行环境的长期快照，后续实施须重新冻结输入后对账。

可复核查询方法（只读，不执行建表/写表）：

```python
import duckdb
c = duckdb.connect('data/database/market_research.duckdb', read_only=True)
r = c.execute("""select run_id from research_runs where status='COMPLETE'
                 order by trade_date desc, completed_at desc limit 1""").fetchone()[0]
# 本次r为research-59677a66206c4314b0b2b4b9e88046d0；复核本次应固定该ID。
print(c.execute('select * from research_runs where run_id=?', [r]).fetchall())
print(c.execute('select list_type,count(*) from research_shortlist where run_id=? group by 1', [r]).fetchall())
print(c.execute('''select count(*),count(*) filter(where current_eligible),
 count(*) filter(where potential_eligible),count(*) filter(where dq5_3 is null),
 count(*) filter(where b_delta3 is null),count(*) filter(where ma20_delta3 is null)
 from research_sector_states where run_id=?''', [r]).fetchall())
c.close()
p = duckdb.connect(':memory:')
print(p.execute("""select count(*),count(distinct date),min(date),max(date)
 from read_parquet('data/normalized/adjusted_daily.parquet')""").fetchall())
p.close()
```

## 6. 新版本设计取舍

**核心优先**：先把日线已具备的数据编排成真实当日研究流程，新增独立回踩/修复/延续事件和蓄势观察。换手率、分时、历史PIT、在线事件扩展都不笼统阻断独立股票研究。

**评分可验证**：删除无法实现一致结果的抽象子分数和浮动惩罚。用有界函数定义每项，权重全列，支持关系分组展示。所有新权重只是候选参数；目前没有证据证明优于原方案，需P12-05对照。缺评分输入时保留已合格对象，不制造伪分数。

**风险更明确**：四类不再允许严重下跌例外，回踩必须有当日确认。这可能减少初期数量，应通过漏斗与分层敏感性判断是否过严，不能为了补榜放松；PULLBACK_UNCONFIRMED仍可供人工观察。

**全量不丢失**：资格、评分、去重、预览分散与分页各自独立。既有“板块6只合格只剩3只”的问题不得因新设计复发。

**历史诚实**：长日线能重算个股，不代表能证明当时板块关系或当时已发布。当前最新前复权也不等于历史时点前复权。三种history_basis明确隔离。

**交付可落地**：先完整研究发布门后UI切换；工程研究预览可独立验收，效果保持PENDING。长期历史增长与综合审计按既有独立政策处理。

## 7. 验证、未完成工作与文件范围

本轮验证包含：源文档结构/公式/阈值自洽检查；新旧问题映射；源码证据与只读库事实；新增评分权重和窗口索引人工复核；两个Markdown文件的编码、代码围栏与链接存在性检查。未运行新业务测试或生产扫描：本次没有实现新算法，运行旧测试不能证明新设计有效。

未完成事项并非本轮文档任务遗漏，而是未来实施阶段：四类新代码/接口/表结构、OHLC接入P05、LOO过滤修复、完整包发布指针、真实全量候选复算与新参数历史/前瞻验证。不得以此修改说明宣称它们已实施。

修改范围仅两个正式文件：

1. `docs/V3_TODAY_RESEARCH_PRIORITY_DETAILED_UPGRADE_PLAN_20260914.md`：原位升级设计。
2. `docs/V3_TODAY_RESEARCH_PRIORITY_AUDIT_CHANGELOG_20260914.md`：本说明与独立问题登记。

工作区开始时已有大量未提交变更，包括业务代码、配置和其它文档，以及删除的历史报告。本轮没有回滚、覆盖或提交这些变更；原方案在Git中本就未跟踪，因此普通git diff不能独立展示其v1.0→v2.0全文差异，本说明以原始hash与逐项映射留痕。

原文输入：41,254字节；SHA-256：`e69966d6e97068825fdd69759ba62c400120d558ff740d4675677cf330a9cef1`。原文被完整阅读后原位升级，不是追加一个相互冲突的补丁附录。

## 8. 阶段结论

`stage_contract=V3_TODAY_RESEARCH_DESIGN_AUDIT_V2`；`acceptance_result=DEGRADED_PASS`。本轮完成设计全面审计与两份文档交付；工程实现与有效性尚未放行。下一实施阶段是P12-01，需按当时最新文档和输入重新冻结基线，再进入因子与扫描器实施；本说明不自动启动构建或修改生产数据。

## 9. 审阅文件与内容指纹

以下指纹由本轮文档发布前读取当前工作区生成，便于定位审计依据；不是Git提交标识，也不证明数据库长期未变。

| File | SHA-256 |
|---|---|
| `AGENTS.md` | `b72647b6275f6ae3489a24ccc8a9e1e29d0e440739c3e2f360c7f05bf44e403d` |
| `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` | `e5dbafcbd61732cb5d6bd8b70ef15255ff723457820b7d08116b52c0c6f3736f` |
| `docs/V3_IMPLEMENTATION_LEDGER.md` | `8897d6484a28c8012a3fadac5ebae13073b88bdedd8158ac13b44442946dc0bd` |
| `docs/FULL_ALGORITHM_LOGIC_AUDIT_AND_OPTIMIZATION_20260914.md` | `b28df2487e7580a2e40c9ed07dfe1a4395fa050f56764675a263616797083ed3` |
| `docs/ALGO_R1_CORRECTNESS_RECEIPT_20260914.md` | `9fd6805cce1f36b869eb6473b92077823d2939abee267033e1ae9e7b97079fdb` |
| `docs/V3_CURRENT_STRENGTH_REAUDIT_20260914.md` | `8c02d1e86a189154c724d00fbb5609e835aca8bcfbdb8a016ae56d06e56282d6` |
| `docs/V3_FINAL_CANDIDATE_AND_PHASE_REVIEW_20260914.md` | `46f0ea9be0e2216b8f537ca0e7464495eb9d53c6707482cca0e8f97cacf9410a` |
| `docs/ADJUSTMENT_CONTRACT_V0_3.md` | `8fa2c46e7c025042684e184555a7cef2aac09068a8f5c9fccff1b8f5de0561bf` |
| `docs/TRADING_CALENDAR_CONTRACT.md` | `2146fd912a5bd077cbcc778871668a2a9bd9f086c57f9acbc4865fc8c06a9abb` |
| `config/research_attention_v3.yaml` | `3b94b19fc5494885ccfc31079e12872ee54a0de5dab69f5a59ab8eea781d14d5` |
| `src/normalize/phase1.py` | `78bc99490426863597e65cdd2a5a41f2c69772c9e238bd9bbc711190f2402c08` |
| `src/factors/registry.py` | `c6486d571be26412ba841e1cf79cd14010079e79dfafc2e534afd1a90dd4d7b1` |
| `src/workbench_analysis/research_features.py` | `1393f4d33f8b6aecb2e666d57e9cd528859a21b8a7712e3749e8f7f2c59a5b20` |
| `src/workbench_analysis/stock_attention.py` | `9bccf4fa7c7fdcba5a9d0c7b8bf81f045e9698f9193c1811f1022ae4f76b30b8` |
| `src/workbench_analysis/strength.py` | `00ff1068ab26ca676defb19eef2886d2016802dec6a8867aa511dd508c5c530b` |
| `src/workbench_service/research_builder.py` | `19cd8c4d915536ec39fddff94f4637fa079c641489d5b65eb1bd25a90570d883` |
| `src/workbench_service/research_association.py` | `e007c4679d557f51645f10252a6ac6d0a646aacd41906cfc3a5043f40504e663` |
| `src/workbench_service/app.py` | `7e5bcf8652bc48157b8787625aeb8b7a3829290119077f013aa00b16848427eb` |
| `src/workbench_service/static/v2/v3-unified.js` | `5e07703e8ce2cbc9fb2367f8349f5c91eb87210ebca37fa0e3a7f87794b619c9` |
| `src/production/daily.py` | `9b377f585f79840b3972281ee9277f0eff9042ba097d90d030e98541f9752380` |

Audited plan SHA-256 (v2.0 historical): `70f18a8f070202b593a8205d19fcd88bb693740ef75a16fa67f96b8ae4349325`

## 10. v2.1线上审计意见处理追加记录

本节记录后续用户提供线上审计后的订正。前面§1–9是v2.0历史说明，版本、数据查询及指纹保留原时点，不代表重新执行。本次源方案已原位升级为 `v2.1-AUDITED`，候选合同同步从V3_2更新为V3_3；没有执行扫描器开发或生产构建。

输入文档：`D:/Users/lps/Desktop/V3_TODAY_RESEARCH_DESIGN_AUDIT_20260914.md`，SHA-256：`b9a4cfbe4fecf83c3ddd5c396e422579913f3ff77fe819385b75086a3db102e0`。把外部文本视为待核实意见，未把它的评级、P0级别或“必须”条款当用户执行授权。

完整逐项采纳表见源方案§23，重要裁决：

- 修正风险函数无上限，但不接受“当前四类因此必然漏入大跌股”的推断：四类自身已有正收益/非负收益门。新增绝对8%与相对4%底线/2倍prior波动的三值OR，8%只是公开候选初值，未宣称验证最优。
- 不强制Full LOO。原方案已注明只剔除成员支持，不重算全轨道；本次进一步统一字段为CURRENT_WITH_LOO_BREADTH_SUPPORT，标记full_track=false。Full LOO对市场、同类排名和重叠板块的删除范围须新合同，不能只重算几项就冒称完整。
- 采纳并扩展回踩事件重构：顺序seed/推进峰值/回调/确认，新增缺日、左截断、峰值重置、20/10会话上限、终态再入及首次确认规则；不能回看t后挑有利锚。
- 回踩收缩改为峰后至t-1对峰前5日金额；t日确认金额独立，评分同步改字段。防止回踩缩量、确认放量反而被拒。
- 多概念保留真实ANY关联支持，增加预先冻结关系集合、tested/evaluable/unknown/支持计数和行业/概念分层。没有可靠主概念数据，也没有证据支持行业一律优先，故不新增主概念等级或任意前K关系门；选择偏差仍独立跟踪。
- 信号依赖锁定传递源码/参数/环境且要求可恢复；复用锁定实现，不复制第二份算法。
- 后验采用每个观察窗口到期日e为本地仿射共同锚，冻结RAW/事件/版本/采集时点；事后修订新建evaluation_revision，e后事件不改旧评价，评价不回写t信号。
- 当前2000万元流动性门保留；效果以真实前瞻及预登记现代PIT段为主，早期年代仅诊断，不无证据叠金额分位资格。
- 延续场景保留STOCK_ONLY影子对照，首页仍要求成员支持；保留固定评分，增加唯一简单排序基线及最多3套预登记候选预算，不继续微调各阈值。

同步完善输出字段、P12各阶段新增证据、依赖窗口、25项固定反例；独立新增关系多重性、回踩事件、评价锚专项。设计可核实问题已经订正，但专项的实现/实证验收仍OPEN，不由文档修改自动关闭。

核查依据为当前research_association.py、stock_attention.py、research_attention_v3.yaml、本地tdx_adjustment.py与调整合同、AGENTS及最新台账。原方案v2.0SHA-256确认未在审阅期间被其他任务改动。本轮未读取TDX、未重跑数据库统计，源§2保留上一轮只读数据基线。

阶段合同 `V3_TODAY_RESEARCH_EXTERNAL_REVIEW_DISPOSITION_V2_1`；结果 `DEGRADED_PASS`，限设计核实与订正；下一阶段P12-01。写入仍仅源方案与本修改说明，在docs内原子替换。验证包括段落/合同引用一致性、评分权重、风险边界与金额示例的独立算术检查、Markdown围栏/本地链接及新旧文本差异检查；不是新业务算法已通过测试或效果验收。

Audited plan SHA-256 (v2.1): `8c80537cfdb6ea30be72945712942dc5c95d1d57ba1d364db333100c01d0ea1a`
