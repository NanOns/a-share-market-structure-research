# 每日关注对象留存、状态判定与全库迁移设计 V2

> 文档版本：`DAILY_FOCUS_FOLLOW_UP_DESIGN_V2`  
> 初稿日期：2026-09-21；V2 修订日期：2026-09-22（Asia/Shanghai）  
> 状态：`REVISED_DESIGN_REVIEW / IMPLEMENTATION_NOT_STARTED`  
> 本文只定义产品、数据与实施方案，不修改现有算法，不执行数据生成，不构成买卖建议。

## 1. 结论先行

新增一级菜单 **“关注跟踪”**，长期保存并持续追踪每天生成的三类对象：

1. 当前关注个股（`CURRENT_FOCUS`）；
2. 提前观察个股（`EARLY_FOCUS`）；
3. 当前强势板块与提前观察板块（`CURRENT_SECTOR` / `EARLY_SECTOR`）。

系统不能只保存“今天还在榜上的对象”，而要保存一个对象从首次出现、持续观察、升级、降级、退出到再次进入的完整事件周期。对象退出当日清单后仍保留后续走势，因此可以回答：

- 当时为什么进入关注；
- 后来是正常回调、直接加速、横盘等待，还是结构破坏；
- 提前观察对象是否升级为当前关注；
- 退出清单后 T+1、T+3、T+5、T+10、T+20 表现如何；
- 当前状态是否仍值得继续研究，等待什么条件，什么条件下失效。

存储架构建议采用 **PostgreSQL + Parquet**，迁移范围是现有生产 DuckDB 的完整业务能力和全部仍被引用的数据，而不只是本次新增表：

- PostgreSQL 是页面、任务状态、关注快照、事件周期和查询接口的唯一服务数据库；
- Parquet 保存大体量日线、因子和可重算历史；
- DuckDB 只作为离线计算引擎读取冻结 Parquet/暂存结果，不再由页面 API 或多个进程直接打开生产数据库文件。

这个方案直接解决两个问题：一是关注对象退出后“消失”；二是 Windows 下 DuckDB 文件被不同进程占用导致页面读取失败。

## 2. 背景与现状问题

### 2.1 已有能力

当前系统已经具备：

- `research_shortlist`：保存某个研究运行中的 `CURRENT_FOCUS`、`EARLY_FOCUS` 和 `INDIVIDUAL`；
- `research_sector_states`：保存某个研究运行中的当前/潜在板块状态和排名；
- `research_runs`、publication、snapshot、membership snapshot 等运行身份；
- 部分 Forward observation/outcome 能力；
- `waiting_for`、`invalid_if`、`previous_state`、`change_reason` 等解释字段；
- T+1/T+5/T+10/T+20 描述性评估合同。

### 2.2 当前缺口

现有首页和接口围绕“当前运行”查询，导致以下问题：

1. **退出即消失**：昨天在提前观察、今天不在清单，就无法从页面继续查看。
2. **没有统一事件周期**：同一股票连续三天出现，是三条日记录还是一个持续观察事件，页面无法明确表达。
3. **状态变化不可见**：提前观察升级为当前关注、当前关注退化为观察、板块转弱等变化没有统一时间线。
4. **走势与入选原因脱节**：能看到当日理由，但看不到入选后的价格路径、最大上涨、最大回撤和结构变化。
5. **个股与板块跟踪断裂**：股票后来上涨，但原支持板块已经转弱，或者板块继续走强但个股掉队，目前难以对照。
6. **“是否应该买入”缺乏结构化提示**：系统没有把等待、确认、过热、回调、破坏等研究状态明确分开。
7. **数据库可靠性不足**：DuckDB 生产文件被服务进程和计算子进程分别打开，在 Windows 下反复产生占用和读取失败。
8. **日期身份容易混淆**：自然日、在线最新交易日、本地数据日和最终发布日期必须继续分开显示。

## 3. 目标与非目标

### 3.1 目标

- 每个交易日原样留存关注个股和板块快照；
- 建立跨日、不可变历史上的关注事件周期；
- 即使对象退出当天清单，也继续计算和展示后续走势；
- 显示从提前观察到当前关注的升级路径；
- 同屏展示个股走势、板块走势、支持关系和每日状态变化；
- 提供研究型“当前判断”，明确等待条件与失效条件；
- 支持按首次出现日期、当前状态、类别、板块、收益/回撤等筛选；
- 页面查询不再与离线计算争抢 DuckDB 文件；
- 所有结果绑定 trade date、publication、research run、算法合同和输入身份。

### 3.2 非目标

- 不给出“买入/卖出”指令、目标价、仓位或上涨概率；
- 不用未来数据改写首次入选理由和当日状态；
- 不把事后涨跌反向包装成当时可知结论；
- 不因本功能修改现有候选准入、评分阈值和排名算法；
- 不自动交易；
- 不保存受现有合同禁止持久化的热榜原始数据。

## 4. 核心产品概念

### 4.1 每日快照 Daily Snapshot

某个交易日、某个完整研究发布下，对象当时的事实。发布后不可修改；同日修订创建新 revision，不覆盖旧版本。

股票快照至少保存：

- 清单类型、当日排名、场景类型、选择模式；
- 入选理由、等待条件、失效条件、风险代码；
- 收盘价及价格口径；
- RPS、均线位置、突破/回踩、成交额、换手率可用状态；
- 主支持板块、其他支持板块、LOO 支持状态；
- publication、research run、bundle digest、算法和参数身份。

板块快照至少保存：

- `CURRENT` / `EARLY` 状态、排名、分支和质量；
- 强度、宽度、相对强度、成交额、成员覆盖；
- 领涨/启动/回踩/观察成员；
- 成员快照身份及计算合同。

### 4.2 关注事件 Episode

Episode 是同一对象的一段连续研究生命周期，不等同于某一天的榜单行。

建议状态：

```text
NEW
  ├─> PERSISTENT
  ├─> UPGRADED          提前观察 -> 当前关注
  ├─> DOWNGRADED        当前关注 -> 提前观察
  ├─> EXITED            不再入选，但继续跟踪
  ├─> INVALIDATED       明确触发失效条件
  └─> DATA_UNAVAILABLE  当日无法可靠判断

EXITED / INVALIDATED
  └─> REENTERED         后续重新满足条件，创建新 episode 并关联前 episode
```

规则：

- 同一对象连续交易日处于任一关注清单，沿用同一个 episode；
- 发生提前观察与当前关注切换，只增加 transition，不新建 episode；
- 退出后继续保存行情观察和到期结果；
- 退出后再次入选，创建新 episode，避免把两次独立机会混成一段；
- 同日数据修订属于 revision，不制造跨日 transition；
- 算法版本变化单独标记 `MODEL_VERSION_CHANGED`，不得解释成市场状态变化。

### 4.3 后续走势 Observation

对每个 episode，每个后续交易日追加一条 observation。它回答“从首次关注以来发生了什么”，不改变过去的入选理由。

核心指标：

- `return_since_first`：相对首次关注日收盘；
- `return_since_current_entry`：相对升级为当前关注当日收盘；
- `max_return_since_first`；
- `max_drawdown_since_first`；
- `drawdown_from_post_signal_peak`；
- T+1、T+3、T+5、T+10、T+20 收益；
- 期间最大上行、最大回撤、首次达到某结构状态的交易日；
- 当前价相对 MA5/MA10/MA20/MA60；
- RPS5/RPS20 及其变化；
- 当日成交额比、换手事实及数据能力状态；
- 原支持板块当前状态、板块同期收益、个股相对板块表现；
- 是否仍在清单、是否已退出、退出原因。

交易日序列必须来自冻结主交易日历，不用自然日换算 T+N。

## 5. “是否值得买入”的产品表达

页面不能输出直接买卖命令。建议改为 **“研究状态”**，让用户知道当前处于哪种结构以及下一步看什么。

| 研究状态 | 含义 | 页面建议文案 |
|---|---|---|
| `WAIT_CONFIRMATION` | 提前观察成立，但触发条件未完成 | 等待确认，不追涨 |
| `BREAKOUT_CONFIRMED` | 当日出现合同定义的突破确认 | 已出现启动确认，检查风险与板块支持 |
| `PULLBACK_HEALTHY` | 入选后回调，但结构和关键均线未破坏 | 正常回调观察，等待止跌/收复信号 |
| `TREND_ACCELERATING` | 趋势、相对强度和板块支持同步增强 | 已进入加速段，注意延伸和回撤风险 |
| `TOO_EXTENDED` | 距均线/波动延伸过大 | 位置偏高，不给出追入结论 |
| `SECTOR_DIVERGENCE` | 个股与原支持板块发生背离 | 单股强、板块弱或板块强、个股弱 |
| `STRUCTURE_DAMAGED` | 触发当时冻结的失效条件 | 原观察逻辑失效 |
| `DATA_UNAVAILABLE` | 当日数据或能力门不足 | 暂不判断，不沿用上一日结论冒充当前结论 |

