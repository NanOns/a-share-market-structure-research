# Focus 同日修订与顺序回放独立审计项

| 字段 | 记录 |
|---|---|
| audit_item | `FOCUS_SAME_DAY_REVISION_ORDERED_REPLAY_GAP` |
| scope | `07A` same-day source revision writer、接受 head 切换、anchor/outcome 可见性及 downstream ordered replay。 |
| evidence | `daily_head_plan.py` 能识别 `REVISION_REQUIRED`；`run_focus_daily.py` 仍以 `FOCUS_DAILY_REVISION_REQUIRED_WRITER_PENDING` fail closed。现有 continuation writer 只接受 NEXT_DAY/revision 1。schema 的 anchor 主键全局唯一，outcome head 仅按 `(anchor_id,horizon)` 选择，没有按 Focus run revision 屏蔽被替代 revision 的 anchor/outcome。`replay.py` 只查询 backlog 并阻止普通前向发布，没有按交易日重建执行器。 |
| acceptance_result | `OPEN / WRITER_AND_REVISION_VISIBILITY_NOT_IMPLEMENTED`。禁止用只去掉 revision=1 限制的改动放行；这会使旧 revision 的 anchors/outcomes 继续参与 accepted 结果。Auto Apply 保持 OFF，07D 保持阻断。 |
| next_stage | 先版本化 accepted anchor/outcome revision head 或等价的 lineage 可见性模型；定义首日修订对冻结 episode facts 的处理；再构建同日原子 writer 与 D1→D2→D3 顺序 replay transaction，并用临时 PostgreSQL schema 验证旧 revision 不可见、旧行不可变、head/projection/outcome lineage 正确。 |

该项与真实多日 Forward gate 分开追踪；代码测试通过不能替代其事务和数据可见性验收。
