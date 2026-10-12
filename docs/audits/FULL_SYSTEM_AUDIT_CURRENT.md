# 全系统代码审计当前入口

原生 Shadow/结算队列工作包已推送：代码 `e05d3268a74776e259e1117d304fad0612988a94`，证据 `6be82f16d179f1fceee02a92310414dd2ab484f1`。[20 表原生 PG、155 PASS、原 152 节点保留及逐项关闭条件](r4_r3_scope_20261011/NATIVE_SHADOW_QUEUE_PACKAGE_R1/SEAL.json) / [Drive 实际下载完整字节一致](r4_r3_scope_20261011/DRIVE_NATIVE_SHADOW_BYTE_READBACK_R1.json)。原 37／22／15 失败及首次全绿但来源 SHA 未独立校验的诊断全部无损保留；实际来源 SHA／大小／行内容负例已补，29 条持久化结算、116 个独立有理数价格路径比较为 0 差异。旧 UNKNOWN 到期记录保留，新增日历到期修订、停止后重启、两个真实 PG 连接的一胜 CAS 通过。独立首版 oracle 的 UNKNOWN 契约状态差异作为失败保留，第二版分别核对直接与 durable 全路径契约。此包只关闭隔离 native Shadow/队列及价格路径局部范围；benchmark/control 全语义、完整合法分母、全部消费者、56 类及生产授权仍 OPEN。R13 五日 Core／Profile／Sector／Market／D0-D2 均已落盘，但 Focus 总收尾及 RESULT 回执缺失，进程已不在运行，断点恢复属于未完成工程，不计通过。

R13 五日 Core 全历史独立对照已推送 `583cbcd9ac65e5f0361e18dc2b58bc222e557c85`：[完整数值与源绑定封存](r4_r3_consumers_20261011/FULL_HISTORY_EXACT_ORACLE_PACKAGE_R1/SEAL.json) / [Drive 实际下载字节一致](r4_r3_consumers_20261011/DRIVE_FULL_HISTORY_BYTE_READBACK_R1.json)。覆盖 16,696,926 条原生二进制记录、26,117 个证券日期行、10,762,706 根 bar、42,974,144 个可比较复权 OHLC 值，差异为 0；19,170 根 UNKNOWN bar 独立核对一致。旧代 80 处舍入失败原件保留，四个执行数学源 SHA 未变。本项仅关闭 R13 五日 Core 全历史价格对照；56 类消费者、后续链、全语义及完整合法分母继续 OPEN。Shadow 原生 PG 首轮 152 节点为 115 PASS / 37 FAIL / 0 ERROR，失败原件保留，仍在工程修复，生产未切换。

DB06 动态桥入口负例补证已推送 `6373cfcbaf288d0c8cb7cc5baa73974775f70c3e`：[已配置／空配置／缺失配置下 12 PASS，原 4 节点保留](r4_r3_scope_20261011/DB06_FAIL_CLOSED_PACKAGE_R3/SEAL.json) / [Drive 实际下载一致](r4_r3_scope_20261011/DRIVE_DB06_BOUNDARY_BYTE_READBACK_R1.json)。独立无 pytest、无驱动替换的实际调用同样拒绝 12 次，socket 连接及新增数据库文件均为 0；该包仅关闭 native 隔离模式的动态桥拒绝边界，不声明所有业务入口已迁移。

当前阶段历史读者适配已推送 `7d60a357cffe6db40a4465b07784f2cbe043de42`：[合并 194 PASS、源字节稳定、原 22 与 166 节点完整保留](r4_r3_scope_20261011/HISTORY_CURRENT_AUTHORITY_PACKAGE_R1/SEAL.json) / [Drive 实际下载字节一致](r4_r3_scope_20261011/DRIVE_HISTORY_AUTHORITY_BYTE_READBACK_R1.json)。旧 19 FAIL／3 PASS 原件保留；当前完整 V4-15 authority 与历史阶段归档分离，三线程历史／当前读回、错误 SHA、越界、权限过称负例通过，原接受 validator 的依赖函数 AST 未变，模块 ROOT 未改。新 V3 适配源仍为 PENDING_EXTERNAL_ACCEPTANCE，不授予业务重接受或生产切换；整个系统、全部真实消费者与全合法分母仍 OPEN。

最新完整原始运行为 4,789 节点：4,487 PASS / 201 FAIL / 98 ERROR / 3 SKIP；原 4,568 节点保留，精确一个 V3-only AST 节点仍为已记录排除，原始交集为 4,567，禁止把后续局部修复回填为本次全量已通过。运行与独立重计已无损封存于 [原始节点修复包](r4_r3_scope_20261011/NATIVE_FIXTURE_REPAIR_PACKAGE_R1/SEAL.json)，提交 `a0dae754de7f27dc49b1ffc1cbd14d0c0c616ad3`。[Drive 完整字节读回](r4_r3_scope_20261011/DRIVE_NATIVE_FIXTURE_BYTE_READBACK_R1.json)一致。后续修复中 V4_13 原有三个模块 77 节点、FEP 原有 20 节点均全部通过，节点身份集合无减少、无新增；FEP fresh 与 upgrade 分别来自真实对应的隔离 canonical 来源，旧同来源副本和早期失败全部保留。伪造生产准入的能力清单被实际拒绝，未进入采集。

