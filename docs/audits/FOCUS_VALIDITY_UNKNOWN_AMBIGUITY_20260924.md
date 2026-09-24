# 独立审计项：Focus validity UNKNOWN 语义混淆

## 范围与证据

跨 V3 股票、V3 板块和 V3.3 候选。旧观察仅存 `validity_state=UNKNOWN`，无法区分来源模型没有正式失效规则和已有规则但事实不足。23 日已接受 Focus head 有 310 条观察，`facts` 均无 `validity_capability`；不能改写既有 as-recorded 证据。

## 修复

`FOCUS_VALIDITY_CAPABILITY_V1` 独立于 validity 结果，定义 `NOT_APPLICABLE`（V3 无正式规则）、`UNAVAILABLE`（V3.3 规则尚不能判定）和 `APPLICABLE`（V3.3 规则已有 TRUE/FALSE 结果）。每条新观察在 JSONB 证据中存合同、来源、理由、规则合同、AST 摘要、结果及证据摘要。已知 V3.3 结果若缺有效 AST 判定证据会拒绝。读取 API 的列表、板块成分和 episode 观察字段显式返回能力状态；旧记录返回 null，表示该合同尚未记录。

## 独立验收

23 日只读重建：310 条，`UNAVAILABLE` 273、`NOT_APPLICABLE` 37，validity 仍全为 UNKNOWN，写入 0。Focus 测试 116 项通过；PostgreSQL 临时表读取 API 演练通过，持久化变化 0。首个新正式交易日的落库与读取回查仍由 07A 正式连续日验收覆盖。
