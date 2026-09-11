# M15-04 数据与恢复审计合同 v1

版本：`M15_DATA_RECOVERY_AUDIT_V1_0`  
依据：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 16.2、16.4、22.10 章，以及 M15-03 性能回执。  
阶段范围：T01–T24、schema 迁移/恢复、分析分片引用、旧 observations/outcomes 不可变、M15-03 开放项复核。

## 审计规则

- 生产库只读连接核查；不调用会登记迁移、写快照、写观察或清理对象的操作。
- 测试通过只作为行为证据，最终结论同时看当前发布绑定、分片/域表实际行、schema 哈希链和旧记录摘要。
- TDX 根目录继续只读；不因审计修复旧发布，不把共享多日 slice 的锚点日期直接改写成新 slice。
- 任何历史锚点表达、性能超预算或浏览器适配器限制均独立登记，不混入当前阶段的核心数据身份判断。

## T01–T24 证据矩阵

| 场景 | 主要证据 | 结果 |
|---|---|---|
| T01 发布相隔多交易日 | M7 quote/universe 测试 | PASS |
| T02 原始/复权输入替换 | M7 quote manifest/source freezer 测试 | PASS |
| T03 目标日后补资料 | M7 source freezer、M8 future guard 测试 | PASS |
| T04 北交所/新股/ST/未知/B股 | M7 display scope/universe 测试 | PASS |
| T05 250日图与100日新高 | M8 chart transform/RPS window 测试；当前查询窗口有 250 日起始边界 | PASS（测试证据） |
| T06 恒价与相等前高 | M8 RPS/new-high 测试 | PASS |
| T07 旧/新版金额比 | M8 technical contract、M10 sector amount 测试 | PASS |
| T08 交叉板块金额/成员计数 | M10 amount、M11 intersection 测试 | PASS |
| T09 删除/缺数/变弱分离 | M9 member state/cycle 测试 | PASS |
| T10 代表状态机 | M9 representative state 测试 | PASS |
| T11 持续与收缩冲突 | M10 mainline state 测试 | PASS |
| T12 目标股独强拒绝关联 | M11 association parity 测试 | PASS |
| T13 参考价/停牌/缺行情 UNKNOWN | M8 reference gate、M13 limit 测试 | PASS |
| T14 崩溃续算/同身份冲突 | M7 activation/history job 测试 | PASS |
| T15 备份恢复 | M7 recovery cleanup 测试；当前库引用完整性只读核查 | PASS |
| T16 在线重复/过期/后补原因 | M14 batch/evidence 测试；当前 online batch/payload/rank 均为 0 | PASS |
| T17 迟到响应与连续开股 | M12 drawer、M15 UI flow/performance contract 测试 | PASS |
| T18 证据长文/遮罩/Esc/焦点 | M12 browser/drawer 测试 | PASS |
| T19 历史结构与旧观察 | M8 history/coverage/technical 测试；observations/outcomes 摘要稳定 | PASS |
| T20 schema 失败与回退 | M7 migration executor 测试；生产库只读执行器返回 ALREADY_CURRENT | PASS |
| T21 新快照增量/分片复用 | M7 slice coordinator/recovery 测试；无孤儿引用，历史锚点项另审 | PASS（锚点项开放） |
| T22 真实页面规模与窗口 | M15-03 固定视口冷测、1920×1080 烟测；浏览器热 30 次适配器限制 | PARTIAL |
| T23 语义误排/人工覆盖 | M7 semantic registry 与 M11 attribute 测试 | PASS |
| T24 三态/并列/NULL排序 | M8 RPS、M9/M10/M11 稳定排序和三态测试 | PASS |

## 生产库只读证据

数据库 `data/database/market_research.duckdb` 以 read-only 打开：75 张表；`schema_migrations` 21 条（含基础版本），20 个迁移文件均有 `schema_migration_checks`，文件哈希不匹配 0，依赖顺序违规 0，`MigrationExecutor.apply()` 返回 `ALREADY_CURRENT`。分析快照 46、快照条目 1169、分析分片 381、存储对象 1。

分片条目、依赖、发布绑定和发布头的缺失引用均为 0；重复 snapshot entry key 和重复 publication head 也均为 0。共有 269 条历史 entry 的 `entry.trade_date` 不等于 slice 的锚点日期，但 269 条均可在对应域表按同一 `slice_id/trade_date` 找到实际行；当前绑定的三个分析快照 `m13-preview-2e7909345548ff1b`、`m11-association-preview-7f33abb5cecfe401` 和 `m8-m9-local-reconstructed-preview-v2-13eacb5a83486cd3` 的差异数分别为 0、0、13，最后 13 条属于该旧共享多日 slice 的同类锚点表达，故不改写旧快照。

`observations` 保持 5777 行、`outcomes` 保持 2030 行；只读摘要分别为 `f68d36144e6c5852468dfe7dcfc405b1ffef31b13580b0c294e0beada94218d3` 和 `937a6e75e4ce0217ef41d67f7a0aa9f6f7a2c57f833c5905a00f8326f99d4e88`。孤儿 outcome、无发布 observation 均为 0。M14 在线 batch、rank entry、payload 均为 0，未发现热榜历史快照落库。

## 阶段判定

核心数据引用、schema 哈希链、恢复测试、旧观察隔离和 T01–T21/T23–T24 通过；T22 继承 M15-03 的性能超预算和浏览器热操作适配器限制。历史共享 slice 锚点表达不改旧数据，作为 `M15-04-LEGACY-SHARED-SLICE-ANCHOR-DATES` 独立审计项开放。因此本阶段为 `DEGRADED_PASS`，`release_ready=false`，不允许进入正式入口切换。

下一阶段仍为 M15-05，但须人工启动；M15-03 性能预算、浏览器热 30 次和本阶段历史锚点项在正式切换前独立闭环。

## 2026-09-11 闭环补充

上述结论是刷新前的阶段结论。M15-03 已由 `m15_03_browser_retest_receipt_20260911.json` 完成固定视口浏览器冷/热复测；269 条历史锚点差异已由 `M15_04_LEGACY_SHARED_SLICE_COMPATIBILITY_V1_0` 明确为可读的旧共享多日 slice 语义，并由 `m15_04_data_recovery_audit_closure_receipt_20260911.json` 关闭。旧数据、旧发布和 TDX 输入均未改写。
