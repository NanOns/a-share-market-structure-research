# 阶段00–22及FEP线上×独立审计综合报告 R1

日期：2026-10-06（Asia/Shanghai）。独立审计HEAD：`e21adab807e7f39960ec555764ab8c9d6b50f47b`。线上报告HEAD：`b7ca247745976aa390387a0701601b00ac0d8498`。分支：`codex/v4-system-reform`。

## 1. 综合结论

**主架构总体遵循最新设计，历史00–15和FEP的限定工程接受可以保留；当前项目不能签“全能力完成 / 全仓release PASS / V4-22最终PASS”。线上报告“没有发现新的P0/P1代码合同偏离”需修订：本轮复现2项Forward P1，并证实独立的旧测试隔离P1；阶段15受影响实现需要修复，不能将所有剩余问题归为等待真实交易日。**

全阶段覆盖包括00A–H、01–22、17G及FEP E1–E5，共36个审查单元。阶段16真实grant仍未授予、实际样本0；17无真实readback；18–22多数是合同设计完成、真实执行/切换/累计/最终接受未完成。FEP没有real OOS/Champion/display/priority/production授权。没有新证实P0，不等于穷尽证明所有P0不存在。

本轮交付为两份审计MD、逐阶段/逐问题证据及机器登记；不修业务代码，不产生新的accepted head或权限。Git发布是文档/证据交付，不是外部接受或下一阶段授权。

## 2. 两份审计的关系、设计基线与版本差异

独立报告：[docs/audits/V4_00_22_FEP_INDEPENDENT_FULL_SCOPE_AUDIT_R1_20261006.md](<E:/codex work/大A交易/docs/audits/V4_00_22_FEP_INDEPENDENT_FULL_SCOPE_AUDIT_R1_20261006.md>)。线上报告原字节归档：[docs/evidence/full_scope_independent_20261006/online_model_report_input.md](<E:/codex work/大A交易/docs/evidence/full_scope_independent_20261006/online_model_report_input.md>)；其SHA256=`7db50099464314b37c0c000c68dace1a62253b4e4c1058d43081f673dfe25993`，43204字节。用户附件及其中恢复/修复建议只作为审计证据，**不是本次用户授权执行的指令**。

主设计：[docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md](<E:/codex work/大A交易/docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md>)，ID=`DA-MSR-V4.2.2-CODEX-REV4-FEP-R2`，SHA256=`203ff46075b4039d1e2d45d54fd76ce09509535739cd6aaef4dc394de1015205`，224998字节。FEP同时遵循§90及归档R2设计/正式successors。线上声称Drive与repo逐字一致，本轮核验本地设计身份，未独立重做Drive文本比较；不把他方Drive检验声明升级为本轮实证。

独立代码/合同审查与反例先形成，再完整读取线上报告逐stage综合。此报告没有简单按线上PASS投票；同scope结论按当前证据解释，不同版本/工程与真实权限分层。

线上排除了正在执行的A08。本轮HEAD已含后续A08传播、外审和Git发布：current A08 scoped工程接受保留，V4 Current Audit Head仍为治理传播candidate而非通用production grant；active V6依赖已更新但grant=null/runtime禁用/真实样本0。这个差异是版本更新，不能说线上当时判错。反之，IA-01/02涉及的`v4_15_settlement.py`、`v4_15_settlement_successor.py`及冻结Forward contract在两HEAD中**字节完全相同**，证据[docs/evidence/full_scope_independent_20261006/cross_model_code_identity.json](<E:/codex work/大A交易/docs/evidence/full_scope_independent_20261006/cross_model_code_identity.json>)：它们是当时已有但线上未检出的实现问题，不能归因于后续A08改动。

## 3. 综合判定规则

| 结果层 | 可支持的声明 | 不可推导的声明 |
|---|---|---|
| 历史外审接受 / PASS_KEEP | 当时冻结字节、合同、capability的接受保留 | 当前所有新源码自动获授权 |
| 本轮工程审查通过/保留 | 已审核心公式、结构、输入边界与合同相符；未发现新证伪 | 穷尽所有输入空间、全市场性能、生产ready |
| DEGRADED / SCOPED | 设计允许UNKNOWN/NOT_IMPLEMENTED和受限consumer | 全能力完成或可填0/补造历史 |
| REPAIR_REQUIRED | 独立反例已证实具体公式/集成偏离 | 无关阶段全部重开 |
| CONTRACT_DESIGN_ONLY | schema/interface/反例/权限设计范围可保留 | runtime/replay/cutover已实现 |
| REAL_GATE_PENDING / NOT_GRANTED | 时间/样本/真实source/权限不足，正常fail-closed | 真实工程执行成功或阶段最终PASS |
| 测试债务/环境不足 | 当前验证证据不完整或失败 | 自动否定所有历史算法或静默忽略得全绿 |

## 4. 36个审查单元的线上、独立与综合矩阵

| 阶段 | 线上结果（原范围） | 独立/综合结果 | 对照性质 |
|---|---|---|---|
| V4-00A | PASS | 历史盘点接受可保留；当前全仓回归不可签PASS | 一致/补充边界 |
| V4-00B | PASS_REQUIRED_SCOPE | 日期有效身份工程审查通过；历史PIT能力受限 | 一致/补充边界 |
| V4-00C | PASS | 发布身份和隔离机制工程审查通过 | 一致/补充边界 |
| V4-00D | PASS | 有界源适配与隔离工程审查通过 | 一致/补充边界 |
| V4-00E | PASS_REQUIRED_SCOPE；前次affine缺口已关闭 | 仿射调整工程保留；Forward消费存在新偏离 | 修订 |
| V4-00F | PASS_CONTRACT | 可选补充源降级审查通过 | 一致/补充边界 |
| V4-00G | PASS | 合同框架/三值/窗口定义工程审查通过 | 一致/补充边界 |
| V4-00H | PASS | 当前Phase0接受可保留；性能外推不通过 | 一致/补充边界 |
| V4-01 | FULL_PASS_REQUIRED_SCOPE | 接受范围内工程审查通过；历史全能力不通过 | 一致/补充边界 |
| V4-02 | PASS_REQUIRED_SCOPE_WITH_EXPLICIT_DEGRADATION | Canonical工程范围通过；历史PIT/制度范围受限 | 一致/补充边界 |
| V4-03 | PASS_AMENDED_SCOPE | amended范围工程审查通过 | 一致/补充边界 |
| V4-04 | FULL_PASS_REQUIRED_SCOPE | Pure-Core状态工程审查通过 | 一致/补充边界 |
| V4-05 | SCOPED_DEGRADED_PASS | DATA_FACTOR_REPLAY_DEGRADED范围保留 | 一致/补充边界 |
| V4-06 | PASS_OPTIONAL_SCOPED | 可选DEGRADED范围保留 | 一致/补充边界 |
| V4-07 | ENGINEERING_PASS_SCOPED | 接受范围工程审查通过 | 一致/补充边界 |
| V4-08 | ENGINEERING_PASS_CAPABILITY_SCOPED；full surface未完成 | capability-scoped工程保留；全能力不通过 | 一致/补充边界 |
| V4-09 | ALGORITHM_ENGINEERING PASS；A08_CURRENT_RUNTIME排除 | 当前producer scoped工程审查通过；生产未授权 | 版本更新 |
| V4-10 | FULL_PASS_STAGE_PURPOSE | interface与后续DAG范围工程保留 | 一致/补充边界 |
| V4-11 | ENGINEERING_PASS_CAPABILITY_SCOPED | D0/scenario scoped工程保留 | 一致/补充边界 |
| V4-12 | ENGINEERING_PASS_CAPABILITY_SCOPED | multi-anchor/episode scoped工程保留 | 一致/补充边界 |
| V4-13 | ENGINEERING_PASS_CAPABILITY_SCOPED | scoped工程保留；完整真实LOO不通过 | 一致/补充边界 |
| V4-14 | ENGINEERING_REPLAY_PASS；HISTORICAL_PIT_EFFECTIVENESS未授权 | ALGORITHM_STATE_REPLAY_DEGRADED范围保留 | 一致/补充边界 |
| V4-15 | ENGINEERING PASS；REAL_MATURITY PENDING；前次修复已通过 | 历史接受保留；当前Forward局部REPAIR_REQUIRED | 修订 |
| V4-16 | ENGINEERING_READY；stage final未完成 | 工程待真实grant；受影响Forward能力先修复 | 修订 |
| V4-17 | ENGINEERING_EXTERNALLY_ACCEPTED；真实end-to-end pending | 只读工程通过；真实readback未通过 | 一致/补充边界 |
| V4-17G | NOT_GRANTED / REAL_GATE_PENDING | NOT_GRANTED / 真实验收未开始 | 一致/补充边界 |
| V4-18 | CONTRACT_DESIGN_PASS；runtime未开始 | 合同设计范围保留；实际runtime未实现 | 一致/补充边界 |
| V4-19 | CONTRACT_DESIGN_PASS；cutover未实现 | 合同设计保留；实际切换未实现 | 一致/补充边界 |
| V4-20 | CONTRACT_DESIGN_PASS；default UI cutover未开始 | 合同设计保留；实际默认切换未实现 | 一致/补充边界 |
| V4-21 | CONTRACT_DESIGN_PASS；真实累计未开始 | native contract设计保留；真实累计未实现 | 一致/补充边界 |
| V4-22 | AUDIT_FRAMEWORK_PASS；FINAL NOT_GRANTED | final audit合同设计保留；最终验收BLOCKED | 一致/补充边界 |
| FEP-E1 | ENGINEERING_ACCEPTED；47/47 mapping | 47-field工程范围保留；真实标签/观测未授权 | 一致/补充边界 |
| FEP-E2 | ENGINEERING_ACCEPTED_CAPABILITY_SCOPED | FIRST_PREWATCH:T1工程范围保留 | 一致/补充边界 |
| FEP-E3 | MODEL_ENGINEERING_PASS；MODEL_EFFECTIVENESS NO | 工程范围保留；有效性/OOS不通过 | 一致/补充边界 |
| FEP-E4 | OPTIONAL ENGINEERING_PASS；vs E2 NO_INCREMENT | optional diagnostic工程范围保留 | 一致/补充边界 |
| FEP-E5 | ENGINEERING_COMPLETE_CURRENT_SCOPE；production/display/priority未授权 | canonical工程范围保留；真实display/priority未授权 | 一致/补充边界 |

## 5. 逐阶段综合审计：代码、算法、通过原因和不通过原因

### V4-00A · Baseline Freeze

线上报告§5：`PASS`。本轮独立/综合：**历史盘点接受可保留；当前全仓回归不可签PASS**。

设计合同：设计§70A、§71、§74、§78；历史baseline、备份/恢复与继承审计登记。

核心代码/结构证据：[data/v4/V4_DEV_BASELINE_HEAD.json](<E:/codex work/大A交易/data/v4/V4_DEV_BASELINE_HEAD.json>)；[data/v4/V4_STAGE_ACCEPTED_HEAD.json](<E:/codex work/大A交易/data/v4/V4_STAGE_ACCEPTED_HEAD.json>)；[docs/audits/V4_00A_PG_RECOVERY_AUDIT_20260925.md](<E:/codex work/大A交易/docs/audits/V4_00A_PG_RECOVERY_AUDIT_20260925.md>)。

算法与数据结构结果：冻结基线和保留函数清单是基础盘点；恢复/删除历史记录不替代当前运行授权。数据层采用版本化head，继承问题保持独立登记。

通过/保留依据：当前stage head的phase0_status=FULL_PASS；基线和恢复证据存在。旧head历史字节可从Git恢复。

未通过/未完整的原因：本轮没有再次执行真实数据库恢复演练；默认pytest存在收集错误。不能把历史备份成功推导为本HEAD全仓release ready。

综合裁决及差异解释：基线冻结接受可保留；本轮默认全仓收集失败和IA-09测试隔离问题是独立当前验证债务，不推翻Phase0历史范围。

