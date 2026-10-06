# 2026-10-06 独立全阶段审计证据索引

代码基线：e21adab807e7f39960ec555764ab8c9d6b50f47b。范围：00A–H、01–22、17G、FEP E1–E5，36单元。交付：独立报告、线上综合报告和10项OPEN_AUDIT_ONLY登记；不是正式release或运行权限。

| 文件 | 用途 |
|---|---|
| audit_baseline.json / source_inventory.json | 2819文件身份/语法/符号清单、起始工作区状态 |
| heads_snapshot.json / exact_binding_checks.json | 当前heads原内容及4797条绑定逐引用核验 |
| historical_binding_provenance.json / active_reader_checks.json | 20旧引用/15身份Git原字节可找回；current读取器PASS |
| migration_namespace_coverage.json | 最新18适用226个SQL声明一致；排除16个R23旧工程表的理由 |
| semantic_probes.py/json | IA-01..04独立synthetic反例，不是真实市场样本 |
| online_model_report_input.md / online_report_identity.json | 用户附件原字节和身份；仅证据，不作为新执行指令 |
| cross_model_code_identity.json / cross_model_stage_decisions.json | 两HEAD Forward字节相同、36阶段综合裁决 |
| pytest_full.log/xml | 默认全仓collection错误1；未运行全套 |
| pytest_continue.log / global_rerun_interruption.json | 全仓继续复跑被中止；无完整JUnit、无通过计数，旧真实DB启动风险IA-09 |
| stage_test_selection.json / pytest_stages.log/xml | 明确限定范围首轮4014 passed / 243 failed / 38 errors / 281 skipped |
| namespace_recheck_selection.json / pytest_namespace_recheck.log/xml | TEMP/TMP与basetemp统一E盘后的72 passed / 1 failed；不与首轮累加 |
| pytest_m14.log/xml | direct/capture-retired 5 passed，fake fetchers，无在线重抓 |
| pytest_summary.json / pytest_failure_inventory.json / TEST_RESULTS.md | 完整节点结果、错误/skip原文及文本导航分类；分类不是自动关闭 |
| audit_cli_bootstrap.py / cli_bootstrap_probe.json | IA-10只读--help导入对照：默认exit1、明确root+src PYTHONPATH exit0 |
| audit_items.json | 10项独立scope/证据/原因/影响/接受条件，未覆盖canonical head |
| deliverable_validation.json | 36阶段、303本地引用、源文件未变化、FEP设计身份一致性核验 |
| DELIVERY.json | 审计发布commit、push回执与后续边界 |

原始日志因根.gitignore的*.log默认忽略而单独纳入本审计提交。本目录.gitattributes禁用文本自动转换，保留附件和证据字节。进程运行时日志只是过程证据；完成后封存，不用中途日志签验收。生成/摘要脚本使用原子替换输出，临时目录在E盘，TDX根没有写命令。

全部测试反例、fixture、重构模型均不计REAL、PIT_OBSERVED、Forward maturity或OOS；Git/source无diff不能证明ignored DB零写，具体限制已按IA-09记录。未改变业务code/config/heads，未授予生产或下一阶段权限。
