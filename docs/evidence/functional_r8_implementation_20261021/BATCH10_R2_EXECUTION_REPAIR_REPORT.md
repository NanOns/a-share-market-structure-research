# BATCH10-R2 实际执行与修复报告

- 执行日期：2026-10-22（Asia/Shanghai）
- 仓库/分支：`NanOns/a-share-market-structure-research` / `codex/v4-unified-development`
- 起始基线与远端 HEAD：`00e4a34c64d2767f8b9f9ebc6efb7c7f7b50aeb3`
- 状态：`BATCH10_R2_PARTIAL / M0_PASS / M1_FAIL / M2_NOT_VERIFIABLE / M3_FAIL / M4_PARTIAL`
- 阶段 0：`DEGRADED_PASS`（既有阶段收据；受限扫描器能力仍按项目门禁关闭）

## 执行摘要

本轮实施了 D0 新候选源码字节的 content-addressed 只追加归档，并加入正例和损坏对象拒绝负例。两个定向测试通过。归档后 PG 仍通过原有 `source_path`、SHA256 和 bytes 严格读回，不放宽历史版本检查。

实际尝试了 10/16 D0 发布。发现唯一 T0=10/16 的 `ab13eb13456fcf2d725137d5404ef55e10a4b6496203da5ecb50faff7c694ea6` 候选，其 Core、Focus、Prewatch、Raw、Adjusted 等 Owner SHA 与 T0 错误的旧候选完全相同，故不能作为已按新日期成员重算的候选发布。受限 D0 publisher 实际被调用，并在插入 PG 行之前以 `D0_R8_SNAPSHOT_PUBLICATION_NOT_FOUND` 拒绝：开发 PG 只有旧 10/16 token `33cf6cdb91f51592cddebb41667c22720eb68e47592d179e8dfd0b0b5b5fc440` 的 R8 publication。

因此，本轮没有生成或发布满足完整重算要求的新 10/16 Owner/R8/D0 候选，也未启动四日顺序 rebase。没有执行 PG DDL/DML，没有改写既有 token、历史 NON_PIT、候选 Head 或正式 Head。28766 保持旧 10/21 token；没有把旧 token 页面误报为新版本验收。28765 未监听。

## M0—M4 结果

| 里程碑 | 结果 | 执行与证据 |
|---|---|---|
| R2-M0 不可变源码证据 | **PASS（代码/定向测试范围）** | 新增 `archive_immutable_bytes` 与 `_archive_source_ref`，按 SHA256 路径原子写入并验证 bytes；D0 publisher 对每个 consumed source 在计算闭包和写 PG 前归档原始字节。测试证明原工作文件改变后归档字节仍一致，并证明归档路径字节损坏会 fail closed。`tests/test_d0_immutable_source_archive_r2.py`：2 passed。旧 PG 记录与 reader 未改。 |
| R2-M1 10/16 重发 | **FAIL** | 现存正确成员 authority token `ab13…694ea6` 的 T0 是 10/16，但其 Owner SHA 与旧候选一致（membership、raw、adjusted、core、prewatch、focus 等均相同），不满足重算约束。实际执行 D0 发布命令后，在 R8 查询处以 `D0_R8_SNAPSHOT_PUBLICATION_NOT_FOUND` 失败；PG 中未出现 `ab13…694ea6` publication。旧 R8 token 仍为 `33cf…b5fc440`，D0 旧发布保留。 |
| R2-M2 四日顺序回补 | **NOT_VERIFIABLE** | 10/16 合格新候选和 R8/D0 发布未完成，不能把旧 10/19→10/20→10/21 predecessor 链重标为新链。旧 token 仍为 `f9c4…e136862`、`dba3…06bd9aad`、`c8b6…49d3c528`；没有写新日期行。 |
| R2-M3 28766 六入口业务真验 | **FAIL（新版本验收门）** | 28766 当前仍绑定旧 10/21 token `c8b6…49d3c528`。对 status/context/home/focus/forward statistics/priority/stocks 发起了真实 GET：均为 HTTP 200 且返回同一旧 token；旧业务值包括 Focus 3,929、Priority 可排名 936/股票 5,224。此结果只能证明旧页面前态，不能证明修订页面通过。六入口中的 Market/Sectors 业务字段、新日期 token、修正后分母/搜索/筛选/日周月及 DOM 均未验收。 |
| R2-M4 故障恢复/性能 | **PARTIAL** | content-addressed 内容损坏负例与源文件替换正例已执行通过；D0 发布缺少 R8 前态时 fail closed。未执行 PG 写入后 CAS 故障、部分日期恢复、四日混读和两轮服务性能测量。 |