设计偏离与下一步：未证实盘点设计偏离；GLOBAL-PYTEST为持续开放的跨阶段问题。下一步是独立处置测试债务，不是重跑或删除数据库。

### V4-00B · Security Lifecycle / Universe / PIT

线上报告§5：`PASS_REQUIRED_SCOPE`。本轮独立/综合：**日期有效身份工程审查通过；历史PIT能力受限**。

设计合同：设计§5、§6、§6A、§7.10；后续identity、source authority及A11正式变更。

核心代码/结构证据：[src/workbench_analysis/security_entity_identity.py](<E:/codex work/大A交易/src/workbench_analysis/security_entity_identity.py>)；[src/workbench_analysis/dated_security_alias.py](<E:/codex work/大A交易/src/workbench_analysis/dated_security_alias.py>)；[src/workbench_db/migrations/v4_postgres/001_v4_phase0_foundation.sql](<E:/codex work/大A交易/src/workbench_db/migrations/v4_postgres/001_v4_phase0_foundation.sql>)。

算法与数据结构结果：security_id与源symbol分离；稳定ID来自exchange、anchor symbol、list_date。lifecycle按security_id/effective_from/source_revision复合键保存，Universe用独立snapshot/member主键，保留知识时间。

通过/保留依据：不能靠当前证券代码直接覆盖旧实体；未知上市日返回未解析，别名关系有独立证据。Foundation表并非一股仅一行。

未通过/未完整的原因：旧历史legal lifecycle/type和首次可得时间不能完整证明；当前名册不能自动用于存活偏差修正。

综合裁决及差异解释：一致：日期有效身份/knowledge time结构成立；全历史AS_RECORDED与法律实体类型不自动完整。

设计偏离与下一步：这是已声明的能力限制，未发现允许用当前名册冒充历史PIT的新证据。未来按真实源和alias合同扩展。

### V4-00C · Publication / Revision / Namespace

线上报告§5：`PASS`。本轮独立/综合：**发布身份和隔离机制工程审查通过**。

设计合同：设计§4、§4.6–4.9、§45A、§51A；namespace/publication/head后续加固迁移。

核心代码/结构证据：[src/workbench_db/migrations/v4_postgres/001_v4_phase0_foundation.sql](<E:/codex work/大A交易/src/workbench_db/migrations/v4_postgres/001_v4_phase0_foundation.sql>)；[src/v4/state_identity.py](<E:/codex work/大A交易/src/v4/state_identity.py>)；[src/v4/research_state_persistence.py](<E:/codex work/大A交易/src/v4/research_state_persistence.py>)。

算法与数据结构结果：物理publication与逻辑输入digest分开；同日revision和前市场会话状态分开。manifest绑定实际消费源；namespace、模型、lineage不隐式跨用；head推进靠约束/事务而非任意最新记录。

通过/保留依据：当前读取器检查accepted range、current head、owners、日历与data head一致性；读取验证实际通过。

未通过/未完整的原因：未执行新的生产head推进、跨进程真实发布或数据库部署；本审计没有grant权限。

综合裁决及差异解释：一致：publication/revision/namespace工程范围成立；current owner实际读取通过，不只依赖旧PASS文本。

设计偏离与下一步：未发现新的发布身份硬错误。旧global_head_parent的哈希差异是历史引用，不可用原地重写“修复”。

### V4-00D · TDX VIPDATA Source Contract

线上报告§5：`PASS`。本轮独立/综合：**有界源适配与隔离工程审查通过**。

设计合同：设计§3E、§3F；源package、下载、重叠与archive合同。

核心代码/结构证据：[src/workbench_analysis/tdx_official_daily_source.py](<E:/codex work/大A交易/src/workbench_analysis/tdx_official_daily_source.py>)；[src/workbench_analysis/tdx_snapshot.py](<E:/codex work/大A交易/src/workbench_analysis/tdx_snapshot.py>)；[src/workbench_analysis/canonical_source_selection.py](<E:/codex work/大A交易/src/workbench_analysis/canonical_source_selection.py>)。

算法与数据结构结果：官方页面发现、大小/timeout边界、下载暂存、ZIP manifest校验；ZIP路径、重复大小写成员、symlink/reparse被拒绝。local-overlap优先，补包填local缺口，同时保存替代字节和冲突计数。

通过/保留依据：source family/源revision/记录日期有明确identity；不从源symbol直接猜canonical实体，不使用外部复权价格。

未通过/未完整的原因：本轮不发起下载或重新做全市场源实证；过去A股/非A股分层接受范围仍是权限边界。

综合裁决及差异解释：一致：输入根只读、有界下载/输出分离；本轮未重新下载全量TDX包。

设计偏离与下一步：抽查调用路径未发现写TDX根的操作；不能据此证明仓库每个历史脚本都绝对无潜在写入口。继续仅用项目staging。

### V4-00E · Historical Adjustment / Coordinates

线上报告§5：`PASS_REQUIRED_SCOPE；前次affine缺口已关闭`。本轮独立/综合：**仿射调整工程保留；Forward消费存在新偏离**。

设计合同：设计§3B.6、§41A0、§46A；历史调整与anchor坐标合同。

核心代码/结构证据：[src/adjustment/engine.py](<E:/codex work/大A交易/src/adjustment/engine.py>)；[src/v4/contracts/adjustment.py](<E:/codex work/大A交易/src/v4/contracts/adjustment.py>)；[src/workbench_analysis/v4_12_anchor_runtime.py](<E:/codex work/大A交易/src/workbench_analysis/v4_12_anchor_runtime.py>)；[src/workbench_analysis/v4_15_settlement_successor.py](<E:/codex work/大A交易/src/workbench_analysis/v4_15_settlement_successor.py>)。

算法与数据结构结果：每10股现金/配股/送股生成alpha/beta；连续事件按后事件复合先事件的仿射变换。anchor保留raw bounds、创建基准与source revision；缺当前换基证据保持UNKNOWN。

通过/保留依据：compose顺序与a_total/b_total公式可解释；source有效日期截断；新Forward validator检查系数有限、alpha>0、同基准与identity。

未通过/未完整的原因：A07预capture历史AS_RECORDED不可追补；新Forward校验扩大了区间内部失败对终点收益的影响，见IA-01；板块聚合没有满足新identity，见IA-02。

综合裁决及差异解释：原Affine非法系数硬化可保留，但“已修复”不覆盖IA-01内部缺口/端点隔离，也不覆盖IA-02板块adapter契合。不能据旧修复概括全部Forward正确。

设计偏离与下一步：调整基础公式未证实新错误；消费者隔离出现真实设计偏离。只阻断受影响Forward能力，不撤销基础调整接受。

### V4-00F · BaoStock Supplemental Contract

线上报告§5：`PASS_CONTRACT`。本轮独立/综合：**可选补充源降级审查通过**。

设计合同：设计§3D、§9、§76；A06 scoped acceptance/tolerance后续政策。

核心代码/结构证据：[src/workbench_analysis/baostock_supplemental.py](<E:/codex work/大A交易/src/workbench_analysis/baostock_supplemental.py>)；[src/workbench_analysis/baostock_dm01_capability_v2.py](<E:/codex work/大A交易/src/workbench_analysis/baostock_dm01_capability_v2.py>)；[config/baostock_binding_tolerance_policy_r2_candidate.json](<E:/codex work/大A交易/config/baostock_binding_tolerance_policy_r2_candidate.json>)。

算法与数据结构结果：turn百分点评分换成fraction；provider价格仅用于绑定，不作为Core价格权威。请求预算、版本和重试有界；停牌空量不填0。

通过/保留依据：Core不因BaoStock不可得而失败；未有文档支撑的误差门为null并拒绝strict。

未通过/未完整的原因：STRICT_BINDING_FALSE等限制仍保留；不能把BOUND_SOFT升格为正式换手因子。

综合裁决及差异解释：一致：BaoStock只可选补充，strict-binding不足保持降级，不成为Core总前置。

设计偏离与下一步：与设计允许的可选降级一致。下一步只能消费事先接受的strict证据，不自行拍定容差。

### V4-00G · Algorithm Contract Framework

线上报告§5：`PASS`。本轮独立/综合：**合同框架/三值/窗口定义工程审查通过**。

设计合同：设计§10A0、§72–73、§87A、§78；v1.2/native AST修订。

核心代码/结构证据：[src/v4/contracts/algorithm_contract.py](<E:/codex work/大A交易/src/v4/contracts/algorithm_contract.py>)；[src/v4/contracts/algorithm_contract_v12.py](<E:/codex work/大A交易/src/v4/contracts/algorithm_contract_v12.py>)；[src/v4/contracts/native_rule_r3.py](<E:/codex work/大A交易/src/v4/contracts/native_rule_r3.py>)。

算法与数据结构结果：AST显式FIELD/PARAM/比较/算术与enum；拒绝非有限参数，明确除零缺失、identity/producer/quality/window。技术bar、横截面session、Forward市场horizon分立。标准Kleene与某些required UNKNOWN-dominant wrapper分开记录。

通过/保留依据：因子、Seed、PREWATCH、Rotation、Reducer都有版本合同和参数实例；不能把Kleene FALSE短路当所有消费者都无需缺失质量检查。

未通过/未完整的原因：合同存在不等于所有scope已冻结，marked benchmark等未冻结门仍拒绝；人工语义审查未覆盖每一AST分支的穷尽证明。

综合裁决及差异解释：一致：版本contract/AST/producer/窗口框架成立；IA-01同时说明框架存在与消费公式吻合须分别验证。

设计偏离与下一步：框架没有发现新失效；IA-01表明“有contract”和“实现吻合”必须分开验收。

### V4-00H · Capability / Performance / Rollback

线上报告§5：`PASS`。本轮独立/综合：**当前Phase0接受可保留；性能外推不通过**。

设计合同：设计§49A.2、§52A/B、§74–75、§78；Phase0 final和后续治理归一化。

核心代码/结构证据：[src/v4/contracts/phase0_gate.py](<E:/codex work/大A交易/src/v4/contracts/phase0_gate.py>)；[reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json](<E:/codex work/大A交易/reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json>)；[reports/v4_phase0/V4_PHASE0_PERFORMANCE_BASELINE_R2.json](<E:/codex work/大A交易/reports/v4_phase0/V4_PHASE0_PERFORMANCE_BASELINE_R2.json>)；[data/v4/V4_STAGE_ACCEPTED_HEAD.json](<E:/codex work/大A交易/data/v4/V4_STAGE_ACCEPTED_HEAD.json>)。

算法与数据结构结果：evaluate_phase0检查00A–H齐全、scope owner、必需能力、不合法FULL_PASS+blocked组合；FULL/DEGRADED/BLOCKED与scanner权限分开。

通过/保留依据：当前stage authority已记录FULL_PASS，后续正式记录覆盖早期receipt状态，不把旧PENDING重新判为当前全局bug。

未通过/未完整的原因：2026-09-25性能baseline明确当时v4_runtime_row_count=0，且未运行daily scanner。它不能证明今天全市场DAG、FEP、跨进程路径达到性能预算。marked门未冻结仍受限。

综合裁决及差异解释：历史rollback/performance合同接受保留；本轮没有当前全市场整链负载实证，不能将旧runtime row count=0 baseline外推为当前SLA。

设计偏离与下一步：Phase0状态保留；性能/恢复的当前真实验收为未重验，IA-07记录扩容风险。下一步在真实部署前补当前负载测量。

### V4-01 · TDX History Bootstrap

线上报告§6：`FULL_PASS_REQUIRED_SCOPE`。本轮独立/综合：**接受范围内工程审查通过；历史全能力不通过**。

设计合同：设计§3B、§5.3、§78；R8/R8.3 alias、identity/source-authority正式处置。

