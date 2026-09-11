# 龙字诀 v2.1.2 功能审计与工作台借鉴报告（本地基座＋在线增强版）

## 1. 审计说明

- 样本：`D:\Users\lps\Desktop\龙字诀v2.1.2.exe`
- SHA-256：`A25700BB9F284F628CFEE5BC1B67FB85AB9E981D32A64A18EBE6589AAC525926`
- 文件大小：85,037,257 字节，未发现数字签名或版本资源。
- 技术栈：64 位 PE 启动器、PyInstaller 单文件包、Python 3.12、PyQt6、Matplotlib、Requests、SQLite/本地 JSON 缓存。
- 包内规模：7,306 个归档条目，`PYZ.pyz` 内 2,277 个 Python 模块；本报告覆盖主入口及全部识别出的产品模块，第三方运行库不作为软件业务功能重复罗列。
- 方法：只做静态读取，未启动 EXE、未登录、未调用其在线接口，也未修改原文件。
- 限制：这是代码结构、常量、类/函数、界面文字和接口地址的静态审计，不是完整源码还原。运行时服务端配置、账号套餐和远端返回结构可能改变，因此收费边界分为“确认”“强线索”“待运行验证”。

## 1.1 修订后的数据定位

通达信本地数据是当前项目的基础数据源和可复现测试基座，不代表工作台只能使用离线数据。建议采用两层数据架构：

1. **本地基础层**：通达信日线、复权、板块成员和本地事件承担历史计算、公式测试、回归测试、断网可用及结果复核。
2. **在线增强层**：免费或可合法使用、稳定性可接受且字段可验证的数据源，可以按独立适配器接入实时行情、涨停原因、龙虎榜、资金流、热榜和投资日历。

在线数据不得静默覆盖本地字段。每条增强数据都应携带来源、请求时间、数据交易日、缓存状态、失败原因和适配器版本；在线失败时降级到本地数据，不影响基础工作台。

需要注意：仓库根目录 `AGENTS.md` 已允许受控 M14 在线增强；真正接入时仍须遵守逐 dataset capability gate、请求预算、失败降级和不写本地热榜快照的规则。

## 2. 产品总体结构

软件是一个多页签的短线行情研究终端。核心思路不是单一选股公式，而是把市场情绪、涨停梯队、题材/主线周期、个股热度、新高、龙虎榜/游资、投资事件及复盘导出集中在同一桌面界面，并提供股票代码点击联动到外部交易/行情终端。

其典型数据链路为：

1. 从多个在线行情或资讯接口抓取当日/历史数据；
2. 按交易日和接口类型落地 JSON 缓存；
3. 将题材、股票、涨停层级、资金、事件等转换为内部模型；
4. 进行合并、去重、分层、排序、筛选和交叉选择；
5. 在 PyQt 表格、卡片和 Matplotlib 图表中展示；
6. 支持导出 JSON、Markdown、HTML、Excel、PNG 或股票代码文本；
7. 部分模块经过会员状态或服务端鉴权控制。

## 3. 完整功能清单

### 3.1 首页/增强行情总览

确认功能：

- 题材热点聚合，显示题材标题、题材股票、成交额/资金、最高板、开板数等。
- 题材成员股与同花顺涨停状态合并；按股票代码去重，补充涨停、资金、热门名称等字段。
- 涨停、炸板、跌停等资金流池展示。
- 涨停梯队卡片视图，支持只看涨停、过滤断板/大阳线、题材高亮和股票点击联动。
- 表格手工排序、选择行同步、高亮同题材、搜索匹配置顶。
- 交易日和交易时段判断；支持手动刷新与定时刷新，并计算下一交易日 9:25 等待时间。
- “天眼模式”、置顶、全局字号、斑马纹、紧凑行等界面设置。

处理逻辑：题材块和成员股分别解析，再按代码合并；标题行与股票行使用不同渲染规则；同一股票可跨题材出现，界面允许按题材联动高亮。部分榜单使用稳定排序保留原接口顺序。

可借鉴：将工作台首页改为“市场概况 → 强势板块 → 板块梯队 → 代表个股”的渐进式视图；基础结果读取本地发布快照；在线增强适配器可以补充盘中行情和榜单，并与本地字段清晰区分。

### 3.2 市场情绪、涨停梯队和资金池

确认功能：

- 涨停、炸板、跌停池并列展示。
- 连板高度和梯队构建，区分首板、二板及更高板。
- 题材分布、涨停线、情绪区域和池数据聚合。
- 同花顺与选股宝两类池数据合并、去重。
- 市场温度、涨停数、炸板数、跌停数、炸板率、涨停率、上涨/下跌家数等指标。
- 按 30/60/90/120/250 个交易日绘制市场周期曲线和情绪柱状图。
- 上证指数收盘/涨跌、两市成交额与情绪指标对齐。
- 鼠标悬停竖线、信息面板、曲线开关、历史表格、数据修复对话框。

处理逻辑：多接口并发拉取后转换成统一 `FlowStockRow`、`Echelon` 和情绪日记录；涨停池按层级打包；市场周期按交易日缓存，盘前、盘中、收盘后采用不同的当日缓存策略；零值异常日支持重新校验。

可借鉴：离线通达信数据可完整实现上涨/下跌家数、涨停/跌停近似识别、成交额、炸板近似（需要日内高价触板但收盘未封板）、连板统计、市场温度历史曲线。精确涨停原因和实时炸板时间无法只靠日线复现。

### 3.3 题材周期矩阵

确认功能：

- 按多个交易日展示题材及其股票，形成题材周期矩阵。
- 解析题材高度、最高板、资金/成交额、流通市值、股票涨幅等。
- 看多/大阳线过滤、Top-N 高亮、同题材跨日高亮。
- 点击曲线或单元格查找题材/股票，支持平滑周期曲线和命中测试。
- 支持按 JSON/Markdown 导出题材周期数据。

处理逻辑：每天的题材列表与题材成员列表独立抓取，按题材 ID/名称归并；股票代码标准化；题材跨日聚合后计算出现频次、持续天数、每日成员和高度变化。矩阵允许数据源标签化，避免不同来源直接混为一体。

可借鉴：使用本地板块成员快照和每日板块因子，构建“板块连续上榜天数、强度变化、成员扩散/收缩、龙头更替”的时间矩阵。这是最适合迁移到当前工作台的功能之一。

### 3.4 主线周期/题材挖掘

确认功能：

- 双数据源切换：选股宝类数据源与交易/资讯类数据源。
- 主线题材聚合表、每日题材表、股票详情表。
- 5/10/20/30 日区间选择。
- 题材搜索、股票搜索、只看涨停或包含非涨停股。
- DIY 挖掘：导入条件、后台匹配、进度显示、结果导出。
- 板块曲线、股票代码点击联动、缓存预热和自动拉取。
- 主线周期 JSON/Markdown 导出。

处理逻辑：按日期读取题材与成员，计算题材出现频次、延续性、成员变化和汇总金额；不同数据源通过适配器转为统一快照；表格按题材汇总行与成员行分层渲染。

可借鉴：用本地数据定义可复现的“主线”基础规则，并以在线题材热度、涨停原因和新闻作为独立增强证据，例如近 N 日进入板块强度前列的次数、连续性、上涨宽度、成交额扩张、强势成员保留率，而不是简单累计涨幅。DIY 挖掘可以改为合同化筛选器，不允许用户任意生成不可审计指标。

### 3.5 板块精选与板块内选股

确认功能：

- 板块、子板块、成员股三级浏览。
- 板块强度、涨幅、量比、金额等字段格式化和着色。
- 板块表和个股表独立排序；支持中文排名文本解析。
- 板块选择状态保存与恢复。
- 股票列表按交易窗口缓存，减少重复请求。
- 题材/概念条带选择，点击股票卡片联动。
- 多板块交叉选股，计算所选板块成员交集。
- 股票选择对话框、导出可见股票代码、搜索过滤。
- 炒作原因/异动原因的当日与历史时间线弹窗。

处理逻辑：板块 ID 是主键，成员股先标准化再缓存；交叉选股对多个板块成员集合求交集；板块和股票排序值从显示文本中安全解析；原因信息另行请求并以时间线呈现。

可借鉴：当前工作台已经有板块—个股联动，可增加“选择 2～4 个板块求交集”“板块内筛选五类结构”“成员留存率”“板块内排名变化”。炒作原因可由经过验证的免费在线资讯接口或用户导入补充，但必须显示来源，不能从价格走势反推并冒充事实原因。

### 3.6 概念库与交叉概念选股

确认功能：

- 概念列表、概念详情、概念成员卡片。
- 概念名称搜索、股票名称/代码搜索、排序和展开全部。
- 多概念选择后求共同股票。
- 批量股票报价/涨幅补充。
- 概念本地缓存、强制刷新、会员强制刷新路径。
- 天眼结果在信息栏显示。

处理逻辑：概念元数据与成员详情分离加载；股票详情可批量补充；交叉选择先确保各概念成员已加载，再做集合交集；存在普通加载和 `forced_vip` 强制刷新两条路径。

可借鉴：为本工作台建立只读“板块属性库”，提供交集、并集、排除标签和成员变化审计。离线通达信已有行业/概念/风格成员，可直接实现大部分功能。

### 3.7 投资日历、题材事件和事件关联股票

确认功能：

- 月历/日期选择、事件列表、概念列表、关联股票列表和详细信息。
- 事件按日期、时间范围、类型、新近状态、置顶状态筛选。
- 股票代码、事件原因、最高板、涨停数、股票数等字段。
- 同花顺投资日历、东方财富日历、财联社日历等多来源迹象。
- 月份缓存、最近事件标记、新事件计数、事件时间线。
- 投资日历 JSON/Markdown 导出。

处理逻辑：多个自然月的数据合并为日期映射；事件使用稳定键去重；对当前月份与相邻月份选择性刷新；事件与概念、股票通过代码/名称关联。

可借鉴：以本地公司行为日历作为可复核基座，同时接入免费且稳定的在线投资日历，补充政策、行业会议和公司事件。在线事件必须去重、标源、缓存并显示更新时间。

### 3.8 龙虎榜、游资榜和资金明细

确认功能：

- 龙虎榜简图和明细两个子页签。
- 游资榜、游资净额、营业部/席位、概念标签等。
- 日期选择、刷新、缓存修复、点击行查看明细。
- 数据格式化为万元/亿元，支持按净额排序。
- JSON 导出和 AI 复盘引用。

处理逻辑：按交易日请求榜单，解析股票行与游资明细行；概念和榜单标签单独处理；17:00 前后选择不同目标交易日并决定是否落盘缓存。

可借鉴：通过独立在线适配器接入可合法免费访问的龙虎榜数据，按交易日缓存并保留来源；本地成交额、换手和异常放量作为辅助字段。在线源失效时明确显示不可用。

### 3.9 创新高、RPS 与趋势曲线

确认功能：

- 20/30/60/100 日创新高分类。
- 市场创新高趋势、板块创新高趋势、个股趋势曲线。
- RPS 选择器与连续/单日模式。
- 三张联动表：日期/板块、板块成员、股票明细。
- 搜索高亮、表格同步滚动、手工排序、周期曲线弹窗。
- 近期多个交易日数据抓取、缓存和 JSON/Markdown 导出。

处理逻辑：按日期获取创新高分组，解析 `GroupList/GroupName/List`；股票代码标准化后按板块聚合；连续模式统计跨日出现情况；RPS 作为筛选维度而非单一结论。

可借鉴：本项目已有 `DIST_HIGH20/60`、`POS20/60/120`、RS/RPS 类字段，可完全离线实现创新高池、连续创新高、板块创新高宽度和趋势曲线，而且数据可追溯性会优于在线软件。

### 3.10 涨停分析与涨停原因

确认功能：

- 同花顺涨停分析接口，按题材标签组织股票。
- 展示异常原因、详细原因、股票名称代码和题材导航。
- 过滤接口附带的 AI 免责声明尾部。
- JSON/HTML 导出。
- 另有交易/资讯站点版本的涨停原因快照。

处理逻辑：按交易日请求题材标签页，每个标签页包含股票及原因；转换成精简字段后分组展示。原因文本来自外部资讯，不是行情计算结果。

可借鉴：页面结构值得借鉴，可增加“结构命中原因”和“板块关联依据”分组视图；但真实涨停原因必须来自合法外部资讯或人工输入，不能用价格模式伪造。

### 3.11 同花顺热榜、热门题材和热门个股

确认功能：

- 小时榜、日榜；普通热榜与飙升榜。
- 概念热榜、行业热榜、热门个股、热门话题。
- 热度排名变化、标签解析、题材与股票聚合。
- Markdown/JSON 导出。

处理逻辑：榜单按类型分别请求；统一为板块行或股票行；对排名变化和标签做格式化；失败时可读缓存。

可借鉴：在线热榜作为独立的“平台关注热度”；本地成交额百分位、换手变化、板块成员扩散和队列覆盖作为“行情热度代理”。两者并列展示，不合成为含义不清的总分。

### 3.12 AI 复盘与批量导出

确认功能：

- 按日期拉取并展示 HTML 复盘报告。
- 本地 HTML 导入。
- 在浏览器打开、日期列表、手动刷新、后台抓取。
- 统一导出：龙头周期、梯队周期、游资榜、投资日历、主线周期、市场周期、创新高、同花顺热榜、题材周期、选股宝题材、涨停分析等。
- 输出 JSON、Markdown、HTML；部分表格支持 Excel、PNG 和代码文本。
- 用户可配置导出目录、可见页签、各周期交易日数量和 Top-N。

处理逻辑：每类导出由独立 Model 负责抓取、清洗、建模和保存；AI 复盘页仅显示成功获取的日期；网络操作放在线程中并带超时；缓存路径按功能/年月/日期组织。

可借鉴：给当前工作台增加“每日研究快照导出包”，只使用本地发布数据库，导出 HTML/Markdown/JSON，并嵌入合同版本、数据截止日、来源摘要和哈希。

### 3.13 外部终端联动与盯盘模式

确认功能：

- 点击股票代码发送到外部交易/行情终端。
- 通达信、同花顺、东方财富等平台选择迹象。
- 天眼/盯盘模式、窗口置顶、当前页刷新。
- 表格与卡片的统一代码点击处理。

处理逻辑：股票代码先标准化，再通过全局 trader/平台回调发送；不同表格共用联动入口。

可借鉴：工作台可增加“复制代码”“调用本地通达信定位股票”的可选适配器，但必须只做查看联动，不做自动下单。

### 3.14 缓存、容错与数据修复

确认功能：

- 交易日感知缓存、内存缓存和磁盘 JSON 缓存。
- 并发线程池、请求超时、重试、取消和 worker 清理。
- 旧缓存清理、空结果不落盘、缓存回退。
- 数据修复对话框和异常日期重新验证。
- 配置、表格列顺序、字体、斑马纹、市场周期显示偏好持久化。

可借鉴：本项目应继续坚持接口分页、服务器缓存、原子写入和发布快照不可变；可以增加按页面结果缓存和失效键，但不能跳过发布身份校验。

### 3.15 登录、会员、积分和版本更新

静态代码确认存在：

- 登录、注销、设备 ID、验证码、鉴权失败处理。
- 会员状态、会员到期提示、续费入口、会员模块说明。
- VIP 模型动态更新、测试 VIP、部分模块 VIP 判断。
- 积分显示与积分兑换对话框。
- 服务端配置拉取、公告/福利链接、反馈服务。
- 自动/手动版本检查、下载对话框、百度/夸克下载地址配置。

明确会员线索：概念详情存在普通刷新与 `forced_vip` 强制刷新路径；部分全景/周期模块含 `_is_vip`、`_show_vip_prompt`；主线数据源存在 `_is_valid_member`；AI 复盘和导出模块调用软件自有服务鉴权。

无法仅凭静态代码确认：每个页签当前版本究竟免费、限次、积分兑换还是会员专享；服务端可动态下发模块权限。因此本文不编造具体收费表，需在隔离环境使用合法账号逐页验证。

可借鉴：当前工作台不需要复制该软件的会员体系。若未来多用户部署，可以借鉴“能力开关＋服务端配置＋清晰失效提示”，但研究算法本身不应因账号等级改变。

## 4. 数据来源与用途

| 来源 | 静态证据中的域名/接口 | 主要用途 | 建议接入定位 |
|---|---|---|---|
| 选股宝 | `flash-api.xuangubao.cn`、`flash-api.xuangubao.com.cn` | 涨停/炸板/跌停池、题材与成员、市场情绪线 | 在线增强候选；需验证访问条款、频率、字段和稳定性 |
| 同花顺 | `data.10jqka.com.cn`、`dq.10jqka.com.cn`、`ozone.10jqka.com.cn`、`quota-h.10jqka.com.cn`、`comment.10jqka.com.cn` | 市场概览、涨停分析、热榜、游资、指数 K 线、投资日历 | 高价值在线增强候选；每个子接口应分别验证，不视为统一免费 API |
| 东方财富 | `push2ex.eastmoney.com`、`datacenter-web.eastmoney.com` | 资金流、投资日历 | 在线增强候选；使用本地行情交叉校验日期和代码 |
| 龙虎榜/开盘啦类站点 | `longhuvip.com` 多个子域 | 创新高、板块、成员、炒作原因 | 语义价值高；需重点验证授权、Cookie 和限流 |
| 新浪/搜狐/腾讯行情 | `hq.sinajs.cn`、`finance.sina.com.cn`、`q.stock.sohu.com`、`qt.gtimg.cn` | 个股报价、涨幅、历史行情补充 | 行情补充或故障交叉校验，不替换本地历史基座 |
| 财联社 | `cls.cn/api/calendar` | 投资日历 | 在线事件增强候选；按来源显示摘要和日期 |
| 软件自有服务 | `www.loong1.com/prod-api` | 登录、会员、配置、反馈、部分市场/复盘服务 | 龙字诀私有服务，不应未经授权复用 |

