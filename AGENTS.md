# Project guardrails

1. `D:/new_tdx` and every configured TDX source directory are read-only inputs.
2. Never create, modify, rename, or delete a file under the TDX root.
3. Phase 0 must finish with `FULL_PASS`, `DEGRADED_PASS`, or `BLOCKED` before scanner work begins.
4. M14 online enhancement is allowed for the approved public-source datasets through versioned source contracts, explicit per-dataset capability gates, auditable timestamps, bounded requests, and fail-closed degradation. It must not use external adjustment services, future data, automated trading, or probability claims; it must not alter local snapshot identities or block the local main flow. M14 hot-rank direct mode is request-time only: no hot-rank raw payload, row, batch, or historical snapshot is persisted.
5. Every factor and scanner must have an explicit, versioned contract and explainable output.
6. Project artifacts are written atomically outside the TDX root.
7. Before executing each stage, consult the latest applicable upgrade document and record the stage contract, evidence, acceptance result, and next stage; tests alone do not establish release readiness.
8. Cross-cutting or comprehensive audit issues (for example, M10 Amount A, but not limited to it) must be opened and tracked as separate audit items, with scope, evidence, and acceptance independent from the current stage gate.
9. After each authorized stage task completes, commit and push the relevant code and evidence artifacts to Git. Preserve unrelated worktree changes; do not treat a push as external acceptance or permission to enter the next gated stage.

10. User storage instruction (2026-10-09): all new Codex temporary files, tests, caches and workspaces are placed on G: only; use G:/codex_tmp and G:/codex work. This supersedes older E/F preferences.

## 服务端口与数据库约束（用户指令，2026-10-15）

11. 本项目网页/API 服务只使用两个固定端口：生产服务 `127.0.0.1:28765`；同时进行开发、修复或合并分支验证的唯一服务 `127.0.0.1:28766`。所有开发分支共用 28766 槽位，切换分支时先停止旧分支服务；不得另起其他端口的候选、预览、验收或调试服务，也不得占用或重启生产 28765 来验证分支。
12. 常规小开发、小修复及分支预览默认复用生产的同一个 PostgreSQL 实例、同一个数据库端口、同一个逻辑数据库和同一套数据源；当前为 `127.0.0.1:5432/market_research`。不得仅因切换分支或进行普通验证而复制数据库、新建数据库实例、另开数据库端口或复制数据源。凭据沿用项目现有安全配置，不得写入本文件或日志。
13. 共用数据库不代表可以随意修改生产数据：分支预览默认使用只读权限，不启动重复的自动任务、采集器或写入 worker；需要写入、迁移或破坏性测试时，必须先明确所需数据操作及其影响。只有存在明确的数据测试、迁移验证、隔离写入或其他实际隔离需求时，才可按任务范围复制数据库用于测试开发，并记录原因、来源、目录、端口和清理责任。
14. 确需隔离数据库时，原则上仅保留生产和一个必要的测试数据库实例，所有新测试数据和临时目录放在 G:。临时数据库和测试进程在任务结束后应正常关闭并按任务授权清理，避免后台残留。启动或交付前核对本项目监听端口、进程和数据库连接，报告实际网页端口与数据库端口；不得将 PostgreSQL 内部子进程数量误报为数据库实例数量。
