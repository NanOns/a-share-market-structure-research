# P12-06 BUNDLE_V3_3 阶段验收

阶段合同`P12-06_BUNDLE_V3_3_ACCEPTANCE_V1`。执行前核对`AGENTS.md`、V3 v2.1升级方案§16、§19及[P12-05验收](P12_05_REPLAY_V3_3_ACCEPTANCE_20260915.md)。新增`TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_01`不可变文件包及独立原子指针，不修改TDX，不切换现有首页数据源。

候选包绑定publication、snapshot、membership、独立P12逻辑run、parameter hash、P12-02 dependency lock、交易日与五个候选合同。当前包含113行完整合格结果，输出摘要`e2eaadca2a8614af661e79e8a203e0cfd49c40f2e4475233f4dd67d3b08d4eae`。文件先在同目录临时目录写入、逐文件校验，再整体改名为摘要目录；完整校验通过后才原子替换独立指针`ACTIVE_RESEARCH_BUNDLE_V3_3.json`。同输入重跑复用相同摘要。

固定反例验证：身份缺失拒绝、结果文件篡改拒绝、交换前注入失败保持旧指针、相同输入幂等。真实候选包可通过指针重新读取；验证重跑前后生产数据库size/mtime一致。当前页面尚不消费此指针，留给P12-07。P12逻辑run是文件包身份，尚未冒充或写入旧`research_runs`结构，因此阶段结果为 **`DEGRADED_PASS`**；文件包与原子可见性通过，数据库新结果模型和首页发布仍不在本阶段通过范围。机器证据见[候选包回执](../reports/p12_06/candidate_bundle_receipt.json)和[阶段门](../reports/p12_06/p12_06_stage_gate.json)。下一阶段为`P12-07_UI_V3_3`。
