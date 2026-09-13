# V3 P11-02：停旧写证明与精确回收预览

日期：2026-09-13  
阶段合同：`V3_P11_OLD_WRITE_RECOVERY_PREVIEW_V1_0`  
适用主文档：`docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` §17.8、§17.9、§18.14 P11-02  
主文档 SHA-256：`52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B`

机器回执：[P11-02-OLD-WRITE-RECOVERY-PREVIEW.json](../reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json)

## 结论

阶段状态：**`DEGRADED_PASS`**。

六个首轮 P03 迁移域（technical、strength、high、member_state、structure、summary）均已证明当前 V3 daily writer 不调用旧 writer；逐 slice 的旧表行数与新 result object 行数全部一致。最新成功发布 `m4-8a99c99719061f4f1f166d0b9184506c`（2026-09-10）可通过关系 resolver、旧读 API 和迁移域 result binding 读取。

阶段没有执行删除、移动、VACUUM、备份、恢复或生产构建。`P11-03` 仍需要明确回收范围授权；当前 `reclaimable_bytes_now=0`，下表中的估算不是已回收空间。

## 阶段合同与边界

- P11-01 回执状态为 `DEGRADED_PASS`，满足本阶段前置条件。
- 复查的首轮迁移域为 V3 §17.6 明确的六个域；旧 writer 函数仍保留给兼容/迁移历史路径，不作为当前 daily writer。
- 旧关系副本和旧结果副本按确切表名、行数和持久 block 估算列出；不使用整个 `data` 目录或表名前缀作为删除目标。
- 解包预览复用 P04-03 只读策略：源包、metadata、最近两个已使用 bundle 受保护；2026-09-07/08 解包仅是等待 P11-03 授权的可再生候选。
- 备份复用当前物理链审计，全部对象继续保留为人工恢复验证候选。

## 1. 停旧写证明

静态扫描 `src` 与 `scripts` 共 243 个 Python 文件，未发现语法错误。六个迁移域的旧 writer 只有定义和兼容/迁移说明，没有非定义调用点：

| 域 | 旧表 | 新物理结果表 | 旧 writer 调用点 | 当前结果 |
|---|---|---|---:|---|
| technical | `stock_technical_daily` | `technical_result_rows` | 0 | `OLD_WRITE_STOP_PROVEN` |
| strength | `stock_strength_daily` | `strength_result_rows` | 0 | `OLD_WRITE_STOP_PROVEN` |
| high | `stock_high_daily` | `high_result_rows` | 0 | `OLD_WRITE_STOP_PROVEN` |
| member_state | `sector_member_state_daily` | `member_state_result_rows` | 0 | `OLD_WRITE_STOP_PROVEN` |
| structure | `historical_structure_daily` | `structure_result_rows` | 0 | `OLD_WRITE_STOP_PROVEN` |
| summary | `stock_structure_summary_daily` | `structure_summary_result_rows` | 0 | `OLD_WRITE_STOP_PROVEN` |

当前 daily 入口是 `src/workbench_service/app.py:run_today` → `scripts/build_m8_m9_preview.py --incremental-current`；新 writer 映射位于该脚本第 632–636、639 行。扫描没有发现生产代码向 `membership_entries` 全量 INSERT。

未迁移辅助域仍有两个明确旧写点，未被冒充为“已停旧写”：`src/workbench_analysis/member_state.py:476` 写 `sector_membership_changes`，`scripts/build_m11_association_preview.py:177` 写 `stock_sector_associations_daily`。它们登记为独立问题 `P11-02-AUD-AUXILIARY-WRITES-01`，后续需选择迁移或明确保留边界。

## 2. 旧/新结果等价与最新发布读取

六个迁移域共覆盖 154 个 `analysis_slices` 绑定中的迁移域 slice；当前逐 slice 旧表行数与 result object 行数均匹配，全部 `FULL_PASS`。新结果对象的物理存储使用 DuckDB result-row 表；同一结果内容被多个 slice 绑定时只按物理对象计一次，未将共享身份误报成历史丢失。

最新成功发布读取结果：

| 检查 | 结果 |
|---|---|
| publication | `m4-8a99c99719061f4f1f166d0b9184506c` / `2026-09-10` |
| 关系 binding | `revision_no=3`，`edge_count=72,136`，`READ_OK` |
| 迁移域 result binding | 14/14 entries `BOUND_AND_READABLE` |
| 未迁移辅助 entries | 26，按旧 reader 预期保留，不冒充新 result binding |
| `dashboard` | `READ_OK` |
| `sectors` | `READ_OK`，total 499，返回 10 |
| `sector_library` | `READ_OK`，total 554，返回 10 |
| `technical` | `READ_OK`，total 6,177，返回 10 |
| `new_highs` | `READ_OK`，total 273，返回 10 |

上述读取全部使用同一个 `read_only=True` DuckDB 连接注入 API 的请求上下文；未启动 build，也未修改 publication head。

## 3. 精确回收预览

### 3.1 关系旧副本

持久 block 估算方法为 `count(distinct persistent block_id) × PRAGMA database_size.block_size`，当前 block size 为 262,144 B。它是表级估算，不承诺执行逻辑 DELETE 后文件立即缩小。

| 确切表名 | 行数 | 估算字节 | 状态 |
|---|---:|---:|---|
| `membership_snapshots` | 6 | 262,144 | `PROTECTED_RELATION_HISTORY` |
| `membership_entries` | 435,472 | 53,215,232 | `PROTECTED_RELATION_HISTORY` |
| `sector_membership_changes` | 33,888 | 262,144 | `PROTECTED_RELATION_HISTORY` |
| `stock_sector_associations_daily` | 671,568 | 26,738,688 | `PROTECTED_RELATION_HISTORY` |
| **合计** | 1,140,934 | **80,478,208** | 当前不可回收 |