每条状态必须同时显示：

- **事实**：发生了什么；
- **解释**：为何归入这个状态；
- **等待**：下一步需要确认什么；
- **失效**：什么情况说明原逻辑不再成立；
- **数据质量**：哪些数据缺失或仅为诊断重构。

## 6. 新菜单与页面设计

### 6.1 一级菜单

菜单名称：**关注跟踪**。

建议包含四个页签：

1. **正在关注**：当前仍在 CURRENT/EARLY 的个股和板块；
2. **后续走势**：已退出但仍处于 T+20 跟踪窗口的对象；
3. **历史事件**：所有已完成、失效或重入的 episode；
4. **统计复盘**：只做满足样本门的描述性统计。

### 6.2 正在关注列表

顶部概览：

- 数据交易日、在线最新交易日、publication 和算法版本；
- 当前关注个股数、提前观察个股数；
- 当前板块数、提前观察板块数；
- 今日新增、升级、降级、退出、重入数量；
- 数据状态与最后成功刷新时间。

个股列表建议列：

| 列 | 内容 |
|---|---|
| 当前状态 | 当前关注 / 提前观察 / 已退出跟踪 |
| 股票 | 名称、代码 |
| 首次关注 | 日期、已跟踪交易日数 |
| 今日场景 | 启动确认、强势回踩、修复转强、趋势延续、蓄势观察 |
| 研究状态 | 正常回调、直接加速、偏高、结构破坏等 |
| 自首次关注收益 | 百分比 |
| 期间最高 / 当前回撤 | 最大上行、距峰值回撤 |
| 原支持板块 | 名称与当前板块状态 |
| 个股相对板块 | 超额/落后，仅描述 |
| 等待 / 失效 | 精简原因，可展开 |
| 数据质量 | READY / DEGRADED / UNAVAILABLE |

板块列表建议列：

- 首次关注、当前/提前状态、持续天数；
- 板块收益、峰值回撤、宽度和强度变化；
- 进入当前关注的成员、仍有效成员、已退出成员；
- 提前观察成员升级率（仅样本事实，不称概率）；
- 板块状态变化时间线。

### 6.3 个股详情

详情采用三段式：

1. **当时为什么关注**：冻结当日理由、场景、板块支持、指标和风险；
2. **后来发生了什么**：K 线、首次关注线、升级线、退出线、原失效线、T+N 标记；
3. **现在怎么看**：当前研究状态、等待条件、失效条件、数据质量。

时间线示例：

```text
09-18 提前观察 NEW
09-21 升级当前关注 UPGRADED
09-22 趋势加速 TREND_ACCELERATING
09-24 回调但结构有效 PULLBACK_HEALTHY
09-28 跌破冻结失效条件 INVALIDATED
10-09 T+10 outcome 到期
```

### 6.4 板块详情

- 板块自身走势与宽度/强度曲线；
- 首次关注、升级、降级、退出节点；
- 当时成员快照与当前成员分开显示；
- 当时关注个股在后续的表现矩阵；
- 个股升级/退出不得反向修改历史板块成员快照。

### 6.5 统计复盘

统计必须遵守已有 Forward 约束：每组至少 30 条完整结果、至少 5 个独立信号交易日，才显示收益分位数和样本内正收益比例。

允许展示：

- 按清单类型、场景、持有观察期、板块支持状态分组；
- 中位收益、25%/75% 分位；
- 中位最大上行、中位最大回撤；
- 提前观察升级为当前关注的样本数量和比例；
- 数据不可用和未到期数量。

必须明确标注：描述性历史样本，不是未来上涨概率，不自动修改模型阈值。

## 7. 数据模型

### 7.1 设计原则

- 事实快照不可变；
- 事件状态通过追加 transition 表达，不覆盖过去；
- 当前状态是历史事件投影，可重建；
- 同日修订不冒充新交易日；
- 股票、板块采用统一实体模型，但各自事实表分开；
- JSON 只保存可变解释证据，核心筛选字段必须列式化；
- 所有时间使用 UTC 存储，业务日期使用 DATE，页面显示北京时间；
- 主键不用名称，股票用 security_id，板块用 sector_id。

### 7.2 PostgreSQL 核心表

#### `focus_runs`

记录一次完整、可查询的日跟踪发布。

关键字段：

```text
focus_run_id PK
trade_date
revision
publication_id
research_run_id
bundle_digest
snapshot_id
membership_snapshot_id
algorithm_contract_id
parameter_hash
dependency_lock_hash
status                 BUILDING / READY / FAILED
created_at_utc
completed_at_utc
error_code
UNIQUE(trade_date, revision)
```

#### `focus_daily_items`

冻结每日关注快照，一条记录表示某个对象在某个日运行中的状态。

```text
focus_run_id
entity_type            STOCK / SECTOR
entity_id
focus_type             CURRENT_FOCUS / EARLY_FOCUS / CURRENT_SECTOR / EARLY_SECTOR
rank
scenario_type
source_research_state   原研究算法当日输出，不由跟踪层改写
membership_state
episode_state
path_state
state_evaluation_id
quality_status
selection_reason_json
waiting_for_json
invalid_if_json
risk_codes_json
primary_sector_id      股票可用
metric_snapshot_json
evidence_json
PRIMARY KEY(focus_run_id, entity_type, entity_id, focus_type)
```

#### `focus_episodes`

```text
episode_id PK
entity_type
entity_id
first_trade_date
last_focus_trade_date
closed_trade_date NULL
initial_focus_type
latest_focus_type
episode_status
parent_episode_id NULL  重入时关联前一 episode
entry_reference_price NULL
entry_price_basis NULL
algorithm_contract_id
created_at_utc
```

#### `focus_episode_transitions`

```text
transition_id PK
episode_id
trade_date
from_state
to_state
reason_codes_json
focus_run_id
revision
created_at_utc
UNIQUE(episode_id, trade_date, revision, to_state)
```

#### `focus_episode_observations`

```text
episode_id
trade_date
source_revision
close_price
price_basis
return_since_first
return_since_current_entry
max_return_since_first
max_drawdown_since_first
drawdown_from_peak
ma5_position
ma10_position
ma20_position
ma60_position
rps5
rps20
amount_ratio
turnover_rate NULL
turnover_basis NULL
membership_state
episode_state
path_state
state_contract_id
parameter_set_id
state_evaluation_id
still_listed
primary_sector_state NULL
relative_to_primary_sector NULL
quality_status
metric_json
created_at_utc
PRIMARY KEY(episode_id, trade_date, source_revision)
```

#### `focus_episode_outcomes`

```text
episode_id
horizon                1 / 3 / 5 / 10 / 20
target_trade_date
target_revision
status                 PENDING / OBSERVED / DATA_UNAVAILABLE / SOURCE_REVISED
forward_return
max_upside
max_drawdown
evaluation_basis
observed_at_utc
PRIMARY KEY(episode_id, horizon, target_revision)
```

#### `focus_stock_sector_links`

冻结股票在每个关注日的板块支持关系。

```text
focus_run_id
security_id
sector_id
relation_type
support_status
loo_status
is_primary
evidence_json
PRIMARY KEY(focus_run_id, security_id, sector_id, relation_type)
```

#### `focus_current_projection`

由事件日志生成的当前投影，用于页面快速查询。它不是历史真相来源，可以重建。

```text
entity_type
entity_id
active_episode_id
latest_trade_date
latest_focus_type
latest_membership_state
latest_episode_state
latest_path_state
latest_state_evaluation_id
days_observed
still_listed
return_since_first
drawdown_from_peak
primary_sector_id
quality_status
updated_at_utc
PRIMARY KEY(entity_type, entity_id)
```

#### `algorithm_contracts` / `algorithm_parameter_sets`

保存不可变算法身份，不把阈值只写在代码里：

