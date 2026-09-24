# FOCUS-02 已接受来源与离线行情事实阶段记录

> 日期：2026-09-23；本记录后续阶段结果见 `FOCUS_02_BASKET_STRENGTH_ACCEPTANCE_20260923.md`。

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 6、14、16、17、19、20 节 |
| prior_phase_0 | `FULL_PASS_TDX_NATIVE`；本阶段只读取 PostgreSQL 与既有 normalized Parquet，不访问 TDX 根目录 |
| stage_contract | `FOCUS_PG_ACCEPTED_SOURCE_READER_V1`、`FOCUS_OBSERVATION_INPUT_V1`、`FOCUS_SECTOR_BASKET_SOURCE_V1` |
| source_authority | 只读 `publication_heads`、同 publication 的 COMPLETE V3 research run、同日且同 publication 的 COMPLETE V3.3 bundle head；不使用文件 mtime 选源 |
| latest_source_probe | 2026-09-22；V3 shortlist stock 40、individual 0、V3 sector 80、V3.3 candidate 273；四族能力均 COMPLETE；补入 V3.3 matched categories 后 source identity digest `4160454e07471b27c418a6d4c48b508585a32fb8a708f5b814785963f5352279` |
| local_price_probe | 可用 normalized artifact SHA-256 `ac248c100ddce7dd6927d7b29e601f3c45193ae94e7880957c76637d0a07f81f`；对 `SH.601801` 的 2026-09-22 实际 BAR 只读物化为 READY，调整版本 `tdx-affine-qfq-v0.2`，输入摘要 `b080c9a506b5ba86b53e8c2b87ac2ebbf89f87016e6542d8832d99dbbfee688e` |
| sector_authority_probe | 当前 publication 的板块成员取其绑定的 `relation_edge_intervals` revision；80 个入选板块全部有成员，单板块成员数 5–462，集合摘要 `36d9187e933e4984f53c6d5a12cdb9c1b0ca0f72a0850be1bd112a4e915b07d1` |
| full_day_input_probe | 2026-09-22 来源行 393、股票来源行 313、唯一股票事实 301；393 个 tracking key，最终计划摘要 `2ad1f1ba3c281b58aafb83966a956b30fb2274c91d44a3d43a3f8f6c8b6b1b62`；共扫描 2,562 个唯一证券，301 个股票事实 READY，80 个板块单日收益及成员宽度 READY，最低价格覆盖 `0.9782608695652173913043478261`；最终输入集合摘要 `ef167d21c8dc027ea52d6fc3c2aa919a2dd1a7601835eacdaedf2354583fee91` |
| tests | 最终 34 项通过；阶段初期的 30 项结果保留为过程证据 |
| acceptance_result | **`DEGRADED_PASS / FIRST_ACCEPTED_DAY_INPUTS_READY`**，详见后续篮子与强度回执；真实历史连续性仍待正式 Focus 日累积后验收 |
| next_stage | `FOCUS-03` 完整 input manifest、状态解释与 core writer 回滚演练；正式 head 激活须经独立门 |

## 已实现的边界

- 来源读写分离。V3.3 `result_payload` 只在内存中检查请求时 hot-rank 字段，不纳入持久化事实；源行只保留允许的候选、因子和 scanner 证据。
- 股票物化先校验整个 normalized artifact SHA-256；只读取指定证券与日期区间。日期缺失、非实际 BAR、调整版本或 VERIFIED 状态不一致时 fail closed，不能用合成 close 或跳日收益补足。
- 每个 observation input 用 canonical JSON 摘要命名与原子落盘；相同路径但不同内容拒绝覆盖。使用位置必须位于 TDX 根目录之外。
- 板块成员按 publication 绑定关系 revision 固定，重复关系边只记一次证券；没有成员或缺绑定则失败，不用最新可变 revision 猜测。
- 板块单日收益只对有前后日真实 BAR 的成员收益取中位数；不足 80% 成员覆盖时返回 `DATA_UNAVAILABLE`，不计算假净值。
- 事实读取先按 `(证券, 日期)` 合并为一次 SHA 校验和一次 Parquet 扫描，再按每个 anchor 起点投射；同股同日跨来源保留各自 lifecycle 决策和 episode 身份。日历独立从 normalized 主交易会话标志导出，非主交易日行不参与路径。
- 冻结板块篮子的逐会话 NAV 遇到覆盖缺口即中断，后续会话不跨缺口续接；单日收益仍可单独诊断。
- 板块起点会话同样要求至少 80% 成员有可靠实际价格；否则连基准 NAV=1 也不发布。
- 前态只读上一已接受 Focus head，并拒绝 `REPLAY_REQUIRED` 链；已完成 episode 的最后身份可供日后重入时建立 parent 链，不从最大 run/revision 或当前投影猜前态。当前真实库还没有 Focus head，所以首次日探针的前态为空。

## 当前未开放的能力

`workbench.focus_*` 表目前仍无业务 run/head。不能将此回执当作持续观察模块已上线。全日演练仍以无历史 Focus head 的首次日为前提；它不证明旧 episode 的冻结篮子、跨日宽度/轮动或 T+N outcome 已有完整事实覆盖。探针中的 14 个自然日读取范围只用于寻找最近前一主交易会话，正式任务必须由版本化主交易日历提供精确会话范围，不能把这个探针范围当业务期限。

板块强势成员状态在现有 M9 `sector_cycle` 合同中以成员状态输入形成 `strong_count` 和 `retention_rate`；Focus 不从涨幅或均线临时重定义强势成员。要激活 `SWIDTH/RETENTION` 的 Focus 状态分支，还需把接受的 analysis snapshot 及对应成员状态事实绑定到同一 publication/日期，并验证输入覆盖。绑定完成前这些谓词保持 U。
