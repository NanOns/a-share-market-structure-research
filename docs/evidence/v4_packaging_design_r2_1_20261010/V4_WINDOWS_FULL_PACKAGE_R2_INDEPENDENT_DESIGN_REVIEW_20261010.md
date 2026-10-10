# 大A V4｜Windows 整体打包与轻量托盘 R2 最终稿独立设计复核

- 审计日期：2026-10-10（北京时间）
- 审计对象：用户提交的 `V4_WINDOWS_SERVICE_CONTROL_CENTER_DESIGN_PROPOSAL_R1_20261010(1).md`，内文 `V4_WINDOWS_FULL_PACKAGE_DESIGN_R2_20261010`（275 行）
- 用户决策：优先整体打包、单桌面入口、轻量托盘、已有 V4 网页；不采用本阶段独立 Supervisor / Windows Service / WPF 管理台
- 仓库：`NanOns/a-share-market-structure-research`，分支 `codex/v4-fp14-r2-repair`；文档声明源码基线 `759573e4da4156dad77aae8aa317420a0a1cae2e`
- 审计方法：直接读提交文件，并核对仓库 `run_workbench_service.py`、`core_product_server_r1.py`、`operational_daily_jobs_v1.py`、`scripts/run_v4_current_daily.py` 等既有源码。审计时远端较文档基线新增一笔 R2 设计文档与收据提交，未核见此笔改变服务业务源码。
- 审计边界：未在用户 Windows 真机编译、安装或运行 EXE，未接管正在运行的 28765；此文件是独立设计意见，不是实现或生产放行。

## 一、唯一裁决

**架构方向：`DESIGN_DIRECTION_ACCEPTED`。按当前文本直接进入无条件 S1/生产接管：`DESIGN_IMPLEMENTATION_CONTRACT_NEEDS_TARGETED_AMENDMENT`。**

R2 的单机、单用户、登录后运行、PyInstaller `onedir` + Windows 安装器选择合理。它清楚保留原日更和正式准入的边界；程序/工作区分离、事务回读、维护退出、跨入口单例、数据与版本回滚约束均有实质质量。无须恢复 R1 的独立 Supervisor、SCM 与 WPF 方案。

但有 **两项 P0 产品/工程遗漏，一项 P0 验收缺口**，应在 S0 合同中订正；其余为 P1/P2，不应扩大为重构。

## 二、逐项审计

