# V4 R9 扫描器解析补充（2026-10-24）

本补充续接 [R9 续修报告](R9_V4_CONTINUATION_REPAIR_20261024.md)，针对用户澄清的 V4 功能范围修正扫描器依赖判断，不把全仓旧维护代码计作 V4 缺陷。

扫描器此前把 `__import__('json')`、`__import__('time')`、`importlib.metadata` 等标准库调用误报为动态依赖；也不能从有限常量 tuple 中追踪 `importlib.import_module(name)`，因而漏掉明确 allowlist 的验证模块。现改为校验标准库模块解析位置确实落在 Python 标准库、而非 site-packages；对局部 tuple/list/set 字符串常量驱动的导入，扫描器将全部目标加入 V4 依赖图。未知模块、site-packages 模块、非字面量导入和 `exec` 继续保持未解析，仍会阻断门禁。由此历史 Publication Reader 的两个静态 allowlist 依赖已进入图，无需改写其冻结源码。

本轮扫描结果：7 个 V4 入口合同 SHA 通过，入口闭包 652 个文件；2,211 个未裁定字面量候选、0 个自动确认违规、11 条活动闭包内未解析动态边、25 个浏览器 fetch/import 路由。维护脚本里另有 25 条未解析动态边和全仓 5,003 个维护候选，不把它们归为当前 V4 运行缺陷。总门禁仍为 `GLOBAL_RUNTIME_LITERAL_GATE_BLOCKED`，未裁定候选、动态边和 UI 路由不能算扫描通过。

扫描器解析、V4 来源上下文、市场缓存范围及 R43 gzip 写入隔离回归共 `36 passed`。本组测试未导入 DuckDB、未连接数据库。此轮没有 PG 写入、服务/Windows 重启或 Head 变更。完整计数与复现路径见 `R9_V4_SCANNER_RESOLUTION_EVIDENCE_20261024.json`。
