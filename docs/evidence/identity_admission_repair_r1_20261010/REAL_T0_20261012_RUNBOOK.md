# 10/12 实际 T0 现场执行手册

当前唯一结论 WAIT_REAL_T0_WITH_IDENTIFIED_BLOCKER。预计交易日须以正式日历确认；周末不执行真实采集或改时钟。已有实际调度时点为北京时间 18:35、19:05、19:35、20:05、20:35、21:05、22:05。

1. 在 G:/codex work/大A交易 设 TMP/TEMP/TMPDIR=G:/codex_tmp、PYTHONDONTWRITEBYTECODE=1；fetch/readback 远端，确认目标日期、Phase0 FULL_PASS 和两个受保护 Head SHA。不得假称本轮源码已加载到生产。
2. 按已授权只读调度获取当日原始 roster/BaoStock 与 TDX 包/GBBQ/Member 原件，保存请求、接收、first-available 和原始 SHA；确认 actual provider 日期/active 覆盖/数值。来源异常按提供方等待，正常但旧池变化记录 WAIT_DATED_IDENTITY_AUTHORITY，保留 last-good。
3. 对真实已有官方 Listing/Delisting/改代码事件调用 dated_identity_candidate_v1.build(root,sources=五份 exact refs,parent_head=旧 accepted Head ref,candidate_directory='docs/evidence/实际日期_identity_candidate',cutoff=实际带时区时间)。先核对源 JSON 合同，缺字段保留 UNKNOWN/SOURCE_GAPS。admission_candidate 目前应返回 NOT_ADMITTED；不把合成 HMAC 当真实授权。
4. 独立审查方需先部署并验收真实 issuer/capability/revocation 服务及 exact source/Head-CAS 合同；另行获得改真实准入源/加载或重启生产/Writer Grant 的明确范围授权。满足前不得调用生产发布，真实服务缺失保持精准阻断。
5. State/Member/Model/Episode/Benchmark 按 STATE_REAL_SOURCE_REQUIREMENTS 核查，首次实际捕获必须当天事实。合法 Genesis 冻结成员、AST、价格与 due-plan，后续按真实日历和 settlement Owner 区分 PENDING/UNKNOWN/COMPLETE。缺一个域不停止其他合法只读研究。
6. 实际发布另行授权后执行两 Head CAS/重试/回读失败回滚现场 QA，留 before/after、原件 SHA、唯一状态与独立验收。提交并 push code/evidence，Drive 原始字节回读。Push 不构成外部验收。

工程可运行验证命令见本轮报告；以上生产发布步骤的必要授权和真实服务均未由本任务卡授予，不能现在执行。