历史保护元数据局部工作包已推送 `1c644a721cc706b51c4145647bf849a22d851ce1`：[166 PASS、原 162 节点完整保留、旧失败无损封存](r4_r3_scope_20261011/PROTECTED_METADATA_REPAIR_PACKAGE_R1/SEAL.json) / [Drive 实际下载字节一致](r4_r3_scope_20261011/DRIVE_PROTECTED_METADATA_BYTE_READBACK_R1.json)。该运行源字节稳定；历史阶段与读者源仅解析精确登记归档，当前权限由当前完整 authority 独立核对，不授予旧源当前业务接受。其他可达历史读者四模块实际仍有 19 FAIL / 3 PASS，当前阶段升级适配仍 OPEN，原始输出保留于 `HISTORY_REACHABLE_ORIGINAL_MATRIX_R1`。五日精确链已完成 09-28、09-29、09-30 Core，分别 5,222／5,223／5,224 个证券行、阶段 errors 为 0；尚未完成全部日期、全历史窗口 oracle 或全部真实消费者验收。总体保持 EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE，工程缺口不得归入未来交易日、成熟样本或部署授权等待门。

FEP 全字段结构补证已推送 `55637e73`：[315 SQL 字段／35 表及 47 注册特征完整清单封存](r4_r3_semantics_focus_20261011/FEP_CATALOG_FIELD_PACKAGE_R2/SEAL.json) / [Drive 字节读回](r4_r3_semantics_focus_20261011/DRIVE_FEP_FIELDS_BYTE_READBACK_R2.json)。独立 `pg_attribute` 字段身份集合与全清单相等，遗漏和伪增字段负例可检出；首次错误的零字段前缀筛选原始输出保留并判为未接受。该清单只证明结构枚举，逐字段生产者、cutoff、quality、实际消费者和数值语义门仍 OPEN，不替代整体 V4 合法分母。

2026-10-12 新增真实输入复权回归包，代码提交 `83e68911e6f4603809376684086d7471b5f00d22`：[限定范围封存](r4_r3_consumers_20261011/EXACT_CORE_REGRESSION_PACKAGE_R1/SEAL.json) / [Drive 完整字节读回](r4_r3_consumers_20261011/DRIVE_EXACT_CORE_BYTE_READBACK_R1.json)。旧五日完整历史 oracle 覆盖 10,762,706 根 bar、42,974,144 个可比较复权价格，发现 80 处一分舍入差异；原始失败保留。精确有理数候选逐项重现全部 80 处，四个 OHLC 均与独立原生输入计算一致，字面数值及负例 11 PASS。该结果仅关闭限定舍入回归；R13 五日实际消费者链及新完整历史对照仍在执行，56 类消费者、全语义、全部 PostgreSQL 入口及正式验收仍 OPEN，生产未切换。

无复制上限补齐后的 29 模块重跑保留全部 560 个原始节点，独立原始 XML 重计为 488 PASS / 72 FAIL / 0 ERROR；旧失败未删。已启动包含新增精确 Core 测试的扩展完整基线重跑，尚未得出最终计数或合法分母终审，不以局部通过代替完整工程关闭。

2026-10-12 主任务续行已推送 `3e1168f5af302d97ba20c4b88f31cedcbd49a033`：[当前 V4_13 消费者与无复制大小上限的局部封存](r4_r3_scope_20261011/CURRENT_OWNER_AND_UNLIMITED_RECOVERY_SEAL_R3.json)。原 45 项数值／溯源负例和新增 4 项当前权限负例共 49 PASS；实际 101 MiB 文件恢复、冲突文件保留测试 1 PASS。无上限输入恢复新增约 2.69 GB，所有逐文件原始校验回执封存，旧达到上限的回执保留。[Drive 新副本完整字节读回](r4_r3_scope_20261011/DRIVE_CURRENT_OWNER_BYTE_READBACK_R1.json)一致。

新扩展采集为 4,778／4,779 节点（仅精确一个 V3-only 排除）；采集不是执行或分母终审，完整合法 V4 分母仍 OPEN。真实源派生已完成五个日期的 Core 数值／OHLC 局部对照并进入 Profile/Structure；仍存在历史空 Episode 证据不足导致 UNKNOWN，该状态不得虚报已通过，也不能据此阻塞可执行算法及工程修复。真实 10-12 捕获按实际时钟及源状态判定，生产权限未变。

R3 主任务接管续行：完整诊断运行保留 4,740 个原始节点（3,866 PASS／414 FAIL／209 ERROR／251 SKIP，另有一个精确 V3-only 排除）；该运行期间存在代码更新，不是最终冻结版本认证。缺失输入恢复后的 29 模块诊断为 456 PASS／94 FAIL／10 ERROR，全部 560 节点及旧失败原件保留，不能替换完整分母。当前三个总目标仍未实现。

