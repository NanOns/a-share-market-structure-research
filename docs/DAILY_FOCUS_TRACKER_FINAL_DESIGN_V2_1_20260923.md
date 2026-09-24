# 候选个股与板块持续观察模块最终合并设计 V2.1

> 合同：`DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1`
> 日期：2026-09-23（Asia/Shanghai）
> 状态：`FINAL_DESIGN / FOCUS_IMPLEMENTATION_NOT_STARTED`
> 范围：合并产品、数据模型、算法、API、运行和验收设计；本文件本身不执行生成、迁移或交易。

## 1. 依据、优先级与当前前提

本文件是以下三份文档中**持续观察模块**内容的最终合并版：

1. `DAILY_FOCUS_FOLLOW_UP_DESIGN_V2_20260922.md`：产品目标、页面、基础数据模型和状态构想；
2. `DAILY_FOCUS_POSTGRES_DESIGN_V2_1_CHANGE_NOTES_20260922.md`：V2.1 数据模型、算法和实施顺序修订；
3. `FOCUS_TRACKER_INDEPENDENT_AUDIT_DISPOSITION_20260922.md`：独立审计问题的最终项目裁决。

冲突时以独立审计裁决和 V2.1 修订为准，V2 中未被修订的产品要求继续有效。尤其采用：来源分族、Episode + Segment + Anchor、六维正交状态、显式激活 head、立即确认板块退出、独立 tracking union、退出锚点、多次升级锚点、独立 outcome 事务。V2 中的单值 `episode_state`、`return_since_current_entry`、`SECTOR_MISS_TOLERANCE=1`、回溯确认退出和“模型换版即关闭 episode”均不再作为实施规则。

数据迁移已由 `POSTGRES_MIGRATION_INDEPENDENT_REACCEPTANCE_20260923.md` 验收为 `FULL_PASS / CURRENT_MIGRATION_DATA_ACCEPTED`。现有 publication、analysis 和 research bundle 的 PostgreSQL 权威 head 已建立；Focus 业务表和 `focus_trade_date_heads` 尚未建立，仍是本模块的实施工作。既有 Phase 0 为 `FULL_PASS_TDX_NATIVE`；本设计不访问或写入 TDX 来源。迁移审计保留的运行时覆盖、每日同步观察等事项继续由其独立审计项跟踪，不被 Focus 阶段结果代替。

## 2. 产品目标和边界

新增一级菜单 **“关注跟踪”**，长期保留每天正式生成的候选个股和板块，记录它们从首次进入、持续、升级、降级、退出、重入到后续结果结算的过程。页面应能回答：当时为何入选、当时知道什么、后来发生什么、原条件是否失效、退出后 T+1/3/5/10/20 如何、原支持板块是否仍有效。

本模块不修改来源算法的准入、评分或排名，不自动交易，不给出买卖、仓位、目标价或上涨概率，不用未来数据改写当时理由，不保存 M14 禁止持久化的热榜原始数据。历史重构与真实前瞻观察分开标记；描述性样本结果不用于自动调参。

## 3. 来源权威与对象身份

| source_family | 权威来源 | 当日 membership | 首版展示 |
|---|---|---|---|
| `V3_SHORTLIST_STOCK` | 已接受 `research_shortlist` | `CURRENT` / `EARLY` | 当前关注、提前观察个股 |
| `V3_SECTOR_TRACK` | 已接受 `research_sector_states` | `CURRENT` / `EARLY`（对应原 CURRENT/POTENTIAL） | 当前、提前观察板块 |
| `V3_3_TODAY_CANDIDATE` | `research_candidates_v3_3` 与已接受 bundle head | `CANDIDATE`，保留四类原场景 | 独立“V3.3 今日候选”页签 |
| `V3_SHORTLIST_INDIVIDUAL` | `research_shortlist(list_type=INDIVIDUAL)` | `INDIVIDUAL` | 数据保留，首版默认列表不启用 |

`source_family` 是身份的一部分。同一证券可在多个来源族中出现，其来源 membership、rank、场景、episode 和 outcome 分别保存；页面可以关联展示但不得静默合并。每条每日来源行必须有 `source_item_key`、`source_item_digest`、`source_contract_id` 和权威 run/head 身份。V3.3 的旧 Forward episode 仅作为关联证据，不复用为新 Focus episode。

每日快照主键为 `(focus_run_id, source_family, entity_type, entity_id)`；`focus_type`、主场景、排名、选择模式都不是主键。若同一来源运行内同一实体出现冲突行，发布前拒绝并形成错误证据，不以任意行覆盖另一行。

## 4. 时间、版本和可追溯性

业务交易日使用冻结主交易日历的 `DATE`；事件时刻保存 UTC instant，页面显示北京时间。自然日、在线最新交易日、本地输入日、publication 日期和 Focus 展示日分别标注，不混用。

一次 Focus run 必须绑定：trade date、publication head、研究 run 或 bundle head、snapshot、membership snapshot、source family set、来源合同、tracker 合同、参数集、日历、价格口径、输入 artifact digest、dependency lock 和运行 revision。输入只能包含该交易日及之前可知的事实。

`focus_trade_date_heads(trade_date, source_authority_contract_id)` 唯一指向已接受并激活的 run。下一交易日的状态前态只读取该 head，不能由文件 mtime、目录顺序、资料完整度启发式或任意 latest 查询决定。同日来源修订创建新 run/revision；旧版历史留存，T+N 不推进、跨日 transition 不重复制造。请求开始时固定一个 `focus_run_id`，详情和列表的全部读取沿用该身份。

## 5. 核心对象模型

### 5.1 Daily Snapshot

发布后不可变。股票保存来源类别/场景/排名、入选理由、等待条件、原失效文本与编译后的 AST、风险、收盘及价格口径、RPS/均线/额量能力、原始及当前支持板块、LOO 证据和数据质量。板块保存 CURRENT/POTENTIAL 来源事实、排名、分支、强度、宽度、相对强度、成交额、成员覆盖、角色成员及成员快照身份。文本解释不作为可执行谓词。

### 5.2 Episode、Segment 与 Anchor

Episode 是同一来源族、同一实体的一次**连续来源关注生命周期**。`FOCUS_EPISODE_ID_V2_1` 的规范输入为：

```text
source_family + entity_type + entity_id + episode_start_trade_date
+ source_selection_contract_family
```

主场景、排名、选择模式、CURRENT/EARLY 不进入 episode 身份。同源在榜连续时延续；EARLY/CURRENT 切换或 V3.3 场景变化只增加 transition。来源正式退出后再入选，创建新 episode 并关联 parent episode。

Segment 标识同 episode 内 source model 或 tracker interpretation 合同的有效区间。来源选择合同变化产生 `SOURCE_MODEL_BOUNDARY` segment；tracker 阈值或状态优先级变化产生 interpretation segment，均不能伪装成市场 NEW/EXITED，也不切断既有收益路径。旧 `AS_RECORDED` 保持不变；新规则历史回算写 `REINTERPRETED`。

Anchor 是一个明确的观察起点：`FIRST_FOCUS`、**每一次** `CURRENT_UPGRADE`、`EXIT_EFFECTIVE`、`INVALIDATION`、`FIRST_SUPPORTED`，以及版本化的只读 `MILESTONE`。每个 anchor 绑定交易日、run/revision、价格口径、参考价和来源事实摘要。退出后表现必须从 `EXIT_EFFECTIVE` 计算，不能拿首次关注表现代替。

### 5.3 六个正交状态

