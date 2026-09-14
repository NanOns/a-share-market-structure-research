# V3 本地服务托盘与控制入口

## 阶段合同

- 合同：`WORKBENCH_LOCAL_SERVICE_CONTROL_V1`
- 范围：本机 `127.0.0.1:28765` 工作台服务
- 判定：`FULL_PASS`

## 实现

`START_WORKBENCH_TRAY.cmd`启动Windows通知区域托盘。托盘每3秒只读查询服务状态，显示运行/停止和PID，并提供打开V3、打开运维中心、启动、受控重启、受控停止、退出托盘、停止服务并退出。托盘启动服务时使用隐藏窗口，且通过命名互斥量避免重复托盘实例。

服务新增`POST /api/operations/stop`，与既有受控重启共用CSRF、维护确认、活动任务和维护锁门。`GET /api/operations/status`增加服务PID、URL和控制合同。运维中心顶部新增明确的“服务控制”区，重启按钮自行提交维护确认并在新服务健康后显示结果。

`OPEN_UNIFIED_WORKBENCH.cmd`现统一启动托盘；托盘确保服务就绪后打开V3。TDX输入目录、生产数据和静态关系均未修改。

## 验收

- PowerShell托盘脚本语法解析通过。
- 服务控制、重启监督和V3入口定向测试7项通过。
- Python编译与`git diff --check`通过。
