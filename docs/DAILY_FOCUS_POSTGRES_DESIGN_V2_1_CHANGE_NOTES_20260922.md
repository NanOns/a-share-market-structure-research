# 每日关注与 PostgreSQL 迁移方案 V2.1 修改优化说明

> 文档版本：`DAILY_FOCUS_POSTGRES_DESIGN_V2_1_CHANGE_NOTES`
> 日期：2026-09-22
> 基线：`DAILY_FOCUS_FOLLOW_UP_DESIGN_V2_20260922.md`
> 配套审计：`FOCUS_TRACKER_INDEPENDENT_AUDIT_DISPOSITION_20260922.md`、`POSTGRES_FULL_MIGRATION_INDEPENDENT_AUDIT_DISPOSITION_20260922.md`。
> 状态：`DESIGN_CORRECTION_PROPOSAL / NO_IMPLEMENTATION`。

## 1. 修改目标

V2 的总体架构继续保留，不重写、不另立 V4。V2.1 只修订实施前会造成错误身份、错误 outcome 或双权威的问题：

1. 明确三类研究来源各自权威；
2. 把 membership、validity、followup、path 拆成正交状态；
3. 用 anchors 真正支持首次、升级、退出和失效后的走势；
4. 新 Focus episode 与旧 V3.3 Forward episode 分离；
5. 退出对象通过 tracking union 获得后续每日事实；
6. PostgreSQL 成为所有 runtime head 的唯一权威；
7. 迁移覆盖文件型 Forward、外部 artifacts、时间语义和 mutable 表；
8. API 和常驻服务彻底退出 DuckDB/Parquet 即时扫描。

## 2. 保留不变的 V2 决策

- PostgreSQL 作为唯一在线服务主库；
- Parquet 保存大体量历史；
- DuckDB 只做离线、内存或任务独立临时分析；
- TDX 目录只读；
- 不建设长期 DuckDB/PG 双写；
- Daily Snapshot 不可变，同日 revision 不覆盖；
- `AS_RECORDED / REINTERPRETED` 分开；
- UNKNOWN 不当 FALSE；
- 历史重构与 REAL_FORWARD 分开；
- 描述性统计不冒充概率或交易建议；
- 旧 DuckDB 未经单独决策不删除。

## 3. Chapter 4 产品模型修改

### 3.1 新增 Source Authority

```text
V3_SHORTLIST_STOCK
V3_SECTOR_TRACK
V3_3_TODAY_CANDIDATE
V3_SHORTLIST_INDIVIDUAL（保留，首版非默认）
```

不同 source family 的 membership、rank、scenario 和 episode 分开保存。页面可以聚合展示，但每行必须显示来源。

### 3.2 Episode 改为 Episode + Segment + Anchor

```text
Episode  连续关注生命周期
Segment  source model / tracker state contract 有效区间
Anchor   FIRST_FOCUS / CURRENT_UPGRADE / EXIT_EFFECTIVE /
         INVALIDATION / FIRST_SUPPORTED / MILESTONE
```

旧 V3.3 episode 保留为 legacy identity，只建立关联，不原位改造。

### 3.3 六维状态

替换 V2 的单一 episode/path 表达：

```text
source_membership_state
membership_phase
validity_state
followup_state
current_path_state
lifetime_path_tags
```

INVALIDATED 不自动等于 EXITED，也不自动关闭仍被源算法关注的 episode。

## 4. Chapter 7 数据模型修改

### 4.1 `focus_runs`

新增：

```text
source_authority_contract_id
source_family_set
accepted_revision
activated_at_utc
core_publication_status
outcome_settlement_status
```

### 4.2 `focus_daily_items`

建议主键：

```text
PRIMARY KEY(focus_run_id, source_family, entity_type, entity_id)
```

新增：

```text
source_family
source_item_key
source_item_digest
source_contract_id
source_focus_class
source_membership_state
membership_phase
validity_state
current_path_state
lifetime_path_tags
```

`focus_type` 不再作为允许同源重复行的主键组成部分。

### 4.3 `focus_episodes`

只保存连续 membership 生命周期：

```text
episode_id
source_family
entity_type
entity_id
first_trade_date
confirmed_exit_date
effective_exit_date
parent_episode_id
episode_status
```

### 4.4 新增 `focus_episode_segments`

```text
segment_id
episode_id
segment_type
source_model_contract_id
state_contract_id
parameter_set_id
start_trade_date
end_trade_date
boundary_reason
```

### 4.5 新增 `focus_episode_anchors`

```text
anchor_id
episode_id
anchor_type
trade_date
source_revision
focus_run_id
reference_price
price_basis
source_fact_digest
```

### 4.6 修改 `focus_episode_transitions`

明确：

```text
transition_trade_date
effective_trade_date
confirmation_trade_date
transition_type
from_membership
to_membership
reason_codes
```

首版不使用板块 provisional miss，因此三个日期通常相同；字段保留以支持未来版本，但不得回写历史 AS_RECORDED。

### 4.7 修改 `focus_episode_observations`

