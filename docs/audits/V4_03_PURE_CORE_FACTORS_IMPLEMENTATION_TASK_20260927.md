# V4-03 Pure-Core Factors Implementation Task

- 日期：2026-09-27
- 状态：TASK DEFINED / ENTRY AUTHORIZED / IMPLEMENTATION NOT STARTED
- 依据：V4-02 R6 最终外部验收；V4-03 入口已授权。

## 准入证据

- V4-02 accepted head：data/v4/V4_02_ACCEPTED_HEAD.json；状态 PASS_WITH_BSE_SCOPE_DEGRADED，外部验收 EXTERNALLY_ACCEPTED。
- 外部验收回执：reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json；SHA-256 见机器回执。
- 当前 accepted head：V4-03 ENTRY = AUTHORIZED。V4-02 Required Scope 为 SH_MAIN、SZ_MAIN、CHINEXT、STAR；BSE 为已接受的 optional/degraded 范围。
- 本任务只承接已接受的 V4-02 数据和合同，不重新实现 Calendar、Price Limit、复权链或特殊阶段。

## 已读取并绑定的合同

- V4.2.2 REV2：docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md，SHA-256 744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd。
- CORE_FACTOR_V1：REV2 §10A0。
- Field → Algorithm Contract Registry：REV2 §87A；实现前按字段展开 schema，登记类型、单位、producer、required/optional、时间、digest 和显示标签。
- 技术、横截面及 forward 窗口：config/v4_algorithm_contract_framework_v1.json，当前 contract id V4_ALGORITHM_CONTRACT_FRAMEWORK_V1，version 1.1.0。当前工作树文件 SHA-256 见机器回执。
- 阶段框架证据：docs/V4_00G_ALGORITHM_CONTRACT_FRAMEWORK_20260925.md；它确认窗口语义已冻结，但每个后续模块仍需独立 AST、参数实例、producer schema、正反向向量和适用 replay 证据。
- 合同哈希对账：V4-00G 旧回执记录的框架文件 SHA-256 为 53f42ab97a0af5f00a819f5285475728f9eb055e249f0524ef601974a5c7974a；当前已提交文件为 version 1.1.0，工作树 SHA-256 见机器回执。窗口条款与 V4-00G 冻结文字一致；后续实现、运行和验收回执必须绑定当前实际消费的精确文件哈希，不沿用旧 hash。

## 阶段目标和边界

按 REV2 §78，建立 V4-03 Pure-Core Factors 的版本化、可解释纯函数和生产计算路径，范围包括 CORE_FACTOR_V1、市场 native primitives、行业/板块 native primitives 的明确子集，以及 Core 历史市场参考路径。

首个工作包先冻结逐字段 scope 和 producer 映射，再产生机器可读算法合同与 parameter_set_id，然后实现正式计算。V4-03 不因入口已授权而自动获得规则或模块验收。

需要先解决的 scope freeze 项：

1. §78 把 sector native primitives 放入 V4-03；§87A 把 SECTOR_FACTORS_V1、SEED_WIDTH_V1、SECTOR_AXES_V1 的字段族登记在 V4-08。V4-03 先完成字段级映射，明确哪些是 V4-03 的基础输入/原语，哪些聚合、rank、seed、rotation 或资格输出留在 V4-08；不得自行扩大 V4-03。
2. REV2 §49A.1 的 MARKET_RELATIVE_REFERENCE_V1 是 Core 历史市场参考，供 rel_market、市场趋势、Market Regime 和历史 Core 比较。§49A.2 的 FORWARD_MARKET_BENCHMARK_V1 使用冻结 T0 固定篮子并消费未来路径；它属于 forward outcome 路径，不纳入 V4-03，也不得将两者共用身份。
3. 对 registry 中 V4-03 / V4-04 共用字段，V4-03 提供纯 primitives；V4-04 才组装全市场 stock profile，不在本阶段提前交付画像资格。

## 计算与窗口合同

- CORE_FACTOR_V1 输入使用同一观察日、同一已验证仿射坐标的 OHLC；amount/volume 按 REV2 定义保留原始单位。内部全精度计算和比较，只在展示层舍入。
- 零分母和必需输入不足按字段合同返回 UNKNOWN；不以 epsilon、填零、前向填充或缩短窗口伪造有效值。每个输出保存 UNKNOWN 原因和实际可用日期。
- TECHNICAL_BAR_WINDOW_V1：最近 N 根已验证实际证券 bar，可跨过本地确认停牌且不消耗 bar；未知或非停牌缺口令相关字段 UNKNOWN。输出 window start/end、calendar span、actual_count、suspended_count 和 window identity；新股不得缩短窗口。
- CROSS_SECTION_SESSION_WINDOW_V1：全体证券固定同一市场会话起止日，端点不为停牌或缺失而平移。retN 端点停牌/缺失为 UNKNOWN；中间确认停牌只留质量注记；未解释缺口为 UNKNOWN。volN 使用 N 个相邻市场会话收益；停牌间隔、缺失或非正价格使整个窗口 UNKNOWN，不跳日、不年化。RPS 使用同日、PIT 可评估 Universe，n<2 为 UNKNOWN，并记录 count/coverage。
- FORWARD_SESSION_WINDOW_V1 是固定 T+N 市场会话语义，仅供后续结算消费者；V4-03 不生成未来 outcome，也不延长停牌 horizon。
- 市场/板块横截面必须绑定历史 Universe snapshot、会话、调整坐标和输入 source digest；禁止以当前存活证券替代历史 PIT Universe。

