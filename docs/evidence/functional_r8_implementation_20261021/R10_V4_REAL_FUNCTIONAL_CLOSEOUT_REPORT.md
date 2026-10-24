# V4 R10 真实功能闭环修复报告（2026-10-24）

## 结论

本轮在 `codex/v4-unified-development` 上完成可直接施工的市场广度分母一致性保护、V4 运行扫描门范围隔离、Home 市场派生失败结果缓存和对应回归测试。结果为 **R10 部分闭环，不能作为发布验收或独立外审通过**。阶段 0 为 `FULL_PASS`；V4 运行扫描门仍 `V4_RUNTIME_GATE_BLOCKED`。没有把缺少的 PIT 来源、业务合同、PG 安全连接或 28766 运行时读回伪称完成。

本轮同步 `origin/codex/v4-unified-development` 后，本地与远端均为任务卡指定审计 HEAD `b44e6b6d263c9782e19d1e68f0877c444fb2519d`，无新增远端提交。适用任务卡为 Google Drive `V4_R9_独立外审_R10业务闭环与新增缺陷修复任务_R1_20261024.md`。本报告/证据与代码均随本轮提交推送；推送不构成外审或生产接纳。

## 阶段合同、证据和验收

| 阶段/主题 | 合同与证据 | 状态 | 验收结论 / 下一步 |
|---|---|---|---|
| S00 基线与阶段 0 | `V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json` SHA-256 `fb15e8131405921375c93f277ebdcc1d39ea518399e03f6e55d18bba0003e583`；任务卡基线 HEAD | `FULL_PASS` / `CODE_PASS` | 允许继续现役扫描器工作；保留 `G:/codex_tmp`、现有 repo 与固定服务/PG。 |
| S01 运行范围扫描 | `V4_RUNTIME_GATE_V1`、活动入口合同 `config/v4_active_runtime_entrypoints_v1.json` | `PARTIAL / GATE_BLOCKED` | 非现役维护脚本不再进入 V4 准入判定；活动闭包仍有未裁定项。逐项裁定 2,198 候选、11 动态边、9 路由后再复扫。 |
| S02 Market / breadth | `R10_MARKET_COMPARISON_UNIVERSE_V1`；候选数值 A/B `R10_MARKET_UNIVERSE_NUMERIC_A_B_V1` | `CODE_PASS / NUMERIC_PARTIAL / SOURCE_BLOCKED` | Core 分母仅在“交易日 + 四板块”投影与 SHA 绑定历史 universe 身份集合完全相等时可作加速；不等即取历史集合，历史集合缺少日期则 `SOURCE_INCOMPLETE`。非 PIT 样本的 10/14–16 历史 universe 计数为 0，因此不能做新业务数值验收。 |
| S03 Priority | R9 `S03_PRIORITY_API_RECONCILIATION_R7.json`、本轮 PG 只读 Owner loader | `OWNER_READBACK_PASS / API_CONSUMER_NOT_RERUN` | 从现有 `config/.env` 安全配置建立只读事务；10/20、10/21 Priority 与 Lifecycle 版本、摘要、行数及 Owner 行摘要通过。未写 PG；新版 HTTP/API 消费者读回仍待 28766 运行窗口。 |
| S04 Focus / Forward | R9 Focus/D2 与 Forward 报告和源样本 | `PARTIAL` | 普通 Focus 仍可用；Focus Priority 排序合同缺失，子页能力单独受限。Forward 历史成熟样本 3,260 / 73,115 可供复核，LIVE 首次捕获为 `WAIT_FIRST_CAPTURE`，不能用历史样本替代。 |
| S05 D0 / D2 | D0 cutoff seal `CUTOFF_CONTRACT_UNRESOLVED`；`FROZEN_INVALIDATION_CONTRACT_R2` 只定义比较器、不定义冻结价生成 | `BLOCK_CONTRACT` | D0 未形成新的来源封口/正式 publication。D2 可实施边界是保留 UNKNOWN/fail-closed；没有入场冻结价合同与字段，不能补写 875 个历史 episode 或生成冻结价。 |
| S06 G1–G4 / 真正新增交易日 | R9 Daily Source、Owner 和增量证据；当前可复用候选至 2026-10-21 | `SOURCE_WAIT / PG_NOT_RUN` | 无同日完整 Identity/Member authority：10/22 缺该来源，10/23 缺 BaoStock 日线/因子。不能构造新真实交易日链、G1–G4 全量对照、publication/CAS 或失败恢复结果。拿到权威数据后从真实前态连续增量重演，不跳过日期。 |
| S06 Home 性能 | R9 性能基线 `R9_IN_PROCESS_REAL_PG_PERFORMANCE_V1`；本轮候选失败路径已缓存 | `CODE_PARTIAL / PERF_NOT_ACCEPTED` | 已避免同一字节身份的缺来源市场派生在每次 Home 请求重新解析大型历史文件；历史交付 Home 冷样本 111.933 秒，单样本不能估 P95。未重启服务，未做新版 HTTP/UI 三并发及冷启动 P95 验收。 |
| S07 运行时 / UI | 固定端口当前只读监听核对 | `UI_RUNTIME_NOT_RELOADED` | 28766 仍运行旧进程 PID 52916；按指示不重启。28765 当前无监听。部署/运行时浏览器读回另待用户允许的运行窗口。 |
| S08 独立审计 / 生产 | 本轮权限边界 | `NOT_RUN / NOT_AUTHORIZED` | 不切正式 Head/28765、不发布、不执行生产调度。独立审计由下一轮 ChatGPT 使用本报告、机器证据和保留的失败材料完成。 |