```text
contract_id PK
contract_family
contract_version
canonical_predicate_json
predicate_sha256
implementation_hash
dependency_lock_hash
price_basis
calendar_contract_id
status                  DRAFT / ACTIVE / RETIRED
created_at_utc
```

参数表以 `(parameter_set_id, parameter_name)` 为主键，保存 value、type、unit、闭开区间和来源说明。ACTIVE 合同及参数禁止 UPDATE。

#### `state_evaluations` / `state_evaluation_facts`

每次状态判断保存最终结果和完整判定过程：

```text
state_evaluation_id PK
episode_id
trade_date
source_revision
state_contract_id
parameter_set_id
evaluation_mode         AS_RECORDED / REINTERPRETED
membership_state
episode_state
path_state
quality_status
evidence_digest
created_at_utc
UNIQUE(episode_id, trade_date, source_revision, state_contract_id, evaluation_mode)
```

`state_evaluation_facts` 逐谓词保存 field、actual value、operator、threshold/anchor、TRUE/FALSE/UNKNOWN、reason code。页面解释和回放直接读取这些事实，不重新在 JavaScript 中推断。

### 7.3 索引

至少建立：

- `focus_daily_items(trade_date, focus_type, rank)`；
- `focus_episodes(entity_type, entity_id, first_trade_date DESC)`；
- `focus_episodes(episode_status, last_focus_trade_date DESC)`；
- `focus_episode_observations(episode_id, trade_date)`；
- `focus_episode_outcomes(status, target_trade_date)`；
- `focus_current_projection(still_listed, latest_focus_type, latest_trade_date DESC)`；
- `focus_stock_sector_links(security_id, focus_run_id)` 和 `(sector_id, focus_run_id)`。
- `state_evaluations(episode_id, trade_date DESC, evaluation_mode)`；
- `state_evaluation_facts(state_evaluation_id, predicate_id)`。

## 8. 存储与并发架构

### 8.1 推荐方案

```text
只读 TDX / 官方日包
        │
        ▼
冻结输入与 Parquet 历史层
        │
        ▼
离线计算进程（DuckDB 仅内存或临时库）
        │  输出 versioned staging files + manifest
        ▼
单一发布写入器
        │  一个 PostgreSQL 事务
        ▼
PostgreSQL 服务库
        │
        ├── API 查询
        ├── 关注跟踪页面
        └── 后台到期 outcome 任务
```

### 8.2 为什么选 PostgreSQL

- 原生支持多进程并发读写，不存在 DuckDB 单文件跨进程占用模型；
- 事务、唯一约束、行级锁、连接池和故障恢复更适合常驻页面服务；
- JSONB 可保存解释证据，普通列和索引可服务筛选排序；
- 后续可以在本机或局域网稳定运行；
- 比 MySQL 更适合当前大量日期、JSON、分析字段和可扩展视图需求。

MySQL 也能解决文件锁问题，但本项目大量使用 JSON 证据、日期快照和研究分析查询，PostgreSQL 更匹配。ClickHouse 等列式数据库适合海量追加分析，但当前数据量和事务性页面需求不值得增加第三套服务；Parquet 已足够承担列式历史层。

### 8.3 DuckDB 的保留边界

DuckDB 不必完全删除，但必须退出在线服务主路径：

- 可以读取 Parquet 进行大批量因子计算；
- 可以使用 `:memory:` 或每个任务独立临时库；
- 不允许页面 API 打开 DuckDB 生产文件；
- 不允许父服务与子进程共享同一个 DuckDB 文件；
- 计算结束只交付带摘要的 staging artifact，由 PostgreSQL 写入器导入；
- 临时库失败不影响已发布结果的读取。

### 8.4 发布一致性

完整发布顺序：

1. Phase 0 输入验收；
2. 冻结 trade date、source bundle、publication、算法和参数身份；
3. 离线计算输出 staging 文件及 manifest；
4. 校验行数、主键、空值、摘要、日期一致性；
5. 在一个 PostgreSQL 事务内写入日快照、episode transition、observation、到期 outcome；
6. 更新 `focus_run` 为 READY 和 current projection；
7. 事务提交后切换当前指针；
8. 页面缓存按 `focus_run_id` 失效。

任一步失败都不得让页面看到半成品。新任务失败时继续展示上一成功运行，并明确显示“最新生成失败 / 当前展示日期”。

## 9. 每日计算流程

```text
输入日期确认
 → 原有每日研究结果 READY
 → 提取股票/板块每日关注快照
 → 与上一成功交易日快照比较
 → 创建或延续 episode
 → 追加 NEW/PERSISTENT/UPGRADED/DOWNGRADED/EXITED 等 transition
 → 为所有未完成 episode 追加当日走势 observation
 → 结算到期 T+1/T+3/T+5/T+10/T+20 outcome
 → 原子发布关注跟踪运行
```

注意：

- “所有未完成 episode”包括已经退出清单但尚未完成 T+20 的对象；
- 某日没有行情时必须写 `DATA_UNAVAILABLE`，不能复制上一日价格；
- 当日重复执行必须幂等；
- 同日源变化创建 revision，不覆盖原记录；
- 周末或非交易日不推进 T+N；
- 本地数据日落后在线最新交易日时拒绝产生新的正式关注发布。

## 10. 状态算法、事件逻辑与防漂移合同

### 10.1 三层状态必须分开

上一版把“是否仍在榜”“价格后来怎么走”“系统现在怎样解释”混在一个 `research_state` 中，容易造成历史漂移。V2 强制拆成三层：

| 层 | 回答的问题 | 是否允许事后改变 |
|---|---|---|
| `membership_state` | 该日是否在 CURRENT/EARLY 清单 | 不允许；绑定当日 run/revision |
| `episode_state` | 从进入、升级、退出到重入处于哪一步 | 不允许覆盖；只能追加 transition |
| `path_state` | 截至该日，价格、强度和板块路径是什么状态 | 按当日冻结合同写入；新合同另写一条，不覆盖旧判断 |

页面必须同时显示三层。例如：`已退出清单 / EXITED_FOLLOW_UP / HEALTHY_PULLBACK`。退出清单不等于结构已经破坏，仍在清单也不等于位置适合追入。

### 10.2 冻结输入

每次状态计算必须绑定：

```text
trade_date
source_revision
focus_run_id
publication_id
research_run_id
bundle_digest
membership_snapshot_id
calendar_contract_id
price_basis
factor_contract_id
scanner_contract_id
state_contract_id
parameter_set_id
dependency_lock_hash
implementation_hash
```

输入事实只能来自该交易日及之前。每条 observation 保存本次实际消费的字段值及质量状态，不能只保存最终标签。

### 10.3 三值逻辑

所有谓词返回 `TRUE / FALSE / UNKNOWN`，禁止把 NULL 当 FALSE。

- 必需谓词为 UNKNOWN：状态降级为 `DATA_UNAVAILABLE`；
- 可选增强谓词为 UNKNOWN：保留基础状态，增加 `OPTIONAL_EVIDENCE_UNKNOWN`；
- 失效谓词为 UNKNOWN：不能宣称“仍有效”，显示 `VALIDITY_UNKNOWN`；
- 多条件 AND/OR 使用 SQL 三值逻辑，并把每个子谓词结果写入 evidence。

### 10.4 Episode 的确定性状态机

对实体 e 在交易日 t 定义：

```text
M_t ∈ {CURRENT, EARLY, NONE, UNKNOWN}
P_t = 上一成功交易日同一算法合同下的 membership
H_t = 历史上是否存在已经关闭的同实体 episode
```

状态迁移按下表执行，顺序不可调整：

| 条件 | transition | episode 处理 |
|---|---|---|
| `M_t=UNKNOWN` | `DATA_UNAVAILABLE` | 不关闭、不推进 miss session |
| `P_t=NONE 且 M_t∈{EARLY,CURRENT} 且 H_t=false` | `NEW` | 新建 episode |
| `P_t=NONE 且 M_t∈{EARLY,CURRENT} 且 H_t=true` | `REENTERED` | 新建 episode，绑定 parent episode |
| `P_t=EARLY 且 M_t=CURRENT` | `UPGRADED` | 延续原 episode |
| `P_t=CURRENT 且 M_t=EARLY` | `DOWNGRADED` | 延续原 episode |
| `P_t=M_t 且 M_t!=NONE` | `PERSISTENT` | 延续原 episode |
| `P_t∈{EARLY,CURRENT} 且 M_t=NONE` | `EXITED` | 结束清单成员阶段，进入后续观察 |
| 冻结失效谓词为 TRUE | `INVALIDATED` | 记录失效日，仍完成到期 outcome |
| T+20 全部结算且已退出/失效 | `FOLLOW_UP_COMPLETED` | 关闭 episode |

