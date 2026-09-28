# V4-03 第二轮云端外部验收审计记录

- 审计目标提交：`1636838fdf7b130fa97a01b778fc1a05a2f9bb07`
- 云端会话 ID：`6aba4b29-191c-83ee-b63c-22c1b16e5dd8`
- 审计性质：云端静态审计；未在云端重跑本地冻结数据
- 结果：`EXTERNAL_ACCEPTANCE_BLOCKED`；V4-04 不放行

以下为云端模型中文原文：

## 独立外部验收结论

对精确提交 [`1636838fdf7b130fa97a01b778fc1a05a2f9bb07`](https://github.com/NanOns/a-share-market-structure-research/commit/1636838fdf7b130fa97a01b778fc1a05a2f9bb07) 的结论是 **`EXTERNAL_ACCEPTANCE_BLOCKED`**，**V4-04 不放行**。

该提交的变更清单确实包含本轮 AST 数值执行器、47 份合同及夹具、全历史截止日候选脚本、独立复核脚本、测试和 R2 回执。分支 `codex/v4-system-reform` 上也能读取与该提交相同的 R2 处置文件。不过，我没有取得分支 HEAD 的独立 SHA 回执，因此只能确认目标提交存在、产物在该提交中，不能把“当前 HEAD 精确等于目标 SHA”作为已验证事实。

### 按严重程度排列的发现

| 严重度 | 审计项 | 实际证据与判断 |
|---|---|---|
| **阻断** | **C05：板块与市场轴** | [`V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R2.json`](https://github.com/NanOns/a-share-market-structure-research/blob/1636838fdf7b130fa97a01b778fc1a05a2f9bb07/reports/v4_03/V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R2.json) 明列没有已接受的历史板块成员输入和板块全市场物化；`market_path_candidate_sha256` 为 `null`。[`V4_03_MARKET_REFERENCE_CANDIDATE_R2.json`](https://github.com/NanOns/a-share-market-structure-research/blob/1636838fdf7b130fa97a01b778fc1a05a2f9bb07/reports/v4_03/V4_03_MARKET_REFERENCE_CANDIDATE_R2.json) 的状态为 `NOT_COMPUTED_HISTORICAL_DAILY_CHAIN_PENDING`、`forward_benchmark_published=false`。三个截止日市场参考值不能代替完整历史市场轴。**未修复。** |
| **阻断** | **C03：全历史与 PIT** | [`run_v4_03_core_frozen_diagnostic.py`](https://github.com/NanOns/a-share-market-structure-research/blob/1636838fdf7b130fa97a01b778fc1a05a2f9bb07/scripts/run_v4_03_core_frozen_diagnostic.py) 的 `--full-history` 将计算输入从末尾 200 日扩至截止日前全部日历；回执记录 786 日、3,989,856 条输入、截止日 5,222 条输出。但脚本仍只生成 **2026-09-24 一个截止日**的字段行，没有逐历史 T 的首次可用日、当时可见版本及发布链回放。回执自身也写明 `cutoff only; historical daily first-availability replay pending`。**200 日截断已修；阶段所需的历史 PIT 未修。** |
| **阻断** | **C04：前序 RPS 血缘** | [`run_v4_03_full_scope_candidate.py`](https://github.com/NanOns/a-share-market-structure-research/blob/1636838fdf7b130fa97a01b778fc1a05a2f9bb07/scripts/run_v4_03_full_scope_candidate.py) 在运行中用历史快照、日线和 `rps_midrank` 计算前序 RPS，并将摘要标为 `DIAGNOSTIC_NON_PIT_RECOMPUTED`；回执进一步标为 `NOT_PREVIOUSLY_ACCEPTED`。复核脚本重复从冻结输入重算，证明候选之间可比对，**不能证明前序 RPS 曾以历史 T 的身份独立产出、接受和发布**。未修复接受链。 |
| **高** | **B01：94 向量的证明范围** | [`algorithm_contract_numeric_v12.py`](https://github.com/NanOns/a-share-market-structure-research/blob/1636838fdf7b130fa97a01b778fc1a05a2f9bb07/src/v4/contracts/algorithm_contract_numeric_v12.py) 确实逐合同解释执行 AST，并比较结果；不只是结构校验。[`build_v4_03_algorithm_contracts.py`](https://github.com/NanOns/a-share-market-structure-research/blob/1636838fdf7b130fa97a01b778fc1a05a2f9bb07/scripts/build_v4_03_algorithm_contracts.py) 用另一套 `independent_core` 等逻辑构造预期值，具备一定实现分离。但每字段仅一个 `OBSERVED` 和一个 `UNKNOWN_INPUT`：后者在执行器中通过**清空全部 history 与 relative 输入**实现，容易得到 `None`，未覆盖局部缺日、停牌穿越、零分母、复权身份切换、窗口边界、并列排名、集合成员变化及 UNKNOWN 传播位置。94 是执行次数，不等于 47 个算法含义及未知输入边界已充分覆盖。**“AST 从未数值执行”的缺陷已修；完整语义验收仍不能据此宣布通过。** |
| **高** | **C04：独立摘要复算的边界** | [`independent_v4_03_full_scope_postcheck.py`](https://github.com/NanOns/a-share-market-structure-research/blob/1636838fdf7b130fa97a01b778fc1a05a2f9bb07/scripts/independent_v4_03_full_scope_postcheck.py) 有自己的核心字段与相对字段计算、`input_digest` 和 `window_identity` 生成路径；[`R2 postcheck 回执`](https://github.com/NanOns/a-share-market-structure-research/blob/1636838fdf7b130fa97a01b778fc1a05a2f9bb07/reports/v4_03/V4_03_INDEPENDENT_POSTCHECK_R2.json) 报告 5,222 行 × 47 字段、身份不匹配为零。这支持**候选内部一致性**，但复核与生产都取同一冻结输入及约定，且回执是仓库内运行结果；本轮云端未独立重跑冻结数据、压缩产物 SHA 或逐行数值。不能将仓库自报的 `PASS` 升格为外部实测 PASS。 |

### 已修复与未修复

- **已确认代码层修复：** B01 增加了真正执行 `RULE_AST_V2` 的解释器、固定夹具和篡改预期值测试；C03 的截止日 Core 候选改用全部 786 日输入；C04 增加了覆盖 47 字段摘要的独立复核实现。R2 回执也如实使用 `DIAGNOSTIC_NON_PIT`、`NOT_STAGE_ACCEPTANCE` 等限定。
- **仍未满足阶段合同：** 逐历史 T 的首次可用性与 PIT 发布链、已接受的前序 RPS 产物、已接受的历史板块成员输入与板块原生产物、完整市场轴和最终发布签收。`AGENTS.md` 第 7 条明确要求阶段合同、证据和验收结果，且**测试本身不能建立发布就绪性**；R2 处置文件也明确维持阻断。

**审计能力边界：** 本轮通过 GitHub 精确提交读取了代码、配置、测试及回执，属于静态审计。云端没有执行本地冻结的 V4-01/V4-02 数据流水线，因此 786 日输入的实际内容、5,222 行候选的逐行计算、独立复核结果及压缩文件哈希均为“审查了实现和回执”，不是我已独立运行验证。基于已能定位的门禁缺口，即使暂采信这些运行回执，V4-03 最终验收仍须阻断，V4-04 仍不得入场。

