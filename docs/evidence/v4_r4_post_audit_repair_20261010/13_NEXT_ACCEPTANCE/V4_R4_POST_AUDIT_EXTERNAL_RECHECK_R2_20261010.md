# 大A V4｜R4 外审后修复·独立复审 R2（2026-10-10）

- **外审编号**：`V4-R4-POST-AUDIT-EXTERNAL-RECHECK-R2-20261010`
- **对象**：`NanOns/a-share-market-structure-research`，`codex/v4-fp14-r2-repair`
- **最新冻结 HEAD**：`336827bf0bc152a4c5c9ba7ec6e4662751fe7422`；基线 `5ad4bb8da48196d9e902d48ece510a15136c4210`；GitHub `compare_commits` 显示 **ahead 10、behind 0**。
- **实际服务运行版本**：`1c47f6ca259716d020bee59533550bf96f5bb745`，最新证据 PID `51368`，`127.0.0.1:28765`。比较从该 SHA 到冻结 HEAD 仅新增两次提交、六个证据文件，**无 src/scripts/config/tests 源代码变化**。因此运行代码与当前已审核业务源代码范围相符，但本外审不能直接控制用户本机进程。
- **数据 T0**：`2026-10-09`；运营 Head SHA `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；严格 PIT Head SHA `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`。
- **独立复审总状态**：`EXTERNAL_ACCEPTANCE_BLOCKED`，**可保留的工程通过**：`R4_ENGINEERING_SCOPED_PASS_WITH_FORMAL_SOURCE_GATES`。对于旧生产切换、FEP 伪授权漏洞及单域503恢复，本轮相对上次审计已有足够实质代码及可复验现场证据，判 **`PASS_SCOPED_EVIDENCE_READY`**。完整 FP13/FP14 正式外审不自动签发。

## 1. 检查方法、权限、证据性质

本次直接读取：GitHub branch 最新 HEAD / commit compare、修改后的 FEP admission 和 `trusted_authority`、板块 `producer_entry_r1` / legacy extraction、Cohort `cohort_capture_readiness` / `cohort_first_capture_producer`、真实服务加载收据、10/09 Native 候选、浏览器矩阵及503拦截收据、PostgreSQL JUnit 与回归执行收据、BCD 集成 JUnit、三个阶段进度及 Drive 最近报告。不是单纯引用开发方总报告。

**未亲自进行**：通过用户本机 `28765` 执行独立浏览器点击/抓包、远程独立 Postgres 测试、重新从数 GB 原始 Owner 计算板块全量、验证所有 ZIP 解包 CRC；开发方记录的测试数量和浏览器事实属于**源码与归档证据支持的工程结论，非审计者现场再执行**。禁止将开发方自报测试绿灯升级为外审正式批准。

## 2. 按上轮 FIX-E/D/B/C/A 逐项裁决

| 工作包 | 本次实际新增的源码和证据 | 外审结论 | 尚不能声称 |
|---|---|---|---|
| **FIX-E 生产工作台** | 旧 PID41528 已在用户单独授权后强制结束（开发方记录）；新PID49428→27956→51368，最终通过正常启动；源码与进程绑定，28765 9路有效 token HTTP200，空/错误 token 409；六入口双尺寸截图和 DOM；受控客户端 breadth503 一次错误、重试恢复两分辨率 | **`PASS_SCOPED_PRODUCTION_CODE_AND_CLIENT_FAULT_QA`**，相较上次真正前进 | 不证明用户此刻进程没有后续变化，不证明服务器自身真实503；正式FP13全矩阵/FP14发布授权未签 |
| **FIX-D FEP** | `admission.py` 把 caller 传入的 bool/dict 限定为 `GATE_ELIGIBLE_CANDIDATE`，真实 production_authorized 恒 False；六字段 null+`SOURCE_INCOMPLETE`；新增 `trusted_authority.py` 的 actual DB repeatable-read只读解析 | **旧伪正向授权和字段状态矛盾：`PASS_SCOPED_FIXED`**；真实生产能力仍 `BLOCKED` | isolated SQL 25项与 E5老50项不代表正式生产模型/独立approval/grant已获准 |
| **FIX-B 板块D2** | 新 `sector/producer_entry_r1.py` 实现六字段 SHA 原件候选入口；`legacy_producer_candidate_r1.py` 复用9/24 legacy样本，TRUE/FALSE/UNKNOWN三项候选提取；10/09真实 Native dq5等有来源 | **`PASS_SCOPED_SOURCE_ADAPTER`，`FORMAL_SECTOR_D2_OWNER_BLOCKED`** | 9/24 golden≠10/09正式验收；六正式状态在10/09仍缺，reducer不能宣称运行成功 |
| **FIX-C 独立Cohort** | 完整信号源freeze→不可变producer→eligible/ineligible全量ledger→Owner/receipt候选→独立grant预检；日更DD入口已接入但缺源时不阻塞日更 | **`PASS_SCOPED_FUTURE_CAPTURE_ENGINEERING`，`REAL_COHORT_ENROLLMENT_BLOCKED`** | 10/09 corrected 非as-recorded，旧2290事件不可补历史冻结，真实入组分母UNKNOWN，不得算胜率/收益 |
| **FIX-A Amount H21** | 继续保留历史20日缺首次获取成员原件、现有金额与当前板块代理字段可读、缺源不显示0 | **`PASS_SCOPED_HISTORY_SEARCH_DISPOSITION`，历史 `NOT_VERIFIABLE`** | 未来交易日不能回补九月首获；正式 Amount A H21 仍非正式通过 |

### 2.1 FIX-E证据核对要点

- `11_CONTINUATION/01_E_BROWSER/E_BREADTH_503_BROWSER_RECEIPT.json`：两个分辨率，`fault=browser_intercepted_503_one_response`，`server_fault=false`，`retry_requests` 精确给出 28765 URL，`unaffected_sections_identical=true`，`date_retained=true`；**只签受控客户端故障隔离**。
- `12_BCD_DEVELOPMENT/PRODUCTION_MODULE_ATTESTATION.json`：当前 PID51368，`exact_HEAD=1c47f6ca...`、`active_port=28765`、受保护Head、模块源路径及 bytecode sha，支持确实加载新版研究代码。新版本的功能实证与旧 `OPERATIONAL_SUCCESSOR_BFF_V1` 不应混同。
- `12_BCD_DEVELOPMENT/LIVE_28765_BCD_READBACK.json`：home/stocks/sectors/focus/market真实请求200+READY；forward/statistics、settlement、FEP返回200+`SOURCE_INCOMPLETE`，这是**明确的缺正式源**，不是功能指标READY。
- 旧九个409的精确原始请求未保留，新的空/旧/正确token回放支持 token 拒绝机制的归因，但不可反推旧九个请求的唯一原因。这个边界开发方有如实保留。

### 2.2 FIX-D确切检查

- `src/workbench_analysis/fep_e5/admission.py::evaluate()` 当前 `candidate_eligible` 即使 True，返回 `production_authorized=False`、`production_status=BLOCKED`、全部字段 `SOURCE_INCOMPLETE`。上一轮“全True可能获得生产授权且各字段NOT_READY”的状态矛盾已消除。
- `src/workbench_analysis/fep_e5/trusted_authority.py::read_canonical_candidate` 使用 PostgreSQL 只读repeatable-read检查 registry、active head、grant、CAS、prediction、revision、source first-asof、训练label成熟及预测字段。`12_BCD_DEVELOPMENT/02_D/D_DB_QUERY_JUNIT.xml` 记录 **25 tests / 0 error / 0 fail**；`11_CONTINUATION/02_D_DB` 旧被阻塞套件有 **50 tests**、其中22个历史DB用例，开发侧结果通过；库在 G盘隔离、测试后停止。
- **新发现的P2/合同表达问题**：`trusted_authority.read_canonical_candidate` 可能在 `result['errors']` 里仍有 `ENGINEERING_CAS_NOT_PRODUCTION_APPROVAL` / `CURRENT_INDEPENDENT_CAPABILITY_APPROVAL_SOURCE_MISSING` / 缺预测源时把 `result['status']` 标为 `CANONICAL_AUTHORITY_CANDIDATE_VERIFIED`。由于 `production_authorized` 始终为 False，这不是当前生产越权，但状态名可能误导后续适配器；应区分 `DB_FACTS_READ_VERIFIED` 与 `CANDIDATE_INCOMPLETE/FORMAL_APPROVAL_MISSING`，并增加错误不为空时不得返回完整候选就绪的负例。此项**不应把已修的旧P0重新打开**。

### 2.3 FIX-B：不可把诊断提取当正式生命周期

- `12_BCD_DEVELOPMENT/03_B/B_REAL_NATIVE_SOURCE_ENTRY_R2.json`：10/09真实 Native 案例，`dq5` 有数值及源SHA，但六项 formal upstream 全部为 null、`reducer_invoked=false`、`formal_consumer_enabled=false`；这是诚实的 fail-closed。
- `B_CURRENT_SOURCE_AND_ENGINEERING_BOUNDARIES.json` 给出真正阻断：历史A05 legacy输入只接受 **2026-09-24**，10/09读取返回 `A05_CURRENT_SNAPSHOT_TARGET_NOT_ACCEPTED`；`q20/dq5_3`排名、SETUP/RECOVERY、原始板块Episode、冻结失效合同、due/settlement和scenario没有10/09合法真源。对不可替代的原件，不能通过改标签或拿今天最新成员回填。
- 9/24三条TRUE/FALSE/UNKNOWN金样本属于旧日期**诊断候选**，并非10/09正式板块 D2 生命周期产物。

### 2.4 FIX-C：冻结生产者已写，真实资料仍不存在

- `cohort_first_capture_producer_r1.py::freeze_source_candidate` 检查当前上海日期、观察截止、原件SHA、完整eligible/ineligible行、冻结identity与幂等 no-clobber；`extract_candidate` 校验真实 State Owner 与producer、提取隔离Owner/receipt；`cohort_capture_readiness_r1.py` 单独要求write grant，缺源不阻断DD业务正常派生。
- 真正合法入组要求独立正式State Owner源及当时 first-capture。`12_BCD_DEVELOPMENT/04_C/C_IMPLEMENTATION_AND_ACTUAL_BOUNDARY.json` 证实10/09运营Head `AS_RECORDED=false, PIT_ELIGIBLE=false`，当日无独立Writer grant，故 `observed_count=null`、`production_write_authorized=false` 是正确行为。
- 开发方 **142项集成测试、C的73项、D的25项**各包含范围重叠，不得直接相加当独立验证样本量。`BCD_INTEGRATED_JUNIT.xml` 实际存在并列有 142 tests，无 errors/failures（开发方工作站记录）。

## 3. 版本化验收账本问题（低危但必须订正）

1. `07_SCOPE_GATE_MATRIX.json` **顶层** `FP13_REAL_BROWSER=CORE_CASES_VERIFIED_DOUBLE_VIEWPORT; CONTROLLED_BROWSER_503_ISOLATION_RECOVERY_PASS`，但 `stages.E.acceptance` 旧文案仍是 `FP13_FAULT_RECOVERY_OPEN`。这形成**同一当前账本内部冲突**；应追加 R2 版本结论/覆盖关系，不改写原始测试结果。属于 `P2_EVIDENCE_STATUS_RECONCILIATION`。
2. `12_BCD_DEVELOPMENT/STAGE_CONTRACT.json` 仍 `acceptance=IN_PROGRESS`，而同目录已有完成报告及测试。这可能是有意保留的开工快照，应在最终ledger显式标明“启动合同，不是最终状态”，避免审计误判。
3. E 当前真实生产 PID51368 与此前 PID49428/27956 不是冲突，是**不同时间的续轮进程**。应以最新带时刻的Attestation为准。

## 4. 五项风险与入场权限

- **不能把真实日更等待作为开发停工理由**。功能和独立准入可继续，但10/12真实行情尚未发生（审计日是周六），无当日source就不得模拟日更。
- **严格历史PIT仍不可验证**。9月历史成员首获不存在时旧 Amount H21、板块纠正计算只能明确标 corrected。
- **板块D2和Cohort当前正式全功能仍未启用**：这是明确真源/准入阻断，而非本轮代码完全失败；下次要围绕被阻断的正式Producer/Owner作决定，不做大量同质未知测试。
- **FEP正式生产预测仍关闭**，且应该关闭。真实registry、正式model revision、Head/CAS与独立授权、成熟标签、合法as-recorded prediction owner尚未构成最终批准来源。
- **FP13 scoped产品QA可交付给独立浏览器复验**；不自动扩展为FP14全系统正式发布。

## 5. 唯一结论、下一动作

**`EXTERNAL_ACCEPTANCE_BLOCKED`**（全正式）；**`ENGINEERING_SCOPED_PASS`**（本次新代码与证据中 E的新版已加载及受控503恢复、D旧伪授权修复、B合法候选接线、C未来首获链）；历史/权限缺口逐项OPEN。

下一轮执行同日配套《V4_R4_NEXT_ACCEPTANCE_GATES_TASK_R1_20261010.md》，只做：1）独立复验生产/FP13核验包；2）修订FEP候选状态与真实Owner接入门；3）B当前日期合法 source production/admission 方案的实际阻断决策；4）C真实 first-capture 的发布准入接口与无合法输入保留UNKNOWN；5）统一R4最终账本。**不重跑旧LOO、旧金额残差或400份无源板块列表**。

## 6. 精确证据路径

- GitHub冻结提交：`https://github.com/NanOns/a-share-market-structure-research/commit/336827bf0bc152a4c5c9ba7ec6e4662751fe7422`
- GitHub本轮产物：`docs/evidence/v4_r4_post_audit_repair_20261010/`
- Drive最新三次开发报告：`V4_R4_POST_AUDIT_TARGETED_REPAIR_RESULT_20261010.md`（`1gk7bipdkSlXz3wtmUX_CMtgsFs4Y7yg0`）、`V4_R4_CONTINUATION_RESULT_20261010.md`（`1axsS8wkYHaeJr8jYSH8XSBJECQVAozbl`）、`V4_R4_BCD_DEVELOPMENT_RESULT_20261010.md`（`1eBV20xDpKaY3UgSj4Ffp9nDKeJ1HWlOn`）。
- FEP：`src/workbench_analysis/fep_e5/admission.py`、`src/workbench_analysis/fep_e5/trusted_authority.py`、`12_BCD_DEVELOPMENT/02_D/D_DB_QUERY_JUNIT.xml`、`11_CONTINUATION/02_D_DB/D_DB_REGRESSION_RECEIPT.json`。
- 板块：`src/sector/producer_entry_r1.py`、`src/sector/legacy_producer_candidate_r1.py`、`12_BCD_DEVELOPMENT/03_B/B_CURRENT_SOURCE_AND_ENGINEERING_BOUNDARIES.json`。
- Cohort：`src/workbench_analysis/cohort_first_capture_producer_r1.py`、`src/workbench_analysis/cohort_capture_readiness_r1.py`、`12_BCD_DEVELOPMENT/04_C/C_IMPLEMENTATION_AND_ACTUAL_BOUNDARY.json`。
- 生产：`12_BCD_DEVELOPMENT/PRODUCTION_MODULE_ATTESTATION.json`、`12_BCD_DEVELOPMENT/LIVE_28765_BCD_READBACK.json`、`11_CONTINUATION/01_E_BROWSER/E_BREADTH_503_BROWSER_RECEIPT.json`。
