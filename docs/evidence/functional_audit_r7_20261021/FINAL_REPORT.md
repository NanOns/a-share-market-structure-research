# V4 R7 功能核心缺陷闭环报告

- 日期：2026-10-21（Asia/Shanghai）
- 基线分支：`codex/v4-unified-development`
- 冻结提交：`5af33dfa4c7b58f78eb3508f6480d2ec5dd116ff`
- 候选上下文：`2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df`
- T0/行情上限：`2026-10-14`。全部 10/12–10/14 行情来自后验重建，均标记 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`production_admission=false`、`NON_PIT`。
- 最新适用升级文档：`docs/upgrade/V4_R8_UNIFIED_SOURCE_REPAIR_SPEC_R1_20261015.md`。R7 只读候选连续修复，没有进入后续受门禁阶段。既有阶段 0 记录为 `DEGRADED_PASS`；本轮没有重新宣称扫描器或发布门通过。

## 结论摘要

| 项目 | 结论 | 说明 |
|---|---|---|
| P0-01 市场压力 / Priority 来源版本缓存 | PASS（候选） | 缓存键由 token 加来源身份构成，身份覆盖生产者、参数、Core、Market、限价 Owner、原始来源及所有匹配回执 SHA。相同来源第二次命中；同 token 的来源版本更换会新建缓存项。 |
| P0-02 市场宽度与参与度 | PASS（候选重建） | 从已绑定的真实历史、市场、Core、成员输入重算 10/12、10/13、10/14；旧 Market Owner 轴值逐日一致。综合市场环境仍不可评估，因为趋势轴没有重算。 |
| P0-03 D2 `frozen_invalidation` | PARTIAL | 新增可执行、失败关闭的候选检测器和 14 个边界向量；历史 Owner 只有 `NOT_IMPLEMENTED`，无冻结价位和坐标合同，故 875 个既有 episode 必须保持 UNKNOWN，不能作真实 TRUE/FALSE 判定。 |
| Focus 主资格原因 | PASS（原因互斥） | 3,247 个 Focus 身份完整映射，互斥原因数合计 3,247；D0/D2 原始资格状态未被改写。 |
| Priority 与板块生命周期独立复核 | PASS（数值样本） | 20 个真实板块样本全部与独立 Oracle 一致；完整 Priority 可排序 141/400 板块、967/967 个股。 |
| 12 项身份缺口 | 仍隔离 | 10/14 成员快照中 12 个代码共 162 条成员关系全部 `UNMAPPED_QUARANTINED`，`security_id=null`；未补造身份。 |
| 页面 / API 回归 | PASS（候选页） | 28766 Focus、Priority 候选页显示新字段和实际结果；一处页面仍写“宽度与参与度未知”的旧文案已修正并回归。 |

本轮没有改写候选历史行、正式 Head、正式 PostgreSQL 数据或 28765 服务；没有扩大行情日期，没有使用外部复权服务、未来行情、概率性结论或交易自动化。

## 代码变更与实数结果

### 1. 市场压力与 Priority 缓存来源版本

修改 `src/workbench_analysis/r6_candidate_market_stress.py` 与 `src/workbench_service/core_product_bff_r1.py`：

- 新增 `R7_CANDIDATE_MARKET_STRESS_CACHE_V2` 身份。候选 token 相同但输入内容或回执不同不会复用旧压力结果；每项源文件先按绑定 SHA/字节数核对，路径逃逸和绑定不符均失败关闭。
- Priority 行缓存与市场风险来源缓存拆开。Priority 缓存读取时单独取得市场风险，避免一个 token 下的旧 Priority 缓存冻结旧市场来源。
- 28766 API 首次风险请求 `cache_hit=false`、身份 `efeae759ecaeaacd70e894b0976160d95cf802828458f8a37ef344a1c3e03d63`；同 token、同来源复读 `cache_hit=true`。回归测试以相同 token 的来源身份 A→B 验证 A 首次冷缓存、A 重复命中、B 再次冷缓存，留下两个版本缓存项。
- 失败反例：历史限价回执可能有多份；实现只接受来源、内容 SHA、大小和统计等价的重复回执，冲突重复不会被任选。被替换但绑定 SHA/大小未同步的 Owner 会在 `_checked` 拒绝。

### 2. 市场宽度、参与度与 Priority

从绑定的市场 Owner `history.jsonl.gz`、历史成员、比较日 Core 和本日 Core 计算，统计不改变压力 Owner 原值：

