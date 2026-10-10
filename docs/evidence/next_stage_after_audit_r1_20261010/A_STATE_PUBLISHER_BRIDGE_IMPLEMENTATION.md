# TASK A 工程候选闭环

版本接口 src/workbench_analysis/state_publisher_bridge_v1.py 接受真实gzip Publisher原件及独立验证上下文传入的精确 review binding。先冻结 quarantine；任何缺独立review、真实当日AS_RECORDED会员、模型首获、事件或benchmark时输出 SOURCE_GAPS，原研究原件不修改。不能从Publisher自称PIT获取权限。

事实完整路径：原件→quarantine→独立review逐源SHA/日期/时钟→新候选JSON→freeze_first_observed→freeze_source_candidate→extract_candidate→完整 eligibility ledger→独立 synthetic GRANT preflight→prepare_capture。权限检查只消费传入的可信上下文；尚未接生产独立审查签发服务，不能把review_role字符串当生产认证。实际事件/benchmark由调用者提供权威原件；不重新生成过去Episode，也不写 NOT_APPLICABLE。

固定两组隔离测试：正向完整合成原件及独立合成Grant，反向历史corrected、首次时钟晚、假current会员、缺event、缺benchmark、Top-K、未来日期、错误Owner SHA、变化成员、相同revision原件次序变化。23项定点测试含既有first-observed测试PASS。合成场景只演练程序日期，未声称2026-10-12真实发生。真实源仍SOURCE_GAPS；未重启28765或写TDX。

小型数值oracle固定与随机seed=20261010抽样300 TRUE：手工数值分支与原冻结AST逐一对照，使用原target_values，无全市场重算。它不独立重建上游数值，也不声称原200项回归完整独立审算法含义。

验收：ENG_PRODUCER_READY / PASS_SCOPED工程证据；正式真实Source、Cohort、Writer Grant、FEP均未授权。下一阶段为真实当日独立Source Review，需实际首获与合法全部上游。

补全正向固定组：调用实际 full_market_state_publisher_v1.build()，使用明确 synthetic 原target_values输入、真实冻结 scanner AST、4原场景及真实producer依赖归档；随后 quarantine→bridge→firstobserved→producer→extract→完整4行 ledger→独立synthetic GRANT→prepare_capture。A_real_build_synthetic_fixture 持久化完整原件，A_FIXTURE_BINDINGS记录两种相对路径上下文及Git可读SHA。测试复用10/09旧target_values只作为合成向量，未提升其现实历史身份。缺首获/冻结时钟现在明确 SOURCE_GAPS，没有伪造默认时间。
