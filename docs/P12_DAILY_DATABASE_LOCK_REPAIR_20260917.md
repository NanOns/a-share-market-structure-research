# P12 页面生成数据库锁修复验收（2026-09-17）

## 阶段合同

本次适用最新的 `P12_DAILY_PAGE_GENERATION_REPAIR_V2`，修复合同为 `P12_DAILY_DATABASE_LOCK_REPAIR_V1`。Phase 0 当前门为 `FULL_PASS`。TDX 源目录仅读；本阶段不运行数据生成，仅修复发布器数据库锁竞争和失败状态呈现。

## 故障证据

- 页面任务：`daily-6f39ee560b104624ae59a6f36c3e613f`。
- 发布子任务：`job-80a1e9abfd47b82dc6a21c021e75a7e6`。
- `job_attempts` 记录 `IOException`：Windows 拒绝打开 `data/database/market_research.duckdb`，原因为文件被其他进程短暂占用。
- 状态轮询在父任务已失败后仍重新读发布子任务，将已捕获的错误覆盖为 `COMPUTING`，导致页面只显示“请查看服务日志”。

## 修复与验收

- 发布器对 DuckDB 文件占用增加 15 秒有界重试，仅重试可识别的文件锁 `IOException`，其他异常仍立即 fail closed。
- 失败时写入带异常类型和消息的 `FAILED` 事件，内存终态状态直接返回真实错误。
- 日常任务已进入 `FAILED/SUCCESS` 终态后不再被子任务轮询覆盖。
- 定向回归：`tests/upgrade_m4/test_one_click_publication.py`，`15 passed`。
- `compileall` 与定向 `git diff --check` 通过。

阶段验收结果：**FULL_PASS**。

## 下一阶段

重启本地工作台服务并只做健康检查。数据生成由用户在页面手动触发。

## 二次故障补充验收

用户手动触发的 `daily-dc0fdfc2c11840ae940cd3a9e2de40c5` 证明首次修复覆盖范围不完整：发布成功后，`build_m8_m9_preview.py` 仍以独立 Python 进程打开生产 DuckDB，而页面 HTTP 请求可在服务进程内同时打开该库。这违反 Windows 下 DuckDB 的跨进程访问约束。

补充修复合同为 `P12_DAILY_DATABASE_PROCESS_OWNERSHIP_REPAIR_V2`：

- `build_m8_m9_preview.py`、`build_m10_mainline_preview.py` 和 `run_p12_daily_pipeline.py` 三个会访问生产库的子进程，统一经由服务的数据库独占边界执行。
- 独占边界先公布 `database_subprocess_active`，再等待已在进行的 HTTP 数据库请求退出，然后启动子进程；此顺序关闭了检查与加锁之间的竞争窗口。
- 构建期间仅保留任务状态、健康检查和静态资源访问；会访问生产库的页面 API 返回可重试的 `503 DATABASE_BUILD_IN_PROGRESS`，不再与构建子进程抢占文件。
- 再次定向回归：`15 passed`；`compileall`、定向 `git diff --check` 通过；三个生产库子进程入口已无绕过独占边界的直接调用。

补充阶段验收结果：**FULL_PASS**。下一阶段仍为重启服务后由用户手动触发，不由修复过程生成数据。

## 第三次锁竞争审计

`daily-814455c1898340d38fedf60d80597b62` 在同一个 `build_m8_m9_preview.py` 子进程中先成功打开第 537 行的只读连接，关闭后在第 584 行打开写连接时被服务 PID 60104 占用。这证明不是子进程自身未释放，而是被放行的 `/api/operations/status` 调用了 `MaintenanceService.status()`，在子进程两次连接的间隙重新打开了生产库。

修复合同升级为 `P12_DAILY_DATABASE_PROCESS_OWNERSHIP_REPAIR_V3`：数据库构建独占期间，健康接口仅返回启动时已缓存的运维信息和内存任务状态，并显式标记 `database_access=SUSPENDED_FOR_BUILD`，不再打开 DuckDB；`/api/jobs` 只允许读取内存中的当日任务，其他任务查询返回可重试 503。定向回归 `15 passed`，`compileall` 和定向 `git diff --check` 通过。

第三次阶段验收结果：**FULL_PASS**。
