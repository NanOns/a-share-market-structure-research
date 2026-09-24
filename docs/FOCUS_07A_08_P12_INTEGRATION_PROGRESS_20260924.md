# FOCUS-07A-08 P12 日任务接入记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 12、38 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 7、9、10、14 节；`docs/P12_DAILY_POSTGRES_SYNC_REPAIR_20260923.md` |
| stage_contract | Focus 仅在 P12/V3.3 成功、PostgreSQL 同步 `FULL_PASS` 且 publication_id/trade_date 精确相符后运行。先执行 exact-date preflight；只有版本化 `FOCUS_DAILY_PIPELINE_GATE_V1` 明确放行后才自动执行 `--apply`。Focus core 与 outcome 状态单独记录于日任务，Focus 失败不回滚或重标已完成的 V3/V3.3 publication/PG sync。 |
| implementation_decision | `run_p12_daily_pipeline.py` 执行时 PG 同步尚未发生；实际生产编排点在 `src/workbench_service/app.py` 的 `sync_latest_publication_to_postgres.py` 成功之后。因此将 Focus 阶段接在该处，而非 P12 脚本内部，以保持 accepted PG source 权威。 |
| evidence | 新增 `src/workbench_service/focus_daily_stage.py` 与默认关闭的 `config/focus_daily_pipeline_gate_v1.json`；工作台日任务在 PG 同步成功后运行 Focus 并把 `focus_stage` 放入任务结果/API。测试覆盖同步身份不符不运行、放行时 preflight→apply 顺序、关闭门时仅预检、preflight 阻断不 apply、outcome 降级保留 core 激活；编译与差异检查通过。 |
| acceptance_result | `IN_PROGRESS / POST_SYNC_ORCHESTRATION_CODE_READY_GATE_CLOSED`。当前本地 2026-09-24 无 accepted publication head，且多日 writer 尚无真实回滚验收；自动 apply 门保持关闭。生产运行期证据待下一连续正式交易日。 |
| next_stage | 在下一次真实日任务完成 PG 同步后核对预检的 `focus_stage`；先执行多日 writer 回滚演练与真实 Forward 验收，再版本化放行自动 apply 门，核对 Focus run/head、episode/observation 数和 outcome 状态。 |

本阶段没有运行日任务或写入已接受 Focus 历史，也没有修改 TDX 输入。跨领域重入重叠与技术 hash 身份审计继续独立开放。
