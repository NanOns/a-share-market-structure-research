# V4 R3 定点闭环 R4 — 修复与独立核验记录

**日期：** 2026-10-21（北京时间）
**基线：** `codex/v4-unified-development` @ `922e05e95d0ec4dc45f96550a403c26c8d01465d`
**阶段合同：** `V4_R3_DEFECT_ROOT_CAUSE_AND_OPEN_FUNCTIONAL_CLOSEOUT_R4`；仅覆盖 2026-10-12、13、14 候选及对应 T0 前冻结事实。排除 10-15 及以后行情、正式 Head、生产 PG 写入、28765 重启、外部复权服务、概率或交易宣称。
**总状态：** `R4_REPAIR_PARTIAL / PRIORITY_UI_ERROR_SEMANTICS_PASS / PRIORITY_ALGORITHM_OFFLINE_SIM_PASS / D2_CAUSAL_ATTRIBUTION_PASS / PRIORITY_OWNER_RESTORE_BLOCKED / LIMIT_SOURCE_LINEAGE_BLOCKED / FUNCTIONAL_CLOSEOUT_BLOCKED`

## 阶段门禁和依据

- Phase 0 沿用已接受状态 `DEGRADED_PASS`，依据 `docs/V4_PHASE0_FINAL_ACCEPTANCE_R3_1_20260925.md`；该报告记录扫描器 `NOT_APPLICABLE_UNTIL_V4_05`。本轮不是 scanner 工作，没有启动 scanner。
- 执行前查阅 `docs/evidence/functional_audit_r3_20261021/FINAL_REPORT.md`、`docs/evidence/functional_audit_r2_20261020/FINAL_REPORT.md` 及适用的 `docs/upgrade/V4_RUNTIME_PERFORMANCE_REPAIR_R1_20261013.md`。R3 确认当前 token 无 Priority Owner、D2 stale 因果待拆分、风险/轮动和来源覆盖未闭环；R4 以其 10/12–14 截止及安全边界为准。
- 本轮仅读候选快照目录 `G:/codex_tmp/v4_daily_candidate_chain_20261020`。未更改或重算候选链输入、未连通 PostgreSQL Owner 写接口、未改变正式 Head。

## P0 — Priority 当前候选

| 检查 | 实际输入与观察 | 判定及动作 |
|---|---|---|
| 当前 binding | 当前 R3 token 为 `2e3a2dd57284e2f8566c265a7c1f112dbc50e7dab3a473f73873d9d02a88b0df`，T0 `2026-10-14`。只读 authority `data/v4/research_priority_authority_r1.json`（SHA-256 `4d0042c9857e70c9482fbaaa40f7e1e4fb29cfffb920f2f0b95531207cbe6a3c`）含旧 token `554f…` 和 `914092…`，不含当前 `2e3a…`。旧 10/14 owner 不是当前 owner，不能跨 token 复用。 | 缺绑定原因直接成立，当前优先级列表仍不可用。没有生成/落库新 Owner，也没有把旧 owner 重新签给新 token。 |
| 排序算法/板块 0 条 | 直接以 10/14 冻结 candidate-only Core 5,225 行、Profile 5,225 行、Sector native/rotation 400 行运行 `src/workbench_service/research_priority_r1.py::build_priority`，上下文设为当前 R3 token 与 T0。股票结果 `967 RANKABLE / 4,258 NOT_RANKABLE`，前十真实代码为 `SZ.002674, SH.600851, SZ.301313, SH.688282, SH.600693, SZ.300733, SH.688552, SH.605318, SZ.002549, SZ.302132`。股票 4,258 个不排序原因中最多为相对强度未改善 2,432、5 日收益非正 1,669、位置过度延伸 59、结构受损 48，其余为明确输入缺失组合。板块 `0 RANKABLE / 400 NOT_RANKABLE`：266 条的缺项为 `maturity + health`；134 条为 `maturity + health + rotation`。原因与 `build_priority` 条件逐行一致，不做插补。离线 payload SHA-256 `2662ac3c09f7608585d9bec1c822a6ae0258fa74a663b7fe9043cfd8d7e54333`，临时位置 `G:/codex_tmp/R4_priority_offline_candidate.json`；其 stock/sector 输入文件及 SHA-256 保留在 payload source descriptors 中。 | **算法模拟 PASS。** 本轮实际解释了当前 token 的非空股票排序及板块 0/400 字段缺口，满足输出反例要求。它只是候选离线结果，未写入 immutable PG Owner/authority，也没有让真实 API 可读；旧 owner 原始 PG payload 因本机没有只读 DSN 未独立读回。与一般 sector 榜 395 条可排名不是同一合同。 |
| 前端错误语义 | `api.js::read` 收到 `/radar/priority` 的 `PRODUCT_READ_FAILED / RESEARCH_PRIORITY_BINDING_MISSING` 后，现显示对应候选优先级尚未生成及当前 T0/token、缺失 Priority Owner、不能复用旧 token；`INVALID_QUERY_BOUND`、scope/rankability 参数错误仍显示筛选参数无效。 | 修复已落在 `src/workbench_service/static/core-product-r1/api.js`；负例测试见下文。仅修正页面解释，不等于恢复非空排序结果。 |
| Owner 物化边界 | `prepare_priority` 会写 PG schema、payload 和 authority；本地目标 DB 为共用 `market_research`，本任务明确禁止生产 PG 写入。候选输入可读，离线模拟 payload 已生成在 G 临时目录，但没有隔离写授权。初次服务观察的日志曾显示旧 token；重启后实际状态 API 返回当前 token `2e3a…`，但当前 token 的 authority 绑定仍缺失。 | 为守住授权边界，没有物化 PG Owner / authority。初始 API 列表不可读；随后用户要求重启服务，运行时验证见本报告后续记录。 |

