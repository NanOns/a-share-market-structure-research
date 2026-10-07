# 增量构建连接生命周期独立审计项

- 状态：CANDIDATE_FIXED_SUBJECT_TO_EXTERNAL_REVIEW。
- 范围：`IncrementalBuildCoordinator.execute()` 与 DuckDB/PostgreSQL 增量仓库连接协议的衔接。仓库 `connect()` 返回上下文管理器，协调器旧实现直接调用其 `execute()` 和 `close()`，导致实际写入路径失败。
- 初始证据：`remainder_full_b.xml` 中 P04-02 增量写入和集成测试出现 `_GeneratorContextManager` 无 `execute`/`close` 方法。原始完整失败日志保留在本轮 execution 目录。
- 修复：协调器使用 `with self._connect() as connection` 获取真实连接。事务仍在全部对象、复用和 snapshot binding 成功后提交，错误仍执行回滚；连接退出由仓库上下文负责。
- 合同边界：不改变构建计划、因子数值、身份摘要、写入对象集合、幂等规则、提交前置条件或数据库约束。不更新 accepted heads，不授予运行权限。
- 局部验收：现有 P04-02 写入和集成测试 17 项通过，涵盖幂等复用、相邻 cutoff、失败回滚和 snapshot/task 范围拒绝；完整回归与最终 source binding 另行封存。
- 独立性：此项与 IA05 全局门禁分别跟踪；局部修复不等于本轮总验收通过，也不消除 TDX 只读边界事件。
