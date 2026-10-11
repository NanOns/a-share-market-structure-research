# R3 复现脚本

这些脚本保留本轮执行的固定 G: 路径与数据 SHA。重新执行前，在 G:/codex_tmp 的独立副本中调整 ROOT/OUT/BASE 并核对冻结来源；使用 Python -B，TMP/TEMP/TMPDIR 均设 G:/codex_tmp。不要把再执行结果覆盖进历史 R1/R2 或已提交本轮收据。

A4 full_recompute 从已冻结最新原生历史创建新候选，原 Owner 保持不变。recover_report 是编排失败后的候选逐行校验，不能代替 full_recompute 的独立算法断言或完整耗时。Core/rank 脚本只是有限历史敏感性，不授予 PIT/consumer 准入。

A6 启动本轮临时 GET-only HTTP 服务，POST=405；不启动 DailyJobs 或接管生产端口。B1 产生明确有限配置版本索引；源码 literal 锚点不是字段语义通过。