| 编号 | 严重性 | 发现 | 证据 | 必要订正 |
|---|---|---|---|---|
| PKG-R2-01 | **P0 产品合同** | R2 托盘菜单只包含“安全退出”，没有用户最初明确提出的“手动启动、停止、重启服务”入口。关闭全部应用再双击不能完全替代在软件内管理服务。 | R2 §3（第64–73行）、§5.1（第113–129行）；原需求为启停重启可操作入口。 | 保持一个主EXE且不新增Supervisor；让**托盘消息循环和内置HTTP/DailyJobs引擎具有独立状态机**。托盘增 `启动引擎`、`安全停止引擎`、`安全重启引擎`、`退出大A应用`、`暂停/恢复日更`。引擎停止后托盘仍可用；“退出应用”关闭全部。按钮须按任务状态启用并反馈进度。 |
| PKG-R2-02 | **P0 打包运行链** | 冻结程序下 `sys.executable` 指向打包 EXE，而不再是通用 Python 解释器。项目存在以 `subprocess.run([sys.executable, '-X', 'utf8', <script> ...])` 运行 Python 子脚本的源码。若该调用属于需打包的生产/恢复能力，将被错误地调用。 | 仓库 `scripts/run_v4_current_daily.py` 中多处 `sys.executable` + 脚本调用；官方 PyInstaller Runtime/Common pitfalls；R2 §4 目前只有概述，无逐实际入口执行合同。 | S0 做**实际可达调用链扫描**（不能武断认为该历史脚本必经当前 `DailyJobs`）。对可达入口采用同一EXE明确子命令分派（例如 `--task=...`）、改模块内调用，或经审计的包内受控执行通路；不回退到系统 PATH/Python。独立回归后才能封版。 |
| PKG-R2-03 | **P0 验收合同** | S1 验收偏重界面可启动、日更开关、退出重进；未明确要求从**真实冻结 EXE**执行一次完整隔离日更 `capture → source readiness → derive → CAS/readback/recover`。可能界面正常但工作任务因动态导入、源码哈希、子进程、运行根而失败。 | R2 §8 S1（第214–219行）以及 §9 验收矩阵。 | S1 添加 `FROZEN_EXE_END_TO_END_PASS`：在独立 G 盘工作区用已归档的可复核来源/合成合法事务，经过打包的EXE完成整条测试工作流和三种失败/重试路径；不能伪造真实当日首获，不能写真实两个Head。无外部Python/PATH；检验所有输出、时间、精确来源SHA和合法CAS。 |
| PKG-R2-04 | P1 用户可用性 | 单机登录后的应用不是登录前常驻服务。应用退出、电脑关机/休眠或未登录时，18:35首次观测可能缺失；重启后可以补日更，但不能补造历史真实 first_available。 | R2 §3第68–73行与 §6.3，设计已说明限制但缺明显运营提示。 | 登录自启设置页及应用首页醒目展示 `CAPTURE_REQUIRES_APP_RUNNING`；下一实际交易日前、目标采集窗口显示休眠/退出风险；错过时标记 `MISSED_REAL_FIRST_CAPTURE`，依事实处理。可选Windows计划任务唤醒仅以后单独评估。 |
| PKG-R2-05 | P1 停机状态机 | 文档正确识别 `DailyJobs.close()` 只等2s及发布读回，但未规定一套够明确的**托盘停引擎、留托盘、再启引擎**状态/边界；补 PKG-R2-01 时须同步。 | 当前 `core_product_server_r1.py::serve_v4` 为 `serve_forever()` + finally close；`DailyJobs` daemon worker + 2 秒 join。 | 定义 `STOPPED/STARTING/RUNNING/QUIESCING/WAITING_SAFE_BOUNDARY/STOPPING/FAILED`；关闭新入队→停止新tick→等待活动任务事务安全终点及必要HTTP回读→shutdown/server_close→线程连接回收→停止；同进程再次启动要重新创建对象，不复用已关闭server/jobs。120秒仅提示，不自动强杀。 |
| PKG-R2-06 | P2 文档治理 | 文件物理名称沿用 `...PROPOSAL_R1...`，内容已是 R2，若把名称当SSOT易错拿旧版。 | R2扉页及 §10。仓库另外已有 `docs/design/V4_WINDOWS_FULL_PACKAGE_FINAL_R2_20261010.md`。 | 指定该R2 canonical为唯一实施基准；R1旧文档作为历史，不用相同文件名无版本引用；实施卡引用 `contract_id` 和精确 Git blob/SHA。 |

### 已经做得正确、可保留的部分

1. **不把持续增长的行情、SQLite/WAL及冻结Head塞入EXE**：R2 §1、§4对于打包资源根、持久G盘工作区的分离合理。
2. **安全退出不等于 `DailyJobs.cancel()`**：避免维护退出使用户任务永久不可重跑，正确。
3. **CAS完成不等于最终已COMMITTED**：保持原HTTP读回与现有 `promote()/recover()`，这是必要边界。
4. **跨入口全工作区单例**：不允许安装版与Python开发入口同时操作同一G盘工作区，方向正确；应将锁置于初始化/恢复前。
5. **受限产品权限**：打包/界面可以合格，却不能自动签发 State/Identity/D2/Cohort/FEP 正式权限，正确。
6. **安装失败与卸载保护**：卸载默认不删数据，禁止将旧Head覆盖新COMMITTED Head，合理。

## 三、最小补充设计（不恢复复杂Supervisor）

### 3.1 一个 EXE、两个内部生命周期