## 代码修复

1. `src/workbench_analysis/r6_candidate_market_stress.py`：将市场广度的比较分母统一到日期匹配、四板块范围内的 SHA 绑定历史 universe。前态 Core Owner 只能作为等价加速；代码投影与历史身份集合逐 ID 相等才使用，否则取历史集合。发现重复身份或历史目标日期无集合时 fail closed。大 gzip 输入流式校验哈希/解析；在解压大型历史行情前先验证比较 session 和 universe。候选缓存身份现在也重新校验历史 universe 绑定，避免改坏绑定后命中旧衍生缓存。
2. `scripts/check_v4_business_literals.py`：运行准入合同改为 `V4_RUNTIME_GATE_V1`；非可达维护代码及维护动态边进入 `REPOSITORY_MAINTENANCE_INVENTORY_V1`，不再单独阻断现役 V4 运行门。它们仍被计数为 `NOT_PROVEN`，没有被静默认定为安全。V4 活动闭包未决项仍会阻断；新增显式 `--strict-runtime`，并让 Windows 打包入口明确使用严格模式。
3. `src/workbench_service/core_product_bff_r1.py`：市场来源验证异常在字节身份、生产者、参数和候选 token 对应的衍生缓存中记为 `SOURCE_INCOMPLETE`。来源/生产者变化会换身份并失效；能力仅在缺失的市场派生上关闭，不阻塞其它 Home 能力。
4. 测试更新涵盖 Core 投影一致与不一致、缺少历史目标日期、缓存身份对历史绑定内容变化的拒绝、维护项与 V4 活动闭包分门，以及 Windows 打包严格扫描参数。旧 UI 路径测试夹具更新为现役 allowlist 内的 `v4-workbench.html` / `v4-workbench.js`。

## 市场 breadth 数值证据与限制

候选逐证券证据是 `NON_PIT_CANDIDATE_REPLAY`，不能充当生产分母或 PIT 证明。绑定历史源文件为 239,298,684 字节，SHA-256 `3c4669d3b6ba9f4017c69bfcb12256b2b64144ad816ac3e7e055a8caf37ba77b`。10/19、10/20、10/21 的比较日分别为 10/14、10/15、10/16；该历史输入对这三个日期的四板块成员计数均为 0，而 Core 日期/板块投影分别有 5,225、5,226、5,226 个身份。故旧有按 Core 计算的 breadth 虽能在候选自身输入上复算（10/20 正收益指示器均值 `0.581573896353167`；10/21 `-0.2131210435449837`），却不能与权威历史分母完成核对。该计算不得被当成新修复后的 READY 数值：新实现应针对这组绑定输入返回 `SOURCE_INCOMPLETE`。

逐证券 JSONL 位于 `G:/codex_tmp/R10_MARKET_UNIVERSE_A_B_20261024.jsonl`（6,344,873 字节，SHA-256 `1d0906f236d25df6bd2451ee93089bf05cba37cc4225e755999869804383e2af`），压缩/明细证据及运行失败日志留在临时证据目录供外审读取；未把一次性脚本加入仓库。首次诊断脚本的日期类型/集合解析假设不匹配而失败，修正后发现是实际绑定历史输入缺日期，而不是数据被补造；失败材料保留，不能引用早期不正确输出。

## 复测、扫描、运行和数据边界

- 定向 pytest：`87 passed, 1 skipped`（市场缓存/范围、字面量门、服务图、官方日源合同、R9 ReadIndex PG 合同测试）；无真实 PG 消费者连接重放。
- `python -m compileall -q` 覆盖本轮 4 个修改的 Python 模块：通过。`git diff --check`：通过。
- 最终严格扫描：3983 个仓库文件作为图输入；7 个入口 SHA 校验通过，V4 可达闭包 639 个文件；`active_violations=0`，`active_unknown=2198`，`dynamic_unresolved=11`，`browser_route_unresolved=9`；非活动维护项 5,003 个字面量候选、25 个动态位点，在独立 `NOT_PROVEN` 清单内。严格扫描返回阻断状态，不能当作发布门通过。完整 41,652,994 字节扫描 JSON 放在 G 临时盘，报告仅保留摘要。
- 修改的业务代码没有新增具体证券/板块身份或固定交易日分支。新增测试的日期、合成证券身份仅用于测试范围；未新增正常业务默认证券、板块、日期。
- 本轮发现应用安全 PG DSN 原先未注入当前 PowerShell 进程；按项目现有 `config/.env` 装载 `WORKBENCH_PG_DSN` 后，以 `SET TRANSACTION READ ONLY` 读取 PG，未输出 DSN、未写 PG。旧报告中“本轮无安全 DSN”的陈述已由此更正。只读监听：开发服务 `127.0.0.1:28766` PID 52916；生产 `127.0.0.1:28765` 无监听；PG `5432` PID 8640。服务/Windows 未重启，正式 Head 未变，未写 TDX 源根。
- 失败证据保留：最终严格扫描非零是活动闭包门禁未决；市场历史 universe 日期范围空；早期市场诊断错误尝试；R9 已有 DM01 精确历史源码合同测试的 4 个失败仍在旧报告，不由本轮放宽合同或掩盖。

