# 关注跟踪长期观察模块独立审计处置（2026-09-22）

> 合同：`FOCUS_TRACKER_INDEPENDENT_AUDIT_DISPOSITION_V1`
> 输入：用户提供的 `DAILY_FOCUS_AND_POSTGRES_MIGRATION_INDEPENDENT_AUDIT_20260922.md`、当前分支 `codex/algorithm-v3-incremental-upgrade`、提交 `180c741`、项目现行合同与设计 V2。
> 边界：外部审计仅作为问题清单；本文逐项以当前仓库源码和已封存证据裁决。本轮不改算法、代码、数据库或 TDX，不运行数据生成。

## 1. 总体结论

外部审计对长期观察模块的总体判断成立：方向正确，但 V2 的事件身份、退出锚点、状态正交性和运行 head 尚不足以直接实施。

本项目裁决为：

```text
DEGRADED_PASS / PREIMPLEMENTATION_CORRECTION_REQUIRED
```

不需要推倒重来，也不需要创建 V4。需要在实施前形成 V2.1 合同，关闭 10 个核心语义问题。

## 2. 当前代码证据

### 2.1 股票确实存在两套研究来源

- `research_shortlist` 支持 `CURRENT_FOCUS / EARLY_FOCUS / INDIVIDUAL`，由 `research_association.py` 生成，`/api/v3/research/shortlist` 和首页研究区读取。
- `research_candidates_v3_3` 保存 `LAUNCH_CONFIRM / RECOVERY_TURN / STRONG_PULLBACK / TREND_CONTINUE` 等 V3.3 类别，`/api/v3/research/today` 通过活动 bundle 文件读取。
- 两者不是同一分类体系，不能把 V3.3 候选自动改名为 CURRENT/EARLY，也不能只跟踪旧 shortlist 而遗漏 V3.3 今日候选。

### 2.2 旧 V3.3 episode 不能复用

`forward_v3_3.py::_episode_id()` 把 `primary_category` 放入身份；只有证券和主类别均不变才延续 episode。新关注跟踪要求“连续被同一来源关注时，场景变化只形成 transition/segment”，因此必须使用新身份合同，旧 Forward episode 只作关联证据。

### 2.3 当前 revision 选择不是正式业务 head

`canonical_observations()` 会在同一交易日优先选择 `market_strength/volatility` 更完整的 observation，再用 digest 排序。这适合旧报告生成，不适合作为下一交易日状态机前态。新模块必须有显式激活的 `focus_trade_date_heads`。

### 2.4 退出对象需要独立每日事实输入

活动 V3.3 bundle 只包含当天候选。股票或板块退出后，bundle 不再提供其后续 MA、RPS、价格和板块联动事实。每日输入必须是“今日关注对象 + 所有未完成后续观察对象”的 union。

### 2.5 文件仍是当前 V3.3 在线 head

`TodayResearchBundleReader` 直接读取 `data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json`、`results.json` 等文件，并在请求时补查 DuckDB。新模块不能继续从文件 mtime、目录或启发式 revision 决定当前版本。

## 3. Source Authority 决策

采纳外部审计 F-01，但不选择“只跟踪其中一套”。本项目已有两套有效且用途不同的研究输出，应显式分族，禁止静默合并。

| source_family | 权威来源 | 跟踪语义 | 首版页面位置 |
|---|---|---|---|
| `V3_SHORTLIST_STOCK` | `research_shortlist` | CURRENT/EARLY 个股生命周期 | “当前关注 / 提前观察”主区域 |
| `V3_SECTOR_TRACK` | `research_sector_states` | CURRENT/POTENTIAL 板块生命周期 | “当前板块 / 提前观察板块”主区域 |
| `V3_3_TODAY_CANDIDATE` | `research_candidates_v3_3` + accepted bundle head | 四类今日算法候选及后续表现 | 独立“V3.3 今日候选”页签 |
| `V3_SHORTLIST_INDIVIDUAL` | `research_shortlist(list_type=INDIVIDUAL)` | 历史兼容/独立个股研究 | 数据迁移保留；首版默认不进入用户要求的主跟踪列表 |

规则：

