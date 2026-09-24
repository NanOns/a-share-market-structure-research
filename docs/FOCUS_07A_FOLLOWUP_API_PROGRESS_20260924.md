# FOCUS-07A Follow-up API 查询修复记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 35.1 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md`。 |
| stage_contract | `/api/v3/focus-tracker/items` 包含当前 run 中来源归属为 `NONE` 且 follow-up 尚未完成的旧 episode；`POST_EXIT` 与 `PENDING_SETTLEMENT` 可见，`FOLLOW_UP_COMPLETED` 不进入 follow-up 列表。同实体的新 episode 与旧 follow-up 按 episode 分别展示。 |
| evidence | `read_api.py` followups CTE 改用来源归属与完成状态过滤。`probe_focus_read_api.py` 的临时 schema 回滚探针分别验证 `POST_EXIT`、`PENDING_SETTLEMENT`、`FOLLOW_UP_COMPLETED`，以及同实体当前与退出 episode 共存；输出 `persisted_changes: 0`。Focus 定向测试 `85 passed, 355 deselected`。 |
| acceptance_result | `FULL_PASS / READ_API_ROLLBACK_PROBE`。仅覆盖查询语义；真实连续 accepted 来源日尚未就绪，因此不代表 07A 多日发布验收完成。 |
| next_stage | 继续核对第 35.2 节前后端枚举；真实连续日来源可用后执行多日 writer 的 Forward 验收。重入重叠问题继续由 `docs/audits/FOCUS_REENTRY_OVERLAP_AUDIT_20260924.md` 独立跟踪。 |

探针没有写入正式 Focus 表、来源快照或 TDX 目录。
