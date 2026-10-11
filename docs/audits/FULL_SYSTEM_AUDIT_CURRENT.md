# 全系统代码审计当前入口

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