注意：接口地址只证明程序包含调用路径，不代表接口公开授权、永久免费、当前可用或适合直接复制。接入前应验证使用条款、Cookie/Token、限流、字段稳定性和缓存许可；不复制龙字诀私有鉴权、密钥或会员绕过机制。

## 5. 个股处理逻辑

1. 股票代码标准化：不同来源的代码统一，随后用于去重、合并和外部终端联动。
2. 多源合并：题材成员、涨停状态、热门标签、资金和榜单详情按代码拼接。
3. 分层模型：股票被转换为 `StockRow`、`FlowStockRow`、`TopicStockRow` 等用途模型，避免直接用接口 JSON 渲染。
4. 队列/梯队：按涨停高度、状态、金额等组成首板到高板梯队，并保留题材分组。
5. 跨日连续性：创新高、题材周期、主线周期会追踪股票跨多个交易日出现情况。
6. 搜索与排序：代码/名称搜索，数值列使用真实数值排序而非字符串排序。
7. 交叉选择：多个概念成员集合求交集，得出共同股票。
8. 原因信息：涨停原因、炒作原因和游资信息来自独立资讯接口，未与量价推导混淆。
9. 缓存：股票列表和详情按交易窗口或日期缓存，过期后刷新。

对当前工作台最有价值的是“内部统一模型、多板块交集、跨日留存、真实数值排序、原因与量价分离”。不建议照搬在线热榜作为研究证据。

## 6. 板块与题材处理逻辑

1. 板块/题材先有独立 ID，再关联成员股票；名称主要用于展示。
2. 板块、子板块、股票形成层级树；支持保存选择状态。
3. 题材跨日聚合，计算出现频次、周期延续、成员变化、最高板和总金额。
4. 不同来源的同名题材不会天然可信地合并，而是通过适配器和来源标签处理。
5. 题材矩阵按日期横向排列，可高亮同题材和代表股票。
6. 板块内股票支持强度着色、数值排序、搜索和导出。
7. 多个板块可求成员交集；板块选择结果可用于后续股票详情。
8. 题材原因、事件和热度属于外部语义，不等同于板块价格强度。

对当前工作台的直接启发：在现有“强势关联板块 V1”之上增加板块跨日状态、成员强势留存率、代表股更替、交叉板块选股和来源/语义标签隔离。

## 7. 免费与收费功能判断表

| 功能 | 静态判断 | 证据与说明 |
|---|---|---|
| 基础 UI、表格、搜索、排序、缓存 | 大概率基础能力 | 没有看到局部 VIP 函数，且是通用基础设施 |
| 首页行情、涨停池、题材显示 | 免费/会员边界待验证 | 数据接口本身分散，权限也可能由远端配置控制 |
| 概念库普通加载 | 存在普通路径 | 同模块另有 `forced_vip` 路径 |
| 概念库强制刷新 | 明确会员线索 | `_load_concept_details_forced_vip` |
| 主线双数据源 | 明确会员校验线索 | `_is_valid_member` 和会员模型更新 |
| 全景/周期类高级模块 | 明确会员线索 | `_is_vip`、`_is_vip_cached`、`_show_vip_prompt` |
| AI 复盘/批量导出 | 账号或服务端权限线索 | 使用软件自有 `prod-api` 鉴权和可见页签配置 |
| 积分兑换 | 确认存在 | `PointsExchangeDialog` 和积分显示更新 |
| 版本更新、公告、反馈 | 基础服务 | 自有服务端配置和下载链接 |

结论：软件采用“本地客户端功能＋远端会员模型/模块开关”的混合授权，不能从一个 EXE 静态地恢复当前账号套餐表。

## 8. 建议迁移到当前工作台的优先级

### P0：高价值且本地数据可完整实现

1. 板块周期矩阵：近 5/10/20/30 日强度、排名、宽度和成交额变化。
2. 板块成员留存与龙头更替：昨日强势成员今天保留多少、首位股票是否变化。
3. 市场情绪历史：上涨/下跌、涨停/跌停、成交额、创新高数量、队列数量。
4. 创新高/RPS 页面：20/30/60/100 日创新高与连续出现统计。
5. 多板块交叉选股：行业＋概念＋五类结构的集合筛选。
6. 每日研究导出包：HTML/Markdown/JSON，带发布 ID、合同版本和哈希。

### P1：本地＋在线增强，需先定义数据合同

1. 本地涨停梯队与连板统计，在线池补充实时封板和炸板状态。
2. “行情热度代理”，使用成交额、换手、宽度和队列覆盖，不能叫互联网热榜。
3. 主线周期描述规则。
4. 板块趋势曲线、市场温度和历史详情弹窗。
5. 本地公司行为/用户导入事件日历。

### P2：依赖在线资讯，验证免费性与合规性后实现

1. 龙虎榜席位与游资明细。
2. 涨停原因、炒作原因、题材新闻。
3. 同花顺/选股宝用户热榜。
4. 在线投资日历和 AI 生成复盘。

这些功能可以通过数据源插件接入；任何在线字段缺失时必须显式降级，不能由价格数据冒充。

## 8.1 在线数据源接入分级

静态分析无法单凭“无需在客户端写账号”就认定接口永久免费。建议实际接入时分四级：

- **A 级：明确开放/官方免费接口**——有公开文档或明确许可，可直接开发适配器。
- **B 级：网页公开数据接口**——浏览器可访问但无正式开放承诺；仅用于个人研究，设置低频缓存、失败降级和字段监控。
- **C 级：依赖 Cookie、动态签名或易变参数**——技术上可能可取，但维护和使用条款风险较高，不作为核心依赖。
- **D 级：龙字诀自有鉴权、会员或私有接口**——不复用。

第一批验证顺序建议：东方财富公开行情/资金接口、交易所或官方披露数据、公开投资日历、公开龙虎榜；随后再评估选股宝和同花顺网页接口。每个适配器先做只读样本验证和字段合同，不能直接写进正式扫描链路。

## 8.2 推荐的融合架构

1. `local_core`：通达信价格、成交量、板块成员和全部结构因子。
2. `online_market`：实时价格、涨停池、炸板池和市场广度。
3. `online_semantic`：涨停原因、题材事件、投资日历、龙虎榜和平台热榜。
4. `normalizer`：代码、交易日、单位和字段语义统一。
5. `evidence_store`：保存来源、原始响应哈希、抓取时间和适配器版本。
6. `workbench_api`：分页返回本地结果及在线增强状态，页面不直接调用第三方接口。

这样既能继续用本地数据开发和回归，又能在在线数据可用时获得龙字诀式的实时性和语义信息。

## 9. 不建议照搬的设计

- 多个第三方接口硬编码在客户端，稳定性、授权和字段漂移风险较高。
- 在线数据与本地缓存来源较多，若缺乏统一身份容易出现日期混用。
- 部分“热度、题材、原因”来自平台定义，不具备跨来源可比性。
- 客户端会员与配置依赖远端服务，离线可复现性弱。
- 单文件打包内含大量依赖，体积大且不利于审计。

当前工作台应借鉴交互结构和数据建模方式，但继续保持本地数据、版本化合同、发布快照、解释性输出和无自动交易。

## 10. 静态证据索引

- 主窗口和会员：`tab_manager`
- 首页和梯队：`tab.tab_1_*`、`tab.echelon_view5`
- 情绪/池：`api2.services.mood_section_service`、`tab.tab_2_*`、`tab.tab_3_vc`
- 热榜：`tab.tab_5_vc`、`api.ths_hot_list`
- 主线：`tab.tab_6_*`
- 题材周期：`tab.tab_7_*`、`ai_review.exports.topic_cycle_export`
- 概念库：`tab.tab_11_*`
- 投资日历：`tab.tab_12_*`、`ai_review.exports.investment_calendar_export`
- 市场周期：`tab.tab_15_*`、`ai_review.exports.market_cycle_export`
- 龙虎榜/游资：`tab.tab_16_*`、`ai_review.exports.hot_money_export`
- 创新高/RPS：`tab.tab_20_*`、`ai_review.exports.new_high_export`
- AI 复盘和导出：`ai_review.*`
- 板块精选：`kpl2.*`
- 版本更新：`update.*`

## 附录 A：逐模块类与函数清单

以下是全部已识别产品模块的静态代码对象清单。`<module>`、推导式和匿名函数已省略；没有命名函数的包初始化模块标为“无命名函数”。这份附录用于保证功能审计可追溯，并不等于复制或公开原始源码。

### `ai_review`

代码对象数：1。

函数/类：无命名函数。

### `ai_review.export_ui_config`

代码对象数：1。

函数/类：无命名函数。

### `ai_review.exports`

代码对象数：1。

函数/类：无命名函数。

### `ai_review.exports.dragon_cycle_export`

代码对象数：21。

函数/类：`DragonCycleExportModel`、`_compound_pct`、`_fetch_daily_pct_map`、`_fetch_jygs_maps`、`_fetch_pool_with_retry`、`_normalize_code`、`_one`、`_ymd_to_dash`、`build_dragon_cycle_json`、`dragon_cycle_latest_trading_ymd`、`fetch_dragon_cycle_jygs_maps`、`fetch_dragon_cycle_jygs_maps_full`、`run_dragon_cycle_export`、`run_dragon_cycle_period`、`save_dragon_cycle_json`、`toolbar_data_source_suffix`。

### `ai_review.exports.echelon_cycle_export`

代码对象数：20。

函数/类：`EchelonCycleExportModel`、`_fetch_three_pools`、`_is_today_ts`、`_label_for_ymd`、`_limit_strings_and_model_from_flow`、`_md_escape_cell`、`_one`、`build_echelon_cycle_json`、`build_echelon_cycle_markdown`、`build_echelon_table1_cells`、`fetch_one_day_echelon`、`pool_detail_url`、`run_echelon_cycle_fetch`、`save_echelon_cycle_json`、`save_echelon_cycle_markdown`、`toolbar_data_source_suffix`。

### `ai_review.exports.hot_money_export`

代码对象数：35。

函数/类：`HotMoneyExportModel`、`_Concept`、`_Data`、`_HotMoney`、`_HotMoneyItem`、`_Item`、`_Response`、`_cache_root`、`_fetch_hot_money_for_date`、`_fmt_net_wan`、`_fmt_net_wan2`、`_hot_money_cache_path`、`_http_get`、`_make_hot_money_info`、`_parse_hot_money_json`、`_should_write_cache`、`_sort_hot_money`、`_split_lines_to_rows`、`_stock_board_tag`、`build_hot_money_json`、`build_plain_hot_money_lists`、`parse_concept`、`parse_data`、`parse_hm_item`、`parse_item`、`percent`、`resolve_hot_money_target_date`、`run_hot_money_export`、`save_hot_money_json`、`save_hot_money_markdown`、`toolbar_data_source_suffix`。

### `ai_review.exports.investment_calendar_export`

代码对象数：21。

函数/类：`InvestmentCalendarEventStore`、`InvestmentCalendarExportModel`、`__init__`、`_apply_store_and_flags`、`_cache_root`、`_format_display_text`、`_http_post_timeline`、`_load`、`_merge_months_into_date_map`、`_months_to_render_for_now`、`_parse_days_from_json`、`_save`、`_store_path`、`build_investment_calendar_json`、`build_investment_calendar_markdown`、`run_investment_calendar_refresh`、`save_investment_calendar_json`、`save_investment_calendar_markdown`、`toolbar_data_source_suffix`、`update_and_show_new`。

### `ai_review.exports.main_line_cycle_export`

代码对象数：20。

函数/类：`MainLineCycleExportModel`、`_attach_stocks_to_topics`、`_fetch`、`_format_plate_total_yi`、`_label_for_ymd`、`_md_escape_cell`、`_parse_amount_yi`、`build_main_line_cycle_json`、`build_main_line_cycle_markdown`、`build_main_line_table1_cells`、`run_main_line_cycle_fetch`、`save_main_line_cycle_json`、`save_main_line_cycle_markdown`、`toolbar_data_source_suffix`。

### `ai_review.exports.market_cycle_export`

代码对象数：38。

函数/类：`MarketCycleExportModel`、`_build_sh_index_daily_pct_map`、`_cache_file_path`、`_cache_root`、`_calc_broken_ratio_pct`、`_count_src`、`_d`、`_emotion_response_ok`、`_fetch_one_trading_day`、`_fetch_overview_day`、`_fetch_xgb_broken`、`_fetch_xgb_hot`、`_get_ths_cookie`、`_http_get_json`、`_lookup_sh_close`、`_md_escape`、`_merge_row_for_table`、`_overview_response_ok`、`_parse_emotion_broken`、`_parse_emotion_hot`、`_parse_overview_data`、`_parse_turnover`、`_request_json_cached`、`_task`、`_ths_overview_headers`、`_xgb_headers`、`_xgb_line_payload_keep_data_last_only`、`build_market_cycle_json`、`build_market_cycle_markdown`、`build_market_cycle_table_strings`、`fetch_sh_index_kline_close_map`、`run_market_cycle_export`、`save_market_cycle_json`、`save_market_cycle_markdown`、`toolbar_data_source_suffix`。

### `ai_review.exports.new_high_export`

代码对象数：33。

函数/类：`NewHighExportModel`、`_cache_file_path`、`_cache_root`、`_cell_text`、`_d`、`_device_id`、`_fetch_one_day`、`_format_cap_tab20`、`_format_money_tab20`、`_http_post_plate`、`_md_escape`、`_one`、`_parse_group_list`、`_plate_response_usable`、`_should_write_plate_cache`、`_stock_rows_from_group`、`_ymd_to_label`、`_ymd_to_mmdd_weekday`、`build_new_high_json`、`build_new_high_markdown`、`build_table1_grid`、`build_top20_stock_tables_for_latest_column`、`format_new_high_stock_row_cells`、`request_new_high_plate_json`、`run_new_high_export`、`save_new_high_json`、`save_new_high_markdown`、`toolbar_data_source_suffix`。

### `ai_review.exports.new_high_stock_line_export`

代码对象数：9。

函数/类：`_build_display_dates`、`_build_stock_entry`、`_get_recent_trading_days`、`build_new_high_stock_line_data`、`fetch_topic_stock_data`、`get_top3_topics_stocks`、`save_new_high_stock_line_json`。

### `ai_review.exports.ths_hot_export`

代码对象数：24。

函数/类：`ThsHotExportModel`、`ThsHotStockRow`、`ThsPlateRow`、`_concept_from_tag`、`_d`、`_fetch_plate`、`_fetch_stock`、`_format_hot_rank_chg`、`_http_get_json`、`_is_ok_payload`、`_md_table_plate`、`_md_table_stock`、`build_ths_hot_json`、`export_ths_hot_to_file`、`format_ths_hot_markdown`、`parse_plate_item`、`parse_plate_list`、`parse_stock_item`、`parse_stock_list`、`run_ths_hot_export`、`save_ths_hot_json`、`save_ths_hot_markdown`。

### `ai_review.exports.topic_cycle_export`

代码对象数：36。

函数/类：`MatrixSnapshot`、`Stock`、`Topic`、`TopicCycleExportModel`、`__post_init__`、`_extract_plate_ids`、`_extract_plate_names`、`_fetch`、`_format_amount`、`_format_ltsz`、`_format_percent`、`_format_price`、`_get_weekday_name`、`_is_bullish`、`_md_escape_cell`、`_parse_height_from_high_days`、`_parse_stock_list_from_stocks_json`、`_parse_topic_list_from_plates_json`、`_source_key_to_label`、`aggregate_topics`、`build_full_topic_cycle_markdown`、`build_topic_cycle_json`、`compute_matrix_snapshot`、`fetch_one_day_ai`、`get_count`、`get_trading_days_for_cycle`、`matrix_snapshot_to_markdown_section`、`run_topic_cycle_fetch`、`save_topic_cycle_json`、`save_topic_cycle_markdown`、`sorted_topics_for_table1`、`toolbar_data_source_suffix`、`topic_date_range_display`。

### `ai_review.exports.xgt_topic_export`

代码对象数：52。

函数/类：`XgtTopicExportModel`、`XgtTopicExportOutcome`、`_ExportHotSpot`、`_ExportTopicStock`、`_StockItem`、`_StockParseStats`、`__init__`、`_cache_file_path`、`_cache_root`、`_d`、`_data_date_label`、`_get_json_items`、`_http_get_json`、`_json_load_source_label`、`_limit_time_col`、`_parse_xgt_topic_row`、`_parse_xgt_topic_stocks`、`_plain_open_count`、`_sanitize_field`、`_set_code`、`_set_first_limit_time`、`_set_high_days3`、`_set_hs_rate`、`_set_name`、`_set_percent_topic`、`_set_topic_amount`、`_set_topic_id_list`、`_set_topic_ltsz`、`_should_write_cache`、`_strip_cell_display`、`_surge_items_is_list`、`_swap`、`_truncate_json`、`_weekday_cn`、`_zt_time_plain`、`build_topic_home_lines`、`build_urls_and_request_date`、`build_xgt_topic_json`、`clear_request_cache`、`default_export_dir`、`default_export_timestamp`、`export_dir_for_ymd`、`export_xgt_topic_to_file`、`format_topic_home_markdown`、`lines_to_table_layout`、`make_topic`、`parse_hot_spots_from_topic_json`、`request_json_with_cache`、`run_xgt_topic_export`、`save_xgt_topic_json`、`save_xgt_topic_markdown`。

