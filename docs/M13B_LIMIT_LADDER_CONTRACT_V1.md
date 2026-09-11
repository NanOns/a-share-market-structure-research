# M13B-01 市场日梯队递推合同 v1

合同 ID：`LIMIT_LADDER_V1_0`  
适用阶段：M13B-01  
依据文档：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 13、20.3 接口表、21.3 和 21.4 节。

## 范围

本阶段只负责把已经由 M8C 本地规则/参考价能力判定的逐股票逐交易日状态，按市场交易日递推为收盘梯队状态，并提供 API34 的分页读取路径。M8C 没有可核验输入时，API 返回 `NOT_BUILT`，不能根据涨幅、名称或默认 10% 规则推断涨停。

输入只允许来自固定分析快照或显式测试行；不读取网络、不读取未来数据、不写 observations/outcomes、不自动交易。每个 `security_id + trade_date` 只能有一条输入。

## 状态与递推

对外标准状态为：`UP`、`DOWN`、`NONE`、`UNKNOWN`、`NO_LIMIT`、`SUSPENDED`。M8C 的 `LIMIT_UP`、`LIMIT_DOWN`、`NOT_LIMIT` 兼容映射为 `UP`、`DOWN`、`NONE`。任何无法核验的状态均为 `UNKNOWN`，不得降级为 `NONE`。

- `UP` 且前一市场日为已知 `UP`：`streak = previous_streak + 1`，`streak_known = true`。
- `UP` 但左截断、前一日缺失或前一状态未知：只给 `streak_min_known = 1`，`streak_known = false`，`ladder_level = UNKNOWN`。
- `NONE`、`DOWN`、`NO_LIMIT` 是已知边界；它们不进入梯队层级，后续 `UP` 可从 1 板开始已知递推。
- `SUSPENDED` 中断连续事件，输出 `SUSPENSION_BREAK`；停牌不被计成断板或晋级失败。
- 缺少行情行输出 `UNKNOWN` 和 `MISSING_MARKET_OBSERVATION`；后续有效 `UP` 只能给最短可确认数，不回填未知日。

精确 `UP` 的 `ladder_level` 为 `1`、`2`、`3`、`4PLUS`；左截断或未知边界的 `UP` 为 `UNKNOWN`。本阶段不计算晋级分母，`promotion_state=NOT_EVALUATED`、`denominator_eligible=NULL`，留给 M13B-02。

## 物化与 API34

逻辑物化表 `limit_ladder_daily` 每行绑定 `slice_id`、`security_id`、`trade_date`、`contract_id`，并保存参考口径、规则 ID、涨跌停价、连续状态、左边界最短数、前一状态连续数、层级、停牌中断原因和晋级占位字段。写入必须遵守 slice 不可变；本阶段不改旧 snapshot。

`GET /api/limit-ladder?publication_id=...&page=1&page_size=50&level=ALL&state=ALL&promotion=ALL&basis=RECONSTRUCTED` 只返回固定 snapshot 的分页梯队行。支持 `level=ALL/1/2/3/4PLUS` 和标准状态筛选；`UNKNOWN` 独立可筛选；按层级降序、当日成交额降序、`security_id` 升序。没有绑定 `limit_ladder` 域或物化表时，返回 `status=NOT_BUILT`、空 `items` 和能力说明，而不是 500 或空数据冒充已完成。

## 验收

必须通过：

1. 已知连续 `UP` 正确递推到 1/2/3/4PLUS；未知不变成 `NONE`。
2. 缺失行情、左截断、停牌分别保留 `UNKNOWN`、最短连续数和 `SUSPENSION_BREAK` 证据。
3. 物化迁移原子、哈希受控，旧 snapshot 数据不改；API34 分页和状态筛选有边界测试。
4. 当前没有 M8C 规则/参考价数据时 API 明确 `NOT_BUILT`，不得产生伪造梯队数量。

物理迁移使用 `020_m13_limit_ladder.sql`：现有仓库的 `013` 已由 M9 代表股迁移占用，该编号差异单独记录，不改变本合同的逻辑依赖“仅基于已冻结 M8C/历史输入”。
