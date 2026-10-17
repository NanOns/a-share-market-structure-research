# V4 R21-R5 全模块文件引用与 Workspace 集中实修收尾

- 日期：2026-10-18；分支：`codex/v4-workspace-cleanup`。
- 结果：`V4_CODE_PATHS_IMPLEMENTED / LIVE_PG_READBACK_PASS / BROWSER_PASS_28766 / FORMAL_HEAD_RECONCILIATION_OPEN`。
- 数据库：共用 `127.0.0.1:5432/market_research`（OID `646711`）；开发网页 `127.0.0.1:28766`。未启动或触碰生产网页 `28765`。

## 已完成

- 修复历史源 ingress、PG Owner/Head/Registry 精确读取、V4-13 合同包、V4-14 replay/artifact、V4-15 FEP 标签合同与持久化；业务消费者不再从工作区/Git 历史回退读取相应 authority/artifact。
- 修复日更合同 Registry、TDX 成员候选重建、源包 PG candidate append/readback、日更入口路径配置、研究快照可用日期、BFF 与行情候选调用路径。TDX 源根保持只读。
- 在同一 PostgreSQL 实例完成获准的候选/合同/Owner 状态写入和 readback；完成成员重解析候选 55,136 条、映射 54,613 条、隔离 523 条。未执行正式 Head CAS。
- 266 个基线 P1 调用点中，265 个 V4 点已有 PG-bound candidate/consumer 实现；1 个非 V4 调用点登记为 out of scope。矩阵当前状态为 264 个待历史清单/Head 对账、1 个无本地文件回退、1 个非 V4 登记；没有把候选路径冒称正式发布。
- 定向编译 18 个变更 Python 文件及 `git diff --check` 通过；未运行全仓扫描、完整测试套件、GitHub CLI 流程测试或 GitHub Actions。

## 28766 浏览器验收

- Codex 内置浏览器在当前工作树服务验证首页、板块列表/搜索/详情、股票列表/搜索/详情、日线/周线图表、Focus/Forward、市场与事件、Diagnostics Health/Jobs/Sources/Contracts、Compare、Replay。
- 核验实际候选快照：T0 `2026-09-30`、5,213 股票、378 板块；“中华企业”精确返回 SH.600675（2.520），区域地产含 43 个成员；股票日线 120/253 根、周线 54/54 根。Focus 469 项、Forward 117 项。
- 市场页实际返回 2,344 涨、2,712 跌、155 平、13 未知；Diagnostics 显示 worker 未启动且 source requests=0。Compare/Replay 严格 PIT 日期为 0，页面保留重建/非 PIT 限制。
- 28766 由当前分支候选服务提供，PostgreSQL 实例为上述共享实例；`28765` 未监听。页面明确标识 `PG 候选快照 · 不代表正式 Head`。

## 未闭合事项

- 基线 266 个 P1 的正式 source-edge、T0、namespace 与 accepted publication Head 对账仍是 0/266；22 条历史 reference edge 未精确映射（21 个唯一调用点）。这些是历史 inventory join，不是声称尚有未实现的 V4 PG candidate consumer。不得伪造边 ID 或 Head 身份。
- 当前数据库没有 accepted operational publication Head。正式 Head 切换、生产部署/网页 28765、物理删除及强推未执行；需要相应单独授权。非 V4 调用点 `src/workbench_analysis/history_170_v3_3.py:13` 仅登记，未改。
- 保留原有 5 个无关 untracked 文件，未纳入本次提交。
