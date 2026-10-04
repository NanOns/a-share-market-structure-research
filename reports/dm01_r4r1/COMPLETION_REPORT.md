# DM01 R4R1 完成报告

本轮本地修复结论：PASS_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT。

继承父链与目标日观察按作用域分开：历史重建来源保留，混合整头 AS_RECORDED=false。晋升必须满足 real_forward_evidence=true、原生目标日收盘后观察、全部九组件检查与精确外部验收授权。首可用时间需要独立精确来源证明；同日收到数据不构成首可用证明，当前已接受证明来源清单为空，默认 false。R25 入口要求精确父/子/目标来源/观察/九组件桥接，整头标签不能独立放行。

最终受测源码：`f664d13a83260eae959f851fc5d8723d2eb59416`；标签：`codex/dm01-r4r1-pit-lineage-tested-source-20261005`。本地与独立检出完整回归均为 2021 项：1992 通过、26 项原有失败、3 跳过；R4 25 项与 R4R1 15 项全部通过，12 个规定向量均覆盖。26 项历史债务独立登记，完整回归 pytest exit_code=1，没有宣称全绿。最终首轮本地与独立目录并发运行均遇旧 HTTP 测试 DuckDB 文件占用，隔离复查及同源码完整复查通过，原日志保留于 attempts，详见 REGRESSION_RECHECK_DISPOSITION.json；HTTP 文件占用稳定性另立独立开放审计项，不因复查通过而关闭。

所有证据为工程模拟或反事实投影；R4R1-01 是纯元数据投影，07 的合成证明只通过工程结构检查；02/08 的隔离 CAS 测试使用明确的 admission monkeypatch，仅证明拒绝与 CAS/整头构造，不作为真实行情授权。九组件调用原 R3_3 数值内核，独立数值 oracle 未改变。

实际 V2 Data Head 仍为 2026-09-30，日历覆盖至 2026-12-31。2026-10-08 保持 WAIT_MARKET_CLOSE，source_requests=0。REAL_TARGET_SESSION_PACKAGE=NOT_CREATED，R25=WAIT_ACCEPTED_DAILY_INPUT，REAL_SHADOW_EXECUTION=NOT_STARTED，REAL_SHADOW_OBSERVATIONS=0，Production/Shadow/Focus=false。TDX 未写入；无关工作区文件保留。

下一步：STOP_WAIT_DM01_R4R1_INDEPENDENT_EXTERNAL_AUDIT。当前没有创建或模拟外部接受头；真实 runtime 仍需精确源码、合同、策略哈希绑定的 PASS_DM01_R4R1_GO_FORWARD_RUNTIME 外部结论。提交和推送不代表外部接受或授权下一阶段。