核心代码/结构证据：[src/workbench_analysis/tdx_local_snapshot.py](<E:/codex work/大A交易/src/workbench_analysis/tdx_local_snapshot.py>)；[src/workbench_analysis/v4_01_required_scope.py](<E:/codex work/大A交易/src/workbench_analysis/v4_01_required_scope.py>)；[src/workbench_analysis/v4_01_alias_completeness.py](<E:/codex work/大A交易/src/workbench_analysis/v4_01_alias_completeness.py>)；[data/v4/V4_01_ACCEPTED_HEAD.json](<E:/codex work/大A交易/data/v4/V4_01_ACCEPTED_HEAD.json>)。

算法与数据结构结果：archive/extraction摘要、local snapshot身份、source key→canonical entity别名证据与历史Universe映射；缺失required identity关闭相应scope。

通过/保留依据：accepted status为FULL_PASS_REQUIRED_SCOPE，有别名/改代码closure链；快照校验防文件变化和路径逃逸。

未通过/未完整的原因：FULL_PASS_REQUIRED_SCOPE不是两年历史全部生命周期首次可得证据PASS。当前entity修复和historical legal/type范围不可互代。

综合裁决及差异解释：一致：Bootstrap工程接受可保留；线上引用4035729行/786 sessions是历史外审数据，不是本轮又做了一次raw全扫。

设计偏离与下一步：能力降级按设计保留，未发现必须重建已接受bootstrap的新算法证据。

### V4-02 · Canonical Daily / PIT Periods

线上报告§7：`PASS_REQUIRED_SCOPE_WITH_EXPLICIT_DEGRADATION`。本轮独立/综合：**Canonical工程范围通过；历史PIT/制度范围受限**。

设计合同：设计§3C、§7.2/7.5、§10N、§59；R6、A10/A12、DM01 R4R2后续约束。

核心代码/结构证据：[src/workbench_analysis/v4_02_closure.py](<E:/codex work/大A交易/src/workbench_analysis/v4_02_closure.py>)；[src/workbench_analysis/special_price_phases.py](<E:/codex work/大A交易/src/workbench_analysis/special_price_phases.py>)；[src/v4/go_forward_r3.py](<E:/codex work/大A交易/src/v4/go_forward_r3.py>)；[data/v4/V4_DATA_ACCEPTED_HEAD.json](<E:/codex work/大A交易/data/v4/V4_DATA_ACCEPTED_HEAD.json>)。

算法与数据结构结果：原始/调整日线分立；周月由截至asof日线派生，closed与asof period隔离；有bar为ACTUAL，缺bar由日期有效provider status分停牌/数据缺口/UNKNOWN；除权参考用Decimal tick舍入。

通过/保留依据：当前data head接受日期为2026-09-30，正式状态为EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN；daily bridge验证目标日、源/producer实例及lineage。

未通过/未完整的原因：实时capture后才可积累知识时间；historical corrected不升格AS_RECORDED；BSE/special price phase缺证据只降级对应规则，不推断正常limit。DM01直接脚本入口缺repo-root导入bootstrap，见IA-10。

综合裁决及差异解释：Canonical核心和9/30 accepted链结论一致；historical first availability不可补造。另IA-10证实DM01直接CLI缺repo-root bootstrap，底层公式接受不代表独立脚本入口可运行。

设计偏离与下一步：未复活旧A12 blocker；未发现当前数据head被历史源静默覆盖。Forward端实际可估值证据仍缺，见阶段15。

### V4-03 · Pure-Core Factors

线上报告§8：`PASS_AMENDED_SCOPE`。本轮独立/综合：**amended范围工程审查通过**。

设计合同：设计§9A、§10/10A0、§27、§49A.1；Sector ownership正式amendment。

核心代码/结构证据：[src/v4/factors/core.py](<E:/codex work/大A交易/src/v4/factors/core.py>)；[src/v4/factors/relative.py](<E:/codex work/大A交易/src/v4/factors/relative.py>)；[src/v4/factors/native.py](<E:/codex work/大A交易/src/v4/factors/native.py>)；[data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json](<E:/codex work/大A交易/data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json>)。

算法与数据结构结果：MA/ATR/HHV/LLV技术bar窗口跳过已确认停牌并对不明缺口UNKNOWN；retN用固定market endpoints，RPS同分midrank；市场参考起点Universe可评估集等权，delta依赖当时prior RPS工件。

通过/保留依据：asof裁剪、序列唯一递增、调整/source identity和nonfinite输入受检；横截面coverage和input/output/window digest明确。市场参考不是Forward固定篮子。

未通过/未完整的原因：历史prior RPS首次可得/存活偏差不能因accepted historical重构自动证明；Sector native ownership转到08不等于03漏实现。

综合裁决及差异解释：一致：Sector full-market责任移到08有正式amendment，不是主架构偏离。

设计偏离与下一步：与正式ownership修订一致，基础因子抽查无新硬公式错误。保留历史PIT能力边界。

### V4-04 · Full-Market Core Profile

线上报告§9：`FULL_PASS_REQUIRED_SCOPE`。本轮独立/综合：**Pure-Core状态工程审查通过**。

设计合同：设计§10A.3、§10B–10G/10I；r4语义closure、Amount-A独立接受。

核心代码/结构证据：[src/v4/profile_core.py](<E:/codex work/大A交易/src/v4/profile_core.py>)；[src/v4/profile_primitives.py](<E:/codex work/大A交易/src/v4/profile_primitives.py>)；[src/v4/profile_status.py](<E:/codex work/大A交易/src/v4/profile_status.py>)；[data/v4/V4_04_ACCEPTED_HEAD.json](<E:/codex work/大A交易/data/v4/V4_04_ACCEPTED_HEAD.json>)。

算法与数据结构结果：趋势/位置/均线/相对/压缩/量额/extension按冻结阈值顺序和UNKNOWN规则映射；技术长窗要求日期状态与日历一致。UNKNOWN和NOT_IMPLEMENTED不同；Participation缺clv只影响所需分支。

通过/保留依据：Core Profile不依赖Turnover/sector/advanced；技术停牌与未知缺口有明确区别，branch顺序可解释。

未通过/未完整的原因：Sector Amount-A producer scoped accepted不能给H21 consumer或Stock AMR20授权；derived原始接口仍要求上游accepted输入合同。

综合裁决及差异解释：一致：Pure-Core分层和全市场profile已实现；规则分类不等于策略收益已验证。

设计偏离与下一步：未发现新Pure-Core branch漂移；A04_H21及historical Amount-A继续单独保留。

### V4-05 · Replay Gate A

线上报告§10：`SCOPED_DEGRADED_PASS`。本轮独立/综合：**DATA_FACTOR_REPLAY_DEGRADED范围保留**。

设计合同：设计§53 Gate A、§54–55；R4.1/R4.2 exact candidate绑定及A02下游amendment。

核心代码/结构证据：[src/v4/replay_r4_identity.py](<E:/codex work/大A交易/src/v4/replay_r4_identity.py>)；[src/v4/replay_r4_lfs.py](<E:/codex work/大A交易/src/v4/replay_r4_lfs.py>)；[src/v4/replay_r3_guards.py](<E:/codex work/大A交易/src/v4/replay_r3_guards.py>)；[data/v4/V4_05_ACCEPTED_HEAD.json](<E:/codex work/大A交易/data/v4/V4_05_ACCEPTED_HEAD.json>)。

算法与数据结构结果：因子/日线/Universe/坐标重放identity，exact candidate ledger及逻辑摘要；LFS实体与pointer分开，target日期限定Universe身份。

通过/保留依据：Accepted status明确DEGRADED；当前代码有源和ledger绑定，不单靠测试数量签release。

未通过/未完整的原因：重构重放稳定并不证明historical AS_RECORDED。旧target日期受accepted artifact限定，不能自动用于新目标日。

综合裁决及差异解释：一致：Replay Gate A可在受限capability内成立；历史PIT effectiveness未授权。

设计偏离与下一步：未发现新Gate A身份缺陷；全仓pytest不绿是独立测试债务，不能改写历史Gate A范围。

### V4-06 · Turnover Supplemental

线上报告§11：`PASS_OPTIONAL_SCOPED`。本轮独立/综合：**可选DEGRADED范围保留**。

设计合同：设计§9、§9A、§76；TURNOVER_CONTEXT_V1与A06 binding tolerance。

核心代码/结构证据：[src/workbench_analysis/v4_06_supplemental.py](<E:/codex work/大A交易/src/workbench_analysis/v4_06_supplemental.py>)；[src/workbench_analysis/baostock_supplemental.py](<E:/codex work/大A交易/src/workbench_analysis/baostock_supplemental.py>)；[data/v4/V4_06_ACCEPTED_HEAD.json](<E:/codex work/大A交易/data/v4/V4_06_ACCEPTED_HEAD.json>)。

算法与数据结构结果：append-only enrichment revision；strict-only历史窗口，confirmed suspension与UNKNOWN分开。证券映射拒绝重复/歧义，换代码须显式accepted映射。

通过/保留依据：不修改Core publication/资格、不把turn字段变成自由流通换手；补充源异常只影响自身。

未通过/未完整的原因：strict binding不可证明时上下文继续PENDING/UNAVAILABLE/UNKNOWN，不能自动恢复成正式输入。

综合裁决及差异解释：一致：Supplemental缺失不阻断07；严格源绑定不足只影响对应补充能力。

设计偏离与下一步：设计允许的可选降级，不构成07前置全局block。下一步补充能力需自己的外审。

### V4-07 · Stock Base Seed / PASS A

线上报告§12：`ENGINEERING_PASS_SCOPED`。本轮独立/综合：**接受范围工程审查通过**。

设计合同：设计§13A–14；BASE_SEED_V1、参数/field/vector freeze和A02 amendment。

核心代码/结构证据：[src/v4/base_seed.py](<E:/codex work/大A交易/src/v4/base_seed.py>)；[config/v4_07_base_seed_contract_v1.json](<E:/codex work/大A交易/config/v4_07_base_seed_contract_v1.json>)；[config/v4_07_parameter_set_v1.json](<E:/codex work/大A交易/config/v4_07_parameter_set_v1.json>)；[data/v4/V4_07_ACCEPTED_HEAD.json](<E:/codex work/大A交易/data/v4/V4_07_ACCEPTED_HEAD.json>)。

算法与数据结构结果：仅消费Core原始安全、位置、结构、相对变化；不读Final State、Focus、在线补充。参数ID、comparison、status和值域校验，UNKNOWN保留理由；输出规则路径和谓词。

通过/保留依据：真实loader验证full-market行数、board/date/publication与receipt/artifact摘要，不把单条成功样本代表全Universe。

未通过/未完整的原因：历史prior RPS不可得影响对应分支；当前Freeze为candidate本身不授予新目标日生产权限，授权靠接受链。

综合裁决及差异解释：一致：BaseSeed Pure-Core whitelist与unknown propagation；真实prior-RPS bootstrap限制仍保留。

设计偏离与下一步：未发现新反馈/参数偷换；上游质量限制必须继续传播。

### V4-08 · Sector / Rotation / PASS B

线上报告§13：`ENGINEERING_PASS_CAPABILITY_SCOPED；full surface未完成`。本轮独立/综合：**capability-scoped工程保留；全能力不通过**。

设计合同：设计§15–21A；R5.2 accepted context、A05 B2 amendment、A04 producer scoped acceptance。

核心代码/结构证据：[src/sector/native_r5.py](<E:/codex work/大A交易/src/sector/native_r5.py>)；[src/sector/rotation_r5.py](<E:/codex work/大A交易/src/sector/rotation_r5.py>)；[src/sector/accepted_context_r5_2.py](<E:/codex work/大A交易/src/sector/accepted_context_r5_2.py>)；[data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json](<E:/codex work/大A交易/data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json>)。

算法与数据结构结果：membership有效时点、common members、sector等权median/width/rank、Wilson seed width；Rotation冻结pulse basket/denominator，quality四态，missing history关闭分支；不用1/N成员稀释替代重叠诊断。

