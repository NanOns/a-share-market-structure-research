# DD R2.2 数据优先执行结果（2026-10-10，Asia/Shanghai）

最终总体状态：**DATA_CHAIN_BLOCKED_PROD_RELOAD**。本轮现在可执行的只读预检、隔离回归、两板块补强及轻量归档已完成；A 未通过，B 真实后继日尚未发生，不自签外部通过。

BASE_SHA：302a40113576b38bb4b7e0b01192c415e320d67c（执行前 git fetch origin 后核实；工作分支 codex/v4-fp14-r2-repair，原工作树无用户修改）。RESULT_SHA：268f1ee84cf00cd355f0b96afda55818834eefe2（脚本及工程证据提交；最终归档提交与远端对齐另见 DELIVERY_READBACK.json）。没有修改生产数据算法或旧 Head。

P0-A：PID 41528，E:/python/pythonw.exe，真实启动 2026-10-09T21:44:51.150154+08:00；命令为 run_workbench_service.py --v4-default --host 127.0.0.1 --port 28765，入口明确定位到 G:/codex work/大A交易。它早于最终 executor/source gate/V2 adapter 源码修改。六文件的磁盘 SHA、mtime、Git blob/ref 已归档；当前进程内部实际模块路径和加载 SHA 未有可核实回执，不能用磁盘文件或 HTTP 200 替代。没有正常重载，PROD_RELOAD_REQUIRED。原 AUTO=ON，worker_error=null，无活动 Job。

当前 context、operations/status、stocks、sectors、market、focus 六读端点均为 HTTP 200、同一 10/09 token；六个旧 token 请求均 409。10/09 运营 Head 55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e，严格 PIT Head 38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40，旧 DAY_RECEIPT SHA 1b0da91a2dc953fbcaa408433977cd90cff1ab7ea222052a8b4fa68e1a9fc2d1 全部未变。

P0-B：按已接受日历字节与官方 SSE/SZSE 协议复核，10/09 后首个交易日为 2026-10-12；10/10 不在 session_dates。首查 2026-10-12T18:35:00+08:00。现实时间门未成熟，未请求未来目标的 TDX/BaoStock 日线/因子，未造 10/12 行数、未派生、未 CAS；状态 PROD_DEPLOYMENT_BLOCKED / WAIT_REAL_SESSION。冻结 10/09 来源的原 SHA、观测时间、日线/停牌/因子数量仅作为历史预检列出，绝不是 10/12 来源证据。真实新日 RAW/QFQ、周/月、Core/RPS、板块/Market/Focus、Owner QA 与新 token 六接口均 NOT_RUN_NEXT_DAY。前轮 DATA_NUMERIC_SAMPLE_EXTERNAL_PASS 保留；不重跑旧 4GB Owner。

P1-C：C_PASS_SCOPED。以冻结 10/09 TDX 原始成员快照和 dated identity/lifecycle 过滤，按有效成员数降序、sector_id 升序确定选样，行业要求原始叶级，概念要求原文件 GN 分类；没有编造热门/主线。

| 对象 | 编号 | 有效成员 | 独立复算范围 |
|---|---|---:|---|
| 电气设备（TDX INDUSTRY） | INDUSTRY:T0706 | 322 | ret1/ret5 中位数、上涨比例、已知分母、一个实际 LOO 目标 |
| 智能机器（TDX GN CONCEPT，内部名 THEME） | THEME:880904 | 1160 | 同上 |

完整紧凑成员贡献、停牌状态、等权与有效分母、核心输入 SHA、成员 authority 行及原始来源 SHA 均在 178839 字节 ZIP 中。独立标准库脚本离线 18 项检查，0 差异，CRC/载荷 SHA 全通过。成员 as-of 是 2026-10-09T09:44:01.158745+08:00，RECONSTRUCTED_LATEST_MEMBERSHIP，AS_RECORDED/PIT_ELIGIBLE=false。不证明全板块、完整 relative state、全部 Market 轴或全市场上游收益率。

隔离预检回归：33 passed，9.34 秒，退出码 0。真实命令与输出在关键 JSON；测试临时路径 G:/codex_tmp/test_temp/dd_r22_preflight。不是真实下一交易日发布验收。

人工重载指引（当前不能由我代做）：
1. 核对上述 PID/命令，仅处理这一个工作台服务；关闭浏览器或“退出托盘（服务继续）”不会停止它。
2. 使用原有管理工具正常退出旧服务。当前仓库 V4 只读服务没有停止 HTTP 路由，托盘“停止/重启”实际禁用；若没有正常退出入口，保持 PROD_RELOAD_REQUIRED，不以 taskkill /F、强制结束或修改 ACL 替代。
3. 旧服务正常退出后，确认 28765 不再监听；不要在仍占用时启动第二个实例。
4. PowerShell 设置临时目录：`$env:TMP='G:/codex_tmp'; $env:TEMP=$env:TMP; $env:TMPDIR=$env:TMP`。
5. 从项目主目录执行 `& 'E:/python/python.exe' -X utf8 -B 'G:/codex work/大A交易/scripts/start_dd_r22_attested_workbench.py'`。该入口只做真实模块导入取证，然后启动既有 serve_v4/AUTO；端口占用会直接拒绝，不停止任何进程。后续可在此启动终端用 Ctrl+C 正常退出。
6. 通知当前任务复验新 PID、runtime/dynamic_daily/loaded_modules_r22.json、原 Head/AUTO 与六 HTTP；这些事实通过后才可 A-PASS。

可重复预检：在 G 盘临时环境下运行 `python scripts/audit_dd_r22_data_first.py`（先把当前工作台进程身份写入 G:/codex_tmp/dd_r22_process.json）。C 离线命令见 ZIP README。10/12 首查之后，只有 A-PASS 且真实三源共同 VERIFIED 才允许既有 AUTO 派生/CAS；任何缺口保留 last-good，按既有有界重试。真实 B 的首个失败当前尚不存在，不能预判来源成功或失败；失败时仅定点归档首节点及 5–20 条异常样本。

本轮归档只新增 MD、关键 JSON、178839 字节板块 ZIP 三个文件；预算预检及上传/原始字节回读见 DELIVERY_READBACK.json。没有上传完整 Owner、551MB ZIP 或数据库。DD-A01/A02/A05/A06/A07/A08 保持独立 OPEN，TDX Native Amount 主权威不变；Windows 整机重启不在本轮范围。

此前自动审批拒绝“停止并重载 PID 41528 工作台服务”，返回 blocked by policy，未给出进一步原因。本轮不重试、不绕过；生产重载和未来真实新日验收明确保留未完成。
