# V4 日常运营与应急回滚 R1

当前只具备已接入的真实研究模块范围；完整产品发布结果 BLOCKED。运行地址 http://127.0.0.1:28765/，显示已处理截至 2026-09-30，不能冒充当日行情或收益验证结论。

## 启动与状态

在项目根用 `python -B run_workbench_service.py --v4-default --host 127.0.0.1 --port 28765` 启动。OPEN_RESEARCH_WORKBENCH.cmd 与 OPEN_UNIFIED_WORKBENCH.cmd 均调用 START_WORKBENCH_TRAY.cmd，既有默认 `/`、`/v4` 与研究首页同一六入口壳。`/v4/shadow` 是独立诊断，`/v3` 只有数据库已退役的历史通知，不能当可用旧数据库恢复。启动器既有行为不代表完整产品通过。

检查 `/api/operations/status`、`/api/v4/context`，核对真实 release_id、context_token、已接受日期与数据更新时间。页面刷新继续读取当前稳定指针。单域错误应先查对应源/合同，不扩全站 UNKNOWN 或删除已成功产物。

## 每交易日处理

1. 检查官方接受交易日历与下一已完成输入。TDX 根包括 D:/new_tdx 始终只读，不复制、修补或删除根内文件。
2. 在项目根运行 `python -B scripts/run_fp02_research_snapshot.py --daily`。没有新增已核验输入，本次实测 NO_NEW_COMPLETED_SESSION、source_requests=0、指针不变。
3. 真正新增已核验输入由现有 DM01 链处理，原有 owner 合同控制；适配器必须绑定同日 head、版本和来源。各域增量、Focus 写入、Forward 结算只能按实际准入执行，未准入能力不因这份手册自动启用。
4. 读 runtime/research_daily/DAILY_LATEST.json 或 FAILED_RECEIPT.json，核对接受日期、发布状态和指针保留；失败时仍用上一成功版本。禁止把“pipeline exit=0”当全产品验收。
5. 每日独立更新债务：真实 PIT 首获、历史成员、Focus 路径/旧历史、消息源、样本成熟与统计证据。未成熟样本保持 PENDING/RIGHT_CENSORED，不生成胜率或概率断言。

新增真实日全域增量、消费链和 UI+read 联合回滚尚未完成现场验收，是 QA13-08/FP14 欠项；不以合成新日填补。当前 Focus 自动写入仍关闭。

## 应急回滚

对当前**同一 UI 版本下的研究快照**，先保留当前指针和候选/前驱 manifest 摘要，再使用既有 CAS 回滚；它不撤销或删除历史样本及 Episode/Outcome 文件。

```powershell
$expectedResearchAuthority = (Get-FileHash -LiteralPath 'config/v4_research_snapshot_authority_v1.json' -Algorithm SHA256).Hash.ToLowerInvariant()
python -B scripts/run_fp02_research_snapshot.py --rollback $expectedResearchAuthority
```

过期摘要必须拒绝；发生冲突重新读取当前状态，不盲目覆盖。回滚后读取 context、真实样本和各域日期/版本，并做六入口浏览器 smoke。若 UI 也发生版本变更，以上命令不是完整产品联合回滚；必须使用以后经过准入的同一原子 UI+read 发布包，当前未启用该执行器。

隔离演练命令：`python -B scripts/run_fp14_release_readiness.py --rehearse-rollback`。它复制两份真实历史 manifest、数据库和必要序列到 runtime/fp14_rehearsal，验证前驱回滚、精确恢复、过期 CAS 拒绝，绝不切换在线权威。

候选检查：`python -B scripts/run_fp14_release_readiness.py`，本次退出码 2，唯一结果 BLOCKED；此命令只准备清单，不具有激活能力。禁止手动把全产品标志改为 true 绕过 FP13。

## 外审待办

独立核对 FP13 原始 DOM/截图、owner/raw 数字与 HEAD/source hash；接通 Edge 重跑两尺寸、真正离线与新日/回滚现场链；逐项关闭 docs/audits/FP13_FULL_PRODUCT_OPEN_ITEMS_20261008.md。Git 推送是归档，不是外部验收。

## 2026-10-12 断档日全流程排障记录（2026-10-20）

本次按补跑目标日 2026-10-12 检查代码、PostgreSQL、运行配置与数据依赖，并实际执行至来源采集阶段。结论：**全流程未通过，不能发布 2026-10-12**。没有切换正式 Head、启动/切换 28765 或写入业务发布记录。

### 实际执行与停止点