通过/保留依据：retention不删除不可得成员；price basis不匹配不算收益；mature-only UNKNOWN不无条件污染early允许分支。

未通过/未完整的原因：legacy valid-member仅CURRENT_SNAPSHOT范围；Amount-A H21和历史Amount-A未授权，WARM受限制；historical PIT成员不得以现在成员补造。

综合裁决及差异解释：一致；进一步区分Amount-A producer工程接受、H21正式consumer和historical consumer。producer接受不关闭A04_H21/HISTORICAL；IA-02是其Forward消费专项，不否定当日Rotation Core。

设计偏离与下一步：这些是正式限制。IA-02只涉及Forward板块结算，不能因此否定Rotation当日Core算法。

### V4-09 · Stock PREWATCH / PASS C

线上报告§14：`ALGORITHM_ENGINEERING PASS；A08_CURRENT_RUNTIME排除`。本轮独立/综合：**当前producer scoped工程审查通过；生产未授权**。

设计合同：设计§22–25、§37–39；r1.1 priority provenance、A08 current runtime最新外审和V4传播。

核心代码/结构证据：[src/v4/stock_prewatch.py](<E:/codex work/大A交易/src/v4/stock_prewatch.py>)；[config/v4_09_priority_provenance_contract_r1_1.json](<E:/codex work/大A交易/config/v4_09_priority_provenance_contract_r1_1.json>)；[config/v4_16_runtime_capability_resolution_v2.json](<E:/codex work/大A交易/config/v4_16_runtime_capability_resolution_v2.json>)；[data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4.json](<E:/codex work/大A交易/data/v4/V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V4.json>)。

算法与数据结构结果：raw采用UNKNOWN_DOMINANT_AND(base_seed,mandatory quality)；Emergence/Structure/Risk独立三轴，priority axes有producer/source identity。先遇到未解析HIGH候选不越过它直接选MEDIUM。

通过/保留依据：当前load_package实际通过；A08_CURRENT_RUNTIME为ACCEPTED_SCOPED，scope shadow blocker false；V6 resolver分issue_id和runtime capability，未知issue fail-closed。

未通过/未完整的原因：V4 Current Audit Head整体status仍是GOVERNANCE_PROPAGATION_CANDIDATE；A08外审与生产/真实激活权限不能等同。production blocker仍true，permission_granted=false。

综合裁决及差异解释：版本更新：本轮包含当前A08 V4/active V6传播，ACCEPTED_SCOPED仅工程Shadow依赖；production_blocking仍true，permission=false。线上排除是其当时scope，不能沿用为本轮排除。

设计偏离与下一步：相比线上报告的b7ca247基线，A08传播状态更新不是审计分歧；本轮不改变任何正式head。

### V4-10 · Multi-Axis State Reducer

线上报告§15：`FULL_PASS_STAGE_PURPOSE`。本轮独立/综合：**interface与后续DAG范围工程保留**。

设计合同：设计§30–33、§78；authority/lineage/calendar同日修订加固。

核心代码/结构证据：[src/v4/research_state.py](<E:/codex work/大A交易/src/v4/research_state.py>)；[src/v4/state_provenance.py](<E:/codex work/大A交易/src/v4/state_provenance.py>)；[src/v4/research_state_persistence.py](<E:/codex work/大A交易/src/v4/research_state_persistence.py>)；[data/v4/V4_10_ACCEPTED_HEAD.json](<E:/codex work/大A交易/data/v4/V4_10_ACCEPTED_HEAD.json>)。

算法与数据结构结果：model boundary→硬失效→required UNKNOWN→阶段选取→降级hysteresis/health/expiry/reentry；停牌保留旧状态，市场会话计龄，同会话不reentry，episode/invalidation identity冻结。

通过/保留依据：硬失效优先于UNKNOWN；stock WARM为NOT_APPLICABLE；同日不累加downgrade天数；边界保留followup旧episode，不把新模型偷接旧state。

未通过/未完整的原因：10本身accepted是interface scope，完整owner DAG由11/12/14验收；仍有R3C item级production/historical re-audit debt。

综合裁决及差异解释：一致：本stage要求interface/独立向量；完整DAG在14验收。不因旧10 Head NOT_IMPLEMENTED判全stage失败。

设计偏离与下一步：未发现必须重写reducer的新业务证据；不能把接口PASS叫完整模型实证PASS。

### V4-11 · Confirmation / Events

线上报告§16：`ENGINEERING_PASS_CAPABILITY_SCOPED`。本轮独立/综合：**D0/scenario scoped工程保留**。

设计合同：设计§34A、§71；R5 sealed D2 authority、stock AMR20 semantic erratum。

核心代码/结构证据：[src/v4/confirmation.py](<E:/codex work/大A交易/src/v4/confirmation.py>)；[src/v4/confirmation_events.py](<E:/codex work/大A交易/src/v4/confirmation_events.py>)；[src/v4/confirmation_d2_candidate_r5.py](<E:/codex work/大A交易/src/v4/confirmation_d2_candidate_r5.py>)；[src/v4/sealed_owner_authority_r5.py](<E:/codex work/大A交易/src/v4/sealed_owner_authority_r5.py>)。

算法与数据结构结果：原V3.3 detector AST/参数精确提取；D0禁FINAL_STATE/FOCUS/online/future，同日downstream scenario diagnostic-only。prior_session真实state事件diff，logical event与same-day observation分离。

通过/保留依据：包校验legacy AST/参数；缺required fact保持UNKNOWN；Stock AMR20与Sector Amount-A隔离，不因A04 producer接受就授权stock confirmation。

未通过/未完整的原因：TREND_CONTINUE中无法纯化的LOO依赖保持diagnostic；R3C prior/停牌/坐标外审item仍开放。

综合裁决及差异解释：一致：LAUNCH/RECOVERY正式，另两scenario diagnostic及历史event debt不能误写为四场景全正式。

设计偏离与下一步：符合“不伪造owner能力”设计；可保留既有scenario范围，不能宣布全部scenario生产完成。

### V4-12 · Structure / Anchor / Support

线上报告§17：`ENGINEERING_PASS_CAPABILITY_SCOPED`。本轮独立/综合：**multi-anchor/episode scoped工程保留**。

设计合同：设计§10J–L、§41A–G；R13 breakout episode、R9会话计数修订及R14 promotion。

核心代码/结构证据：[src/workbench_analysis/v4_12_anchor_runtime.py](<E:/codex work/大A交易/src/workbench_analysis/v4_12_anchor_runtime.py>)；[src/workbench_analysis/v4_12_multi_anchor_state.py](<E:/codex work/大A交易/src/workbench_analysis/v4_12_multi_anchor_state.py>)；[src/workbench_analysis/v4_12_structure_engine.py](<E:/codex work/大A交易/src/workbench_analysis/v4_12_structure_engine.py>)；[src/workbench_analysis/v4_12_breakout_episode.py](<E:/codex work/大A交易/src/workbench_analysis/v4_12_breakout_episode.py>)。

算法与数据结构结果：每anchor绑定event/episode，raw坐标不可改；创建当日计数为0且support IDLE，杜绝自确认。selector按距离/日期/ID，不用首项fallback；会话/实际bar计数不同；hard invalidation优先。

通过/保留依据：多anchor独立owning episode/counter digest；同日revision和unknown按冻结合同处理；coordinate_view缺换基证据UNKNOWN。

未通过/未完整的原因：真实owner、raw-anchor换基和历史窗口证据未全覆盖，不能从裸日线自行补造accepted结构输入。部分validator当前字节与历史接受SHA不同，旧字节可在Git精确恢复。

综合裁决及差异解释：一致：multi-anchor/coordinate/episode/counters实现；真实owner/historical capability受限，历史validator路由债务独立记录。

设计偏离与下一步：限定能力保留；独立追踪historical/production re-audit及IA-08历史validator路由，不原地改接受工件。

### V4-13 · Advanced Projection / LOO

线上报告§18：`ENGINEERING_PASS_CAPABILITY_SCOPED`。本轮独立/综合：**scoped工程保留；完整真实LOO不通过**。

设计合同：设计§20–21、§41F/§65；R16 input binder、projection、publication与R17 active binding。

核心代码/结构证据：[src/workbench_analysis/v4_13_input_binder.py](<E:/codex work/大A交易/src/workbench_analysis/v4_13_input_binder.py>)；[src/workbench_analysis/v4_13_loo_runtime.py](<E:/codex work/大A交易/src/workbench_analysis/v4_13_loo_runtime.py>)；[src/workbench_analysis/v4_13_profile_runtime.py](<E:/codex work/大A交易/src/workbench_analysis/v4_13_profile_runtime.py>)；[data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json](<E:/codex work/大A交易/data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json>)。

算法与数据结构结果：先排除目标再native、seed、端点和cross-section重算；primary industry与algorithmic support分开；全候选不完整时不能从已知候选“挑最好”掩盖UNKNOWN。

通过/保留依据：prior自包含Rotation不冒充独立LOO episode；未知accepted history保持UNKNOWN；raw stock资格不反吃context enrichment。

未通过/未完整的原因：代码明确历史LOO NOT_VERIFIABLE/legacy B2 NOT_IMPLEMENTED/real support UNKNOWN；当日完整LOO/Rotation不能由这些工程输出宣称有实证。

综合裁决及差异解释：一致：target exclusion在LOO重算之前；current membership与historical membership authority分离。

设计偏离与下一步：允许的分层降级，未发现新自反馈证据；当前真实能力仍不足。

### V4-14 · Replay Gate B / Full DAG

线上报告§19：`ENGINEERING_REPLAY_PASS；HISTORICAL_PIT_EFFECTIVENESS未授权`。本轮独立/综合：**ALGORITHM_STATE_REPLAY_DEGRADED范围保留**。

设计合同：设计§13A、§53 Gate B、§54–58；R18 precall consumption/独立oracle/rollback。

核心代码/结构证据：[src/workbench_analysis/v4_14_precall_runtime.py](<E:/codex work/大A交易/src/workbench_analysis/v4_14_precall_runtime.py>)；[src/workbench_analysis/v4_14_owner_edge_runtime.py](<E:/codex work/大A交易/src/workbench_analysis/v4_14_owner_edge_runtime.py>)；[src/workbench_analysis/v4_14_full_dag.py](<E:/codex work/大A交易/src/workbench_analysis/v4_14_full_dag.py>)；[src/workbench_analysis/v4_14_candidate_rollback_drill.py](<E:/codex work/大A交易/src/workbench_analysis/v4_14_candidate_rollback_drill.py>)。

算法与数据结构结果：F0→A→B→C→D0/D1→D2→context/projection按owner/input digest边绑定；precall先消费验证而不是结果出来后补伪trace；跨进程重放和rollback有独立记录。

通过/保留依据：当前owner-head读取验证通过，synthetic事实明确标SYNTHETIC；reconstructed不自动成为historical PIT。

未通过/未完整的原因：engineered full DAG不是历史首次可得实证；Current Audit仍保留若干R3C/Git portability/real-window item；本轮未重新运行真实整市DAG。

综合裁决及差异解释：一致：DAG输入绑定、时序和revision replay是工程证据；不是全历史PIT，也不是M14在线增强模块。

设计偏离与下一步：既有scoped Replay B保留；全模型historical PIT effectiveness/生产资格仍NOT_GRANTED。

### V4-15 · Radar / Cohort / Settlement

线上报告§20：`ENGINEERING PASS；REAL_MATURITY PENDING；前次修复已通过`。本轮独立/综合：**历史接受保留；当前Forward局部REPAIR_REQUIRED**。

设计合同：设计§36、§45A–49B；R20持久化/independent oracle、R21接受、full-chain successor修复。

