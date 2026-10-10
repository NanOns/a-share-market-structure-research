# Python 模块安全加载计划（未执行）

现状只读检查：127.0.0.1:28765 LISTEN，PID 42552。审计给出的已加载提交为0c9305129cfe90148008d898162f0f40959d1af5；本轮没有证明磁盘新代码已经进入该进程。本轮不重启28765。

需加载的B增量：operational_daily_executor_v1.py、next_t0_identity_preflight_v1.py；A/前轮Publisher/FirstObserved与BFF加载清单须主任务合并后锁定 exact release commit +逐文件SHA。诊断只新增读取，不修改 source gate授权条件。

1. 独立授权窗口前，G:/codex_tmp 上隔离函数预检；如需HTTP隔离，先确认28766空闲，用禁用DailyJobs的研究实例，隔离data/runtime副本，不能连生产Writer/CAS。端口启动仍不是本轮已完成事项。
2. 生产加载需要用户明确授权重启稳定服务。授权后先记录PID/端口/命令行、release commit+代码SHA；查询active_job必须为空，scheduler线程无执行中任务。若有任务，等待自然结束，不杀采集。
3. 在G:/codex_tmp/deployment_backups/<actual_timestamp>/原子备份 data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json 和 data/v4/V4_DATA_ACCEPTED_HEAD.json、scheduler政策/配置及运行loaded SHA；只备份不替换。两Head当前SHA分别55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e与38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40。
4. 原源码/运行版本恢复材料保存到G:隔离checkout，保留现有工作区无关改动；不对运行后已有新采集数据做reset。以已授权启动方式加载exact release，读回PID/端口/loaded SHA，六研究入口、jobs/Head只读健康检查。
5. 加载或读取失败：停止新实例，恢复已保存旧运行版本和配置，以原授权方式恢复服务，Head若未变化不替换；若CAS已经成功产生新日Head，不自动覆写，先保留现场并按原发布合同处理。复验last-good和jobs任务。整个流程不得写TDX。

需许可事项：生产28765停止/重启和具体窗口；如旧身份闸需支持合法新Identity，另行独立合同/准入审批。本轮工程不依赖此许可，真实10/12结果PENDING。
