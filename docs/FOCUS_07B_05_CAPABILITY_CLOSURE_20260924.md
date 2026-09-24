# 07B-05 Source Capability Closure（2026-09-24）

## 阶段合同

依据修订方案第 21 节，`FOCUS_SOURCE_PATH_CAPABILITIES_V2` 对每条路径声明 required fact set，并以已注册提供者集合检查适用状态。`APPLICABLE` 路径缺提供者时在 preflight 报 `CAPABILITY_CONTRACT_BROKEN`；运行时字段键缺失同样报合同错误。已提供字段的空值是数据缺口，不作为合同错误。

## 证据与结果

- 当前适用路径：V3.3 候选 `STRUCTURE_DAMAGED`、`PULLBACK_HEALTHY`、`EXITED_FOLLOW_UP`；V3 股票 `EXITED_FOLLOW_UP`；V3 板块 `SECTOR_PERSISTENT`、`SECTOR_EXITED_FOLLOW_UP`。其它原 V1 适用路径缺事实提供者，已明确改为 `NOT_APPLICABLE`。详细审计见 `docs/audits/FOCUS_PATH_CAPABILITY_PROVIDER_GAP_20260924.md`。
- `release_gate` 校验来源合同静态闭包；`daily_builder` 在观察事实组装后校验实际字段键，并记录 V2 能力证据。已为所有股票和板块观察显式提供 `exited`，V3.3 无当日来源时显式提供空 `structure_break`。
- Focus 测试 111 项通过，含发布门错误声明与运行时缺字段。23 日已接受数据只读重建 310 条、写入 0；validity 全为 UNKNOWN；路径为 V3.3 `DATA_UNAVAILABLE` 273、板块 `SECTOR_PERSISTENT` 17、V3 股票 `UNCLASSIFIED` 20；闭包摘要 `424cf014e12f80371feddb6e55b85f2c018642300cad3bb8213935a1ff348637`。

## 验收与下一阶段

07B-05 的声明和运行时提供者闭包完成。V2 缩小了可用路径范围，不代表缺失策略已实现。下一阶段 07B-06 定义三态 validity 能力，区分规则不适用、事实缺失和可执行。24 日正式连续日验收仍属 07A。