| 字段 | 含义 |
|---|---|
| `source_membership_state` | 来源当日 CURRENT/EARLY/CANDIDATE/NONE/UNKNOWN 事实 |
| `membership_phase` | NEW/PERSISTENT/UPGRADED/DOWNGRADED/EXITED/REENTERED 等跨日变化 |
| `validity_state` | 冻结研究 thesis 的 VALID/INVALIDATED/UNKNOWN |
| `followup_state` | ACTIVE_FOCUS/POST_EXIT/PENDING_SETTLEMENT/COMPLETED 等任务状态 |
| `current_path_state` | 截至当日最重要的价格或板块结构状态 |
| `lifetime_path_tags` | episode 历史曾发生的路径标签，不充当当前主状态 |

仍在榜但 `INVALIDATED` 是合法组合；失效不自动退出，不单独关闭 episode。退出但结构未破坏同样合法。状态判断要保存事实、解释、等待、失效与数据质量；缺必要事实时为 UNKNOWN，不沿用昨日判断冒充今日结果。

## 6. 每日集合、去重与增长控制

```text
TRACKING_UNION_t =
  当日全部正式来源 membership
  ∪ 尚未完成 followup 的历史 episode 对象
  ∪ 当日需要结算 anchor outcome 的对象
```

联合时先按 `(entity_type, entity_id, trade_date, fact_contract, price_basis)` 去重计算可共享的行情事实，再分别投射到各 `source_family + episode_id`。来源语义不得随共享事实合并。同一来源、同一 run 的每日行由主键去重；同一 episode、交易日、source revision、评价模式的 observation 唯一；同一 `(anchor_id, horizon, target_revision)` 的 outcome 唯一。重复运行同一输入和 revision 应得同一逻辑摘要并幂等；输入变更必须提升 revision，不覆盖旧版。

仍在榜的 episode 无固定最长天数，持续每日观察；长周期每 20 个交易日可建只读 `MILESTONE`，但不切断 episode。退出后继续到 `EXIT_EFFECTIVE` 及其他**必需** anchor 的 T+20 进入明确终态。完成条件是来源 membership 已正式结束、无未决 gap/revision、所有必需结果已终结；完成后移出每日 tracking union，历史仍可查询。`INVALIDATED` 本身不能令仍在榜的对象退出计算池。

若停牌、退市或实际行情缺失，outcome 分别标记 `SUSPENDED`、`DELISTED`、`DATA_GAP` 并保存原因、最后核验日和重试/终结依据。不得按经过的自然日自动删数据或挪动目标日。第 15.3、16.1 和 17.2 节固定其终态判据：证据未封存前保持待处理并计入逾期监控；封存后仍可由新的资料修订开启新 revision。

长期保存每日来源快照、episode、segment、transition、anchor、解释所需核心事实和 outcome。大体量日线/因子留在受版本管理的 Parquet 历史层；当前投影和缓存可重建、有界清理；staging 经发布与摘要核验后按运维合同清理。**移出每日计算池不等于删除历史**。任何历史归档或物理删除须另有保留期、引用检查、恢复和审计合同，首版不做自动删历史。

## 7. 每日状态算法

执行顺序固定：

```text
已接受 publication/research/bundle heads
 → 按 source family 校验并读取今日 membership
 → 读取上一 accepted focus head
 → 构造 tracking union
 → 离线物化今日 actual facts、质量及输入 artifact
 → 判定 membership phase
 → 评估冻结 invalidation AST 得到 validity
 → 判定 current path 和 lifetime tags
 → 追加 episode/segment/transition/anchor/observation
 → 更新可重建的 current projection
 → 原子激活 focus head
 → 在独立事务结算到期 outcomes
```

仅当当日完整、已接受、同 source contract 的来源 run 明确不含该对象时，`M_t=NONE` 才可判定 `EXITED`。失败日、缺失来源、UNKNOWN 或来源合同边界不制造退出。首版板块不使用 provisional miss：完整合格日 CURRENT/POTENTIAL 均不入选即当日退出，后续再入选为新 episode；不回溯修改旧日事实。来源合同变化只标 segment boundary。

| 上一接受状态 → 当前来源 | membership 结果 |
|---|---|
| NONE → 首次入选 | `NEW`，建立 episode 与 FIRST_FOCUS anchor |
| NONE → 退出后再入选 | `REENTERED`，建立新 episode，关联 parent |
| EARLY → CURRENT | `UPGRADED`，延续 episode，建立本次升级 anchor |
| CURRENT → EARLY | `DOWNGRADED`，延续 episode |
| 同类持续在榜 | `PERSISTENT` |
| 在榜 → 完整日 NONE | `EXITED`，建立 EXIT_EFFECTIVE anchor，进入后续观察 |
| 来源不完整或 UNKNOWN | `DATA_UNAVAILABLE`，不推进退出或连续谓词 |
| 同日 revision | `SOURCE_REVISED`，不推进交易日 |
| 来源模型换版 | `SOURCE_MODEL_BOUNDARY` segment，不伪造市场变化 |

失效 AST 由独立 `FOCUS_INVALIDATION_COMPILER_V1` 基于场景、信号日事实、来源合同和参数集编译并冻结；不解析自然语言 `invalid_if`。操作数显式区分 `CURRENT_FIELD`、`FROZEN_SIGNAL_VALUE`、`FROZEN_EPISODE_VALUE`、`DERIVED_DYNAMIC_FIELD`。每个谓词使用 TRUE/FALSE/UNKNOWN 三值逻辑并保存字段值、阈值、比较符、参与交易日和原因。`CONSECUTIVE` 只允许连续主交易会话；中间无 actual bar 时为 UNKNOWN，不能跨缺口拼接。

## 8. 价格、板块与路径状态

每个 observation 以观察日 `t` 为共同 affine anchor，按 `FOCUS_PATH_PRICE_BASIS_V1` 重算从信号日到 `t` 的整段调整 OHLC，再计算 `C_t/C_first-1`、期间最高上行、最低路径、峰值回撤和 anchor 收益。不得混用不同观察日各自锚定的历史调整价。价格来源、调整版本/哈希、日历、实际参与会话、停牌及覆盖质量随结果保存。无行情时不复制旧收盘价，也不制造收益。

股票状态按固定优先级评估所有谓词并选一个主 `current_path_state`：`DATA_UNAVAILABLE` → `STRUCTURE_DAMAGED` → `TOO_EXTENDED` → 健康/未确认回调 → 启动确认 → 趋势加速 → 板块背离 → `WEAKENING` → 等待确认 → 退出后跟踪。`WEAKENING` 高于横盘等待；`SIDEWAYS_RANGE` 是副标签；曾经直接上行写 `HAD_DIRECT_ADVANCE` lifetime tag，不长期占据当前主状态。现有锁定 scanner 的 EXTENDED/LAUNCH_CONFIRM/TREND_CONTINUE 等事实优先复用，不在跟踪器另造同名信号。

板块收益首版明确标为成员收益构造指标，不称官方板块指数。`ENTRY_FROZEN_BASKET` 保留入选时成员，用于原 thesis 路径；`CONTEMPORARY_SECTOR_BASKET` 使用当日有效成员，用于当前板块生态。宽度、强势成员留存率和相对强度须通过成员可比与覆盖门；否则 UNKNOWN，并记录 `comparison_gap_sessions`、`continuity_quality`。首次无板块支持的股票可后来建立 `FIRST_SUPPORTED` anchor，但 `entry_primary_sector_id` 继续为空，`current_primary_sector_id` 单独更新。股票与原板块的领先、落后、同步回调等联动标签仅作描述。

