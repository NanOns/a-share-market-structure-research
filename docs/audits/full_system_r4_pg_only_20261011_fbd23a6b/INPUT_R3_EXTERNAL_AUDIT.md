# 大A V4｜全系统代码审计 R3 独立外部复核 R1

> 版本：R1 / 2026-10-11（北京时间）  
> 文件性质：独立外部审计、问题状态处置及下一轮执行依据；不是生产变更许可  
> 目标仓库：`NanOns/a-share-market-structure-research`  
> 目标分支：`codex/v4-fp14-r2-repair`  
> **冻结远端 HEAD**：`fbd23a6ba08d0948fe7ad421d1765fe363648522`  
> 本轮修复入场基线：`239fb9b545ac25305af02a645a77d82246cbb71a`  
> 当前统一入口：`docs/audits/FULL_SYSTEM_AUDIT_CURRENT.md`  
> 主合同：V4.2.2 REV4 / FEP R2 与当前生效 V4 阶段合同；本轮用户限定 **V4 / PostgreSQL-only**  
> **唯一全系统总状态：`EXTERNAL_ACCEPTANCE_BLOCKED` / `AUDIT_INCOMPLETE`**。部分 A 项为 `SCOPED_ENGINEERING_RECHECK_SUPPORTED`，不得外推成正式生产可用、已加载或阶段全通过。

## 0. 方法、来源和独立性边界

1. 先读已归档 Drive 的全系统审计总任务书和上轮 R2 独立复审，再核对 GitHub 实际最新 HEAD、七个增量提交与 R3 审计统一入口。Drive 已知项目任务文件夹在本轮检查时尚未显示 Codex 的 R3 新报告，R3 的代码与证据从 GitHub 精确版本读取。
2. 比对本轮修复源码：`core_product_bff_r1.py`、`replay.js`、`fep_engineering_storage.py`、`fep_e2/registry.py`、`fep_e3/protocol.py`、`tdx_adjustment_v0_3.py`、`full_loo_v3_3.py`、`operational_daily_jobs_v1.py`、`scan_no_symbol_specific_runtime_logic.py`，及 R3 合同、回归汇总、反例、问题总账。
3. 独立按精确分数计算 SH.688553 / 2025-04-14 open：按先后两次有效除权事件进行逆序仿射复合，得 `a=25/37`、`b=-663/1480`，原价 `15.13` 产生 `391/40=9.775`，两位十进制 HALF_UP 为 **9.78**，与 R2/R3 数值反例吻合；不是重跑全股测试。
4. **限制**：没有用户本机 G 盘全部临时数据和完整行情原件、未连接 28765 生产进程、没有直接执行 4,568 个本机用例、没有物理安装/重启/并发生产切换。对于百万级比较、浏览器及本机 PostgreSQL 回执，作的是源码/收据/时间来源/声称边界交叉核查，不冒充独立重新执行。
5. 本轮仅审计，无业务代码写入、无 TDX、accepted/strict/operational Head、生产数据库、模型/权限 Grant 改动。

## 1. 总裁决与阶段结果

