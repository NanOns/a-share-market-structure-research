# FOCUS-03 输入 manifest 阶段记录

> 日期：2026-09-23；当前结果：`IN_PROGRESS / IMMUTABLE_STAGING_READY`。

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 7、10、14、15、19 节；`FOCUS_02_BASKET_STRENGTH_ACCEPTANCE_20260923.md` |
| prior_stage | FOCUS-02 `DEGRADED_PASS / FIRST_ACCEPTED_DAY_INPUTS_READY`；Phase 0 为 `FULL_PASS_TDX_NATIVE` |
| stage_contract | `FOCUS_DAILY_INPUT_MANIFEST_V1`、`FOCUS_DEPENDENCY_LOCK_V1`、`FOCUS_SOURCE_PATH_CAPABILITIES_V1`、`FOCUS_INVALIDATION_AST_V1`、`FOCUS_OBSERVATION_ASSEMBLY_V1`、`FOCUS_V33_SCANNER_FACT_BRIDGE_V1`、`FOCUS_CORE_INPUT_CLOSURE_V1`、`FOCUS_CORE_RUN_IDEMPOTENCY_V1`、`FOCUS_CORE_HEAD_ACTIVATION_V2`、`FOCUS_ORDERED_REPLAY_CHAIN_V1`、`FOCUS_CURRENT_PROJECTION_REBUILD_V1`、`FOCUS_CORE_PUBLICATION_GATE_V1`、本轮准备合同 `FOCUS_FIRST_FORWARD_PUBLICATION_V1` |
| evidence | 对 2026-09-22 的接受来源、393 条 tracking key、301 个共享股票事实、80 个冻结板块篮子及强度事实生成 canonical JSON；完整主交易日历取同一 SHA-256 已验证 normalized Parquet；Python 3.13.14、pyarrow 24.0.0、psycopg 3.3.6 与版本化依赖锁一致。新增 `scripts/run_focus_core_publication.py`：强制指定日期，默认 exact-date REAL_FORWARD 预演并原子暂存内容寻址 manifest；`--apply` 才进入完整初始日写入、projection 重建核验和 head 激活事务。apply 重建输入并比对预演 manifest digest；锁内重复检查 accepted source digest、cutover、calendar/lock、replay 和空 head；hash 异常 technical facts 继续由 reader fail-closed 为 UNKNOWN/UNAVAILABLE。CLI `--help` 通过；9/23 预演按预期 fail-fast 为 `NO_ACCEPTED_PUBLICATION_FOR_EXPECTED_TRADE_DATE`，未创建 9/23 staging 目录；全量 9/22 历史回滚 rehearsal 仍写入 12 类表后全部 rollback 为 0；FOCUS 测试 56 passed。未生成 9/23 manifest 或写入 Focus 业务数据 |
| staged_artifact | `runtime/focus_staging/20260922/input-manifest-37b030ee69b2b7aa15d26c93f1fd1fcddfefd958fab6f7d96a4810a4d49cf6c2.json`；内容寻址、原子写入、同路径不同内容拒绝覆盖 |
| release_gate | 2026-09-22 输入为 `HISTORICAL_RECONSTRUCTED_INPUT`。版本化提交门要求交易日不早于 `config/focus_core_release_gate_v1.json` 的 2026-09-23 cutover，且 expected date、source date、完整日历、依赖锁全部相符；该日仅用于回滚演练。publication 的 `source_identity_sha256` 为空，明示 `PUBLICATION_ID_ONLY`，不伪造 SHA |
| regression | 上一实现版本的 FOCUS-00/02/03 51 项测试通过；当前改动 py_compile 通过；393 条真实来源闭包与全量初始日 PG 同事务 rollback 通过，含 head 激活和从 immutable observations 重建 projection；另以 6 个临时 run 在单个 PG 事务内验证同日 r1→r2、两条后继 head 失效、跳日重放拒绝及顺序重放清空；演练全 rollback、持久行数变化为 0 |
| acceptance_result | **`IN_PROGRESS`**。输入冻结、全量初始日事务、head 激活、projection 重建、同日 revision 与顺序重放机制均已在回滚演练中验证；正式提交入口受版本化 REAL_FORWARD cutover 门保护；accepted technical result 哈希无法复现，已 fail closed 并另立审计；真实前瞻发布尚未验收 |
| next_stage | `FOCUS_FIRST_FORWARD_PUBLICATION_V1` 入口已准备。用户生成并接受今日来源后，先运行 `$env:PYTHONPATH='src;scripts'; python -m scripts.run_focus_core_publication --trade-date YYYY-MM-DD` 预演；只有报告 `PREFLIGHT_READY`、日期/来源/manifest 摘要核实一致，才使用同日期追加 `--apply` 提交首个 REAL_FORWARD run/head。当前 expected date 的 publication 还不存在，尚不能执行成功预演或正式提交；真实 9/23 接受仍待数据生成。现有 2026-09-22 回滚探针只作回归，不会激活。technical result 哈希审计维持单独 `FAIL_CLOSED`，本合同不修复或绕过技术因子身份；后续多日常规重放/修订编排与首日验收继续独立开放 |

