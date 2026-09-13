# V3 P06-01：板块 CURRENT 聚合

## 结论

依据最新 V3 主实施文档 §3.2、§4、§5.1、§18.9 与 C20-15，P06-01 验收结果：**FULL_PASS**。CURRENT 是独立的同日成员报价事实，不读取旧 `sector_cycle` 的长期 `rank`、`RET20` 或主线等级；旧域保持兼容用途。

## 阶段合同

- 合同 ID：`SECTOR_CURRENT_PREVIEW_1`；入口：`workbench_analysis.sector_attention.build_sector_current()`。
- 输入为同一 publication 绑定的成员快照、同日独立全 A 技术报价宇宙，及可选的正式 `SECTOR_AMOUNT_COMMON_AGG_V1` 金额 A。成员跨板块不会参与市场基准计算，避免重复计数。
- 每个 NORMAL_ATTRIBUTE 板块计算 `m1`（成员 ret1 中位数）、`b1`（有效成员上涨占比）、`rel1=m1-market_m1`、按 sector_type 的 `p1`、上涨人数、`top1_positive_share`，并记录报价/横截面覆盖和逐谓词 checks。
- CURRENT 同时要求：成员数不少于 5、板块报价覆盖不少于 .70、全市场报价覆盖不少于 .90、同类型横截面可评覆盖不少于 .70 且不少于 5、`m1>0`、`b1>=.60`、`rel1>=.003`、`p1>=.80`、至少 3 只上涨、最大单股上涨贡献不超过 .50。
- W 独立判断；本小任务已经实现 `(m1<0 and b1<.35)`。涉及 `b_delta3` 的第二分支等待 P06-02 的固定共同成员比较输入，明确保持 UNKNOWN，绝不回读旧 breadth 序列伪造结果。

## 实际输入证据

只读运行绑定 `2026-09-10` publication `m4-8a99c99719061f4f1f166d0b9184506c` 与 membership snapshot `f3c7f45…99567534`，读取 75,028 条成员关系和 6,178 条全 A 技术报价。机器证据见 [P06-01_CURRENT_DISTRIBUTION.json](../reports/upgrade_v3/P06-01_CURRENT_DISTRIBUTION.json)。

该日市场报价有效覆盖未达到 .90 的发布门，因此 554 个板块 CURRENT 均为 UNKNOWN，未发布任何 CURRENT 卡片：这不是 false 也不是空缺被默认通过。报告同时记录 496 个 NORMAL_ATTRIBUTE、294 个具正式金额 A 的板块，以及最主要的 UNKNOWN 原因 `UNKNOWN_MARKET_COVERAGE`（554）。这一真实分布证明“市场/类型覆盖不足时不发全市场 CURRENT 榜”的 fail-closed 行为；不以零命中为由调整阈值。

## 验收

定向测试覆盖：

- 长期强/旧排名高但当日 `m1` 为负，不得进入 CURRENT；
- 单股集中拉升即使其余指标较强也被 `NOT_SINGLE_STOCK_DRIVEN` 拒绝；
- 市场报价覆盖不足时所有 CURRENT 必须 UNKNOWN，且保留明确原因。

全量回归为 `193 passed in 50.15s`；新增 P06-01 定向测试为 `3 passed`，源码编译通过。真实运行只读数据库、原子写入报告；未写生产数据库、未修改 TDX、未启动 scanner，也不声称任何效果或概率。

## 下一阶段

进入 P06-02：在同一固定成员与三值基础上，计算 BREADTH_BUILD、BASE_BUILD、RECOVERY_BUILD 三个 POTENTIAL 分支，并与 CURRENT 强制互斥。