| 工作包 | 本轮交付 | 外部复核 | 未关闭边界 |
|---|---|---|---|
| A1 / FA-001 | 事件优先级使用 `setdefault` 按升序留第一；1,956 组合、5 日真实只读回放 | **PASS_SCOPED_CODE_AND_EVIDENCE** | 生产 PID 未加载新代码；真实日无多类型重叠反例 |
| A2 / FA-005 | `engineering_directory` 解析后的 allowlist；E3 kind 单段 token 检查；18 项最终测试 | **PASS_SCOPED_CODE_AND_EVIDENCE** | junction 已测，Windows symlink 创建权限限制保留；生产 E2/E3 不授权 |
| A3 / FA-013/014 | 比较使用 `resolve_dated_object`；按 stock/sector 分流 RPS；4 mode DOM 与 5 日 HTTP | **PASS_SCOPED_CODE_AND_EVIDENCE** | 测试为隔离新代码，非旧生产进程已经升级 |
| A4 / FA-016 | opt-in v0.3 `Fraction` 精确复合和 cents HALF_UP，候选全股核查 | **PASS_SCOPED_NUMERIC_CANDIDATE** | 56 类消费者/transport/正式资格/旧 Head 均未升级；见 §2 |
| A5 / FA-017 | LOO candidate02 在全部成员被剔除后不再盲调下层 `build_sector_current`，新增日期检查 | **PASS_SCOPED_CANDIDATE** | 非正式 V4 LOO 许可；仅候选域 |
| A6 / FA-004 | 同一 Head 的性能/并发/内存测量已提供 | **MEASUREMENT_PASS; CAPACITY_GATE_OPEN** | 无已批准阈值，未优化且单机扩并发无吞吐提升 |
| B1 / FA-009 | 84 版本、674 注册记录、298 字段名、37,264 schema 原子 | **PARTIAL** | 词法/注册不等于合法全需求分母及逐字段语义验证 |
| B2 / FA-002/003/011 | FIRST 真实生产函数120个排列、ANY 合成集合；右截尾边界 | **PARTIAL** | 正式 target 未启用、Cohort/PIT/prior/D0D1D2 均缺证 |
| B3 / FA-006 | 245 模块、4,568 节点的 V4-only 回归 | **FAIL_FULL_REGRESSION** | 237 FAIL / 209 ERROR / 312 SKIP，不得称 PASS |
| B4 / FA-012 | 旧日 Amount 表示与因子回执复用 | **PASS_SCOPED_ONLY** | 378 板块 H21 无合法 20 日 PIT 输入，不能消费 |
| FA-018 / FA-019 | 现行 V4 SQLite 日更调度/历史图表索引 | **OPEN_CONFIRMED_BACKEND_DEVIATIONS** | PostgreSQL-only 方案、无损转换及现场生产准入未完成 |
| FA-020 | 治理扫描计行复杂度反例 | **OPEN_CONFIRMED_COST_PROBLEM** | 尚未修复且不能降低原硬门 |

总状态 **BLOCKED**。R3 工程证据不提供正式外部全模块验收。当前生产进程仍登记启动旧 SHA `be2a3d6d...` / PID 22956；R3 已修代码是否在真实在役进程完整加载不成立。

## 2. FA-016 精确复权：修复方向正确，但升级不能简化为换文件

### 2.1 已核实的独立数学机制

`tdx_adjustment_v0_3.py` 使用 `Fraction(Decimal)` 携带有理数 `exact_qfq_mul/exact_qfq_add`、按有效事件逆序复合并执行整数 cents HALF_UP。相比旧 v0.2 中有限精度 Decimal 系数乘加，此设计能避免精确 0.005 边界被近似误差压向下方。7 证券、16 OHLC 反例及正负 tie/多事件专项测试有对应回执。

R3 证据记录：5,224 股票、2,162,962 个原生日线位置、8,636,512 个可用 QFQ 价格单元，候选与精确有理数 oracle 零不一致。此为 **Codex 本地计算回执**，不是外部重复执行的结果。

### 2.2 已确认的历史影响

- 16 个旧 QFQ 价格单元发生 0.01 元订正；7 证券的 2,547 个证券日期、共 99,333 次 Core 字段比较中，**1,081 个历史字段结果改变**，影响 28 个字段族。
- 历史候选横截面 16 个收益日期窗口内，RPS 敏感性记录 **845 行排名变化**。该分母是当前成员重构及端点合法样本，**非历史 PIT 股票全集**。
- 五个现行冻结运营 T0 的这 7 只股票短窗口 Core 未发现变化；此结果不得推断其余历史 Structure/D0/D1/D2/Focus/Forward 与回测无影响。
- 新候选仍未加载正式生产；老 `tdx_adjustment.py` 的接受 SHA 被保留，不允许原地覆盖 Owner。

### 2.3 重要的未关闭代码边界

`AdjustmentFactor.qfq_price` 对 `exact_qfq_mul` 缺失的情形，会降级为 `Fraction(self.qfq_mul)`；如果来源仅持有截断后的 Decimal 系数，这个变换只是**对近似小数精确化**，并不能恢复原始事件有理数身份。R3 将 56 类消费者登记为尚未升级，说明目前尚未证明所有调用都携带 `exact_*` 参与运算。

