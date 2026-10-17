# V4 R21-R5 全模块文件引用与 Workspace 集中实修收尾

- 日期：2026-10-18；分支：`codex/v4-workspace-cleanup`。
- 状态：`CODE_SCOPE_PARTIAL / BROWSER_PARTIAL / LIVE_PG_VERIFIED / FORMAL_HEAD_CLOSURE_PENDING`。
- 矩阵代码级状态：264/266 个 P1 调用点已改为 PG-bound 消费/精确源入库路径；1 个旧 Owner successor 转换缺少 operational predecessor/authority source binding；1 个非 V4 consumer 只登记。正式 P1 调用点仍 0/266 完成 source-edge/Head reconciliation，22 条 unmapped edges 未被伪报已解决。
- 数据库：共享 `127.0.0.1:5432/market_research`（OID 646711），本轮仅追加候选/诊断事实并做 PG readback。没有 Accepted Head CAS。
- 端口：浏览器验收使用开发 `127.0.0.1:28766`；生产 `28765` 未触碰。开发服务 PID 42876 在本批修改前启动。自动审查拒绝了停止这一精确 PID 的命令，拒绝原因是阻止停止运行中进程；未以其他命令绕过，因此运行中的后端不是本批代码的新进程。

## 实际代码修复

- 新增 `src/workbench_db/v4_historical_source_ingress_pg_r1.py::admit_bound`：只接收 Head/candidate 明确绑定的相对路径、SHA-256 和可选字节数；首次读源只发生在此入口，append 到共享 PG 后校验 PG 读回 bytes/SHA/size，消费者从 PG 解析。已有 PG 记录只读 PG，不回落到磁盘。
- `v4_membership_reference_pg_v1.py` 的 Membership、identity lifecycle、search identity、research input/sidecars 均接入精确 PG ingress 与候选 Owner 写回；semantic/dependent Profile correction 的 patch 和 producing source 也接入精确 PG ingress，补齐 8 个先前开放的源入库调用点。它们仍是 candidate-only、`publication=false`、不提升 PIT/Head。
- TDX package、target bars、local snapshot manifest、snapshot delta、startup attestation、Daily/BaoStock/runtime consumers 与 workspace path 变更见前序源码修复记录；对应 PG 事实已按下节所列做 append/readback。

## 真实 PG 写入与读回

- 2026-10-12 日更 source candidate：append/readback PASS，4 个来源绑定（Baostock、runtime manifest、TDX target bars、TDX 官方当前包）；包 SHA `47a0da…123801`。
- TDX target candidate：5,212 行，T0 `2026-10-12`，append/readback PASS；保持 candidate-only、非 PIT。
- TDX 本地 snapshot manifest：snapshot `1644752b…c78c70`，12,245 文件、941,724,256 bytes，文件清单验证与 PG manifest readback PASS。
- 官方 TDX package identity：当前包 source ID/T0/revision/CRC/SHA 的 PG readback PASS。
- PG startup/publication reader 连接同一实例；当前无 accepted publication Head（`NO_ACCEPTED_PUBLICATION_HEAD`）。没有执行 Head CAS。
- 本次新增的 8 个 `admit_bound` 消费点已做语法与暂存策略检查；由于当前 Head 不绑定这些 Membership/Profile source，未伪称它们已完成 domain-specific live payload acceptance。

## 28766 浏览器验收

通过 Codex 内置浏览器真实打开并操作：

- 个股：搜索 `600675`，返回唯一 `中华企业 / SH.600675`，显示收盘价 2.520、启动确认/符合。
- 板块：读出 378 条；展示成员数、20/5 会话强度、上涨宽度和来源状态。
- Focus/Forward：Focus 469 条、Forward 117 条、期限计划 585、已发布期限状态 5；展开区域显示未接入字段与候选权限缺口。
- 市场与事件：显示 5,224 分母、5,213 实际行情、14,378.36 亿元成交额及指数/涨跌停统计。
- Diagnostics Jobs：显示 T0 `2026-09-30`、PG 候选快照、source requests 0、next complete session 未记录、未启动 daily worker；缺口含 11 个 profile identity 及 Focus 写入 admission。
- 数据页均明确标识 `PG 候选快照 · 不代表正式 Head`。页面真实渲染与交互通过，但因 PID 42876 未能重启，以上不能证明本次新后端代码已被 28766 加载，故整体仍为 `BROWSER_PARTIAL`。此前已交互的主页、Compare/Replay 与数据更新页记录见旧版升级报告。

## 尚未完成且原因明确

- 唯一仍属本批源码矩阵开放的 V4 调用点：`V4-BCA-R2-7fddcd4c3b5a5c41502c`，`src/workbench_db/v4_operational_owner_authority_v2.py::prepare_successor`。现有 `data/v4/V4_DATA_ACCEPTED_HEAD.json` 是 2026-09-30 数据 Head，没有 predecessor、publication ID 或 operational Owner binding；共享 PG 查询也没有 accepted operational Head。不能生成旧 Owner successor 的来源绑定而不伪造身份。
- 266 个 P1 的正式 inventory/reachability/source-edge reconciliation、22 条未映射 reference edges 仍未完成；本轮没有重复全仓扫描。
- 本批新增源入库 helper 使用精确候选绑定；必须等真实 Membership/Profile candidate bindings 进入流程后才能执行各域 live acceptance。
- 正式 Head CAS/切换、生产部署、物理删除、历史重写、强推不在本轮授权范围。GitHub connector 对 Issue #2/PR #3 返回 403；未用 CLI 绕过。

## 检查与交付

- 只运行最小语法编译、`git diff --check`、强制 staged repository policy 和实际浏览器交互；未运行完整测试、GitHub CLI workflow 或 Actions。
- 提交前保留了已有的 5 个无关 untracked 用户文件，未暂存。
- 最终 commit/push 状态记录于提交完成后追加。