- 一个实体可同时属于不同 source family，各自拥有独立 source membership；
- 页面可以联查，但不得把不同来源的 rank、membership 或 episode 合并成一条无来源状态；
- `INDIVIDUAL` 不删除、不丢迁移数据，但本次用户范围未要求其成为默认长期跟踪对象；后续可作为独立页签启用；
- source row 必须保存 `source_item_key`、`source_item_digest` 和 `source_contract_id`。

## 4. 修订后的状态模型

### 4.1 六个正交维度

V2 的三层状态仍不够。V2.1 使用：

```text
source_membership_state   原来源当日事实
membership_phase          跨日进入/持续/升级/降级/退出/重入
validity_state            当时研究 thesis 是否仍有效
followup_state            后续观察任务是否进行/完成
current_path_state        当前最重要的价格/结构状态
lifetime_path_tags        episode 历史上曾发生过的路径标签集合
```

合法组合示例：

```text
source_membership_state = CURRENT
membership_phase        = PERSISTENT
validity_state          = INVALIDATED
followup_state          = ACTIVE_FOCUS
current_path_state      = STRUCTURE_DAMAGED
```

这表示“源算法今天仍把它列为当前关注，但原跟踪 thesis 已失效”。不能因为 INVALIDATED 就伪造退出，也不能关闭 source membership episode。

### 4.2 Episode 与 Segment

```text
Episode = 同一 source family 下，一次连续关注生命周期
Segment = episode 内某个 source model / tracker state contract 的有效区间
```

- source selection contract 变化：开启 `SOURCE_MODEL_BOUNDARY` segment；前后 membership 不解释为市场 NEW/EXITED；
- tracker 状态阈值或优先级变化：同 episode 新开 interpretation segment；不切断收益和持续时间；
- `AS_RECORDED` 永久保留；新规则回算写 `REINTERPRETED`，不覆盖旧状态。

### 4.3 新 Episode 身份

采用 `FOCUS_EPISODE_ID_V2_1`：

```text
source_family
entity_type
entity_id
episode_start_trade_date
source_selection_contract_family
```

不把 `primary_category`、当日排名或选择模式写入 episode PK。场景变化写 transition；退出后重入建立新 episode，并关联 parent episode。

## 5. Anchor 与 Outcome 决策

外部审计 F-02、F-13 正确，V2 的 first-focus T+N 不能回答“退出以后怎样”。

### 5.1 必需 anchors

| anchor_type | 建立时机 | 回答的问题 |
|---|---|---|
| `FIRST_FOCUS` | episode 首次正式关注 | 从第一次发现后怎样 |
| `CURRENT_UPGRADE` | 每次 EARLY→CURRENT | 从本次升级后怎样 |
| `EXIT_EFFECTIVE` | source membership 正式退出 | 退出以后怎样 |
| `INVALIDATION` | validity 首次变为 INVALIDATED | thesis 失效以后怎样 |
| `FIRST_SUPPORTED` | 独立个股首次获得有效板块支持 | 后来获得板块支持以后怎样 |
| `MILESTONE` | 长 episode 的版本化里程碑 | 长周期只读诊断 |

每次升级建立独立 anchor。Observation 不再使用模糊的 `return_since_current_entry`，改为 `first_current_anchor_id`、`latest_current_anchor_id`，收益由明确 anchor 计算。

### 5.2 Outcome 状态

采用：

```text
PENDING
OBSERVED
DATA_GAP
SUSPENDED
DELISTED
SOURCE_REVISED
```

并保存 reason code。EXIT/INVALIDATION 后仍结算已经计划的 outcome。

### 5.3 Episode 关闭

```text
source membership 已正式结束
AND 没有未决数据 gap/revision
AND 所有要求的 EXIT_EFFECTIVE outcome 已进入终态
```

INVALIDATED 不单独决定 episode 关闭。

## 6. 板块掉榜与后见回写裁决

外部审计正确指出 V2 的通用 EXIT 与 `SECTOR_MISS_TOLERANCE=1` 冲突。首版不实施 provisional miss 和回溯生效日，直接删除该容忍参数：

