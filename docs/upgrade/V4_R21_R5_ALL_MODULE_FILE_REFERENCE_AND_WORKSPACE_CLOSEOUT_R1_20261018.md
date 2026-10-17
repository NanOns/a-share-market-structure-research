# V4 R21-R5 全模块文件引用与 Workspace 集中实修收尾

- 日期：2026-10-18；分支：`codex/v4-workspace-cleanup`。
- 状态：`CODE_SCOPE_PG_BOUND_CANDIDATE_COMPLETE / LIVE_PG_PASS / BROWSER_PARTIAL_28766_OLD_PROCESS / FORMAL_HEAD_RECONCILIATION_PENDING`。
- 范围：集中修复现役 V4 的历史源 ingress、Operational Owner authority、Workspace 来源路径与前端调用链；非 V4 调用点只登记。

## 代码与调用点

- V4 P1 基线 266 个调用点中，265 个已有 PG-bound candidate/consumer 路径；1 个非 V4 调用点登记为 out of scope。22 条历史 reference edge 无精确 join，正式 Head/source-edge reconciliation 仍为 0/266，未宣称正式发布闭环。
- `v4_historical_source_ingress_pg_r1.py::ingest_file`：仅在显式 Head/candidate source-ingress 且精确 SHA 校验失败时解析 Git LFS pointer，读取对应 `.git/lfs/objects` 对象并校验 pointer SHA、文件 bytes 和对象 SHA；数据库消费者不回读工作区。
- `v4_operational_owner_authority_v2.py`：支持旧 `V4_DATED_OPERATIONAL_RECONSTRUCTED_OWNER_V1` predecessor，按精确 Owner binding 从 PG ingress 读取；新增 `prepare_legacy_candidate` 生成 candidate-only authority/descriptor。
- `v4_operational_predecessor_pg_v1.py::prepare`：PG current predecessor 保留精确 CAS identity check；当 successor candidate 精确绑定旧文件时，在一次性 ingress 边界导入其 SHA/bytes 校验源至 PG fact 并 readback，再由现有 `prepare_successor` 继续处理。该 legacy predecessor 不被标成 accepted Head。
- 直接调用 `prepare_successor` 全链路通过：PG predecessor fact、88 个 Owner domain payload 和 authority manifest 校验完成，`publication=false`、`accepted_head_changed=false`。
- 继续定向检查发现 `core_product_bff_r1.py::dated_product_manifest` 仍保留 legacy R1/R2 JSON authority 回退；已收紧为只接受 Head-bound PG catalog，要求 candidate 含 PG descriptor，并从 PG readback 后核对 Owner/catalog digest。隔离行情候选路由 `exact_candidate_chart_r3.py` 改为从 `accepted_api` candidate 载入 PG catalog，不再读取本地 `core_product_read_authority_r1.json`。

## 共享 PostgreSQL 实际读写

- 实例：`127.0.0.1:5432/market_research`，OID `646711`；Schema `v4_forward_812843566da3f180`。
- candidate source：`data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json` SHA `55d78be5…acf4dc83e`（29,799 bytes）；predecessor：`data/v4/predecessors/e751fb6e…d853c8.json` SHA `e751fb6e…d853c8`（17,096 bytes）。
- Owner authority manifest fact key `ec708c8f…d67e15e`；candidate descriptor fact key `19b26172…21d1d2`。全链路 `prepare_successor` 又验证了 88 个 Owner domain，PG readback 成功。无 Accepted Head CAS。
- 未另起 PostgreSQL 实例/端口。之前日更 source candidate、TDX snapshot/package 等 append/readback 结果见上一版升级记录。

## 28766 真实浏览器验收