### `ai_review.exports.zt_analysis_export`

代码对象数：17。

函数/类：`ZtAnalysisExportModel`、`ZtStock`、`ZtTab`、`_cache_path`、`_http_get`、`_is_usable_payload`、`_parse_payload`、`_strip_disclaimer`、`_today_yyyymmdd`、`build_sidebar_items`、`build_zt_analysis_json`、`render_zt_analysis_html`、`resolve_zt_analysis_target_date`、`run_zt_analysis_export`、`save_zt_analysis_json`、`toolbar_data_source_suffix`。

### `ai_review.exports.zt_analysis_jygs_export`

代码对象数：5。

函数/类：`_snapshot_to_tabs`、`_ymd_to_dash`、`run_zt_analysis_jygs_export`、`save_zt_analysis_jygs_json`。

### `ai_review.lib`

代码对象数：1。

函数/类：无命名函数。

### `ai_review.lib.ai_review_client`

代码对象数：6。

函数/类：`AiReviewNoReportError`、`_base_url`、`fetch_review_html`、`fetch_short_code`、`short_url_for`。

### `ai_review.lib.cache_flow`

代码对象数：7。

函数/类：`CacheFlowDecision`、`SessionCacheParams`、`delay_close_cache_params`、`delay_intraday_cache_params`、`general_business_cache_params`、`resolve_flow`。

### `ai_review.lib.calendar_cache_paths`

代码对象数：3。

函数/类：`candidate_read_calendar_dirs`、`primary_write_calendar_dir`。

### `ai_review.lib.echelon_flow`

代码对象数：8。

函数/类：`EchelonFlowState`、`PoolDataType`、`__init__`、`clear`、`get_model_list`、`make_stock_info`、`sort_percent`。

### `ai_review.lib.echelon_line`

代码对象数：16。

函数/类：`Line`、`__init__`、`_stock_line_plain`、`_stock_row`、`add_level_title`、`add_num`、`add_stock`、`copy_hot_name_info`、`get_hot_name`、`make_limit_strings_and_model`、`make_line`、`make_sub_level_list`、`merge_list`、`sort_by_percent`、`sort_high_days`。

### `ai_review.lib.echelon_model`

代码对象数：5。

函数/类：`EchelonDayEchelonModel`、`EchelonLevelBlock`、`EchelonRateSummary`、`EchelonStockRow`。

### `ai_review.lib.echelon_stock`

代码对象数：30。

函数/类：`EchelonStock`、`EchelonTopicStock`、`KeyType`、`Plate`、`StockType`、`__init__`、`parse_xgt_stream_data`、`set_code`、`set_first_break_time`、`set_first_limit_time`、`set_high_days`、`set_hot_name`、`set_hs_rate`、`set_last_break_time`、`set_last_limit_time`、`set_lb_count`、`set_ltsz`、`set_name`、`set_open_count`、`set_percent`、`set_price`、`set_topic_amount`、`set_topic_hs_rate`、`set_topic_ltsz`、`set_y_down_days`、`set_y_lb_count`、`set_zt_time`。

### `ai_review.lib.server_auth`

代码对象数：4。

函数/类：`api_key_secret`、`auth_headers`、`server_base_url`。

### `ai_review.lib.trading_calendar`

代码对象数：11。

函数/类：`_fetch_holidays_via_api`、`_save_holidays_to_disk`、`_should_fetch_year`、`_try_load_holidays_from_disk`、`default_export_timestamp_int`、`ensure_holidays_for_year`、`get_previous_trading_day`、`get_trading_date_yyyymmdd`、`is_trading_day`、`request_timestamp_unix`。

### `ai_review.vc`

代码对象数：1。

函数/类：无命名函数。

### `ai_review.vc.tab_ai_export_vc`

代码对象数：163。

函数/类：`EchelonCycleFetchWorker`、`FuncWorker`、`InvestmentCalendarFetchWorker`、`MainLineCycleFetchWorker`、`MarketCycleFetchWorker`、`NewHighFetchWorker`、`TabAIExportVC`、`TopicCycleFetchWorker`、`__init__`、`_apply_one_click_models`、`_bind_export_dir_toolbar`、`_bootstrap_first_tab`、`_data_source_suffix`、`_drop_worker`、`_ensure_timestamp`、`_export_all_for_anchor`、`_fetch_all_for_anchor`、`_fill_dc_table`、`_fill_dc_tables`、`_fill_ec_table`、`_fill_hm_tables`、`_fill_mc_table`、`_fill_ml_table`、`_fill_nh_table1`、`_fill_nh_table2`、`_fill_plate_table`、`_fill_stock_table`、`_fill_tc_table1`、`_fill_ths_tables`、`_fill_xgt_table`、`_finish_one_click`、`_keep_worker`、`_launch_demo`、`_on_choose_export_dir`、`_on_dc_jygs_done`、`_on_dc_period_done`、`_on_echelon_fetch_finished`、`_on_export_date_changed`、`_on_investment_calendar_fetch_finished`、`_on_main_line_fetch_finished`、`_on_market_cycle_fetch_finished`、`_on_new_high_fetch_finished`、`_on_nh_table1_cell_clicked`、`_on_topic_cycle_fetch_finished`、`_on_zt2_side_item_clicked`、`_on_zt_side_item_clicked`、`_refresh_export_dir_label`、`_render_zt2_view`、`_render_zt_view`、`_save`、`_selected_anchor_ymd`、`_set_plate_row`、`_show_tc_matrix_for_topic`、`_strip_cache_hint`、`_trading_day_label`、`_try`、`_update_dc_progress`、`_wire`、`_xgt_data_source_toolbar_suffix`、`done`、`exported`、`fetched`、`get_count`、`get_tab_widget`、`job`、`on_clear_cache`、`on_export_dragon_cycle_json`、`on_export_echelon_markdown`、`on_export_hot_money_markdown`、`on_export_investment_calendar_markdown`、`on_export_main_line_markdown`、`on_export_market_cycle_markdown`、`on_export_new_high_markdown`、`on_export_new_high_stock_line`、`on_export_ths_markdown`、`on_export_topic_cycle_markdown`、`on_export_xgt_markdown`、`on_export_zt_analysis_json`、`on_export_zt_analysis_jygs_json`、`on_one_click_export`、`on_refresh_dragon_cycle`、`on_refresh_echelon_cycle`、`on_refresh_hot_money`、`on_refresh_investment_calendar`、`on_refresh_main_line_cycle`、`on_refresh_market_cycle`、`on_refresh_new_high`、`on_refresh_ths`、`on_refresh_topic_cycle`、`on_refresh_xgt`、`on_refresh_zt_analysis`、`on_refresh_zt_analysis_jygs`、`on_tab_shown`、`on_tc_table1_clicked`、`part`、`run`。

### `ai_review.vc.tab_ai_export_view`

代码对象数：56。

函数/类：`TabAIExportView`、`__init__`、`_apply_ai_export_table_bg`、`_build_dragon_cycle_page`、`_build_echelon_page`、`_build_hot_money_page`、`_build_investment_calendar_page`、`_build_main_line_page`、`_build_market_cycle_page`、`_build_new_high_page`、`_build_ths_page`、`_build_toolbar_dragon_cycle`、`_build_toolbar_echelon`、`_build_toolbar_fixed`、`_build_toolbar_hot_money`、`_build_toolbar_investment_calendar`、`_build_toolbar_main_line`、`_build_toolbar_market_cycle`、`_build_toolbar_new_high`、`_build_toolbar_topic_cycle`、`_build_toolbar_zt_analysis`、`_build_toolbar_zt_analysis_jygs`、`_build_topic_cycle_page`、`_build_ui`、`_build_xgt_page`、`_build_zt_analysis_jygs_page`、`_build_zt_analysis_page`、`_make_status_label`、`_status_font`、`_toolbar_time_text`、`_wrap_table`、`set_dc_refresh_time_now`、`set_dc_status`、`set_ec_refresh_time_now`、`set_ec_status`、`set_hm_refresh_time_now`、`set_hm_status`、`set_ic_refresh_time_now`、`set_ic_status`、`set_mc_refresh_time_now`、`set_mc_status`、`set_ml_refresh_time_now`、`set_ml_status`、`set_nh_refresh_time_now`、`set_nh_status`、`set_tc_refresh_time_now`、`set_tc_status`、`set_ths_refresh_time_now`、`set_ths_status`、`set_xgt_refresh_time_now`、`set_xgt_status`、`set_zt2_refresh_time_now`、`set_zt2_status`、`set_zt_refresh_time_now`、`set_zt_status`。

### `ai_review.vc.tab_ai_review_html_vc`

代码对象数：11。

函数/类：`AiReviewHtmlWidget`、`__init__`、`_build_ui`、`_patch_svg_to_png`、`_restore_attr_spaces`、`clear`、`fix_tag`、`load_file`、`load_html`、`replace_svg`。

### `ai_review.vc.tab_ai_review_vc`

代码对象数：26。

函数/类：`TabAIReviewVC`、`_FetchWorker`、`__init__`、`_bind_events`、`_build_ui`、`_cleanup`、`_current_selected_date`、`_fmt_dash`、`_fmt_underscore`、`_handle_fetch_failure`、`_now_hhmmss_full_width`、`_on_calendar_date_changed`、`_on_export_clicked`、`_on_fetch_done`、`_on_import_local_clicked`、`_on_open_browser_clicked`、`_on_refresh_clicked`、`_on_table_selection_changed`、`_rebuild_table1`、`_sorted_dates_desc`、`_start_fetch`、`run`、`stop_all_workers`。

### `ai_review.vc.topic_cycle_matrix_qt`

代码对象数：3。

函数/类：`create_topic_cycle_matrix_table`、`fill_matrix_table_from_snapshot`。

### `api`

代码对象数：1。

函数/类：无命名函数。

### `api.api_watch`

代码对象数：4。

函数/类：`_sanitize_paths`、`report_api_business_error`、`report_api_system_error`。

### `api.base_request`

代码对象数：10。

函数/类：`BaseRequest`、`DataType`、`__init__`、`get`、`get_data`、`get_model_list`、`get_type_data`、`get_url`、`make_stock_info`。

### `api.stock_new_high_api`

代码对象数：17。

函数/类：`StockNewHighApi`、`_get_cache_path`、`_get_device_id`、`_get_prev_trade_day`、`_get_user_id`、`_is_cache_stale`、`_load_cache`、`_request`、`_request_with_cache_logic`、`_request_with_cache_logic_for_trend`、`_save_cache`、`get_day_new_high_trend`、`get_pie_chart_data`、`get_plate_data`、`get_stock_data`。

### `api.stock_percent_api`

代码对象数：14。

函数/类：`_extract_pct`、`_fetch_top_stocks_from_api`、`_fill_names_from_tencent`、`_is_after_close_1530`、`_is_before_open_0915`、`_load_top_gain_cache`、`_to_sohu_code`、`_top_gain_cache_file`、`_ymd`、`fetch_stock_daily_percent`、`fetch_top_stocks_60`、`fetch_top_stocks_no_cache`。

### `api.theme_stock_zf_api`

代码对象数：6。

函数/类：`_strip_prefix`、`debug_fetch`、`get_sina_batch_stock_data`、`get_tencent_batch_stock_data`、`print_stock_data`。

### `api.theme_stock_zf_service`

代码对象数：11。

函数/类：`ZhangfuWorker`、`__init__`、`_fetch_all_concurrent`、`_fetch_batch`、`_is_cache_mode`、`_is_cache_valid`、`_stock_id_to_api_code`、`fetch_zhangfu_async`、`run`。

### `api.ths_hot_list`

代码对象数：14。

函数/类：`HotType`、`THSHotList`、`__init__`、`get_data`、`get_hot_plate_data`、`get_hot_topic_data`、`get_model_list`、`get_popular_stocks_data`、`get_type_data`、`get_url`、`make_stock_info`、`parse_hot_concept_and_plate`、`parse_hot_topic_data`。

### `api.ths_loong_list`

代码对象数：32。

函数/类：`Concept`、`Data`、`HotMoney`、`HotMoneyItem`、`Item`、`Response`、`THSLoongList`、`Tag`、`__init__`、`_get_detail_cache_path`、`_get_hot_money_cache_path`、`_get_simple_cache_path`、`fetch_hot_money_list`、`fetch_list_data`、`get_hot_money_list_data`、`get_loong_detail_list_data`、`get_loong_simple_list_data`、`make_hot_money_info`、`make_list_info`、`make_loong_info`、`parse_concept`、`parse_data`、`parse_hot_money_item`、`parse_item`、`parse_json`、`parse_tag`、`percent`、`set_net_value`、`set_net_value2`、`sort`。

### `api.ths_market_overview`

代码对象数：7。

函数/类：`_get_cookie`、`build_headers`、`build_url`、`fetch_overview`、`get_overview_data`。

### `api.ths_sh_index`

代码对象数：2。

函数/类：`fetch_sh_index_kline`。

### `api.ths_vc_calendar`

代码对象数：56。

函数/类：`CLSVCCalendar`、`DCVCCalendar`、`JiuYanGongShe`、`THSVCCalendar`、`TimelineArticle`、`TimelineDay`、`TimelineInfo`、`TimelineResponse`、`TimelineTheme`、`UserInfo`、`VCEventStore`、`__init__`、`_get_store_path`、`_get_type_data`、`_load`、`_save`、`ensure_initial`、`fetch_data`、`fetch_timeline_data`、`format_date`、`get_data`、`get_data2`、`get_month`、`get_relevant_months`、`get_request`、`make_json_data`、`parse_data`、`parse_timeline_response`、`print_timeline`、`update_and_is_new`。

### `api.xgt_instance`

代码对象数：45。

函数/类：`LatestRowsStore`、`Stock`、`Topic`、`XGTApi`、`XGTDataBridge`、`XGTInstance`、`__init__`、`__new__`、`__post_init__`、`_extract_plate_ids`、`_extract_plate_names`、`_format_amount`、`_format_ltsz`、`_format_percent`、`_format_price`、`_get_bridge_stock_rows_for_today`、`_get_recent_trading_days`、`_get_weekday_name`、`_now_dt`、`_parse_stock_rows_from_json`、`_set_bridge_stock_json`、`_set_bridge_topic_json`、`_set_bridge_update_time`、`_today_str`、`get`、`get_instance`、`get_latest_rows`、`get_stock_data`、`get_stock_list_13_2`、`get_stock_list_13_828`、`get_topic_aggregation`、`get_topic_aggregation7`、`get_topic_aggregation_for_distribution`、`is_brige_data`、`request_topic_and_stock_data`、`request_topic_and_stock_data_all`、`search_latest_rows`、`set`、`set_recent`、`set_today`。

### `api2`

代码对象数：1。

函数/类：无命名函数。

### `api2.core`

代码对象数：1。

函数/类：无命名函数。

### `api2.core.cache`

代码对象数：17。

函数/类：`CacheFlow`、`CacheParams`、`_cache_path`、`_is_future`、`_is_today`、`_is_usable_payload`、`_log`、`_resolve`、`_should_write_cache`、`_surge_items_is_list`、`delay_close_params`、`general_business_params`、`realtime_params`、`request_json_with_cache`。

### `api2.core.errors`

代码对象数：6。

函数/类：`Api2CacheError`、`Api2Error`、`Api2HttpError`、`Api2ParseError`、`report_api_error`。

### `api2.core.http_client`

代码对象数：6。

函数/类：`_build_session`、`close_http_client`、`get_json`、`get_jsonp`、`get_session`。

### `api2.core.result`

代码对象数：5。

函数/类：`ApiResult`、`data_or`、`fail`、`success`。

### `api2.core.thread_pool`

代码对象数：3。

函数/类：`bounded_pool`、`fetch_parallel`。

### `api2.core.trading_day`

代码对象数：14。

函数/类：`_calendar`、`_should_use_previous_trading_day`、`get_data_date`、`get_previous_trading_date`、`get_previous_trading_date2`、`get_reqeust_timestamp`、`get_trading_date`、`get_trading_date2`、`is_over_10_days`、`is_stock_trading_day`、`is_today`、`is_trading_day`、`is_trading_time`。

### `api2.endpoints`

代码对象数：1。

函数/类：无命名函数。

### `api2.endpoints.dc_flow_api`

代码对象数：8。

函数/类：`DcDownInfo`、`_dc_time_from_hhmmss`、`_fmt_fund`、`_parse_down_item`、`_parse_payload`、`_url_limit_down`、`fetch_dc_limit_down`。

### `api2.endpoints.jygs_topic_api`

代码对象数：21。

函数/类：`JygsStockRow`、`JygsTopicApiError`、`JygsTopicFetchThread`、`JygsTopicGroup`、`JygsTopicSnapshot`、`__init__`、`_cache_path`、`_do_post`、`_on_done`、`_print_snapshot`、`_run_in_thread`、`_safe_callback`、`fetch_topic_snapshot`、`from_raw`、`from_response`、`run`、`total_stocks`、`try_load_cached_snapshot`。

### `api2.endpoints.limit_count_api`

代码对象数：3。

函数/类：`_i`、`fetch_limit_counts`。

### `api2.endpoints.ths_flow_api`

代码对象数：20。

函数/类：`ThsFlowBundle`、`_demo`、`_fmt_fund`、`_fmt_pct`、`_fmt_price`、`_fmt_ratio`、`_fmt_yi`、`_parse_down_row`、`_parse_header_rate`、`_parse_limit_up_row`、`_parse_n_boards`、`_parse_rows`、`_rate_cell`、`_time_from_str_stamp`、`_url_limit_down`、`_url_limit_up`、`fetch_ths_limit_down`、`fetch_ths_limit_up`。