核心代码/结构证据：[src/workbench_analysis/v4_15_radar_cohort.py](<E:/codex work/大A交易/src/workbench_analysis/v4_15_radar_cohort.py>)；[src/workbench_analysis/v4_15_settlement.py](<E:/codex work/大A交易/src/workbench_analysis/v4_15_settlement.py>)；[src/workbench_analysis/v4_15_settlement_successor.py](<E:/codex work/大A交易/src/workbench_analysis/v4_15_settlement_successor.py>)；[src/workbench_analysis/v4_15_fep_label_time.py](<E:/codex work/大A交易/src/workbench_analysis/v4_15_fep_label_time.py>)。

算法与数据结构结果：日账本、logical event、enrollment按独立键；T0参考/controls/固定权重冻结。Forward T+1/3/5/10/20，统一evaluation basis，MDD为路径峰值回撤；outcome append-only，source revision与first/latest分开。

通过/保留依据：股票公式、未知benchmark不阻断absolute、ITT不因对照后来入选而删除的结构设计成立；A/B/C对照分开。

未通过/未完整的原因：IA-01区间内部失败错误清空已验证端点R；IA-02板块aggregate少adjustment_identity且旧实现close-only冒充MFE_N。IA-03同源PENDING→DUE被幂等复用。real matured source/跨日换基尚未授权。

综合裁决及差异解释：实质修订：IA-01/02当前Forward局部REPAIR_REQUIRED；IA-03/04分别为通用API状态和输入边界P2。真实成熟待积累仍正确，但并非全部剩余问题只需等市场时间。

设计偏离与下一步：IA-01/02为当前实现与合同偏离；IA-03限定通用工程API。不得用historical engineering接受抹掉本轮反例。

### V4-16 · Realtime Shadow Dual-Run

线上报告§27：`ENGINEERING_READY；stage final未完成`。本轮独立/综合：**工程待真实grant；受影响Forward能力先修复**。

设计合同：设计§51A、§52B、§77；最新V6 dependencies/authority V5、P0-02 R1R1和A08传播。

核心代码/结构证据：[scripts/v4_16_go_forward_shadow_runtime_r4r4.py](<E:/codex work/大A交易/scripts/v4_16_go_forward_shadow_runtime_r4r4.py>)；[scripts/v4_16_settlement_worker_v2.py](<E:/codex work/大A交易/scripts/v4_16_settlement_worker_v2.py>)；[migrations/v4_16_real_shadow_integrity_v2.sql](<E:/codex work/大A交易/migrations/v4_16_real_shadow_integrity_v2.sql>)；[config/v4_16_runtime_activation_authority_v5.json](<E:/codex work/大A交易/config/v4_16_runtime_activation_authority_v5.json>)。

算法与数据结构结果：grant在源读取/数据库打开之前；exact activation_head决定重启authority；queue由namespace/model/lineage/enrollment/horizon/due/source构造，CAS lease fence及at-least-once delivery；STOP不停止已接受结算义务。

通过/保留依据：V6绑定核验均匹配；A08只解capability blocker不grant。P0-02已拒绝queue identity冲突和错误activation记录。trigger/FK为publication/slot/event/freeze/enrollment/due/outcome建立关系。

未通过/未完整的原因：当前grant=null、runtime_authorized=false、real_shadow_authorized=false，真实样本0。worker仍调用IA-01/02的successor；AcceptedPriceSource缺T0_basis_verified/available_at时降级，不能得到成熟OBSERVED。

综合裁决及差异解释：真实grant/样本0结论一致；“工程ready”需缩限：durable worker使用IA-01路径，Sector开放前还需IA-02。不能直接从前次hardening PASS推断当前全Forward范围ready。

设计偏离与下一步：保持禁用符合设计，不是bug；“所有capability工程ready”不成立。IA-01针对Stock路径质量，IA-02在Sector开放前须修复。

### V4-17 · Shadow UI

线上报告§28：`ENGINEERING_EXTERNALLY_ACCEPTED；真实end-to-end pending`。本轮独立/综合：**只读工程通过；真实readback未通过**。

设计合同：设计§62A–H、§69、§78；R26只读UI/source manifest合同。

核心代码/结构证据：[src/workbench_service/shadow_context.py](<E:/codex work/大A交易/src/workbench_service/shadow_context.py>)；[src/workbench_service/static/shadow-v4.js](<E:/codex work/大A交易/src/workbench_service/static/shadow-v4.js>)；[src/workbench_service/app.py](<E:/codex work/大A交易/src/workbench_service/app.py>)；[config/v4_17_shadow_ui_source_v1.json](<E:/codex work/大A交易/config/v4_17_shadow_ui_source_v1.json>)。

算法与数据结构结果：context token绑定namespace/date/publication revision/model/params/lineage/daily input/source/readback manifest。SQLite mode=ro+query_only，路由GET-only，缺来源UNKNOWN。

通过/保留依据：accepted_readback=null时不发现任意latest文件、不打开DB；simulation只能constructor注入；HTTP写被拒绝。

未通过/未完整的原因：没有真实publication/component readback外审；UI工程通过不等于真实今日V4页面完整。R26-A01继承V3失败单独保留。

综合裁决及差异解释：一致：只读context token/GET/SQLite read-only工程保留；accepted readback为空时无连接、不以目录最新simulation替代。

设计偏离与下一步：缺真实门符合设计。下一步必须受独立真实manifest接受后才签real UI readback。

### V4-17G · Shadow Stable / Provisional Forward Gate

线上报告§29：`NOT_GRANTED / REAL_GATE_PENDING`。本轮独立/综合：**NOT_GRANTED / 真实验收未开始**。

设计合同：设计§51–52B、§78；capability cutover policy与R30 native session owner。

核心代码/结构证据：[config/v4_capability_cutover_policy_v1.json](<E:/codex work/大A交易/config/v4_capability_cutover_policy_v1.json>)；[config/v4_21_continued_forward_observation_contract_v1.json](<E:/codex work/大A交易/config/v4_21_continued_forward_observation_contract_v1.json>)；[config/v4_16_observation_slot_contract_v2.json](<E:/codex work/大A交易/config/v4_16_observation_slot_contract_v2.json>)。

算法与数据结构结果：按capability累计连续accepted/evaluable session、漏slot/泄漏/回滚以及独立成熟事件；不把20–60日稳定期当模型盈利证明。

通过/保留依据：政策区分engineering/forward/production permission，设计oracle不会grant。

未通过/未完整的原因：真实accepted session和matured event尚不足/为0；Sector/Rotation等未冻结门不能借stock事件取得授权。

综合裁决及差异解释：一致：尚无真实session，不可用reconstructed历史数凑stable/Forward门。

设计偏离与下一步：正常真实门待满足，不靠补造历史关闭。

### V4-18 · Migration Replay Gate C

线上报告§30：`CONTRACT_DESIGN_PASS；runtime未开始`。本轮独立/综合：**合同设计范围保留；实际runtime未实现**。

设计合同：设计§34–35、§53 Gate C、§77–78；最新namespace inventory successor V1_3。

核心代码/结构证据：[config/v4_18_migration_replay_contract_v1_3.json](<E:/codex work/大A交易/config/v4_18_migration_replay_contract_v1_3.json>)；[tests/fep/test_v4_18_namespace_successor.py](<E:/codex work/大A交易/tests/fep/test_v4_18_namespace_successor.py>)；[tests/test_v4_18_migration_contract.py](<E:/codex work/大A交易/tests/test_v4_18_migration_contract.py>)。

算法与数据结构结果：逐表REFERENCE/CARRY/NOT_MIGRATED/COPY、读源/写目标/rollback，保留open episode、pending settlement、user pin/note。当前226个适用SQL declaration与namespace matrix相符；旧R23工程schema不在该当前迁移范围。

通过/保留依据：FEP canonical reconstruction/parallel legacy/033 signal registry与queue/integrity表已入最新矩阵；无生产write target冒领。

未通过/未完整的原因：future interfaces均未实现，receipts=null，migration_execution=false，accepted head不存在。最新successor不能继承旧版本外审就视为exact runtime接受。

综合裁决及差异解释：一致：V1_3设计-only，六接口未实现；独立inventory适用226个声明全部覆盖。R23历史工程16表不属active migration，不能报漏表；真正runtime前仍需最终successor exact外审。

设计偏离与下一步：是计划内gate暂停；工程未完成，不能写“Migration Replay已通过”。实现前固化最终successor exact external acceptance。

### V4-19 · Focus Source Cutover

线上报告§31：`CONTRACT_DESIGN_PASS；cutover未实现`。本轮独立/综合：**合同设计保留；实际切换未实现**。

设计合同：设计§42–44、§52A/B、§77–78；R28 CUTOVER_V2 scoped policy。

核心代码/结构证据：[config/v4_19_focus_source_cutover_contract_v1.json](<E:/codex work/大A交易/config/v4_19_focus_source_cutover_contract_v1.json>)；[reports/r28/design_oracle.py](<E:/codex work/大A交易/reports/r28/design_oracle.py>)；[tests/test_v4_19_focus_cutover_contract.py](<E:/codex work/大A交易/tests/test_v4_19_focus_cutover_contract.py>)。

算法与数据结构结果：Stock Core、Sector Stage、stock-sector、Rotation、risk change权限有依赖图；source route CAS、rollback按affected scope，user state不作为算法证据。

通过/保留依据：oracle支持混合能力不全局promotion；无receipt、错scope、不足样本都NO_CUTOVER。

未通过/未完整的原因：route CAS/rollback声明implemented=false，cutover=false，V4_19 head NOT_CREATED；只有设计向量，不是运行迁移器。

综合裁决及差异解释：一致：capability permissions/writer/CAS/rollback未执行，Focus源未切。

设计偏离与下一步：与等待17G/18 runtime门一致；不能把设计PASS扩成Focus生产完成。

### V4-20 · Default UI Cutover

线上报告§32：`CONTRACT_DESIGN_PASS；default UI cutover未开始`。本轮独立/综合：**合同设计保留；实际默认切换未实现**。

设计合同：设计§62A–H、§68–69、§78；R29 mixed-module/context policy。

核心代码/结构证据：[config/v4_20_default_ui_cutover_contract_v1.json](<E:/codex work/大A交易/config/v4_20_default_ui_cutover_contract_v1.json>)；[reports/r29/design_resolver.py](<E:/codex work/大A交易/reports/r29/design_resolver.py>)；[tests/test_v4_20_default_ui_contract.py](<E:/codex work/大A交易/tests/test_v4_20_default_ui_contract.py>)。

算法与数据结构结果：模块权限分别路由Legacy/V4/Shadow，context锁publication身份；stale session失效缓存，历史deep link只读，跨mode不静默重绑定。

通过/保留依据：全模块当前LEGACY_PRODUCTION，显式shadow页面工程只读；模拟resolver不修改真实route。

未通过/未完整的原因：DEFAULT_UI_CUTOVER=false、生产permission全false，cutover接口尚未runtime实现。

综合裁决及差异解释：一致：模块逐项permission和mixed routing，当前默认Legacy；不是全局V4生产页。

设计偏离与下一步：产品目标尚未完成；这是gate保护下的欠交付，不是当前静默切换bug。

### V4-21 · Continued Forward Observation

线上报告§33：`CONTRACT_DESIGN_PASS；真实累计未开始`。本轮独立/综合：**native contract设计保留；真实累计未实现**。

设计合同：设计§46–52、§78；R30R1 native status/owner binding修订，v1版本1.0.1。

核心代码/结构证据：[config/v4_21_continued_forward_observation_contract_v1.json](<E:/codex work/大A交易/config/v4_21_continued_forward_observation_contract_v1.json>)；[reports/r30r1/session_authority.py](<E:/codex work/大A交易/reports/r30r1/session_authority.py>)；[reports/r30/design_ledger.py](<E:/codex work/大A交易/reports/r30/design_ledger.py>)。

算法与数据结构结果：按owner原生ACCEPTED_ON_TIME/MISSED_OBSERVATION_SLOT等状态与projection evaluable分开；SHADOW_REAL/PRODUCTION_REAL/replay lane隔离；事件/结果/日期计数不同。