- 开发服务 `127.0.0.1:28766`；生产 `28765` 未触碰。首页、个股列表/详情、板块列表/详情、Focus/Forward、市场与事件、Diagnostics Health/Jobs/Sources/Contracts、比较和冻结回放均真实打开。所有数据页均标记 `PG 候选快照 · 不代表正式 Head`。
- 本轮复开 Codex 内置浏览器核验首页、个股列表及搜索（“中华企业”精确 1 条，SH.600675，2.520）、板块列表、关注/Forward、市场与事件、Diagnostics；页面加载真实记录并未停留在加载态。此前已验证个股日/周线交互、比较和冻结回放。
- 板块详情「区域地产」43 名成员；交互搜索「中华企业」精确返回 1 条（SH.600675，收盘 2.520），可进入个股详情。
- 个股日线实际显示截至 `2026-09-30`、120/253 根及蜡烛图；通过浏览器周期控件选周线后显示 54/54 根周线蜡烛图，`/api/v4/stocks/{id}/chart?period=W` 实测 HTTP 200、状态 READY；再切回日线正常。行情周期交互验收通过。
- 比较页显示严格 PIT 可用日期 0、模型为重建版本。冻结回放缺口抽屉显示 `PG_CANDIDATE_SNAPSHOT`、`AS_RECORDED=false`，原因是缺少 first-available-at-T0 证明；页面正确阻止将重建数据伪报为 PIT。
- 28766 PID `42876` 于本轮 Owner/predecessor 后端改动前启动；停止该精确 PID 的操作被自动审查拒绝，未通过其他命令绕过。Owner/predecessor 新路径由直连 PG 的 `prepare_successor` 全链路 readback 验证；浏览器覆盖该进程当前服务的 V4 页面和 API 行为。当前网页服务只有 `127.0.0.1:28766` 在监听；`28765` 未监听；PostgreSQL 仍为 `5432`。
- 当前 28766 进程也早于最后这次 BFF helper 修复启动；活跃页面浏览器验收覆盖该服务版本中原本已走 PG 的正常 BFF 路由。最后收紧的 helper 与隔离 exact-candidate 路由完成语法和 diff 验证，但没有把这两个新代码路径冒称为已在此旧进程上运行验证。

## 剩余开放点

- 正式 266 个 callsite 与 accepted publication Head、source edge、T0/namespace 对账未关闭；22 条 reference edge 仍 unmapped，当前 PG 无 accepted operational publication Head。本轮没有构造来源身份或做 Head CAS。
- 22 条 unmapped edge 行涉及 21 个唯一调用点 ID（`src/workbench_analysis/v4_current_stage_authority.py:53` 对应两条 edge）：`scripts/capture_dm01_a01_r3_tdx_package.py:48`；`src/workbench_analysis/historical_binding_routing_remainder.py:45`；`tdx_latest_daily_source_v2.py:144`；`tdx_local_daily_fallback_v1.py:32`；`tdx_local_snapshot.py:21,87`；`tdx_member_retro_r43.py:57,115,117,139,170`；`tdx_official_daily_source.py:65,151,395,430`；`tdx_snapshot.py:16,94`；`v4_13_accepted_contract_package.py:78`；`v4_current_stage_authority.py:42,53,53,56`。这些调用路径已有 PG candidate 实现；待完成的是历史 inventory 的精确 edge join。唯一未改的非 V4 点是 `V4-BCA-R2-3a03bb9b0ef3ec4fa6a3`，`src/workbench_analysis/history_170_v3_3.py:13`。
- 未运行全仓基线扫描、GitHub CLI 流程测试、完整测试套件或 GitHub Actions；执行了最小语法编译、JSON parse、`git diff --check`、staged repository policy 和真实浏览器交互。
- 未执行正式 Head 切换、生产 28765 部署、物理删除、历史改写或强推。正常提交/推送不表示正式数据发布或生产验收。
- 保留原有 5 个无关 untracked 文件，未暂存。

## 本轮续做：DM01 Head、合同和共享 PG 读链