**必须补充合同级验收**：v0.3 被选用时，正式生产消费者应获得精确系数及其来源 digest，或得到明确 `EXACT_FACTOR_UNAVAILABLE` 并 fail-closed；不能静默使用旧小数传输而仍标记为“精确 v0.3”。须完成全消费者的版本/输出/质量/差异矩阵，冻结候选、独立重放、明确新旧命名空间和可回滚升级。

## 3. A1 / A2 / A3 / A5 独立代码核查

### A1：首页优先级

`core_product_bff_r1.py` 的 `HOME_EVENT_PRIORITY` 以 `INVALIDATED=0` 开始；`prioritize_home_changes` 排序后使用 `selected.setdefault(entity_id,row)` 留第一条。这正确修复了 R2 用字典推导式留最后一条的 P1。风险数及净信息应从同一结果派生。工程回归有证据；正式运行仍待部署核对。

### A2：存储根边界

E2/E3 改用统一 `engineering_directory`，对 `..` 显式拒绝，`Path.resolve()` 后用 `.is_relative_to(root)` 约束，同时限制 E3 `kind` 匹配 `[A-Za-z0-9_-]+`，防止路径构造注入。单纯 `G:/` 整盘未被放开，旧 E/F 路径仍拒绝。真实 junction 场景支持本轮判定；不能声称因权限失败的 Windows symlink 组合已经亲自跑通。

### A3：比较身份及字段

比较入口通过 `resolve_dated_object()` 在 as_of 的已发布对象中匹配 identity/symbol/search_aliases，歧义拒绝；DOM 根据 `mode` 选择股票 `rps5/20` 与板块 `sector_rs5/20`。源码与 R3 HTTP/DOM 回执一致。页面明确标示历史比较为重构非 PIT。另需持续注意：日期对象别名属于重构研究语义，不自动证明历史某 T0 当时的原始别名首获。

### A5：空集合 LOO

`recompute_full_current_loo()` 先确保共同单个 trade_date；当 market 剔除后为空受控拒绝，而仅 sector 剔除后为空时生成空 DataFrame，逐相关板块返回 `SECTOR_EMPTY_AFTER_EXCLUSION`、支持值 UNKNOWN。符合此候选代码缺陷的最小闭环；正式 D2/PIT/LOO 仍未自动解锁。

## 4. B3 大回归：必须阻断“全功能完成”结论

R3 给出受控 V4 / PostgreSQL-only 测试清单，245 模块、4,568 项，统计守恒：

| PASS | FAIL | ERROR | SKIP | 总量 |
|---:|---:|---:|---:|---:|
| 3,810 | 237 | 209 | 312 | 4,568 |

失败+错误合计 446；分流：SQLite 意图被拒 97、缺精确夹具143、旧 PG 夹具身份49、未解析断言/运行时73、历史 V3 兼容2、文件权限1、隔离 PG 初始化超时81，总和446。

后续对598节点定向复验结果 `435 PASS / 98 FAIL / 64 ERROR / 1 SKIP`，是**单独重测分母**，绝不能把它与原 4,568 数字相减或将全量结论修改为绿色。PG 先前312项跳过中，309项已有额外测试，但这同样不等于全库重新验收。

**附加审计风险 AR3-E03**：首次完整回归的数据库护栏抛 `ValueError`，可能误满足原业务负例断言；新隔离插件将非 PG 连接改为继承 `BaseException` 的 `V4NonPostgresBackendError`，在配置连接的2个反例上证明不能误满足 `ValueError`。因此原 3,810 PASS 是执行结果，不能一概认定为业务语义 PASS。**全量 clean rerun 必须使用修正后的护栏与精确 V4 测试分母**，且所有真实 SQLite 入口应进入架构缺口、而非简单剔除测试。

### 审计证据治理新增项 AR3-E04（P2）

