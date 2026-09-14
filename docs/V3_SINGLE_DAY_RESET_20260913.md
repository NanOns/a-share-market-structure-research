# V3 单日清库重建记录（2026-09-13）

- 阶段合同：`V3_SINGLE_DAY_CLEAN_REBUILD_V1_0`
- 用户目标：删除项目本地数据（含生成的静态数据），仅构建 2026-09-11，并允许从页面直接触发；保留代码、配置、规格/验收文档和只读 TDX 源。
- 前置：Phase 0 `FULL_PASS`；V3 主规格 §0、§2.1、§3、§18，AGENTS.md 只读输入与原子输出边界。
- 官方日包信息：`_hsjdayinfo.js` 于 2026-09-13 查询为 `2026-09-11 15:58:57`，状态 `PASS`。
- 删除范围：项目 `data/`、`reports/`、`logs/` 中的旧生成物；不触碰 `D:/new_tdx` 或任一配置 TDX 源、`src/`、`config/`、`docs/`、`references/`。
- 安全策略：先在项目内隔离旧生成目录，空库重建通过后才永久移除隔离副本；若重建失败，保留副本供恢复，不声称删除完成。
- 页面合同：根页面可在零 publication 时提交完整构建，`expected_trade_date` 不匹配则拒绝发布；任务串联 M3 日包、M4 发布、分析绑定和 V3 研究构建。
- 页面实现：根页面支持零 publication 空态，目标日输入固定显示 2026-09-11；提交体含 `expected_trade_date` 和 `build_research_v3=true`。服务端串联 M3 官方日包、M4 publication、M8/M9 分析绑定、V3 research；目标日不匹配 fail-closed。
- 构建证据：官方包 SHA-256 `611ea3ccc1e64717aebc9a14ce9c8b1ed06526b5fd69bd14275fc376f4f44272`；publication `m4-5fd06398dde1d174114e253af4330825`；analysis snapshot `m8-m9-local-reconstructed-preview-v2-fa7ae877fdb0ce0e`；research run `research-5fbbc614e78a42e384f329048792353c`。
- 关系与层级：版本化板块—个股关系 72,537 条；层级节点 553 个，其中 76 个子节点绑定至 22 个父板块；分析成员状态 75,432 条。
- 本地研究：531 个板块全部 `READY`；CURRENT 3 个，CURRENT_FOCUS 9 条，成员角色 2,054 条，关联 13 条；POTENTIAL/EARLY_FOCUS 当日按规则为 0，不用旧数据填充。
- 页面验收：V3 context 指向上述唯一 research run；CURRENT API 返回 3；CURRENT_FOCUS 返回 9；抽查 `INDUSTRY:T020603` 的 ALL_MEMBERS 返回 19/19。
- 清理结果：旧 `data/`、`reports/`、`logs/` 隔离副本已永久删除（不可恢复）；失败重试的重复 release、shadow run、静态 workbench 和失败日志已删除。数据库仅 1 个成功 publication 和 1 个 COMPLETE research run，日期均为 2026-09-11。
- 保留边界：代码、配置、规格/验收文档、Phase 0/模型版本凭据以及生成 9 月 11 日指标所必需的历史行情窗口保留；它们不是旧发布日期。TDX 源始终只读。
- 测试：相关 V3 research/API/UI `12 passed`，P09 在线产品 `20 passed`；Python compile 与 `git diff --check` 通过。全套 V3/M7/M14/M15 为 `334 passed, 21 failed`，21 项均是旧测试强制读取已按用户要求删除的 `reports/upgrade_*` 历史回执，不是当前业务计算/API失败；这些旧静态证据不恢复。P09 运行开关已从被删除回执解耦，改由版本化 capability 配置控制。
- 当前验收：`FULL_PASS`（单日清库重建合同范围）。
- 下一阶段：从页面按后续最新官方交易日增量构建；若目标日与官方包不一致，保持拒绝发布。