## 工作包

1. Scope freeze：将 CORE_FACTOR_V1 和 §87A 的 V4-03 字段逐项列出，标明输入、producer、窗口类型、单位、缺失语义、参数集、PIT 身份、consumer 和阶段归属；关闭上述两个跨阶段映射问题。
2. Contract generation：为每个算法创建独立 versioned contract、AST/schema、parameter_set_id 和可复现 digest。不得只登记算法名称或复用 V3 registry 宣称完成。
3. Pure-core stock primitives：实现明确归属 V4-03 的 ret/vol、MA/TR/ATR、HHV/LLV、slope、amount/volume ratio、RPS、market-relative primitives 等；每个字段按各自 window mapping 计算，不让技术窗口和 cross-section 窗口共用无语义 rolling helper。
4. Market primitives：按 MARKET_RELATIVE_REFERENCE_V1 形成历史市场参考收益/路径和 MARKET_REGIME_V1 所需底层字段；保存 universe、coverage、source 和 coordinate identity。不得将 endpoint 均值误称为日再平衡路径累计收益。
5. Sector primitives：只实现 scope freeze 明确落在 V4-03 的 native inputs/primitives；sector qualification、Seed/Rotation、正式 sector ranking 与 §87A 指向 V4-08 的字段留给 V4-08。
6. Publication：先写 TDX root 之外的 versioned staging artifact，以原子方式发布；不改变 V4-02 accepted input identities，不在此阶段启用 scanner 或 formal trading consumers。

## 验收门

- 每个消费字段均有唯一有效的 contract_id、parameter_set_id、schema、producer、时间语义、质量语义、window identity 和 digest；字段映射与 REV2 §87A、§78 一致。
- 正反向 golden vectors 覆盖基本计算、边界、同值排名、零分母、短历史、确认停牌、复牌、真实缺口、非正价格、新股历史不足和复权坐标身份。
- 对技术窗口和横截面窗口使用彼此独立的固定输入样例，验证停牌时窗口端点和 actual/suspended counts，不允许依赖共享的未声明索引约定。
- PIT market/sector membership、required board scope、coverage、UNKNOWN inventory、input/output digest、scanner/factor/trading run count 和 TDX-root write count均可审计；BSE 降级不得污染 Required Scope。
- 独立 postcheck 重新消费 staging 输出与 accepted inputs，逐字段核对结果、质量及 digest。测试通过是必要证据之一，不单独构成 release readiness。

## 明确不在本任务内

- V4-04 的完整全市场 stock profile 与画像状态；V4-06 Turnover/Supplemental；V4-08 的 sector/rotation qualification 与排名输出。
- V4-15 Forward settlement、fixed-T0 market/sector benchmark、matched controls、MFE/MAE/MDD。
- Scanner、正式资格筛选、自动交易、概率或收益承诺。
- 重新打开已接受的 V4-02；只有新的可复核下游反证才能建立独立 audit item。

## 独立审计项保持开放

REV2 合同复审仍由 docs/audits/V4_2_2_CONTRACT_REAUDIT_20260925.md 独立跟踪（文件 SHA-256 见机器回执）。V4-02 外部验收只关闭 V4-02 阶段 gate，不代表复审中的跨阶段字段映射、模块 AST、benchmark/control、Amount A 权限等问题已关闭。V4-03 只对其自身合同和验收范围签发结果；涉及其他阶段的发现继续按原 audit item 的独立范围和接受条件处理。

## 当前结果和下一步

本次只完成准入核对、合同读取和任务定义；未实现算法、未发布因子、未运行测试或 scanner，也未写入任何 TDX 根目录。

任务定义结果：TASK_DEFINITION_PASS / V4-03_ENTRY_AUTHORIZED / IMPLEMENTATION_NOT_STARTED。
下一阶段：V4-03_SCOPE_FREEZE_AND_ALGORITHM_CONTRACTS；先冻结逐字段边界并生成机器合同，再进入纯函数实现与独立验收。