R3 `EFFECTIVE_AUDIT_ITEMS_R3.json` 虽已修正 FA-012 错误来源，但若干 `effective_location` 残留旧代码行号，例如：
- FA-001 指向 `core_product_bff_r1.py:312-313`；真正优先级函数位于新源码约第 17–24 行，入口使用处另在首页分支。
- FA-013 指向 `core_product_bff_r1.py:352-355`；新比较入口在约第 365–374 行。

该项不是新的交易算法错误，却破坏“有效问题总账直接定位当前冻结代码”的承诺。建议 R4 以 **`symbol/function + exact SHA + verified line range`** 更新 effective 位置，原 R1/R2 历史定位另字段保留，不改原件。

## 5. PostgreSQL-only：两条确证的现行违约链路

**FA-018 / 调度持久化**：`operational_daily_jobs_v1.py:31` 创建 `runtime/dynamic_daily/jobs.sqlite3`，`:146–149` 直接 `sqlite3.connect()` 并设置 WAL/FULL；真实启动登记的调度模块源码 SHA 与新读源码相同。它保存调度策略、任务、重试、作业事件与状态。此为现行 V4 后端依赖，不是旧 V3 测试扩张。

**FA-019 / 历史图表**：`core_product_bff_r1.py:207–209` 连接 manifest 绑定的 `history.sqlite?mode=ro`，用于 `/api/v4/stocks/{entity}/chart`；已登记真实冻结索引大小 426,196,992 字节。该入口独立于调度 SQLite，也不是 PostgreSQL 市场主表。

应分成两个完全独立的 PG 迁移合同：调度的状态迁移/幂等/CAS/进程重启和图表的不可变历史索引/复权/日期/分页/速度/源SHA。**当前运行态的 SQLite 文件和旧 Head 必须原字节保护；没有独立数据差异与恢复准入前，不允许原地迁移。** `production_v4.py` 中其他 SQLite snapshot 的默认现行可达性尚需补证，不能凭源码存在就声称已在主入口使用。

## 6. 性能：不只是前端慢

A6 记录首页响应 6,313,877 B（约 6.02 MiB），两次首次首页读取约 12.73/9.80 秒。并发客户端从1提升到4、8时总吞吐约2.526→2.414→2.424 req/s，P95约1.01→2.98→4.44秒；采样 RSS 峰值约4.55 GB。

现有 BFF 会修改共享 snapshot，不能直接拆全局锁，否则多日期、并发读写时可能混淆 Head/T0。建议优先做**按请求冻结不可变快照**与首页 payload 投影/分页/缓存，再按具体用户工作负载确认响应/吞吐/内存阈值。现无权威数值门，不得自造合格标准。

FA-020 治理扫描器在扫描非 Python 文本时按每个命中重复 `text.count('\n',0,pos)`，最坏随文本长度与命中次数相乘。源码确实如此；应建立换行位置索引或单次顺序扫描，并做位置/类别/Unicode/CRLF 完整对照。该缺陷属于 QA 扫描性能，不能与首页吞吐混成一个指标，更不能为了速度关闭硬门。

## 7. 尚未完成且不应因 R3 推进而改变的正式门

- **FA-009**：全设计原子需求/全部 §87A 字段族的合法分母、公式/阈值/质量/时点/producer/consumer/UI 语义审计未闭环。84版本、674条注册及37,264个 schema 原子只是范围内索引；39模块继续 PARTIAL。
- **FA-002/003**：真正的历史先验 PIT、D0/D1/D2合法 prior、正式 Radar/完整 Validation Cohort/Forward 源及权限没有获得闭环证据。重构板块成员关系不能替代历史成员当时已知性。
- **FA-011**：FIRST/ANY 实际标签目标仍 `REGISTERED_NOT_ENABLED`，成熟样本、OOS、正式模型和 Priority V2 继续关闭；FIRST 的构造测试不能代替真实分母。
- **FA-012**：Amount A 原生/辅助源和股票窗口的有限数值可复用，378个板块 H21 无20个合法 PIT 日期的状态应继续 UNKNOWN。
- **FA-008**：截至2026-10-11，2026-10-12新交易日尚未发生；不得制造后继会话或将稍晚历史重构叫做真实first-observed。
- **FA-007**：S1/S2工程回执并未替代实体 Windows 机器安装/重启/登录/托盘/回滚、真实进程全加载图及用户授权。

