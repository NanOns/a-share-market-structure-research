# IA05 历史验收产物缺失独立审计项

- 状态：OPEN_HISTORICAL_EVIDENCE_RECOVERY_REQUIRED。
- 范围：全量回归实际引用、当前工作区不存在且 `git log --all -- <exact path>` 无记录的历史产物。初始逐路径清单见 `reports/forward_r2_remainder_consolidated_20261007/IA05_MISSING_HISTORICAL_FIXTURES.json`。
- 证据：完整 `remainder_full_a.xml` 与日志保留原始失败；清单包含引用测试节点、准确路径、当前存在性和全部可见 Git refs 的查询结果。后续回归结果独立记录，不将初始失败自动视为已修复。
- 边界：未找到 Git 记录不能证明产物从未存在，也不能证明在其他备份中不可恢复。当前证据不足以恢复原始发布身份。
- 处置：保留原断言及失败，不忽略、不跳过、不重造同名历史验收文件，不将当前生成结果冒充旧发布结果。
- 验收要求：找回可核验的原始发布产物及对应身份，或完成明确批准、保留旧身份和断言的正式测试 supersession；随后执行相关节点及完整回归。
- 当前阶段关系：这是独立历史证据债务。它不授予当前运行、First Real Shadow、Production、模型展示或优先级使用权限；IA05 不能因其他工作包通过而自动关闭。
