# FOCUS-07A 全量筛选项修复记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 35.4 节；`docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md`。 |
| stage_contract | `/api/v3/focus-tracker/facets` 对固定的 accepted Focus run，以 `/items` 相同的当前条目与未完成退出后观察条目范围生成完整筛选值；不受列表分页或当前筛选条件影响。页面使用该接口提供的来源、名单、失效、路径、来源质量、场景和板块筛选项。 |
| evidence | `read_api.py` 抽出共用 items CTE，增加 `FOCUS_ITEMS_FACETS_V1` 响应；`focus-tracker.html` 单独读取 facets。回滚探针在 `/items?page=1&page_size=1` 只返回一条时仍核对两个 episode 的名单与路径筛选值，结果 `persisted_changes: 0`。2026-09-23 正式 accepted run 的只读 `/facets` 返回 200/AVAILABLE：3 个来源、1 个路径、2 个场景、6 个板块。Node 脚本语法检查通过；Focus 定向测试 `85 passed, 355 deselected`。 |
| acceptance_result | `FULL_PASS / UNPAGINATED_FACETS`。列表自身的分组加载上限及来源质量与观察质量的展示一致性不属于本门，后者按第 35.5 节继续修复。 |
| next_stage | 处理第 35.5 节质量字段一致性；24 日数据生成后执行 23→24 日真实连续日验收。 |

没有写入正式 Focus 数据或 TDX 目录。