最新已推送局部实现 `d4a1c00bc364a153558a4fbc2cb479a55a27fd47`：[31 项完整 PG 内容校验与两交易日实际性能封存](r4_r3_integration_20261011/CAPACITY_VERIFIER_SEAL_R3.json)；首次／热访问及 1、4、8 并发完整响应 SHA 一致，独立发布的 09-30 R2 快照完整内容验证成功，峰值 RSS 2,533,408,768 字节。容量阈值未获批准，容量验收仍 OPEN。[Drive 新副本字节读回](r4_r3_integration_20261011/DRIVE_CAPACITY_BYTE_READBACK_R1.json)一致。该结果不声明全部真实消费者或 56 类通过。

Canonical 重构／元数据／权限局部 263 项通过，提交 `c2281724a5bdc727b1f8f1000948e9900ea7a5db`；逐请求 PG 校验事务复用 28 项通过，提交 `4d3f845d52dff6997ac762064b494a4e293afbac`。历史 09-30 实际生产者在隔离 PG 联合发布与 7 路 HTTP 健康读回成功，仍需完成运行消费者总体闭环；不得借此授予 FIRST_OBSERVED／PIT 或生产切换。

2026-10-11 用户明确取消我设置的 1 GiB 总量与 100 MiB 单文件冻结输入复制上限。继续 G 盘无该人为大小上限恢复、精确 SHA、源只读与已有冲突保留；此前达到复制上限的记录保持历史原件，不再作为后续工程停止理由。真实当日捕获、成熟样本与部署授权仍单列，所有可执行工程缺口仍 OPEN。

R3 B2 续行增量：[UI/传输/Shadow证据](r4_r3_integration_20261011/B2_UI_TRANSPORT_SHADOW_INCREMENT_R3.md)，提交 `b476e8de43388390892b6b01db8c4f56f42d4a02` 已推送；[Drive完整字节读回](r4_r3_integration_20261011/DRIVE_B2_INCREMENT_BYTE_READBACK_R3.json) SHA一致。48个合法局部节点通过，六路传输前后完整内容SHA一致，桌面/390浏览器及4项数据数量对照已补。旧基线失败保留，完整合法回归/全部消费者/56类及全语义门仍OPEN。Series全1,309,832行PG对照是另一个未提交增量，联合发布仍在修复，不构成总验收。

R3 续行工程检查点：[进度与未关闭门](r4_r3_integration_20261011/ENGINEERING_PROGRESS.md) / [Drive 检查点读回](r4_r3_integration_20261011/DRIVE_CHECKPOINT_READBACK.json)。实现提交 `2a7c6cb4d41822a1bed83e9abcfab11bba4deb90`，有界13项真实调度/控制与36项复权测试；合法全分母、所有消费者和全语义仍OPEN，完整基线重跑尚未绿。该检查点不替代下方R2与历史裁决。

最新用户指定复审 R2 隔离整改：[本轮报告](r4_external_repair_r2_20261011/REPAIR_REPORT.md) / [独立问题与继承处置](r4_external_repair_r2_20261011/R2_DISPOSITION.json)。206 项本轮能力重跑通过；四表/Series/Journal/Shadow 新内容身份、联合 PG CAS、五日期跨行业默认 HTTP/独立 oracle 已补证。完整合法分母、全真实消费者、容量、正式角色和生产准入继续 OPEN。总状态 EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE。

最新隔离工程：[R4 外审修复第二批](r4_external_repair_batch2_20261011/REPAIR_REPORT.md) / [有效阶段处置](r4_external_repair_batch2_20261011/BATCH2_DISPOSITION.json)。60项能力回归通过；正常authority产品HTTP、全字段差异溯源和旧出版物四表PG无损迁移已补证。正式外部验收/生产切换及全V4分母仍OPEN。

当前外审修复首批：[修复回执](r4_external_repair_20261011/REPAIR_REPORT.md) / [独立问题台账](r4_external_repair_20261011/AUDIT_ITEMS.json)。定向10/10通过；完整验收仍阻断。

当前 R4：EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE。隔离工程基线 fbd23a6ba08d0948fe7ad421d1765fe363648522；尚未完成总任务或集成在役目标分支。

- [R4 工程报告](full_system_r4_pg_only_20261011_fbd23a6b/REPAIR_REPORT_R4.md)
- [R4 有效问题视图](full_system_r4_pg_only_20261011_fbd23a6b/EFFECTIVE_AUDIT_ITEMS_R4.json)
- [R4 源版本限定](full_system_r4_pg_only_20261011_fbd23a6b/R4_SOURCE_BASELINE_QUALIFICATION.json)
- [历史 R3 报告](full_system_repair_r3_20261011_239fb9b5/REPAIR_REPORT_R3.md)
- [历史 R3 问题视图](full_system_repair_r3_20261011_239fb9b5/EFFECTIVE_AUDIT_ITEMS_R3.json)

范围 V4 / PostgreSQL-only；合法测试分母仍 OPEN，局部 PASS 不代替全量回归。历史原件保留，正式 PIT/H21/Cohort/FEP/Windows 与外部验收门禁未解除。
