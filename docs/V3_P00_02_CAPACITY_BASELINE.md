# V3 P00-02 容量与历史覆盖基线

## 采集合同

| 字段 | 值 |
|---|---|
| task_id | P00-02 |
| status | PASS |
| collected_at | 2026-09-12T00:15:38+08:00 |
| branch | codex/v3-upgrade-analysis |
| input_revision | 5ae8de42b1bf742aafdda535f2367f4b4dd0378a |
| V3 主实施文档 SHA-256 | 912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24 |
| database | data/database/market_research.duckdb，以 read_only=True 打开 |
| 采集范围 | 数据库全表行数、业务键/切片键、slice/version、数据库块、data 目录、runtime/cache 大文件、关系边摘要、high window、结果摘要、当前发布引用 |
| 写入行为 | 无；未执行清理、VACUUM、备份、迁移、重建或数据库事务写入 |
| TDX | 未访问、未写入 |

本报告遵循 V3 主实施文档第 17.2、17.8、18.3 P00-02 的口径。键重复和内容重复分开记录；无法从只读证据确认可删除大小的对象标为 UNKNOWN，不用目录差额冒充可回收空间。

## 一、数据库物理基线

### 1.1 DuckDB 块占用

| 指标 | 值 |
|---|---:|
| PRAGMA database_size | 1.6 GiB |
| block_size | 262,144 bytes |
| total_blocks | 6,594 |
| used_blocks | 5,759 |
| free_blocks | 835 |
| 空闲块折算 | 218,890,240 bytes，约 208.75 MiB |
| WAL | 0 bytes |
| memory_usage | 7.7 MiB |
| 数据库文件 market_research.duckdb | 1,728,589,824 bytes |
| data/database 目录 | 4 files，1,731,747,842 bytes |

文件大小、有效数据大小和空闲块不能互相替代；本阶段没有执行压缩或物理迁移。

### 1.2 全部数据库表行数

当前共 75 张 BASE TABLE。以下是只读 COUNT(*) 结果：

| 表 | 行数 | 表 | 行数 |
|---|---:|---|---:|
| analysis_daily_basis | 371 | analysis_slice_dependencies | 509 |
| analysis_slices | 389 | analysis_snapshot_audit_status | 4 |
| analysis_snapshot_entries | 1,209 | analysis_snapshot_hierarchy | 23 |
| analysis_snapshots | 47 | audit_receipts | 0 |
| backup_catalog | 33 | candidate_daily | 8,607 |
| cleanup_jobs | 1 | config_versions | 1 |
| data_sources | 0 | historical_coverage_daily | 33 |
| historical_structure_daily | 409,510 | job_attempts | 22 |
| job_events | 42 | jobs | 14 |
| leases | 0 | limit_ladder_daily | 129,717 |
| limit_promotion_daily | 56 | limit_rule_versions | 21 |
| m8c_rule_audit_events | 11 | mainline_daily | 26,592 |
| market_cycle_daily | 21 | market_daily | 2 |
| market_reference_daily | 111,204 | membership_entries | 435,472 |
| membership_snapshot_metadata | 0 | membership_snapshots | 6 |
| metadata_snapshots | 2 | observations | 5,777 |
| online_batches | 0 | online_evidence | 0 |
| online_fetch_runs | 0 | online_payloads | 0 |
| online_quote_entries | 0 | online_rank_entries | 0 |
| online_security_map | 0 | outcomes | 2,030 |
| publication_analysis_snapshots | 3 | publication_artifacts | 26 |
| publication_heads | 5 | publication_memberships | 7 |
| publications | 8 | queue_memberships | 6,815 |
| queue_rankings | 8,406 | representative_state_daily | 24,730 |
| schema_migration_checks | 20 | schema_migrations | 21 |
| sector_base_daily | 18,282 | sector_cycle_daily | 24,730 |
| sector_daily | 4,008 | sector_member_state_daily | 3,365,740 |
| sector_membership_changes | 33,888 | sector_semantic_versions | 554 |
| sector_versions | 0 | security_metadata_versions | 37,068 |
| security_versions | 0 | source_bundles | 5 |
| source_files | 0 | source_packages | 4 |
| state_transitions | 0 | stock_daily | 43,436 |
| stock_high_daily | 1,112,040 | stock_sector_associations_daily | 671,568 |
| stock_strength_daily | 278,009 | stock_structure_summary_daily | 81,902 |
| stock_technical_daily | 278,009 | storage_objects | 1 |
| structure_details | 213,490 | tdx_sector_hierarchy_nodes | 1,662 |
| tdx_sector_hierarchy_versions | 3 | unified_board | 8,406 |
| universe_state_daily | 0 |  |  |