## 实现边界

Manifest 列出 publication、V3/V3.3 接受绑定、relation/member-state 身份、四族完整性及行摘要、calendar 与 adjusted Parquet SHA、股票事实、板块篮子及强度摘要、状态与参数合同、实现源码摘要和依赖锁。构造前逐项校验日期、集合、摘要格式和合同身份。当前 staging 不修改 `workbench.focus_*` 业务数据；页面与查询仍不暴露 Focus 结果。

## 谓词能力和失效口径进展

适用谓词按来源族和精确 source contract 静态登记；未知合同直接拒绝。V3 shortlist 没有结构化失效条件，V3.3 candidate 的 `STRUCTURE_DAMAGED` 适用；来源未正式提供 EXTENDED 的族均把 `TOO_EXTENDED` 记为 `NOT_APPLICABLE`。真实接受日的 V3.3 scanner 证据存在 `NOT_STRUCTURE_BREAK` 检查，但不能仅凭有字段就在运行时提升合同能力。

`RECOVERY_TURN` 的失效 AST 现在把信号日收复的 MA5/MA20 类型锁定到对应动态操作数；类型缺失时对应叶节点保持 U，不借另一条均线补值。冻结价格阈值仍须通过同一调整价格口径重锚；未完成之前不把失效 UNKNOWN 判成 VALID。

## 六维 observation 只读演练

`FOCUS_OBSERVATION_ASSEMBLY_V1` 汇合来源 membership、生命周期 phase、validity、follow-up、路径主状态和 lifetime tags，并保存每个适用谓词的三值证据及输入摘要。价格 BAR、close、drawdown 和 MFE 只能来自已验证的共享股票路径，外部谓词事实不能覆盖。仍缺动态因子或冻结失效操作数时保持 `UNKNOWN`/`DATA_UNAVAILABLE`。

在 2026-09-22 的已接受来源上只读演练：393 条 observation（V3 股票 40、V3.3 候选 273、V3 板块 80）；393 条 validity 均为 `UNKNOWN`，路径均为 `DATA_UNAVAILABLE`，follow-up 均为 `ACTIVE_FOCUS`。这是故意暴露尚缺的 MA/RPS、板块历史可比及阈值重锚证据，不是把该日判断为 393 条坏数据。演练写入次数为 0，不生成正式 Focus run/head。该日继续标记 `HISTORICAL_RECONSTRUCTED`。

## 来源事实桥接与核心事务机制

`FOCUS_V33_SCANNER_FACT_BRIDGE_V1` 仅接受 `TODAY_RESEARCH_SCANNER_V3_3_CANDIDATE_01`、同证券同日期的 `NOT_STRUCTURE_BREAK` 布尔检查；多分支冲突时报错，缺值为 U。桥接后的 2026-09-22 全量只读演练仍为 393 条 validity UNKNOWN；缺失的冻结价格阈值没有被当作 F。

`scripts/probe_focus_core_transaction.py` 取一条真实已接受 V3.3 来源及其 SHA 校验的本地价格事实，在单个 PG 事务内插入 run、item、episode、segment、transition、anchor、observation、evaluation facts、projection、head，事务内验证 head 可见，然后无条件 rollback。演练通过，回滚前后 run/head/observation 计数均为 `(0,0,0)`。这只验收外键和基本事务可见性，不代表 393 条全量发布、失败注入、revision 切换或生产发布门已通过。

## 全量输入闭包

`FOCUS_CORE_INPUT_CLOSURE_V1` 在事务前严格核对 manifest 自身摘要、来源/计划身份、各族来源行数与摘要、来源行原始摘要、tracking union 与 observation 键集、生命周期 episode/membership/phase、逐条 observation 证据摘要、共享股票事实集合和 manifest 内的价格事实摘要。板块 observation 还须逐条匹配 manifest 的冻结篮子与成员强度事实摘要。漏一条 observation、重复键、源行被改或行情/板块摘要被换均拒绝。2026-09-22 的 393 条真实 observation 闭包通过，当前 technical 因子被标记 `UNAVAILABLE` 并带 hash 差异 reason；计入 V2 head activation 实现摘要后的闭包 digest 为 `3b4cb93d608c2e5b47c4b2975403ce9be5987a6a3a6c283eed7fecc839f47534`。这是历史重构演练摘要，不解除发布门。