## P1 — D2 归因

直接读取 T0 `2026-10-14` `corrected_d2.json.gz`，SHA-256 `3b38ddfc05a50ea56e5a18d7a83709e22aa160e88713791f731387495d05a5d7`，共 5,225 行。它标记 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`，来源系统可得时间为 10/20；保留事后重建边界。

全量维度交叉计数：`prior_episode` 依 reducer 的 `frozen_invalidation` 是否进入 `unknown_predicates` 判定；它只在确有前序 episode 时作为 required unknown。每行 `frozen_invalidation=UNKNOWN`；`CONFIRMED=TRUE 145 / UNKNOWN 5,080`；最终 `TRUE/FRESH 65`、`UNKNOWN/STALE 5,160`。`boundary_event` 全部 null，`suspended=FALSE 5,214 / UNKNOWN 11 / TRUE 0`。PREWATCH `FALSE 4,790 / TRUE 397 / UNKNOWN 38`，SEED `FALSE 4,807 / TRUE 397 / UNKNOWN 21`。

| 前序 episode | frozen invalidation | CONFIRMED | unknown_predicates | final / freshness | 行数 |
|---|---|---|---|---|---:|
| 无 | UNKNOWN（不阻断） | UNKNOWN | `CONFIRMED` + `dq5/episode_invalidation_contract_id/followup_complete/scenario` optional unknown | UNKNOWN / STALE | 4,249 |
| 无 | UNKNOWN（不阻断） | UNKNOWN | CONFIRMED + PREWATCH + core_price_damage + suspended；及 delta3、dq5、episode invalidation、followup、risk、scenario 的部分 optional unknown 组合（余下无前序 stale 互斥组合） | UNKNOWN / STALE | 36 |
| 无 | UNKNOWN（不阻断） | TRUE | dq5、episode invalidation、followup、scenario optional unknown | TRUE / FRESH | 65 |
| 有 | UNKNOWN（阻断） | UNKNOWN | CONFIRMED + frozen invalidation + optional unknown；含少量 PREWATCH/core damage/suspended 等额外 unknown 互斥子组 | UNKNOWN / STALE | 795 |
| 有 | UNKNOWN（阻断） | TRUE | frozen invalidation + dq5、episode invalidation、followup optional unknown | UNKNOWN / STALE | 80 |
| **总计** |  |  |  |  | **5,225** |

因此 5,160 stale 不能统称为 frozen invalidation 导致：至少 4,285 行没有 prior episode，frozen invalidation 不进入 reducer 硬阻断 unknown；其中 4,249 行确认 UNKNOWN 已足以解释资格 UNKNOWN，另 36 行还叠加其它必需未知。875 行有 prior episode 且 invalidation unknown；其中 80 行 CONFIRMED 为 TRUE 但仍被前序 invalidation 阻断。其余细分互斥组合由表中附加谓词集合约束，全部计数回到 5,225，无跨组重复。

为保留 `unknown_predicates` 的互斥细分，5,225 行对应 13 种完整组合（未列出的 optional unknown 均不存在）：

| prior | invalidation | CONFIRMED | unknown_predicates | eligibility/freshness | count |
|---|---|---|---|---|---:|
| N | UNKNOWN/nonblocking | UNKNOWN | `CONFIRMED; dq5?; episode_invalidation_contract_id?; followup_complete?; scenario?` | UNKNOWN/STALE | 4,249 |
| Y | UNKNOWN/blocking | UNKNOWN | 上行谓词 + `frozen_invalidation` | UNKNOWN/STALE | 792 |
| Y | UNKNOWN/blocking | TRUE | `dq5?; episode_invalidation_contract_id?; followup_complete?; frozen_invalidation` | UNKNOWN/STALE | 80 |
| N | UNKNOWN/nonblocking | TRUE | `dq5?; episode_invalidation_contract_id?; followup_complete?; scenario?` | TRUE/FRESH | 65 |
| N | UNKNOWN/nonblocking | UNKNOWN | `CONFIRMED; PREWATCH; core_price_damage; delta3?; dq5?; episode_invalidation_contract_id?; followup_complete?; risk?; scenario?; suspended` | UNKNOWN/STALE | 9 |
| N | UNKNOWN/nonblocking | UNKNOWN | `CONFIRMED; PREWATCH; SEED; delta3?; dq5?; episode_invalidation_contract_id?; followup_complete?; scenario?` | UNKNOWN/STALE | 9 |
| N | UNKNOWN/nonblocking | UNKNOWN | `CONFIRMED; PREWATCH; SEED; dq5?; episode_invalidation_contract_id?; followup_complete?; scenario?` | UNKNOWN/STALE | 7 |
| N | UNKNOWN/nonblocking | UNKNOWN | `CONFIRMED; PREWATCH; core_price_damage; dq5?; episode_invalidation_contract_id?; followup_complete?; risk?; scenario?` | UNKNOWN/STALE | 4 |
| N | UNKNOWN/nonblocking | UNKNOWN | `CONFIRMED; PREWATCH; SEED; core_price_damage; delta3?; dq5?; episode_invalidation_contract_id?; followup_complete?; risk?; scenario?` | UNKNOWN/STALE | 3 |
| N | UNKNOWN/nonblocking | UNKNOWN | `CONFIRMED; PREWATCH; core_price_damage; delta3?; dq5?; episode_invalidation_contract_id?; followup_complete?; scenario?` | UNKNOWN/STALE | 2 |
| N | UNKNOWN/nonblocking | UNKNOWN | `CONFIRMED; PREWATCH; SEED; core_price_damage; dq5?; episode_invalidation_contract_id?; followup_complete?; risk?; scenario?` | UNKNOWN/STALE | 2 |
| Y | UNKNOWN/blocking | UNKNOWN | `CONFIRMED; PREWATCH; core_price_damage; delta3?; dq5?; episode_invalidation_contract_id?; frozen_invalidation; risk?; scenario?; suspended` | UNKNOWN/STALE | 2 |
| Y | UNKNOWN/blocking | UNKNOWN | `CONFIRMED; delta3?; dq5?; episode_invalidation_contract_id?; followup_complete?; frozen_invalidation; scenario?` | UNKNOWN/STALE | 1 |

`?` 表示 predicate 名后缀 `:OPTIONAL_INPUT_UNKNOWN`；其他名称是 required unknown。完整计数合计 5,225。

真实代码核对：`src/v4/research_state.py::reduce_state` 以 `invalid_required=bool(prior and prior['episode_id'])` 决定 frozen invalidation 是否追加至 required unknown。新增回归向量在 `prior_state=None`、CONFIRMED TRUE、其他必需事实完整而 frozen invalidation UNKNOWN 时验证其不单独造成 stale；不把 UNKNOWN 改成 FALSE。真实 CONFIRMED UNKNOWN 的底层 detector 输入仍未证明可由已有事实判 FALSE，故未更改 producer。

10 个代表性真实代码可由快照重现（均非严格 PIT）：`SZ.001965`、`SZ.002469` 为 CONFIRMED TRUE/FRESH；`SH.688349`、`SH.600703` 为 CONFIRMED UNKNOWN/STALE；`SH.601059` 为 PREWATCH UNKNOWN、suspended UNKNOWN；`SZ.000582`、`SH.601995` 为 SEED UNKNOWN；`SH.688349` 与 `SH.600703` 的 PREWATCH FALSE 样本分别对应有/无 prior episode。全量没有 boundary event，也没有 CONFIRMED FALSE 行；故不能伪造 boundary 或 CONFIRMED false 样本。已有测试覆盖 reducer 边界，不意味着 D0 detector 的真实源事实已经闭合。

## P1 — 涨跌停覆盖与来源一致性

10/14 `daily_price_limits_v1.jsonl.gz`（SHA-256 `7d039c25f56bc14bb721445e0e15598b91318722329ab445c02f61b22a561cde`）5,225 行：`NOT_LIMIT=59`、`SUSPENDED=5`、`UNKNOWN=5,161`；未知全部标 `REFERENCE_PRICE_UNKNOWN`，已知有效参考价覆盖 59/5,225 = 1.13%。样本包括 `SZ.002462` 的已知 `NOT_LIMIT`、`SH.601059` 的 SUSPENDED、`SH.688349` 的 UNKNOWN。

对照同候选 `sources/daily.json`（SHA-256 `8f949e7418355e8f60dbd859598e27ad948c4cfdf9bed69b37c5f04d65db755e`）、RAW 和历史 K 逐代码核对，出现内部证据不一致：5,133 个代码的 BaoStock `preclose` 与 10/13 RAW close 相等；20 个不等（例 `SZ.000581`：17.7300 对 18.03）；2 个无前日 RAW close；另有 6 个 `tradestatus=0` 且无 RAW bar。daily limit 文件 **5,225/5,225 行** 的第三个 BaoStock source_ref 都指向 10/09 收盘采集查询文件（例 SH.688349 的 Bao 来源 SHA `c8be0138…`，参数日期为 2026-09-28），而不是本候选 10/14 `sources/daily.json`。这使输出状态与冻结候选输入/引用链无法重现，且与当前限价 producer 在有效参考价情况下应继续解析版本化规则的行为不相符。

**判定：** 直接输入覆盖不足的事实成立；更底层原因不能安全归于缺行情或规则，而是日限价产物来源引用日期/版本错配待独立重放。未硬编码板块规则、未把未知改为无涨跌停，也未覆盖候选产物。10/12 有两个候选限价 owner（`54ed1…` 与 `a4c619…`，覆盖差异很大）；10/13 与 10/14 也有重复候选目录。缺少可验证的同链 token/源合同选择证据，本轮不任意选择它们来代表正式 chain。P1 覆盖审计因此未验收。

各日期现存 candidate-only 文件计数如下（同日重复目录保持并列，不择优）：

| T0 | owner目录短 SHA | 行数 | LIMIT_UP | LIMIT_DOWN | NOT_LIMIT | SUSPENDED | UNKNOWN |
|---|---|---:|---:|---:|---:|---:|---:|
| 10/12 | `54ed1…` | 5,224 | 1 | 0 | 49 | 7 | 5,167 |
| 10/12 | `a4c619…` | 5,224 | 47 | 23 | 5,122 | 12 | 20 |
| 10/13 | `e13782…` | 5,225 | 0 | 0 | 47 | 6 | 5,172 |
| 10/13 | `eed256…` | 5,225 | 0 | 0 | 47 | 6 | 5,172 |
| 10/14 | `727b8c…` | 5,225 | 0 | 0 | 59 | 5 | 5,161 |
| 10/14 | `cadc80…` | 5,225 | 0 | 0 | 59 | 5 | 5,161 |

## 板块 / 风险、概念关系、Focus 与图表

- 直接读 10/14 sector 文件：400 板块（132 行业 + 268 概念）；成员快照为截至 10/09 的重建。轮动态：`NONE=216`、`UNKNOWN=134`、`ROTATION_FAILED=45`、`ROTATION_PULSE=4`、`ROTATION_IN=1`；rotation quality `PROXY_RECONSTRUCTED=266 / UNKNOWN=134`。native sector 行中无 health/maturity 字段（400/400 缺失）；RS5/RS20 为 `PROXY_RECONSTRUCTED`，不能替代 lifecycle health。市场候选四轴为 trend WEAK、breadth DETERIORATING、participation THIN、stress UNKNOWN，regime UNKNOWN，stress 原因 `STRESS_INPUT_OR_COVERAGE_UNKNOWN`。已有 `build_sector_family`/Priority 条件在 health 缺失时按 UNKNOWN / NOT_RANKABLE 收口；没有接受的 lifecycle health Owner，因此不改 risk 合同、不造平行服务。本轮未完成行业/概念 400 行 10/12–14 每日三语义全量逐字段拆分。
- 5G 概念 `THEME:880506` 源成员 454、映射 442、未映射 12、有行情 440；本轮能直接复核总数，尚未取得可审计的 12 个原代码和逐个身份原因。没有强塞行业映射或缩小分母。
- Focus 3,247 是重建观察/跟踪池，不能解释成真实持仓或前瞻样本；没有重算每个状态及首页变化分母，沿用现有页面约束并标记未关闭。
- 初次进程为 `127.0.0.1:28766`、PID 49564；检查实际启动脚本后确认它直接运行候选预览 `ThreadingHTTPServer`，未启动后台 Jobs。PG 监听 `5432`、PID 8640；初次检查时无 28765 listener。用户后续明确要求重启开发服务；重启及其运行时验证见本报告后续记录。未做浏览器桌面及 390×844 交互验收。
- 未确认现役 joint UI 实际加载的 `labels.js` 文件来源及 SHA，保留 R3 的待核项。

## 代码修复与验证

1. `src/workbench_service/static/core-product-r1/api.js`：准确区分 `RESEARCH_PRIORITY_BINDING_MISSING` 与 `INVALID_QUERY_BOUND` / Priority scope 和 rankability 参数错误。前者显示 T0、当前 token 及已知 Owner 缺口；后者仍提示筛选参数无效。
2. `tests/test_core_product_api_errors_r1.mjs`：新增 Owner 缺失与参数错误两条负例。
3. `tests/v4_10/test_research_state.py::test_unknown_frozen_invalidation_does_not_block_without_prior_episode`：新增 reducer 向量回归。
4. 验证命令：
   - `node --test tests/test_core_product_api_errors_r1.mjs`：2 passed。
   - `node --check src/workbench_service/static/core-product-r1/api.js`：通过。
   - `pytest -q tests/v4_10/test_research_state.py -k unknown_frozen_invalidation_does_not_block_without_prior_episode`：1 passed。
   - `git diff --check`：通过。

## 阶段验收与后续

- 已验收：前端 400 错误语义区分；D2 stale 与 invalidation 的直接因果拆分；无 prior episode 的 reducer 模拟；限价覆盖总计和候选来源引用错配的具体反证。
- 未验收：恢复当前 token Priority 非空列表与 API/页面验收；旧板块 Priority 0/400 逐字段拆因；真实 CONFIRMED UNKNOWN detector 根因；有效限价覆盖重放及 10/12–14 同链选择；风险/轮动字段全量交叉核验；12 个 5G 成员身份；Focus 分母；修复后 28766 冷/热与窄屏真实交互。
- 下一步需在不写生产 PG 的授权路径下准备当前 token 的 Priority Owner：先确定可写候选 owner 物化的隔离边界及恢复步骤，再生成并绑定当前 token、读取非空真实股票列表及合法板块列表；随后修复/重放限价的日期化 source lineage。生产 Head、28765 和 10/15+ 行情仍不在下一步授权内。
- 本报告是独立范围证据，不是发布验收、正式 Head 更新或下一受门禁阶段许可。

## 用户要求重启服务后的追加修复记录（2026-10-21）

### 操作、证据与运行边界

- 依用户明确要求重启开发服务。先核对监听 PID 49564 的命令行为 `E:\python\python.exe -B G:\codex_tmp\v4_daily_candidate_chain_20261020\serve_preview_28766.py`；阅读脚本确认它只启动候选 `ThreadingHTTPServer`，不启动自动任务、采集器或写入 worker。确认该 PID 正占用 `127.0.0.1:28766` 后停止它，再从同一候选根启动，恢复 PID 17888。没有启动其它网页端口。
- 重启后 `/api/operations/status` 为 `READY`、`V4_DEVELOPMENT_CANDIDATE_PREVIEW`、`read_only_ui=true`、T0 `2026-10-14`、token `2e3a2dd…`、formal Head 仍为 `2026-10-09`。`/v4/research/`、静态 `api.js` 均 HTTP 200。`/api/v4/radar/priority` 使用当前 T0/token 实际返回 HTTP 400，原因 `RESEARCH_PRIORITY_BINDING_MISSING`。这证实旧日志的 `914092…` 不是重启后的实时 token；缺 Owner 的判断仍成立。
- 实时服务根是 G 临时候选链，UI 字节从主仓库直接读取。脚本在每个静态资源请求时读取文件，因此新增前端修改已经由当前服务提供，无需第二次重启。Priority Owner 缺失时，读取在 authority 查找处失败；本轮没有调用 `prepare_priority`，没有写 PG schema、owner payload 或 authority。PG 监听 `127.0.0.1:5432` PID 8640；28765 无监听。没有改生产 Head、TDX 源、候选快照或行情数据。

### 新发现并完成的修复

- 实际 Priority 请求揭示错误包装差异：候选预览 handler 将 BFF `ValueError` 返回为 `INVALID_OPERATIONAL_QUERY`，而另一服务 handler 返回 `PRODUCT_READ_FAILED`。先前修复的 API 文案只识别后一包装，真实 28766 页面仍会落入通用“读取失败”。
- 修改 `src/workbench_service/static/core-product-r1/api.js`：Priority Owner 缺失和 scope/rankability/query-bound 错误均依据稳定的业务 `reason` 码判断，不再依赖外层传输 `code`。新增两条测试覆盖当前候选 handler 的真实包装，同时保留原包装的测试。
- 验证：`node --test tests/test_core_product_api_errors_r1.mjs`：4 passed；`node --check src/workbench_service/static/core-product-r1/api.js` 通过；`git diff --check` 通过。修改后从 28766 读取静态脚本 HTTP 200，并确认包含新错误映射；Priority endpoint 仍返回预期缺 Owner 业务原因。

### 未修复项及原因

- 当前 token 的 Priority 列表没有 immutable PG Owner/authority binding。离线重算能得到股票 `967 RANKABLE / 4,258 NOT_RANKABLE`，但 UI 运行时不能读取离线 JSON：Owner 合同要求先写入 PostgreSQL 不可变 schema，再绑定文件 authority；目标是共享 `market_research`，当前 R4 授权明确禁止写生产 PG。不能将离线试算伪装为真实 API，也不能篡改 authority 绕开 digest、DB identity 和 immutable Owner 校验。因此仅修复了缺失状态说明，列表仍未恢复。
- 板块缺 `health/maturity` 的 400/400 不是展示或排序代码问题；没有可信、带合同的 Owner 输入时补值会造数据，故未插补。
- D2 仍有 detector required facts UNKNOWN；没有证据证明其可判 FALSE，不能把 UNKNOWN 改为 FALSE。限价仍有来源引用与日期错配、候选根重复；无同链选择和可复现重放证据，不选择或覆盖候选结果。
- 5G 概念的 12 个未映射证券身份/原因及 Focus 的状态分母尚未从可审计证据闭合；本次重启没有新增这类证据，因此未推断映射或修改分母。
- 页面静态资源与真实 API 状态已探测，但未做浏览器冷/热缓存、390×844 窄屏交互和截图验收；因此不能声称 UI 全链路验收通过。当前服务使用候选 10/14 T0、formal Head 是 10/09，页面数据仍带有事后重建和非 PIT 边界。

### 阶段结论更新

本次重启本身成功，28766 为 READY 且只读；新发现的前端错误包装问题已修并针对真实包装添加回归覆盖。Priority 实时 Owner、价格限制来源闭环和其他未关闭项仍未验收。下一步若要恢复真实 Priority 列表，须先取得明确的隔离写范围/DB 影响授权并按 immutable owner 流程准备证据；生产 28765、formal Head 与 10/15+ 数据仍不在范围内。