## 二、库外容量

目录统计只覆盖项目目录，不递归进入 TDX 源目录；父目录数字包含子目录，不能相加。

| 路径 | 文件数 | 字节数 | 约 GiB | 解释 |
|---|---:|---:|---:|---|
| data | 68,301 | 13,160,481,049 | 12.26 | 项目数据总盘面 |
| data/input_staging | 49,642 | 6,106,503,079 | 5.69 | 源包、解包和 metadata |
| data/backups | 72 | 3,466,219,849 | 3.23 | catalog 仅登记 33 个备份对象，目录还含 manifest/objects；可删除大小 UNKNOWN |
| data/.phase1_cache | 18,534 | 954,775,668 | 0.89 | 可再生缓存；活动引用和最近使用边界尚未完成审计 |
| data/normalized | 1 | 876,179,188 | 0.82 | 全历史规范化资产；不等同于重复 |
| data/database | 4 | 1,731,747,842 | 1.61 | 主库、候选库和锁文件 |
| data/analysis_objects | 1 | 9,571 | <0.01 | 已登记的 PARQUET 分析对象 |
| data/source_bundles | 9 | 26,675 | <0.01 | source bundle 元数据/目录对象 |
| data/online | 17 | 339,881 | <0.01 | 在线能力相关小文件 |
| runtime | 74 | 1,409,431,425 | 1.31 | 项目外库内运行时、迁移/恢复演练和运行资产 |
| logs | 74 | 244,849,532 | 0.23 | 日志；是否可删需按保留和审计引用确认 |

runtime 中发现的两个大文件：

| 文件 | 字节数 | 当前分类 |
|---|---:|---|
| runtime/migration_drills/m5-ui-audit-market.duckdb | 660,090,880 | 迁移演练数据库；可删除大小 UNKNOWN |
| runtime/restore_drills/20260908T103624951391/backup-20260908T103503Z-c8ff439c73ec.duckdb | 660,090,880 | 恢复演练数据库；可删除大小 UNKNOWN |

上述对象只被识别和登记，没有隔离或删除。不得把 runtime 演练库、日志或 backup 目录的全部差额直接宣称为可回收。

## 三、关系边与 membership 快照

### 3.1 总体

| 指标 | 值 |
|---|---:|
| membership_entries 行数 | 435,472 |
| membership_snapshots | 6 |
| 跨所有快照的 distinct (sector_id, security_id) | 76,875 |
| 6 个快照的 payload_values | 每个快照均等于该快照行数 |

### 3.2 每个快照

| trade_date | snapshot_version | 行数 | distinct 边键 | distinct payload | 边集合 hash |
|---|---|---:|---:|---:|---|
| 2026-09-04 | sector-membership-snapshot-v1.0 | 72,004 | 72,004 | 72,004 | 070598a5713d6f013c4441c2c54d995f |
| 2026-09-07 | sector-membership-snapshot-v1.0 | 72,084 | 72,084 | 72,084 | ff51a64dabb99f6a923467ffab97da5b |
| 2026-09-07 | m4-source-bundle-v1 | 72,084 | 72,084 | 72,084 | ff51a64dabb99f6a923467ffab97da5b |
| 2026-09-08 | m4-source-bundle-v1 | 72,136 | 72,136 | 72,136 | d4e986a4fa70a60ffc4fb8dbb33c550e |
| 2026-09-09 | m4-source-bundle-v1 | 72,136 | 72,136 | 72,136 | d4e986a4fa70a60ffc4fb8dbb33c550e |
| 2026-09-10 | m4-source-bundle-v1 | 75,028 | 75,028 | 75,028 | d2bee83dc9132db2528047c95c930abf |