- 一个 accepted、完整、同 source contract 的交易日 run 中板块不在 CURRENT/POTENTIAL，则当日 `EXIT_CONFIRMED`；
- 数据不可用或整日 run 失败时状态为 UNKNOWN，不制造退出；
- 后续恢复时建立 REENTERED episode；
- 页面可以显示“一日后重入”，但不把两个 episode 后见合并；
- 未来若真实观察证明边界抖动严重，再以新合同增加双日期确认，不修改首版历史。

因此 F-05 的矛盾必须修；F-06 提出的双日期方案在首版不需要实施，但“禁止用未来事实回写前日 AS_RECORDED”保留为硬约束。

## 7. 每日事实计算范围

```text
TRACKING_UNION_t =
    今日所有正式 source membership
    UNION 未完成 followup 的历史 episode 对象
    UNION 今日需要结算 anchor outcome 的对象
```

离线任务生成 `focus_observation_input` versioned artifact，至少包含：

- 当日 actual bar、RAW/调整 OHLC、额量和数据状态；
- 当前/冻结锚点所需的 MA、RPS、结构与风险事实；
- 个股当时和当前板块关系；
- entry-frozen 与 contemporary 两套板块篮子事实；
- adjustment source/version、calendar、publication、snapshot 和 source row digest。

PostgreSQL 只接收最终 observation facts 和 artifact identity，不在 API 请求时计算这些指标。

## 8. Invalidation AST 裁决

采纳 F-10，但不直接改变 V3.3 scanner 核心输出。新增独立 `FOCUS_INVALIDATION_COMPILER_V1`：

```text
输入：scenario + signal facts + source scanner contract + tracker parameter set
输出：canonical predicate AST + frozen anchors + dynamic operand definitions + digest
```

AST operand 必须声明：

```text
CURRENT_FIELD
FROZEN_SIGNAL_VALUE
FROZEN_EPISODE_VALUE
DERIVED_DYNAMIC_FIELD
```

`CONSECUTIVE` 首版定义为连续主交易会话；任何会话缺 actual bar 时结果为 UNKNOWN，不把 D1 与 D3 跨缺口拼成连续两次。停牌/缺失的细分语义由数据状态合同提供。

## 9. Path 状态优化

- `current_path_state` 与 `lifetime_path_tags` 分开；
- 风险优先：`WEAKENING` 高于 `SIDEWAYS_WAIT`；横盘作为副标签；
- `TOO_EXTENDED` 继续优先于加速；
- `DIRECT_ADVANCE` 改为 lifetime tag `HAD_DIRECT_ADVANCE`，不长期占用当前主状态；
- 初始阈值 3%—12%、5 日 8%、RPS 连降 3 日等只标 `CANDIDATE_ENGINEERING_PARAMETERS`；在真实前瞻证据前不宣称有效，不自动调参。

## 10. 板块与个股关系

### 10.1 两套板块路径

- `ENTRY_FROZEN_BASKET`：episode 首日冻结成员，回答“当时关注的那批成员后来怎样”；
- `CONTEMPORARY_SECTOR_BASKET`：每天使用当时有效成员，回答“板块当前生态怎样”。

原 thesis 的峰值/回撤优先使用 entry-frozen basket，并要求覆盖门；当前板块状态使用 contemporary basket。两者不混算。

### 10.2 首次独立、后来获得支持

分别保存：

```text
entry_primary_sector_id
current_primary_sector_id
first_supported_anchor_id
```

不回填首次关系，也不让首次 NULL 阻断后续板块联动。

## 11. 核心发布与 Outcome 解耦

采纳 F-22：

- Core Focus Publication 原子事务包含 run、daily items、episode/segment、membership/validity transition、当日 observations、current projection 和 accepted head；
- Outcome Settlement 是独立幂等事务；失败只把 `outcome_settlement_status` 标为 DEGRADED，不阻断今天的新关注页面。

## 12. 外部审计逐项裁决