通过/保留依据：错拼status、错owner SHA、诊断lane混真实计数、MISSED却evaluable被拒绝；production native owner未绑定则不能计real gate。

未通过/未完整的原因：REAL_CONTINUED_FORWARD_OBSERVATION=NOT_STARTED，当前真实production status authority=null；设计模拟不能算真实累计。

综合裁决及差异解释：一致：native ACCEPTED_ON_TIME归owner，evaluable独立投影；真实继续观察无writer授权。

设计偏离与下一步：合同修复有效，实际持续观察仍未交付/未开始。先解决Forward局部错误和真实activation，再按授权积累。

### V4-22 · Independent Audit

线上报告§34：`AUDIT_FRAMEWORK_PASS；FINAL NOT_GRANTED`。本轮独立/综合：**final audit合同设计保留；最终验收BLOCKED**。

设计合同：设计§51、§80–81、§85、§78；R31R2 fail-closed/item closure/exact reconstruction修订。

核心代码/结构证据：[config/v4_22_independent_audit_contract_v1.json](<E:/codex work/大A交易/config/v4_22_independent_audit_contract_v1.json>)；[reports/r31/audit_oracle.py](<E:/codex work/大A交易/reports/r31/audit_oracle.py>)；[reports/r31r2/build_contract.py](<E:/codex work/大A交易/reports/r31r2/build_contract.py>)；[tests/test_v4_22_r31r2_repair.py](<E:/codex work/大A交易/tests/test_v4_22_r31r2_repair.py>)。

算法与数据结构结果：closure evidence与closing authority分开exact path/SHA/contract校验；canonical digest本身不足。诊断lane先完整校验再过滤，最终verdict由open items、真实gates、accepted receipt共同构成。

通过/保留依据：版本1.0.2避免旧builder无条件制造新canonical版本；OPEN-09非blocking语义独立保留。模拟final formula成立仍acceptance_granted=false。

未通过/未完整的原因：真实shadow/forward/migration/cutover/rollback和本轮IA-01/02未关闭，最终final pass NOT_GRANTED，head未创建。

综合裁决及差异解释：一致：closure evidence/item authority/schema加固是合同审计；真实前置未完成，且本轮新项未关闭，不能签最终验收。

设计偏离与下一步：本审计是输入证据，不能自称V4-22最终独立接受或替用户授予下一stage。

### FEP-E1 · Dataset / Identity / Registry

线上报告§22：`ENGINEERING_ACCEPTED；47/47 mapping`。本轮独立/综合：**47-field工程范围保留；真实标签/观测未授权**。

设计合同：设计§90 FEP.1–6、FEP R2；E1 R2 final owner/governance及028–030 migration。

核心代码/结构证据：[src/workbench_analysis/fep_e1/observation.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e1/observation.py>)；[src/workbench_analysis/fep_e1/feature_owner.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e1/feature_owner.py>)；[src/workbench_analysis/fep_e1/labels.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e1/labels.py>)；[src/workbench_analysis/fep_e1/datasets.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e1/datasets.py>)。

算法与数据结构结果：observation按scope/entity/date/signal逻辑身份；feature从exact accepted owner取47字段，不重算；label复制V4-15权威revision、source/mature/revision三时间。完整分母/每partition asof selection、缺失不删除。

通过/保留依据：per-fold日期/episode不跨partition；不回填FIRST_OBSERVED；历史owner仅reconstruction。real adapter即使调用者传horizon字典也明确拒绝。

未通过/未完整的原因：FEP_REAL_FIRST_OBSERVED_ENTRY与REAL_MATURED_LABEL未授权；当前E1 live owner传输不同于E2历史工程数据。IA-06：本轮真实PG环境未完整复验，历史fresh/upgrade接受仅范围保留。

综合裁决及差异解释：一致：owner字段copy、完整分母/as-of三时间；本轮PG因fixture/DSN不足skip，限制重新验收，真实label和FIRST_OBSERVED尚无。

设计偏离与下一步：已知接口缺口按设计fail-closed；不得宣传实时训练标签已可用。IA-07记录dataset权重算法扩容风险。

### FEP-E2 · Conditional Statistics Baseline

线上报告§23：`ENGINEERING_ACCEPTED_CAPABILITY_SCOPED`。本轮独立/综合：**FIRST_PREWATCH:T1工程范围保留**。

设计合同：设计§90 FEP统计/backoff/support；E2 R1R2 event strata及support policy v1_1。

核心代码/结构证据：[src/workbench_analysis/fep_e2/conditional.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e2/conditional.py>)；[src/workbench_analysis/fep_e2/support.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e2/support.py>)；[src/workbench_analysis/fep_e2/event_strata.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e2/event_strata.py>)；[config/fep_e2_support_policy_registry_v1_1.json](<E:/codex work/大A交易/config/fep_e2_support_policy_registry_v1_1.json>)。

算法与数据结构结果：桶内每日期总权1/D，同日每样本1/(D*n_d)，Fraction精确权重；逆经验CDF分位数；固定L4→L3→L2→L1 backoff，支持度不按收益选。count按rows/dates/nonoverlap blocks/entities/episodes，完整分母缺失与TV诊断。

通过/保留依据：连续/类别/any-event不同口径，类别必须NONE，any-event不强行归一化；unsupported只diagnostic，不grant display/priority。首次事件stratum不以每日landmark替代。

未通过/未完整的原因：已接受scope只有FIRST_PREWATCH:T1；其他目标、事件、horizon/quality support未自动通过；descriptive频率不是个人预测概率。

综合裁决及差异解释：一致：FIRST_PREWATCH×ABS_RETURN:T1工程范围；Fraction日期平权、固定backoff/support。pooled/REENTRY/NEW_CONFIRMED不自动授权。

设计偏离与下一步：代码与当前工程统计合同抽查一致，无新hard backoff/weight错误；全样本/真实预测效力仍不可宣称。

### FEP-E3 · Interpretable Models / Calibration

线上报告§24：`MODEL_ENGINEERING_PASS；MODEL_EFFECTIVENESS NO`。本轮独立/综合：**工程范围保留；有效性/OOS不通过**。

设计合同：设计§90 FEP建模；protocol v1_1 FIRST_PREWATCH:T1 reconstruction scope。

核心代码/结构证据：[src/workbench_analysis/fep_e3/protocol.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e3/protocol.py>)；[src/workbench_analysis/fep_e3/models.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e3/models.py>)；[reports/fep_e3_r1/LOCAL_ACCEPTANCE_MATRIX.json](<E:/codex work/大A交易/reports/fep_e3_r1/LOCAL_ACCEPTANCE_MATRIX.json>)。

算法与数据结构结果：TRAIN/TUNE/CALIBRATION/OUTER按日期chronological且purge event_end/知识cutoff/shared episode；scaler/OOD只TRAIN fit，调参只INTERNAL_TUNE；Huber点模型与线性quantile分开。

通过/保留依据：固定feature manifest/无插补；rearrangement事前注册；回归calibration为diagnostic，不伪称概率校准；JOINT_OOD UNSET不能global_OOD_OK。

未通过/未完整的原因：已记录MODEL_EFFECTIVENESS=NO_INCREMENT、REAL_OOS=false。Outer按重构知识时间评估，不是历史当时可用模型。本轮模型fit重演因当前Python缺sklearn受限（IA-06）。

综合裁决及差异解释：一致：split/purge/train-only preprocess/calibration/OOD工程；有效性/OOS不是PASS，NO_INCREMENT/弱coverage应如实保留。

设计偏离与下一步：没有增益不是工程失败，也不阻断E5 baseline。新增概率分类/全horizon模型不在当前scope。

### FEP-E4 · Optional Tree Challenger

线上报告§25：`OPTIONAL ENGINEERING_PASS；vs E2 NO_INCREMENT`。本轮独立/综合：**optional diagnostic工程范围保留**。

设计合同：设计§90 optional challenger；E4 protocol和2026-10-06外部接受reconciliation。

核心代码/结构证据：[src/workbench_analysis/fep_e4/challenger.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e4/challenger.py>)；[config/fep_e4_challenger_protocol_v1.json](<E:/codex work/大A交易/config/fep_e4_challenger_protocol_v1.json>)；[reports/fep_e4_reconciliation_final_audit_r1/FINAL_CLOSURE_READBACK.json](<E:/codex work/大A交易/reports/fep_e4_reconciliation_final_audit_r1/FINAL_CLOSURE_READBACK.json>)。

算法与数据结构结果：exact复用E3 fold/feature/preprocessing/OOD；HGB固定seed、无early stopping外侧选择，试验次数bounded；数值树序列化与sklearn预测parity阈值1e-12。

通过/保留依据：seen Outer强制SEEN_OUTER_DIAGNOSTIC_ONLY/TEST_PREVIOUSLY_SEEN，失败trial保留，不把mixed表现选最好后声称冠军。

未通过/未完整的原因：CHAMPION=false、PROMOTION/priority/display未授权，无独立新OOS；sklearn private _predictors依赖版本锁，升级需重新parity。本轮4个实际tree parity用例因缺sklearn未完成（IA-06）。

综合裁决及差异解释：一致：challenger实现可通过而不成为Champion；Outer为见过的诊断复用，不能声称new real OOS。

设计偏离与下一步：当前optional工程保留，不能宣传模型优越/生产替代。

### FEP-E5 · Projection / Priority Shadow

线上报告§26：`ENGINEERING_COMPLETE_CURRENT_SCOPE；production/display/priority未授权`。本轮独立/综合：**canonical工程范围保留；真实display/priority未授权**。

设计合同：设计§90独立prediction ledger/API/CAS/rollback；R1R1C canonical metadata接受、full-chain033 hardening。

核心代码/结构证据：[src/workbench_analysis/fep_e5/projection.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e5/projection.py>)；[src/workbench_analysis/fep_e5/canonical_ledger.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e5/canonical_ledger.py>)；[src/workbench_analysis/fep_e5/metadata_binding.py](<E:/codex work/大A交易/src/workbench_analysis/fep_e5/metadata_binding.py>)；[src/workbench_db/migrations/v4_postgres/033_fep_signal_contract_integrity_v1.sql](<E:/codex work/大A交易/src/workbench_db/migrations/v4_postgres/033_fep_signal_contract_integrity_v1.sql>)。

算法与数据结构结果：slot/model固定选择cutoff与deadline，输出不许覆盖identity；transaction中prediction/run/receipt一起accept；revision parent精确匹配。canonical fep.*通过FK/registry trigger检查signal family/predicate；deploy CAS head与rollback不修改预测历史。

通过/保留依据：历史canonical reconstruction无live publication_id，由独立reconstruction authority绑定；旧parallel schema是显式历史工程范围，不能凭它打开生产。baseline可直接接E5。

未通过/未完整的原因：SHADOW_INFERENCE工程权限不是MODEL_DISPLAY/PRIORITY_USE。real FIRST_OBSERVED/OOS不足，CURRENT real source label gate未开放；PG负向测试本轮受环境限制。

综合裁决及差异解释：一致：canonical reconstruction authority、signal binding、slot/deployment/CAS与legacy isolation保留。上游IA-01/02有修复需要，不可将受影响outcome作为有效标签；本轮真实PG验收也不全。

设计偏离与下一步：既有工程接受可保留；新增全scope/实时预测须独立授权和证据。上游IA-01/02不关闭前，不能把受影响outcome投射成可靠标签。

## 6. 综合问题清单与独立关闭标准

下列10项独立于stage历史gate登记为OPEN_AUDIT_ONLY；原Current Audit canonical items照旧保留，本轮没有覆盖/关闭它们。不同性质不能混为“10个新算法bug”。完整反例与源行号见独立报告§6及audit_items.json。

