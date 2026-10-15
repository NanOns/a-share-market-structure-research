# R8 两日修复与断档验收（阶段记录）

- 任务合同：`V4-R8-UNIFIED-REPAIR-2DAY-CATCHUP-20261015/R1`。
- 本阶段：Step A 源码修复与隔离 fixture；已查阅任务卡 §0–§7、`docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`、`docs/upgrade/V4_R7_FORWARD_SIGNAL_SPEC_R1.md` 和 `R8_UNIFIED_SOURCE_FINAL.md`。
- 当前状态：**`FIXED_SOURCE_PASS_WAIT_2DAY_DATA`**。这只接受已执行的源码与 fixture 范围，不代表真实 10/14、10/15 数据验收或放行打包。
- 唯一开发分支：`codex/v4-unified-development`；起始 HEAD 与远端一致，为 `ca324fe2eaa86d461d56313cf65d90e7a921c1e2`。源码提交：`7f63eab3f`（已推送）。未创建分支。

## 本阶段改动与证据

1. **FIX-01 旧 `NO_QUOTE` 纠错**：待结算扫描纳入旧 `NO_QUOTE`；新增 `LEGACY_NO_QUOTE_REVIEW_R1` 受控检测。来源未接受追加 `DUE_SOURCE_NOT_ACCEPTED`；来源已接受但无证券级状态证明追加 `SOURCE_GAP` 或真实价格结算；有效 `NO_QUOTE/SUSPENDED` 证券事实保留。修订是 append-only，记录新旧 revision、原因、来源日、source digest/bindings 与时钟。相同 digest 幂等，来源 digest 变化追加新 revision。首页成熟数量与 Forward 分页/汇总改用相同最新有效修订计算。真实旧账本计数和 10/14 依赖案例等 15 日合并源就绪后验收，当前不填造数字。
2. **FIX-02 采集计划时钟**：`next_capture_plan` 升为 R2，按官方会话、Head 缺口、源 ready 回执及只读日更作业状态计算。两日缺口只有两日来源都 ready 才显示为一个 batch。15:00 仅为市场收盘；冻结窗口截止为下一会话 09:30；没有可靠调度触发或调度器被暂停时 `next_attempt_at` 留空。Forward 页及候选来源页显示价格收盘、源就绪、首次可用、Head 接受、冻结和窗口结束。
3. **FIX-03 成员快照 PIT 证明**：移除在线路径固定 `AS_RECORDED`。以逐板块有效日、observed/available 时钟、源哈希/路径、源 binding 和 Head binding 分类；证据不足为 `UNKNOWN_MEMBERSHIP_BASIS`，后期快照为 `MEMBERSHIP_RETRO`。股票价格 PIT 与板块成员 PIT 分开，成员未知的板块行保留并排除 LIVE OOS，股票行可独立保留。

定点验证：`tests/test_r8_s2_data_repairs.py`、`tests/test_r8_s3_ledger.py` 共 **19 passed**；4 个修改 Python 模块 AST 解析通过；`git diff --check` 通过；Forward 页面 JavaScript `node --check` 通过。测试临时目录及 `TMP/TEMP/TMPDIR` 使用 `G:\codex_tmp\test_temp`。未运行完整旧版测试或 GUI 扫描。

## 生产与日更安全记录

- 只读检查 `127.0.0.1:28765`：PID `48936`，仍为既有 1.1.7 包；首页 GET 200。当前接受 Head 仍是 `2026-10-13`，SHA-256 `974c60e0095de0e37e2089edca710876d25f43de604fecafd115b675745375c3`。
- 2026-10-15 12:04（北京时间）日更状态：缺口 `[2026-10-14, 2026-10-15]`，`source_ready=false`；自动日更原为开启，18:35 有自动触发；10/14 的既有自动任务两次尝试后 `QA_BLOCKED`（`SOURCE_EXECUTION_FULL_OWNER_LIFECYCLE_CONSERVATION_FAILED`），10/15 仍排队且尝试次数 0；无活动任务，Head 未变。
- 按任务卡授权，于 12:05 将日更 `auto_enabled` 暂停，设置 revision 8→9。回读确认暂停生效、无活动任务、Head/SHA 未变。这是可逆的调度设置，不是代码永久关闭。
- 恢复条件：10/14 与 10/15 一次批量采集及逐日候选验收完成，或用户明确决定停止本轮 catch-up；在此之前不恢复自动触发，以免 10/14 被单独发布。没有新增采集、回放、接受、归档、Head 发布、生产重启或打包。

## 验收矩阵阶段结果

| 编号 | 阶段结果 | 范围 |
|---|---|---|
| V-01 | PASS | 固定分支，源码在 `7f63eab3f` 并已推送；其他工作树未改动。 |
| V-02 | PASS（fixture）/ 等真实源 | 追加修订、合法状态、未接受来源、同状态重试幂等与最新分母逻辑；真实旧账本计数待双日窗口。 |
| V-03 | PASS（fixture） | 多日缺口、完整 batch gate、15:00/次日 09:30、等待源状态与 UI 字段；真实来源时钟待双日窗口。 |
| V-04 | PASS（fixture） | 独立成员源绑定的当日成员、次日反推、缺少成员源证据负例、未知成员与股票/板块身份拆分；10/14、10/15 实际源哈希待双日窗口。 |
| V-05 | WAIT | 当前 `source_ready=false`，必须在 15:00 后待两日源齐备一批抓取。 |
| V-06 | WAIT | 尚未在隔离候选 Head 运行 10/13→10/14→10/15。 |
| V-07 | WAIT | 真实证券集合及 `SZ.301660` 计数待源就绪。 |
| V-08 | WAIT | 真实 10/08 T+3、10/13 T+1、10/14 T+1 结算对账待源就绪。 |
| V-09 | WAIT | 双日隔离重试/幂等与跨日读回尚未运行。 |
| V-10 | NOT RUN（前置门未通过） | 未构建候选包；未创建 `SINGLE_PACKAGE_RECEIPT`。 |