```text
大A交易.exe
  ├─ 托盘/UI消息循环（主线程，持续存在直到“退出应用”）
  │  ├─ 启动引擎
  │  ├─ 安全停止引擎
  │  ├─ 安全重启引擎
  │  ├─ 暂停／恢复自动日更
  │  ├─ 打开 V4 网页／日志
  │  └─ 退出应用（先安全停引擎，再退UI）
  └─ EngineController（内部状态机，非独立Supervisor/服务）
     ├─ ThreadingHTTPServer 127.0.0.1:28765
     └─ DailyJobs/SQLite/原发布与回读事务
```

托盘 `RUNNING/STOPPED` 不等于日更 `AUTO_ON/OFF`。手动 `STOP_ENGINE` 不应伪改用户保留的自动开关；再次启动恢复用户原设置。引擎停止时托盘可以读最后一次已记录的G盘快照，但标注原观测时间、不可称实时；启动时验证端口身份/PID/工作区。若因崩溃整个EXE死亡，首版允许用户再次双击启动，不要求无进程的托盘能够继续存在。

### 3.2 打包运行时的可审计契约

- `APP_RESOURCE_ROOT`：PyInstaller固定资源、网页、必要的源码原件/精确合同（只读）。
- `WORKSPACE_ROOT`：G盘Head、原始证据、运行数据库和用户配置（持久、可写），不同EXE版本不得改变受保护相对来源关系。
- `BUILD_RELEASE_ID`、`SOURCE_SHA`、`RESOURCE_MANIFEST_SHA`、`WORKSPACE_SCHEMA_VERSION`：在GUI/运行API读回。
- 通过 manifest 白名单穷举包内动态导入、脚本子任务、`.py`原件哈希依赖、`.dll/.pyd`、网页/字体（如有）、各资源相对路径；缺一不可用静默fallback。
- 冻结EXE的子任务调用必须有 `FROZEN_TASK_DISPATCH` 明确协议。验证所有**实际可达**的 `sys.executable`/`subprocess` 路径，并保留旧开发入口不受破坏。

### 3.3 S0/S1/S2 建议验收增补

| 阶段 | 新增强制验收，不改变原三阶段边界 |
|---|---|
| S0 | 菜单/状态合同定稿；可达调用图（PyInstaller子进程与根路径）；工作区生命周期单例；引擎线程启动、停止、重启、异常路径；真实发布读回的待机安全停止协议 |
| S1 | 真正打包 EXE 无Python可运行；五类托盘动作（启动/停止/重启/暂停/退出）；EXE E2E隔离完整日更与重试；重复/多端口实例无双写入；主动退出不中断合法回读 |
| S2 | Windows安装/卸载/登录自启/升级回退/1366与1920实机；生产接管须独立授权，真实新日首获与完整FP14发布门各自独立 |

## 四、下一步决策

**建议：仅对现有R2做定点 R2.1 合同补充，然后正式授权S0隔离实施。**

- 不回退到 R1 的两个独立EXE加Windows Service。
- 不要求打包前解决FEP/正式Cohort/历史PIT，而是严格保持原权限。
- 不因 2026-10-12 当晚采集窗口而冻结S0/S1隔离开发；不在未经另行批准前替换仍在运行的生产28765。
- 如用户明确接受“停止整个应用，再双击启动”而无需**软件内直接重启**，则 PKG-R2-01 可以产品需求取舍降级；在此之前应按原始需求保持 P0。

## 五、最终结论

**`DESIGN_DIRECTION_ACCEPTED / TARGETED_AMENDMENTS_REQUIRED_BEFORE_UNCONDITIONAL_BUILD`**。

R2值得采用，其复杂度与用户本阶段目标相匹配。真正要补的是服务启停入口的产品需求闭环、冻结后子任务执行合同以及从真实打包EXE完成完整日更验证。这三项做完即可进入S0/S1的工程实施，不需要架构推倒重来。

### 来源提示

- 用户提交R2文档（本次上传）。
- GitHub原项目源码：`run_workbench_service.py`、`src/workbench_service/core_product_server_r1.py`、`src/workbench_analysis/operational_daily_jobs_v1.py`、`scripts/run_v4_current_daily.py`。
- PyInstaller官方运行路径及冻结程序子进程说明：`https://pyinstaller.org/en/stable/runtime-information.html`、`https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html`。