`EXITED` 与 `INVALIDATED` 可以同日发生，但分别保存：前者是榜单事实，后者是结构事实。数据缺失日不会制造退出；只有一个完整、同合同、成功发布的日运行才能判定 `M_t=NONE`。

### 10.5 模型升级与同日修订

- `state_contract_id`、scanner、参数或主要依赖变化时，写 `MODEL_BOUNDARY`；旧 episode 以 `MODEL_VERSION_ENDED` 关闭，新合同从当日建立 baseline，不把差异称为 NEW/EXITED。
- 同一交易日来源 revision 变化时写 `SOURCE_REVISED`；不得推进 T+N，不得制造跨日 transition。
- 同合同的显示层改版不创建事件；只更新页面资源版本。
- 如需用新合同重算旧日，只能写 `reinterpretation_version`，页面默认仍显示 `AS_RECORDED`，并把“按新规则重解释”单独展示。

### 10.6 个股事实定义

使用同一调整价口径：

```text
C_t                当日调整收盘
R_n(t)             C_t / C_{t-n} - 1
PEAK_t             max(C_j), j ∈ [episode.first_date, t]
RET_FROM_FIRST_t   C_t / C_first - 1
DD_FROM_PEAK_t     C_t / PEAK_t - 1
MFE_t              max(C_j / C_first - 1)
MAE_t              min(C_j / C_first - 1)
REL_SECTOR_t        个股自首次日收益 - 主支持板块同期收益
```

`C_first`、当时主支持板块、当时失效条件和突破平台均在 episode 建立时冻结。之后板块归属变化不得重写初始关系。

### 10.7 个股状态参数集 V1

首版参数集标识 `FOCUS_STOCK_PATH_PARAMS_V1_CANDIDATE`，属于待前瞻验证工程初值，不宣称最优：

| 参数 | 初值 | 用途 |
|---|---:|---|
| `PULLBACK_MIN` | 0.03 | 至少从 episode 后峰值回撤 3% 才叫回调 |
| `PULLBACK_MAX` | 0.12 | 超过 12% 不再标“健康回调” |
| `SIDEWAYS_SESSIONS` | 5 | 横盘判断窗口 |
| `SIDEWAYS_RANGE_MAX` | 0.08 | 5 日高低范围不超过 8% |
| `RPS_WEAKEN_SESSIONS` | 3 | RPS 连续下降观察窗口 |
| `SECTOR_DIVERGENCE_MIN` | 0.05 | 个股相对原板块偏离至少 5 个百分点才标明显背离 |
| `FOLLOW_UP_HORIZON` | 20 | 退出后正式观察到 T+20 |

这些值必须存入参数表并参与 hash。修改任何一个值都生成 V2 参数集，不允许原位修改。

### 10.8 个股失效谓词

失效不是一句文字，而是 episode 建立时编译并冻结的 predicate AST。按场景至少支持：

| 场景 | 冻结事实 | 失效条件示例 |
|---|---|---|
| `LAUNCH_CONFIRM` | 突破平台 `PHH20_signal` / `PHC20_signal` | 连续两交易日收盘低于冻结平台，或现有 `STRUCTURE_BREAK=true` |
| `STRONG_PULLBACK` | seed、episode peak、回调低点、确认日 MA | 跌破回调 episode 的冻结失效低点，或 `STRUCTURE_BREAK=true` |
| `RECOVERY_TURN` | 收复的 MA5/MA20 及确认价 | 连续两日重新落回对应均线下且 RPS 未改善 |
| `TREND_CONTINUE` | 信号日 MA20、趋势方向和关键低点 | `STRUCTURE_BREAK=true` 或收盘跌破冻结关键低点 |
| `SETUP_WATCH` | 等待突破价、等待量额条件、观察期限 | 超过观察期限未确认，或提前触发结构破坏 |

实现时不能解析自然语言 `invalid_if`。scanner 必须输出版本化结构，例如：

```json
{
  "op": "OR",
  "args": [
    {"field": "structure_break", "cmp": "EQ", "value": true},
    {"op": "CONSECUTIVE", "sessions": 2, "predicate": {"field": "close", "cmp": "LT", "anchor": "signal_phh20"}}
  ]
}
```

### 10.9 个股 `path_state` 决策表

先计算所有事实，再按以下固定优先级只选一个主状态，同时保留所有副标签：

| 优先级 | 主状态 | 完整判定 |
|---:|---|---|
| 1 | `DATA_UNAVAILABLE` | 当日无 actual bar，或所需价格/日历/因子质量为 UNKNOWN |
| 2 | `STRUCTURE_DAMAGED` | 冻结失效 AST 为 TRUE；保存命中的具体叶节点 |
| 3 | `TOO_EXTENDED` | 现有锁定合同 `EXTENDED=true`；V1 不另造第二套延伸阈值 |
| 4 | `DIRECT_ADVANCE` | `MFE>=PULLBACK_MIN` 且首次日至今从未出现 `DD_FROM_PEAK<=-PULLBACK_MIN`，并且当前价不低于峰值 3% |
| 5 | `PULLBACK_HEALTHY` | `DD_FROM_PEAK∈[-PULLBACK_MAX,-PULLBACK_MIN]`，`C_t>=MA20_t`，`STRUCTURE_BREAK=false`，失效 AST 为 FALSE |
| 6 | `PULLBACK_UNCONFIRMED` | 满足回撤区间，但 `C_t<MA20_t` 或必要确认谓词未成立，且尚未失效 |
| 7 | `BREAKOUT_CONFIRMED` | 当日原 scanner 的 `LAUNCH_CONFIRM=true`，且状态质量 READY |
| 8 | `TREND_ACCELERATING` | 原 scanner 的 `TREND_CONTINUE=true`，`R_5>0`、`RPS20_delta3>=0`，且当前主支持板块为 CURRENT；任何必需项 UNKNOWN 则不成立 |
| 9 | `SECTOR_DIVERGENCE` | 原主支持板块不再 CURRENT，且 `abs(REL_SECTOR)>=SECTOR_DIVERGENCE_MIN`；副标签注明个股领先或落后 |
| 10 | `SIDEWAYS_WAIT` | 最近 5 个真实交易日 `max(H)/min(L)-1<=SIDEWAYS_RANGE_MAX`，未失效、未突破 |
| 11 | `WEAKENING` | `C_t<MA20_t` 或 RPS20 连续 3 个可比交易日下降，但尚未命中冻结失效条件 |
| 12 | `WAIT_CONFIRMATION` | EARLY/SETUP 对象未命中以上状态且等待谓词仍可评估 |
| 13 | `EXITED_FOLLOW_UP` | 已退出清单、未失效、未满足其他更高优先级路径状态 |

关键说明：

- `DIRECT_ADVANCE` 只描述“未明显回调而持续上行”，不等于可追入；
- `PULLBACK_HEALTHY` 只说明冻结结构尚未破坏，不等于买点；
- `TOO_EXTENDED` 优先于加速，避免把过热位置只显示成强势；
- `WEAKENING` 与 `STRUCTURE_DAMAGED` 分开，避免一次走弱立即被判彻底失效；
- `EXITED_FOLLOW_UP` 不是兜底覆盖其他事实，若退出后发生健康回调仍显示健康回调并附 `LIST_EXITED`。

### 10.10 板块事实定义

板块收益首版继续使用同一 publication、当日冻结成员的个股收益中位数，不冒充官方板块指数：

```text
SRET1_t       当日有效成员 RET1 中位数
SWIDTH_t      满足板块强势条件的有效成员数 / 可评成员数
SREL_t        板块成员收益中位数 - 同日正常股票全集收益中位数
SPEAK_t       episode 内累计板块指数化净值最高点
SDD_t         当前指数化净值 / SPEAK_t - 1
RETENTION_t   上一可比日强势成员在本日仍强势的比例
```

跨日宽度/保留率只有在成员集合交并比、覆盖率和共同成员门通过时才可比较，否则为 UNKNOWN。

### 10.11 板块状态参数集 V1

参数集 `FOCUS_SECTOR_PATH_PARAMS_V1_CANDIDATE`：

