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
| V-02 | PASS（fixture）/ 等真实源 | 追加修订、合法状态、未接受来源、幂等与最新分母逻辑；真实旧账本计数待双日窗口。 |
| V-03 | PASS（fixture） | 多日缺口、完整 batch gate、15:00/次日 09:30、等待源状态与 UI 字段；真实来源时钟待双日窗口。 |
| V-04 | PASS（fixture） | 当日成员、次日反推、未知成员与股票/板块身份拆分；10/14、10/15 实际源哈希待双日窗口。 |
| V-05 | WAIT | 当前 `source_ready=false`，必须在 15:00 后待两日源齐备一批抓取。 |
| V-06 | WAIT | 尚未在隔离候选 Head 运行 10/13→10/14→10/15。 |
| V-07 | WAIT | 真实证券集合及 `SZ.301660` 计数待源就绪。 |
| V-08 | WAIT | 真实 10/08 T+3、10/13 T+1、10/14 T+1 结算对账待源就绪。 |
| V-09 | WAIT | 双日隔离重试/幂等与跨日读回尚未运行。 |
| V-10 | NOT RUN（前置门未通过） | 未构建候选包；未创建 `SINGLE_PACKAGE_RECEIPT`。 |

## 下一步

状态维持 `FIXED_SOURCE_PASS_WAIT_2DAY_DATA`。15:00 到点不等于源已齐；收到/检测到正式 10/14、10/15 全套源后，使用一次 source batch，在隔离同构 PG 中先验收 10/14、再以其为前态验收 10/15，并完成 V-05–V-09。只有这些项目通过后才进入任务卡唯一候选打包步骤。生产 Head 与 28765 不由本任务切换。

暂不生成 `TWO_SESSION_20261014_15_CATCHUP.json` 或 `SINGLE_PACKAGE_RECEIPT_20261015.json`，避免写入虚构批次/包回执。