按排序后的 sector_id、security_id 计算边集合摘要，2026-09-07 的两个快照相同，2026-09-08/09 的两个快照相同。该结论只证明关系边集合相同，不证明完整 payload、来源、观察日期和身份可以盲删；本阶段不做删除。

## 四、切片级业务键与重复倍数

业务键不含 slice_id；slice 键包含 slice_id。同一业务键跨多个 slice 出现是键级重复候选，不等于内容一定可合并。

| 表 | 行数 | 业务键数 | slice 键数 | slices | 日期数 | 关键维度 |
|---|---:|---:|---:|---:|---:|---|
| sector_member_state_daily | 3,365,740 | 374,014 | 3,365,740 | 31 | 5 | trade_date, sector_id, security_id |
| stock_technical_daily | 278,009 | 30,890 | 278,009 | 31 | 5 | trade_date, security_id |
| stock_strength_daily | 278,009 | 30,890 | 278,009 | 31 | 5 | trade_date, security_id |
| stock_high_daily | 1,112,040 | 123,560 | 1,112,040 | 31 | 5 | trade_date, security_id, window；4 windows |
| stock_sector_associations_daily | 671,568 | 298,467 | 671,568 | 9 | 4 | trade_date, security_id, sector_id |
| historical_structure_daily | 409,510 | 81,905 | 409,510 | 15 | 3 | trade_date, security_id, queue_name |
| stock_structure_summary_daily | 81,902 | 16,381 | 81,902 | 15 | 3 | trade_date, security_id |

### 4.1 high 的 window 维度

| window | 行数 | (trade_date, security_id) 键数 | slices |
|---:|---:|---:|---:|
| 20 | 278,010 | 30,890 | 31 |
| 30 | 278,010 | 30,890 | 31 |
| 60 | 278,010 | 30,890 | 31 |
| 100 | 278,010 | 30,890 | 31 |

新高的业务键必须包含 window；若忽略 window，会把 4 个合法窗口错误计算成约 36 倍重复。

## 五、slice/version 与内容摘要分组

analysis_slices 共 389 条，18 个 domain，4 个日期，166 个 logical_hash，1 个 storage_object_id。下表以 domain、trade_date、contract_id、logical_hash 为内容候选分组键；duplicate_excess 只表示同组多出的 slice 身份数，不是可直接删除行数。

| domain | slices | 日期数 | 内容组数 | duplicate_excess | 最大同组重复 | 重复组数 |
|---|---:|---:|---:|---:|---:|---:|
| association | 9 | 4 | 9 | 0 | 1 | 0 |
| coverage | 27 | 4 | 7 | 20 | 7 | 4 |
| high | 31 | 4 | 8 | 23 | 7 | 5 |
| limit_ladder | 21 | 3 | 9 | 12 | 5 | 3 |
| limit_promotion | 14 | 2 | 4 | 10 | 6 | 2 |
| mainline | 20 | 4 | 18 | 2 | 2 | 2 |
| market_cycle | 21 | 3 | 9 | 12 | 5 | 3 |
| market_reference | 18 | 3 | 18 | 0 | 1 | 0 |
| member_state | 31 | 4 | 16 | 15 | 4 | 7 |
| membership_changes | 14 | 2 | 5 | 9 | 5 | 4 |
| quote_input | 2 | 1 | 1 | 1 | 2 | 1 |
| representative | 31 | 4 | 11 | 20 | 5 | 8 |
| sector_base | 27 | 4 | 8 | 19 | 7 | 4 |
| sector_cycle | 31 | 4 | 26 | 5 | 3 | 4 |
| strength | 31 | 4 | 12 | 19 | 6 | 4 |
| structure | 15 | 3 | 3 | 12 | 12 | 2 |
| summary | 15 | 3 | 3 | 12 | 12 | 2 |
| technical | 31 | 4 | 12 | 19 | 6 | 4 |

最明显的内容摘要重复候选是 structure 和 summary 各有一个内容组重复 12 次；coverage/high/sector_base 等也有最多 7 次的同摘要组。内容 hash 相同仍需再核对 schema、质量、价格基准、来源依赖和身份层，不能以 hash 直接回收。