V2 中股票回调 3%—12%、5 日区间 8%、RPS 连降 3 日、板块回调 2%—8%、宽度下降 15 个百分点、成员留存 50%、Jaccard 0.90、覆盖 0.80 等初值作为固定的 `CANDIDATE_ENGINEERING_PARAMETERS`，精确数值、端点、优先级和缺失处理以第 18 节为准并写入不可变参数合同；在真实前瞻证据和独立审计前不称其为有效阈值，不自动优化。V2 的 `SECTOR_MISS_TOLERANCE` 已取消。

## 9. Anchor outcome 与观察终点

正式期限为 T+1、T+3、T+5、T+10、T+20，T+N 以冻结主交易日历中的后续第 N 个交易会话确定，不按自然日推算。每次升级各建自己的 anchor 和 outcome；首次、退出、失效分别结算，不能覆盖或互相代替。结果状态为 `PENDING / OBSERVED / DATA_GAP / SUSPENDED / DELISTED / SOURCE_REVISED`，带原因代码、目标日、目标 revision、价格口径、覆盖和评价 basis。

Core Focus Publication 与 Outcome Settlement 分为两个幂等事务。历史 outcome 结算失败只令 `outcome_settlement_status=DEGRADED` 并留下可重试任务，不阻断今天的 Focus head 发布。已退出且全部必需 anchor 结果终结后标记 `FOLLOW_UP_COMPLETED`，不再每日追加 observation；仍长期保留已记录路径与结果。

## 10. PostgreSQL 数据模型与事务

在现有已验收的 PostgreSQL `workbench` 数据域原生新增 Focus schema，不把旧 DuckDB 007—035 迁移文件当作 Focus DDL。关键表及唯一性：

| 表 | 责任和主要键 |
|---|---|
| `focus_runs` | run、日期、修订、publication/source head、合同、输入摘要、核心/结算状态 |
| `focus_daily_items` | 不可变来源行；PK `(focus_run_id, source_family, entity_type, entity_id)` |
| `focus_episodes` | episode 身份、起始日、parent、退出和结束事实 |
| `focus_episode_segments` | 来源模型与解释合同有效区间及 boundary 原因 |
| `focus_episode_transitions` | 日期、来源状态前后值、transition、reason 和 revision |
| `focus_episode_anchors` | anchor 类型、交易日、run、参考价和来源摘要 |
| `focus_episode_observations` | episode、日、source revision、六维状态、事实、质量和 digest |
| `focus_episode_outcomes` | PK `(anchor_id, horizon, target_revision)`；状态、收益、风险和原因 |
| `focus_outcome_heads` | PK `(anchor_id, horizon)`；指向唯一 accepted target revision |
| `focus_stock_sector_links` | 原始与当前支持关系、角色、LOO 与证据 |
| `focus_current_projection` | 按 source family/entity 的可重建页面投影 |
| `state_evaluations` / `state_evaluation_facts` | AS_RECORDED 决策与逐谓词证据 |
| `algorithm_contracts` / `algorithm_parameter_sets` | 不可变合同、参数、源码及依赖锁 |
| `focus_trade_date_heads` | PK `(trade_date, source_authority_contract_id)`；唯一 accepted run |

核心发布事务包含 run、daily items、episode/segment、transitions/anchors、当日 observations、评估证据、current projection 和 head 激活；任一步失败全部回滚。head 指向 READY + ACTIVATED 的完整 run；同日修订以新 revision 原子替换 head，旧行保留。投影从不可变历史可重建并用逻辑摘要核验。PostgreSQL 只接收已核验的离线事实和 artifact identity；API 不即时运行 DuckDB、扫描 Parquet 或请求在线行情。

## 11. 页面、API 与降级

一级菜单为“关注跟踪”。主区域分别展示 V3 当前/提前个股和板块；V3.3 今日候选独立页签；另有退出后走势、历史 episode、详情时间线和达到样本门后的统计复盘。列表显示来源、数据交易日、首次关注、持续会话、状态六维摘要、收益/回撤、原支持板块、等待与失效条件及数据质量。详情分为“当时为什么关注”“后来发生了什么”“现在如何解释”，标记首次、升级、退出、失效和 outcome 节点。

只读 API 建议沿用 `/api/v3/focus-tracker/summary`、`/items`、`/episodes/{id}`、`/stocks/{id}`、`/sectors/{id}`、`/transitions`、`/statistics`、`/runs`；列表支持 source family、日期、membership、validity、path、板块、场景、质量及分页。每个响应返回固定 `focus_run_id`、trade date、revision、合同和数据状态。PG 不可用返回 503，不回退 DuckDB 或文件 pointer；生成中或生成失败时可显示上一成功 run 并明确标注展示日期与失败状态。

统计复盘沿用至少 **30 条完整结果且 5 个独立信号交易日**的描述性显示门。只给样本数、分位收益、最大上行/回撤和数据缺口，不给未来概率；跨 source family、合同版本、历史重构/真实前瞻不得混成一个未标注样本。

## 12. 实施顺序与阶段门

PostgreSQL 全库迁移属于已完成前提，不再作为 Focus 开发步骤重复执行。后续按下列阶段推进；每阶段执行前复核最新适用升级文档，并记录合同、证据、接受结果和下一阶段，测试通过不能单独代表发布就绪。

| 阶段 | 工作 | 必需验收 |
|---|---|---|
| `FOCUS-00` | 冻结 source authority、episode/segment/anchor、六维状态、AST、价格路径、head、tracking union、观察终结合同 | 双来源、多次升级、仍在榜但失效、退出后 T+20、失败日、场景切换、同日修订、停牌/退市、后获板块支持反例 |
| `FOCUS-01` | PG schema、约束、索引、迁移 ledger、备份恢复 | Focus 表可独立恢复；唯一键/FK/CHECK 与既有 head 一致 |
| `FOCUS-02` | 已接受来源封存和共享事实物化 | 权威 head 唯一；source row digest、tracking union 和缺失质量完整 |
| `FOCUS-03` | Core Focus 原子发布、重放、同日修订与 projection | 幂等、失败回滚、单 head、历史不可覆盖、投影可重建 |
| `FOCUS-04` | anchors、T+N outcome、完成和逾期管理 | 交易日历正确；退出后跟踪；结算失败不阻断 core |
| `FOCUS-05` | API、页面、列表/详情/状态证据 | 单请求固定 run；PG 503；来源分族和日期标签准确 |
| `FOCUS-06` | 连续真实交易日观察、性能、统计门及独立审计 | 完整阶段回执；无伪历史、伪退出、伪结果或混合权威 |

页面实现须在 `FOCUS-00` 十项语义硬门和核心数据合同通过后开始。首版从 PG 正式 Focus 日开始记 `REAL_FORWARD`；如需补记迁移期间日期，只能在存在同期封存的 source rows、身份和能力证据时另立重构合同，不能从今天结果推造过去可知状态。

## 13. 验收与运行指标

功能反例必须包括：连续在榜同 episode；EARLY→CURRENT→EARLY 与多次升级 anchor；退出后重入新 episode；已退出对象继续到结算；仍在榜但 thesis 失效；板块一日合格掉榜立即退出；失败日不退出；同日修订无跨日事件；来源或 tracker 换版仅 segment；停牌、退市和缺 actual bar 的 outcome；股票先独立后获板块支持；跨来源同股不合并；完成后不再日算但历史可查。

数据验收要求：每日来源键无重复，tracking union 与待结算计划可对账，所有 path state 有输入/谓词/合同解释，`AS_RECORDED` 不被回算覆盖，同输入同依赖锁重放摘要一致，projection 可从历史重建，PG head 指向唯一完整 run，备份真实恢复通过。性能以列表 P95 < 500 ms、详情 P95 < 800 ms 为初始目标，实测记录硬件和样本量；统计使用物化或异步结果，不阻塞日常页面。

