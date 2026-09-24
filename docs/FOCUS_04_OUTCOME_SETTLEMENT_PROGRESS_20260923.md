# FOCUS-04 Outcome 结算阶段记录

> 开始日期：2026-09-23；当前结果：`IN_PROGRESS / CONTRACT_FROZEN`。

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 9、10、15.3、17.2、17.3、19 节；FOCUS-03 当前阶段记录 |
| prior_stage | FOCUS-03 `IN_PROGRESS`；其当前控制面可在 rollback rehearsal 验收，但无已提交 REAL_FORWARD Focus head。依用户指示并行进入 FOCUS-04，不将 FOCUS-03 标为 PASS |
| stage_contract | `FOCUS_ANCHOR_OUTCOME_V2`、`FOCUS_OUTCOME_TARGET_PLAN_V1`、`FOCUS_OUTCOME_SETTLEMENT_TXN_V1`、`FOCUS_OUTCOME_RETRY_V1`、`FOCUS_FOLLOWUP_TERMINATION_V1`、`FOCUS_OUTCOME_TASK_ORCHESTRATION_V1`、`FOCUS_OUTCOME_OVERDUE_MONITOR_V1` |
| stage_boundary | 本阶段只结算已有正式锚点的固定 T+1/3/5/10/20 目标；不创建核心 Focus head，不改变 source membership，不因经过天数删除 episode/outcome。结算任务仅从有效且已激活的 accepted Focus head 启动。事务从 PostgreSQL 固定 publication head、artifact catalog、目标状态审计表读取已接受封存证据；调用方不能直接传入 sealed 布尔值或终态审计。缺少证据时不得制造终态。日任务默认为只读预览，必须显式 `--apply` 才写 outcome/retry 生命周期数据；逾期监控为只读快照，晚于固定 target session 的未终结结果计为 overdue，不改变 target date |
| evidence | outcome schema 已应用并只读核验；目标数据审计 schema 已回滚演练、应用并只读核验；代码编译通过；股票/板块算法边界和 outcome revision/head 用回滚事务探针验证；观察日计划集成只读探针通过。细项见下文；不访问或写入 TDX 根目录 |
| acceptance_result | **`IN_PROGRESS`** |
| next_stage | 控制面、受控编排、重试退避/领取、目标 source/artifact 修订重算、逾期只读监控及 25 个必需 anchor/horizon 的自动完成→自动重开→重新完成路径均已完成回滚验收；下阶段在存在已提交 `REAL_FORWARD` Focus head 与真实到期正式锚点后执行真实 `--apply` 验收。完成这些运行期证据前，本阶段保持 `IN_PROGRESS` |

## 已冻结的数据边界

- T+N 只能用完整、严格递增且含 anchor date 的主交易会话日历计算；目标日期不存在时保持 `PENDING`，不延用下一次运行日期或自然日。
- 仅当目标输入被接受且 sealed、anchor/target 实际 BAR 完整、同一版本本地复权路径可完整重建时，状态才是 `OBSERVED`。
- `SUSPENDED`、`DELISTED` 需要证券/目标日的审计身份和摘要；不能仅凭缺 BAR、零成交量、`INFERRED_GAP` 或 `DELISTED_OR_INACTIVE` 文本终结。
- `DATA_GAP` 需要目标输入 sealed、缺口及不可恢复性审计；未审 gap 保持 `PENDING` 并进入 retry/逾期监控。
- `SOURCE_REVISED` 非终态，触发目标重算并追加 `target_revision`。`focus_outcome_heads` 仅由同一事务中的已接受 outcome 更新。
- outcome 结算单独事务化。失败先回滚 outcome/head/batch，再在独立事务记 retry task 并置相应 core run 为 `DEGRADED`；不修改 core head。
- retry 以 `(focus_run_id, as_of_trade_date)` 唯一排队；失败第一次 15 分钟后重试，此后等待时间翻倍，最长 24 小时；成功后结束任务并清除 backoff。任务领取按 UTC wall clock 判断到期，默认 worker 先取已到期且仍对应有效 accepted head 的 retry task，再处理最新有效 head。固定 target date 不随重试移动。
- 仅 `FIRST_FOCUS`、每次 `CURRENT_UPGRADE`、`EXIT_EFFECTIVE`、`INVALIDATION`、`FIRST_SUPPORTED` 是必需结算锚点；`MILESTONE` 只作诊断，不阻止 episode 完成。
- 板块只使用其 immutable entry basket 计算成员中位数收益和 NAV；板块路径不冒充官方指数。没有单独的日内聚合合同前，sector outcome 的 intraday MFE/MAE 留 NULL，close NAV return 与 close-based MDD 按已定义可比会话计算。

## 实施与验收证据（2026-09-23）

