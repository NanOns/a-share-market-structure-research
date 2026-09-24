# FOCUS-07A-03 多日 Head 阶段记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 7、38 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 4、7、10 节；`docs/FOCUS_03_FIRST_FORWARD_PUBLICATION_20260923.md` |
| stage_contract | 每个 exact-date 日任务读取同一 authority 的前一 accepted head、同日 revision 和最早 replay backlog；区别首日、次日与同日修订。旧 head 不被改写。未有可处理多日 episode 的 writer 前，次日和修订均不得写库。 |
| evidence | `src/focus_tracker/core_activation.py` 已支持前一 head 绑定、revision 增量和下游 replay 标记，故无需改动该历史合同。新增 `src/focus_tracker/daily_head_plan.py`，Daily Runner 改用明确计划。7 项定向测试通过；2026-09-24 只读预检识别为 `NEXT_DAY` 并返回 `FOCUS_DAILY_NEXT_DAY_WRITER_PENDING`，未调用首日 writer。现有首日 writer 会对每个 observation 插入新 episode，且要求全部 phase 为 NEW；它不适用于次日。 |
| acceptance_result | `IN_PROGRESS / HEAD_PLAN_READY_WRITER_NOT_READY`。前态与 revision 的只读计划完成；多日正式写入尚未完成，不得放行。 |
| next_stage | 先完成 07A-04/05 的 tracking union observation 与历史 context，使正式 batch 覆盖延续和退出 episode；再实现复用既有 episode、按变化写 transition/anchor 的多日 writer，并回到本项验收。 |

跨领域 technical hash identity 仍按独立审计项处理。本阶段不修改旧 Focus run/head 或 TDX 输入。

## 多日 writer 代码推进（2026-09-24）

| 字段 | 记录 |
|---|---|
| stage_contract | `scripts/run_focus_continuation_core_transaction.py` 仅处理前一 accepted head 后的全新交易日。writer 在事务锁内重读 head、前态和今日来源身份，复用延续 episode，仅对 NEW/REENTERED/MODEL_BASELINE 插入新 episode；追加 transition、anchor、observation 和谓词证据，重建 projection 后激活 head。失败事务回滚；outcome 仍由独立事务处理。同日 source revision 暂不进入此 writer。 |
| evidence | Daily Runner 已将 NEXT_DAY 指向该 writer；5 项 runner 定向测试通过，Focus 测试总计 `77 passed, 355 deselected`，编译及差异检查通过。2026-09-24 的只读 preflight 在 accepted publication head 缺失处返回 BLOCKED，未进入 writer，未写 Focus 业务数据。 |
| acceptance_result | `IN_PROGRESS / MULTI_DAY_WRITER_CODE_READY_REAL_ROLLBACK_PENDING`。当前环境缺少第二日 accepted publication，故尚无多日 writer 的真实回滚或 apply 证据；不能宣布 07A-03 通过。 |
| next_stage | 取得下一连续主交易日的 accepted publication 后先执行 NEXT_DAY 预检与 writer 回滚演练，核对 episode 延续/退出、完整 observation、projection 和无持久副作用；通过后再正式 apply 并验收 head/outcome。另行实现同日 revision/replay 写入。 |
