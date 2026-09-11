# M14-02 批次基础合同 V1

- 阶段：`M14-02`
- 合同 ID：`M14_BATCH_FOUNDATION_V1_0`
- 设计基线：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 14.2、14.3 节及第 22.9 节
- 来源范围：仅允许用户选择的 `PERSONAL_RESEARCH_ONLY` 本机分支；当前采集 `TONGHUASHUN_HOT_RANK` 与 `EASTMONEY_HOT_RANK`。东方财富载荷必须使用版本化解码器 `EASTMONEY_AES_CBC_NODE_CRYPTO_V1`，解码失败即拒绝该批次。

## 1. 交付范围

本阶段只实现单来源 `fetch → payload → batch` 分离、原始哈希、固定批次身份、显式代码映射和本地原子落盘。当前不实现 API37–40、页面、在线原因、盘中报价或龙虎榜融合。

生产发布保持关闭：`publication_enabled=false`、`production_adapters_enabled=false`。采集结果不得改变 `analysis_snapshot`、发布头、因子、scanner 或 M13 数据。

## 2. 请求和时间合同

- 每个端点单次请求，连接/总超时15秒，最大响应1 MiB，重试次数0；
- 请求和接收时间必须记录；响应没有 `source_as_of` 时，`source_as_of=NULL`，仅标记 `OBSERVED_AT_ONLY_SOURCE_AS_OF_MISSING`；
- 不得把观察时间伪装成来源时间，不得参与严格 `AS_OF` 历史视图；
- 原始响应按 `raw_sha256` 去重保存，批次按来源、dataset、列表类型、载荷哈希、观察时间和合同身份生成；
- 平台排名原样保留，过滤或映射不得重排平台名次；
- 证券代码只按明确市场码映射：同花顺使用 `17→SH`、`33→SZ`；东方财富使用载荷中的 `SRCSECURITYCODE`，并优先匹配当前 `RANK`；未知映射保留 NULL，不模糊拼接。

## 3. 隔离与验收

本机个人研究对象可以保存原始载荷和标准化批次，但必须写入隔离路径并带 `personal_research_only=true`。不得写入在线生产表、API/UI 消费表或发布对象。

本阶段通过条件：批次可重放、重复抓取不覆盖不同观察、失败不产生半成品、迁移在临时 DuckDB 原子应用、旧本地快照哈希不变。来源缺 `source_as_of` 和许可未明确属于独立开放项，不因单批采集成功关闭。