| T0 | 压力 | 宽度 | 宽度可计算 | 参与度 | 参与度可计算 | 综合环境 |
|---|---|---:|---:|---|---:|---|
| 2026-10-12 | LOW | DETERIORATING (-0.237317) | 5,204 | NORMAL (0.824059) | 5,203 | UNKNOWN：趋势轴未重算 |
| 2026-10-13 | LOW | IMPROVING (0.221667) | 5,206 | NORMAL (0.927898) | 5,203 | UNKNOWN：趋势轴未重算 |
| 2026-10-14 | LOW | DETERIORATING (-0.398579) | 5,206 | THIN (0.756886) | 5,205 | UNKNOWN：趋势轴未重算 |

- 宽度合同公式：`MEAN(SIGN(RET1_T)-SIGN(RET1_T_MINUS_3))`；参与度：已观测 `Core.amount_ratio20` 中位数。10/12 使用数据中有证据的 9/30 比较日 Core 成员集；10/13–10/14 按逐日绑定窗口计算。未计算值不填 0。
- 10/12、10/13、10/14 每日计算出的两个分类与各自绑定的历史 Market Owner 轴分类一致；10/14 限价覆盖率 0.993493，已知 5,191/5,225。原始日线和回执均为 10/20 后验采集，不能作为 PIT。
- 旧 R6 页面称“宽度轴和参与度轴未知”。第一次候选 Priority 页回归发现 API 已有实值但页面仍显示未知；修改 `app.js` 后重新载入 28766，页面显示 `宽度：恶化（-0.399，5206 可计算）；参与度：偏低（0.757，5205 可计算）`。页面继续明确“综合环境仍不可评估，趋势轴未重算”。
- Priority API：股票 `READY`，967/967 可排序；板块 `READY`，141 可排序、259 行不可排序。独立页示例第一只股票常山北明 `SZ.000158`，分值 11.741，排名理由逐项显示。

### 3. D2 冻结失效检测

新增 `config/v4_r7_frozen_invalidation_contract_r2.json` 和 `src/workbench_analysis/r7_frozen_invalidation_v2.py`，并接入 `src/workbench_analysis/r6_reason_attribution.py` 与 Focus UI：

- 合同 `FROZEN_INVALIDATION_CONTRACT_R2`（2.0.0，候选、未接纳）要求 prior episode/合同、冻结失效价与价格坐标、T0 实际收盘价、日期一致和有效源 SHA。相同坐标下 `close <= frozen_level` 为 TRUE，否则 FALSE；缺失或矛盾一律 UNKNOWN；没有 prior episode 为 NOT_APPLICABLE。
- 14 个向量覆盖无 prior、episode ID 缺失、合同缺失/不支持、等于/低于/高于边界、阈值/收盘缺失、坐标不匹配、非实际行情、非法数值和坏 SHA。等于与低于阈值产生 TRUE，高于产生 FALSE；未知证据不会变成 FALSE。
- 真实数据反例：10/13 D2 Owner 中 5,225 行的冻结失效来源都是 `V4_12_EPISODE_INVALIDATION_NOT_IMPLEMENTED` / `UNKNOWN`，source payload 为空；其中 875 行有 prior `episode_id`。10/14 当前 D2 Owner 5,225 行同样没有冻结价位/价格坐标合同；875 个 prior episode 的 `invalidation_contract_id` 均缺失或不受支持。原始 10/14 D2 Owner SHA-256 为 `5e466ef0bcb3fab050fdedea4c94a12943e0503c825c8961e16f2f85cb09a8bc`。
- 接入结果：Focus 3,247 行的 R7 候选失效分类为 NOT_APPLICABLE 2,372 / UNKNOWN 875；对 D0 为 TRUE 且 D2 UNKNOWN 的 80 个先前 episode，互斥主原因为 `D2_FROZEN_INVALIDATION_UNKNOWN`。没有候选历史失效价位可支持真实重算，所以本项为 PARTIAL；需要上游版本化 episode 生产者在 episode 建立时冻结失效位与坐标，再使用有 SHA 的实际 T 日 bar 评估。当前合同禁止历史回填与生产准入。

### 4. Focus 互斥资格原因

