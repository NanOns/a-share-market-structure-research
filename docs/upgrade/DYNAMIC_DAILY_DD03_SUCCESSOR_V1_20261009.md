# DD03 / DD04 后继合同与验收计划

执行依据：V4-DYNAMIC-DAILY-R1.1 第 3.2、4、9 节以及 DD03、DD04；继承当前 R4.3 运营研究范围与原 Kernel，不修改旧四日 Owner、旧 reader 或严格 PIT Head。

后继合同：`V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1`。每次只增加一个准确连续的官方交易日，引用全部旧 Owner；新日按生命周期、停牌与实际 Bar 守恒对账。计算器在独立私有 IO 作用域复用原生产函数，保存独立来源 SHA、观察时间和目标日期。不把较晚来源称为历史首次可得。Core、历史 QFQ、RPS 端点与下游结构、板块、市场、Focus 连续重算；周/月使用 DD06 原聚合内核。发生新 GBBQ 修订时另存行动 QA，必须通过重新计算的原独立仿射 oracle；新成员来源冻结独立非 PIT S。

发布合同：用户本轮只读日更指令绑定的版本化策略；必须列出已接受且 SHA 未变的算法绑定。每个候选需新日 DERIVED_READY 收据、完整 Owner 和分日来源注册表。CAS 预期旧 SHA，归档精确前驱，再执行真实同 token 的 context、operations/status、stocks、sectors、market、focus HTTP 读回。失败原子回滚；读回未完成就崩溃时启动恢复精确前驱。取消在发布之前生效，已发布日保留。

当前阶段：IN_PROGRESS。证据分别写入 `data/v4/dynamic_daily_owners/<day>/<source_sha>/`、事务日志及 `docs/evidence/dynamic_daily_20261009/`。四项事务故障注入通过仅证明工程事务行为，不代表真实 Owner 或独立外审通过。下一阶段：完成真实冻结来源全链重跑、数值与口径差异审计，然后准入用户绑定策略，再运行新目标日 CAS 与真实浏览器验收。
