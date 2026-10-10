# 大A V4｜下一个真实交易日之前可以立即执行的工程任务卡 R1

- 日期：2026-10-10，项目`NanOns/a-share-market-structure-research`。
- 基准冻结HEAD：`3356e833fcf604c36db0cd856a8e31ed91fc8472`。Codex启动前git fetch并记录实际base，绝不从旧HEAD强推。
- 唯一目标：**当前正式缺门不得阻止真正可做的工程**；必须补齐上游原始State Producer与 D2资格源、为新T0第一次真正采集准备一条可自动执行的、证据可复核的流水线。
- 受保护运营Head `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`、strict PIT Head `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`，不得改；TDX D:/new_tdx只读；G:/codex_tmp放所有临时文件。既有28765运行服务不为工程测试重启。用户已授权的范围化研究显示保留。

## Task 1 P0｜真正State Publisher，不再只造Reader

1. 盘点当前实际State算法/owner的生成位置、模型/参数/窗口和基准/事件来源。编写从现有算法与**当时观察合法原件**产生 `FULL_MARKET_STATE_PRODUCER_OUTPUT_V1` 的正式候选生成代码，而不是测试fixture或纯粹检查`state.contract_id`的函数；对没得真实源的字段明确标不可用，不应凭空补出Episode/event或benchmark。
2. 对全市场全场景逐条输出 eligible/ineligible/unknown、排除原因、first_available、冻结T0时间、member版本、model/parameters SHA、每项来源Owner SHA、实际 cutoff 与场景身份；与已存在`full_state_first_observed_v1.py`串联，候选首先进入隔离无权限命名空间。
3. 现有10/09以历史研究身份完成端到端数据形状验证，拒绝PIT_OBSERVED升格；使用不同证券/板块Universe、晚到数据、模型变更、缺信号、数据污染和重试开展合成实验。演练Writer grant前后的边界，但**不得产生实际Grant**。
4. 交付实际源码+运行合同+一组完整研究候选原始输出和SHA+负例，不接受仅有`SOURCE_NOT_PRESENT`清单。

## Task 2 P0｜板块D2资格口径事实复核

1. 实际复核 `phase2.py::prepare` 和 `legacy_valid_member_a05_v1.py::exact_value` 与 `valid_member_qualification_v3.py` 的每个条件：正则、缺失字段、显式None、`missing_state`枚举、normal、sector_valid、停牌、重命名。旧源码正确，不再发新的原正则故障报告。
2. 使用有原始来源的不同证券身份及小板块golden对照按字段出PASS/DIFFERENCE/UNKNOWN；在未来真实T0取得legitimate legacy missing_state之前，只准发布修正研究诊断，不批准A05跨日期或正式D2。
3. 六字段Producer要形成真实来源生成/继承/缺源逻辑；没有先前合法Episode时显式 `NO_PRIOR_EPISODE`，尚未到期显式 `PENDING`，缺证明是`UNKNOWN`；不能用非正式Native proxy替代官方判定。
4. 输出算法输入对照与独立入场申请范围，而非重复输出400×六字段NULL。

## Task 3 P0｜预演真实日期的一次性首获流

1. 从 `execute_sources → first_capture_source_candidate → new Owner build/seal → SAME_DAY_SOURCE_SCOPE_RECONCILIATION_V1 → State / sector候选` 走**真正函数调用链**的隔离E2E；保证Source在 readiness gate失败时也先保存原字节与当时可信时间，Day0旧Head的成员范围清楚标临时预范围。
2. 至少覆盖新增证券、退市、证券更名、停复牌、新增或删除板块成员、source后到、source文件内容冲突、临时失败/重试、CAS失败、不一致成员SHA；测试旧T0/未来T0绝不会冒充真实首次观测。
3. 准备真实T0收集运行手册：18:35定时/重试、自动检查`requested_at/received_at`、采集当时来源、日更主流程不受候选异常阻挡、HEAD与历史回放不可覆盖、待审核 candidate 单独持久化。
4. 不真实触发2026-10-12，也不人为修改机器时间冒充真实行情到来。

## Task 4 P1｜当前研究产品的范围化外部验收和可回滚

1. 已部署28765候选读域专门保留，不再重复大批端口切换。测试真实10/09板块与Cohort研究候选只读、10/08原件缺失、10/12未来拒绝、历史股票分页、旧token409、坏archive SHA拒绝，中文状态与用户可理解的原因。
2. 研究候选要显示`RECONSTRUCTED_RESEARCH_ONLY`和明确的源截止/观测时间，防止“研究TRUE”被页面当正式CONFIRMED TRUE或统计胜率。进一步测试历史多个Head变化（仅合成）仍能保持原冻结字节和合法身份。
3. 生产切换与回滚另走用户授权及独立QA，工程实现不自动取得FP14全能力许可。

## Task 5 P2｜FEP权限与模型仅限准备

1. 检查真实registry和Head/CAS可信读取器到`current_gate`的接线缺口，明确区分Source、训练/成熟数据缺失与Grant缺失；保留生产预测Blocked，工程可以写正反例和单独迁移合同。
2. 不运行生产模型推断或给页面虚假5日收益期望；不要求在下个真实交易日到来前取得5日结果。

## 一轮必须交付的内容及验收条件

- `STATE_PUBLISHER_SOURCE_AND_OUTPUT.md`、`STATE_PUBLISHER_ISOLATED_RUN.json`、关键源码和单测、独立源时钟反例。
- `D2_LEGACY_QUALIFICATION_ORACLE.md`、`D2_PRODUCER_SOURCE_MATRIX.json`、TRUE/FALSE/UNKNOWN准确区别。
- `NEXT_T0_REAL_CAPTURE_DRY_RUN.md`、`NEXT_T0_CAPTURE_CHECKLIST.json`、跨Universe和主DD不退化的负例、唯一故障定位。
- `PRODUCTION_RESEARCH_SCOPE_QA.md`：审查的是研究产品范围，不宣称正式D2/Cohort/FEP。
- `GATE_STATUS_R1.json`必须分别有研究候选PASS_SCOPED/真实首获PENDING/State Source Owner入场状态/正式D2/正式Cohort/FEP/FP14，不能把所有项一个BLOCKED。
- Git提交、Push核对remote exact HEAD；轻量MD+测试及原始候选哈希同步Drive，读取云端原字节SHA验真。不要复制整个多GB数据库/旧历史或重复构建无用大型zip。

**停工条件仅限真正无法从当前事实源生成的源资料/真实日期**，不得因其余Producer未正式授权停下所有工程。所有缺源按`SOURCE_PRODUCER_NOT_IMPLEMENTED`/`FUTURE_REAL_OBSERVATION_PENDING`/`INDEPENDENT_ADMISSION_REQUIRED`/`HISTORICAL_NOT_VERIFIABLE`定类。Codex不自签外部验收，不改已接受Head/正式权限。
