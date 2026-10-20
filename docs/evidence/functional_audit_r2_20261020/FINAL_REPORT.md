# V4 R2 二次独立审计与 P0/P1 定点修复

日期：2026-10-21  
基线：`codex/v4-unified-development` @ `3e6d3a56fb69744391d27432ea6d298ef2d1cf16`  
合同：执行卡 `V4_真实功能二次独立审计与连续日更P0P1定点修复_执行卡_R2_20261020.md`；代码保留已有模块边界与数据 Owner 合同，新增关系读数合同 `R2_CURRENT_MEMBERSHIP_NAMED_RELATIONS_V1`。阶段前已查阅适用升级文档。  
结果：P0 连续候选链 10/12–10/14 完整，28766 预览稳定；本次要求范围内代码修复已提交。正式 Head 未变更。

## 1. 连续日更与数值证据

| 日期 | 候选产物 | 数值 Oracle | 当前读者与约束 |
|---|---|---|---|
| 2026-10-12 | freeze SHA256 `75f7d126f503b11599e63936f585cd7ac53eb065bc90f8c9c93b5af93c631d72`；candidate token `bd6e9a0ca23db1566a452a9fd3c81fee77aae30e98e6988b5c193920fb687e14` | PASS，219,408 checks，0 error；RAW/QFQ period 各 15,672 | 候选只读读者建立；仅工程候选，非正式 Head |
| 2026-10-13 | `SUCCESSOR_CANDIDATE.json` token `c11fbb1008af84fff0b4f19116c8e739fe413ee1ece7b9988b5c193920fb687e` | PASS，219,436 checks，0 error；RAW/QFQ period 各 10,450；15/15 reader domains READY | SOURCE_READY；新上市证券 `SZ.301660` 仅进入候选；不具严格 PIT 资格 |
| 2026-10-14 | freeze SHA256 `5619c0fdf47679d6563d450298a6a97abded1e3865358d027cf71fc2087a6d39`；`SUCCESSOR_CANDIDATE.json` token `2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df` | PASS，219,436 checks，0 error；Oracle JSON SHA256 `d9264da2429458f30d8c096cf7c8ae82536255f0afb5888887a1f82958e8253c`；RAW/QFQ period 各 10,450 | SOURCE_READY，previous head identity scope match；15/15 reader domains READY；正式 Head 仍为 2026-10-09 |

10/14 候选域实数：CORE 5,225 行、RAW 5,214 行、PROFILE/STRUCTURE 3,468 anchors、板块 400；RAW/adjusted、CORE、PROFILE、RELATIVE_SECTOR、FOCUS、LIFECYCLE、SECTOR、ROTATION、MARKET、FORWARD、SPECIAL_PHASE、PERIOD、DIAGNOSTIC 等 15 个 reader domains 均 READY。板块 400 = 132 INDUSTRY + 268 THEME；395 可排名、5 不可排名；主行业资格 378 true / 22 false。轮动状态为 NONE 216、UNKNOWN 134、ROTATION_FAILED 45、ROTATION_PULSE 4、ROTATION_IN 1；质量标记 PROXY_RECONSTRUCTED 266 / UNKNOWN 134，仍按来源限制解释。D0 UNKNOWN 5,080 / TRUE 145；PREWATCH FALSE 4,790 / TRUE 397 / UNKNOWN 38；D2 stale 5,160 / fresh 65。以上均为当前成员重建候选读数，不宣称严格 PIT 或正式接受。

截至本次核查，源就绪/冻结输入没有 10/15、10/16、10/19、10/20 的可用日包；因此链保持最新可复算候选日 10/14，未合成行情、未倒填 Forward 首捕。读者的 `production_accepted=false`、`formal_head_match=false`、`PIT_ELIGIBLE=false`；成员来源为 `RECONSTRUCTED_LATEST_MEMBERSHIP`。正式 Head 原摘要 SHA256 `55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e` 保持不变。

## 2. P0 服务与页面验收

- 开发预览仅监听 `127.0.0.1:28766`（PID 49564）；`28765` 无监听。复用既有 `127.0.0.1:5432/market_research`（PostgreSQL PID 8640）。未重启生产服务、未变更正式 Head。
- 当前 `/api/v4/context?trade_date=2026-10-14` 返回 HTTP 200、`READY`，日期 10/14、context token 与候选 token 一致。股票列表返回 READY、5,225 条。
- 浏览器已打开并确认八个入口：home、market、sectors、stocks、focus、radar、forward、diagnostics。浏览器同时可见当前日期 10/14、正式日期 10/09 和最新成员回算/非严格 PIT 提示。数据加载区块按路由异步读取。
- 个股详情样本：三一重能 SH.688349。RAW 日线 422 根，默认展示最近 120 根；UI 切换到 60 后显示 `60 / 422`，20 根已核验；RAW T0 收盘 12.55。QFQ 60 根可载入，声明按 T0 冻结 TDX GBBQ 与逐日 RAW 计算。MA20=13.124，MA60=13.876；成交量/额均有真实字段展示。
- 窄屏 390×844 视口未能通过当前浏览器自动化接口设置，窄屏排版未验收。浏览器 smoke 属于页面可达性验收，不替代后端数值 Oracle。

## 3. 本次 P1 修复

1. **行业/概念关联**：股票详情的 `membership_relations` 以已绑定的日期 sector Owner `member_ids` 校验；按明确的行业 ID 和主题成员集产生双向关联，未经成员校验不生成链接。输出记录日期、来源字段、Owner、观察时间、成员集合 as-of、重建 lineage、PIT=false，并区分关系缺失与来源不完整。展示行业及关联概念分组。
2. **120 日线与价格口径**：详情图默认最近 120 根，可选 20/60/120，分页以所选窗口步进；候选历史索引只读延伸 RAW 行，过滤 T0 之后数据，以 T0 GBBQ 重算 QFQ；缓存键包含 candidate token、日期、证券、价基及历史索引版本，返回缓存副本避免调用方改写缓存。
3. **板块优先级、Focus 层级、Forward 首捕**：沿用已有带版本合同和定点实现；本轮回看读数保留 rankable/not-rankable 与轮动质量/UNKNOWN 的明确区别。Focus 的关注轨迹、事件观察、独立前瞻队列分开展示，并声明不代表持仓。Forward 只有未来经授权的首捕 cohort owner 可形成首捕；10/14 历史回算不是首捕，继续显示 `NO_AUTHORIZED_COHORT_OWNER`，不将 unknown 计作零，也不授予 PIT/OOS。

## 4. 验收与下一步

- 定向测试：`85 passed in 10.71s`，覆盖 UX/API 读路由、候选日线与 QFQ 缓存、优先级风险状态、cohort readiness 与首捕 producer；`node --check` 与 `git diff --check` 均通过。
- 这是 R2 定点修复与候选环境证据，不等于生产发布验收。当前无源输入的后续连续日更、严格 PIT 成员历史、经授权的 Forward cohort owner/未来真实首捕，以及 390×844 页面验收仍未完成。
- 下一阶段：取得合规的 10/15 及之后日源后，沿同一 candidate-only 合同顺序续建并重新跑数值 Oracle/读者；由授权 owner 在未来日期实际创建 cohort 并记录首捕；补做 390×844 页面验收。不得据本报告推进正式 Head。

证据生成于 `G:\codex_tmp\v4_daily_candidate_chain_20261020\reports\functional_audit_r2_20261020`；候选 PG schema/read index 留在任务授权的同一 PostgreSQL 内。该目录内容仅供审计复核，不作为生产身份或正式发布证据。
