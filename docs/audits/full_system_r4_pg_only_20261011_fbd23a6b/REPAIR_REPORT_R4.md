# R4 隔离工程交付记录（第一批，未完成总任务）

系统状态：EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE。
目标集成分支 codex/v4-fp14-r2-repair，冻结基线 fbd23a6ba08d0948fe7ad421d1765fe363648522。候选在 codex/r4-pg-only-20261011、G:/codex work/r4-pg-only-20261011；为保护在役源版本而隔离，尚未集成目标分支。

## 已执行与证据边界

- 原生 PG 调度、版本化历史/研究快照/series、copy-on-write journal、桌面/服务 fail-closed 与精确有理数 transport 已形成候选实现；没有切换生产。
- 真实历史 5224 股 / 2162962 行逐股规范哈希与只读 SQLite 对照零差异：R4_03_REAL_HISTORY_ORACLE.json。
- 原始调度七表迁移逐行一致：R4_02_REAL_JOB_MIGRATION.json。隔离 PG 物理停止时实际 HTTP 503，重启后持久队列恢复：R4_02_PHYSICAL_RESTART_RESULT.json。执行器进程崩溃恢复仍未证明。
- 研究快照同一冻结 producer/source 的 6337 objects、12106 aliases、50162 members 完整对照零差异：R4_04_SAME_SOURCE_ORACLE_RESULT.json。与既有 accepted snapshot 的差异保留于 R4_04_REAL_SNAPSHOT_RESULT.json，不宣称覆盖历史单位口径审计。
- 候选隔离 native 命名范围 98 PASS：R4_SCOPED_4695de28_RESULT.json；journal 后续修复 5 PASS：R4_JOURNAL_FROZEN_VERSION_JUNIT.xml。独立 FEP E1 fresh、精确冻结夹具与新增 SQL intent 记录 96 PASS：R4_SCOPED_683c04b4_RESULT.json。这些范围不可相加为全量通过。
- 865 模块仅完成逐模块源码审阅（原 included245 / excluded620），原4568节点逐节点保留。合法分母仍 null；不能将 AST 静态候选当成实际运行可达证明。
- 治理扫描优化在合成反例和4真实文件下输出一致，完整容量/性能门仍 OPEN。
- 10171 保护绑定读回：10169 字节一致；2源码初始基线在早期编辑之后采集，恢复原基线后不同。详见 R4_SOURCE_BASELINE_QUALIFICATION.json 与独立 AR4-E01。保护结果必须带此限定，未证明完整 TDX 清单或生产 PG 全库身份。

## 阶段门与下一步

R4-00/01 IN_PROGRESS：动态入口、完整权限条件与生产加载哈希不足，双清单及 DB 能力矩阵待正式确认。
R4-02 ENGINEERING_PARTIAL：checkpoint/crash、多worker、accepted-T0 no-redispatch 等真实闭环待补。
R4-03 ENGINEERING_PARTIAL：五个 T0 各自冻结源完整 PG 对照通过；HTTP/browser、性能门待补。
R4-04 ENGINEERING_PARTIAL：同源完整 PG 快照对照通过；联合 CAS、失败回滚、正式候选发布待补。
R4-05 ENGINEERING_PARTIAL：PG series/journal 已实现；实际全消费者仍待证明。
R4-06 IN_PROGRESS：局部 PG/FEP 原始日志与连接意图可审计；合法全量 clean-slate 与全部节点处置未完成。
R4-07 IN_PROGRESS：R3 已修事项定位更新已登记；独立 HTTP/DOM、五日语义、生产加载分别待复审。
R4-08 ENGINEERING_PARTIAL：exact transport 已实现；56类调用者、rank/Core/PIT影响待补。
R4-09 ENGINEERING_PARTIAL：扫描语义对照通过；完整治理扫描及预算待补。
R4-10 IN_PROGRESS：设计/字段全分母、producer/source/time/quality/API/UI、正式研究主链与独立反例待逐项闭合。

后继真实交易日、H21/PIT/OOS、Formal Grant、Windows 实体安装与外部签收各自保留门禁，不影响其它工程继续。

## 版本和原始证据

新 scoped 结果绑定实际脏树逐文件字节清单 R4_SOURCE_TREE_*.json。早期 source_SHA=fbd 只表示 Git 基线；没有实际执行树绑定的历史回执不补造证据。所有失败 JUnit/log 原件保留。SQL intent 只记操作/关系标记/查询摘要，不存参数或 raw payload。

