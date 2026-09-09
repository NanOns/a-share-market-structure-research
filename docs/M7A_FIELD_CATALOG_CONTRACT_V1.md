# M7A 字段目录与 API 合同 v1

适用步骤：`M7A / 7A-06`。公共接口合同为 `workbench-api-v2.1`，字段目录为 `workbench-field-catalog-v1.0`。

## API05

`GET /api/metadata/field-catalog?api_contract=workbench-api-v2.1&language=zh-CN` 不依赖发布版本，返回：

- `items`：每个字段的 `field_id`、中文 `label`、`type`、`unit`、`nullable`、`description`、`sort_supported`。
- `enums`：所有公共枚举的规范值到中文显示名映射。前端不得通过中文反查枚举值。

当前目录由 `src/workbench_service/catalog.py` 提供，值为静态、可审计的本地合同注册表；新增或改名必须提升目录版本，并在 API 合同中说明兼容关系。

## API01 / API02 扩展

旧模式不变。传入 `include_analysis=1` 时：

- API01 `GET /api/publications` 的每个 `items` 包含 `revision`、`production_version`、`analysis_capabilities`，响应回显 `api_contract`。
- API02 `GET /api/identity` 回显 `contracts`、`capabilities`、`data_quality`、`analysis_snapshot_id`、`cutoff_date` 及发布修订信息。
- `AVAILABLE`、`PARTIAL`、`UNAVAILABLE`、`NOT_BUILT` 表示能力状态，不等于每个证券字段都有效；字段覆盖应由 `field_coverage` 或质量代码进一步解释。

历史分析尚未生成时，`analysis_snapshot_id` 保持 `null`，能力标记为 `NOT_BUILT`，不得用当前发布的局部结果伪造历史快照身份。

## 显示约束

原始数值的单位和数学含义不因中文显示改变：收益和比例以 `fraction` 传输，金额以 `CNY` 传输，价格以 `CNY/share` 传输。缺失可选数值显式为 `null`；不得将 `null` 转成零或猜测性中文标签。队列、研究带、板块类型、语义桶、报价状态和能力状态均使用本目录中的规范值。