## 全量初始日事务回滚演练

`scripts/probe_focus_full_core_transaction.py` 在写入前重新核对 accepted publication head 与来源摘要，只接受空 Focus head、全 `NEW` 的初始日以及唯一的 `HISTORICAL_RECONSTRUCTED_INPUT` 门禁。事务内写入 1 run、393 daily items、393 episodes/segments/transitions/anchors/observations/evaluations、3770 predicate facts、80 entry baskets 和 1 trade-date head；再删除写入时 projection 并从 immutable observations 全量重建、逐行摘要核验。数量断言按实际输入集合动态生成，没有固定人数上限。最新回归使用 V2 activation 执行成功；随后无条件 rollback，相关 12 张表回到 0 行。此演练验证初始日事务和可重建 projection；正式提交仍被 REAL_FORWARD 日期门禁拦截。

## 失败原子性、run 身份和 head/projection

对同一 393 条输入在写入第 100 条 observation 后主动抛出 `FOCUS_CORE_INJECTED_AFTER_OBSERVATIONS`；此前版本事务回滚后 12 张相关表均为 0 行。全量演练现使用 `FOCUS_CORE_HEAD_ACTIVATION_V2` 激活 READY run，并将未来 head 标为 `REPLAY_REQUIRED`；V2 在持锁事务内核对最早待重放日期，拒绝跳过更早的 stale head，避免缺失交易日时被较新的有效 head 掩盖。`FOCUS_CURRENT_PROJECTION_REBUILD_V1` 只允许从最新 VALID head 重建投影。`FOCUS_CORE_RUN_IDEMPOTENCY_V1` 在持有同日事务锁时核对 `(trade_date,authority,revision)` 槽、run ID、source/observation 摘要、state/parameter/dependency 身份和有效 head；完全一致识别为 `ALREADY_ACTIVATED`，同槽更换 observation 摘要明确拒绝。

新增 `scripts/probe_focus_revision_replay_activation.py`，运行命令：`$env:PYTHONPATH='src'; python -m scripts.probe_focus_revision_replay_activation`。单一 PostgreSQL 事务先建三日有效 head，再修订首日；后两日正确变为 `REPLAY_REQUIRED`，先重放第三日被拒绝，随后第二、三日各递增 revision 后待重放链清空。输出为 `temporary_runs=6`、`persisted_changes=0`，结束时无条件 rollback。该演练验收 head/replay 控制面，不模拟 source facts、observations 或跨阶段数据重算；未构成真实前瞻发布接受。

## 独立审计阻塞：technical result hash

已在 [TECHNICAL_RESULT_HASH_RECONCILIATION_20260923.md](audits/TECHNICAL_RESULT_HASH_RECONCILIATION_20260923.md) 单独登记并找到根因。只读维护备份中同一 result object 的 6186 行由原始 `_technical_hash` 精确重现登记哈希，备份 SHA-256 为 `793dae0682a79aaf7b21366baad39ab899a5b043e9cde06e14fdeb1e92650cac`；与 PG 逐行比较时所有非 JSON 字段一致，`quality_codes`、`basis_json` 均为 JSON 语义相同、存储类型由序列化文本转成 JSONB，造成字符串哈希不同。技术因子 reader 已做全对象哈希核验并 fail closed，故 Focus 继续将 technical 标记 `UNAVAILABLE`。没有修改备份或 PG 数据；是否做版本化身份修复需独立审查。当前发布入口只允许从 2026-09-23 起的 exact REAL_FORWARD 来源日期，当前最新 accepted publication 是 2026-09-22，因此尚无可正式提交的首日。

## 首个 REAL_FORWARD 发布后更新（2026-09-23）

9/23 accepted publication 现已生成并成功同步；依本文件预备的 exact-date 门禁执行后，首个 REAL_FORWARD Focus run `focus-run-f8ba1c4915d1c330506d9bc8954b0a2d` 已 `ACTIVATED`，trade-date head `VALID`。完整阶段 evidence 和 API/UI 验收见 [FOCUS_03_FIRST_FORWARD_PUBLICATION_20260923.md](FOCUS_03_FIRST_FORWARD_PUBLICATION_20260923.md)。前述“尚无首日”是生成前的历史记录，不代表当前状态。

技术 result hash 差异仍独立 `FAIL_CLOSED`：310 observations 均保留 `validity=UNKNOWN`、`current_path_state=DATA_UNAVAILABLE`。9/22 仍只作历史回滚演练，不激活为正式 run。后续逐日发布须遵守 ordered replay/head contracts。
