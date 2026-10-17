# V4 R21-R5 全模块文件引用与 Workspace 集中实修收尾

- 日期：2026-10-18；分支：`codex/v4-workspace-cleanup`。
- 状态：`CODE_SCOPE_PG_BOUND_CANDIDATE_COMPLETE / LIVE_PG_PASS / BROWSER_PASS_CURRENT_28766 / FORMAL_HEAD_RECONCILIATION_PENDING`。
- 范围：集中修复现役 V4 的历史源 ingress、Operational Owner authority、Workspace 来源路径与前端调用链；非 V4 调用点只登记。

## 代码与调用点

- V4 P1 基线 266 个调用点中，265 个已有 PG-bound candidate/consumer 路径；1 个非 V4 调用点登记为 out of scope。22 条历史 reference edge 无精确 join，正式 Head/source-edge reconciliation 仍为 0/266，未宣称正式发布闭环。
- `v4_historical_source_ingress_pg_r1.py::ingest_file`：仅在显式 Head/candidate source-ingress 且精确 SHA 校验失败时解析 Git LFS pointer，读取对应 `.git/lfs/objects` 对象并校验 pointer SHA、文件 bytes 和对象 SHA；数据库消费者不回读工作区。
- `v4_operational_owner_authority_v2.py`：支持旧 `V4_DATED_OPERATIONAL_RECONSTRUCTED_OWNER_V1` predecessor，按精确 Owner binding 从 PG ingress 读取；新增 `prepare_legacy_candidate` 生成 candidate-only authority/descriptor。
- `v4_operational_predecessor_pg_v1.py::prepare`：PG current predecessor 保留精确 CAS identity check；当 successor candidate 精确绑定旧文件时，在一次性 ingress 边界导入其 SHA/bytes 校验源至 PG fact 并 readback，再由现有 `prepare_successor` 继续处理。该 legacy predecessor 不被标成 accepted Head。
- 直接调用 `prepare_successor` 全链路通过：PG predecessor fact、88 个 Owner domain payload 和 authority manifest 校验完成，`publication=false`、`accepted_head_changed=false`。

## 共享 PostgreSQL 实际读写

- 实例：`127.0.0.1:5432/market_research`，OID `646711`；Schema `v4_forward_812843566da3f180`。
- candidate source：`data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json` SHA `55d78be5…acf4dc83e`（29,799 bytes）；predecessor：`data/v4/predecessors/e751fb6e…d853c8.json` SHA `e751fb6e…d853c8`（17,096 bytes）。
- Owner authority manifest fact key `ec708c8f…d67e15e`；candidate descriptor fact key `19b26172…21d1d2`。全链路 `prepare_successor` 又验证了 88 个 Owner domain，PG readback 成功。无 Accepted Head CAS。
- 未另起 PostgreSQL 实例/端口。之前日更 source candidate、TDX snapshot/package 等 append/readback 结果见上一版升级记录。

## 28766 真实浏览器验收

- 开发服务 `127.0.0.1:28766`；生产 `28765` 未触碰。首页、个股列表/详情、板块列表/详情、Focus/Forward、市场与事件、Diagnostics Health/Jobs/Sources/Contracts、比较和冻结回放均真实打开。所有数据页均标记 `PG 候选快照 · 不代表正式 Head`。
- 板块详情「区域地产」43 名成员；交互搜索「中华企业」精确返回 1 条（SH.600675，收盘 2.520），可进入个股详情。
- 个股日线实际显示截至 `2026-09-30`、120/253 根及蜡烛图；通过浏览器周期控件选周线后显示 54/54 根周线蜡烛图，`/api/v4/stocks/{id}/chart?period=W` 实测 HTTP 200、状态 READY；再切回日线正常。行情周期交互验收通过。
- 比较页显示严格 PIT 可用日期 0、模型为重建版本。冻结回放缺口抽屉显示 `PG_CANDIDATE_SNAPSHOT`、`AS_RECORDED=false`，原因是缺少 first-available-at-T0 证明；页面正确阻止将重建数据伪报为 PIT。
- 28766 PID `42876` 于本轮 Owner/predecessor 后端改动前启动；停止该精确 PID 的操作被自动审查拒绝，未通过其他命令绕过。Owner/predecessor 新路径由直连 PG 的 `prepare_successor` 全链路 readback 验证；浏览器覆盖该进程当前服务的 V4 页面和 API 行为。当前网页服务只有 `127.0.0.1:28766` 在监听；`28765` 未监听；PostgreSQL 仍为 `5432`。

## 剩余开放点

- 正式 266 个 callsite 与 accepted publication Head、source edge、T0/namespace 对账未关闭；22 条 reference edge 仍 unmapped，当前 PG 无 accepted operational publication Head。本轮没有构造来源身份或做 Head CAS。
- 未运行全仓基线扫描、GitHub CLI 流程测试、完整测试套件或 GitHub Actions；执行了最小语法编译、JSON parse、`git diff --check`、staged repository policy 和真实浏览器交互。
- 未执行正式 Head 切换、生产 28765 部署、物理删除、历史改写或强推。正常提交/推送不表示正式数据发布或生产验收。
- 保留原有 5 个无关 untracked 文件，未暂存。
