# M7B-04 Slice Coordination Contract v1

版本：`history-slice-coordination-v1.0`。

## 范围

本步骤只负责历史分片的准备、身份计算和封存，不实现技术因子、结构规则或市场聚合。调用方必须传入已冻结输入中的可解释行集，并为每个分片提供 `domain`、`trade_date`、`contract_id`、`basis` 和显式依赖。

## 身份

- `logical_hash` 使用列名和行内容的规范逻辑摘要，不依赖 Parquet 物理布局。
- `input_hash` 绑定逻辑摘要、行数、source manifest 和 source bundle 身份。
- `dependency_hash` 对 `input_domain`、`input_date`、`input_slice_id` 排序后规范化计算。
- `slice_id` 绑定域、交易日、合同、输入哈希、依赖哈希和 basis；任何经济输入或依赖变化都会得到新身份。
- 对象使用 `analysis-obj-{logical_hash}.parquet`。同内容跨重试或跨分片复用同一个对象；交易日或行集变化不会覆盖旧对象。

## 准备与 seal 顺序

1. 只读批量读取选定证券和交易日；不访问或写入 TDX source directory。
2. 写入 `data/analysis_objects` 下的临时 Parquet。
3. 读回临时对象，重新计算逻辑哈希和行数；校验通过后才原子替换为内容地址对象。
4. 在一个 DuckDB 事务中登记 `storage_objects`、`analysis_slices`、依赖关系和可选 `analysis_daily_basis`。
5. 同一 `slice_id` 只允许完全相同身份复用；对象缺失、哈希冲突或依赖不存在时 fail-closed。

## 交付验收

`SliceCoordinator.coordinate` 返回 `reused=false/true`，并返回 slice、object、逻辑哈希和行数。重复提交同一批次必须复用；修改行内容或依赖必须产生新身份；临时对象读回校验失败不得写入 `analysis_slices`。对象和 slice 都保留 basis 以及 `CURRENT_SNAPSHOT_ONLY` 的非 PIT 标记（如调用方采用该成员口径）。
