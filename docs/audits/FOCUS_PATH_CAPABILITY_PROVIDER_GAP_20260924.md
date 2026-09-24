# 独立审计项：Focus 路径能力与事实提供者不一致

## 范围

横跨 V3 股票、V3.3 候选和 V3 板块路径；独立于 07A 连续日正式验收。旧 `FOCUS_SOURCE_PATH_CAPABILITIES_V1` 将多条无运行时事实提供者的路径标为 `APPLICABLE`，使 `UNKNOWN` 混合了合同错误与市场缺值。

## 证据

`states.py` 所需字段与 `daily_builder.py` 实际输出逐项核对：`TREND_ACCELERATING` 缺 `rps20_delta3`、`trend_continue`、`primary_sector_current`；`SECTOR_ACCELERATING` 缺 `srel`、`prior_swidth`、`retention`；等待确认、板块背离、RPS 连续走弱等路径也缺提供者。23 日只读来源有 V3.3 273 条、V3 板块 17 条、V3 股票 20 条。23 日已接受历史版本不回写。

## 修复与独立验收

新 `FOCUS_SOURCE_PATH_CAPABILITIES_V2` 把每条路径的所需字段、注册提供者和适用状态纳入可审计证据摘要。当前保留 V3.3 三条、V3 股票一条、V3 板块两条有提供者的路径，其余标为 `NOT_APPLICABLE`。发布门检查静态声明；日构建检查观察记录实际包含全部字段。提供者键缺失报 `CAPABILITY_CONTRACT_BROKEN`；键存在但值为 `None` 仍按数据缺值处理。

单元与发布门测试覆盖错误声明及运行时缺字段；Focus 111 项通过。23 日只读重建 310 条、写入 0，能力校验通过。此审计项的代码和历史只读验收完成；24 日正式写入是 07A 独立验收项目。