- 使用现有 `market_research` PostgreSQL 与 `v4` schema。10-12 的 BaoStock 当日运行验收、TDX 目标日行情及来源冻结文件已重新采集/生成；来源冻结位于 `data/v4/dynamic_daily_sources/daily_freezes/2026-10-12/`。采集发生在 2026-10-20，记录为晚采集（`AS_RECORDED=false`、`PIT_ELIGIBLE=false`），只可作为普通研究来源，不能声称 10-12 当时已知。
- 执行在来源门禁读取已接受日期 2026-10-09 的 owner 时停止：缺少 `data/v4/dynamic_daily_owners/2026-10-09/6c04ca70243fb34e33adef9e472fa229fab57aa8968a1b93db70d72105021917/sources/2026-10-09/lifecycle.json`。HEAD 声明的 SHA-256 为 `3df8cb50dce3771db1b8605cb8aeabadb0076eebcd05d6eb7454ae260155e9cd`。因此未完成来源就绪回执、10-12 owner 派生、独立读回、候选验证或发布 CAS；不得把采集成功当成日更成功。
- 当时 `V4_OPERATIONAL_RESEARCH_HEAD.json` 仍指向 2026-10-09，引用 137 个对象，其中 30 个对象缺失，另有 8 个算法源码绑定摘要与当前源码不符；10-09 引用的 20 个 owner 文件全部缺失。10-08 留存的 owner/候选属于旧合同，且来源注册缺少现行 generation，不能直接冒充 10-09 前态或 10-12 候选。
- PG 连接目标与旧入口配置名不一致：项目已有 `WORKBENCH_PG_DSN`，原生入口只查 `V4_NATIVE_PG_DSN`。现代码改为接受两个进程环境变量名，仍不从文件回退；日常任务也改为映射至 `v4` 中已存在的 `jobs_*_r1` 表，并以只读方式检查表，不再按项目根哈希创建业务 schema/DDL。此次只读状态查询成功；由于上游 owner 缺失，没有对任务状态或业务表执行写入。
- 原执行器在来源门禁抛出的 `FileNotFoundError` 会将关键路径吞成通用来源错误。本次增加了受限路径/错误类型诊断字段，便于后续定位；不改变原有重试与发布状态规则。
- PG 中现有 10-12 历史任务记录显示：旧运行曾完成来源冻结，然后在同一缺失的 10-09 lifecycle 依赖处失败并取消。PG 的调度自动开关为关闭；当前规划状态落后到 10-09。另有 10-13 的旧发布记录，但与当前文件 Head 不一致，不能用来证明当前工作区可从 10-13 连续恢复。
- 当前未发现 28765/28766 监听；本次未启动服务。`V4_DATA_ACCEPTED_HEAD.json` 另有一条 `V4_STAGE_ACCEPTED_HEAD.json` 摘要不匹配，需在对应读路径核验其实际影响，不能据此篡改指针。

### 后续恢复条件

先从可信来源恢复并核验 HEAD 所引用的 10-09 lifecycle 原字节及对应 owner 集合，或按既有合同完整重建 10-09 的有效前态、来源注册与算法绑定；随后重新验证当前 HEAD 所有引用和源码摘要。完成前不得跳过来源门禁、借用 10-08 旧合同产物、手改 HEAD 或发布 10-12。恢复后从 10-12 重跑，并逐项取得来源就绪、owner 结果、独立数据库读回与发布绑定证据。当前采集产物及请求账本作为本次真实运行记录保留。

## 2026-10-20 前态恢复复核

- 按原 path、bytes、SHA-256 从 `repository_consolidation_20261015/production_runtime_20261012` 恢复 28 个缺失的唯一数据对象和 8 个 HEAD 绑定源码原件；HEAD 的 137 个 path 字段对应 122 个唯一路径，现均精确匹配。HEAD 字节未改，SHA-256=`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`，仍接受至 2026-10-09。
- exact daily policy 的 660 个引用中，另从同一归档恢复 36 个摘要/字节不符对象及 1 个缺失策略归档。候选模式的 66 个算法绑定和 604 个组件绑定校验通过；完整模式仍被 `EXACT_V2_LOADED_ALGORITHM_VERSION_MISMATCH` 阻断，当前加载的 `r43_owner_replay` 与该策略版本不一致。
- 2026-10-12 冻结来源复核为 `SOURCE_READY`。冻结 SHA=`425b1418ba8e646e755e38b6555ef1c1aef8bcc6d660a270547567b3b01c558b`，观察时间仍为 `2026-10-20T10:19:45.760110+08:00`，`AS_RECORDED=false`、`PIT_ELIGIBLE=false`。
- 候选链在 Owner 开始前因恢复的 10-09 Owner `prepare` 与当前 ready-owner adapter 接口不兼容（不支持 `candidate_only_exact`）停止；未生成 10-12 Owner、独立读回或候选，未切换 Head。下一步需先按当前合同解决并绑定该运行时代码版本，再重跑 Owner→计算→独立读回→候选验证。
- PG DSN 别名、9 张 `v4.jobs_*_r1` 表接线已通过只读构造检查；真实路径错误诊断代码存在。针对执行器、日历和后端合同的定向回归为 16 passed。以上结果不构成 10-12 发布验收。