| 参数 | 初值 | 用途 |
|---|---:|---|
| `SECTOR_PULLBACK_MIN` | 0.02 | 从 episode 峰值至少回撤 2% |
| `SECTOR_PULLBACK_MAX` | 0.08 | 健康板块回调上限 |
| `WIDTH_DROP_WARN` | 0.15 | 宽度较信号日下降 15 个百分点为扩散转弱提示 |
| `RETENTION_WARN` | 0.50 | 强势成员保留率低于 50% 为内部转弱提示 |
| `MEMBER_JACCARD_MIN` | 0.90 | 跨日成员集合可比门 |
| `COVERAGE_MIN` | 0.80 | 板块指标最低覆盖 |
| `SECTOR_MISS_TOLERANCE` | 1 | 允许一次合格发布中的短暂掉榜，再确认退出；明确失效除外 |

### 10.12 板块 `path_state` 决策表

| 优先级 | 主状态 | 完整判定 |
|---:|---|---|
| 1 | `DATA_UNAVAILABLE` | 覆盖不足、成员不可比或必要板块事实 UNKNOWN |
| 2 | `SECTOR_STRUCTURE_DAMAGED` | 冻结板块失效谓词 TRUE，或 CURRENT/POTENTIAL 均 FALSE 且 `SREL<0`、`SWIDTH` 低于合同硬门 |
| 3 | `SECTOR_ACCELERATING` | CURRENT=true，`SRET1>0`、`SREL>0`、`SWIDTH` 较前日不下降、`RETENTION>=RETENTION_WARN` |
| 4 | `SECTOR_HEALTHY_PULLBACK` | `SDD∈[-SECTOR_PULLBACK_MAX,-SECTOR_PULLBACK_MIN]`、CURRENT 或 POTENTIAL=true、`SREL>=0`、覆盖门通过 |
| 5 | `SECTOR_DIFFUSION_WEAKENING` | 宽度较信号日下降至少 `WIDTH_DROP_WARN`，或 `RETENTION<RETENTION_WARN`，但尚未失效 |
| 6 | `SECTOR_ROTATION` | 板块仍合格，但原领涨成员退出且新领涨成员进入；成员可比门必须通过 |
| 7 | `SECTOR_EARLY_WAIT` | POTENTIAL=true、CURRENT!=true，等待分支尚未失效 |
| 8 | `SECTOR_PERSISTENT` | CURRENT=true 且不满足以上变化状态 |
| 9 | `SECTOR_EXITED_FOLLOW_UP` | 已退出板块清单但仍在 T+20 观察期 |

板块掉榜采用一次成功交易日容忍，避免因单日边界抖动频繁开关 episode；但明确结构失效不使用容忍。被容忍的中间日标记 `PROVISIONAL_MISS`，若下一可比日恢复则 transition 为 `PERSISTENT_AFTER_MISS`，若仍未恢复则退出日回溯锚定为首次 miss 日，但记录的事实不可改写。

### 10.13 个股—板块联动状态

联动只用 episode 首日冻结的 primary sector，同时展示当前其他支持关系：

| 个股 | 原板块 | 联动标签 |
|---|---|---|
| 强 / 加速 | 强 / 加速 | `STOCK_SECTOR_CONFIRMED` |
| 强 / 加速 | 转弱 / 退出 | `STOCK_LEADING_WEAK_SECTOR` |
| 转弱 | 强 / 加速 | `STOCK_LAGGING_STRONG_SECTOR` |
| 回调健康 | 回调健康 | `SYNCHRONIZED_PULLBACK` |
| 结构破坏 | 任意 | `STOCK_INVALIDATED` |
| 任意 | 结构破坏 | `ORIGINAL_SECTOR_INVALIDATED` |
| 任一 UNKNOWN | 任意 | `LINKAGE_UNKNOWN` |

不能因为股票后来加入另一个强板块而重写首次关注时的支持来源；新关系只作为当日新增证据。

### 10.14 到期结果与退出规则

- T+1/T+3/T+5/T+10/T+20 均从 episode 首次关注交易日计算；升级为 CURRENT 另建一组 `upgrade_anchor` outcome，但不覆盖 first-anchor outcome。
- EXITED、INVALIDATED 后仍结算已计划 outcome。
- episode 正式结束条件：已退出/失效，T+20 已 OBSERVED 或明确 DATA_UNAVAILABLE，且无未处理 revision。
- 对仍持续关注超过 20 日的对象，episode 保持活动；每 20 个交易日建立只读 milestone，不切断生命周期。
- 同一股票同时命中多个场景时，主场景沿现有 ranking contract；其他场景作为副标签，不开多个重叠 episode。

### 10.15 防状态漂移机制

新增以下表或等价实体：

```text
algorithm_contracts
algorithm_contract_dependencies
algorithm_parameter_sets
state_predicate_definitions
state_evaluations
state_evaluation_facts
state_reinterpretations
```

硬约束：

1. 合同发布后不可 UPDATE，只能新增版本；
2. predicate 以规范化 JSON AST 保存并计算 SHA-256；
3. 参数、源码、依赖、日历、价格口径、数值库版本共同进入 `dependency_lock_hash`；
4. 每个标签必须能反查实际字段值、比较符、阈值和 TRUE/FALSE/UNKNOWN；
5. 页面默认读取 `AS_RECORDED`；新规则历史重算只能进入 `state_reinterpretations`；
6. 合同版本改变时不得继续原 episode 并把差异解释成市场变化；
7. 回放测试必须验证同输入、同依赖锁得到相同逻辑摘要；
8. 浮点比较采用合同化精度与容差，不依赖页面格式化值；
9. 状态统计按合同版本分组，禁止跨版本直接合并；
10. 人工修订只能追加审计事件，不能编辑算法结果。

状态只描述事实，不自动决定交易。回调不等于买点，直接主升不等于仍适合追入，退出清单不等于必须卖出，样本内表现不等于未来概率。

## 11. API 设计

建议新增只读接口：

```text
GET /api/v3/focus-tracker/summary
GET /api/v3/focus-tracker/items
GET /api/v3/focus-tracker/episodes/{episode_id}
GET /api/v3/focus-tracker/stocks/{security_id}
GET /api/v3/focus-tracker/sectors/{sector_id}
GET /api/v3/focus-tracker/transitions
GET /api/v3/focus-tracker/statistics
GET /api/v3/focus-tracker/runs
```

列表接口统一支持：

- `as_of_date`、`focus_type`、`membership_state`、`episode_state`、`path_state`；
- `sector_id`、`scenario_type`、`quality_status`；
- 首次关注日期范围；
- 收益、回撤和持续天数排序；
- 游标或页码分页；
- 每次响应返回 `focus_run_id`、trade date、revision 和数据状态。

错误响应统一包含：

```json
{
  "code": "FOCUS_TRACKER_DATA_UNAVAILABLE",
  "message": "关注跟踪数据暂不可用，当前仍展示上一成功交易日",
  "retryable": true,
  "display_trade_date": "2026-09-18",
  "requested_trade_date": "2026-09-21"
}
```

API 只查询 PostgreSQL，不在请求过程中启动 DuckDB、扫描 Parquet 或调用在线行情。

## 12. 数据保留策略

- 每日关注快照、episode、transition、T+N outcome：长期保存；
- 支撑最终解释的核心指标和身份：长期保存；
- 大体量逐日行情和因子：Parquet 分区保存；
- 页面投影和缓存：可重建，有界清理；
- staging 文件：发布成功并完成摘要核验后按策略清理；
- 原始来源继续遵守现有三交易日与审计保留合同；
- 删除缓存不得删除 episode、transition 和 outcome。

## 13. 现有生产数据全量迁移到 PostgreSQL

### 13.1 迁移目标与边界

迁移不是只创建关注跟踪新表，而是把当前生产 DuckDB 中仍被服务、生成任务、历史查询、运维和审计使用的全部数据与行为迁到 PostgreSQL。迁移完成后：

- PostgreSQL 是任务、输入身份、publication、研究结果、关系、在线封存、Forward、运维和关注跟踪的唯一在线主库；
- 页面和常驻服务不再打开 `market_research.duckdb`；
- DuckDB 只在离线任务内读取 Parquet 或任务独立临时库；
- 旧 DuckDB 作为只读迁移证据保留，未获得逐表删除授权前不删除；
- TDX 输入目录继续只读，不进入数据库迁移写范围。

### 13.2 迁移对象不只包括数据库表

完整迁移集合分四类：