- `FOCUS_OUTCOME_SETTLEMENT_SCHEMA_V1` 已应用；migration checksum `947ca6124d1ba8878534820a49de95d12d6b36bfdece4d4a20f0824ad9dfe992`；只读 verifier 确认 3 张表、24 项主键/唯一/外键/检查约束，当前无生产结算批次、重试任务或生命周期事件。
- `FOCUS_TARGET_DATA_AUDIT_SCHEMA_V1` 已先 rollback rehearsal（9 项约束）后应用；checksum `14140adc4b5a9fcf98de75fa422b1fc257765c9ec62bb1df30ef0a6ea67a8535`；只读 verifier 确认 `workbench.focus_target_data_audits` 存在且有 9 项约束，目前无审计行。
- `settle_due_outcomes` 的公共入口不接受外部 `target_seals` / `target_audits`。锁内重新计算固定到期计划，并在同一事务内读取接受的 publication head、当前 normalized artifact 和按来源/artifact 双身份绑定的审计行；失败回滚后另起事务写 settlement retry task。
- `due_anchor_plan` 对已终结 outcome 也核对目标日 accepted publication source identity 和当前 normalized artifact SHA。任一身份变化时自动重纳计划、追加结果 revision，并在新 evidence 记录旧/新摘要；相同身份的终态仍从日计划排除。
- 新增 `scripts/run_focus_outcome_settlement.py` (`FOCUS_OUTCOME_TASK_ORCHESTRATION_V1`)：默认只读预览；可指定 `--trade-date`，否则优先选择已到期 retry task 对应的 `VALID + ACTIVATED` Focus head，再回退到最新有效 head；从 SHA 校验的本地 normalized artifact 构建完整主交易日历，只读所需证券和接受的 immutable entry baskets。只有显式 `--apply` 才调用 `settle_due_outcomes`，不会创建/更改 core head。结算事务锁住 retry task，并在 `next_retry_at_utc` 前返回 `RETRY_BACKOFF`。
- 新增 `src/focus_tracker/outcome_monitor.py` 与 `scripts/report_focus_outcome_overdue.py` (`FOCUS_OUTCOME_OVERDUE_MONITOR_V1`)：只读取有效 accepted run 和冻结主日历；报告未终结 outcome 数、超出固定目标交易日的会话数、`PENDING/SOURCE_REVISED` 分布、可领取 retry 与退避中的 retry 数，并限制详情返回数。完成 episode 不再显示在 open outcome details；修订重开后重新出现。
- `python -m compileall -q src/focus_tracker scripts/...` 通过（FOCUS-04 相关模块及脚本）。
- `PYTHONPATH=src python -m scripts.probe_focus_outcome_settlement`（PowerShell 等价设置 `$env:PYTHONPATH='src'`）通过 rollback-only 演练：目标日期 2026-09-22 / T+1、股票 `BJ.899050` 路径 READY；板块仅 close NAV 且 MFE/MAE 为 NULL；未审 gap 为 PENDING、有审计 gap 为 DATA_GAP；重复批次幂等；结果历史追加 r1-r4 且 head 为 r4；目标 source identity 修订会重新纳入计划并生成带 revision reason 的 materialized outcome；重试首次/二次退避为 15/30 分钟，未到期任务不进入领取队列，过期任务可以领取。另以 2026-08-24 至 2026-09-22 的 21 个 master sessions 构造 5 必需 anchor × 5 horizon：全部终结时 writer 自动写 `FOLLOW_UP_COMPLETED`，union 移除；强制历史修订产生 PENDING 时 writer 自动写 `SETTLEMENT_REOPENED` 并重纳 union；修订结终后再次自动完成。逾期报告在 episode 完成时移除该 episode，修订为 PENDING 后报告 1 个 overdue，重新完成后再次移除。所有探针最终 `persisted_changes=0`。这验证事务生命周期，不替代真实 forward 数据验收。
- `PYTHONPATH=src python -m scripts.probe_focus_observations` 只读通过：2026-09-22 纳入 393 个观察项（40 shortlist、80 sector track、273 today candidate），所有 393 项均为 `ACTIVE_FOCUS`，`writes=0`。当前库无真实 Focus 核心 head，因此这些行均为历史重建输入，`UNKNOWN / DATA_UNAVAILABLE`，不构成 forward 结果证据。
- 受控日任务编译和 `--help` 校验通过。默认只读执行返回 `NO_VALID_ACCEPTED_FOCUS_HEAD`、`writes=0`；环境里没有有效 head，因此真实 settlement apply 路径本轮未执行。
- 逾期报告工具编译和 `--help` 校验通过；当前环境执行返回 `NO_VALID_ACCEPTED_FOCUS_HEAD`、`writes=0`。不会因无 head 伪报零逾期。
- 本轮复核：FOCUS-04 相关模块与脚本 `compileall` 通过；报告工具在 `PYTHONPATH=src` 下 `--help` 通过；两个 schema verifier 再次确认 checksum/约束未变且生产结算表、目标审计表均为 0 行；生命周期回滚探针再次通过并报告 `persisted_changes=0`。`git diff --check` 无空白错误（仅提示仓库既有 CRLF/LF 转换）。
- 本轮门禁重查：结算编排器预览和逾期报告均返回 `NO_VALID_ACCEPTED_FOCUS_HEAD`、`writes=0`；来源 head 只读探针显示最新 accepted publication 仍是 2026-09-22（publication `m4-547e88ce22e6d89590876c7ea1d68ca0`），低于 `FOCUS_CORE_PUBLICATION_GATE_V1` 的 2026-09-23 最早 REAL_FORWARD 日期；因此当前无可供 FOCUS-04 真实结算的合格核心 head。该结果是前置发布门未满足，不是零逾期结论。
- 阶段判定：`IN_PROGRESS`。迁移、算法边界、事务原子性、幂等及回滚证据通过；数据库尚无真实终态审计行、settlement batch 和 REAL_FORWARD Focus 锚点，不能据此宣布真实运行期验收完成。FOCUS-03 仍为 `IN_PROGRESS`，依用户要求直接推进 FOCUS-04，不改变前阶段状态。

## 首个 REAL_FORWARD head 后更新（2026-09-23）

FOCUS-03 随后已激活 2026-09-23 REAL_FORWARD Focus head `focus-run-f8ba1c4915d1c330506d9bc8954b0a2d`。这满足 outcome settlement 的核心 run 前置，但所有 anchor 是 9/23 首日新锚点，固定 T+1/T+3/T+5/T+10/T+20 尚未到期；没有真实 settled outcomes、target seals 或 target audit rows。FOCUS-04 保持 `IN_PROGRESS`，只在交易日历到期且目标输入审计齐全后验收，不提前合成收益或终态。