- 新增 `v4.dm01_data_accepted_heads` 及 append-only history/CAS migration（045），接入应用 Phase 0 migration ledger。已在同一 `market_research` 实例执行该 DDL，并按现有已入库 Head 的精确原始字节 bootstrap generation 1；Head SHA 为 `38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`、日期仍为 `2026-09-30`。未执行 CAS，未改变 accepted Head 内容。
- 对当前 Registry 中 15 个合同版本完成批准事件 readback；包括 Full Closeout 4.2、Head schema 2.0、promotion policy 4.1、已接受 R4R1 4.1 与现行日更运行合同。该操作为本轮用户授权的 DB Registry 状态写入，不代表第三方外部验收，也未放宽 Head/生产权限。
- DM01 运行合同、日历 Head、source ingress、calendar 来源、历史 Head archive 和组件 receipts 统一在共享数据库读快照中读取。验证同一 RR/RO connection 嵌套复用；当前 parent 为 9 个组件，R4 acceptance envelope、4.2 Registry contract 和 calendar readback 通过。`2026-10-19` 的 session gate 因缺少 `2026-10-08` 中间交易日而拒绝捕获，未启动日更或采集器。
- 修正新增 Head 查询未限定 `v4` schema 的运行错误；修正只读连接包装器把业务校验异常误报为 `PG_READ_FAILED` 的错误映射。历史 Git ingress 现在校验精确 `git:<commit>:<path>` blob 字节后才接收入库。
- 历史 R3.3 链的源冻结重建不再在当前源码写入 `D:/new_tdx`；从 Head 合同指定、已精确导入 PG 的历史 builder blob 解析该次历史运行的 `TDX_ROOT`，保持原有接受链摘要可复核，同时现役采集/构建路径仍走中央 `resolve_tdx_root` 配置。
- 13 个变更 Python 文件定向编译通过，`git diff --check` 通过。没有运行完整测试集、GitHub CLI/Actions 或重复全仓扫描。
- 浏览器上一轮覆盖的页面和交互仍对当前旧 28766 服务有效；但服务入口 `G:/codex_tmp/v4_r21_r5_dev_candidate_28766.py` 直接导入服务模块，PID `42876` 在最终代码修改前启动。停止该精确进程的操作被自动审查拒绝，本轮没有通过其它方式绕过。故最新修改后的浏览器验收记为 `BROWSER_PARTIAL`，需在允许安全重启 28766 后复验。

## 本轮续做：日更合同 Registry 与 TDX 成员重建

- `operational_daily_executor_v1.verify_source_gate` 去掉读取 `config/tdx_a_stock_delta_scope_policy_v2.json` 的运行时文件依赖，改从同一共享 PostgreSQL 的批准合同 Registry 读取 `TDX_A_STOCK_DELTA_SCOPE_POLICY_V2/2.0.0`；按精确合同 ID、版本、SHA-256、namespace 和源 revision 校验。Registry/批准事件在同一 `market_research` 实例提交，SHA-256 为 `f7e1134867f2ec771d2ebcc21fec12d6b616e41efb68b6b1d6e0b932e8582647`；只读 RR 运行时 readback 通过。
- `tdx_member_retro_r43.py` 选择器和重解析路径不再用 `MEMBER_SNAPSHOT_S.json` 本地指针选快照；改由 PG `tdx_membership_candidate` 精确候选驱动，从已接受 PG identity projection 的 `records` 读取身份，校验唯一来源键/实体键。历史接受 membership artifact 仅在明确 source-ingress 边界导入并读回 PG。解析器冻结副本写入 `G:/codex_tmp` 临时目录；移除未使用的整棵 TDX `block_*.dat` 扫描。
- 使用现有入口实际生成当前诊断候选 `TDX_MEMBER_SNAPSHOT_S_20261018_5fddbc66d45184b1bfecc1f0bbff414c0d77856d475adf7df388dcea70962fca`：55,136 条成员关系、54,613 条映射、523 条隔离；完整冻结源重解析结果 `FROZEN_SOURCE_REPARSE_V2_PASS`，原始/标准化成员摘要均为 `5fddbc66d45184b1bfecc1f0bbff414c0d77856d475adf7df388dcea70962fca`。仅新增诊断 PG candidate，未切换正式 Head。
- 验证期间首先发现接受 identity projection 使用 `records` 而非旧文件的 `rows` 字段，随后按其 `ACCEPTED_IDENTITY_NORMALIZED_VIEW_R3` 合同适配；又发现接受 membership `facts` 是明确 ingress 绑定，不是历史 ingress 中现成对象，改为边界导入再读取。最终 capture + reparse 全流程通过。
- Codex 内置浏览器本轮直接访问 `127.0.0.1:28766`：首页有 5,213 只股票 / 378 个板块；股票模块 5,213 条、板块模块 378 条；Focus 469 条、Forward 117 条；市场宽度/指数/事件真实加载；Diagnostics 健康源表 4 组（ADJUSTED_DAILY 5,213、IDENTITY_UNIVERSE 5,224、RAW_DAILY 5,213、TRADING_STATUS 5,224）。页面均显示当前候选截至 2026-09-30。
- 以上浏览器页面运行于既有 PID `42876`。该进程在本轮最后两处后端编辑前启动，读取了旧 Python 模块；停止该精确进程曾被自动审查拒绝。因此本轮浏览器页面验证的是 28766 现存服务版本，不能声称本轮新增日更合同和成员捕获代码已由该 Web 进程加载。上述两处分别由 Registry RR readback、真实 PG capture/reparse 端到端验证；待 28766 可重载后复验前端集成。
