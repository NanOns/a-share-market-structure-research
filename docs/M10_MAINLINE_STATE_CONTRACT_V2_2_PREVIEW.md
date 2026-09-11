# M10 主线状态合同 v2.2-preview

> 本文件是 v2.2 的历史合同。当前实现已升级到 [v2.3-preview](M10_MAINLINE_STATE_CONTRACT_V2_3_PREVIEW.md)，本文件不再作为当前默认合同。

合同 ID：`MAINLINE_STATE_V2_2_PREVIEW`

## 1. “有效样本”是什么意思

主线分类不是按表格行数直接判断。对单个板块来说，每一个交易日最多贡献一个板块观察值；只有该日的 `sector_rs20_pct` 是可计算、可验证的数值，才计入 `valid_observation_days`。

因此：

- `observation_days` 是进入分类计算的交易日数量；
- `valid_observation_days` 是具有有效板块 RPS20 分位的交易日数量；
- 缺少 RPS20 分位、覆盖率或成员可比数据时，不把缺失当成 0，也不把板块判成退潮；
- 当前合同分三层：至少 3 个有效 RPS20 观察日进入短期观察池，至少 5 个观察日才允许快速状态，至少 10 个观察日才允许稳定状态；20 个观察日只用于长期证据，不再作为所有状态的总闸门。当前板块覆盖率仍需至少为 80%。

`DATA_INSUFFICIENT` 的意义是“连短期观察所需的 3 个有效观察日都不足”，不是“主线弱”，也不是“退潮”。3 至 4 个观察日会显示为 `OBSERVING`，表示短期观察池，不是正式主线结论。

## 2. 分类依据与优先级

每个板块、每个交易日只生成一个 `mainline_class`。分类条件全部以 `predicates` 保存，状态为通过、失败或未知；页面证据弹窗直接展示这些条件，不使用隐藏综合分数。

分类优先级为：

1. `FADING`：可用的近 20 日历史中曾经入选，当前分位低于 60%，且相对比较日明显回落，同时宽度和成交额都走弱；
2. `HIGH_LEVEL_CONTRACTION`：当前仍处于 80% 以上高位，但宽度或成员留存明显收缩；
3. `REACCELERATING`：10 日入选天数、当前分位、分位变化、宽度变化和成交额条件同时满足；
4. `SUSTAINED`：短期持续位于高位，宽度和成员留存达到阈值；
5. `NEW`：当前达到高位，当前 5 日窗口中此前观察很少入选，宽度/成交额改善，且进入成员多于退出成员；
6. `BROADENING`：当前达到扩散阈值，进入成员多于退出成员，宽度改善；
7. `OBSERVING`：数据足够但没有任何分类条件成立。

如果高优先级条件为未知，低优先级条件即使成立，也返回 `DATA_INSUFFICIENT`，并在 `conflict_resolution` 标记 `UNKNOWN_HIGHER_PRIORITY`。

状态变化还必须区分市场变化和口径变化：同一 `history_basis`、`contract_id` 和 `config_hash` 下，分类变化才可记录为对应的主线状态；`contract_id` 或 `config_hash` 变化记录为 `MODEL_CHANGE`，`history_basis` 变化记录为 `BASIS_CHANGE`。模型变化优先于历史口径变化，二者都不能解释成退潮或其他市场状态。

## 3. 页面与证据

- “主线周期”页面只读取当前发布绑定的 M10 分析快照；
- 表格支持按主线分类、板块类型和证据回看天数筛选；
- 点击“证据”查看当前分类、历史分类变化、关键指标和每个谓词的状态；
- 页面显示各主线分类的当前数量卡片；点击数量卡片与分类下拉框使用同一筛选条件，数量卡片不受当前分类筛选反向影响；
- 证据条件按历史与数据门槛、持续与强度、上涨宽度、成交额、成员变化与留存、最终组合判断分组，避免把原始谓词平铺成不可读的字段清单；
- `history_basis=RECONSTRUCTED` 表示数据来自本地历史重建，不代表官方原生主线标签；
- 当前预览快照若只有 3 个交易日，页面应展示有限数量的“短期观察池”，并明确显示 `3/5` 历史进度，不能把每个板块默认显示为正式主线或伪造完整周期。

## 4. 存储与接口

- 结果存储于 `mainline_daily`，与 `sector_cycle_daily` 按 `slice_id + sector_id + trade_date` 绑定；
- `GET /api/mainlines` 返回当前截止日列表；支持 `group=INDUSTRY_ROOT`、`INDUSTRY_LEAF`、`THEME`、`STYLE`，不同分组独立排名；
- `GET /api/mainlines` 返回 `class_counts`，它在指定 `group` 和 `sector_type` 范围内统计全部分类，独立于 `class` 筛选，用于页面数量卡片；
- `GET /api/mainlines/{sector_id}/evidence` 返回板块的历史证据点；
- 主线字段和枚举已加入公共字段目录，便于后续页面扩展和联动。
