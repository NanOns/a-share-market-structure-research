# V4-00C Publication / Revision / Namespace 阶段回执（2026-09-25）

| 字段 | 记录 |
|---|---|
| stage | `V4-00C / PUBLICATION_REVISION_NAMESPACE` |
| stage_contract | V4.2.2 REV2 §4.1–4.9、§6A、§78：冻结 publication 身份/修订、as-of 与输入消费、Prior-Session State、事件修订投影、Execution Namespace 和迁移前态。 |
| consulted_upgrade | 正式 REV2 SHA-256 `744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd`（执行前复核，未变化）；合同复审 `docs/audits/V4_2_2_CONTRACT_REAUDIT_20260925.md` SHA-256 `8ae62a108262ddb63c42457c0920e0418b8df1013c26263edb3b3e34de8b4747`。复审原记录仍是 `CONTRACT_INCOMPLETE`；REV2 是后续文档修订，不等于独立审计关闭。 |
| input_identity | HEAD `3ef5bf63455447dd605534dc4c1717eb238a86f5`；只读 PostgreSQL primary `market_research`。执行沿用 V4-00A/00B 回执，不改其历史。 |
| execution_boundary | 读取合同、schema、写入路径、Focus 事务实现并以 PostgreSQL `BEGIN READ ONLY` 统计当前记录；无 publication、Focus 或数据库写入，无 scanner/历史 replay/TDX 访问。 |

## V4 冻结合同

1. **Publication identity 与修订：** `publication_id` 稳定且不承担日期/参数 hash 编码；publication 必须显式绑定 `trade_date`、`revision`、status、source/computation identity 及 source manifest。每次同日修订追加新 revision，旧记录不可覆盖；唯一 current head 只指向已接受 revision。页面/API context 同步固定 `(trade_date, publication_id, core_revision, model_namespace, optional_enrichment_revision)`，迟到异步响应 token 不匹配即丢弃。
2. **Publication cutoff 与精确消费：** 每次发布冻结目标交易日、TDX 包及声明更新/观察时间、本地 TDX snapshot、membership/universe snapshot、mandatory/optional cutoff、计算起止及 accepted 时间；正式因子 `max_source_trade_date<=target_trade_date`。`AS_RECORDED` 只从该 publication 冻结的 `publication_consumed_sources(key, source_revision_id, digest)` 取源；source 的有效区间覆盖 T0 且 `system_available_at<=cutoff`。`provider_available_at` 不等于系统实际获知时间。
3. **Revision 与 tombstone：** source facts、tombstone、修订边 append-only；同一 fact 只可沿确定的 supersedes 链选择 cutoff 前唯一末端，分叉/冲突 fail closed。供应商早已公开但系统后来才采集的数据不进入过去 AS_RECORDED；迟到历史更正只能用新 `RECONSTRUCTED_CORRECTED` lineage，不改变原 publication、历史 Universe digest 或 Forward enrollment。
4. **Prior-session 与同日修订：** 首次生成 T 的 lineage 时冻结同模型上一市场会话 accepted publication 的 id/revision/logical digest。T 的 r1/r2/r3 共用该 prior-session head；same-day revision parent 仅用于差异追踪。若 r1 曾满足资格、r2 因数据更正撤销，追加 `RETRACTED` event observation；current projection 取 r2，原 PIT enrollment 保留并标注 `SOURCE_CORRECTION`，不得改写成市场失效。若 T-1 后来修订，不静默改写已冻结 T；需要传播时另建 corrected-reconstruction lineage 顺序重放。
5. **Core 与 supplemental 权限：** TDX core publication 决定资格/状态/Focus transition/Forward enrollment。BaoStock 后置 supplemental revision 可更新批准的换手/参与度/交叉核对/解释 UI，但不能改 core eligibility/state/focus transition；除非新的 CORE_SOURCE_CONTRACT 明确改变此权力。
6. **Execution namespace：** 状态账本每行绑定 `model_contract_id, execution_mode, namespace, publication_id, core_revision`。至少区分 `PRODUCTION_LEGACY`、`SHADOW_V4`、`PRODUCTION_V4`；shadow 只读取自身前态。State lineage id 与 namespace 不同义。Shadow→Production 需显式 migration manifest，继承最后 Shadow 前态与 episode mapping；不同模型以 `MODEL_BOUNDARY` 开新 cohort。未结 follow-up/outcome 保留原来源并继续结算。
7. **能力/证据分类：** 唯一 `evidence_origin`=`PIT_OBSERVED / RECONSTRUCTED_ASOF / RECONSTRUCTED_CORRECTED / DIAGNOSTIC_NON_PIT`；唯一 `execution_mode`=`PRODUCTION / SHADOW / REPLAY`。正式 Forward cohort 只收 PIT_OBSERVED，按 Shadow/Production 分层；同一 publication 的组件按实际依赖的最弱来源能力降级。

## 现有实现/生产库只读证据