## 8. 下一轮分批任务建议（可供 Codex 直接引用）

### P0治理/短周期立即推进

1. **R4-01 全量回归责任拆解**：从本轮4,568原JUnit逐节点输出稳定ID→失败族→第一失败根因→相关业务模块→所需真实fixture/后端迁移/代码修复→owner→复验。优先解决真正源码断言与当前PG架构冲突；以新 BaseException 保护及精确 G-PG 重新执行，不采用全局跳过或降低合约。
2. **R4-02 A1/A2/A3/A5 独立收尾**：校验最新 SHA 的反例、五日只读 Head+token 消费和浏览器数值，更新 effective 位置，保留原件。签 `PASS_SCOPED` 而不是大阶段 PASS。
3. **R4-03 FA-016 运输与消费链**：精确有理系数 typed transport 和 `exact_*` 缺失时 fail-closed；56类调用逐一列消费真实可达、旧/新差异、源日期/PIT、历史输出影响与版本升级策略；保持现行 Owner 不动。
4. **R4-04 FA-018/019 双独立 PG 设计+隔离迁移**：调度和图表索引分别产出表、升级、并发、日期、SHA、回滚和新旧值审计；直到正式准入才可以生产接管。
5. **R4-05 FA-004/020 性能专项**：受控同 Head/token 日期交叉与并发；冻结用户负载和阈值后以 immutable snapshot 减锁、精简首页 payload；扫描器保留所有报警类别并优化重复计行。

### B类旧日补证与持续推进

6. 全 Normative 需求语义索引建立最终合法分母、每个因子/状态/版本的生产公式、实际消费、错误反例；逐模块将真正完成的范围与继续PARTIAL范围严格拆开。
7. 旧日正式 prior-state / LOO / FIRST/ANY labelling producer 和完整 eligible/ineligible cohort 的工程闭环；凡无真实历史 first-available 均标清 `RECONSTRUCTED`，不编造PIT。
8. 逐源核查 Amount A、M14 原probe缺档、24 symbol命中和所有残留失败/跳过，不因整体合规改动而无证据地豁免。

### 等待/另授权项

- **C：真实2026-10-12及后继交易日**：仅实际来源可用后首获、source-aware time、writer Grant、QA、CAS、readback/回滚、六入口同头；不阻塞 R4-01～R4-05。
- **D：真实成熟 Forward/FEP**：按交易会话 T+1/3/5/10/20 逐步累积、右截尾、控制组、OOS 与统计有效性，不让 shadow/回构升级成生产预测。
- **E：Windows现场验收/生产切换**：需用户明确批准窗口，不由审计/工程测试自动授权。

## 9. 版本治理、交付与恢复入口

- 本报告只追加 R3 外部复核，不修改 R1/R2、Codex R3 文件或历史判断。
- 建议下一轮统一问题入口基于 `EFFECTIVE_AUDIT_ITEMS_R3.json` 按本报告增加 `AR3-E04`，并使 old_location/current verified location 分离；文档文本与机器 JSON 对齐。
- Codex R3 包有效入口：`docs/audits/FULL_SYSTEM_AUDIT_CURRENT.md`；R3 报告：`docs/audits/full_system_repair_r3_20261011_239fb9b5/REPAIR_REPORT_R3.md`；全量回归收据：`.../B3_V4_FULL_REGRESSION_RESULT.json`。
- 后续运行禁止以单项工程PASS、自签证明、push成功或索引有字段就解除外部总门。

**最终结论：** `EXTERNAL_ACCEPTANCE_BLOCKED` / `AUDIT_INCOMPLETE`。本轮 A1/A2/A3/A5 具备范围内可复核修复证据，A4 数值候选通过但尚未完整下游消费，A6 无容量PASS。V4中仍有两条实际SQLite依赖，回归有446个失败/错误，字段和正式生产权威主链未闭环。推荐将 R4 的主线转向全量回归分流、PostgreSQL-only 后端实现、精确复权运输与完整因子/状态消费者，而不是继续盲目增加页面。