| ID | 优先级/类型 | scope / 具体问题 | 综合处置与接受条件 |
|---|---|---|---|
| IA-01 | P1 / NEW_REPRODUCED_CONTRACT_DEVIATION | V4-15/16 Stock Forward绝对终点收益与路径质量隔离；区间内部不可得使已验证终点收益被整体清空 | 保持endpoint/T0坐标严格验证；仅endpoint无效时R_N不可用。内部缺口限制MFE/MAE/MDD并给路径reason。独立向量覆盖missing/invalid interior、有效endpoint、无效endpoint/T0、确认停牌、公司行为，持久化worker/readback同预期；accepted历史字节不改。 |
| IA-02 | P1 / NEW_REPRODUCED_INTEGRATION_AND_SCHEMA_DEVIATION | V4-15/16 Sector自身篮子Forward与字段语义；板块聚合路径不满足新结算identity；旧实现把close极值写入价格MFE字段 | 独立Sector篮子path及lineage合同定义每成员同basis到聚合指数的identity；有效篮子R正确、partial保持UNKNOWN而不重权，输出MFE_CLOSE/MAE_CLOSE；不得伪填股票high/low。n<2的股票relative-sector和Sector自身篮子分别验收。 |
| IA-03 | P2 / NEW_REPRODUCED_GENERIC_API_STATE_COLLISION | V4-15通用engineering SettlementRuntime；未证明当前durable real worker受影响；同一evaluation source的PENDING结果覆盖后续DUE幂等查询 | pending保持在独立due/planner层或冻结明确的状态revision规则，禁止覆盖历史outcome。验收同源pre-due→due、重复due、corrected source、first/latest、重启和持久化读取；保持设计唯一键，不简单把执行时间塞key破坏幂等。 |
| IA-04 | P2 / NEW_REPRODUCED_BOUNDARY_HARDENING | Forward数值输入边界；正式上游可达性未证实；有限但非法的实际价格仍被标OBSERVED | 明确上游保证与消费者check责任；actual-price不合法拒绝/降级，终值退市0走独立terminal路径且保留证据，不能拒绝合法terminal=0；验收raw OHLC包络，变换后价格允许域按最新合同独立冻结，不凭本报告任意定义。 |
| IA-05 | P1 / EXISTING_OPEN_CROSS_CUTTING_TEST_DEBT | 全仓回归与release证据；独立于各stage historical gate；默认pytest收集失败，全仓回归不能签绿 | 复用原global audit item，按失败node独立分类、baseline、正式supersession或修复，DB测试先验证隔离环境；保留退役写入口禁用；最终默认完整pytest无收集错误且失败有独立验收。禁止删测/静默ignore冒充绿。 |
| IA-06 | P1 / VERIFICATION_AND_DEPLOYMENT_EVIDENCE_GAP | 本轮FEP/阶段DB fresh-upgrade/权限/trigger及模型依赖实证复验；隔离库fixture/DSN和模型依赖不足，当前环境验证未完成 | 仅使用已确认disposable隔离DB，冻结空库/升级迁移列表，逐项negative insert/权限/CAS/rollback实证；冻结兼容模型runtime依赖并完成fit/parity，统一E/F TEMP及fixture安全根。记录当前source SHA；环境验证不自动grant生产。 |
| IA-07 | P2 / PERFORMANCE_VALIDATION_DEBT_NOT_PROVED_TIMEOUT | FEP E1 dataset/E3 purge、全市场Forward controls与整链负载；若干二次复杂度路径尚缺当前规模性能证据 | 按合同规模测elapsed/peak memory/output bytes；必要时预聚合population weights、partition边界和复用固定features，保留完全相同logical digest/selection/weight。 |
| IA-08 | P2 / HISTORICAL_PROVENANCE_ROUTING_DEBT | 旧head/validator exact身份；非当前active head损坏；历史引用需显式版本路由，不能与当前工作区字节等同 | 复用Current Audit已开放Git/production再审item，固定旧字节回放路由或新successor外审；所有current consumers绑定新scope的源码，禁止generic normalize/改历史SHA。 |
| IA-09 | P1 / NEW_CONFIRMED_TEST_ISOLATION_DEFECT | 全仓旧UI测试fixture与审计运行环境；独立于V4算法stage gate；旧浏览器测试直接启动实际工作区数据库的发布恢复入口 | fixture只使用已冻结disposable数据库/根目录，启动前对绝对路径fail-closed；测试显式选择无生产恢复入口的服务或隔离恢复，校验test前后production heads/jobs/artifacts无变更。重复全仓之前先完成安全环境验证；不修改TDX源。 |
| IA-10 | P2 / NEW_CONFIRMED_STANDALONE_CLI_BOOTSTRAP_GAP | DM01 R4/R4R1 daily直接脚本启动；非底层九组件数值算法；DM01脚本仅加入src，未满足kernel的scripts包导入 | 冻结支持的直接CLI/模块launcher及root+src环境bootstrap合同，在干净child环境验证--help和future-session WAIT/no capture；补实际已授权session的隔离入口向量，保留历史字节，依赖/入口修复不自动grant数据发布。 |

### 6.1 对线上“七项已修复”及“无新P1”的精确修订

**IA-01（Stock Forward）**：T0基准10、末端close11且identity/adjustment/T0 basis均验证，内部日无换基证明时，端点收益应独立保留`R_N=0.1`，MFE/MAE/MDD不可评估。当前successor先遍历全部rows验证，内部失败返回整份`ADJUSTMENT_UNKNOWN / R_N=null`。冻结contract的`ENDPOINT_RETURN_INDEPENDENT_IF_VERIFIED`与设计§46A提供独立oracle；这是额外丢弃合法端点收益，而非设计允许的“整段收益不可用”。worker实际调用该successor，但真实activation未开启，未证明已有真实污染。

**IA-02（Sector Forward）**：等初始权重两个成员10→11，成员端点均有效，Sector subject basket应有0.1绝对收益。旧settle聚合行未带successor必需的adjustment_identity，因此新runtime整段null；回退旧runtime虽返回0.1，却把basket close写成high/low并输出MFE_N/MAE_N，违反§49A.3仅允许板块MFE_CLOSE/MAE_CLOSE的字段语义。当前PURE_CORE_STOCK并未授权Sector，故严重级为对应能力P1，不夸大为全部Stock流P0。

两项均在已复用的历史settle和additive validator拼接处出现。原“非法affine拒绝”和“benchmark surface补齐”验收可保留，但它们不覆盖内部缺口/终点独立性与Sector生成行schema一致性。历史接受不能抹掉本轮精确证伪，也不因此全局重开00–15。

**IA-03/04**：PENDING→DUE同源key复用已复现，限定通用API，durable worker只入队due所以尚未证明其真实故障；负实际价被标OBSERVED已复现，但正式upstream raw producer有校验，本轮未证明该输入可从正式链传来。分别P2，避免人为升为P0/P1。

**IA-09（测试隔离）**：旧M12浏览器fixture实际启动工作区DB，serve的恢复逻辑可能更新真实jobs/重跑任务。本轮发现后中止。没有前DB精确指纹，不能证明零DB写，也没有证明发生具体重发布；tracked业务diff为空只支持代码未改。此项独立于V4金融算法接受，新的全仓复跑须先使用确认过的disposable环境。

**IA-10（独立CLI）**：daily脚本只加入src，而kernel导入scripts包需repo root。独立只读--help探针在继承环境exit1，显式root+src PYTHONPATH后exit0；确认入口bootstrap缺口，但没有执行capture/build/promotion，不否定底层九组件公式或data head。应明确launcher合同，不能将此条误归为缺第三方sklearn。

独立反例：[docs/evidence/full_scope_independent_20261006/semantic_probes.py](<E:/codex work/大A交易/docs/evidence/full_scope_independent_20261006/semantic_probes.py>)与[docs/evidence/full_scope_independent_20261006/semantic_probes.json](<E:/codex work/大A交易/docs/evidence/full_scope_independent_20261006/semantic_probes.json>)；都是SYNTHETIC_AUDIT_COUNTEREXAMPLES，不计REAL/PIT_OBSERVED/maturity/OOS样本。

### 6.2 仍开放的原canonical能力与生产债务

- A04_H21_CONSUMER=ACCUMULATION_CONTINUES，A04_HISTORICAL_AMOUNT_A=BLOCKED_AFFECTED_SCOPE；producer/consumer/历史能力分别验收。
- A03继续真实forward积累，A07与HISTORICAL_PIT_EFFECTIVENESS保留永久/预capture能力限制。
- R3C suspension/adjustment coordinates/D2 prior authenticity/event UNKNOWN、Git portability继续OPEN_EXTERNAL_REAUDIT。
- V4_12_REAL_OWNER、V4_13_REAL_OWNER、15真实cohort maturity和真实matured accepted-source settlement是NONBLOCKING_VALIDATION_DEBT；nonblocking不等于已经取得结果。
- A08 current scoped工程接受已传播，但production_blocking/permission限制仍有效。

这些不是本轮新增P1，也不被上面的10项登记替代。关闭须指定scope、exact authority、独立证据和acceptance，不能只由某stage tests通过或push自动关闭。

## 7. 数据结构、合同、来源与性能专项综合

Foundation 001–009保存namespace/publication/revision/prior session/source guards；010–012为lifecycle/date-valid identity；013–014 supplemental；015 Seed；016–020 Sector/Rotation；021/025 PREWATCH；022–024 State；026–027 Confirmation；028–033 FEP。FEP reconstruction不借live publication authority，signal registry有FK及语义guard，旧engineering ledger只诊断；真实Shadow以R24/queue v2/integrity v2 SQLite独立存储。静态schema吻合不证明本轮实际生产库部署。

18最新版namespace matrix在适用SQL集合下226项全部覆盖。初始广搜包含R23旧simulation schema得到242项；其中16历史表不是active migration源，已按正确范围重核验，不报新漏表。证据[docs/evidence/full_scope_independent_20261006/migration_namespace_coverage.json](<E:/codex work/大A交易/docs/evidence/full_scope_independent_20261006/migration_namespace_coverage.json>)。

4797条path/SHA/byte绑定中4777当前literal匹配、20旧引用与工作区不同；20对应15个独立身份都能找到Git原blob，当前CurrentStageAuthority及PREWATCH读取实际PASS。不能将历史差异判为active头损坏；也不能把Git可找回等同于所有旧CLI当前可运行。IA-08与已有Git/production再审项追踪明确版本路由。

M14在线增强不是V4-14 Replay。direct API仅请求时LATEST，collector capture禁用、能力gate三项persist=false，有界HTTP与按源UNAVAILABLE；现路径不落raw/row/batch或改local snapshot身份。旧batch reader不在当前direct API调用链。5项针对性测试通过，本轮不声称在线源重新实测可用。

FEP E1逐row扫描population权重、E3逐row扫描later集合及Forward逐signal controls复算存在二次复杂度风险；旧baseline runtime row count=0不支持当前全市场SLA。IA-07为性能证据债务，未测得timeout，不能写成已发生性能故障。

## 8. 本轮测试、实际执行与未完成验证

默认全仓命令：`python -m pytest -q --basetemp tmp/full_scope_audit_pytest_20261006 --junitxml=docs/evidence/full_scope_independent_20261006/pytest_full.xml`。退出1；collection error 1：`tests/upgrade_m14/test_online_batches.py:9`导入退役`_commit_raw_and_batch`失败。未进入全套测试，不能报全仓passed。既有GLOBAL-PYTEST item OPEN/NOT_ACCEPTED范围继续保留，不恢复被禁止的热榜落盘入口来迎合旧测试。

继续收集全仓复跑：加`--continue-on-collection-errors`。发现旧M12浏览器fixture启动实际工作区DB的恢复入口后中止，partial log最后84%，**无完整JUnit/无完整结果，计数不报告**。IA-09记录隔离问题及无法证明零DB写的取证局限。

随后显式选取阶段/FEP相关目录及root stage tests，见`stage_test_selection.json`与`run_stage_tests.py`：首轮**4014 passed / 243 failed / 38 errors / 281 skipped**，JUnit testcases=4576，耗时约982.16秒。这是**限定阶段测试复验，不是全仓绿**。没有把排除的legacy UI/upgrade/root范围计为通过。