| 编号 | 裁决 | 本项目处理 |
|---|---|---|
| F-01 | 接受 / P0 | 建立 Source Authority，多来源分族，不静默合并 |
| F-02 | 接受 / P0 | 新增 exit、upgrade、invalidation 等 anchors |
| F-03 | 接受 / P0 | membership、validity、followup 正交拆分 |
| F-04 | 接受 / P0 | INVALIDATED 不关闭仍在榜 episode |
| F-05 | 接受问题，调整方案 / P0 | 删除首版板块 miss tolerance |
| F-06 | 原则接受，首版不采用双日期 | 禁止回写；立即退出使该复杂机制暂不需要 |
| F-07 | 接受 / P0 | 新 Focus episode，不复用旧 V3.3 episode PK |
| F-08 | 接受 / P0 | 只用显式 activated focus head |
| F-09 | 接受 / P0 | 每日 tracking union 独立物化事实 |
| F-10 | 接受 / P0 | AST 明确冻结/动态 operand mode |
| F-11 | 接受 / P1 | source model 与 tracker interpretation 分界 |
| F-12 | 接受 / P1 | Episode + Segment |
| F-13 | 接受 / P1 | 每次升级独立 anchor，去除模糊字段 |
| F-14 | 接受 / P1 | current path 与 lifetime tags 拆分 |
| F-15 | 接受 / P1 | WEAKENING 风险优先 |
| F-16 | 接受 / P1 | entry-frozen / contemporary 双板块路径 |
| F-17 | 接受 / P1 | entry/current sector 与 first-supported anchor |
| F-18 | 接受 / P1 | 保存 comparison gap 与 continuity quality |
| F-19 | 接受 / P1 | outcome 保留停牌/退市/数据缺口原因 |
| F-20 | 接受 / P1 | 主键按 source family 唯一，focus type 不入主键 |
| F-21 | 接受 / P1 | 源行 key/digest/contract 必存 |
| F-22 | 接受 / P1 | 冻结 rolling affine adjustment path contract |
| 事务拆分建议 | 接受 / P1 | core publication 不被历史 outcome 故障阻断 |
| PRE-PG capture | 条件接受 | 若迁移跨越真实交易日则启用；否则从 PG 正式日开始 |
| INDIVIDUAL 正式跟踪 | 首版不需要 | 数据保留、可查询，不进入默认用户范围 |
| 参数有效性 | 待观察 | 至少积累前瞻样本后独立审计 |
| 样本门 30/5 | 暂时保留 | 仅描述性显示门；用于调参时必须另设更高门 |

## 13. 实施前硬门

以下全部完成前，不开始页面实现：

1. `FOCUS_SOURCE_AUTHORITY_V1`；
2. `FOCUS_EPISODE_LIFECYCLE_V2_1`；
3. `FOCUS_MODEL_SEGMENT_V1`；
4. `FOCUS_ANCHOR_CONTRACT_V1`；
5. `FOCUS_VALIDITY_AND_FOLLOWUP_STATE_V1`；
6. `FOCUS_INVALIDATION_AST_V1`；
7. `FOCUS_PATH_PRICE_BASIS_V1`；
8. `FOCUS_REVISION_HEAD_V1`；
9. tracking union 事实物化合同；
10. 反例测试：双来源、多次升级、仍在榜但失效、退出后 T+20、数据失败日、场景切换、同日 revision、停牌/退市、独立后获板块支持。

## 14. 观察项

- 状态工程阈值是否能提供有效解释；
- 板块 entry-frozen basket 的历史覆盖是否足够；
- 同源频繁退出/重入是否需要未来引入 miss tolerance；
- PRE-PG PIT capture 是否需要启用；
- 描述性统计样本门是否需要提高；
- `INDIVIDUAL` 是否在后续版本开放独立跟踪页签。

这些事项不得在没有真实数据的情况下拍脑袋写成正式效果结论。

## 15. 阶段记录

| 字段 | 内容 |
|---|---|
| stage | `FOCUS_TRACKER_EXTERNAL_AUDIT_DISPOSITION_20260922` |
| stage_contract | `FOCUS_TRACKER_INDEPENDENT_AUDIT_DISPOSITION_V1` |
| evidence | 当前 shortlist/V3.3 schema、research association/query、V3.3 forward identity/revision、bundle reader、outcome materializer、P12-08/P12-16 合同与设计 V2 |
| acceptance_result | `DEGRADED_PASS / V2_1_CORRECTION_REQUIRED` |
| code/config/database_changed | 否 / 否 / 否；仅新增审计文档 |
| tdx_access_or_write | 未访问 / 未写入 |
| next_stage | 与迁移审计和 V2.1 修改说明共同评审；通过后进入 FOCUS-00 合同冻结，不直接开发页面 |