### `api2.endpoints.xgt_flow_api`

代码对象数：29。

函数/类：`_PoolSpec`、`_collect_hot_name`、`_demo`、`_derive_high_days`、`_fetch_pool`、`_fill_broken`、`_fill_down`、`_fill_limit_up`、`_fill_nearly_new`、`_fill_new`、`_fill_super`、`_fill_y_limit_up`、`_fmt_pct`、`_fmt_price`、`_fmt_ratio`、`_fmt_yi`、`_parse_item_common`、`_sort_by_pct_desc`、`_sort_by_y_down_desc`、`_time_from_stamp`、`_url_and_target_date`、`fetch_broken`、`fetch_down`、`fetch_limit_up`、`fetch_nearly_new_stock`、`fetch_new_stock`、`fetch_super`、`fetch_y_limit_up`。

### `api2.endpoints.xgt_topic_api`

代码对象数：23。

函数/类：`_Col`、`_demo`、`_derive_high_days`、`_fmt_pct`、`_fmt_price`、`_fmt_ratio`、`_fmt_yi`、`_make_topic_blocks`、`_parse_plates`、`_parse_stock_row`、`_parse_stocks`、`_plate_names_and_ids`、`_plates_url`、`_stocks_url`、`_time_from_stamp`、`fetch_topic_full`。

### `api2.l_color`

代码对象数：7。

函数/类：`Sector`、`color_for_code`、`color_for_name`、`color_for_pct`、`color_for_time`、`sector_of`。

### `api2.models`

代码对象数：1。

函数/类：无命名函数。

### `api2.models.echelon`

代码对象数：9。

函数/类：`EchelonBundle`、`EchelonLevelBlock`、`EchelonRateSummary`、`EchelonRowKind`、`EchelonStockRow`、`empty_fail_bundle`、`empty_limit_bundle`、`empty_rate_summary`。

### `api2.models.flow`

代码对象数：9。

函数/类：`FlowHeaderRate`、`FlowStockRow`、`RateCell`、`StockState`、`empty_flow_header_rate`、`empty_rate_cell`、`rows_today`、`rows_yesterday`。

### `api2.models.stock_row`

代码对象数：3。

函数/类：`StockRow`、`make_sector`。

### `api2.models.topic`

代码对象数：3。

函数/类：`TopicBlock`、`TopicStockRow`。

### `api2.services`

代码对象数：1。

函数/类：无命名函数。

### `api2.services.echelon_builder`

代码对象数：10。

函数/类：`_echelon_row`、`_kind_of`、`_merge_dedup`、`_pack_level`、`_sort_for_line`、`build_echelons`、`flush`、`mk`。

### `api2.services.mood_section_service`

代码对象数：22。

函数/类：`MoodSectionDataset`、`MoodSectionLimit`、`MoodSectionPools`、`_build_limit_line`、`_demo`、`_merge_ths_flow_rows`、`_result_to_rows`、`_run`、`_t`、`_take_rows`、`_task`、`_task_ths_flow`、`_task_xgt_topic`、`fetch_limit_section`、`fetch_mood_section`、`fetch_pools_only`。

### `api_auth`

代码对象数：24。

函数/类：`ApiAuth`、`ApiAuthConfig`、`ApiAuthV2`、`__call__`、`__init__`、`_attach_jwt`、`_body_bytes_for_sign`、`_canonical_query`、`_sha256_hex`、`add_auth_to_headers`、`generate_auth_headers`、`generate_nonce`、`generate_signature`、`generate_timestamp`、`get_api_auth`、`get_api_auth_v2`、`get_auth_headers`、`get_current_jwt`、`set_api_auth_config`、`set_jwt_provider`。

### `config`

代码对象数：8。

函数/类：`AppConfigModel`、`ServerConfigModel`、`VersionCheckConfigModel`、`_platform_os`、`get_app_config`、`get_server_config`、`get_version_check_config`。

### `config_fetcher`

代码对象数：19。

函数/类：`ConfigFetchWorker`、`ConfigFetcher`、`__init__`、`_build_api_url`、`_on_fetch_failed`、`_on_fetch_success`、`_on_worker_finished`、`clear_cache`、`fetch_config_async`、`get_config_fetcher`、`get_config_sync`、`get_instance`、`refresh`、`run`。

### `configparser`

代码对象数：109。

函数/类：`BasicInterpolation`、`ConfigParser`、`ConverterMapping`、`DuplicateOptionError`、`DuplicateSectionError`、`Error`、`ExtendedInterpolation`、`Interpolation`、`InterpolationDepthError`、`InterpolationError`、`InterpolationMissingOptionError`、`InterpolationSyntaxError`、`LegacyInterpolation`、`MissingSectionHeaderError`、`NoOptionError`、`NoSectionError`、`ParsingError`、`RawConfigParser`、`SectionProxy`、`__contains__`、`__delitem__`、`__getitem__`、`__init__`、`__iter__`、`__len__`、`__repr__`、`__setitem__`、`_convert_to_boolean`、`_get`、`_get_conv`、`_handle_error`、`_interpolate_some`、`_interpolation_replace`、`_join_multiline_values`、`_options`、`_read`、`_read_defaults`、`_unify_values`、`_validate_value_types`、`_write_section`、`add_section`、`append`、`before_get`、`before_read`、`before_set`、`before_write`、`converters`、`defaults`、`get`、`getboolean`、`getfloat`、`getint`、`has_option`、`has_section`、`items`、`name`、`options`、`optionxform`、`parser`、`popitem`、`read`、`read_dict`、`read_file`、`read_string`、`remove_option`、`remove_section`、`sections`、`set`、`write`。

### `features`

代码对象数：1。

函数/类：无命名函数。

### `features.longzijue_service`

代码对象数：2。

函数/类：`open_longzijue_in_browser`。

### `hardware_id`

代码对象数：5。

函数/类：`_compute_hardware_id`、`_is_valid_uuid`、`get_hardware_id`。

### `kpl2`

代码对象数：1。

函数/类：无命名函数。

### `kpl2.api`

代码对象数：1。

函数/类：无命名函数。

### `kpl2.api._common`

代码对象数：3。

函数/类：`require_dict`、`unwrap_ajax_result`。

### `kpl2.api.boom_reason_api`

代码对象数：7。

函数/类：`_coerce_json`、`build_summary`、`build_today_summary_text`、`fetch_boom_detail`、`fetch_boom_reason_history`、`fetch_boom_reason_today`。

### `kpl2.api.plate_api`

代码对象数：3。

函数/类：`_parse_plate_list`、`fetch_plate_list`。

### `kpl2.api.stock_list_api`

代码对象数：8。

函数/类：`_f`、`_ff`、`_parse_stock_list`、`_row_from_dict`、`_row_from_list`、`fetch_stock_list`。

### `kpl2.api.sub_plate_api`

代码对象数：4。

函数/类：`_parse_sub_plate`、`fetch_sub_plate`。

### `kpl2.models`

代码对象数：1。

函数/类：无命名函数。

### `kpl2.models.boom_reason`

代码对象数：5。

函数/类：`BoomDetail`、`BoomReasonSummary`、`to_dict`。

### `kpl2.models.plate`

代码对象数：7。

函数/类：`PlateInfo`、`StockInfo`、`SubPlateInfo`、`to_dict`。

### `kpl2.net`

代码对象数：1。

函数/类：无命名函数。

### `kpl2.net.async_worker`

代码对象数：11。

函数/类：`AsyncWorker`、`__init__`、`_dispatch_done`、`_on_future_done`、`_pool_for`、`_run_task`、`latest_token`、`shutdown`、`submit`。

### `kpl2.net.errors`

代码对象数：5。

函数/类：`Kpl2Error`、`Kpl2HttpError`、`Kpl2ParseError`、`report_kpl2_error`。

### `kpl2.net.http_client`

代码对象数：7。

函数/类：`_build_session`、`_decode_json`、`close_http_client`、`get_json`、`get_session`、`post_form`。

### `kpl2.net.result`

代码对象数：5。

函数/类：`ApiResult`、`data_or`、`fail`、`success`。

### `kpl2.service`

代码对象数：1。

函数/类：无命名函数。

### `kpl2.service.boom_cache`

代码对象数：11。

函数/类：`BoomReasonCache`、`__init__`、`_compute_window_start`、`_ensure_window`、`clear`、`get`、`has_history`、`put`、`put_history`、`size`。

### `kpl2.service.plate_service`

代码对象数：23。

函数/类：`PlateService`、`__init__`、`boom_cache`、`load_boom_history`、`load_boom_reason`、`load_boom_today`、`load_plate_list`、`load_stock_list`、`load_sub_plate`、`on_done`、`shutdown`、`stock_cache`、`task`、`worker`。

### `kpl2.service.stock_cache`

代码对象数：11。

函数/类：`StockListCache`、`__init__`、`_b`、`_current_window_id`、`_ensure_window`、`clear`、`get`、`put`、`should_cache`、`size`。

### `kpl2.util`

代码对象数：1。

函数/类：无命名函数。

### `kpl2.util.format`

代码对象数：3。

函数/类：`format_decimal`、`format_to_yi`。

### `kpl2.vc`

代码对象数：1。

函数/类：无命名函数。

### `kpl2.vc.plate_pick_export`

代码对象数：11。

函数/类：`Table2Exporter`、`__init__`、`_collect_codes`、`_iter_visible`、`_parse_change`、`build_default_filename`、`export`。

### `kpl2.vc.plate_pick_search`

代码对象数：9。

函数/类：`Table2Search`、`__init__`、`_set_visible_recursive`、`apply_search_filter`、`attach`、`attach_clear_button`、`on_clear_clicked`。

### `kpl2.vc.plate_pick_sort`

代码对象数：22。

函数/类：`TableSorter`、`__init__`、`_match_first_number`、`_parse_table1`、`_parse_table2`、`_pure_number`、`on_table1_header_clicked`、`on_table2_header_clicked`、`parse_cell_sort_value`、`parse_cn_rank_1_to_99`、`reapply_table1_if_needed`、`reapply_table2_if_needed`、`set_table2_column_ids`、`sort_table1_by_column`、`sort_table2_by_column`、`table2_column_ids`、`update_table1_sort_header`、`update_table2_sort_header`。

### `kpl2.vc.plate_pick_state`

代码对象数：11。

函数/类：`Table1SelectionState`、`__init__`、`find_top_item_by_plate_id`、`reset`、`restore`、`save`、`save_from_current`、`select_plate`、`selected_item_path`、`selected_plate_id`。

### `kpl2.vc.plate_pick_vc`

代码对象数：48。

函数/类：`PlatePickVC`、`__init__`、`_apply_persisted_visual_order`、`_apply_table2_columns_to_view`、`_build_export_default_name`、`_clear_component2_cards`、`_collect_table2_codes_names`、`_current_target_plate_id`、`_get_component2_card_size`、`_is_trading_day`、`_is_trading_time`、`_latest_trading_date_str`、`_make_click`、`_on_boom_reason_label_clicked`、`_on_boom_reason_received`、`_on_calendar_date_changed`、`_on_component2_card_clicked`、`_on_export_clicked`、`_on_plate_data_received`、`_on_refresh_clicked`、`_on_refresh_tick`、`_on_request_failed`、`_on_rps_clicked`、`_on_stock_data_received`、`_on_sub_plate_received`、`_on_table1_item_clicked`、`_on_table2_section_moved`、`_rebuild_component2_cards`、`_render_table2`、`_rps_plate_name`、`_save_component2_scroll`、`_seamless_update_table1`、`_show_boom_history_dialog`、`_sync_component2_inner_geometry`、`_update_component2_selected_visuals`、`_wire_service_signals`、`_wire_view_signals`、`on_cross_select_completed`、`shutdown`、`start_refresh_timer`、`stop_refresh_timer`、`trigger_first_load`、`walk`。

### `kpl2.vc.tab0_kpl2_vc`

代码对象数：6。

函数/类：`Tab0KPL2VC`、`__init__`、`_on_cross_select_clicked`、`_on_main_tab_changed`、`shutdown`。

### `kpl2.view`

代码对象数：1。

函数/类：无命名函数。

### `kpl2.view.dialogs`

代码对象数：1。

函数/类：无命名函数。

### `kpl2.view.dialogs.boom_reason_dialog`

代码对象数：27。

函数/类：`KPL2BoomReasonDialog`、`_TimelineBackLine`、`_TimelineRow`、`__init__`、`_build_date_card`、`_build_msg_frame`、`_build_row`、`_build_stock_box`、`_build_stock_card`、`_default_stock_color`、`_format_date_card`、`_handle_stock_clicked`、`_parse_lz_info`、`_render_days`、`_schedule_back_line_update`、`_setup_ui`、`_update_back_line_geometry_and_repaint`、`paintEvent`、`set_date_card`。

### `kpl2.view.dialogs.stock_selection_dialog`

代码对象数：39。

函数/类：`KPL2StockSelectionDialog`、`_CircleCheck`、`__init__`、`_add_plate_row`、`_build_table3`、`_build_table4`、`_build_toolbar`、`_collect_selected_ids`、`_compute_intersection`、`_default_label_text`、`_extract_checkbox`、`_extract_circle`、`_finalize_selection`、`_name`、`_on_close_clicked`、`_on_export_clicked`、`_on_request_failed`、`_on_select_clicked`、`_on_stock_received`、`_on_table4_item_clicked`、`_populate_table4`、`_release_resources`、`_render_table3`、`_resolve_find_date`、`_setup_ui`、`_signed_color`、`_start_selection`、`_update_selected_label`、`closeEvent`、`enterEvent`、`isChecked`、`leaveEvent`、`mousePressEvent`、`paintEvent`、`setChecked`、`toggle`。

### `kpl2.view.plate_pick_view`

代码对象数：15。

函数/类：`PlatePickView`、`__init__`、`_apply_sizes`、`_build_data_splitter`、`_build_frame1`、`_build_table1`、`_build_table1_container`、`_build_table2`、`_build_table2_container`、`_build_toolbar`、`_make_hline`、`_setup_ui`、`get_widget`。

### `kpl2.view.tab0_kpl2_view`

代码对象数：5。

函数/类：`Tab0KPL2View`、`__init__`、`_setup_ui`、`get_widget`。

### `kpl2.view.table2_columns`

代码对象数：5。

函数/类：`header_labels_for_order`、`load_column_order`、`save_column_order_async`、`validate_column_ids`。

### `kpl2.view.table_render`

代码对象数：13。

函数/类：`_fmt_int_or_dash`、`_fmt_pct`、`_fmt_yi_or_dash`、`_liangbi_color`、`_signed_color`、`_stock_code_color`、`_style_cell`、`apply_table2_row`、`build_table1_item`、`build_table2_display`、`stock_code_color`、`strength_color_for_concept`。

### `kpl2.view.widgets`

代码对象数：1。

函数/类：无命名函数。

### `kpl2.view.widgets.concept_strip`

代码对象数：5。

函数/类：`ConceptStripItem`、`__init__`、`mousePressEvent`、`set_selected`。

### `kpl2.view.widgets.hide_tab_bar`

代码对象数：9。

函数/类：`HideLabelTabBar`、`__init__`、`_all_hidden`、`hide_index`、`minimumSizeHint`、`sizeHint`、`tabSizeHint`。

### `kpl2.view.widgets.reason_label`

代码对象数：3。

函数/类：`ClickableWrapLabel`、`mousePressEvent`。

### `monitor`

代码对象数：1。

函数/类：无命名函数。

### `monitor.app_watch_decorators`

代码对象数：22。

函数/类：`PerformanceMonitor`、`SystemErrorHandler`、`__enter__`、`__exit__`、`__init__`、`_get_function_name`、`_get_user_action_from_context`、`catch_system_error`、`decorator`、`monitor`、`monitor_performance`、`performance_monitor`、`report_business_error`、`system_error_handler`、`wrapper`。

### `monitor.app_watch_error_code`

代码对象数：6。

函数/类：`AppWatchErrorCode`、`__init__`、`code`、`message`、`resolve_message`。

### `monitor.app_watch_reporter`

代码对象数：20。

函数/类：`AppWatchReporter`、`__init__`、`_base_payload`、`_cache_record`、`_clean_payload`、`_enqueue`、`_flush_and_clear_cache`、`_get_watch_cache_dir`、`_is_dedup`、`_is_trading_time`、`_post_with_retry`、`_to_string`、`_worker_loop`、`get_app_watch_reporter`、`instance`、`record_business_error`、`record_performance_issue`、`record_security_event`、`record_system_error`。

### `monitor.crash`

代码对象数：1。

函数/类：无命名函数。

### `monitor.crash.c_signals`

代码对象数：4。

函数/类：`_thread_excepthook`、`get_crash_log_dir`、`install_c_signals`。

### `monitor.crash.crash_reporter`

代码对象数：24。

函数/类：`_check_daily_limit`、`_compute_crash_signature`、`_detect_crash_type`、`_do_check_and_report`、`_extract_crash_prev`、`_extract_recent_prev`、`_generate_device_id`、`_get_app_name`、`_get_device_info`、`_get_version`、`_has_real_crash_signature`、`_increment_daily_count`、`_is_interrupt_only_exit`、`_list_historical_sessions`、`_parse_session_version`、`_parse_timestamp_from_line`、`_read_last_line`、`_remove_session_files`、`_report_one_session`、`_tail_has_normal_mark`、`check_and_report_last_crash`、`write_normal_exit_mark`。

### `monitor.crash.log_cleanup`

代码对象数：3。

函数/类：`_pid_alive`、`cleanup_old_session_logs`。