- Focus Owner 的 3,247 个实体分别全部映射到 10/14 D0 与 D2 Owner，成员来源为 10/09 最新成员回算，不是严格 PIT。D0 145 TRUE、3,102 UNKNOWN；D2 65 TRUE、3,182 UNKNOWN，与旧资格状态一致。
- 新增 `R7_FOCUS_PRIMARY_REASON_V1`，按固定优先序为每个 Focus 实体分配一个原因：`D0_UNKNOWN=3,102`、`D2_FROZEN_INVALIDATION_UNKNOWN=80`、`FIRST_CAPTURE_NOT_PROVEN=65`，共 3,247。未把 UNKNOWN 变成 FALSE，也未改变 D2 判定。
- Focus API `GET /api/v4/focus?context_token=…&trade_date=2026-10-14&limit=1` 返回 HTTP 200 / READY；上下文日期 10/14，总数 3,247，D0/D2 映射均 3,247。页面显示上述原因数、冻结失效状态以及来源不足的事件观察。

### 5. Priority / 生命周期独立复核

- 使用现有 `scripts/audit_sector_lifecycle_reconstructed_r1.py` 独立按 10/8、10/9、10/12–10/14 五个会话重建 400 个唯一板块。成熟度可判 242/400（DEVELOPING 22、EARLY 9、MATURE 1、NONE 210、UNKNOWN 158）；健康度可判 230/400（DAMAGED 113、NONE 4、WATCH 5、WEAKENING 108、UNKNOWN 170）。
- 独立真实样本 20/20 匹配；审计器报告 `independent_oracle_acceptance=PASS`。候选生命周期非 `AS_RECORDED`、非 PIT，生产准入 false。
- Priority 复核只评估已具备输入的候选，板块 141/400 可排序、259/400 不可排序；股票全体 967/967 可排序。缺源行维持不排名，仍可通过页面“候选规则、排除分母与来源 SHA”查看依据。某些板块原因显示 `ROTATION_ROTATION_FAILED`，不纳入实值评价之外的推断。

### 6. 身份缺口

使用 10/14 候选成员快照及其绑定 identity artifact 对任务卡 12 个代码逐一核对；12 项全部仍为 `UNMAPPED_QUARANTINED`，每条 `security_id=null`，总计 162 条成员关系。identity artifact 中没有这些代码的可确认证券实体。继续隔离，不推断名称、上市日或稳定证券 ID；既有 TDX 源根目录只读，未修改。

## 失败反例、API 和页面验收

- 页面反例：候选市场 API 已输出实际宽度、参与度轴，但旧 Priority 页仍统一显示“Breadth 与 participation 未知”。修正文案与数据绑定后，28766 页面显示分类、数值和有效样本数；复合环境依旧显示 UNKNOWN。
- 实际 D2 反例：任取一个带 prior episode 的 Focus 实体，旧数据的 `frozen_invalidation` source payload 为空、producer `NOT_IMPLEMENTED`，且无冻结价/坐标。候选检测器输出 UNKNOWN / `PRIOR_INVALIDATION_CONTRACT_MISSING_OR_UNSUPPORTED`，没有产生伪 TRUE/FALSE。
- 缓存反例：相同 token 但来源身份 A→B 不共享 Priority 市场风险项；相同 token、同来源的重复 API 请求命中同一身份。SHA/字节数不符的绑定拒绝重用。
- API：Focus 返回 HTTP 200 / READY / 3,247 行；Priority sectors 与 stocks 返回 HTTP 200 / READY，分别 141 和 967 可排序。候选标记均为 `CANDIDATE_RECONSTRUCTED · NOT_ACCEPTED · NON_PIT`。
- 页面：通过 Codex 内置浏览器实开 `http://127.0.0.1:28766/v4/research/focus` 和 `/v4/research/radar/priority?view=candidate`。Focus 页面显示 3,247 条和互斥原因；Priority 候选页显示 10/14 宽度、参与度、生命周期覆盖、分母、前 10 板块/前 30 个股排序及原因。页面未将候选表达为正式接受结果。

## 验收、运行状态与下一步

- `pytest -q tests/test_v4_r6_risk_priority.py tests/test_sector_lifecycle_reconstructed_v1.py`：12 passed（basetemp 在 `G:/codex_tmp/test_temp/r7_core_final`）。
- 修改模块 `py_compile`、Priority 页面 `node --check`、`git diff --check` 均通过。
- 28766 预览运行在 `127.0.0.1:28766`，候选 T0=10/14；28765 未监听。PostgreSQL 仅现有 `127.0.0.1:5432`，本任务未写入数据库、未启动写进程。正式 Head 未更改。
- 保持未完成：D2 的真实失效判断依赖上游新增冻结价位与坐标来源；趋势轴依然未重算；身份 12 项需新的权威身份来源。只有补齐来源并再次独立复核后，才能将对应结论从 UNKNOWN/隔离升级。本报告、代码推送和测试均不构成外部验收、正式 Head 接受或 28765 部署许可。