1. **DuckDB 表、索引、约束及 schema migration 身份**；
2. **数据库引用的外部文件**：Parquet 结果对象、bundle、manifest、receipt、备份 catalog 对象；
3. **当前指针**：publication head、analysis snapshot binding、active research bundle 等；
4. **读写程序**：API、publisher、research builder、运维、备份、迁移、历史任务和脚本。

外部文件本身不必全部写入 PostgreSQL 大字段，但其路径、摘要、大小、合同、引用状态和可用性必须迁移并重新核验。不能只搬数据库行而留下失效路径。

### 13.3 表域迁移清单

在 P0 必须从真实生产库 `information_schema` 生成最终清单；下表是基于当前 schema 和 007—035 migrations 的最低范围，不能作为遗漏其他真实表的理由。

| 域 | 现有表族 | PostgreSQL 处理 |
|---|---|---|
| schema/审计 | `schema_migrations`、`schema_migration_checks`、`audit_receipts` | 一对一迁移；另建 PG migration ledger，保留原 DuckDB migration hash |
| 任务 | `jobs`、`job_attempts`、`job_events` | 一对一迁移；状态枚举和唯一键保持 |
| 输入 | `source_packages`、`source_files`、`metadata_snapshots`、`source_bundles` | 一对一迁移；JSON 转 JSONB；补路径可用性检查 |
| 发布 | `publications`、`publication_heads`、`publication_artifacts`、`publication_memberships` | 一对一迁移；head 外键延后校验；历史 revision 全保留 |
| 基础结果 | `market_daily`、`sector_daily`、`stock_daily`、`candidate_daily`、`structure_details`、`queue_memberships`、`queue_rankings`、`unified_board` | 一对一迁移；保持 publication 复合唯一键和 Decimal 精度 |
| 旧关系 | `membership_snapshots`、`membership_entries` | 保留迁移；不能因新 relation 表存在而丢弃历史兼容证据 |
| V3 关系 | `relation_revisions`、`relation_edge_intervals`、`relation_observations`、`relation_snapshot_bindings`、`relation_publication_bindings`、`sector_attribute_*` | 一对一迁移；先 revision/attribute，再 edge/observation，最后 binding |
| 分析身份 | `analysis_slices`、`analysis_slice_dependencies`、`analysis_snapshots`、`analysis_snapshot_entries`、`publication_analysis_snapshots`、`analysis_daily_basis` | 一对一迁移；保持依赖拓扑和逻辑摘要 |
| 结果对象 | `analysis_result_objects`、`analysis_slice_result_bindings` 及 technical/strength/high/member/structure result rows | 元数据和行表迁移；物理对象逐个校验 sha256 和可读性 |
| M8/M9/M10 | `stock_technical_daily`、`stock_strength_daily`、`stock_high_daily`、`sector_base_daily`、`historical_coverage_daily`、`historical_structure_daily`、`stock_structure_summary_daily`、`sector_cycle_daily`、`sector_member_state_daily`、`sector_membership_changes`、`representative_state_daily`、`mainline_daily` | 全量迁移；这些旧/辅助表仍有兼容读取，不能跳过 |
| M11/M13 | `stock_sector_associations_daily`、`limit_ladder_daily`、`limit_promotion_daily`、`market_cycle_daily` | 全量迁移；保留 append-only/有界 writer 语义 |
| 日历/证券/规则 | `membership_snapshot_metadata`、`sector_semantic_versions`、`security_metadata_versions`、`universe_state_daily`、`market_reference_daily`、`limit_rule_versions`、`tdx_sector_hierarchy_*`、`analysis_snapshot_hierarchy`、M8C audit 表 | 全量迁移；保留时点、来源和审计状态 |
| 研究运行 | `research_runs`、`research_stock_states`、`research_sector_states`、`research_sector_signal_state`、`research_sector_member_roles`、`research_shortlist`、`research_signal_outcomes` | 全量迁移；先 run，再各状态与 outcome |
| V3.3 registry | `research_runs_v3_3`、`research_candidates_v3_3` | 全量迁移；bundle path 重新做文件引用核验 |
| 在线持久化 | `data_sources`、`online_fetch_runs`、`online_payloads`、`online_batches`、`online_rank_entries`、`online_security_map`、`online_evidence`、`online_quote_entries`、V3 online event 表 | 按各数据集保留合同迁移；热榜 request-time-only 数据不得因迁移而新增持久化 |
| Forward | `observations`、`outcomes`、`state_transitions` 及研究 signal outcomes | 全量迁移；append-only、revision、T+N 身份不变 |
| 运维 | `config_versions`、`storage_objects`、`leases`、`cleanup_jobs`、`backup_catalog` | 全量迁移；路径合法性和引用关系重验；旧 DuckDB 备份 catalog 标记 source engine |
| 新关注跟踪 | 第 7、10 节定义的 focus/contract/evaluation 表 | 在 PostgreSQL 原生创建，不先写回 DuckDB |

### 13.4 每张表的迁移分类

P0 生成 `database_migration_catalog.json`，每张真实表必须且只能属于一种类别：

```text
COPY_1_TO_1          结构和数据直接映射
COPY_WITH_CAST       需显式类型转换
TRANSFORM_SPLIT      一个旧表拆成多个新表
TRANSFORM_MERGE      多个旧表形成一个投影，但旧表仍原样留存
REBUILD_PROJECTION   可从不可变事实重建的 current/cache 表
RETAIN_EXTERNAL      数据保留在 Parquet/对象文件，PG 迁移 catalog 与引用
EXCLUDE_BY_CONTRACT  明确禁止迁移，必须写原因和证据
```

没有分类、没有主键、没有消费者盘点或摘要算法的表不得进入切换。

### 13.5 类型映射

| DuckDB | PostgreSQL | 规则 |
|---|---|---|
| `VARCHAR` | `text` / 有长度约束的 `varchar` | 主键标识统一 text；不截断 |
| `BOOLEAN` | `boolean` | NULL 保留，不转 false |
| `DATE` | `date` | 不带时区 |
| `TIMESTAMP` | `timestamptz` 或 `timestamp` | 事件时间统一 timestamptz/UTC；业务本地时间需显式转换 |
| `BIGINT/INTEGER` | `bigint/integer` | 导入前验证范围 |
| `DOUBLE` | `double precision` | NaN/Inf 必须按合同转 NULL 或阻断，不能静默写入 JSON |
| `DECIMAL(p,s)` | `numeric(p,s)` | 保持金额精度，不经 float 中转 |
| `JSON` | `jsonb` | 导入前规范化；摘要仍按跨引擎 canonical JSON 计算 |
| list/struct | `jsonb` 或规范化子表 | 用途可查询则拆表；纯证据才保留 JSONB |

DuckDB 的 `INSERT OR REPLACE`、宽松 GROUP BY、日期函数、list/struct、JSON 函数、`read_parquet` 和 `QUALIFY` 等语义不得直接复制；必须经过 repository 方言适配和合同测试。

### 13.6 跨引擎逻辑摘要

数据库字节哈希不可比较。为每张表定义 engine-neutral 摘要：

1. 固定列顺序和主键排序；
2. DATE 使用 `YYYY-MM-DD`；时间统一 UTC ISO-8601 微秒；
3. NULL 使用独立类型标记，不等同空字符串；
4. Decimal 按固定 scale 文本化；
5. float 使用合同化十六进制或精确规范化方法，禁止页面两位小数；
6. JSON 递归排序 key、保留数组顺序、拒绝 NaN/Inf；
7. 字符串 UTF-8 NFC 规范化，长度进入编码；
8. 每行做 SHA-256，再按主键顺序滚动聚合；
9. 同时保存 row count、NULL count、min/max date、主键 distinct count。

大表除全表逻辑摘要外，必须按 trade_date/publication/slice 分区摘要，便于定位差异。只对行数不能算迁移成功。

### 13.7 迁移元数据表

PostgreSQL 新增：

```text
migration_runs
migration_table_catalog
migration_table_attempts
migration_partition_checks
migration_reference_checks
migration_consumer_cutovers
migration_rollback_events
```

每次迁移记录源 DuckDB 文件 SHA-256、离线副本 SHA-256、源 schema 摘要、目标 schema version、开始/完成时间、程序版本、逐表结果和最终接受状态。

### 13.8 程序访问层改造

当前存在大量 `duckdb.connect()` 直连点，不能只迁数据不迁代码。所有生产读写入口必须归入以下适配器：