## 实际执行记录

1. 读取 Drive 正式卡 `V4_BATCH10_R2_OFFICIAL_CODE_REPAIR_TASK_20261022.md`，核对 `docs/plans/V4_FUNCTIONAL_R8_REPAIR_PLAN_R2_FINAL_20261021.md`、Phase 0 收据及 D0 publisher/restricted reader。
2. 确认本地与远端基线一致：`00e4a34c64d2767f8b9f9ebc6efb7c7f7b50aeb3`。保留无关未跟踪 `.githooks/`、`config_back/`、`script_back/`。
3. dry-run 命令：

   ```powershell
   $env:TMP='G:\codex_tmp'; $env:TEMP='G:\codex_tmp'; $env:TMPDIR='G:\codex_tmp'; $env:PYTHONPATH='src'
   python scripts/run_batch10_r2_d0_release.py --from-date 2026-10-16 --to-date 2026-10-16 --input-root G:\codex_tmp\v4_daily_candidate_chain_20261020 --candidate-safe --dry-run
   ```

   dry-run 选中 T0=10/16 的 `ab13…694ea6` 候选。

4. 实际发布尝试（不是 dry-run）：

   ```powershell
   python scripts/run_batch10_r2_d0_release.py --from-date 2026-10-16 --to-date 2026-10-16 --input-root G:\codex_tmp\v4_daily_candidate_chain_20261020 --candidate-safe
   ```

   结果：`ValueError: D0_R8_SNAPSHOT_PUBLICATION_NOT_FOUND`，发生在 `d0_source_seal_r2.py::publish_candidate` 查询指定 token 的 R8 publication 时、任何 D0 publication/facts INSERT 前。PG 回读确认旧 R8/D0 行仍在，目标 `ab13…694ea6` 无发布行。

5. 只读 PG 身份确认：数据库 `market_research`，服务端 `127.0.0.1:5432`。读取 R8 publication 和 D0 publication 表，确认四日均只有旧 R8 token；没有执行 DDL/DML。
6. 服务前态：28766 监听 PID 7844，5432 PID 8640；28765 无 listener。28766 返回旧 `c8b6…49d3c528`，本轮未切换或重启它。

## 数据与完整性边界

- 保留的旧 token：10/16 `33cf6cdb91f51592cddebb41667c22720eb68e47592d179e8dfd0b0b5b5fc440`；10/19 `f9c4fa37dcef3cb4d28cf2a4e6e41f448898947be9fb16240f67cfd8ee136862`；10/20 `dba3131d7405ab5eac4fddff2a4b3ccb1ecb76ce3c70e907fd63a68406bd9aad`；10/21 `c8b6b32f7fd578c7a6bb347320382f091c1545b01c1d70b4a9ca68b049d3c528`。
- 唯一找到的正确日期成员候选 token：10/16 `ab13eb13456fcf2d725137d5404ef55e10a4b6496203da5ecb50faff7c694ea6`。它仅修订了候选绑定；Owner SHA 对照表明业务 Owner 未重算，所以不发布、不宣称完成。
- PG 事务只执行到 R8 存在性读取，随后 fail closed；没有数据表写入。不存在新 10/16—10/21 R8/D0 token。
- 全部旧 `AS_RECORDED=false`、`PIT_ELIGIBLE=false` / NON_PIT 事实保持原样；未切换生产 28765。

## 后续实施阻断

需先从 10/15 合法 predecessor 的受控候选状态真正重放 10/16：重建 dated membership snapshot/identity，重新生成 Core、Profile、Focus、Prewatch 及其它 Owner，完成 R8 G1–G4 与 PG publication；然后以新 10/16 Token 重建并验证 10/19、10/20、10/21。当前预制的 `ab13…694ea6` 不是可发布的重算候选。完成这些步骤前，不能将四日链、PG ReadIndex/Priority 或 28766 新页面标为 PASS。