持续监控每日新增/升级/退出/重入、活动及退出后待观察 episode 数、超过目标日未结算 outcome 数、数据缺口、revision、池中对象数量增长、staging 与 PG 摘要、API P50/P95、PG 错误和备份恢复结果。异常增长或跨切面审计问题须单独立项，范围、证据和接受条件独立于当前 Focus 阶段门。

## 14. 规范化算法合同：输入与来源完整性

本节及以下各节是**实现约束**，不是示例。实现代码、SQL、任务和页面不得自行改变顺序、空值含义、阈值或身份。需要改变时先发布新合同版本、反例和迁移/并存规则。

### 14.1 一日输入清单

一次正式 run 的输入 manifest 必须包含：`trade_date`、主交易日历摘要、publication/head ID、各 source family 的 accepted run/head ID、源行数与规范摘要、snapshot/membership snapshot、实际行情输入摘要、调整事件来源和版本、板块成员快照身份、factor/scanner/source selection/tracker 合同、参数集、实现与依赖锁、评价 basis (`REAL_FORWARD` 或明确的 `HISTORICAL_RECONSTRUCTED`)。任一身份跨日期或互相不一致时整次 run 拒绝。在线热榜即时结果不进入此 manifest 或持久化表。

同一 publication 下若某来源有多个 COMPLETE 研究 run 而无已接受绑定，拒绝该来源族，不按创建时间或 row count 选择。若本地输入交易日落后于生产合同确定的 expected trade date，不发布伪“今日”正式 Focus run；已有 accepted 旧日可继续明确标日期展示。主交易日历缺失或待修订时不产生 T+N 目标日期。

每个来源族独立给出 `COMPLETE / UNAVAILABLE / REVISED / CONTRACT_BOUNDARY` 能力状态。`COMPLETE` 要求该族的权威 head 存在、所属 publication 已接受、运行成功、行数与摘要核对通过、源行日期一致、无同键冲突。**空清单只有在 COMPLETE 且源运行明确报告 0 行时才表示全体退出**。运行缺失、文件无法读、行数不符、摘要不符、合同不认识均为 `UNAVAILABLE`；既有成员为 `UNKNOWN`，不能从“查不到行”推出 `NONE`。若三族中的一族不可用，其余族可发布但必须保存该族的降级能力与未推进状态；不得用旧日该族清单冒充今日入选。首个正式 Focus accepted 日之前不构造 `REAL_FORWARD` episode；历史来源行只能在独立重构模式和同期来源证据下进入。

V3 shortlist 使用所属已接受研究 run 的 `CURRENT_FOCUS`、`EARLY_FOCUS` 原行；同一证券同日若两种类型均存在，按来源合同的正式唯一选择裁决，若无明确裁决则拒绝该族发布，不按排名任意取一行。板块以 `current_eligible=true` 为 CURRENT；否则 `potential_eligible=true` 为 EARLY；两者都不满足不产生当日来源行。V3.3 只用 PG 已接受 `research_bundle_heads` 绑定的 bundle 候选行；`primary_category` 及 `matched_categories` 原样保存，不能重命名为 CURRENT/EARLY。来源合同变化要显式标边界，不能用旧/新榜单集合差制造市场退出。

### 14.2 规范化与重复处理