### `monitor.crash.paths`

代码对象数：2。

函数/类：`resolve_crash_log_dir`。

### `monitor.crash.session_id`

代码对象数：4。

函数/类：`get_session_suffix`、`parse_pid_from_name`、`parse_suffix_from_name`。

### `monitor.crash.session_log`

代码对象数：11。

函数/类：`_SessionLogTail`、`__init__`、`_custom_print`、`append`、`get_session_log_tail`、`install_print_replacement`、`install_session_log_print_tap`、`path`、`record_print_line`。

### `monitor.crash_forensics`

代码对象数：6。

函数/类：`_install_qt_message_handler`、`_install_qthread_hooks`、`handler`、`patched_init`、`setup_crash_forensics`。

### `monitor.qt_safe_emit`

代码对象数：3。

函数/类：`_is_deleted`、`safe_emit`。

### `network_cache_manager`

代码对象数：28。

函数/类：`NetworkCacheManager`、`__init__`、`__new__`、`_get_app_root`、`_get_cache_file_path`、`_get_cache_file_path_by_name`、`_get_previous_trading_day`、`_get_request_type`、`_get_url_hash`、`_sanitize_filename`、`clear_cache`、`download_and_cache_image`、`get_actual_data_date`、`get_image_base64_from_cache`、`get_instance`、`get_target_date`、`is_trading_day`、`is_trading_time`、`load_from_cache`、`load_from_cache_by_name`、`request_with_cache`、`request_with_cache_by_name`、`save_image_to_cache`、`save_to_cache`、`save_to_cache_by_name`、`should_cache_data`、`should_request_network`。

### `network_worker`

代码对象数：8。

函数/类：`DataWorker`、`NetworkWorker`、`__init__`、`fetch_data_sync`、`run`。

### `setting`

代码对象数：6。

函数/类：`get_toolbar_font_family`、`search_input_qfont`、`search_input_qss_font_properties`、`toolbar_qfont`、`toolbar_qss_font_properties`。

### `sky_eye`

代码对象数：1。

函数/类：无命名函数。

### `sky_eye.batch_match`

代码对象数：1。

函数/类：无命名函数。

### `sky_eye.batch_match.matcher`

代码对象数：12。

函数/类：`BatchMatcher`、`MatchResult`、`StockLogicItem`、`_ensure_jygs_ready`、`_ensure_xgt_ready`、`_match_jygs`、`_match_xgt`、`_norm_date`、`_recent_trading_days`、`run`。

### `sky_eye.batch_match.plate_logic_exporter`

代码对象数：3。

函数/类：`_build_json_dict`、`write_plate_logic_report`。

### `sky_eye.batch_match.stock_logic_exporter`

代码对象数：6。

函数/类：`_build_json_dict`、`_build_txt_report`、`_safe_input_label`、`write_report_to_paths`、`write_stock_logic_report`。

### `sky_eye.config`

代码对象数：1。

函数/类：无命名函数。

### `sky_eye.config.runtime_settings`

代码对象数：6。

函数/类：`_load_all`、`load_selected_sources`、`load_topic_detail_mode`、`save_selected_sources`、`save_topic_detail_mode`。

### `sky_eye.config.sources_config`

代码对象数：1。

函数/类：无命名函数。

### `sky_eye.config.views_config`

代码对象数：1。

函数/类：无命名函数。

### `sky_eye.controller`

代码对象数：18。

函数/类：`SkyEyeController`、`__init__`、`_apply_topic_detail_to_sources`、`_build_section`、`_ensure_recent_rows_background`、`_on_disable`、`_on_enable`、`_on_sources_toggle_changed`、`_on_topic_detail_changed`、`_recent_prefetched`、`_render_current`、`_reset_button_checked`、`connect_sources`、`on_stock_code_clicked`、`on_window_closed`、`toggle`。

### `sky_eye.render`

代码对象数：10。

函数/类：`render_concepts`、`render_error`、`render_header`、`render_hint`、`render_jygs`、`render_not_found`、`render_topic_detail`、`render_xgt_recent`。

### `sky_eye.services`

代码对象数：1。

函数/类：无命名函数。

### `sky_eye.services.jygs_service`

代码对象数：22。

函数/类：`JygsTopicService`、`__new__`、`_fetch_one_worker`、`_init_once`、`_list_recent_trading_days`、`_normalize_code`、`_notify_pending_if_any`、`_ymd_to_dash`、`clear_pending`、`is_ready`、`prefetch_async`、`query_by_code`、`query_codes_async`、`query_topic_detail_by_code`、`ready_days`、`set_days`、`set_pending`。

### `sky_eye.sources`

代码对象数：1。

函数/类：无命名函数。

### `sky_eye.sources.aggregator`

代码对象数：5。

函数/类：`build_sources`、`prefetch_all`、`query_all`。

### `sky_eye.sources.base`

代码对象数：9。

函数/类：`SkyEyeDataSource`、`SkyEyeQueryResult`、`empty`、`fetch`、`is_ready`、`normalize_code`、`prefetch_async`。

### `sky_eye.sources.jygs_topic_source`

代码对象数：9。

函数/类：`JygsTopicSource`、`__init__`、`apply_params`、`fetch`、`is_ready`、`prefetch_async`、`set_refresh_callback`、`set_topic_detail_mode`。

### `sky_eye.sources.xgt_recent_source`

代码对象数：13。

函数/类：`XgtRecentSource`、`__init__`、`_worker`、`ensure_ready_async`、`fetch`、`is_ready`、`prefetch_async`、`set_refresh_callback`、`set_topic_detail_mode`。

### `sky_eye.sources.zhiku1_source`

代码对象数：5。

函数/类：`Zhiku1Source`、`fetch`、`is_ready`、`prefetch_async`。

### `sky_eye.top_hint_manager`

代码对象数：7。

函数/类：`SkyEyeTopHintManager`、`__init__`、`_on_dialog_closed`、`_on_dialog_shown`、`eventFilter`、`reset`。

### `sky_eye.window`

代码对象数：23。

函数/类：`SkyEyeWindow`、`__init__`、`_add_section_title`、`_adjust_text_edit_height`、`_attach_search_box`、`_build_search_box`、`_clear_detail_widgets`、`_create_content_card`、`_detach_search_box`、`_do`、`_on_checkbox_toggled`、`_on_code_text_changed`、`_on_topic_detail_cb_toggled`、`closeEvent`、`get_current_html`、`resizeEvent`、`setup_source_toggles`、`setup_topic_detail_toggle`、`showEvent`、`show_detail`、`show_detail_multi`、`show_text`。

### `sky_eye.wiring`

代码对象数：4。

函数/类：`_safe_connect`、`_scan_vc_attrs`、`connect_all`。

### `stock`

代码对象数：78。

函数/类：`HotStock`、`Json2Stock`、`KeyType`、`LHList`、`LoongDepart`、`LoongDetail`、`LoongHuStock`、`Plate`、`Stock`、`StockItem`、`StockType`、`TopicStock`、`Tureye`、`__init__`、`parse_dongcai_data`、`parse_loong_detail_stock`、`parse_looooooong_list_data`、`parse_ths_flow_data`、`parse_ths_hot_list_data`、`parse_ths_topic_data`、`parse_xgt_stream_data`、`parse_xgt_topic_data`、`set_amount`、`set_bug_sell_money`、`set_code`、`set_concept`、`set_depart`、`set_detail`、`set_down_fund`、`set_first_break_time`、`set_first_down_time`、`set_first_limit_time`、`set_fund`、`set_high_days`、`set_high_days2`、`set_high_days3`、`set_high_days_pure`、`set_hot_name`、`set_hot_percent`、`set_hot_rank_chg`、`set_hs_rate`、`set_info`、`set_is_limit_up`、`set_last_break_time`、`set_last_down_time`、`set_last_limit_time`、`set_lb_count`、`set_limit_reason`、`set_ltsz`、`set_money`、`set_name`、`set_net_rate`、`set_net_value`、`set_open_count`、`set_order`、`set_percent`、`set_price`、`set_rate`、`set_surge`、`set_topic_amount`、`set_topic_hs_rate`、`set_topic_id_list`、`set_topic_ltsz`、`set_y_down_days`、`set_y_lb_count`、`set_zt_time`。

### `stock_percent_request`

代码对象数：26。

函数/类：`StockPercentFacade`、`StockPercentRequest`、`__new__`、`_check_cache`、`_fetch`、`_get_cache_path`、`_init`、`_load_cache`、`_request_batch_loong1`、`_save_cache`、`_to_ts_code`、`_ts_code_to_code`、`fetch_realtime_zhangfu_async`、`get_daily_pct_batch`、`get_stock_percent_data`、`get_stock_percent_data_async`、`get_stock_percent_data_batch`、`get_stock_percent_facade`、`get_stock_percent_request`、`should_fetch_realtime`。

### `tab`

代码对象数：1。

函数/类：无命名函数。

### `tab.concept_update_manager`

代码对象数：10。

函数/类：`ConceptUpdateManager`、`__init__`、`__new__`、`_load_update_times`、`_save_update_times`、`get_concept_update_manager`、`get_update_time`、`record_update_time`、`should_update_concept`。

### `tab.echelon_cell_style`

代码对象数：5。

函数/类：`code_color_css`、`code_color_qcolor`、`pct_color`、`title_color`。

### `tab.echelon_view5`

代码对象数：70。

函数/类：`ConceptCard`、`StockCard`、`View5Echelon`、`_CardPool`、`_LevelSection`、`__init__`、`_apply_border`、`_apply_btn_border`、`_apply_highlight_for_concepts`、`_build_concept_area`、`_build_divider`、`_build_stock_area`、`_build_toolbar`、`_compute_cols`、`_current_levels`、`_filter_level`、`_filter_level_break_drop`、`_filter_level_limit_only`、`_find_concepts_for_code`、`_fmt_summary`、`_format_pct`、`_iter_active_stock_cards`、`_layout_grid`、`_make_card`、`_on_concept_clicked`、`_on_stock_clicked`、`_refresh`、`_render_concepts`、`_render_mixed_mode`、`_render_parallel_mode`、`_render_stock_levels`、`_save_btn_state`、`_toggle`、`_toggle_mode`、`_update_stock_area_mode`、`_update_title_style`、`acquire`、`active_cards`、`all`、`bind`、`concept`、`concepts`、`mousePressEvent`、`populate`、`relayout`、`release_after`、`resizeEvent`、`set_highlighted`、`set_selected`、`set_title`、`set_title_style`、`stock_code`。

### `tab.mpl_shared`

代码对象数：3。

函数/类：`_init_matplotlib`。

### `tab.tab_11_0_vc`

代码对象数：5。

函数/类：`Tab11_0_VC`、`__init__`、`_bg`、`_on_tab_current_changed`。

### `tab.tab_11_model`

代码对象数：40。

函数/类：`ConceptLibraryModel`、`StockInfoFetcher`、`StockQuoteAPI`、`__init__`、`_build_request_data`、`_convert_detail_data`、`_format_stock_code`、`_get_theme_list_cache_path`、`clean_html_text`、`clear_cache`、`convert_percentage`、`convert_to_float`、`fetch_stock_info`、`format_timestamp`、`get_app_data_path`、`get_batch_stock_quotes`、`get_data_zip_path`、`get_data_zip_path_info`、`get_legacy_app_data_path`、`get_stock_info`、`get_stock_info_async`、`get_stock_quote`、`is_trading_time`、`load_concept_data`、`load_concept_details`、`parse_stock_data`、`sort_left_table`、`sort_right_table`。

### `tab.tab_11_select_stock_vc`

代码对象数：29。

函数/类：`CrossConceptSelectController`、`CrossConceptSelectDialog`、`__init__`、`_bind_events`、`_display_stocks_in_table2`、`_ensure_stock_lists_then_cross_select`、`_get_common_stocks`、`_get_stock_info`、`_get_stocks_for_concept`、`_init_ui`、`_load_concept_data`、`_on_clear_search`、`_on_search_text_changed`、`_on_select_stocks`、`_on_stock_lists_loaded_then_select`、`_on_table_cell_clicked`、`_perform_cross_concept_selection`、`_toggle_concept_selection`、`_update_select_label`、`_update_table`、`get_selected_concept_ids`、`load_then_select`、`show_cross_select_dialog`、`update_concept_data`。

### `tab.tab_11_vc`

代码对象数：78。

函数/类：`ConceptDetailsWorker`、`ConceptListWorker`、`HotOverlayDelegate`、`Tab11VC`、`__init__`、`_add_stocks`、`_bind_events`、`_display_tianyan_result_in_info_label_direct`、`_ensure_tianyan_data_loaded`、`_execute_debounced_stock_search`、`_fetch_zhangfu_for_stocks`、`_generate_concept_table_item`、`_get_all_stocks_from_cache`、`_load_concept_details_forced`、`_load_concept_details_forced_vip`、`_norm_code`、`_normalize_code`、`_on_concept_details_error`、`_on_concept_details_finished`、`_on_concept_details_ready`、`_on_concept_list_error`、`_on_concept_list_finished`、`_on_concept_list_ready`、`_on_search_full_library_changed`、`_on_tab_changed`、`_on_zhangfu_done`、`_perform_search`、`_populate_right_table`、`_query_tianyan_data`、`_refresh_current_concept_data`、`_refresh_table2_display`、`_send_to_trader`、`_show_error_in_info_label`、`_show_initial_hint`、`_show_no_tianyan_data_message`、`_show_tianyan_not_available_message`、`_show_tianyan_not_enabled_message`、`_test_network_connection`、`clear_cache_and_refresh`、`export_right_table_codes`、`get_app_data_path`、`load_concept_data`、`on_clear_stock_search`、`on_cross_concept_select`、`on_expand_all_clicked`、`on_left_header_clicked`、`on_left_refresh_clicked`、`on_left_table_cell_clicked`、`on_line_chart_clicked`、`on_main_branch_sub_branches_toggle`、`on_main_branch_toggle`、`on_right_header_clicked`、`on_right_search_btn_clicked`、`on_right_search_cleared`、`on_right_search_key_release`、`on_right_search_text_changed`、`on_search_key_release`、`on_stock_code_search`、`on_stock_code_text_changed`、`on_stock_row_selected`、`on_sub_branch_toggle`、`paint`、`populate_concept_table`、`run`、`sort_main_branches`。

### `tab.tab_11_view`

代码对象数：14。

函数/类：`ClickableHeaderLabel`、`Tab11View`、`__init__`、`clear_table1`、`clear_table2`、`get_widget`、`mousePressEvent`、`set_concept_title`、`set_status_text`、`setup_ui`、`update_right_sort_indicator`、`update_sort_indicator`。

### `tab.tab_12_2_vc`

代码对象数：34。

函数/类：`Tab12_2_VC`、`_TimelineBackLine`、`_TimelineRow`、`__init__`、`_fallback_to_cache`、`_fetch_jygs_data`、`_months_to_render_for_now`、`_on_data_ready`、`_on_error`、`_on_search_clear_clicked`、`_on_search_text_changed`、`_on_sub_tab_current_changed`、`_on_worker_finished`、`_render_months`、`_schedule_back_line_update`、`_setup_ui`、`_toggle_detail_mode`、`_toggle_new_flag_mode`、`_toggle_show_month_mode`、`_update_back_line_geometry_and_repaint`、`_update_refresh_time_label`、`eventFilter`、`merge_response`、`on_tab_activated`、`paintEvent`、`refresh`、`set_date_card`。

### `tab.tab_12_data_fetcher`

代码对象数：16。

函数/类：`TAB12DataFetcher`、`__init__`、`_convert_to_model`、`_fetch_from_ths_topic_new_url`、`_fetch_from_ths_topic_old_url`、`_fetch_from_url`、`_fetch_single_date`、`_get_cache_file_path`、`_get_cached_data`、`_is_valid_data`、`_should_cache`、`_should_fetch_today`、`get_app_data_path`、`get_stock_data`、`get_stock_data_cache_only`。

### `tab.tab_12_vc`

代码对象数：58。

函数/类：`Tab12VC`、`__init__`、`_cleanup_month_cache`、`_on_month_data_error`、`_on_month_data_loaded`、`_on_month_data_ready_async`、`_on_stock_data_error`、`_on_stock_data_ready`、`_op_fetch_months`、`_op_fetch_stock`、`_show_selected_stock_detail`、`_worker`、`enter_to_app`、`filter_stock_data`、`format_date_range`、`generate_event_key`、`get_code_priority`、`get_new_events_count_for_concept`、`get_target_months`、`get_trading_date_before`、`get_trading_dates_between`、`init_data_in_background`、`is_event`、`load_concept_event_data`、`load_initial_30_days_data`、`load_pinned_concepts`、`load_stored_events`、`load_target_month_data`、`normalize_event_text`、`on_concept_pin_clicked`、`on_concept_table_select`、`on_date_selected`、`on_event_table_select`、`on_stock_date_selected`、`on_stock_table_select`、`on_tab_activated`、`process_data_to_model`、`rebuild_concept_code_map`、`refresh`、`reset_date`、`reset_stock_date`、`save_events_to_json`、`save_pinned_concepts`、`setup_events`、`setup_ui`、`update_concept_table`、`update_event_table`。

### `tab.tab_12_view`

代码对象数：26。

函数/类：`ConceptView`、`__init__`、`create_concept_table`、`create_date_picker`、`create_detail_text`、`create_event_table`、`create_main_widgets`、`create_stock_table`、`get_selected_concept`、`get_selected_date`、`get_selected_stock_date`、`on_concept_cell_clicked`、`on_concept_selection_changed`、`on_date_changed`、`on_event_selection_changed`、`on_reset_date_clicked`、`on_stock_date_changed`、`on_stock_reset_date_clicked`、`on_stock_selection_changed`、`reset_date_to_today`、`reset_stock_date_to_today`、`update_concept_table`、`update_detail_text`、`update_event_table`、`update_stock_table`。

