# P12 页面一键生成修复验收（2026-09-16）

## 阶段合同

本次依据 `P12_DAILY_ONE_CLICK_INPUT_REPAIR_V1` 和 P12-06/P12-12 完整发布要求，修复合同为 `P12_DAILY_PAGE_GENERATION_REPAIR_V2`。Phase 0 当前门为 `FULL_PASS`。TDX 源目录只读；市场总体的 `tdxhy.cfg` 必须从当次发布绑定的不可变 source bundle 和 metadata snapshot 解析，不得猜测旧的按交易日目录。

## 故障与修复

页面任务 `daily-b8a23237844444029b3371bbdd7c46e8` 已完成 2026-09-16 输入封存、正式发布和 M8/M9，但研究构建仍读取 `data/input_staging/metadata/20260916/T0002/hq_cache/tdxhy.cfg`，在 metadata 已按 snapshot ID 版本化后返回 `MARKET_UNIVERSE_SOURCE_MISSING`。P12-12 Full LOO 存在同类遗漏。

修复后，研究构建和 P12-12 均从 publication 的 source bundle 解析 `metadata.root`，校验 bundle ID、项目边界和文件 SHA-256；只对旧发布保留日期目录兼容路径。页面错误文案同时修正为直接显示 `job.progress.error`。

## 证据与验收

- 定向测试：`5 passed`；`compileall` 和 `git diff --check` 通过。
- 真实研究构建：`research-83e436e0e8be44a189b6fe9a247af799`，`COMPLETE`，6,184 股、531 板块、25 短名单。
- P12-12：`FULL_PASS`，56 候选，9 TRUE / 47 FALSE / 0 UNKNOWN。
- P12 整链：发布 `m4-76df0b33d52b49518b72dcec0415c6f3` 返回 `READY`，10 个必需阶段全部完成。
- 页面同入口无人工接力验收：任务 `daily-fbdb4b31a25347379693fd1ac5e1f97e` 最终 `SUCCESS/READY`，交易日 2026-09-16，发布 `m4-f12020c80155a9b60005f6107fd0a760`，研究运行 `research-c8d8fb4a3a934130bdb44a3872487773`，V3.3 bundle digest `292e9881...a22c`。

阶段验收结果：**FULL_PASS**。

## 下一阶段

恢复从页面直接使用“生成今日数据”。后续新交易日依次封存 source bundle、发布、研究运行和 P12 包；任一身份或摘要不匹配时仍 fail closed。