```text
Repository                 基础 publication/结果
ResearchRepository         research run/shortlist/sector state
RelationRepository         V3 relation/attribute
OnlineEvidenceRepository   允许持久化的在线证据
OperationsRepository       config/storage/backup/job
FocusTrackerRepository     新关注跟踪
ArtifactCatalog            Parquet/bundle/object 引用
```

迁移规则：

- API 层禁止出现数据库方言 SQL；
- 生产脚本禁止硬编码 `market_research.duckdb`；
- `--database-url` 或统一配置注入 repository；
- Parquet 扫描保留在离线计算适配器，不通过 PostgreSQL API 请求临时扫描；
- 每个现有直连点必须登记为 `MIGRATED`、`OFFLINE_DUCKDB_ALLOWED` 或 `RETIRED`；
- 未登记的生产直连点使切换门 BLOCKED。

### 13.9 全量迁移执行顺序

#### PGM-00：只读盘点与 Phase 0

- 完成 Phase 0：`FULL_PASS / DEGRADED_PASS / BLOCKED`；
- 从真实库导出表、列、约束、索引、行数、日期范围和消费者清单；
- 对所有外部对象建立引用图；
- 记录 DuckDB 版本、扩展、文件大小和 SHA-256；
- 输出迁移 catalog，不写生产库。

#### PGM-01：PostgreSQL 基础设施

- 专用 database、owner、runtime role、migration role、backup role；
- 本机仅监听需要的地址，密码/连接串不写入仓库；
- schema migration 工具、连接池、statement timeout；
- UTC、locale、collation、numeric/JSON 行为验收；
- 建立备份并完成真实恢复演练。

#### PGM-02：建立目标 schema

- 按依赖顺序创建表、主键、唯一约束和必要 CHECK；
- 大批量导入前可延后非唯一索引与部分外键，但不能省略；
- DuckDB 原 migration 作为历史证据导入，新 PG migration 使用独立命名空间；
- 新 focus 表同时创建，但不生成历史算法状态。

#### PGM-03：冻结源副本

- 进入维护窗口，停止新任务并等待活动写入结束；
- 关闭所有 DuckDB 连接；
- 创建经试开验证的一致性备份副本；
- 后续全量导出只读该副本，不读取变化中的活动文件；
- 活动服务可恢复，但迁移期间新增量进入后续 delta 阶段。

#### PGM-04：分域全量导出与导入

推荐顺序：

```text
身份/合同/配置
 → 输入/source bundle
 → publication 与成员身份
 → 基础 market/sector/stock 结果
 → analysis slice/snapshot/result object
 → relation revision/edge/observation/binding
 → M8-M13 结果与旧兼容表
 → research run/state/shortlist/V3.3 registry
 → online allowed datasets
 → Forward observation/outcome
 → jobs/events/storage/backup catalog
 → current heads/projections
```

导出使用版本化 Parquet/CSV staging，manifest 保存列、类型、行数、摘要和源 SQL。导入以分区事务执行；失败只回滚当前分区，修复后使用幂等键重放。

#### PGM-05：增量追平

不做长期双写。全量迁移期间如 DuckDB 服务继续运行，则通过不可变时间/主键边界追平新增数据：

- publication 按 created_at + publication_id；
- append-only 表按主键/sequence；
- current head、config、storage projection 最后重新读取；
- 无可靠增量边界的表必须在最终维护窗口重新全量比较或重导；
- delta 导入后再次计算全表/分区摘要。

#### PGM-06：影子双读

- API 测试环境对同一请求分别查 DuckDB 与 PostgreSQL；
- 比较响应语义，不比较无意义的行顺序或序列化格式；
- 覆盖 publications、dashboard、sectors、stocks、queues、linkage、research、online evidence、jobs、operations；
- 任何经济值、身份、成员集合、排名或状态差异必须形成差异单；
- 影子双读只读，不在两个数据库同时生产写入。

#### PGM-07：最终切换窗口

1. 阻止新任务；
2. 排空活动任务；
3. 关闭 DuckDB 所有连接；
4. 创建最终一致性备份；
5. 导入最终 delta；
6. 完成逐表摘要、引用、关键 API 和恢复前检查；
7. 配置切换为 PostgreSQL；
8. 重启服务；
9. 执行只读 smoke；
10. 执行一项受控、可回滚的测试写入并验证任务状态；
11. 解除维护窗口。

#### PGM-08：观察与回退期

- 旧 DuckDB 保持只读，不接受新写入；
- PostgreSQL 每日备份、连接池和错误率持续检查；
- 至少经过约定数量的真实交易日和一次完整日生成；
- 任何回退必须停止 PG 新写入，明确处理 PG-only 新数据，不能直接把旧 DuckDB 当作最新；
- 回退方案是“导出 PG 增量并经合同导回兼容库”或“恢复切换前状态并声明期间数据未合并”，由故障等级决定。

#### PGM-09：DuckDB 在线退役

- 代码扫描证明页面/API/常驻服务无生产 DuckDB 直连；
- 所有脚本入口完成分类；
- 旧库、备份和迁移回执进入只读归档；
- 是否删除旧表或数据库必须另行得到逐项授权，本设计不授权删除。

### 13.10 外部文件和路径迁移

对于 `analysis_result_objects`、V3.3 bundle、Parquet 历史、manifest：

- 优先保持物理文件不动，只迁 catalog；
- 路径存储为 managed-root + relative path，不固化临时绝对路径；
- 每个对象检查存在、大小、SHA-256、合同、引用者和可读性；
- 丢失对象不因数据库行已迁移而标记成功；
- 旧路径更换时先复制到新受管根、核验，再原子切换 catalog；
- TDX 根永远不作为迁移目标或受管写目录。

### 13.11 不做伪历史回填

关注跟踪上线前的历史可以分两类：

- 已有不可变 `research_shortlist` / sector state / publication 的日期：允许构建 `HISTORICAL_RECONSTRUCTED` episode，但必须标注重构合同和历史能力；
- 缺少当时成员、当时 universe、当时算法依赖或状态事实的日期：只迁原数据，不生成伪 episode。

正式 `REAL_FORWARD` 关注生命周期从功能上线后的第一个成功交易日开始。重构历史不能与真实前瞻样本合并统计。

### 13.12 切换门

满足全部条件才能把 PostgreSQL 设为主库：

- 真实表 catalog 覆盖率 100%；
- 仍被引用表迁移成功率 100%；
- 主键重复 0、必需外键孤儿 0；
- 所有关键分区 row count 与逻辑摘要一致；
- current head、active bundle、latest successful publication 身份一致；
- 外部对象引用全部为 AVAILABLE 或有明确允许的降级；
- 生产直连点盘点覆盖率 100%；
- 关键 API 双读语义一致；
- PG 备份恢复演练通过；
- 最终维护窗口回执为 `FULL_PASS`；
- 回退演练通过。

## 14. 可靠性与降级

### 14.1 页面可用性

- 数据计算中：继续展示上一 READY 版本并显示构建中；
- 今日生成失败：展示失败原因，同时保留上一版本；
- PostgreSQL 短暂不可用：返回统一 503，不回退读取 DuckDB；
- 某个指标缺失：局部标记 UNKNOWN，不让整页崩溃；
- 图表失败：表格和文字时间线仍可用。

### 14.2 监控

记录：

- 最近成功 focus run；
- 当前展示日期与在线最新日期差；
- READY/FAILED 运行数量；
- episode transition 数量异常；
- 待结算 outcome 数量和逾期数量；
- API P50/P95 延迟、连接池占用、数据库错误率；
- staging 导入摘要与 PostgreSQL 逻辑摘要。

### 14.3 备份

- PostgreSQL 每日一致性备份；
- 定期恢复演练，而不只检查备份文件存在；
- 备份记录 schema version、最大 trade date、关键表计数和摘要；
- Parquet manifest 与 PostgreSQL 身份交叉校验。

## 15. 验收标准

### 15.1 功能验收

- 某股票提前观察后退出，仍可从“后续走势”找到；
- 提前观察升级当前关注，时间线只有一个连续 episode 和一个 UPGRADED transition；
- 退出后重入，产生新 episode 且能关联旧 episode；
- 股票详情能同时显示首次关注事实、后续走势和当前研究状态；
- 板块退出后，其原关注股票仍能继续跟踪；
- T+N 严格使用后续交易日；
- 日期落后时页面明确显示展示日，不冒充今天。

### 15.2 数据验收

