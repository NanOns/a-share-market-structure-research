# FOCUS-07A-01 Daily Builder 修复记录

| 字段 | 记录 |
|---|---|
| applicable_upgrade | `D:/Users/lps/Desktop/FOCUS_CONTINUOUS_TRACKER_CLOSURE_PLAN_V1_1_20260924.md` 第 5 节、38 节；仓库 `docs/DAILY_FOCUS_TRACKER_FINAL_DESIGN_V2_1_20260923.md` 第 6、7、10 节 |
| stage_contract | 将已存在的首日 manifest、observation 批次构建和首日核心事务从 `probe` 实现提取成正式实现；首日发布入口不再导入 probe；probe 调用同一正式实现。此步保持 V1 状态算法、输入身份及首日事务语义。 |
| evidence | 新增 `src/focus_tracker/daily_manifest.py`、`src/focus_tracker/daily_builder.py`、`scripts/run_focus_initial_core_transaction.py`；三个 probe 脚本保留兼容入口并委托正式实现；`scripts/run_focus_core_publication.py` 改用正式实现。相关 Focus 03 测试 10 passed；使用项目 `PYTHONPATH=src;scripts` 的正式入口导入成功；Python 编译通过；`git diff --check` 通过。 |
| acceptance_result | `FULL_PASS / 07A-01_PRODUCTION_PROBE_DEPENDENCY_REMOVED`。范围仅为现有首日构建与事务的依赖方向；不宣称多日发布已完成。 |
| next_stage | `07A-02 Daily Runner`：基于正式 builder 定义显式批次返回合同并实现有前态的每日 preflight/apply；随后处理 tracking union、次日路径与历史窗口。 |

现有工作区中 `data/current` 和 `reports/p12_*` 的修改早于本阶段，本阶段未触碰。技术结果 hash 的跨领域修复仍保留为独立审计项，不由本阶段验收代替。
