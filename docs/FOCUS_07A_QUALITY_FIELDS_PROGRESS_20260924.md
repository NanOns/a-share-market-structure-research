# FOCUS-07A 质量字段对齐记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 35.5 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md`。 |
| stage_contract | 来源质量与观察质量分别展示、分别筛选；`source_quality` 取来源行，`observation_quality` 取当日 observation。退出后观察条目的来源质量只可从首次来源行取得，不用当日 observation 质量冒充。旧 `quality` 查询参数仍按来源质量解释。 |
| evidence | `/items` 增加 `observation_quality` 明确字段与对应过滤；`/facets` 分别返回 `source_qualities`、`observation_qualities`；界面提供两项独立筛选及两行质量展示。回滚探针使用来源 `COMPLETE`、观察 `READY` 的条目验证两个筛选结果不同，且无持久化写入；Node 脚本语法检查通过；Focus 定向测试 `85 passed, 355 deselected`。 |
| acceptance_result | `FULL_PASS / QUALITY_FILTER_DISPLAY_PARITY`。 |
| next_stage | 继续阶段 A 中不依赖 24 日数据的静态和回滚验收；数据就绪后执行 23→24 日真实连续日 Forward 验收。 |

没有写入正式 Focus 数据或 TDX 目录。