## 下一步

状态维持 `FIXED_SOURCE_PASS_WAIT_2DAY_DATA`。15:00 到点不等于源已齐；收到/检测到正式 10/14、10/15 全套源后，使用一次 source batch，在隔离同构 PG 中先验收 10/14、再以其为前态验收 10/15，并完成 V-05–V-09。只有这些项目通过后才进入任务卡唯一候选打包步骤。生产 Head 与 28765 不由本任务切换。

暂不生成 `TWO_SESSION_20261014_15_CATCHUP.json` 或 `SINGLE_PACKAGE_RECEIPT_20261015.json`，避免写入虚构批次/包回执。

## 追加修复：成员证据与旧 `NO_QUOTE` 重试（2026-10-15）

- 阶段合同：沿用 `V4-R8-UNIFIED-REPAIR-2DAY-CATCHUP-20261015/R1` 的 Step A 源码修复门；按 `docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md` 与 `docs/upgrade/V4_R7_FORWARD_SIGNAL_SPEC_R1.md`，`AS_RECORDED` 只接受有独立冻结来源的在线成员关系，真实双日数据门维持 WAIT。
- 修复 A：`classify_membership_provenance()` 不再从 sector Owner 回填成员 hash/path。仅当 Head 存在独立 membership（或 membership_snapshot）Owner，Owner 文件通过校验，且行内成员源路径/hash 与该 Owner 一致时，才可能输出 `AS_RECORDED`。同日时间戳但只带派生 sector 产物的负例输出 `UNKNOWN_MEMBERSHIP_BASIS`。
- 修复 B：`review_legacy_no_quote()` 对相同 `DUE_SOURCE_NOT_ACCEPTED` 状态、原因、空 source digest 和 settlement 结果直接幂等跳过；当来源以后被接受，仍进入已接受来源核验与纠正路径。
- 验证：`tests/test_r8_s2_data_repairs.py`、`tests/test_r8_s3_ledger.py` **19 passed**；`git diff --check` 通过。源码提交 `161b32aee`，证据提交见本文件所在提交。此结果仅证明固定 fixture 语义；不构成 10/14、10/15 实源验收或打包放行。


## Step B 实际触发记录（2026-10-15 收盘后）

- 最新阶段结论：**`SOURCE_BATCH_READY_DERIVATION_BLOCKED`**，替代前述等待源数据的状态。不能再将“本地缺少回执”解释为上游通达信/BaoStock 未更新。
- 已真实下载通达信 10/15 官方包（552,456,022 bytes），SHA-256 `768c907a6433bc5cfc1fb0c4f6b0cf0ae25f5fe94bf86d95987418558b1acd9d`；从同一包分别冻结 10/14、10/15 的 SH/SZ 日线。BaoStock 分别为 5,225、5,226 行；14 日复用既有已验证缓存并保留早间真实时钟，15 日实时查询。不能将旧缓存声称为晚间重新抓取。
- 两日来源门均 `source_ready=true`，15 日新增 `SZ.301569` 通过现有新代码身份核验；`SZ.301660` 在两日来源集合中均保留。Core/Profile 尚未派生，不能把源集合计数写成 Core/Profile 验收计数。
- 真正触发的候选 PG 日更任务：`0b1c9e6f00b74c68b1bb2634fb7c8395`，模式 `CATCH_UP`，缺口 `[2026-10-14,2026-10-15]`，独立候选 schema `v4_jobs_64d0f9c30983a3ac`，复用原 `127.0.0.1:5432/market_research`；未创建新数据库实例。
- 任务进入 10/14 计算后最终 `QA_BLOCKED`：`RANGE_REPAIR_REQUIRED:NUMERIC_ALGORITHM_REVISION:src/workbench_analysis/operational_owner_adapter_v1.py`。R8 生命周期参数传递改动与 10/13 已接受市场修正驱动绑定不同。差异核对表明是身份传递新增，但本轮没有修改或关闭版本门，也没有自行将它声明为已准入。15 日仍排队且尝试次数 0。
- 两个 Head 均仍为 10/13；生产 Head SHA-256 保持 `974c60e0095de0e37e2089edca710876d25f43de604fecafd115b675745375c3`。本轮未启动 HTTP 服务，28765/28766 均未监听；候选调度保持关闭，临时执行/复制进程均已停止。
- 阶段矩阵：V-05 已取得双日绑定来源，但 14 日 BaoStock 使用旧缓存的真实时间明确保留；V-06 在驱动准入门阻断；V-07 仅来源集合通过；V-08、V-09 未达执行前置；V-10 未打包。详细日期级哈希、来源时钟、任务状态和源集合见 `TWO_SESSION_20261014_15_CATCHUP.json`。
- 下一阶段：完成 R8 生命周期传递改动相对于已接受市场驱动的有界候选数值准入，再重试同一隔离任务。禁止通过忽略 revision guard、伪造已接受 Head、跳过 14 日或变更生产门获得 PASS。
