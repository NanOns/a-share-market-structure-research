# 大A V4｜整体审计后 A–E 执行轮独立外审 R1

- 审计时间：2026-10-10，Asia/Shanghai；市场休市，下一个预计交易日为 2026-10-12。
- 仓库：`NanOns/a-share-market-structure-research`，分支 `codex/v4-fp14-r2-repair`。
- 冻结远端 HEAD：`d7b19feabc8e17ca4948bfdef38047f10fd6f97c`；上轮基线 `c0b9903fe596c1884c04f5529d6699034548850e`；领先8提交。源码证据锁定 SHA `6bd8c50d66c2c0847bca4addc3f646dedde4f7be`，此后1次提交仅增加交付回读及其脚本。
- 最新 Drive 开发报告：《V4_NEXT_STAGE_AFTER_OVERALL_AUDIT_EXECUTION_RESULT_20261010.md》，文件 ID `18GYSgQxob5fLzdoTtcbkeWLEWNky_HWh`。
- 使用原合同：V4.2.2 REV4 §78/§90、`AGENTS.md`、上轮总调度卡《V4_NEXT_STAGE_EXECUTION_MASTER_AFTER_OVERALL_AUDIT_R1_20261010.md》。
- 保护运营 Head：`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；严格 Head：`38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`。本轮开发者读回声明前后未变；未获新用户授权重启 `28765`。

## 一、唯一裁决与证据限度

**总体 `EXTERNAL_ACCEPTANCE_BLOCKED`；本轮工程 `A/B/C=PASS_SCOPED_EVIDENCE_REVIEWED`；D=`PASS_SCOPED_HTTP_MODULE_ONLY/BROWSER_PENDING`；E=`CORRECT_HOLD`。不代表V4-00～22全部重开，也不撤销此前具有独立证明的分能力阶段性成果。**

本审计实际通过连接器读取远端HEAD差异、新源码、单测源码、结果/账本/源码映射、部分运行原件目录和Drive报告；不直接连接用户本机 `127.0.0.1:28765`、未在Windows/G盘自行执行pytest或重算全部41,790/800条数值。因此开发者的 `87 Python + 5 JS PASS`、68项HTTP、独立RS/q20 oracle 仅可按冻结证据范围评估，不写成外审者亲自现场全量PASS。用户真实10/12盘后Source尚未产生，不能以合成夹具证明实际新日首获。

## 二、逐包证据与意见

| 包 | 本轮可确认变化 | 外审裁决 | 必须保留的限制 |
|---|---|---|---|
| A State Publisher→First-Observed | 新增 `src/workbench_analysis/state_publisher_bridge_v1.py`；实际gzip→quarantine→桥接→FirstObserved→完整ledger/提取→合成Grant preflight；23项定点测试；35条固定/随机 TRUE 原target/AST抽样一致 | 工程范围化通过 | 真10/09仍 `RECONSTRUCTED_RESEARCH_ONLY`，`source_owner_admitted=false`、`observed_count=null`；缺真实当日Membership/Model/Event/Benchmark/独立审核。|
| B 下一T0预检 | 新 `next_t0_identity_preflight_v1.py` 并修改 `operational_daily_executor_v1.py`；实际来源保存、差异字段诊断；12项隔离测试；28768无worker只读加载、已关闭 | 预检通过，不等于新日全链发布通过 | 主DD仍严格依赖上一Head身份集合，一旦新增/更名无法发布，必须区分身份变化与provider故障。|
| C D2 Episode | 新 `src/sector/episode_genesis_candidate_v2.py`；creation-bound成员、失效合同、场景优先级、V4-15 due plan；49项相关工程测试；研究 rank/RS数值对照 | 候选工程通过 | 仍没有真实Genesis及日更Publisher/Owner准入；9/24 A05黄金与10/09回建身份隔离；WARM各分支的Amount H21不能绕过。|
| D FP13 | 68项已有生产只读HTTP、六入口数据、D/W/M×RAW/QFQ、错误Token409/未来400、5项JS模块测试 | HTTP及语义范围化通过 | 真实1366/1920浏览器在该轮被客户端拦截，不可写成两视口UI Pass。Forward/FEP/Replay仍部分 `SOURCE_INCOMPLETE`，Stock timeline `EMPTY_VALID`。|
| E FEP | 保留当前模型正式门关闭、不伪造Forward统计和成熟样本 | HOLD合理 | Registry / Prediction Owner / fit labels /可信CAS+Grant未产生；不阻塞已可用Native/研究。|

## 三、需要订正的具体工程与治理问题

### AUD-A01：声明性Review文档不是可信独立审核机构，P0

`state_publisher_bridge_v1.bridge()` 接收任意哈希绑定的本地 `admission_binding`，检查文档的 `contract_id/decision/reviewer_role/sources/T0` 与时钟；若满足即把候选 `evidence_class` 转成 `PIT_OBSERVED` 并进入隔离 `freeze_first_observed()`。该检查能够检验**自洽性和字节绑定**，不能证明review原件来自外部已接受的身份/签发Authority或该角色持有真实权限。开发报告也明确“reviewer_role文字和合成Grant不构成生产认证”。

**风险限定**：当前返回的 `production_write_authorized=false`，FirstObserved工程候选不是正式Writer授权，尚未观察到真实Head被提升。不能因此判定已发生生产越权；但不能以本桥接的正向合成测试签 `STATE_SOURCE_ADMITTED`。要求建立可信 admission resolver/签发来源白名单/Head CAS与验真链；任何只由caller或同工作区新写的Review必须留`UNTRUSTED_CANDIDATE`，即使文档SHA正确。

### AUD-B01：主DD将旧身份集合差异仍标为BaoStock UNVERIFIED，P0

`operational_daily_executor_v1.py::verify_source_gate` 第239～245行从**previous accepted Head**读取 `life.identity`，用其 `expected_codes` 和当前BaoStock `actual_codes` 比较，任何差异都会设置 `sources['baostock_daily']['status']='UNVERIFIED'`。第253～268行虽生成 `old_head_identity_preflight` 明确标记 `PREVIOUS_HEAD_IDENTITY_SCOPE_MISMATCH`，但没有将“提供方数据确实对齐TDX”和“相对旧身份新上市/更名”从状态机根因分开；开发负例自己展示：native已校验且新增SZ代码时 `readiness_status='WAIT_BAOSTOCK_DAILY'`。

**结果**：如果10/12发生符合来源的真实证券范围变化，原始SHA会保存，但当日主运营Head仍可能因旧集合不相等无法升级。要求先版本化生产合法当日identity来源准入和状态分类，不能直接删除旧保护比较；得到独立合同批准后才能让同日完整identity替换旧身份依据。未批准时保持last-good，但错误必须报 `WAIT_DATED_IDENTITY_AUTHORITY` 而非误导为BaoStock提供方不可用。该问题在10/12之前可完成工程代码/隔离仿真，不应留作无限等真实行情。

### AUD-C01：Episode followup状态汇总丢失“未到期”语义，P1

`episode_genesis_candidate_v2.observe()` 调用已存在的 `followup()`：各horizon未到期返回 `PENDING`，到期无合法结算为 `UNKNOWN`；但汇总 `followup_complete` 仅在全部 `COMPLETE` 时`TRUE`，其他统一`UNKNOWN`。这使“全部尚未到期”与“到期后缺证据”汇总值无法区分。本轮测试断言子项PENDING，却未覆盖相应顶层清晰展示。

需要在**不破坏冻结D2布尔字段合同**前提下另增 `followup_status`（例如 `PENDING_NOT_DUE` / `DUE_SOURCE_MISSING` / `COMPLETE`），`followup_complete`保持原合同要求的null/UNKNOWN/TRUE；更新页面与回归，确保没有给新Genesis编造已成熟结算。

### AUD-D01：FP13浏览器仍无真实双视口签收，P1

仓库 `D_GATE_DISPOSITION.json` 明确 `browser_viewport_1366/1920=PENDING_BROWSER_SURFACE`。IAB的 `ERR_BLOCKED_BY_CLIENT`/Chrome不可用，是测试执行环境不足，不等于源码完全失败；禁止用旧截图或HTTP200自动签全站产品。应分离当前可签的API研究子域与FP13完整版，并在可用本机浏览器环境对真实用户交互完成1366/1920 DOM、失败隔离/日期切换/回退/搜索/日周月实际显示。工具不可用就明确移交一次性人工QA清单，其他开发继续。

### AUD-A02/B02：真实新日首次观察仍依赖另一条原始Source Owner，非纯等待，P0

已有 `full_market_state_publisher_v1` 和 `bridge` 的研究及合成路径，不等于生产首次观测。实际当前Owner `AS_RECORDED=false/PIT_ELIGIBLE=false`；事件、benchmark、模型可用时钟、同日成员原件仍缺独立准入。同时B的旧身份集合可能先挡住新Owner发布。这属于可开发的源出版和跨日身份衔接，不能用“10/12还没到”掩盖所有实现工作；但真实10/12 SHA/时钟必须等当日合法来源出现。

## 四、独立分层结果

- 现有运营读域 `PASS_SCOPED_EVIDENCE_READY`；新Python/BFF字段仅隔离加载；生产28765旧PID未重启。
- State Publisher/Bridge `ENGINEERING_PASS_SCOPED`; `STATE_SOURCE_ADMITTED=NOT_GRANTED`。
- 未来同日身份证据链 `ENGINEERING_PREFLIGHT_PASS_SCOPED`; 主DD新身份放行 `NOT_GRANTED/CONTRACT_REQUIRED`。
- D2研究/Genesis `PASS_SCOPED_CANDIDATE`; 正式D2 `NOT_GRANTED`。
- Cohort正式分母 `null`；Writer `NOT_GRANTED`；真实Forward样本需T+1/3/5持续积累。
- FP13浏览器/全产品 `BLOCKED_BY_MISSING_BROWSER_E2E`；FP14全发布 `NOT_GRANTED`。
- FEP生产 `BLOCKED_CORRECTLY`，独立支线。
- V4-22总门 `EXTERNAL_ACCEPTANCE_BLOCKED`，不能拿本轮scope回归覆盖历史已签合同，也不要求它阻塞研究页面新功能。

## 五、接下来建议与明确时点

**10月10日～11日可做（无需未来行情）**：优先解决AUD-B01新身份合法来源/状态门可执行方案及AUD-A01可信Review接入边界；补Episode pending状态；现有API研究域可分范围签证据，浏览器待合适环境。冻结两Head并保留用户授权边界。**10月12日（预计真实交易日）18:35及重试**：保存实时原件、会员来源、GBBQ、当日新增代码/removed代码对账、State与D2实际候选；不得冒充15:00已知。真实采集+独立源审核在完整真源产生后按单项申请，不要求当日完成T+5成熟统计。

## 六、质量与安全约束

`AGENTS.md` Phase0已在阶段合同中标记FULL_PASS；D:/new_tdx只读；G盘保存新增temp/cache/work；原Accepted Head/模型/历史研究原件不可覆盖。独立审计仅对本轮新实现外推受影响范围，避免重复全量历史数据生产和几百条NULL状态表。不得因为测试通过而自行授权、重启28765、运行FEP生产预测或给正式胜率。

证据链接：
- GitHub commit `https://github.com/NanOns/a-share-market-structure-research/commit/d7b19feabc8e17ca4948bfdef38047f10fd6f97c`
- 开发执行报告 `https://drive.google.com/file/d/18GYSgQxob5fLzdoTtcbkeWLEWNky_HWh/view`
- 源码 `src/workbench_analysis/state_publisher_bridge_v1.py`、`next_t0_identity_preflight_v1.py`、`operational_daily_executor_v1.py`、`src/sector/episode_genesis_candidate_v2.py`。
