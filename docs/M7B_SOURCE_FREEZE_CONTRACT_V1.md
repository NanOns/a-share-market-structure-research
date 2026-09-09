# M7B-03 Source Freeze Contract v1

版本：`history-source-manifest-v1.0`；交付物为不可变 `SourceManifest`。

## 冻结策略

冻结器只引用或登记已存在于 Workbench 受管目录的本地输入，不修改 `D:/new_tdx` 或任何 TDX source directory。原始日线通过 source bundle extraction 根目录引用，报价计算使用已经由该冻结输入生成的 `data/normalized/adjusted_daily.parquet`；公司行为、证券元数据、板块成员源、交易日历和当前成员快照分别登记，避免把一个总包哈希误当成每个分片的经济输入哈希。source bundle 必须同时匹配发布的 source revision、source identity 组件和目标日期；缺少发布 source revision 时 fail-closed，不猜测 bundle。

每条输入记录包含角色、相对路径、文件 SHA-256（目录引用则包含 source bundle SHA-256、entry_count、total_bytes 与逐文件内容形成的 tree SHA-256）、`observed_at`、`effective_date` 和日期范围。当前成员快照明确标记 `CURRENT_SNAPSHOT_ONLY`、`pit_safe=false`；它可固定成员回算，但不能被描述为历史 PIT 成员序列。

## 身份与原子性

SourceManifest 绑定 `publication_id`、`source_revision_id`、source identity、已有 `INPUT_SNAPSHOT_MANIFEST` 和 source bundle。清单自身使用规范 JSON SHA-256，首次写入采用临时文件后原子替换；同路径内容不同则拒绝覆盖。TDX 只作为已封存 source bundle 的上游身份，不作为输出目录。

## 复核

`verify_source_manifest` 校验清单自身哈希、工作区路径边界、每个文件 SHA-256，以及目录的 tree SHA-256、文件数和总字节数。只改变目录内文件内容而保持文件数不变也必须失败。修订后的清单使用内容哈希文件名并保留旧清单，不覆盖历史身份；冻结步骤不做历史计算、不写分析表、不改变发布头。