## 后续顺序

1. 先取得匹配 10/22–10/23 的合法 Identity/Member、BaoStock 日线/因子及来源合同，之后按真实相邻交易日完成 Source→Core→派生、G1–G4、publication/CAS、消费者读回与失败恢复。
2. 取得安全 PG 配置并使用现有连接配置执行只读读回；只有被授权的目标写事务才明确范围后执行。按用户本轮限制不重启 28766，因此新版 UI 验收需独立运行窗口。
3. 完成活动 V4 动态边、浏览器路由和字面量逐项裁定；维护清单另按实际入口证明状态。
4. 在业务方提供 D0 cutoff/seal、D2 冻结价生成、Focus Priority 排序和 Forward LIVE 首捕获合同/样本后再关闭对应能力。
5. 跨源 Amount A 继续作为独立审计项跟踪；不把它混作本阶段已通过。


## 存量数据停增量核查（2026-10-24）

按用户要求，本轮停止新增日线/因子采集、追加和累计。计划任务 `Codex-V4-OperationalDaily-28765` 核实为 Disabled（最近执行 2026-10-14，NextRun 为空）；没有对计划任务或任何服务作更改。PG 只读核对显示 SourceIngress 最新日期为 2026-10-23。

用现存 `config/.env` 的安全配置，在 `market_research` / `127.0.0.1:5432` 执行只读审计。SourceIngress 7 个日期合计 38,974 行，逐日与其已保存的 `bars.json` 按完整证券集合及 open/high/low/close/amount/volume 六字段比较：缺行、额外行、数值字段差异、重复证券身份、空字段、非正价格、OHLC 区间错误、负 amount/volume 均为 0；每份源文件 SHA、字节数和行数均与收据一致。所有收据均仍是 `candidate_only=true`、`production_accepted=false`，故修复目标不是把这些非 PIT 样本改标成正式来源。

以生产只读 loader 从仓库根验证 R9 已有 10/20、10/21 Priority 与 Lifecycle Owner：两日 Priority 均为 5,224 股票 + 400 板块；Lifecycle 各 400 行；版本封存、Owner digest、payload/逐行 digest、日期/token/PG 身份一致。此次只读校验未修改 PG。canonical V4 的 `market_universe_snapshots`、`market_universe_snapshot_rows`、`publications`、`publication_heads` 目前均为 0 行，没有需要回写的已发布错误 breadth/Publication。

已确认且不可用现有数据修成真值的边界：

- 绑定历史 universe 在比较日 2026-10-14、15、16 没有四板块成员；而 Core 投影存在约 5,225/5,226 个身份。旧 Core 分母结果不能继续消费；R10 源码现已在该缺口下返回 `SOURCE_INCOMPLETE`，不从 Core 伪造历史 denominator。没有权威 PIT 成员源前不写值。
- 10/20、10/21 Priority 中 `INVALID_INPUT` 记录分别为股票 49/42、板块 5/5；另有缺字段记录按合同 `NOT_RANKABLE`。这些记录来自现存重建输入缺失/不可用字段，现阶段没有可证明的正确替代事实，保持 fail-closed，不能补中性值。
- 10/22 BaoStock 与 TDX 的 4,789 个 amount 表示差异及 139 个未证明 provider-generation 的共同样本继续隔离审计；TDX 为 raw amount 权威，BaoStock 是 audit-only。差异本身不证明任一来源损坏，未覆盖写入。10/23 BaoStock 日线/因子和 10/22–23 Identity/Member 权威来源缺失；按停止累计要求不再请求新来源。
- D0 cutoff/seal、D2 冻结失效价生成和 Focus Priority 排序合同仍缺。它们属于缺业务合同，不是允许通过重算或改历史行“修复”的数据。

审计过程曾把一条仓库根 Lifecycle 绑定误判为临时链目录缺失；Schema 身份计算确认 R9 绑定属于仓库根后，已从原字节备份将临时目录恢复至原 SHA-256 `dc6015bcfafe0354062b4089a4042cef2bf7a97dce6ae4fe64e5cc419cc48722`。随后仓库根 Priority/Lifecycle 两日只读 loader 全部通过。无 PG 写入或遗留候选根改动。机器记录见 `existing_data_repair_audit`。

本轮结论：**没有发现 SourceIngress 或已绑定 Priority/Lifecycle Owner 的可确证数值损坏；没有应当立即覆盖的 PG 行。** 已有源码修复负责阻止错误 breadth 分母复用；仍待权威历史成员数据和业务合同的项目明确列为阻断，不报告为全部数据问题已清零。