源行规范摘要采用版本 `FOCUS_CANONICAL_JSON_V1`：字段名按 Unicode 码点序排序，UTF-8、无额外空格，DATE 用 `YYYY-MM-DD`，instant 用 UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`，NULL、缺字段、空字符串和空数组各自不同；布尔值不得转 0/1；Decimal 保留合同声明 scale 的十进制字符串，binary64 规范为大端 IEEE-754 64 位十六进制字符串，拒绝 NaN/Infinity，负零规范为零；有序数组保序，无序 ID 集合先按规定的 ID 排序。摘要是上述规范字节的 SHA-256；字段白名单、数值类型和数组语义随 source contract 固定。相同主键、相同摘要的重复导入可幂等忽略；相同主键、不同摘要必须阻断或建立新 source revision，绝不 last-write-wins。跨来源族同股保留多条 membership；共享行情事实只计算一次，再按不同 episode 解释。历史修订行不可 UPDATE/DELETE，数据库唯一键只是最后防线，发布前仍需对输入主键、数量和摘要做校验。

## 15. 规范化生命周期、版本与重放算法

### 15.1 状态机的精确定义

令 `k=(source_family, entity_type, entity_id)`；`M_t(k)` 是当日该来源的 `CURRENT/EARLY/CANDIDATE/INDIVIDUAL/NONE/UNKNOWN`。`NONE` 仅在该族 COMPLETE 时有意义；`UNKNOWN` 表示不能作有无结论。`P_t(k)` 取**上一已接受的可比较 Focus 交易日 head**，而非最近生成但未激活的 run。可比较要求来源选择合同族相同；模型边界另处理。日历中间缺正式发布日时保存 `comparison_gap_sessions` 和 `continuity_quality`，不把两日当连续会话，也不从缺日推断退出。

执行优先级如下，先命中的 membership 分支决定当日相位：

| 优先级 | 输入条件 | 相位和动作 |
|---:|---|---|
| 1 | 同日 source revision，尚未进入下一交易日 | `SOURCE_REVISED`；重新形成该日的被接受投影，不新增 T+N 会话或跨日事件；旧 revision 不覆盖 |
| 2 | 该族 UNAVAILABLE 或 `M_t=UNKNOWN` | `DATA_UNAVAILABLE`；当前 episode 保持原 membership 连续性未知，禁止 EXIT/NEW、升级和连续谓词通过 |
| 3 | 来源选择合同族变化 | 新建 `SOURCE_MODEL_BOUNDARY` segment；对前后 membership 不作市场 NEW/EXITED 推断；在新合同具可比较基线后恢复状态机 |
| 4 | `P=NONE, M≠NONE`，无已退出前 episode | `NEW`；新 episode、FIRST_FOCUS anchor |
| 5 | `P=NONE, M≠NONE`，有已退出前 episode | `REENTERED`；新 episode 与 parent 链接、FIRST_FOCUS anchor |
| 6 | `P=EARLY, M=CURRENT` | `UPGRADED`；同 episode，本次独立 CURRENT_UPGRADE anchor |
| 7 | `P=CURRENT, M=EARLY` | `DOWNGRADED`；同 episode |
| 8 | `P=M≠NONE` | `PERSISTENT`；同 episode；场景/选择模式变化另记 source attribute transition |
| 9 | `P≠NONE, M=NONE` 且该族 COMPLETE | `EXITED`；同 episode，当日 EXIT_EFFECTIVE anchor、开始退出后观察 |
| 10 | `P=NONE, M=NONE` 且 episode 未完成结算 | `POST_EXIT`；仅追加后续 observation/outcome，不新建 episode |

`CANDIDATE/INDIVIDUAL` 仅同类持续；来源内部场景改变记 `SCENARIO_CHANGED`，不等价于升级。`INVALIDATED` 是 validity transition，可与任何 membership 相位同日并存；首次由非 TRUE 变 TRUE 时建立 INVALIDATION anchor，之后持续 TRUE 不重复建。股票原本无有效板块支持，后来首次满足已冻结的有效支持门，建立 FIRST_SUPPORTED anchor；后续关系变化不回写入选日。`EXITED` 和 `INVALIDATED` 可同日建两个不同 anchor。

来源模型边界日另有确定动作：边界前后均在榜的对象沿用 episode 并开 source segment；仅新合同出现的对象建立 `MODEL_BASELINE` episode 与 FIRST_FOCUS anchor，但不计入市场 NEW 数；仅旧合同出现的对象当日记 `BOUNDARY_UNKNOWN` 并继续观察，不建 EXIT anchor。下一**同新合同且 COMPLETE**的可比交易日仍无该旧对象时，才以那一天为 EXIT_EFFECTIVE，不回溯到边界日。若 source selection **合同族**也变，全部新合同对象从 `MODEL_BASELINE` 新 episode 起步、旧 episode 建边界关联与待判结束状态，不互相共享 episode ID。

### 15.2 同日修订、后到资料和重放

同日新 revision 在冻结的前一交易日 head 上**重新计算整日**，不能在旧同日结果上再推进一次。旧 run、source rows、`AS_RECORDED` evaluation 和 outcome revision 均保留；新 head 原子指向新 run。每个 `focus_trade_date_heads` 保存 `predecessor_focus_run_id` 和 `lineage_state=VALID/REPLAY_REQUIRED`。受修订影响的后续日期须按交易日顺序显式重放并生成各自新 revision；在重放完成前原后继 head 标 `REPLAY_REQUIRED`，API 不把它作为当前或下一日前态，只能明确以旧 revision 历史视图查看。不能让先前按旧事实形成的后续状态继续冒充新链条。相同输入 manifest、合同和依赖锁重复运行应得到同一逻辑摘要；不同内容占用同一 run/revision 主键必须失败。

来源选择合同换版时 episode 身份中的**合同族**保持稳定才可延续并加 segment；若合同族本身变化，则不能直接复用旧 episode ID，须创建明确 `SOURCE_FAMILY_BOUNDARY` 关联与新基线，前后不称市场 NEW/EXITED。tracker 解释合同换版不改变来源 episode；只开启 interpretation segment。`REINTERPRETED` 的规则、结果和版本单独保存，页面默认仍显示当日 `AS_RECORDED`。

### 15.3 观察池算法与终结

先按 source family/episode 建待观察键，再归并可共享实体事实。当前在榜 episode 始终在池中，不受 20 日上限影响。退出后，只要其任何正式锚点的必需 T+1/3/5/10/20 未终结、同日修订待处理或输入 gap 待审，就留在池中；MILESTONE 为诊断锚点，不阻止终结。`SOURCE_REVISED` 要重新规划，不算终态。`OBSERVED` 是正常终态；`SUSPENDED` 仅在目标日停牌已有证券/日期审计证据时是该固定 horizon 的无收益终态；`DELISTED` 只有在可靠身份/退市证据下为终态；`DATA_GAP` 只有目标交易日输入已最终封存且缺失原因和可恢复性审计完成后才可作为该 horizon 的终态。无任意“过了 N 天就删”的规则。

正式关闭要求：来源已确认退出，全部**必需**锚点的所有期限达到上述终态，无待重放 revision，无未审数据 gap。目标日的输入已成为 accepted 且摘要封存后，若依 `DATA_STATE_SEMANTICS_CONTRACT_V1` 确认为非 BAR 而无可计算价格，以具体缺失态、来源摘要和审计时刻形成该 horizon 的 `DATA_GAP` 终态；若有证券/日期对应的已审停牌证据，则以 `SUSPENDED` 终结该固定目标日的结果，收益保持 NULL，不挪目标日；`DELISTED` 只在已审退市证据下终结。关闭写 `FOLLOW_UP_COMPLETED` 事件和完成日，此后不进入日计算 union；历史快照、路径、transition 和结果不删除。若完成后收到合法历史修订，开启明确的 `SETTLEMENT_REOPENED` 修订链，不能悄悄覆盖旧结算。

## 16. 规范化三值逻辑、失效 AST 与数据质量

### 16.1 三值真值表和能力门

所有必需谓词结果为 `T/F/U`。`NOT U=U`；`T AND U=U`，`F AND U=F`；`T OR U=T`，`F OR U=U`。**U 不是 F**。必需输入缺失、非有限数值、价格非正、日历不一致、成员覆盖不足或合同不匹配，相关谓词为 U，并保存原因；若主状态无法可靠判定则 `DATA_UNAVAILABLE`。可选谓词为 U 不推翻已由完整必需事实成立的状态，但增加 `OPTIONAL_EVIDENCE_UNKNOWN`。失效 AST 为 U 则 `validity_state=UNKNOWN`，不得显示“仍有效”。

每个 source contract 同时登记适用的 path 谓词能力：`APPLICABLE`、`NOT_APPLICABLE`。明确不适用的分支跳过，不参加优先级阻断；已声明适用但事实缺失则为 U，不能悄悄降成不适用。例如来源未正式输出 EXTENDED 时不能由跟踪层另算，也不能把 EXTENDED 缺值解释为 F。若全部分支均不适用但基础行情完整，使用 `UNCLASSIFIED`；若适用的高优先级分支为 U 且会改变已选结果，使用 `DATA_UNAVAILABLE`，并保留其余可知事实。这份能力映射作为 `FOCUS_SOURCE_AUTHORITY_V1` 的版本化内容，不由运行时探测“字段有值就启用”。

`DATA_STATE_SEMANTICS_CONTRACT_V1` 的实际 `BAR` 才可参与价格路径、收益和连续交易谓词。`INFERRED_GAP` 不等于停牌；无单独审计的证券/日期状态证据不能写 `CONFIRMED_SUSPENSION`。合成参考 close、派生零成交量和 `tradable` 兼容字段均不能当 actual bar 或真实可交易证据。`NOT_LISTED_YET`、`DELISTED_OR_INACTIVE`、`FILE_MISSING` 各保留原状态，不统一写零收益。

### 16.2 AST 语法、冻结与求值

`FOCUS_INVALIDATION_COMPILER_V1` 接受确定的 `scenario + signal facts + source scanner contract + tracker parameter set`，输出规范 JSON AST、冻结字段、动态字段定义、实现/依赖锁与 SHA-256。首版允许 `AND/OR/NOT`、`EQ/LT/LE/GT/GE`、`CONSECUTIVE(n,predicate)`；未知操作、未知字段、自然语言表达或非法单位使该 thesis 的失效能力为 U，**不**允许程序猜测一个价格阈值。每个叶节点声明以下取值模式之一：

| operand mode | 含义 | 例子 |
|---|---|---|
| `CURRENT_FIELD` | 当日实际可观测字段 | 当日 close、structure_break |
| `FROZEN_SIGNAL_VALUE` | 信号日已知并冻结的数值 | 信号平台 PHH20 |
| `FROZEN_EPISODE_VALUE` | episode 建立时冻结的值 | 首次参考价、原主板块 |
| `DERIVED_DYNAMIC_FIELD` | 按固定合同用截至当日事实导出的字段 | 当日 MA20、从 episode 起的 peak |

`CONSECUTIVE(2,p)` 检查主日历上的当日与前一会话；任一会话非 actual BAR 时整个谓词 U，不能跳过缺日去找上一个有价格的会话。每个叶节点保存参与日期、actual、阈值/冻结 anchor、运算符、单位、精度、结果和 reason code。来源 `invalid_if` 文本仅作展示；不能 `eval` 文本。`SETUP_WATCH` 的“超出观察期限”只有来源合同或冻结参数显式提供期限时才可求值，否则该分支 U，不能自行设天数。

首版 V3.3 的 tracker 失效 AST 固定如下。表中任一冻结 operand 在 signal day 不存在或身份不可靠，该叶节点为 U，按三值逻辑求整体结果；不从 `invalid_if` 文本、后续行情极值或当前板块信息补造冻结值。`structure_break_v3` 沿已接受来源 scanner 的原合同，不另定义。

| 主场景 | 冻结 operand | 首版 AST；比较均用同一调整价格口径 |
|---|---|---|
| `LAUNCH_CONFIRM` | signal day `phh20` | `OR(structure_break_v3=T, CONSECUTIVE(2, close < frozen_phh20))` |
| `STRONG_PULLBACK` | 来源 pullback episode 的冻结失效低点 | `OR(structure_break_v3=T, close < frozen_pullback_invalid_low)` |
| `RECOVERY_TURN` | signal day 明确被收复的 MA5 或 MA20 类型 | `AND(CONSECUTIVE(2, close < dynamic_reclaimed_MA), RPS20_t ≤ RPS20_{t-3})`；被收复均线类型不得事后改换 |
| `TREND_CONTINUE` | signal day 来源关键低点 | `OR(structure_break_v3=T, close < frozen_trend_key_low)` |

这组 AST 是**跟踪层的研究 thesis 定义**，不回写或替代 V3.3 候选算法。`STRONG_PULLBACK` 或 `TREND_CONTINUE` 的来源证据未给出明确可冻结低点时，相关叶节点 U；若 `structure_break_v3=F`，整体为 U，不得用任意近五日低点代替。`RECOVERY_TURN` 缺被收复均线身份或 RPS20 比较日事实时为 U。V3 shortlist 和板块若没有可编译的结构化失效条件，原文保留，但 validity 为 UNKNOWN；不能因算法今天仍入选就断言原 thesis VALID。后续增加模板只可发布新 tracker 合同和 segment，不能重算覆盖旧 `AS_RECORDED`。

## 17. 规范化价格路径与 outcome 算法

### 17.1 股票价格路径

以现有本地复权合同的 RAW 与 XRXD 事件为唯一价格调整依据，不使用外部调整服务。对观察日 `t`，用 `t` 作共同 affine anchor，令 `A_t=1,B_t=0`，逆序组合所有生效日不晚于 `t` 的事件，对 episode 首日至 `t` 的 RAW open/high/low/close **整段重算**为 `P_{j|t}=ROUND_HALF_UP(A_{j|t}·RAW_j+B_{j|t},0.01)`；volume/amount 保持原始口径。调整事件即使落在无 bar 日也纳入组合；未来事件绝不使用。每条 observation 保存事件集合/调整 source hash、价格口径、RAW 输入摘要及共同锚点日期。若事件结构或身份不可靠，路径质量 U，不以 RAW 和调整价混算。

当冻结 normalized Parquet 已逐行保存同一版本地调整的 `qfq_mul=A_j`、`qfq_add=B_j` 时，可用完全等价的坐标变换 `P_{j|t}=ROUND_HALF_UP((A_j·RAW_j+B_j-B_t)/A_t,0.01)`；它把 normalized 文件较晚锚点的未来调整从 t 日观察中抵消。必须核验 j→t 所有行来自同一 `adjustment_version`、状态 VERIFIED、同一 artifact 摘要且 `A_t>0`；若任一行不满足则 U。这个等价式不得用于混合不同文件或不同调整版本。

冻结价格阈值须同时保存信号日来源数值、该数值的口径、可重算的 RAW 基础值或等价 affine 身份。观察日比较前把冻结阈值也转换到 `t` 的共同锚定口径；不能拿 signal-day QFQ 数字直接与 t-day QFQ close 比较。无法复现阈值转换时，对应失效叶节点为 U。对数值不变的类别/布尔阈值不做价格转换。

在同一 `t` 锚定路径上定义，`s` 为 anchor 交易日，`J=[s,t]` 中只含真实 BAR 且同时检查会话完整性：

```text
R_close(s,t) = C_{t|t}/C_{s|t} - 1
MFE(s,t)     = max_{j∈J}(H_{j|t}/C_{s|t} - 1)
MAE(s,t)     = min_{j∈J}(L_{j|t}/C_{s|t} - 1)
PEAK_CLOSE(t)= max_{j∈J} C_{j|t}
DD_CURRENT(t)= C_{t|t}/PEAK_CLOSE(t) - 1
MDD(s,t)     = min_{j∈J}(C_{j|t}/max_{u∈[s,j]}C_{u|t} - 1)
```

`MFE/MAE` 是日内 high/low excursion，`DD_CURRENT/MDD` 是 close 路径回撤，不能使用同一字段名混指。`C_{s|t}≤0`、任一必需 adjusted 价格无效或期间存在影响连续路径的缺 BAR，会使相应路径指标 U；可单独展示已覆盖区间的诊断值，但不得将它标成完整 MFE/MDD。MA/RPS/成交额比沿既有 factor contract 和可用状态读取，不自行修改窗口或补值。`first_current_anchor_id` 与 `latest_current_anchor_id` 分列；每次升级收益通过指定 anchor 的 `R_close` 计算，不存模糊的单一“当前进入收益”。

### 17.2 T+N 日、目标修订与数据缺口

`due_date(anchor,n)=calendar.successor(anchor.trade_date,n)`，其中 successor 是**之后**第 n 个主交易会话。周末、节假日和任务运行次数不计入 n。目标日尚未来到为 `PENDING`；已到而输入不完整为 `DATA_GAP` 待审或在有审计依据时 `SUSPENDED/DELISTED`，绝不挪到下一有 BAR 的日期冒充 T+N。`OBSERVED` 必须有 anchor 参考日及目标日实际 BAR、同一评价价格口径、可复现调整路径和目标 source revision。结果含 `R_close`、到期区间 MFE/MAE/MDD、覆盖、输入摘要及 `REAL_FORWARD/HISTORICAL_RECONSTRUCTED`。同一 anchor/horizon 的后到修订只新增 `target_revision`；旧 revision 留存。页面默认版本由 `(anchor_id,horizon)` 唯一的 `focus_outcome_heads` 指向已接受 target revision，指针与 outcome 插入在同一结算事务内更新；不得用 `max(target_revision)` 猜测。

### 17.3 板块路径与可比性

板块不假称官方指数。对某篮子 B、某交易日 t，用该篮子中具有 t 和前一主会话实际 BAR 的成员计算个股一日 close 收益；`SRET1(B,t)=median(r_i)`，有效数和覆盖率同时保存。构造净值 `NAV(B,s)=1`，随后仅在每个必需交易会话可比且覆盖门通过时 `NAV(B,t)=NAV(B,t-1)·(1+SRET1(B,t))`。任何中间缺口使跨缺口累计净值和峰值回撤 U，不把 D1 与 D3 直接连成一日。冻结篮子 B 固定为 entry membership snapshot；当代篮子 `B_t` 取 t 的有效 membership snapshot，两条 NAV/宽度序列分开命名和存储，不能互换。

对有效成员：`SWIDTH=strong_member_count/evaluable_member_count`，`SREL=SRET1-normal_universe_median_RET1`，`RETENTION=前一可比日强势成员中今日仍强势数量/前一可比日强势成员数量`，`JACCARD=|B_t∩B_prev|/|B_t∪B_prev|`。中位数对奇数样本取排序中项、偶数样本取中间两项算术平均；正常股票全集必须与同日 publication/snapshot 一致。覆盖率分母是该篮子应有成员数，分子是有该指标完整输入的成员数。分母为 0、覆盖小于 0.80、Jaccard 小于 0.90 或缺少共同成员时，相关**跨日比较**为 U；保存分母、成员数、覆盖及质量。当前板块状态用 contemporary basket；原 thesis 路径优先用 entry-frozen basket。原板块与股票相对收益只在相同起止日期、价格口径及板块路径覆盖通过时计算，否则 `LINKAGE_UNKNOWN`。

## 18. 股票、板块路径判定的固定优先级

参数以 V2 工程初值注册为 `FOCUS_STOCK_PATH_PARAMS_V1_CANDIDATE`、`FOCUS_SECTOR_PATH_PARAMS_V1_CANDIDATE`：`PULLBACK_MIN=.03`、`PULLBACK_MAX=.12`、`SIDEWAYS_SESSIONS=5`、`SIDEWAYS_RANGE_MAX=.08`、`RPS_WEAKEN_SESSIONS=3`、`SECTOR_DIVERGENCE_MIN=.05`、`SECTOR_PULLBACK_MIN=.02`、`SECTOR_PULLBACK_MAX=.08`、`WIDTH_DROP_WARN=.15`、`RETENTION_WARN=.50`、`MEMBER_JACCARD_MIN=.90`、`COVERAGE_MIN=.80`。这些是**固定的首版工程参数**，仅其效果未经验证；实现不得私自改值。调整后 OHLC 用本地合同规定的分币精度；价格/收益比率由这些精确分币值形成，不先把百分比展示值四舍五入。所有阈值按上述十进制有理数作严格 `<`、`>` 或含端点的 `≤`、`≥` 比较，零额外 epsilon；来源 factor 的浮点值必须有限且按其原合同精度比较，非有限值为 U。展示格式化值不得参与决策。

股票先求全部可用谓词和副标签，再按下表从上至下选第一个 TRUE 的主状态；U 不当 F，若 U 会影响优先级判定，主状态为 `DATA_UNAVAILABLE` 并保存已知副事实：

| 顺序 | 主状态 | 必需 TRUE 条件 |
|---:|---|---|
| 1 | `DATA_UNAVAILABLE` | actual BAR/调整路径/必需 factor 或失效能力不足以作本日判断 |
| 2 | `STRUCTURE_DAMAGED` | 冻结 invalidation AST=T，附命中叶节点 |
| 3 | `TOO_EXTENDED` | 来源已锁定 EXTENDED=T，不另设阈值 |
| 4 | `PULLBACK_HEALTHY` | `DD_CURRENT∈[-.12,-.03]` 且 `C≥MA20`、structure_break=F、invalidation=F |
| 5 | `PULLBACK_UNCONFIRMED` | 同回撤区间，`C<MA20` 或合同必需确认=F，且 invalidation=F；invalidation=U 时由能力门降级 |
| 6 | `BREAKOUT_CONFIRMED` | 来源 LAUNCH_CONFIRM=T 且质量 READY |
| 7 | `TREND_ACCELERATING` | 来源 TREND_CONTINUE=T、`R5>0`、`RPS20_delta3≥0`、当前主板块=CURRENT |
| 8 | `SECTOR_DIVERGENCE` | 原板块不再 CURRENT，且同起点股票与原板块收益差绝对值≥.05 |
| 9 | `WEAKENING` | `C<MA20` 或 RPS20 在连续 3 个可比主会话严格下降；尚未 invalidated |
| 10 | `WAIT_CONFIRMATION` | 来源 EARLY/SETUP，等待谓词可评且未确认 |
| 11 | `EXITED_FOLLOW_UP` | 已退出且上列均不成立；保留 `LIST_EXITED` 标签 |
| 12 | `UNCLASSIFIED` | 事实完整但无合同规定的主状态命中；不可暗示强弱 |

`SIDEWAYS_RANGE`：最近 5 个连续、真实 BAR 的 `max(H)/min(L)-1≤.08` 且尚未失效，作为副标签，不覆盖 WEAKENING。`HAD_DIRECT_ADVANCE`：从首次至今 MFE≥.03、从未发生 `DD_CURRENT≤-.03`，且当日 close 距 close peak 不低于 -.03；一旦为真可保留为 lifetime tag，不能作为永久主状态。股票强于弱板块、弱于强板块、同步回调、原板块失效等均是 secondary linkage tags；任一必需侧 U 时为 `LINKAGE_UNKNOWN`。

板块同样先求谓词再按固定优先级选首个 TRUE：

| 顺序 | 主状态 | 必需 TRUE 条件 |
|---:|---|---|
| 1 | `DATA_UNAVAILABLE` | 必需成员/覆盖/可比或价格事实 U |
| 2 | `SECTOR_STRUCTURE_DAMAGED` | 冻结板块 invalidation AST=T；原 V2“掉榜且相对强度负”不得被跟踪层自行改写为失效 |
| 3 | `SECTOR_ACCELERATING` | 来源 CURRENT，SRET1>0、SREL>0、SWIDTH 不低于前可比日、RETENTION≥.50 |
| 4 | `SECTOR_HEALTHY_PULLBACK` | 冻结篮子 `SDD∈[-.08,-.02]`、来源 CURRENT/EARLY、SREL≥0、覆盖通过 |
| 5 | `SECTOR_DIFFUSION_WEAKENING` | SWIDTH 较信号日下降≥.15 或 RETENTION<.50，且未失效 |
| 6 | `SECTOR_ROTATION` | 来源仍合格、原领涨成员退出而新领涨成员进入、Jaccard/覆盖通过 |
| 7 | `SECTOR_EARLY_WAIT` | 来源 EARLY，等待条件未失效 |
| 8 | `SECTOR_PERSISTENT` | 来源 CURRENT，未命中更高优先级 |
| 9 | `SECTOR_EXITED_FOLLOW_UP` | 已退出而未命中更高优先级 |
| 10 | `SECTOR_UNCLASSIFIED` | 事实完整但无规则命中 |

`SWIDTH` 以原板块强势判定合同的成员谓词为准；若该谓词或信号日基准宽度不存在，依赖它的状态 U，不能临时发明“强势成员”定义。板块 membership 退出和 path 结构破坏始终分开。以上优先级是 V2.1 对 V2 冲突项的最终取舍；效果统计在真实前瞻证据前不得反向改表。

## 19. 数据结构、事务与查询边界的逐项约束

`focus_runs` 增加 `source_authority_contract_id`、`source_family_set`、accepted revision、activated UTC、`core_publication_status`、`outcome_settlement_status`；每族能力另有完整性字段。`focus_daily_items` 的主键固定为 `(focus_run_id,source_family,entity_type,entity_id)`，列式保存来源等级/排名和源 row key/digest/contract，JSON 只放变长证据。`focus_episode_transitions` 明确 `transition_trade_date/effective_trade_date/confirmation_trade_date`；首版三者同日，不用未来日回写旧 transition。`focus_episode_observations` 禁止模糊 `episode_state` 和单值 `return_since_current_entry`，保留六维状态、comparison gap、entry/current sector、first-supported anchor、adjustment source hash、事实与质量摘要。outcome 主键固定 `(anchor_id,horizon,target_revision)`。

### 19.1 表字段和可空边界

以下是首版最小必需列，允许额外审计列，但不能改变主键或用 JSON 替代需筛选/关联的列。

| 表 | 必需非空列 | 允许 NULL 的条件 |
|---|---|---|
| `focus_runs` | run ID、date、revision、publication ID、source authority、family capability map、输入摘要、calendar/price/contract/parameter/dependency 身份、core status、created UTC | activated UTC 仅未激活时 NULL；settlement status 在 core 发布前可 NULL |
| `focus_daily_items` | run/source family/entity type/entity ID、source row key/digest/contract、membership、quality、原始 source facts 摘要 | rank、主场景、主支持板块仅来源无该字段时 NULL，不填 0/空字符串冒充 |
| `focus_episodes` | episode ID、source family/entity、first trade date、selection contract family、first run、episode status | parent 仅首次 episode 为 NULL；confirmed/effective exit 与 completed date 未发生时 NULL |
| `focus_episode_segments` | segment ID、episode ID、类型、source model/state contract、参数集、起始日、boundary reason、run | 结束日仅开放 segment 为 NULL |
| `focus_episode_transitions` | episode ID、run/revision、transition/effective/confirmation dates、类型、前后 membership、reason codes | 不允许空日期或把 UNKNOWN 存成 NULL |
| `focus_episode_anchors` | anchor ID、episode ID、类型、交易日、run/revision、来源 fact digest、price basis | 无 actual BAR 时 reference price 为 NULL 并带质量原因；无原主板块时 FIRST_SUPPORTED 尚不存在 |
| `focus_episode_observations` | episode ID、trade date、source revision、run、六维状态、quality、continuity quality、fact digest、evaluation mode | 价格、RPS、收益、entry/current sector、first-supported anchor 按实际能力可 NULL，必须有逐字段缺失原因 |
| `focus_episode_outcomes` | anchor ID、horizon、target revision、target trade date、status、basis、输入摘要、reason codes | forward return/MFE/MAE/MDD 在非 OBSERVED 时 NULL；observed UTC 未结算时 NULL |
| `focus_outcome_heads` | anchor ID、horizon、accepted target revision、activated UTC | 不允许空指针或指向未完成 outcome |
| `focus_stock_sector_links` | focus run、security ID、sector ID、relation type、support/LOO status、是否主支持、关系来源摘要 | 原入选时无任何支持关系则无行，不生成虚构 NULL sector 行 |
| `focus_current_projection` | source family/entity、latest run/date、六维摘要、projection digest | 当前 active episode 可在已退出/完成时 NULL，但 last episode ID 保留 |
| `state_evaluations` 与 facts | episode、日、source revision、state/parameter contract、AS_RECORDED 或 REINTERPRETED、predicate ID、operand mode、结果与证据摘要 | actual/threshold 可因 U 而 NULL，必须保存 reason code |

所有日期列用 PG `date`，UTC 事件用 `timestamptz`，价格用固定十进制精度或与现有分币合同无损等价类型，禁止以展示字符串入库。JSONB 只承载变长来源证据、谓词树和 reason 列表；核心标识、状态、质量、run/revision、日期、rank、价格和 outcome 数值列式化。`source_family/entity_type/entity_id` 的实体代码以 source contract 规范化，股票名称和板块名称只作展示，不入键。外键至少约束 run→publication、item→run、episode/segment/transition/anchor/observation→run/episode、outcome→anchor、两个 head→已接受 run/outcome；无需每个来源列都复制一份无外键文本。

### 19.2 唯一性与只追加规则

`focus_runs` 唯一 `(trade_date,source_authority_contract_id,revision)`；`focus_daily_items` 主键见上；episode 业务唯一键为第 5.2 节的五元组；segment 唯一 `(episode_id,segment_type,start_trade_date,source_model_contract_id,state_contract_id)`；transition 唯一 `(episode_id,focus_run_id,transition_type)`；anchor 唯一 `(episode_id,anchor_type,focus_run_id)`，允许不同日多次 CURRENT_UPGRADE；observation 唯一 `(episode_id,trade_date,source_revision,evaluation_mode,state_contract_id)`；outcome 主键见上。相同键不同摘要视为冲突；同日 revision 必须用新键追加。历史事实、合同、评价及 outcome 行只追加；current projection、trade date head、outcome head 和显式任务状态是允许事务更新的派生/指针层。

Core transaction 在一个 PG 事务内校验来源摘要，插入 immutable run/items/evaluations/episodes/segments/transitions/anchors/当日 observations，重建投影，标 READY/ACTIVATED，并更新唯一 Focus head；提交前所有 FK、数量、主键、日期和摘要通过。旧 head 直到事务提交仍可读；失败不产生半成品。Outcome transaction 只处理已到期 anchors、幂等插入新 target revision 和结算状态；失败不修改 core head。页面不能做业务推断，只读已物化结果。对历史日修订的受影响后继 head，必须执行第 15.2 节重放链规则。

PostgreSQL 物化表长期保存身份和解释最小充分事实，逐日大行情仍在版本化 Parquet；页面绝不因节省存储删除已发布解释。`focus_current_projection`、分页缓存和成功导入的 staging 可按引用及摘要合同清理。上线前须用真实行数估算活动池、退出后池、每 episode 平均观察会话和单日入库字节；告警监控池增长、重复键冲突、逾期 outcome 和历史重放积压，不能用任意人数硬截断 tracking union。

## 20. 固定反例与验收矩阵

| 反例输入 | 必需输出 |
|---|---|
| 同股同日在 V3 shortlist 与 V3.3 候选 | 两个来源 membership/episode；共享行情事实只算一次 |
| EARLY→CURRENT→EARLY→CURRENT | 一个 episode、两枚 CURRENT_UPGRADE anchors、相应四次状态事实 |
| 仍在 CURRENT，冻结失效 AST=T | membership=CURRENT、validity=INVALIDATED；无伪 EXIT |
| 板块完整发布日掉榜，次日重入 | 当日 EXIT，次日新 episode；无 provisional miss 或回溯 |
| 整族失败/0 行未核验 | UNKNOWN；不因缺行退出 |
| 同日 source revision 改榜，后续日已发布 | 同日新 run/head；后继显式重放或冻结，不沿用旧链 |
| 来源场景变或 tracker 阈值升级 | 场景 transition/interpretation segment；不切 episode |
| 来源选择合同族变化 | 新身份基线与边界关联；不标市场 NEW/EXIT |
| 缺 actual BAR、只有推断 gap | 无伪 close/收益；连续谓词 U；不得宣称停牌 |
| 停牌有审计证据、随后复牌 | SUSPENDED 与实际复牌 BAR 分明；不把复牌日当原 T+N |
| 首日无板块支持，后来获得支持 | entry sector 仍 NULL，current sector 更新，建 FIRST_SUPPORTED |
| 退出后仍有升级/失效/退出 anchor 待结算 | 留在池内；全部必需 outcome 终态后才完成 |
| 完成后历史来源修订 | 显式 reopened revision 链，旧记录保留 |

每条反例须核验 PostgreSQL 实际行、head、逻辑摘要、API 输出和页面日期标注；纯单元测试不足以建立上线接受。首版发布前由独立审计检查所有状态标签可追溯到输入、AST、参数、评价模式和 run identity。

## 21. 阶段记录

| 字段 | 结果 |
|---|---|
| stage | `FOCUS_TRACKER_FINAL_DESIGN_20260923` |
| stage_contract | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1` |
| evidence | 本文第 1 节三份设计/审计源、`POSTGRES_MIGRATION_INDEPENDENT_REACCEPTANCE_20260923`、现行项目 guardrails |
| prior_phase_0 | `FULL_PASS_TDX_NATIVE`（既有 release seal） |
| migration_precondition | `FULL_PASS / CURRENT_MIGRATION_DATA_ACCEPTED`；Focus schema/head 仍待实施 |
| acceptance_result | `FULL_PASS / DESIGN_CONSOLIDATED`；仅表示设计合并完成，不表示模块已上线 |
| code/config/database_changed | 否 / 否 / 否；仅新增本设计文档 |
| tdx_access_or_write | 未访问 / 未写入 |
| next_stage | `FOCUS-00`：将本文第 14–20 节落实为九类子合同与反例回执，随后进入 PG Focus schema |