新增：

```text
source_membership_state
membership_phase
validity_state
followup_state
current_path_state
lifetime_path_tags
continuity_quality
comparison_gap_sessions
entry_primary_sector_id
current_primary_sector_id
first_supported_anchor_id
adjustment_source_hash
```

移除模糊的单值 `episode_state` 和 `return_since_current_entry`。

### 4.8 修改 `focus_episode_outcomes`

主键改为：

```text
PRIMARY KEY(anchor_id, horizon, target_revision)
```

状态增加：

```text
DATA_GAP
SUSPENDED
DELISTED
```

### 4.9 新增 `focus_trade_date_heads`

```text
trade_date
source_authority_contract_id
accepted_focus_run_id
accepted_revision
activated_at_utc
PRIMARY KEY(trade_date, source_authority_contract_id)
```

只有 READY + ACTIVATED run 才能成为下一日状态前态。

## 5. Chapter 10 算法逻辑修改

### 5.1 状态执行顺序

```text
1. 解析 accepted publication/research/bundle heads
2. 按 Source Authority 读取今日 membership
3. 读取上一 accepted focus head
4. 建 tracking union
5. 离线物化 tracking union 当日 facts
6. 计算 source membership 与 membership phase
7. 评估 invalidation AST → validity
8. 评估 current path 与 lifetime tags
9. 追加 transitions / segments / anchors
10. 写 daily items 与 observations
11. 重建 current projection
12. 原子激活 focus head
13. 独立结算 due outcomes
```

### 5.2 删除首版板块 miss tolerance

删除 `SECTOR_MISS_TOLERANCE=1`。完整 accepted 日中不再入选即退出；失败/UNKNOWN 日不制造退出。未来若真实数据证明频繁边界抖动，再以新合同引入确认机制。

### 5.3 Path 状态

- `WEAKENING` 优先于 `SIDEWAYS_WAIT`；
- `SIDEWAYS_RANGE` 作为 secondary tag；
- `DIRECT_ADVANCE` 改为 `HAD_DIRECT_ADVANCE` lifetime tag；
- `TOO_EXTENDED` 继续风险优先；
- 阈值继续标 candidate，不用于效果声称。

### 5.4 Invalidation compiler

不强制修改源 scanner。新增 `FOCUS_INVALIDATION_COMPILER_V1`，明确 `CURRENT_FIELD / FROZEN_SIGNAL_VALUE / FROZEN_EPISODE_VALUE / DERIVED_DYNAMIC_FIELD`。

### 5.5 连续条件

缺 actual bar 的主交易会话使连续谓词 UNKNOWN，不跨缺失日拼接“连续两日”。实际参与日期写入 evidence。

### 5.6 复权路径

新增 `FOCUS_PATH_PRICE_BASIS_V1`：每个 observation 以当日 t 为共同 affine anchor 重算 signal→t 整段窗口的 close/high/low，再计算累计收益、MFE、MAE 和回撤；不得混合不同日期各自锚定的历史调整价。

## 6. Chapter 13 数据迁移修改

### 6.1 PGM-00 拆分

```text
PGM-00A database consumer catalog
PGM-00B real database catalog
PGM-00C artifact/pointer catalog
PGM-00D timestamp/change-capture catalog
```

### 6.2 PG schema

- 新建 `PG_SCHEMA_V1`；
- 007—035 只作为 legacy migration evidence；
- 不复用 DuckDB MigrationExecutor；
- 不把 `DatabaseMigration` 文件复制功能冒充跨引擎迁移。

### 6.3 全部 runtime heads 迁移

新增 `research_bundle_heads` 等 PG 权威表，文件 pointer 退为兼容缓存。PostgreSQL 事务只引用已经完整落地并校验的 immutable artifact。

### 6.4 文件型 Forward 纳入迁移

V3.3 observations、outcome plan/results、evaluation sources、R4 artifacts 均进入 ArtifactCatalog，逐类决定 IMPORT/RETAIN/LEGACY。

### 6.5 每表变更策略

迁移 catalog 增加 `change_capture_strategy`，最终切换优先使用短维护窗口和 mutable 表全量重载，不建设复杂 CDC。

### 6.6 时间与路径

- 每个 DuckDB TIMESTAMP 逐列确认 UTC instant 或 local wall time；
- absolute path 转 managed root + relative path + artifact_id；
- 旧绝对路径只保留为迁移证据。

### 6.7 跨引擎摘要

- 应用层 bytewise PK 排序；
- canonical JSON；
- IEEE binary64 候选编码；
- Decimal scale、NULL 和空值严格区分。

### 6.8 API 退出分析引擎

切换门同时扫描 HTTP 路径中的 `duckdb.connect()` 和 `read_parquet()`，不只扫描生产数据库文件名。

### 6.9 Backup

旧 DuckDB backup 标注 legacy engine；PostgreSQL 建独立 backup/restore contract 并完成真实恢复演练。

## 7. 事务边界优化