- 每个 READY focus run 与对应 research run、publication、bundle digest 一致；
- 每日快照主键无重复；
- transition 可从连续快照确定性重建；
- current projection 可从 episode 和 transition 全量重建并摘要一致；
- 任何历史修订不覆盖旧 revision；
- 缺数据不生成伪价格、伪收益或伪状态。
- 每个 `path_state` 能反查 predicate AST、实际输入值、阈值、比较结果和合同版本；
- 同输入、同依赖锁重复回放的 transition、state 和逻辑摘要完全一致；
- 模型换版只产生 `MODEL_BOUNDARY`，不产生伪 NEW/EXITED；
- `AS_RECORDED` 与历史重解释分表、分版本，旧状态没有被覆盖；
- 个股失效锚、原支持板块和首次参考价在 episode 期间保持冻结。

### 15.3 并发与故障验收

- 页面并发读取期间离线计算可正常运行；
- 计算子进程崩溃不影响上一发布版本查询；
- PostgreSQL 写入事务中断不出现半发布；
- 页面 API 进程中不存在生产 DuckDB 文件连接；
- 连续重复执行同日任务结果幂等；
- 服务重启后任务和关注事件状态可恢复。

### 15.4 性能目标

- 列表查询 P95 小于 500ms；
- 个股/板块详情 P95 小于 800ms；
- 首页不查询全量历史，不超过约定分页；
- 单日关注发布写入在明确超时内完成；
- 统计页使用预聚合或异步物化，不阻塞日常页面。

### 15.5 全库迁移验收

- 真实生产表、视图、索引、约束和直连消费者盘点覆盖率 100%；
- 第 13.3 节所有仍被引用表均有明确分类、迁移结果和摘要；
- DuckDB 与 PostgreSQL 逐表/逐分区 row count、NULL count、主键 distinct 和逻辑摘要一致；
- publication head、active research bundle、analysis snapshot、relation binding 全部一致；
- Parquet、bundle、manifest 和结果对象引用不存在未解释丢失；
- 关键 API 影子双读通过；
- PG 备份恢复、最终切换和故障回退演练通过；
- 切换后代码扫描确认 API、publisher、运维与每日生成不再直连生产 DuckDB；
- 旧 DuckDB 只读归档，未执行未经授权的删除。

## 16. 实施顺序建议

1. `PGM-00`：完成真实生产库、外部对象和所有 DuckDB 直连点盘点；
2. 冻结 `FOCUS_TRACKER_CONTRACT_V2`、predicate AST、参数集和跨引擎摘要合同；
3. `PGM-01/02`：建立 PostgreSQL、权限、schema、备份和恢复演练；
4. 改造 repository 边界，禁止 API 和生产任务散落数据库方言 SQL；
5. `PGM-03/04/05`：离线一致性副本全量迁移、增量追平和逐域核验；
6. `PGM-06`：关键接口影子双读，无长期生产双写；
7. `PGM-07`：维护窗口完成 PostgreSQL 主库切换；
8. 在 PostgreSQL 上实现 focus snapshot、episode、transition 和状态评估；
9. 完成每日 observation、退出后 T+20 和升级锚 outcome；
10. 开发“关注跟踪”菜单、股票/板块详情和联动时间线；
11. 经过真实交易日观察后开放统计复盘；
12. `PGM-08/09`：完成观察期，将 DuckDB 从所有在线路径退役并只读归档。

不建议在 PostgreSQL 只建新功能表后长期维持两套生产主库。短期迁移窗口可以旁路验证，但正式上线关注跟踪前，应先完成核心 publication、research、relation、Forward 和运维域迁移，保证新功能不会反过来依赖仍可能被锁住的 DuckDB。统计复盘在真实样本积累后开放。

## 17. 待确认的产品选择

实施前需要最终确认但不影响本设计评审的选项：

1. “关注跟踪”默认展示最近 20、40 还是 60 个交易日；建议默认 20，历史可搜索；
2. 退出后跟踪到 T+20 即结束，还是结构未失效时继续到 T+60；建议正式结果到 T+20，T+60 仅诊断；
3. 板块走势使用成员收益中位数，还是未来接入独立板块指数；首版沿用成员收益中位数并明确标签；
4. PostgreSQL 是随本机服务安装，还是连接已有实例；建议先使用本机独立实例和专用数据库/账号；
5. 是否允许用户手工添加“个人关注”；建议作为后续独立来源，不与算法关注混合，字段标记 `source_type=MANUAL`。

## 18. 风险与约束

- 历史成员关系不完整时，不能把当前成员回填成历史 PIT 成员；
- 同一股票多板块归属会形成机会数量偏差，必须保留当日冻结关系和 LOO 证据；
- 复权锚变化可能影响跨期收益，outcome 必须绑定评价日可复现的价格口径；
- 算法升级造成榜单变化时，不能全部解释成市场变化；
- 换手率分母未核实时只能展示事实能力状态，不能用作必需门；
- 样本不足时统计页不显示胜率式结论；
- 数据库迁移期间禁止双写后静默忽略差异，所有差异必须形成独立审计项。

## 19. 与现有合同的关系

本设计复用但不替代以下合同：

- `TODAY_RESEARCH_*_V3_3`：决定每日候选和解释；
- `R4_FORWARD_OBSERVATION_CONTRACT_V1`：提供 forward-only、不可覆盖和交易日 T+N 原则；
- `FORWARD_EVALUATION_CONTRACT_V1`：提供样本门与描述性统计限制；
- `DATA_STATE_SEMANTICS_CONTRACT_V1`：约束缺失数据和停牌语义；
- `P12_DAILY_DATABASE_PROCESS_OWNERSHIP_REPAIR_V3`：作为迁移完成前的 DuckDB 临时并发保护；
- `P12_DAILY_EXPECTED_TRADE_DATE_V1`：继续阻止旧日期被静默发布为今日数据。

本设计新增的核心合同建议为：

- `FOCUS_DAILY_SNAPSHOT_CONTRACT_V2`；
- `FOCUS_EPISODE_LIFECYCLE_CONTRACT_V2`；
- `FOCUS_PATH_STATE_CONTRACT_V1`；
- `FOCUS_STATE_PREDICATE_AST_CONTRACT_V1`；
- `FOCUS_FOLLOW_UP_OBSERVATION_CONTRACT_V2`；
- `FOCUS_TRACKER_API_CONTRACT_V2`；
- `DUCKDB_TO_POSTGRES_FULL_MIGRATION_CONTRACT_V1`；
- `CROSS_ENGINE_LOGICAL_DIGEST_CONTRACT_V1`；
- `POSTGRES_PUBLICATION_WRITER_CONTRACT_V1`。

## 20. 本次设计阶段记录

| 字段 | 内容 |
|---|---|
| stage | `DAILY_FOCUS_FOLLOW_UP_DESIGN_REVISION_20260922` |
| stage_contract | `DAILY_FOCUS_FOLLOW_UP_DESIGN_V2` |
| consulted | V3 今日研究详细方案、P12-16 闭环审计、Forward observation/evaluation、数据状态语义、统一工作台 V2、M5 运维迁移、M7B schema migration、V3 读写切换与旧表保留决定、P12 DuckDB 锁修复与目标交易日修复、当前 base schema、007—035 migrations、research schema/query/build 与 DuckDB 直连清单 |
| evidence | V1 仅设计新功能表且状态判定不完整；当前真实系统包含基础发布、旧兼容结果、V3 relation/result object、research、online、Forward、运维等多个表域和大量 DuckDB 直连点；状态若不保存冻结事实、predicate 和依赖锁会随阈值/代码变化漂移 |
| acceptance_result | `DEGRADED_PASS / REVISED_DESIGN_READY_FOR_REVIEW`：已补齐现有全库迁移对象、类型与摘要、程序访问层、全量/增量/双读/切换/回退方案；已补齐个股与板块状态算法、失效谓词、三值逻辑、模型边界和防漂移机制。尚未执行真实库 P0 inventory、PostgreSQL 实测、迁移或页面实现 |
| code/config/database_changed | 否 / 否 / 否；仅新增本设计文档 |
| tdx_access_or_write | 未访问 / 未写入 |
| next_stage | 用户确认 V2 后，先进入 `PGM-00 / FOCUS_TRACKER_P0`：对真实生产库和全部直连消费者做只读盘点，冻结跨引擎摘要与状态 predicate；Phase 0 完成接受门后才开始 PostgreSQL schema 和实现 |