Git 提交/push 仅归档此工程批次，不授权生产变更或自动进入未通过的后续阶段。未声明 R4 总任务完成。

## 五日期 HTTP 增量

R4_03_CHART_HTTP_RESULT_01.json：实际产品 handler/BFF/PG reader 的30请求中，14 READY、16按冻结Owner缺口明确 SOURCE_INCOMPLETE；不是30个完整周期Owner通过。最新日期6种 RAW/QFQ × D/W/M 与独立冻结SQLite mode=ro图表数值零差异。错误token409、篡改非PG authority400，所有隔离响应 production_accepted=false。缺失周期Owner的原迭代空值崩溃修复，原失败日志保留。

99个命名native测试零FAIL/ERROR/SKIP：R4_SCOPED_01d4c10b_RESULT.json。此分母包含后续journal反例，不能覆盖原4568或合法全量分母。HTTP工程运行中的额外class默认属性修改单列为运行时源绑定限制；结果的源树是证据发射时清单，下一次执行使用提交后稳定代码验证。

工程包（398399fa）已Drive归档，文件ID 1rAuHeDGY3jWrL6xOACf45hrYmX9sRk7z；metadata名称/3241285bytes/父目录匹配。仅局部工程包，不等于全系统验收。

## 稳定代码复验与纯计算依赖增量

提交 c0d186283dad45b09706253d8bdf67147be25ec8 后，实际 HTTP 再次30请求符合预期、最新6组合零差异、409/400负例通过，结果 R4_03_CHART_HTTP_RESULT.json。被执行的 handler/BFF/helper 文件没有再修改；新增审计脚本使整体工作树不洁，因此回执未虚填 source_SHA。

R4_DYNAMIC_DB_EVIDENCE_R1.json 绑定命名范围/FEP/真实HTTP连接栈与 SQL intent；原4568中仅163个节点在所选两份JUnit有精确对应，不改变合法分母，也不称163个节点完成全部合同。连接栈深度有限，仍非完整入口/权限/UI动态图。

DB-06：V4 rank producer 现在引用独立纯排名模块，函数 AST 与冻结 helper 完全相同；独立子进程禁止 legacy builder 和 workbench_db 导入仍执行正确。原相同比较/并列/不稳定业务节点保留，3 PASS，见 R4_DB06_PURE_RANK_RESULT.json。仅该函数依赖闭合，未排除整个旧研究仓库。

## 浏览器、进程故障与最终保护读回增量

R4_03_BROWSER_RESULT.json：浦发银行 SH.600000 的五日 DOM 截止日期正确，最新日 RAW/周/月切换分别呈现正确末根与 CLOSED_ONLY_READY / AS_OF_PARTIAL_READY；Sep30 缺失 period owner 明确报错。第一轮中断未持久连接日志，只作为 DOM 证据。第二轮 latest/Sep30 有逐请求落盘 PG intents；显式隔离工程标识、production_accepted=false、只读预览禁止所有写方法，源写护栏无拒绝事件（即未发生源写尝试）。临时页面与55891预览进程均已关闭。

R4_02_PROCESS_CRASH_RESULT.json：只强制终止 owned worker PID34092；PG checkpoint字节化读回保持一致，竞争worker执行器零调用且拒绝锁占用，重启执行唯一未完成fixture日期，旧PUBLISHED fixture保持。仅工程executor fixture，不宣称真实源流水线/CAS checkpoint复用、正式accepted T0重发验证完成。

R4_SOURCE_WRITE_GUARD_RESULT.json：独立G fixture下四种实际源写操作在改动前拒绝、源文件字节不变；异常为非业务BaseException。过程内保护原工作区与D:/new_tdx，不代替完整配置根清单或外部子进程保护。

最终再次读取10171保护绑定仍10169一致/2已解释源码基线差异，R4_PROTECTED_AFTER.json与R4_SOURCE_BASELINE_QUALIFICATION.json必须联读。远端目标分支重新fetch仍fbd23a6ba08d0948fe7ad421d1765fe363648522，生产28765仍PID22956。

R4-00_SCOPE_GATE.json 明确 NOT_VERIFIABLE；当前静态和有限动态证据不足以闭合整个入口/权限/UI/worker图和合法分母，未自签scope冻结完成或系统全PASS。各开放工程项仍在独立台账，下一优先级为真实source executor/candidate闭环、jointCAS/rollback与逐合同合法回归。
