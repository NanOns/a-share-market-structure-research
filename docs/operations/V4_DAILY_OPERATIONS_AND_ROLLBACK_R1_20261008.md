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
