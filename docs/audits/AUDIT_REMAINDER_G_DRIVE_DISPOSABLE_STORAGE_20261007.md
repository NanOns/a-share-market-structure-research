# G 盘测试临时空间独立审计项

范围：按用户“E 盘空间不足时临时文件放 G 盘”的明确约定，允许本轮测试选择 `E:/codex_tmp/test_temp` 或 `G:/codex_tmp/test_temp`。

原 `tests/runtime_isolation.py` 与 `tests/runtime_isolation_plugin.py` 源码保持不变。新增 `tests/remainder_storage.py` 只接受两个显式根目录；本轮插件在测试进程中选择该根目录，服务子进程在调用原 `serve()` 前做同样的选择。原 protected-root、数据库必须位于隔离目录、disposable marker 和恢复模式检查继续执行。其他盘符、项目及 TDX 根目录仍被拒绝。生产入口不加载这项测试适配。

隔离 PostgreSQL 仍绑定已记录的 E 盘数据目录和端口，不因测试 TEMP 改为 G 盘而允许其他实例。历史 Git 副本与大文件放 G 盘。曾被自动审批拒绝清理的 E 盘目录保留。

验收证据：`remainder_g_scope_final` 中的保护负例、真实 M12 服务子进程，以及最终全量回归；实际计数和失败保留在本轮 execution 目录。此项与 IA05 及 TDX 写入事件分别跟踪，测试适配不授予真实恢复或任何运行权限。

FEP E2/E3/E4 和 forward R2 CLI 的小型工程产物继续使用 E 盘隔离目录，以满足原 E/F 存储合同；大型副本和其他临时输出使用 G 盘。专项验证 remainder_bounded_g_storage_final：108 passed。
