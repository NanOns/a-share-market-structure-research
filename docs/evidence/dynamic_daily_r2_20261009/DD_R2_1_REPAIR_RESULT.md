# DD R2.1 继续修复记录（2026-10-09）

总状态：BLOCKED_PENDING_REMAINING_MANDATORY_GATES。没有授予外审通过。Windows 整机重启按用户指令暂不纳入。

代码版本：a8e5c2cf31ce8c9739ad6d6e225f7c224319504c；审计基线 851770b1932d95836ce76bb44fd292117958bf04。临时文件统一 G:/codex_tmp，项目/工作空间主目录 G:/codex work。

已补齐：
- R2-01：冻结旧版本与修复版本使用同一终止失败/源恢复场景；旧版不恢复，修复版创建新尝试并按序执行。实际旧 schema WAL 创建、升级和旧读取器兼容验证保留全部原历史。修复探测健康恢复和中断任务误复用。
- R2-02：实际 Bar 日期、成功目标日因子查询及零变化证明；就绪记录绑定生命周期、身份、5224 接受池、GBBQ、成员快照。10/09 冻结重放缺失/未知代码均 0。新增 V2 IO 适配绑定日收据；旧 Owner 源码字节恢复以维持已发布 Head 摘要。曾因修改该文件导致 HTTP 503，恢复后真实 HTTP 200；没有改旧日收据。
- R2-03：两日各 3 个完整板块贡献，6 个目标剔除相对收益用例；两日完整 Market 参与度贡献向量。保留 Core 字段完整窗口/来源元数据。
- R2-04：回滚写入故障后新进程恢复、持锁进程崩溃后重新获取锁、双调度进程和手工重试并发只有一个任务与执行进程。
- R2-05：244 项真实周期日历视图检查，6 类明确 FIXTURE 的 192 项状态/计数/null 检查。
- R2-06：本地轻量 ZIP 重建并在 G 盘隔离解压，CRC/载荷 SHA/独立 oracle 全部通过。

测试：68 passed，退出码 0。命令：python -m pytest -q tests/test_dd_r21_process_races.py tests/test_dynamic_daily_r21_repair.py tests/test_operational_daily_jobs_v1.py tests/test_operational_daily_executor_v1.py tests/test_operational_daily_calendar_v2.py tests/test_operational_successor_release_v1.py tests/test_operational_daily_periods_v1.py tests/test_operational_successor_control_v1.py --basetemp G:/codex_tmp/test_temp/dd_r21_g_only_adapter_v2。

离线 oracle：23296 checks，0 errors；其中周期算术/真实视图 1994 项，状态边界 192 项。只验证列出的字段，不代表全部 Owner/源或全部 Market/LOO 正确。

仍未签收：样本事件/异常量价/身份沿袭分层的完整证明；原始源到仿射复权的全链；全 cohort 前置收益率；全部 Native/LOO 状态、Market 其他轴；真实历史缺失日状态守恒；新增代码生产部署与新日实际三源门后的完整派生；本次新 ZIP 的云端替换和回读。必过门不能由 scoped PASS 顶替。

云端已有三份文件及旧回读保持历史有效，但它们不等于本次本地新包。此前累计上传 1870325 字节，本次尚未新增上传；预算不能重置。新包大小和摘要见 R2_06_OFFLINE_ACCEPTANCE.json。

DD-A01/A02/A05/A06/A07/A08 继续独立开放；Amount Native 主权威未替换。严格 PIT 与运营 Head 保持原摘要；TDX 输入只读。

下一阶段：补齐样本剩余分层/事件链、生产部署与门控复验，并在总上传预算内更新三份轻量交付及实际回读。外部验收仍需独立签发。
