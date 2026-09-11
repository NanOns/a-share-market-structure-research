# M14 个人研究分支复开合同 V1

- 阶段：`M14-01-REOPEN-PERSONAL`
- 合同 ID：`M14_PERSONAL_RESEARCH_REOPEN_V1_0`
- 前置复核：`reports/upgrade_m14/m14_01_review_receipt_20260911.json`

## 裁定

用户明确选择仅个人使用的隔离分支后，允许继续执行 M14-02 的本机批次采集和视图验证；这不是来源生产准入，也不推翻 M14-01 对东方财富、同花顺 `REJECTED` 的许可裁定。

## 硬边界

- `production_adapters_enabled=false`、`publication_enabled=false`、`personal_research_only=true`；
- 不启用 API37–40、在线 UI、发布头、因子、scanner 或本地模型消费；
- 不共享、发布或向第三方提供采集对象；
- 只允许版本化适配器、15 秒/1 MiB/零重试预算、可审计请求/接收/来源时间和原子隔离落盘；
- 来源缺许可、`source_as_of` 或字段证据时，能力继续降级，不得把个人分支标成生产可用；
- 任何失败不得阻塞本地主流程，也不得改变 `analysis_snapshot` 身份。

## 复开验收

复开回执必须绑定本合同、原 M14-01 复核回执和用户个人研究选择；M14-02 起始回执必须引用本复开回执。生产来源仍保持 `REJECTED`，仅个人隔离对象可以继续。
