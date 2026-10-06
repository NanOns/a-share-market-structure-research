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
