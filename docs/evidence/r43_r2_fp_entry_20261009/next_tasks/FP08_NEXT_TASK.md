# FP08 下一轮定向任务卡

原合同：`docs/evidence/fp01_20261008/tasks/08_Focus持续跟踪与Episode生命周期_R1_20261008.md`；最新 Drive 合集：`17tbCyE-gYhe2pwoy2gLFeoNNwq9NPKxu`。这是一张原合同续办卡，不另造设计或降低范围。

现状：2477关注对象和真实事件读域可读。

执行：逐字段检查Episode/T0/Anchor/Observation/outcome；自动写入与读域独立门。沿用未变的 S/四日 Owner 字节，不重抓551MB ZIP，不修改 TDX，不覆盖旧 PIT，不混用9/30替代10/08。

验收：按原 FP08 合同 feature→producer→source→API→UI→test→screenshot 逐项核验；用真实来源、上下文token、数值抽样及浏览器证明。缺失Owner精确标注，不能以HTTP200、工程测试或统计未成熟冒充整体通过。记录阶段合同、证据、验收和下一阶段，完成后commit+push及Drive归档回读。

当前正式结果：NOT_GRANTED_BY_THIS_RUN；外部数值与权限来源审计单独跟踪。下一步仅沿原调度依赖执行，不能跳过FP13进入完整FP14发布。