### `tab.tab_14_vc`

代码对象数：6。

函数/类：`Tab14VC`、`__init__`、`_maybe_auto_activate_theme_if_current`、`_on_sub_tab_changed`、`_on_tab_current_changed`。

### `tab.tab_15_market_cycle_table_dialog`

代码对象数：18。

函数/类：`Tab15MarketCycleTableDialog`、`__init__`、`_after_layout`、`_apply_default_dialog_height`、`_apply_table_style`、`_build_sh_index_daily_pct_map`、`_calc_broken_ratio_pct`、`_dispose`、`_fill_table_widget`、`_lookup_sh_close`、`_merge_row_for_table`、`_on_close_clicked`、`_sync_dialog_width_to_table`、`_turnover_foreground`、`closeEvent`、`showEvent`、`show_market_cycle_table_dialog`。

### `tab.tab_15_vc2`

代码对象数：50。

函数/类：`Tab15VC2`、`__init__`、`_cleanup_legacy_caches`、`_debug`、`_fetch_data_worker`、`_fetch_emotion_one_date`、`_fetch_one_date`、`_global_max_min_indices`、`_load_initial`、`_load_market_cycle_prefs`、`_load_or_request`、`_local_extrema_indices_numeric`、`_on_data_ready`、`_on_error`、`_on_progress_updated`、`_on_tab_current_changed`、`_override_limit_counts`、`_parse_overview_data`、`_parse_turnover`、`_restore_buttons`、`_revalidate_zero_count_days`、`_save_market_cycle_prefs`、`_select_long_range_labels_outward_in`、`_should_cache`、`_should_request_today`、`_show_data_repair_dialog`、`_show_desc_dialog`、`_show_market_cycle_table_dialog`、`_toggle_chart_line_panel`、`_toggle_emotion_panel`、`_update_chart`、`get_trading_days`、`on_days_clicked`、`on_refresh_clicked`、`toggle_chart_line`、`toggle_emotion_line`。

### `tab.tab_15_view`

代码对象数：16。

函数/类：`PlaceholderBorderDelegate`、`Tab15View`、`__init__`、`_on_chart1_leave`、`_on_chart1_mouse_move`、`_toggle_chart1_line`、`create_chart1`、`create_control_area`、`create_table_and_chart_area`、`create_table_area`、`get_widget`、`paint`、`setup_ui`。

### `tab.tab_15_view2`

代码对象数：21。

函数/类：`Tab15View2`、`__init__`、`_build_info_html`、`_draw_emotion_info_panel`、`_draw_info_panel`、`_event_to_axes_coords`、`_is_in_emotion_info_zone`、`_is_in_info_zone`、`_on_chart_button_press`、`_on_chart_button_release`、`_on_chart_leave`、`_on_chart_mouse_move`、`create_chart`、`create_toolbar`、`draw_emotion_toggle_legend`、`draw_line_toggle_legend`、`get_widget`、`rebuild_axes`、`setup_ui`。

### `tab.tab_16_1_vc`

代码对象数：26。

函数/类：`Tab16_1_VC`、`_LoongDetailFetchWorker`、`__init__`、`_adjust_table2_column_widths`、`_extract_number`、`_on_data_error`、`_on_data_ready`、`_on_worker_finished`、`_parse_and_display_data`、`_parse_and_display_detail_data`、`_set_cell`、`_set_detail_cell`、`_set_label_height`、`_set_toolbar_enabled`、`_start_fetch`、`on_data_repair_clicked`、`on_date_selected`、`on_refresh_clicked`、`on_table1_clicked`、`on_table2_clicked`、`on_table2_selection_changed`、`refresh_data`、`refresh_data_with_data`、`run`。

### `tab.tab_16_1_view`

代码对象数：10。

函数/类：`HtmlItemDelegate`、`Tab16_1_View`、`__init__`、`_build_toolbar`、`get_widget`、`paint`、`setup_ui`、`sizeHint`。

### `tab.tab_16_2_vc`

代码对象数：24。

函数/类：`Tab16_2_VC`、`_HotMoneyFetchWorker`、`__init__`、`_on_data_error`、`_on_data_ready`、`_on_worker_finished`、`_parse_and_display_data`、`_parse_and_display_table2_data`、`_parse_hot_money_row`、`_parse_stock_row`、`_set_cell`、`_set_table2_cell`、`_set_toolbar_enabled`、`_start_fetch`、`on_data_repair_clicked`、`on_date_selected`、`on_refresh_clicked`、`on_table1_clicked`、`on_table2_clicked`、`refresh_data`、`refresh_data_with_data`、`run`。

### `tab.tab_16_2_view`

代码对象数：7。

函数/类：`Tab16_2_View`、`__init__`、`_build_toolbar`、`get_widget`、`setup_ui`。

### `tab.tab_16_vc`

代码对象数：3。

函数/类：`Tab16VC`、`__init__`。

### `tab.tab_16_view`

代码对象数：5。

函数/类：`Tab16View`、`__init__`、`get_widget`、`setup_ui`。

### `tab.tab_18_2_vc`

代码对象数：34。

函数/类：`Tab18_2_VC`、`_ExportDialog`、`_PanoramaTable`、`_Worker`、`__init__`、`_apply_table_bg`、`_build_content_text`、`_build_ui`、`_fill_table`、`_get_stock_color`、`_keep_worker`、`_make_checkbox`、`_on_export_txt`、`_on_jygs_done`、`_on_period_done`、`_on_save`、`_on_tab_current_changed`、`_postprocess_row`、`_reap_workers`、`_set_time_text`、`_start_refresh`、`_trigger_sky_eye`、`_update_progress`、`_wrap_table`、`run`、`selected_contents`、`selected_periods`。

### `tab.tab_18_vc`

代码对象数：69。

函数/类：`Tab18VC`、`_Tab18HotNameThread`、`_Tab18RefreshThread`、`__init__`、`_apply_block_highlight`、`_apply_highlight_button_styles`、`_apply_toggle_style`、`_compound_pct_window`、`_compute_n_days`、`_get_trader`、`_highlight_block`、`_hq_to_series`、`_init_data`、`_is_vip`、`_is_vip_cached`、`_mm_dd`、`_on_confirm_clicked`、`_on_days_clicked`、`_on_days_seg`、`_on_export_clicked`、`_on_hot_clicked`、`_on_hot_name_built`、`_on_leave`、`_on_linkage_clicked`、`_on_mode_seg`、`_on_mouse_click`、`_on_mouse_move`、`_on_pick`、`_on_pin_clicked`、`_on_refresh_finished`、`_on_refresh_progress`、`_on_search_text_changed`、`_on_tab_current_changed`、`_plot`、`_resolve_highlight_set`、`_rotate_next_block`、`_row_trans`、`_seg_y_from`、`_set_mode`、`_show_vip_prompt`、`_start_hot_name_build`、`_start_refresh`、`_start_threshold_pct`、`_trigger_linkage`、`_trigger_sky_eye`、`_update_info_from_x`、`on_progress`、`run`。

### `tab.tab_1_home_vc`

代码对象数：39。

函数/类：`Tab1HomeVC`、`__init__`、`_apply_big_yang_btn_style`、`_distribute_data_to_tabs`、`_ensure_market_status_timer_started`、`_get_next_trading_day_925_datetime`、`_get_next_wait_target_datetime`、`_on_auto_refresh_timeout`、`_report_fetch_error`、`_start_auto_refresh_timer`、`_start_data_worker`、`_stop_auto_refresh_timer`、`_update_auto_refresh_button`、`_update_auto_refresh_countdown_to_925`、`_update_refresh_time`、`apply_toolbar_styles`、`check_market_status`、`create_toolbar`、`get_timestamp`、`hide_loading_mask`、`load_data`、`load_data_async`、`on_auto_refresh_clicked`、`on_big_yang_clicked`、`on_data_loaded`、`on_data_worker_error`、`on_data_worker_finished`、`on_date_changed`、`on_export_clicked`、`on_help_clicked`、`on_refresh_clicked`、`on_tab_shown`、`on_worker_finished_cleanup`、`refresh`、`setup_ui`、`show_loading_mask`、`update_loading_mask_position`。

### `tab.tab_1_vc`

代码对象数：56。

函数/类：`RoundedCellDelegate`、`Tab1VC`、`__init__`、`_apply_table4_sort_if_needed`、`_fill_table4_row`、`_filter_block_stocks`、`_format_topic_title`、`_fund_or_pct`、`_highest_board_text`、`_make_item`、`_merge_ths_limit_up`、`_on_table4_header_clicked`、`_on_table_selection_changed`、`_reset_table`、`_send_stock_to_trader`、`_set_table_highlighted`、`_sort_table4_by_column`、`_table3_row_color`、`_table4_sort_key`、`_update_table4_sort_header`、`apply_global_header_style`、`apply_table4_selection_style`、`cleanup_all_workers`、`get_font_family`、`is_title_row`、`is_title_row_fast`、`is_title_row_optimized`、`is_trading_day`、`is_trading_time`、`kind_of`、`move_matching_row_to_top`、`on_export_clicked`、`on_stock_code_clicked`、`on_table3_cell_clicked`、`on_table3_cell_clicked_handler`、`paint`、`populate_table3_hot_spots`、`populate_table4_topic_home`、`populate_table7_flow`、`populate_table8_header`、`populate_view5`、`prefix_match`、`refresh`、`set_show_big_yang`、`should_auto_refresh`、`start_refresh_timer`。

### `tab.tab_1_view`

代码对象数：15。

函数/类：`BoldOnlyColumnDelegate`、`Tab1View`、`__init__`、`configure_table_global_settings`、`create_frame1`、`create_frame2`、`create_frame3`、`create_frame4`、`get_widget`、`initStyleOption`、`paint`、`setup_ui`。

### `tab.tab_20_vc`

代码对象数：42。

函数/类：`StockNewHighWorker`、`Tab20VC`、`TrendDataWorker`、`__init__`、`_collect_recent5_codes_for_concept`、`_collect_table2_code_to_name`、`_collect_table2_codes`、`_fill_table3_single_day`、`_on_mode_toggled`、`_show_stock_percent_chart`、`_start_trend_worker`、`container_close_event`、`on_clear_search`、`on_cycle_curve_clicked`、`on_data_ready`、`on_day_btn_clicked`、`on_error_msg`、`on_export_clicked`、`on_market_trend_clicked`、`on_plate_trend_clicked`、`on_progress_updated`、`on_rps_select_clicked`、`on_search_changed`、`on_stock_trend_clicked`、`on_tab_changed`、`on_table1_clicked`、`on_trend_data_ready`、`refresh`、`run`、`update_table1`。

### `tab.tab_20_view`

代码对象数：32。

函数/类：`Tab20View`、`Table1`、`Table2`、`Table3`、`_SortItem`、`__init__`、`__lt__`、`_apply_header_alignment`、`_connect_scroll_sync`、`_create_orange_separator`、`_highlight_cells`、`_init_ui`、`_manual_sort`、`_on_cell_clicked`、`_on_header_clicked`、`_refresh_header_labels`、`get_code_to_name`、`get_stock_codes`、`highlight_by_search`、`highlight_by_text`、`initUI`、`load_stocks`、`set_continuous_mode`、`sort_key`、`update_data`。

### `tab.tab_2_2_vc`

代码对象数：31。

函数/类：`MatrixItemDelegate`、`Tab2_2_VC`、`__init__`、`_clean_topic_title`、`_find_code_by_name`、`_init_corner_label`、`_is_bullish`、`_matrix_table_mouse_press_event`、`_parse_amount_to_float`、`_parse_height_from_high_days`、`_render_full_matrix`、`_rerender_after_toggle`、`_send_to_trader`、`_setup_ui`、`_strip_first_char`、`_update_corner_label`、`displayed_count`、`get_settings_filename`、`on_bullish_changed`、`on_desc_changed`、`paint`、`populate_matrix_blocks`、`populate_matrix_data`、`refresh`、`sizeHint`。

### `tab.tab_2_vc`

代码对象数：19。

函数/类：`Tab2VC`、`__init__`、`_on_simple_clear_clicked`、`_on_simple_search_changed`、`adjust_table2_columns`、`on_stock_code_clicked`、`populate_distribution_blocks`、`populate_limit_line`、`populate_limit_simple`、`refresh`、`setup_events`、`setup_table1`、`setup_table2`、`setup_ui`。

### `tab.tab_3_vc`

代码对象数：28。

函数/类：`Tab3VC`、`__init__`、`_debug_log_path`、`_on_table_selection_changed`、`_populate_flow_rows`、`_set_table_highlighted`、`create_separator`、`get_font_family`、`populate_pools`、`populate_table1_rows`、`populate_table2_rows`、`populate_table3_rows`、`populate_table4_rows`、`populate_table5_rows`、`populate_table6_rows`、`refresh`、`setup_common_table_properties`、`setup_events`、`setup_table_type1`、`setup_table_type2`、`setup_ui`。

### `tab.tab_5_vc`

代码对象数：52。

函数/类：`DataWorker`、`Tab5VC`、`__init__`、`_debug_log_path`、`_enable_hot_fetch`、`_fill_merged_cell`、`_fill_single_cell`、`_on_hot_table_cell_clicked`、`_on_search_text_changed`、`_on_table_selection_changed`、`_on_topic_table_cell_clicked`、`_set_cell_alignment`、`_set_table_highlighted`、`fetch_data`、`fetch_hot_data`、`fetch_hot_plate_data`、`fetch_hot_topic_data`、`fetch_plate_data`、`fetch_topic_data`、`fill_aggregation_table`、`fill_left_aggregation_table`、`fill_right_aggregation_table`、`get_font_family`、`on_data_error`、`on_data_ready`、`on_plate_data_ready`、`on_stock_code_clicked`、`on_sub_tab_changed`、`on_tab_changed`、`on_topic_data_ready`、`populate_hot_aggregation_data`、`populate_table_data`、`refresh`、`setup_events`、`setup_hot_aggregation_ui`、`setup_popular_stocks_ui`、`setup_table`、`setup_topic_tab_ui`、`setup_ui`。

### `tab.tab_6_1_vc`

代码对象数：10。

函数/类：`Tab6_1_VC`、`_XGTFetchWorker`、`__init__`、`_fetch_one`、`_fetch_stocks_for_date_api`、`_load_cache_sync`、`_make_fetch_worker`、`run`。

### `tab.tab_6_2_vc`

代码对象数：46。

函数/类：`Tab6_2_VC`、`_Tab6_2_FetchWorker`、`__init__`、`_apply_bullish_button_style`、`_build_board_curve_data`、`_disable_buttons`、`_fetch_one`、`_find_code_by_name`、`_get_weekday_name`、`_is_bullish`、`_load_cache_worker`、`_load_initial_cache_only`、`_on_board_curve_clicked`、`_on_cache_loaded`、`_on_clear_search_clicked`、`_on_search_text_changed`、`_on_tab_current_changed`、`_on_worker_day_ready`、`_on_worker_finished`、`_parse_height_from_high_days`、`_report_business_error`、`_report_performance_issue`、`_report_system_error`、`_restore_buttons`、`_send_to_trader`、`get_count`、`get_trading_days`、`on_bullish_changed`、`on_days_button_clicked`、`on_export_image_clicked`、`on_tab_activated`、`on_table1_item_clicked`、`on_update_clicked`、`on_update_clicked_with_days`、`run`、`update_table1`、`update_table2_for_topic`、`validate_days_input`。

### `tab.tab_6_2_view`

代码对象数：13。

函数/类：`Tab6_2_View`、`__init__`、`_init_corner_label`、`_update_corner_label`、`create_control_area`、`create_table1`、`create_table2`、`create_table_area`、`custom_mouse_press_event`、`get_widget`、`setup_ui`。

### `tab.tab_6_base_vc`

代码对象数：66。

函数/类：`Tab6BaseVC`、`__init__`、`_add_summary_row_to_table2`、`_add_topic_row_to_table2`、`_apply_bullish_button_text`、`_apply_search_filter`、`_browse`、`_collect_stock_rows`、`_collect_table2_display_rows`、`_collect_table2_topic_items`、`_create_summary_table2_data`、`_current_topic_name`、`_disable_buttons`、`_do_export`、`_fetch_stocks_for_date_api`、`_filter_table3`、`_load_cache_sync`、`_load_export_cfg`、`_load_initial_cache_only`、`_make_fetch_worker`、`_on_bullish_toggled`、`_on_search_text_changed`、`_on_table3_selection_changed`、`_on_worker_day_ready`、`_on_worker_finished`、`_parse_limit_analysis`、`_recompute_topic_stock_counts`、`_restore_buttons`、`_save_export_cfg`、`_show_batch_match_dialog`、`_show_export_dialog`、`_stock_in_topic_display`、`_update_table3_detail_panel`、`_update_table3_for_date_summary`、`_update_table3_from_topic`、`attach`、`board_num`、`clear_table3`、`detach`、`escape_html`、`filter_table2_by_topic_name`、`get_trading_days`、`on_days_button_clicked`、`on_table1_item_clicked`、`on_table2_item_clicked`、`on_update_clicked`、`on_update_clicked_with_days`、`priority`、`refresh_view`、`update_table1`、`update_table2`、`update_table3`、`validate_days_input`。

### `tab.tab_6_diy_dialog`

代码对象数：18。