## 六、当前发布引用与唯一原始证据

### 6.1 发布头与分析绑定

当前 publication_heads 共 5 个日期：

| trade_date | publication_id |
|---|---|
| 2026-09-04 | 695c7ae5affd4abbb3d86eddb4b154e0 |
| 2026-09-07 | m4-5212a91982eb6d63b7455d8855676fa5 |
| 2026-09-08 | m4-44e401cad4337d38105b496077a4f36e |
| 2026-09-09 | m4-c136480b3c17eae920dc92bd0f77d5b6 |
| 2026-09-10 | m4-8a99c99719061f4f1f166d0b9184506c |

publication_analysis_snapshots 当前仅有 3 个绑定：

| publication_id | snapshot_id | entries | entry domains |
|---|---|---:|---:|
| m4-44e401cad4337d38105b496077a4f36e | m8-m9-local-reconstructed-preview-v2-13eacb5a83486cd3 | 22 | 9 |
| m4-c136480b3c17eae920dc92bd0f77d5b6 | m11-association-preview-7f33abb5cecfe401 | 33 | 13 |
| m4-8a99c99719061f4f1f166d0b9184506c | m13-preview-e71f413f40ac7270 | 40 | 15 |

### 6.2 storage object 引用异常

storage_objects 只有 1 条，payload 标记 referenced=true，路径为 data/analysis_objects 下的一个 PARQUET 对象。analysis_slices 中有 2 个 quote_input slice 指向它，但这两个 slice 没有出现在任何 analysis_snapshot_entries 中；从当前 publication head 经 snapshot、entry、slice 链路查询，实际被当前发布引用的 storage object 数为 0。

这是需要后续单独追踪的引用一致性问题，不能据此删除该对象；对象的可删除大小记为 UNKNOWN。

### 6.3 源包、原始证据和备份

数据库登记 5 个 source_bundles、4 个 source_packages、33 个 backup_catalog 记录。source bundle 的 package SHA-256、目标交易日、解包根和 metadata 摘要存在于数据库；当前 publication 的 source_path 指向 data/source_bundles 下对应对象。规范化全历史文件 data/normalized 只有 1 个 876,179,188 字节文件，不因单文件形态认定重复。

data/input_staging 中的源包和解包内容、data/normalized、TDX 输入均按唯一原始证据或可复算证据保护处理；本阶段不删除、不移动、不覆盖。

## 七、结论、开放项与下一阶段

### 7.1 P00-02 验收

- 已记录采集时间、代码 revision、主库路径和 V3 文档 hash。
- 已记录全库每表行数、DuckDB block 使用和空闲块。
- 已按 data 目录统计库外文件，并补查 runtime 与 logs 大文件。
- 已把关系边集合重复、业务键重复、slice 身份重复、内容摘要重复分开记录。
- high 的 4 个 window 已单独计入业务键。
- 已记录当前 publication head、analysis snapshot、slice 和 storage object 的引用链。
- 可删除大小在缺少完整引用/保护证明处均为 UNKNOWN。
- 未写入 TDX，未执行任何清理。

P00-02 结果为 PASS，允许进入 P00-03。

### 7.2 需要单独跟踪但不在本阶段处理的项目

1. storage_objects 的 referenced=true 与当前 publication 实际引用数为 0 不一致，需要后续核对绑定链。
2. membership_entries 的相同边集合仍携带不同快照身份和 payload，不能直接删整行。
3. 31 个 slice 的技术/强度/新高/成员状态等结果存在内容摘要归并候选，应在 V3 结果共享契约确认后迁移。
4. data/backups 的 33 条 catalog 与 72 个物理文件之间需要建立 manifest/objects 对照；可回收量当前 UNKNOWN。
5. runtime 的迁移/恢复演练库和 logs 需要按审计保留策略分类，不能按大文件自动删除。

下一阶段：P00-03，冻结配置、DTO、合成夹具和 capability 状态；P00-03 前不执行容量清理、不改变旧表、不启动 scanner。
