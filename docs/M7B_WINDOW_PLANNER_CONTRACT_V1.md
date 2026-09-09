# M7B-02 Window Planner Contract v1

版本：`history-window-dependency-v1.0`；交付物为 `WindowPlan` 与 API03 `GET /api/history/coverage`。

## 规则

规划器使用 `MASTER_TRADING_CALENDAR` 的有序交易日序列。请求 `D` 个输出日时，`output_start` 是截止日前第 D 个可用交易日，`output_end` 是截止日序列中的最后一天。每个域根据自己的最大依赖窗口向左回溯，`read_start` 不以固定“120日预热”代替依赖计算；当前最长依赖来自 100 日新高窗口。

`missing_dates` 只报告预期交易日序列中未出现在已观测输入的日期，不把周末自动当作缺失交易日。`calendar_gap_diagnostics` 仅是工作日缺口提示，不能据此推断开市。若本地最早日期不足以提供完整预热，返回 `left_truncated=true`、`warmup_shortfall` 和实际可用预热数；不把左截断误称为完整历史。缺日不前填、不伪造结果；域能力降为 `PARTIAL` 或 `UNAVAILABLE`。历史分析本身在 M7B-04 之前保持 `NOT_BUILT`。

## 依赖注册表

`config/history_windows.yaml` 固定报价、技术、强弱、新高、结构、板块周期与市场域的窗口及预热理由；因子域采用 5/10/20/60，创新高采用 20/30/60/100。配置提升 `contract_version` 后才允许改变窗口含义。

## API03

`GET /api/history/coverage?publication_id=P&days=250&basis=AUTO` 返回 `item`，包含发布截止日、输出/读取边界、最长所需历史、缺日、输入/输出覆盖率、域级 `available_from/to`、`required_history`、`supported_basis`、`field_coverage` 和能力状态。`AUTO` 当前解析为 `OBSERVED`，但不创建快照；请求的 `RECONSTRUCTED` 只表示规划口径，实际历史分析仍须后续任务生成。返回 `snapshot_id=null` 与 `snapshot_capability=NOT_BUILT`，不把规划结果冒充已完成分析快照。
