# V4-00B Security Lifecycle / Universe / PIT 阶段回执（2026-09-25）

| 字段 | 记录 |
|---|---|
| stage | `V4-00B / SECURITY_LIFECYCLE_UNIVERSE_PIT` |
| stage_contract | V4.2.2 REV2 §5.1–5.3、§6A、§7.10、§78：冻结日期有效身份、知识时间、历史覆盖与不支持范围；当前 Universe 不冒充历史 PIT Universe。 |
| consulted_upgrade | 正式 REV2 文档 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`；当日再次确认 SHA 未变。复审 SHA-256 `8ae62a108262ddb63c42457c0920e0418b8df1013c26263edb3b3e34de8b4747`。REV2 §7.10 已明确 `REVISIONABLE_FACT_META_V1` 展开字段及生命周期迟到更正验收。 |
| input_identity | HEAD `3ef5bf63455447dd605534dc4c1717eb238a86f5`；TDX 根目录配置 `D:/new_tdx`。只读盘点 `D:/new_tdx/vipdoc`：21,531 个文件、4,743,047,776 bytes，含 `.day` 和 `.lc1`；未读取/修改 TDX 文件内容。旧 Phase 0 日线审计（2026-09-13）记录 12,245 个日线文件、29,428,636 条记录，覆盖 1990-12-19 至 2026-09-10；此为当时行情 bar 覆盖，不是历史证券身份覆盖。 |
| execution_boundary | 读取 REV2、代码/配置/已有审计；对 PostgreSQL 只读查询相关表的元数据和行数。没有 scanner、历史重建、下载、数据库写入或 TDX 写入。 |

## 当前身份与 Universe 行为

- `config/universe.yaml`（SHA-256 `cb77dd2810f72570658a49d75f834c83679ba6a931cf6c10f00d12361bfc001e`）指定 `MARKET.CODE`、`A_STOCK`、120 条历史记录、最近 20 个市场会话覆盖率至少 0.75、要求最新主会话有 raw bar；来源基准为 `TDXHY_CURRENT_A_SHARE_MEMBERS`。
- `src/normalize/universe_recent.py`（SHA-256 `cb476ea8711496dab31407377090e0b67e8cefb9401cfcd6042f5dfa91e1f6cc`）将 `timeline.current_member`、文件存在/结构有效、历史条数、近期覆盖、最新 bar 合并成 `normal_universe`。`src/phase0_1_runner.py` 与 `src/tdx/tdx_audit.py` 显示证券主档由当前 `tdxhy.cfg` 行业分配、本地 TNF 名称和冻结代码规则建立；这不是历史生效区间身份来源。
- 当前生产输出已明示 `membership_basis=CURRENT_TDX_MEMBERSHIP`、`pit_membership=false`、`historical_backtest_safe=false`。故旧逻辑可描述为“当前成分的当日 Universe”，不能直接用于历史 RPS、breadth、sector percentile 或 matched-control 样本。
- 旧配置没有冻结 ST、北交所、上市天数、长期停牌等 Research Universe 纳入/排除决定。依 §5.1，本阶段不把这些规则从文件名、当前代码或市场习惯推断出来；`V4_RESEARCH_UNIVERSE_V1` 的实体筛选矩阵仍需单独合同准入。

## PIT 元数据与可评估范围

REV2 锁定如下合同语义，供 V4-00C 及后续数据阶段实现：

1. 证券生命周期、身份、ST/board/security_type 和板块成员修订均显式带 `effective_from/to`、`provider_available_at`（可未知）、`observed_at`、`ingested_at`、`system_available_at`、`source_revision_id`、`supersedes_revision_id`、`source_identity`。`system_available_at=max(observed_at,ingested_at)`；供应商公开时间不能代替本系统当时可消费时间。
2. `AS_RECORDED(T0)` 只消费该 publication 冻结的 `publication_consumed_sources` key/revision/digest；还需满足有效时间覆盖 T0 且 `system_available_at<=cutoff`。同一事实按修订链取 cutoff 内唯一末端；分叉、内容冲突或顺序不明为 `SOURCE_REVISION_CONFLICT`，不得按最大时间猜选。
3. append-only 原始事实与 tombstone 保留。T+N 才录入、但有效日早于 T0 的更正，只能进入独立的 `RECONSTRUCTED_CORRECTED` lineage；不得改变 T0 当时已冻结的 Universe digest、发布消费集合或 Forward enrollment。
4. bar 缺失只表达缺失，不能推成停牌、退市或证券不存在；停牌须有日期有效证据。退市、停牌、DATA_GAP、UNKNOWN 与涨跌停是不同维度，金额/换手等缺失不能填零。
5. 历史 evaluable universe 必须逐日有 universe contract/digest/count。若只有当前成分可用，`universe_basis=CURRENT_UNIVERSE_REPLAY` 且仅为 `DIAGNOSTIC`；不得用于正式历史 RPS/breadth/controls 或真实 PIT 效果声明。

## 现场能力证据与范围

- 实时只读 PostgreSQL 查询发现 `workbench` 与 `legacy` 中 `security_metadata_versions`、`security_versions`、`universe_state_daily`、`membership_snapshots`、`membership_snapshot_metadata`、`membership_entries`、`publication_memberships`、`sector_membership_changes`、`online_security_map` 均为 0 行；`security_lifecycle_history` 与 `sector_membership_observations` 不存在。`queue_memberships` 有行，但其为发布候选队列，不构成证券生命周期或 PIT 板块成员事实。
- 因而当前能力分级为：本地历史价格 bar = 有历史覆盖证据；当前有效证券列表 = CURRENT snapshot；逐日历史证券生命周期/PIT identity = `UNAVAILABLE`；历史成分归属 = `UNAVAILABLE`；由当前成分回放得到的历史横截面 = `DIAGNOSTIC_ONLY`；迟到更正的真实 AS_RECORDED 证明 = `UNAVAILABLE`，须待消费 manifest/revision 写入链实施并验收。
- 禁止支持的推断：从最近 bar 推定仍上市；从无 bar 推定停牌/退市；从当前主档反推过去的 ST、board、security type；用 survivor-only 当前 Universe 为退市股票补不存在的历史 membership；将历史价格行数等同于 PIT 横截面覆盖。

## 独立审计与阶段判定

- `AUD-HIST-01` 保持 `OPEN`，其范围包括历史成员/PIT Universe、跨日派生状态、同日/前视隔离和生命周期验证；本阶段新增“真实证券 lifecycle/security identity 元数据当前空缺”的现场证据及数据限制，不关闭该审计项。
- V422-B07（AS_RECORDED 实际消费版本）仍为 `OPEN`，需由 V4-00C 的精确消费 manifest、冻结前驱和实际接收时间实现/验证。V4-00B 只冻结语义，不宣称历史实际观察链已经存在。
- **接受结果：`DEGRADED_PASS / CURRENT_UNIVERSE_ONLY_PIT_UNAVAILABLE`。** 日期有效合同语义、旧 Universe 实际行为、知识时间与能力边界已记录；正式 PIT 历史身份/Universe 不可用。此结果不是 PIT replay、历史 scanner 或新 Research Universe 发布许可。
- **下一阶段：`V4-00C / PUBLICATION_REVISION_NAMESPACE`。** 执行前重读当时最新 REV2/复审，冻结 publication 前驱、consumed-source manifest、修订/tombstone、原子接受及 namespace 隔离合同；V4-00H Phase 0 总门完成前仍不启动 scanner。
# Repair addendum (2026-09-25): `DEGRADED_PASS / CONTRACT_COMPLETE_WITH_DECLARED_HISTORICAL_LIMITATIONS`

Machine contracts were added at `config/v4_research_universe_v1.json`, `config/v4_security_lifecycle_fact_v1.json`, and `config/v4_pit_membership_fact_v1.json`; the fresh PostgreSQL schema stores effective interval, system-available time, source revision, supersedes, source identity, and quality. Current membership replay remains diagnostic. Missing bars remain unknown and never imply suspension/delisting. Historical PIT lifecycle/membership is explicitly unavailable pending V4-01 bootstrap and append-only observations; this is nonblocking for V4-01 RAW A-stock bootstrap.