保护原因是最新发布仍通过 versioned relation binding 解析，legacy relation importer/research compatibility reader 仍存在，且没有 P11-03 范围授权。当前 relation revision 为 4、edge interval 为 75,136；这些新关系表不是旧副本，不列入删除候选。

### 3.2 首轮迁移域旧结果副本

| 域 | 旧表行数 | 持久 block 估算字节 | 逐 slice 等价 | 状态 |
|---|---:|---:|---|---|
| technical | 278,009 | 45,875,200 | `FULL_PASS` / 31 slices | `PROTECTED_LEGACY_HISTORY_WAITING_P11_03_SCOPE_AUTHORIZATION` |
| strength | 278,009 | 28,311,552 | `FULL_PASS` / 31 slices | 同上 |
| high | 1,112,040 | 20,709,376 | `FULL_PASS` / 31 slices | 同上 |
| member_state | 3,365,740 | 87,293,952 | `FULL_PASS` / 31 slices | 同上 |
| structure | 409,510 | 4,456,448 | `FULL_PASS` / 15 slices | 同上 |
| summary | 81,902 | 1,572,864 | `FULL_PASS` / 15 slices | 同上 |
| **合计** | 5,525,210 | **188,219,392** | 全部通过 | 当前不可回收 |

当前未授权回收估算为 0 B。所有旧表仍保留，因为还需要在 P11-03 中进行最终等价/引用复核，并确认兼容 reader、tombstone 和物理压缩边界。

首轮迁移之外的辅助结果表也逐项保护，未作为 P11-02 的回收候选：`sector_base_daily`（18,282 行）、`historical_coverage_daily`（33）、`representative_state_daily`（24,730）、`sector_cycle_daily`（24,730）、`mainline_daily`（26,592）、`market_cycle_daily`（21）、`market_reference_daily`（111,204）。机器回执保留了各表持久 block 估算和当前保护原因。

### 3.3 解包、metadata 和 phase-1 cache

| 对象 | 文件数 | 字节 | 当前决定 |
|---|---:|---:|---|
| `data/input_staging/extracted/20260907` | 12,399 | 948,565,152 | `PREVIEW_RECLAIMABLE_REBUILDABLE_WAITING_P11_03` |
| `data/input_staging/extracted/20260908` | 12,399 | 948,868,320 | `PREVIEW_RECLAIMABLE_REBUILDABLE_WAITING_P11_03` |
| `data/input_staging/extracted/20260909` | 12,402 | 949,178,304 | `PROTECTED_RECENT_USED_BUNDLE` |
| `data/input_staging/extracted/20260910` | 12,404 | 949,487,072 | `PROTECTED_RECENT_USED_BUNDLE` |
| `data/.phase1_cache` | 18,534 | 954,775,668 | `WITHIN_BUDGET`，不回收 |

最近两个按交易日和 bundle 身份保留；唯一 source package 与 4 组 metadata snapshot 全部受保护。2026-09-07/08 只是精确到目录的预览候选，当前不删除、不移动。

### 3.4 备份

当前真实只读物理链审计耗时约 19.98 s：`backup_catalog=12`、完整链 `12/12`、不完整链 0、孤立数据库/manifest/object 0/0/0；物理文件 16 个、22,737,490,910 B。12 个数据库文件、2 个 manifest 和 2 个 `.objects` 目录均按确切路径写入机器回执，全部为 `PROTECTED_BACKUP_CHAIN`，当前回收 0 B。

### 3.5 runtime

`runtime` 当前 77 个文件、5,531,414,409 B，未纳入 P04 输入回收策略。两个最大的 `v3_builder_audit*.duckdb` 各为 2,060,988,416 B，另有两个历史 drill 数据库各 660,090,880 B；它们都列为 `PROTECTED_RUNTIME_SCOPE_UNCONFIRMED`，需单独确认引用/owner 后才能进入后续范围，不使用整个 runtime 目录作为删除目标。

## 4. 独立问题与验收

### P11-02-AUD-STORAGE-01（开放）

范围：`storage_objects` 的 `referenced` 标志与完整 publication/result graph 对账，以及旧分析对象 tombstone 的物理路径核对。当前发现 17 个 stale referenced flags，另有 1 个 `analysis-obj-a9e40...` tombstone 指向不存在的物理文件。接受条件是在任何物理回收前逐对象完成 graph 对账；当前不清除标志、不删除、不补登记。

### P11-02-AUD-AUXILIARY-WRITES-01（开放）

范围：`sector_membership_changes`、`stock_sector_associations_daily` 的旧写入点。接受条件是迁移这些辅助域，或将它们登记为有界、可解释的保留旧 writer；当前不把它们纳入六域停旧写证明。

机器验收结果：

| 维度 | 结果 |
|---|---|
| 功能与旧读兼容 | `FULL_PASS` |
| 六域数据等价/绑定 | `FULL_PASS` |
| 六域停旧写 | `FULL_PASS` |
| 存储回收预览 | `DEGRADED_PASS`，有独立开放审计项 |
| 生产 DB | 只读；size `2,060,988,416` B、mtime_ns `1789229388750638600` 前后一致 |
| TDX / cleanup / backup / restore | 未访问 TDX；未执行 cleanup、backup 或 restore |

## 下一阶段

进入 **P11-03**。执行前必须取得明确回收范围授权；若未取得，则按精确清单登记 `WAITING_DECISION` 并保持所有保护对象。P11-03 不得把当前估算写成已回收空间，也不得通过全库 VACUUM 或新备份掩盖未解决的 storage audit。
