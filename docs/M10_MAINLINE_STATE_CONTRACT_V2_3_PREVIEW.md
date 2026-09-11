# M10 主线状态合同 v2.3-preview

合同 ID：`MAINLINE_STATE_V2_3_PREVIEW`

## 1. 有效样本与数据不足

对单个板块来说，每个交易日最多贡献一个板块观察值；只有该日的 `sector_rs20_pct` 是可计算、可验证的数值，才计入 `valid_observation_days`。

- `observation_days`：进入分类计算的交易日数量；
- `valid_observation_days`：具有有效板块 RPS20 分位的交易日数量；
- 缺少 RPS20 分位不按 0 计算，也不直接解释为退潮；
- 当前覆盖率必须达到 80%，否则不能输出正式主线状态；
- 3、5、10 日分别是观察、快速状态、稳定状态门槛；20 日仅用于完整证据展示，暂不作为所有状态的总闸门。

`DATA_INSUFFICIENT` 有三类明确原因：

1. `OBSERVATION_HISTORY_NOT_REACHED`：有效 RPS20 观察日不足 3 天；
2. `BASE_INPUT_UNKNOWN`：当前成员覆盖率缺失或未达到 80%；
3. `UNKNOWN_HIGHER_PRIORITY`：更高优先级状态所需的条件未知，不能把板块降级为较低优先级状态。

因此，`DATA_INSUFFICIENT` 不等于主线弱，也不等于退潮。3 至 4 个有效观察日、且当前覆盖率合格时，显示为 `OBSERVING`。

## 2. 分类依据与边界

分类条件全部写入 `predicates`，不使用隐藏综合分数，优先级为：

其中，M10 使用的上涨宽度 B 为 `breadth_ret1_common`：前后比较日同时存在、且两日当日涨幅都有效的共同成员中，当日上涨成员数除以该共同有效成员数。B 的 1 日/3 日变化也必须在各自同一共同有效成员集合上分别计算，不能用两个不同成员分母的宽度直接相减；全体当日成员宽度 `breadth_ret1` 仅作描述性统计。

板块 `sector_rs20` 必须来自有效 RS20 成员统计；RS20 缺失时保持 NULL，不得用 RET20 回填。成员状态的板块内排名严格使用 RET20，RS20 不替代该排名口径。

1. `FADING`：历史曾达到入选阈值，当前分位低于 60%，相对比较日明显回落，且上涨宽度、成交额都严格下降；持平不算下降；
2. `HIGH_LEVEL_CONTRACTION`：当前仍在 80% 以上，但宽度或成员留存明显收缩；
3. `REACCELERATING`：10 日入选次数、当前分位、分位变化、宽度变化和成交额同时满足；
4. `SUSTAINED`：短期持续位于高位，宽度和成员留存达标；
5. `NEW`：当前达到高位，当前日前连续 5 个历史位置中达到入选阈值不超过 1 天，宽度/成交额改善，且进入成员多于退出成员；
6. `BROADENING`：当前达到扩散阈值，进入成员多于退出成员，宽度改善；
7. `OBSERVING`：数据足够但没有任何分类条件成立。

状态变化必须区分市场变化和口径变化：合同或配置变化记录为 `MODEL_CHANGE`，历史基础变化记录为 `BASIS_CHANGE`，不能解释成市场退潮。

## 3. 页面与证据

- 页面只读取当前发布绑定的 M10 分析快照；
- 一级行业、细分行业、概念和风格分组独立展示；
- 主线证据显示当前分类、历史阶段、缺失字段、冲突解释和每个谓词的业务含义；
- 历史阶段阈值从快照中的 `history_policy` 读取，不在前端另写一套阈值；
- `history_basis=RECONSTRUCTED` 表示本地历史重建，不代表官方原生主线标签。

## 4. 存储与接口

- 结果存储于 `mainline_daily`，与 `sector_cycle_daily` 按 `slice_id + sector_id + trade_date` 绑定；
- `GET /api/mainlines` 返回当前截止日列表、分类数量和 `history_policy`；
- `GET /api/mainlines/{sector_id}/evidence` 返回历史证据点和同一份 `history_policy`；
- 行业父子展示读取 M9 生成并绑定到快照的静态层级表；该表以已审计的 TDX 行业代码前缀规则构建。概念和风格保持平级展示；地区不进入 M10 公共主线列表。