函数/类：`DiyMiningDialog`、`_MatchWorker`、`__init__`、`_cb`、`_dispose_worker`、`_on_close_clicked`、`_on_export`、`_on_failed`、`_on_import`、`_on_match_done`、`_on_progress`、`_set_matching_ui`、`_stamp`、`_start_match`、`closeEvent`、`run`。

### `tab.tab_6_jygs_vc`

代码对象数：24。

函数/类：`Tab6JygsVC`、`_JYGSCacheWarmWorker`、`_JYGSFetchWorker`、`__init__`、`_adapt_snapshot`、`_auto_refresh_active_view`、`_check_auto_pull`、`_due_auto_pull_node`、`_fetch_one`、`_fetch_stocks_for_date_api`、`_is_valid_member`、`_load_cache_sync`、`_make_fetch_worker`、`_on_auto_warm_finished`、`_one`、`_run_auto_pull`、`_setup_auto_pull_timer`、`_yyyymmdd_to_dash`、`run`、`update_table3`。

### `tab.tab_6_vc_main`

代码对象数：6。

函数/类：`Tab6VCMain`、`__init__`、`_on_outer_tab_changed`、`_on_source_changed`、`_sync_bullish_button_to`。

### `tab.tab_6_view`

代码对象数：11。

函数/类：`Tab6View`、`__init__`、`create_control_area`、`create_table1`、`create_table2`、`create_table3`、`create_table_area`、`get_widget`、`setup_ui`。

### `tab.tab_7_vc`

代码对象数：75。

函数/类：`CycleCurveChartDialog`、`Tab7VC`、`_Tab7FetchWorker`、`__init__`、`_action_buttons`、`_apply_highlight_to_curve`、`_apply_top_n_highlight`、`_apply_zebra_style`、`_build_cycle_curve_amount_data`、`_build_cycle_curve_data`、`_build_mappings`、`_concept_color`、`_cubic_hermite_monotone`、`_cubic_hermite_smooth`、`_date_label_to_mm_dd`、`_highlight_block`、`_highlight_same_topic_cells`、`_hit_test_curve`、`_init_matplotlib_for_cycle_chart`、`_load_initial_cache_only`、`_on_amount_curve_clicked`、`_on_curve_group_segment`、`_on_cycle_chart_button_press`、`_on_cycle_chart_leave`、`_on_cycle_chart_mouse_move`、`_on_cycle_curve_clicked`、`_on_cycle_search_changed`、`_on_days_shortcut_clicked`、`_on_reset_highlight_clicked`、`_on_show_top_n_clicked`、`_on_tab_current_changed`、`_on_table1_hscroll`、`_on_table2_hscroll`、`_on_table2_selection_changed`、`_on_top_n_changed`、`_on_worker_day_ready`、`_on_worker_finished`、`_parse_amount_to_float`、`_parse_stock_name`、`_parse_topic_name`、`_rotate_next_block`、`_setup_scroll_sync`、`_smooth_curve_through_points`、`_sync_qbtn_days`、`_sync_table_column_config`、`_trim_leading_trailing_zeros`、`_update_block_buttons_style`、`_update_table2_for_topic`、`board_value`、`clear_table2`、`closeEvent`、`fetch_day`、`get_trading_days`、`on_options_changed`、`on_table1_item_clicked`、`on_update_clicked`、`run`、`to_label`、`update_table1`、`validate_days_input`。

### `tab.tab_7_view`

代码对象数：12。

函数/类：`Tab7View`、`__init__`、`_init_table1`、`_init_table2`、`create_control_area`、`create_table_area`、`get_widget`、`setup_ui`。

### `tab.tab_8_vc2`

代码对象数：61。

函数/类：`Tab8VC2`、`_SignalEmitter`、`__init__`、`_build_table_dialog_content`、`_cleanup_on_close`、`_date_to_label`、`_date_to_timestamp`、`_disable_buttons`、`_fetch`、`_fetch_bundles`、`_get_recent_trading_days`、`_load_initial_cache_only`、`_on_chart_stock_nature_clicked`、`_on_chart_top_n_changed`、`_on_data_cell_clicked`、`_on_data_ready`、`_on_days_changed_sync_top_n`、`_on_days_seg_clicked`、`_on_error`、`_on_export_clicked`、`_on_header_cell_clicked`、`_on_ladder_line_chart_clicked`、`_on_reset_date_btn_clicked`、`_on_search_changed`、`_on_start_date_btn_clicked`、`_on_start_date_selected`、`_on_tab_current_changed`、`_on_tier_seg_clicked`、`_on_worker_finished`、`_render_chart`、`_restore_buttons`、`_show_table_dialog`、`_stocks_for_level`、`_sync_header_col_widths`、`_update_progress`、`on_close`、`on_days_button_clicked`、`on_refresh_clicked`、`on_refresh_clicked_with_days`、`show_fail_map_dialog`、`show_limit_map_dialog`、`show_promotion_chart`。

### `tab.tab_99_desc_vc`

代码对象数：37。

函数/类：`CycleTheoryDialog`、`DesignConceptDialog`、`LzjClassicCaseDialog`、`QRCodeDialog`、`Tab99DescVC`、`Tab99DescView`、`ToolbarDescDialog`、`__init__`、`_on_anchor_clicked`、`_on_data_received`、`_on_error`、`_on_worker_finished`、`_start_fetch`、`center_on_parent`、`closeEvent`、`create_buttons_area`、`create_disclaimer`、`create_header`、`create_rounded_pixmap`、`generate_html`、`get_widget`、`on_classic_case_clicked`、`on_cycle_theory_clicked`、`on_design_concept_clicked`、`on_fans_clicked`、`on_feedback_clicked`、`on_fuli_clicked`、`on_progress_clicked`、`setup_ui`。

### `tab.tab_ai_export_config`

代码对象数：16。

函数/类：`_load_code_config`、`apply_user_export_dir_env`、`default_export_base_dir`、`echelon_cycle_trading_days`、`get_user_export_dir`、`load_export_ui_config`、`main_line_cycle_trading_days`、`market_cycle_trading_days`、`new_high_stock_top_n`、`new_high_trading_days`、`set_user_export_dir`、`should_show_cache_path`、`tab_export_enabled`、`topic_cycle_trading_days`、`visible_tabs`。

### `tab.tab_export`

代码对象数：42。

函数/类：`ExportDialog`、`__init__`、`_build_ui`、`_enforce_format_exclusive_initial`、`_export_codes_text`、`_export_excel`、`_export_excel_meta`、`_export_png`、`_export_png_meta`、`_extract_rows_for_topic`、`_extract_rows_for_topic_with_meta`、`_get_export_column_indices`、`_get_topic_block_text`、`_height_col_index`、`_is_blank_row`、`_is_title_row_fast`、`_load_config`、`_on_all_toggled`、`_on_copy_clicked`、`_on_export_clicked`、`_on_format_toggled`、`_on_none_toggled`、`_populate_table9_from_table3`、`_qcolor_to_hex`、`_row_matches_filters`、`_save_config`、`_set_opt`、`_with_suffix`、`_zha_col_index`、`make_checkbox`。

### `tab_manager`

代码对象数：79。

函数/类：`MainWindow`、`__init__`、`_bg`、`_delayed_full_initUI`、`_delayed_init_controllers`、`_delayed_post_init`、`_do_update_tab_star_marks`、`_fetch_member_status`、`_format_vip_modules_text`、`_get_config_value`、`_get_dpi_scale`、`_load_and_apply_font_size`、`_on_auth_failed`、`_on_exchange_points_clicked`、`_on_info_label_clicked`、`_on_login_clicked`、`_on_renew_clicked`、`_on_vip_model_updated`、`_open_learn_vip`、`_perform_logout`、`_popup_background_menu`、`_popup_member_menu`、`_popup_menu_center`、`_refresh_zebra_menu`、`_revert_tab_change`、`_set_all_tables_font_size`、`_set_all_tables_zebra`、`_show_custom_linkage_dialog`、`_update_info_label_text`、`_update_login_button_text`、`_update_tab_star_marks`、`callback`、`center`、`check_version_update`、`create_info_bar`、`create_toolbar`、`custom_set_visible`、`ensure_zhiku_data_ready`、`initUI`、`init_controllers`、`make_platform_callback`、`manual_check_update`、`on_cancel`、`on_copy_close`、`on_copy_wechat_close`、`on_custom_toggled`、`on_ok`、`on_tab_changed`、`on_test_vip_clicked`、`refresh_current_tab`、`setup_font`、`show_hardware_id_dialog`、`show_toolbar_desc`、`toggle_main_stay_on_top`、`toggle_tianyan_mode`、`update_tianyan_font_color`、`update_timed_refresh_button`。

### `thread_registry`

代码对象数：9。

函数/类：`ThreadRegistry`、`__init__`、`get_thread_registry`、`register_qthread`、`register_thread`、`stop_all`、`stop_by_name`、`unregister`。

### `tool`

代码对象数：1。

函数/类：无命名函数。

### `tool.app_trader`

代码对象数：30。

函数/类：`AppTrader`、`SendResult`、`__init__`、`_find_tdx_window`、`_force_foreground`、`_get_custom_window`、`_get_eastmoney_window`、`_get_ths_process`、`_get_ths_window`、`_get_ths_yh_window`、`callback`、`check_running`、`send`、`send_to_custom`、`send_to_eastmoney`、`send_to_tdx`、`send_to_ths`、`send_to_ths_yh`、`sort_key`。

### `tool.app_trader_macos`

代码对象数：8。

函数/类：`MacHelper`、`__init__`、`_input_via_applescript`、`_update_app_name_from_settings`、`activate_app`、`open_stock`、`send`。

### `tool.app_trader_macos_fallback`

代码对象数：8。

函数/类：`MacHelper`、`__init__`、`_input_via_applescript`、`_update_app_name_from_settings`、`activate_app`、`open_stock`、`send`。

### `tool.base64_image_gzh`

代码对象数：1。

函数/类：无命名函数。

### `tool.base64_image_pay`

代码对象数：1。

函数/类：无命名函数。

### `tool.base64_image_zy`

代码对象数：1。

函数/类：无命名函数。

### `tool.base64_loonglog`

代码对象数：1。

函数/类：无命名函数。

### `tool.cache_path_tool`

代码对象数：12。

函数/类：`CachePathTool`、`__init__`、`__new__`、`_get_app_root`、`get_cache_file_path`、`get_cache_file_path_by_name`、`get_cache_path_tool`、`get_cache_root`、`get_image_cache_root`、`get_instance`、`sanitize_filename`。

### `tool.calendar_tool`

代码对象数：28。

函数/类：`CalendarFetchWorker`、`CalendarTool`、`__init__`、`_get_cache_file_path`、`_get_cache_root`、`_get_default_holidays_from_calendar`、`_load_current_year_on_startup`、`_load_year_holidays_from_cache`、`_on_fetch_failed`、`_on_fetch_success`、`_on_worker_finished`、`_save_year_holidays_to_cache`、`_should_fetch_year`、`_start_fetch_worker`、`ensure_year_data`、`get_app_watch_reporter`、`get_calendar_tool`、`get_next_trading_day`、`get_previous_trading_day`、`get_trading_days`、`is_stock_trading_day`、`is_trading_day`、`on_failed_wrapper`、`on_finished_wrapper`、`on_success_wrapper`、`run`。

### `tool.event`

代码对象数：15。

函数/类：`EventReport`、`__init__`、`__new__`、`_fetch_ip_location`、`_format_time_diff`、`_generate_device_uuid`、`_get_os`、`_initialize_class_vars`、`_post_request`、`ensure_ip_ready`、`fetch`、`launch_app_request`、`log`、`send`。

### `tool.linkage_settings`

代码对象数：14。

函数/类：`LinkageSettings`、`__init__`、`_auto_detect_and_save`、`_load`、`_save`、`get_linkage_settings`、`get_selected_platforms`、`get_settings_filename`、`update_bring_to_front`、`update_custom_app`、`update_custom_exe`、`update_custom_window_name`、`update_selection`。

### `tool.persist_store`

代码对象数：7。

函数/类：`_get_hidden_base_dir`、`get_dir_path`、`get_json_filename`、`get_json_path`、`load_json`、`save_json`。

### `tool.table_export`

代码对象数：7。

函数/类：`add_watermark`、`export_table_to_png`、`get_default_export_filename`。

### `tool.table_scroll_preserve`

代码对象数：3。

函数/类：`_clamp_v`、`refresh_preserve_scroll`。

### `tool.tool`

代码对象数：24。

函数/类：`TextColor`、`_should_use_previous_trading_day`、`create_toolbar_divider`、`format_countdown`、`get_bg_color_style`、`get_chi_color`、`get_data_date`、`get_kaipanla_trade_count_down`、`get_previous_trading_date`、`get_previous_trading_date2`、`get_reqeust_timestamp`、`get_title_color_style`、`get_trade_count_down`、`get_trading_date`、`get_trading_date2`、`is_over_10_days`、`is_stock_trading_day`、`is_today`、`is_trading_day`、`is_trading_time`、`is_workday`、`print_colored_text`、`strip_emoji_for_chart`。

### `tool.zhiku1_tool`

代码对象数：17。

函数/类：`Zhiku1Tool`、`__init__`、`__new__`、`_append_stock_row`、`_build_global_rows`、`_build_rows_from_directory`、`_build_rows_from_zip`、`_do_task_1_unzip`、`_do_task_3_build_tianyan`、`_path_under_temp`、`_unzip_data_zip_to_theme_stock_list`、`get_global_rows_raw`、`get_zhiku1_tool`、`trigger_task_1`、`trigger_task_3`。

### `ui`

代码对象数：1。

函数/类：无命名函数。

### `ui.auto_tip`

代码对象数：5。

函数/类：`AutoTip`、`__init__`、`mousePressEvent`、`show_tip`。

### `ui.base_table`

代码对象数：34。

函数/类：`BaseTable`、`__init__`、`_get_dpi_scale`、`_init_trader`、`_select_row_and_trigger_action`、`_send_to_trader`、`_trigger_cell_click_action`、`_validate_current_row`、`apply_header_style`、`apply_unified_style`、`clear`、`configure_table_global_settings`、`connect_custom_click_handler`、`connect_left_right_navigation_handler`、`create_grid_toggle_button`、`get_stock_code`、`hide_grid_lines`、`insertRow`、`keyPressEvent`、`navigate_down`、`navigate_left`、`navigate_right`、`navigate_up`、`on_cell_clicked`、`select_current_row`、`setItem`、`set_code_column`、`set_last_column_right_align`、`set_zebra_enabled`、`setup_base_events`、`setup_base_style`、`show_grid_lines`、`toggle_grid_lines`。

### `ui.base_tree`

代码对象数：38。

函数/类：`BaseTree`、`__init__`、`_get_dpi_scale`、`_get_next_visible_item`、`_get_previous_visible_item`、`_init_trader`、`_select_first_visible_item`、`_select_item_and_trigger_action`、`_select_last_visible_item`、`_send_to_trader`、`_trigger_item_click_action`、`_validate_current_row`、`addTopLevelItem`、`addTopLevelItems`、`apply_header_style`、`apply_unified_style`、`clear`、`configure_table_global_settings`、`connect_custom_click_handler`、`connect_left_right_navigation_handler`、`create_grid_toggle_button`、`get_stock_code`、`hide_grid_lines`、`keyPressEvent`、`navigate_down`、`navigate_left`、`navigate_right`、`navigate_up`、`on_item_clicked`、`select_current_row`、`set_code_column`、`set_last_column_right_align`、`set_zebra_enabled`、`setup_base_events`、`setup_base_style`、`show_grid_lines`、`toggle_grid_lines`。

### `ui.basetable2`

代码对象数：20。

函数/类：`BaseTable2`、`__init__`、`_get_dpi_scale`、`_init_trader`、`_on_cell_clicked`、`_select_row_and_trigger_action`、`_send_to_trader`、`_setup_base_style`、`_trigger_cell_click_action`、`apply_unified_style`、`clear`、`connect_custom_click_handler`、`get_trader`、`keyPressEvent`、`navigate_down`、`navigate_up`、`select_current_row`、`set_code_column_offset`、`set_group_size`。

### `ui.calendar_widget`

代码对象数：27。

函数/类：`CalendarButton`、`CustomCalendarWidget`、`__init__`、`_apply_header_colors`、`_async_update_workdays`、`apply_button_styles`、`apply_calendar_styles`、`disable_buttons`、`enable_buttons`、`get_calendar_widget`、`get_non_workday_format`、`get_workday_format`、`go_to_next_trading_date`、`go_to_previous_trading_date`、`on_date_clicked`、`on_date_selected`、`setText`、`set_buttons_enabled`、`setup_calendar`、`setup_header_colors`、`setup_ui`、`show_calendar`、`text`、`toggle_calendar`、`update_workdays`。

### `ui.cycle_curve_dialog`

代码对象数：32。

函数/类：`CycleCurveChartDialog`、`__init__`、`_apply_highlight_to_curve`、`_apply_top_n_highlight`、`_concept_color`、`_cubic_hermite_monotone`、`_cubic_hermite_smooth`、`_date_label_to_mm_dd`、`_highlight_block`、`_hit_test_curve`、`_init_matplotlib_for_cycle_chart`、`_on_cycle_chart_button_press`、`_on_cycle_chart_leave`、`_on_cycle_chart_mouse_move`、`_on_cycle_search_changed`、`_on_reset_highlight_clicked`、`_on_show_top_n_clicked`、`_on_top_n_changed`、`_parse_ymd`、`_rotate_next_block`、`_smooth_curve_through_points`、`_trim_leading_trailing_zeros`、`_update_block_buttons_style`、`closeEvent`。