```text
Core Focus Publication Transaction
  focus run/items
  episode/segment
  transitions/anchors
  today observations
  projection/head

Outcome Settlement Transaction
  due anchor plan
  materialized outcomes
  settlement receipt/status
```

历史 outcome 异常不阻断今天的关注状态发布。

## 8. 页面与 API 修改

- 一级菜单仍为“关注跟踪”；
- 页面增加来源筛选和来源标签；
- “当前/提前观察”默认显示 V3 shortlist + sector track；
- V3.3 今日候选作为独立页签，不伪装成 CURRENT/EARLY；
- 详情同时显示 source membership、validity、followup、current path 和 lifetime tags；
- 退出后页面按 EXIT_EFFECTIVE anchor 展示 T+N；
- 每次请求固定 focus_run_id，不多次查询 latest；
- PG 不可用时 503，不回退旧 DuckDB 或文件 pointer。

## 9. 不采纳或暂不实施

| 建议 | 决定 | 原因 |
|---|---|---|
| 首版板块 provisional miss + 次日确认 | 不实施 | 增加后见语义和状态复杂度；先按 accepted 日事实立即退出 |
| 复杂 CDC | 不实施 | 本地系统可用迁移演练 + 短维护窗口更稳 |
| 现在确定 PG 分区/索引数量 | 暂缓 | 缺真实 PGM-00 行数与查询基准 |
| 强制 COPY 所有表 | 不强制 | 大表优先，最终由基准决定 |
| 强制 advisory lock | 条件采用 | 唯一键/单 writer 已可满足时作为防御性机制 |
| INDIVIDUAL 默认进入长期跟踪 | 首版不做 | 不在本次用户明确范围；数据继续迁移保留 |
| 把现有 V3.3 episode 原位升级 | 不采纳 | 会破坏旧 Forward 身份和效果证据 |
| 在 DuckDB 先建完整 focus schema | 不采纳 | 避免第二次 schema 迁移和双写风险 |

## 10. 待观察

- 状态阈值真实分布与解释价值；
- 是否启用 PRE-PG PIT capture；
- 是否需要未来引入板块 miss tolerance；
- entry-frozen basket 覆盖；
- 描述性样本门；
- PG 索引、分区、连接池和维护窗口大小。

## 11. 优化后的实施顺序

```text
Step 0  接受/修订三份本轮文档
Step 1  FOCUS-00：Source Authority、Episode/Segment/Anchor、状态合同冻结
Step 2  PGM-00A-D：源码、真实库、artifact、时间与变更策略只读盘点
Step 3  冻结跨引擎摘要和 ArtifactCatalog 合同
Step 4  PostgreSQL 基础设施、PG_SCHEMA_V1、backup restore drill
Step 5  Repository/ArtifactCatalog 收口
Step 6  冻结副本全量迁移演练和 API shadow read
Step 7  最终维护窗口与 PG heads 激活
Step 8  在 PostgreSQL 原生实现 Focus Tracker core
Step 9  连续真实交易日观察与退出后 outcome
Step 10 样本门达到后再开放统计复盘
Step 11 DuckDB 在线退役和只读归档
```

若预计 Step 1—7 跨越多个真实交易日且用户希望保留这些日子的前瞻来源，增加轻量 `PRE_PG_FOCUS_SOURCE_CAPTURE_V1`；它只封存 source rows 和身份，不生成后见状态。

## 12. V2.1 验收门

- 所有 source family 权威和主键明确；
- first/upgrade/exit/invalidation anchors 反例通过；
- EXIT/INVALIDATED/FOLLOWUP 正交组合通过；
- 旧 V3.3 episode 和新 Focus episode 不混用；
- tracking union 能覆盖已退出对象；
- AS_RECORDED 不被模型升级或未来事实覆盖；
- PG runtime heads 唯一；
- 文件型 Forward 和 artifacts 全部分类；
- 每张 mutable 表有切换策略；
- 时间列、路径和跨引擎摘要合同冻结；
- HTTP API 不再使用 DuckDB 或即时 Parquet 扫描；
- PG backup/restore drill 通过；
- Phase 0 为 FULL_PASS 或合同允许的 DEGRADED_PASS 后才进入下一阶段。

## 13. 阶段记录

| 字段 | 内容 |
|---|---|
| stage | `DAILY_FOCUS_POSTGRES_V2_1_CHANGE_PROPOSAL_20260922` |
| stage_contract | `DAILY_FOCUS_POSTGRES_DESIGN_V2_1_CHANGE_NOTES` |
| evidence | 两份本项目审计处置、设计 V2、当前 V3/V3.3 research/forward/bundle/schema/app/ops 实现 |
| acceptance_result | `DEGRADED_PASS / READY_FOR_USER_REVIEW`；修改项已定义，尚未形成正式 V2.1 主设计合同或实施代码 |
| code/config/database_changed | 否 / 否 / 否；仅新增修改说明 |
| tdx_access_or_write | 未访问 / 未写入 |
| next_stage | 用户确认后，将修改合并为正式 V2.1 主设计；随后执行 FOCUS-00 与 PGM-00，只读盘点先于实现 |