- `src/workbench_db/schema.sql` SHA-256 `b3532f2490952df088ce1a22e697fa854d093d1dbc9a0d9c286e35c09cec82f4`：`publications` 有日期/修订唯一约束、status 和 source/computation/render hash 字段；`publication_heads` 按 trade_date 保存指针。没有 publication-level consumed-source manifest、data cutoff、model namespace 或 revision-event ledger 表。
- `src/workbench_db/postgres_publication_writer.py` SHA-256 `bfa86c0b64ceec1cc1ad5fe3a8140c2aef516c87ddca1618a5b07798ab8d5ceb`：提供 max revision + 1、publication insert、head upsert；DB schema 未见 append-only update/delete guard。`src/workbench_publish/service.py` SHA-256 `8483201ca1f67b9af50d92e79139465c0c32f8f7d131c5e4f67c9d29f60f5479`：当前 PostgreSQL 发布路径将 publication、结果行、head 和 job 状态放在同一数据库事务；这是旧 publication 路径的原子性证据，不代表 V4 精确源清单合同已实现。
- 实时只读数据库统计：`workbench.publications` 19 行，日期范围 2026-09-11 至 2026-09-24，全部 `SUCCESS`；其中 4 行的 `source_manifest_sha256`、`source_identity_sha256`、`computation_identity_sha256` 同时为空，19 行的 `render_identity_sha256` 均为空；`workbench.publication_artifacts` 0 行。`workbench.publication_heads` 10 行，当前所有 head 均指向同日 `SUCCESS` publication（dangling/date/status mismatch=0）。历史旧行不能被补造为完整 V4 身份。
- 数据库不存在 `publication_consumed_sources`、`publication_revision_events`、`model_namespaces`、`namespace_migrations`、`focus_events`、`focus_event_observations` 表。因此无法仅靠当前数据库重现每个 publication 实际消费的完整 source revision 集合或 V4 event-observation projection。
- `src/focus_tracker/input_manifest.py` SHA-256 `2ddc97228baf70ab74071b06137b5b40157e2764efa685354c02cced6771e572`：Focus 已构造 canonical input manifest/digest 并核对 accepted source bindings；这为 V4 借鉴输入闭包提供实现证据，但数据库 run 只存摘要/来源字段，并非可按 publication 查询的完整逐源消费账本。
- `src/workbench_db/focus_schema_v1.sql` SHA-256 `c680b361a262101b8ae323855ee7670ce2af5493e460c47e935140cb544f304d`：Focus 有 trade-date + authority 的 accepted head 和 predecessor run；`focus_runs` 绑定来源/日历/输入摘要、state contract、parameter、price/evaluation basis。表中没有 V4 `execution_mode/namespace/model_contract_id/core_revision` 完整身份，也没有 namespace migration manifest。当前实时 PG 有 2 个 `REAL_FORWARD / ACTIVATED` Focus run，2 个 head 均 `VALID`；本轮只读，不改变这些 head。
- `src/focus_tracker/core_activation.py` SHA-256 `4d50ebd6273f903be89261425cad0be350ba11a19562a1c068f31c6908b3856c`：Focus activation 在调用方事务及日期锁内激活 READY run、读取前一有效 head、同日递增 revision，并把后续有效 head 标为 `REPLAY_REQUIRED`。这是 Focus 子系统状态账本能力，不可替代 V4 的 `prior_session_state_head` digest 和独立 namespace。
- `docs/audits/FOCUS_SAME_DAY_REVISION_ORDERED_REPLAY_GAP_20260924.md` SHA-256 `ca957e7d0165e38effb404243610707f02b5c20499b5c8556c1e118922e74e28` 已关闭其代码/合成 PostgreSQL E2E 范围；其真实 Forward 门仍独立开放。不可把 Focus 的关闭状态泛化为 V4 关闭。

## 独立问题与接受结果

- V422-B06（事件观察修订、撤销投影、前驱冻结）和 V422-B07（publication 实际消费版本）在复审册中保持 `OPEN`。REV2 已补入确定性合同语义；仍需逐版本 schema/writer 实现和独立正反向验证，不能仅以本次文本盘点关闭。
- V422-B01/B03 及其他未关闭的合同冲突保持各自 scope；`AUD-HIST-01`、`AUD-AMOUNT-A-06`、`V4-00A-PG-RECOVERY-01` 继续独立跟踪，不由此阶段吸收或关闭。
- **接受结果：`DEGRADED_PASS / V4_CONTRACT_FROZEN_EXISTING_PG_GAPS_OPEN`。** V4 publication/revision/namespace 目标与修订语义已冻结；旧 publication/Focus 的事务、head 和回放能力已盘点；production 表缺精确消费清单、事件修订账本、完整摘要和 V4 namespace schema，故不能宣称实现验收、PIT 或 V4 publication readiness。
- **下一阶段：`V4-00D / TDX_VIPDATA_SOURCE_CONTRACT`。** 执行前重读当时最新 REV2 与审计回执，冻结官方数据包下载边界、有界请求、隔离 staging、manifest、校验/archive、重叠核验；所有输出留在项目路径，TDX root 永远只读。V4-00H 前不启动 scanner。
# Repair addendum (2026-09-25): `FULL_PASS / V4_EMPTY_DATABASE_PUBLICATION_NAMESPACE_SCHEMA_READY`

The fresh `v4` PostgreSQL schema now contains versioned publications, accepted heads, consumed-source manifests, revision events, explicit model namespaces and namespace migration manifests, namespace-bound state heads, and append-only event-observation revisions. Hash-checked migrations are `V4_PHASE0_FOUNDATION_V1` and `V4_PHASE0_NAMESPACE_INTEGRITY_V1`. Database tests prove same-day append-only revisions, accepted-head target checks, prior-state namespace isolation, source-revision fork rejection, and no rewriting a previous publication after a correction. The clean database contains no synthetic or accepted publication rows.

## R2 targeted repair addendum — 2026-09-25

R2 `f51e71ec8a3c02a5551bf07f66366856cf146182a76729b549871a680dcd0fe0` withdraws the former `(publication_id, revision)` identity model. Forward migrations now use a globally unique opaque `publication_id` for each physical revision, explicit `publication_lineage_id`/`revision_no`, unique namespace/date/core revision, a same-day parent FK with increasing sequence and single-successor index, and explicit market-calendar session predecessor/digest or gap. Publication heads and dependents reference the unique publication identity. 12 PostgreSQL schema tests pass; stage `FULL_PASS`.