### `ui.data_repair_dialog`

代码对象数：21。

函数/类：`DataRepairDialog`、`__init__`、`_clear_all_cache_worker`、`_clear_date_cache_worker`、`_clear_expiry_cache_worker`、`_extract_date_from_path`、`_get_clean_root`、`_on_clear_all_completed`、`_on_clear_completed`、`_on_clear_expiry_completed`、`on_calendar_date_clicked`、`on_clear_all_clicked`、`on_clear_clicked`、`on_clear_expiry_clicked`、`on_date_selected`、`setup_ui`、`show_data_repair_dialog`。

### `ui.desc_button`

代码对象数：5。

函数/类：`_tune_html`、`create_desc_button`、`highlight_brackets`、`on_clicked`。

### `ui.export_dialog`

代码对象数：23。

函数/类：`ExportDialog`、`__init__`、`_build_datatype_row`、`_build_date_row`、`_build_filename`、`_build_filetype_row`、`_build_path_row`、`_build_ui`、`_default_export_dir`、`_norm_date_ymd`、`_on_export_clicked`、`_on_progress`、`_pick_directory`、`_remember_last_dir`、`_run_concept_match`、`_sanitize_name`、`_write_code_json`、`_write_code_txt`、`_write_concept_report`、`closeEvent`。

### `ui.feedback_dialog`

代码对象数：19。

函数/类：`LFeedbackDialog`、`__init__`、`_clear_global_ref`、`center_window`、`close_dialog`、`disable_widget`、`enable_widget`、`generate_device_id`、`get_device_info`、`get_version_info`、`on_cancel_clicked`、`on_submit_clicked`、`show`、`show_feedback_dialog`、`show_submitting_state`、`submit_feedback`、`validate_input`。

### `ui.feedback_service`

代码对象数：12。

函数/类：`LFeedbackService`、`__init__`、`cleanup_old_files`、`get_local_feedbacks`、`retry_local_feedbacks`、`save_to_local`、`submit_feedback`、`submit_to_server`、`test_connection`。

### `ui.fuli_dialog`

代码对象数：27。

函数/类：`AnimatedTableView`、`FuliDialog`、`FuliHeaderView`、`FuliTableWidget`、`__init__`、`_center_on_screen`、`_format_value`、`_fuli_data`、`_header_colors`、`_init_ui`、`_on_close`、`_on_use_guide_clicked`、`_parse_value`、`_release_resources`、`clear_all_highlights`、`closeEvent`、`highlight_headers`、`mouseMoveEvent`、`paintEvent`、`paintSection`、`reject`、`restore_headers`、`update_highlights`。

### `ui.info_label_widget`

代码对象数：23。

函数/类：`InfoLabelWidget`、`_InfoLabelImageClickFilter`、`__init__`、`_add_section_title`、`_adjust_text_edit_height`、`_create_content_card`、`_do`、`_download_and_show`、`_on_image_clicked`、`_pixmap_from_data_uri`、`_process_html_images`、`_show_image_dialog`、`clear`、`download_and_update`、`eventFilter`、`replace_image`、`set_html`、`set_stock_detail`、`to_html`、`update_ui`。

### `ui.l_button`

代码对象数：14。

函数/类：`LButton`、`__init__`、`_apply_style`、`_color_to_css`、`_update_size`、`build_lbutton_qss`、`setText`、`set_background_color`、`set_border_color`、`set_colors`、`set_hover_background_color`、`set_pressed_background_color`、`set_text_color`。

### `ui.l_color`

代码对象数：3。

函数/类：`StockColorHelper`、`get_stock_color`。

### `ui.l_input`

代码对象数：3。

函数/类：`LInput`、`__init__`。

### `ui.l_line_edit`

代码对象数：5。

函数/类：`get_search_lineedit_qss`、`get_toolbar_lineedit_qss`、`pin_toolbar_row`、`sync_toolbar_control_height`。

### `ui.ladder_height_dialog`

代码对象数：31。

函数/类：`LadderHeightChartWidget`、`__init__`、`_build_series_from_bundles`、`_concept_color`、`_format_date_info_bar`、`_init_matplotlib_for_cycle_chart`、`_mm_dd`、`_mmdd_week`、`_name_matches_search`、`_on_leave`、`_on_mouse_move`、`_plot_chart`、`_smooth_curve_through_points`、`_to_date_val`、`closeEvent`、`collect_codes_from_bundles`、`refresh`、`set_data`、`set_panorama_mode`、`set_search_keywords`、`set_stock_nature_mode`、`set_top_n`。

### `ui.ladder_line_chart_facade`

代码对象数：10。

函数/类：`_latest_trading_day_label`、`_on_chart_destroyed`、`_show_percent_line_chart`、`container_close_event`、`on_data_ready`、`on_error_msg`、`on_progress_updated`、`show_ladder_height_stock_line_chart`、`show_stock_line_chart_for_codes`。

### `ui.line_chart_dialog`

代码对象数：20。

函数/类：`LineChartDialog`、`__init__`、`_draw_chart`、`_format_date_for_info_bar`、`_on_leave`、`_on_mouse_move`、`_toggle_line`、`calculate_rates`、`closeEvent`、`mk`、`plot_chart`、`setup_ui`、`show_line_chart_dialog`、`sk`。

### `ui.loading_mask_manager`

代码对象数：11。

函数/类：`LoadingMaskManager`、`__init__`、`__new__`、`_hide_mask`、`_show_mask`、`get_loading_mask_manager`、`hide_mask`、`set_loading_label`、`show_mask`、`update_position`。

### `ui.new_high_trend_dialog`

代码对象数：14。

函数/类：`NewHighTrendDialog`、`__init__`、`_create_orange_separator`、`_parse_data`、`_update_btn_styles`、`closeEvent`、`on_days_clicked`、`on_hover`、`plot_chart`。

### `ui.notice_bar`

代码对象数：24。

函数/类：`NoticeBar`、`NoticeFetchThread`、`__init__`、`_check_if_scroll_needed`、`_get_dismissed_notice_id`、`_get_font_size`、`_get_label_style`、`_on_close_clicked`、`_on_link_activated`、`_on_notices_fetched`、`_reset_and_start_scroll`、`_save_dismissed_notice_id`、`_scroll_text`、`_start_scrolling`、`_stop_scrolling`、`_update_container_geometry`、`fetch_notices`、`init_ui`、`resizeEvent`、`run`、`showEvent`、`show_notice`、`update_font_size`。

### `ui.points_exchange_dialog`

代码对象数：8。

函数/类：`PointsExchangeDialog`、`__init__`、`_call_exchange_api`、`_on_exchange`、`_on_exchange_error`、`_on_exchange_result`、`_update_points_display`。

### `ui.qbutton`

代码对象数：13。

函数/类：`QButton`、`QButtonSegment`、`__init__`、`_on_segment_clicked`、`_rebuild_buttons`、`_refresh_styles`、`qbutton_toolbar_segment_height_kw`、`selected_index`、`set_highlight_selection`、`set_segments`、`set_selected`。

### `ui.rps_selector`

代码对象数：74。

函数/类：`RpsLoadingDialog`、`RpsPctFetcher`、`RpsSelectionDialog`、`RpsTable`、`_ExportOptionDialog`、`_SortItem`、`__init__`、`__lt__`、`_active_codes`、`_apply_auto_button_style`、`_apply_filter_button_styles`、`_apply_plate_button_styles`、`_average_rank_pct`、`_build_ui`、`_center_on_parent`、`_clamp_int`、`_classify_board`、`_codes_all_visible`、`_codes_recent5_strong`、`_codes_threshold_strong`、`_cumulative_pct`、`_fill_table_for_scope`、`_fmt_pct`、`_in_auto_refresh_window`、`_in_fast_refresh_window`、`_ingest_pct_data`、`_load_persist`、`_on_auto_tick`、`_on_export`、`_on_header_clicked`、`_on_ok`、`_on_plate_clicked`、`_on_progress`、`_on_refresh_clicked`、`_on_refresh_done`、`_on_threshold_changed`、`_parse_hq_daily`、`_reapply_current_sort`、`_refresh_d1_in_table_and_rps`、`_refresh_header_labels`、`_refresh_highlight_and_status`、`_refresh_target_codes`、`_release_refresh_worker`、`_row_val`、`_save_persist`、`_set_filter_mode`、`_set_row`、`_sort_by_column`、`_start_refresh`、`_stop_auto_refresh`、`_sync_auto_interval`、`_toggle_auto_refresh`、`_update_status_text`、`closeEvent`、`key`、`make`、`on_done`、`open_rps_selector`、`run`、`showEvent`。

### `ui.selection_underline_delegate`

代码对象数：5。

函数/类：`SelectionUnderlineDelegate`、`draw_selection_underline`、`install_clean_selection_look`、`paint`。

### `ui.stock_card_grid`

代码对象数：36。

函数/类：`StockCardGridWidget`、`StockCardPlaceholder`、`StockCardWidget`、`_ClickableHeader`、`_ClickableMainHeader`、`_ReasonHoverPopup`、`__init__`、`_apply_zhangfu_style`、`_card_font_size`、`_cols_for_width`、`_create_main_branch_header`、`_create_sub_branch_header`、`_on_card_clicked`、`_rebuild_from_pending`、`_refresh_card_selection`、`_schedule_lazy_update`、`_show_reason_popup`、`_stock_fg_color`、`_stock_reason`、`_update_visible_cards`、`clear`、`enterEvent`、`leaveEvent`、`mousePressEvent`、`resizeEvent`、`set_selected`、`set_structure`、`set_zhangfu`、`update_zhangfu_map`。

### `ui.stock_percent_curve_handler`

代码对象数：15。

函数/类：`StockPercentDataFetcher`、`__init__`、`_parse_board_from_label`、`_process_one`、`container_close_event`、`get_stock_codes_from_table2`、`on_data_ready`、`on_error_msg`、`on_failed_stocks`、`on_finished`、`on_progress_updated`、`run`、`show_stock_percent_curve_dialog`。

### `ui.stock_percent_dialog`

代码对象数：32。

函数/类：`StockPercentChartDialog`、`__init__`、`_apply_highlight`、`_generate_random_color`、`_highlight_block`、`_highlight_polling`、`_mm_dd_from_iso`、`_on_button_press`、`_on_curve_display_mode_changed`、`_on_leave`、`_on_mouse_move`、`_on_pick`、`_on_search_changed`、`_plot_chart`、`_slice_data_by_days`、`_split_curve_by_display_mode`、`_toggle_highlight_for_code`、`_update_block_buttons_style`、`_update_window_title`、`closeEvent`。

### `ui.styled_button`

代码对象数：5。

函数/类：`StyledButton`、`__init__`、`apply_standard_button_style`、`get_standard_button_qss`。

### `ui.ui_message_box`

代码对象数：5。

函数/类：`_center_buttons`、`_center_content`、`ask_yes_no`、`show_ok`。

### `ui.verify_code_dialog`

代码对象数：15。

函数/类：`VerifyCodeDialog`、`__init__`、`_build_ui`、`cancel`、`get_config_thread`、`get_verify_code_config`、`on_config_error`、`on_config_result`、`on_verify_success`、`show_verify_code_dialog`、`verify_code`。

### `ui.view`

代码对象数：14。

函数/类：`ClickableLabel`、`PersistentMenu`、`__init__`、`_check_and_hide`、`addCheckableAction`、`addSeparator`、`focusOutEvent`、`getCheckBox`、`mousePressEvent`、`popup`、`set_click_callback`。

### `update`

代码对象数：1。

函数/类：无命名函数。

### `update.version_checker`

代码对象数：65。

函数/类：`CleanupManager`、`MessageService`、`VersionChecker`、`_UIInvoker`、`__init__`、`_call`、`_show`、`callback_wrapper`、`check_and_show_update`、`check_thread`、`check_update`、`check_update_silent`、`check_update_sync`、`cleanup_old_version_on_launch`、`cleanup_on_launch`、`delayed_exit`、`download_thread`、`download_update_package`、`ensure_dir`、`ensure_parent_dir`、`error`、`get_cleanup_dir`、`get_cleanup_marker_path`、`get_dir`、`get_marker_path`、`get_presigned_download_url`、`get_temp_cleanup_marker_path`、`get_temp_marker_path`、`get_url_thread`、`info`、`install_thread`、`install_update_package`、`log_business_error`、`log_performance_issue`、`log_security_event`、`log_system_error`、`on_check_result`、`require_captcha_for_update`、`run_on_ui_thread`、`should_bypass_captcha_for_update`、`show_error_message`、`show_info_message`、`show_update_dialog`。

### `update.version_download_dialog`

代码对象数：21。

函数/类：`StableUpdateDialog`、`__init__`、`_build_ui`、`_log_system_error`、`_on_close`、`_on_download_complete`、`_on_download_progress`、`_on_install_complete`、`_on_presigned_url_result`、`_on_verify_code_result`、`_reset_buttons`、`_show_verify_code_dialog`、`_start_update`、`closeEvent`、`create_and_show`、`keyPressEvent`、`reject`、`show`、`show_stable_update_dialog`、`update_now`。

### `vip`

代码对象数：1。

函数/类：无命名函数。

### `vip.member_menu`

代码对象数：8。

函数/类：`_on_refresh_vip_clicked`、`add_user_id_button`、`on_copy_close`、`on_user_id_clicked`、`popup_member_menu`。

### `vip.vip_func_tips`

代码对象数：4。

函数/类：`on_learn_clicked`、`on_open_vip`、`show_vip_func_tips`。

### `vip.vip_helper`

代码对象数：2。

函数/类：`ensure_vip`。

### `vip.vip_info_fetcher`

代码对象数：21。

函数/类：`VipInfo`、`VipInfoFetcher`、`__init__`、`_build_headers`、`_build_url`、`_fetch_from_api`、`_is_cache_valid`、`clear_cache`、`clear_vip_info_cache`、`get_vip_info`、`get_vip_info_fetcher`、`has_module_permission`、`instance`、`is_expired`、`is_normal_user`、`is_permanent`、`is_vip`、`should_show_tips`、`wechat_openid`。

### `vip.vip_manager`

代码对象数：68。

函数/类：`ClickablePackageFrame`、`PaymentDialog`、`VipManager`、`VipView`、`__init__`、`_apply_package_heights`、`_build_package_summary`、`_clear_packages_layout`、`_copy_id`、`_create_order_and_get_qrcode`、`_create_package_card`、`_determine_highlight_index`、`_display_qrcode`、`_ensure_view`、`_expired_then_login`、`_fetch_packages`、`_format_pay_title`、`_generate_qrcode_from_url`、`_get_package_display_info`、`_login_then_pay`、`_login_then_proceed`、`_on_package_error`、`_on_package_result`、`_on_package_selected`、`_on_payment_success`、`_on_vip_model_updated`、`_parse_duration_days`、`_parse_packages`、`_poll_order_status`、`_render_packages`、`_show_error`、`_show_payment_page`、`_show_qrcode_image`、`_start_polling`、`_update_highlight_state`、`closeEvent`、`download_image`、`get_vip_manager`、`hide`、`instance`、`mousePressEvent`、`resizeEvent`、`show`、`worker`。

### `vip.vip_module_checker`

代码对象数：19。

函数/类：`VipModuleChecker`、`VipModuleFetchWorker`、`__init__`、`_build_api_url`、`_on_fetch_failed`、`_on_fetch_success`、`_on_worker_finished`、`clear_cache`、`fetch_vip_module_list_async`、`fetch_vip_modules_async`、`get_instance`、`get_vip_module_checker`、`get_vip_module_list_sync`、`is_vip_module`、`refresh`、`run`。

### `vip.vip_share`

代码对象数：5。

函数/类：`on_copy`、`on_share_clicked`、`setup_share_button`。

### `vip.vip_user`

代码对象数：26。

函数/类：`VipUser`、`VipUserModel`、`__init__`、`_build_url`、`_calc_is_vip`、`_get_api_base`、`_trigger_auth_failed`、`_worker`、`call_member_api_raw`、`clear_model`、`fetch_now`、`from_response`、`get_last_error`、`get_model`、`get_vip_user`、`instance`、`is_member`、`is_vip`、`set_auth_failed_callback`、`start_background_refresh`、`stop_background_refresh`、`subscribe`、`test_member_api`、`test_vip_api`、`unsubscribe`。

### `vip.wechat_auth`

代码对象数：33。

函数/类：`WechatAuth`、`WechatAuthSignals`、`WechatLoginDialog`、`__init__`、`_get_config_file`、`_load_auth_info`、`_on_link_activated`、`_on_polling_timeout`、`_poll_status`、`_save_auth_info`、`clear_auth_info`、`closeEvent`、`create_session`、`generate_qr_code`、`get_member_status`、`get_token`、`get_user_info`、`get_wechat_auth`、`get_wechat_openid`、`init_ui`、`on_polling_timeout`、`on_status_update`、`query_status`、`set_token`、`set_wechat_openid`、`show_wechat_login_dialog`、`start_login`、`start_polling`、`stop_polling`。

### `application`

代码对象数：12。

函数/类：`Application`、`__init__`、`_cleanup_old_logs_async`、`_try_report_last_crash`、`closeEvent`、`delayed_cleanup`、`global_exception_handler`、`init_controllers`、`launch_report_async`、`setup_global_exception_handler`。

## 附录 B：机器可读证据

完整模块字符串、名称与代码对象证据位于项目运行目录的 `runtime/longzijue_static_analysis/module_evidence.json`；模块分组位于 `module_inventory.json`。这些文件只包含静态元数据和短字符串，不包含完整反编译源码。