首轮68项namespace失败由本轮runner配置触发：E盘basetemp不在`tempfile.gettempdir()`或固定engineering-fixture根下；不是已证明业务bug。按项目E/F政策把child TEMP/TMP与basetemp统一到`E:/codex_tmp/test_temp`，仅重验`test_r20r1r1_maturity.py`及`test_r20r1r2_dm01.py`，结果**72 passed / 1 failed / 0 errors / 0 skipped**，选择/环境见`namespace_recheck_selection.json`。首轮失败不删，复验不与首轮简单累加作独立样本，也不重签全仓绿。

M14针对性命令：`python -m pytest -q tests/upgrade_m14/test_hot_rank_api.py tests/upgrade_m14/test_hot_rank_capture_retired.py --basetemp tmp/full_scope_m14_direct_20261006 --junitxml=docs/evidence/full_scope_independent_20261006/pytest_m14.xml`。结果5 passed / 0 failed / 0 errors；使用fake fetchers，无真实在线重新抓取。

阶段测试失败导航（按异常文本生成hint，**不是自动认定代码bug或允许忽略**；逐node完整message/traceback、skip原因保留于`pytest_failure_inventory.json`）：

| 初步导航分类 | 条数 |
|---|---|
| MISSING_RUNTIME_DEPENDENCY | 5 |
| HISTORICAL_OWNER_STAGE_AUTHORITY_REJECTION_REQUIRES_TRIAGE | 72 |
| EXACT_IDENTITY_OR_BINDING_ASSERTION_REQUIRES_TRIAGE | 86 |
| ASSERTION_DIFFERENCE_REQUIRES_CONTRACT_SCOPE_TRIAGE | 44 |
| RUNNER_SUBPROCESS_ENCODING_FAILURE | 1 |
| STANDALONE_CLI_PACKAGE_BOOTSTRAP_FAILURE_IA10 | 1 |
| EXCEPTION_REQUIRES_CONTRACT_AND_ENVIRONMENT_TRIAGE | 4 |
| RUNNER_TEMP_NAMESPACE_GATE_REJECTION | 68 |

有失败/错误的模块统计（其余通过模块见`pytest_summary.json.by_module`）：

| 模块 | passed | failed | errors | skipped |
|---|---|---|---|---|
| tests.fep_e3.test_e3_contract | 30 | 1 | 0 | 0 |
| tests.fep_e4.test_e4_contract | 27 | 4 | 0 | 0 |
| tests.test_pre16_governance | 88 | 6 | 0 | 0 |
| tests.test_r17a_historical_governance | 11 | 2 | 0 | 0 |
| tests.test_r17b_promotion | 29 | 3 | 0 | 0 |
| tests.test_r17c_replay_contract | 47 | 2 | 0 | 0 |
| tests.test_r17r1_active_closure | 16 | 1 | 0 | 0 |
| tests.test_r18b_persisted | 0 | 2 | 0 | 0 |
| tests.test_r18c_oracle | 19 | 1 | 0 | 0 |
| tests.test_r18r1_canonical | 23 | 1 | 0 | 0 |
| tests.test_r18r1_owner_edges | 12 | 1 | 0 | 0 |
| tests.test_r18r1r1_canonical | 22 | 1 | 0 | 0 |
| tests.test_r18r1r1_consumption | 23 | 1 | 0 | 0 |
| tests.test_r19_promotion_contracts | 48 | 14 | 0 | 0 |
| tests.test_r20a_current | 11 | 1 | 0 | 0 |
| tests.test_r20e_persisted | 23 | 1 | 0 | 0 |
| tests.test_r20r1_scope | 48 | 3 | 0 | 0 |
| tests.test_r20r1r1_maturity | 2 | 33 | 0 | 0 |
| tests.test_r20r1r2_dm01 | 2 | 36 | 0 | 0 |
| tests.test_r21_promotion | 19 | 1 | 0 | 0 |
| tests.test_r22_contracts | 81 | 4 | 0 | 0 |
| tests.test_r22r1_contracts | 50 | 1 | 0 | 0 |
| tests.test_r23_runtime | 55 | 1 | 0 | 0 |
| tests.test_r23r1_runtime | 13 | 1 | 0 | 0 |
| tests.test_r24r1_a20 | 3 | 17 | 0 | 0 |
| tests.test_r24r1_authority | 16 | 15 | 0 | 0 |
| tests.test_r25_packet | 22 | 1 | 0 | 0 |
| tests.test_v4_12_authority_r2 | 28 | 2 | 0 | 0 |
| tests.test_v4_12_contract_freeze_r1 | 93 | 1 | 0 | 0 |
| tests.test_v4_12_multi_anchor_r12 | 24 | 2 | 0 | 0 |
| tests.test_v4_12_persisted_r11 | 14 | 2 | 0 | 0 |
| tests.test_v4_12_runtime_r1 | 122 | 1 | 0 | 0 |
| tests.test_v4_12_time_counter_r2_1 | 20 | 1 | 0 | 0 |
| tests.test_v4_13_r15_contract | 44 | 1 | 0 | 0 |
| tests.test_v4_13_r16a_runtime | 3 | 0 | 13 | 0 |
| tests.test_v4_13_r16b_runtime | 0 | 0 | 16 | 0 |
| tests.test_v4_13_r16c_publication | 5 | 6 | 0 | 0 |
| tests.test_v4_13_r16r1_repair | 36 | 0 | 9 | 0 |
| tests.test_v4_14_rollback | 25 | 1 | 0 | 0 |
| tests.test_v4_18_migration_contract | 23 | 1 | 0 | 0 |
| tests.test_v4_r14_governance_contracts | 17 | 3 | 0 | 0 |
| tests.v4_09.test_stock_prewatch | 178 | 1 | 0 | 0 |
| tests.v4_10.test_accepted_head_r1 | 0 | 9 | 0 | 0 |
| tests.v4_10.test_promotion | 0 | 7 | 0 | 0 |
| tests.v4_a03_a04_a07_r2.test_real_candidate_readback | 0 | 4 | 0 | 0 |
| tests.v4_a04_r3.test_independent_arithmetic_and_evidence | 1 | 1 | 0 | 0 |
| tests.v4_a04_r3.test_strict_source_admission | 0 | 2 | 0 | 0 |
| tests.v4_a08.test_repair_freeze_authority | 12 | 1 | 0 | 0 |
| tests.v4_dm01.test_official_daily_sources_v2 | 47 | 1 | 0 | 0 |
| tests.v4_dm01_promotion.test_accepted_chain | 23 | 2 | 0 | 0 |
| tests.v4_dm01_r3.test_real_authority_and_chain | 21 | 1 | 0 | 0 |
| tests.v4_dm01_r4.test_runtime | 23 | 2 | 0 | 0 |
| tests.v4_dm01_r4r1.test_lineage | 11 | 4 | 0 | 0 |
| tests.v4_parallel_scoped_consolidation_r3.test_clean_protected_representations | 14 | 1 | 0 | 0 |
| tests.v4_parallel_scoped_consolidation_r3.test_consolidation | 28 | 2 | 0 | 0 |
| tests.v4_parallel_scoped_formalization_r1.test_clean_representations | 18 | 1 | 0 | 0 |
| tests.v4_parallel_scoped_formalization_r1.test_scoped_acceptance | 49 | 9 | 0 | 0 |
| tests.v4_publication_reader_di_r1.test_explicit_views | 2 | 2 | 0 | 0 |
| tests.v4_registry_r3.test_formalization | 2 | 1 | 0 | 0 |
| tests.v4_registry_r4.test_entry | 1 | 1 | 0 | 0 |
| tests.v4_scoped_promotions_r3.test_scoped_readers | 17 | 15 | 0 | 0 |

实际skip原因：62项：FEP_E1_TEST_DSN required for real isolated PostgreSQL；2项：Explicit isolated canonical fixture required；214项：explicit canonical fixtures required；1项：Explicit disposable database DSN required；1项：symlink creation unavailable；1项：symlink creation is unavailable on this runner。其中缺canonical fixture/DSN的PG用例没有执行，不是DDL PASS；本轮没有记录到PG连接错误，不能把38个UNAUTHORIZED_V4_13_STAGE setup errors误写成PG errors。另有5项E3/E4模型测试因当前Python缺sklearn失败、1项DM01 subprocess因GBK解码失败；DM01独立CLI缺repo-root bootstrap的1项失败通过只读--help复验确认（IA-10）。历史PG fresh/upgrade外审只支持原scope，不当作本轮实际部署验证。旧frozen身份/当前supersession差异必须沿合同逐项审查，不因大量失败批量撤销历史接受；同时也不能无确认一概标成“预期失败”。

运行环境：Windows/PowerShell，Python 3.13.14；临时文件在工作区E盘tmp，TDX输入只读。独立semantic probes是synthetic反例、非real统计证据；测试成功不替代独立外审、真实样本、回滚演练或真实迁移验收。


## 9. 按证据排列的后续工作

| 次序 | 工作 | 完成依据 | 当前本报告是否授权执行 |
|---|---|---|---|
| 1 | 独立确认IA-01/02；冻结Stock路径隔离及Sector篮子successor修复范围 | 独立oracle、持久化worker/readback向量、exact新工件外审；历史字节保留 | 仅提供审计结论，未执行修复 |
| 2 | 独立处置IA-03/04及已有Forward向量/owner验证债务 | 状态revision与真实source边界证据，不用同实现做oracle | 未执行 |
| 3 | 先修测试环境隔离，再分类全仓收集/失败与PG fresh-upgrade验证 | disposable根/DB、安全前后保护证据、完整未隐瞒的结果；不恢复retired hot-rank capture | 未执行隔离改造/业务修复 |
| 4 | 复核最新版R25 packet与对应能力consumer/grant | 有效daily input、冻结权限、受影响实现关闭、current exact acceptance | 未授予First Real Shadow |
| 5 | 真实16 publication→17 readback→17G按capability稳定/Forward | 真实市场session、成熟outcome/rollback回执，不以replay凑数 | NOT_GRANTED |
| 6 | 18实际migration replay→19 Focus→20默认UI | 实现六接口/生产writer、幂等/reconcile/CAS/rollback、范围permission与独立外审 | NOT_GRANTED |
| 7 | 21持续真实积累→22最终独立审计；FEP独立真实FIRST_OBSERVED/OOS | canonical真实ledger、完整分母、独立封闭审计；FEP仍非主链总前置 | NOT_GRANTED |

线上提出“不要全局重做00–15、不要补造历史、未来按真实gate推进”的方向保留。需要修订的是“当前只剩真实时间/执行门”：本轮Forward具体实现问题和测试/DB证据也必须按受影响scope先处理，不能原样跳至First Real Shadow。

## 10. 审计交付验收与证明边界

本次阶段合同：READ_ONLY_CODE_ALGORITHM_CONTRACT_REVIEW_AND_SYNTHETIC_COUNTEREXAMPLES_V1。结果：36单元审计及交叉综合已交付；10项独立问题登记完成。项目release接受：**NOT_ACCEPTED_AS_FULL_RELEASE**；V4-22最终接受：**NOT_GRANTED**。下一阶段：对新项独立复核/范围修复和安全验证环境建设，须新的明确任务推进。

完整文件清单/语法覆盖不代表2819文件全部逐行或所有数据全量数学证明。本轮未重新全扫数百万TDX日线、重新抓在线源、测全市场实时负载或执行真实migration/恢复/cutover；PG未跑/skip/error不能写PASS。测试中旧真实库服务启动的局限按IA-09公开记录，不包装成纯隔离全仓成功。

Git交付只提交本轮2份MD及独立证据目录，保留起始用户FEP/design/artifacts/tmp未跟踪工作。发布记录见[docs/evidence/full_scope_independent_20261006/DELIVERY.json](<E:/codex work/大A交易/docs/evidence/full_scope_independent_20261006/DELIVERY.json>)；push不等于外部接受或阶段权限。
