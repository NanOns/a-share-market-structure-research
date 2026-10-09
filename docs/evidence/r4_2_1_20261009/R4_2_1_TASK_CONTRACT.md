# 大A V4｜R4.2.1 通达信板块主体系纠偏、增量范围修复及连续闭环执行任务卡

- 版本：R4.2.1 / 2026-10-09（R4.2 增量修复合同+板块数据源一致性 P0 纠偏）
- 目标仓库：`NanOns/a-share-market-structure-research`
- 当前执行分支：`codex/v4-fp14-r2-repair`（启动时先验证 HEAD，当前审计基线 `fc40acc4ceb4a41002ee3a0ba8ce75f9d7885bc5`）。不要擅自移动 `codex/v4-system-reform` 或其他分支。
- 冻结任务范围：2026-09-28、09-29、09-30、10-08 四个交易日；10-01～10-07 休市，不生成行情。10-09 盘前绝不制造未完成交易日的数据。
- 继承最高约束：`AGENTS.md`、Driver R4.1 原卡及外审 R1、`docs/evidence/r4_1_audit_repair_r1_20261009/HANDOFF.md`、`docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/` 的不可变收据。
- **原产品不可变身份**：V4 板块主体系为通达信行业+概念的板块和成员关系。BaoStock 的证监会行业分类 `BAOSTOCK_CSRC_INDUSTRY` 是**隔离的辅助实验维度**，没有得到替代 V4 378 板块/50162 条现有成员关系的授权。对 10/08 则需要独立取得真实当天板块和有效成员；不能机械假定仍是 378 或 50162。
- **授权范围**：本任务授权连续开发、真实测试、候选产物重建、审计收据及提交推送；**不授权越过正式生产独立准入门、强行改动已有 accepted Head、回填虚假 PIT 或将 UNKNOWN 变 FALSE。** 对生产发布，应具备独立校验及现行发布合同许可；否则交付完整可验收 successor candidate 与明确单项待验收门。

## 0. 为什么上轮不应在 BLOCKED 报告处停止

R4.1 审计修复阶段的 `STAGE_CONTRACT.md` 自行将执行限制为 ZIP 字节与算术复核、日更错误诊断、未绑定身份分类；它要求保留生产 pointer。`AGENTS.md` 要求下一受控阶段有明确授权，这可以解释上轮阶段交接，却**不说明代码不能继续修**。本卡明确授权仍可独立解决的工程子链，不把每个子链的审计门误当作整个执行停止条件。

仓库 `src/workbench_analysis/tdx_snapshot_delta.py` 的 `build_tdx_package_delta()` 会遍历 **所有 changed/added `.day`**，直接以 `_records()` 的普通 OHLC/date 条件校验，任何一个异常抛出 `TDXDeltaError`，整日 delta 不能形成，正式 BaoStock capture 分支也不能到达。`scripts/build_dm01_r4_tdx_delta.py` 是实际中断位置；现有正式 `source_readiness_receipt_r2.json` 为 `BLOCKED_TDX_DELTA_NOT_READY`，并额外报告 `BUILDER_REGISTRY INPUT_DIGEST_MISMATCH`。

`OFFICIAL_PACKAGE_STRICT_DELTA_BLOCKERS.json` 提供 18 项：

- 上证指数及特殊指数/品种：`sh000001`、`sh000002`、`sh000003`、`sh000833`、`sh880006`、`sh880016`、`sh880036`、`sh999997`、`sh999998`、`sh999999`；
- 沪市其他品种：`sh111006`；
- 深市回购及 B 股：`sz131804`、`sz131807`、`sz200012`、`sz200013`、`sz200015`、`sz200053`；
- 深证指数：`sz399001`。

**这 18 项均非正常 A 股股票代码族；这是类型和消费范围需核查的强线索，并非宣称记录本身必然合法。** 任何异常都不能无记录地跳过；指数需要单独符合指数/市场 Owner 的合法数据路径，B 股/回购不能混进 A 股画像，未知身份应 fail-closed。

已完成且不可回退的工程结果：真实官方 551,544,006 字节 ZIP 已采、CRC PASS；前三日原 528 条 QFQ current/prior ATR20 corrected candidate 已恢复、35 条停牌无 BAR；四日 Core/Profile 候选和部分结构/**隔离 CSRC 行业实验候选**已构建；线上 last-good 为 09-30。不再把这些工作从零重做。

## 1. P0-A｜彻底修复 18 项异常导致全 A 股日更阻塞

1. 锁定并分别核验 parent/current 两个官方 ZIP 的精确 SHA/CRC、四日 `.day` 条目、变更清单及证券类型；对 18 项逐个输出 `path, market, inferred_type, verified_instrument_class, current_sha, parent_sha, current_target_bar?, validation_error, consumer_scope, action, authoritative_classification_evidence`。
2. **新增版本化、按品种/consumer scope 的 Delta V2 合同**。把官方**整包字节完整性**（ZIP SHA、CRC、路径安全、重复项、文件损坏）和目标研究**A 股可接受日线记录**分成两个清晰门。A 股目标范围仍校验 OHLCVA、交易日单调、目标日期、行长、涨跌停与交易状态相关机制（在具备对应正式合同的部分）。非目标品种记录必须明示 `NON_A_STOCK_ENTRY_QUARANTINED` / `INDEX_SEPARATE_CONSUMER_REQUIRED` / `UNSUPPORTED_INSTRUMENT` 等分类，附字节 SHA、具体异常、可恢复入口；不能像不存在一样丢掉。
3. 对标准 A 股代码也必须验证身份及生效区间，不得依靠仅 `sh.6/sz.00/sz.30` 的字符串前缀自动正式接受；BJ 原始行、历史转代码或未绑定 identity 单列待核验。无明确品种归属或 A 股本体出错的记录继续 fail-closed。
4. 保留原 `TDX_PACKAGE_DELTA_V1`、旧 receipt 与旧 accepted head；建立 V2 新适配器/测试/迁移说明。不要把旧版本合同的 digest 改成一个新的值假冒既有签名；如需兼容，独立新增 `source_scope_policy` 与 typed delta output，写全量 anomaly manifest 和目标内有效 BAR digest。
5. 检查源的 `removed`, `truncation`, `rewrites`, `historical_correction`：目标内不许放松；非目标品种变化不能被当作不存在，作为独立异常域存档。**不能通过捕获所有异常并 `continue`，或把异常 18 条做 hard-coded 白名单绕过。**
6. 必须真实重跑完整 10-08 和回放 09-28/29/30。验收不是“18 条测试绿了”，而是目标域 delta 真实 READY、目标有效证券清单/哈希、合法排除项/异域异常计数可交叉核验。给出正反例和当前源码路径。

## 2. P0-B｜修正式 DM01 真实业务入口，不要停在上一异常或错误 WAIT

1. 按 `scripts/run_v4_dm01_daily_increment.py` → `build_dm01_r4_tdx_delta.py` → BaoStock 日期批量/因子 → GBBQ/身份/特殊阶段 → `project_source_freeze` → builders → data head 真实顺序逐门执行。
2. A 股目标域 delta 通过后，**必须实际运行其后 BaoStock 入口**并冻结 SDK response、请求预算、日期及源错误；其正式生产采集是否可用与 R4 早期专项联网补采是不同 Gate，不能混淆。
3. 独立检查 `accepted_builder_registry=BLOCKED_BUILDER_REGISTRY / INPUT_DIGEST_MISMATCH`：核对旧 Seal 绑定的源/代码与新实际 Delta V2、builder 的契约差异，新增审计通过的 successor Seal / Registry，保存前驱 SHA、类型、运行窗口、对照样本，保留旧 Seal 不动。绝不通过跳过验证、替换历史 hash、人工改 PROMOTED 来骗过门。
4. 子脚本 `exit_code=0` 的 `WAIT_*` 仍是 WAIT；只接受具有当前目标日同一 source/Owner/合同的真实 `PROMOTED` 或 `NOOP_IDENTICAL`。缓存再用记 `NOOP_SOURCE_ALREADY_FROZEN`，不得将其当成本轮发生新的 HTTP 获取。
5. 若某个辅助源无法合法启用，只隔离相关能力域，不得重新把已验证的 A 股 RAW / Core / Profile 全部清空。受控降级需有新的合同、数值 oracle 与明确 UI 源标签，不得把 corrected 候选改造成事后 `AS_RECORDED`。

## 2A. P0-TAX｜恢复 V4 通达信行业/概念为唯一正式板块—成员主体系（用户新增强制纠偏）

### 2A.1 已核实的问题位置（不是单纯 UI 标签）

- 原 V4 的当前 accepted 2026-09-30 板块记录为 **378 个板块和 50,162 条成员关系**，包含通达信行业/概念。四交易日新研究中，`src/workbench_analysis/corrected_sector_replay.py::dated_industry_memberships()` 读取 BaoStock `query_stock_industry`，构造 `BAO_CSRC:` 命名空间、`BAOSTOCK_CSRC_INDUSTRY` taxonomy；`materialize_sectors()` 用它作为 `sector.native_r5.build_native()`、LOO、相对板块强弱的成员输入。`src/workbench_analysis/corrected_market_rotation.py` 对同一 **83 个 CSRC 行业**做 B0/Rotation；这是一个**另一分类体系的运行结果**。
- `config/v4_dated_membership_source_policy_v1.json` 明言 `TDX_taxonomy_substitution=false, concept_coverage=false, production=false`，原代码报告 `SECTOR_REPLAY.json` 也承认 `CORRECTED_CSRC_TAXONOMY_ONLY`。因此绝对不得把“83 行业算完了、相对强弱 known 5129”等当成 V4 原通达信板块的完成/通过。
- **精确消除过度归因**：`corrected_sector_replay.py` 的 `base_seed_state` 是在 CSRC 行业分组**之前**，由股票本身 Core/Profile 及上个交易日输入计算。`corrected_focus_replay.py` 虽从 `sector["seed"]` 读取它作为 PREWATCH/D2 部分输入，并不自动代表 CSRC 成员污染了数值。必须做输入血缘追溯和 hash/数值对照，不能未经验证就把 Core、Seed、PREWATCH、Focus 全部认错或重跑。

### 2A.2 严格数据源与字段隔离

1. **主板块唯一正式 Owner**：TDX 原行业/概念（包括真实 `sector_id`、`sector_type`、source/provider revision、成分股 security entity id、成员有效时点）。在正式 V4 `sector_native / sector_rs / breadth / ma20_width / Base-Seed 聚合 / B0 / Rotation / relative_sector_state / homepage sector ranks / Focus mainline sector` 的板块字段，**只能消费这个 namespace**；`BAO_CSRC:*` 不得进入主榜单、主字段或新 V4 发布门。
2. **辅助 CSRC 用途**：允许继续冻结为独立 `auxiliary_taxonomy=BAOSTOCK_CSRC_INDUSTRY` 的实验分析或辅助比较，结果名必须另开 `relative_csrc_industry_state`、`csrc_sector_native` 等辅助字段；不得复用原 V4 `relative_sector_state` / `sector_rs5` / `rotation_state` 这些主合同字段，不能把同名结果换个标签再次灌入主链。
3. 对原新四日记录的 `relative_sector_known=5135/5137/5135/5129`，需要在审计报告中**改列为 `CSRC_AUX_RELATIVE_KNOWN`**，不再算 `TDX_V4_RELATIVE_SECTOR_KNOWN`；对旧四日 `83` 个 Rotation UNKNOWN、10/08 B0=21/32/30，重新标注 `CSRC_AUX`，不得用于 TDX 378 原板块完成率。
4. 9/30 原已接受 TDX 378/50162 保持不变。对 9/28、9/29、10/08：检查本机通达信分类及板块文件（如 `T0002/hq_cache/tdxhy.cfg`, `tdxzs.cfg`, `infoharbor_block.dat`，以及存在且格式受支持的板块缓存）、对应已冻结官方源、历史版本和最早可见时间；建立按 `trade_date` 的 `TDX_SECTOR_MEMBERSHIP` owner，**有确切有效日证明才准入**。10/08 当天在 10/09 才采到的分类文件即使文件 mtime 为 10/08，也不证明 10/08 收盘时所见；不得用修改时间倒推有效时点或拿 9/30 成员前/后填充。
5. **可行时分域恢复**：对 9/30 的已接受 TDX 同日板块数值坚持复核不回退；对有有效当日 TDX 证据的其余日期完成同口径源适配、冻结与 Core→Sector→LOO→Rotation 运行；缺成员有效性仅将依赖成员时点的原 V4 对应字段标为 `UNKNOWN/NO_ACCEPTED_TDX_DATED_MEMBERSHIP`，**不能阻塞四日股票 RAW、Core、Profile 和无成员依赖的独立 Seed**。
6. 任何用 CSRC 行业实验提前构造的历史 `prior rotation`、`sector rank velocity`、`relative_sector`、板块强弱/主线选择，均禁止跨 taxonomy 回灌成 V4 TDX 前驱。跨 taxonomy 算术即使数值相等也不具语义等价性；历史 T0 一样遵守 first-available 和 corrected-only 边界。

### 2A.3 必须进行的下游污染审计

- 构造字段级依赖清单，逐项标记 `TDX_PRIMARY / CSRC_AUX_ONLY / STOCK_ONLY / UNAFFECTED / UNKNOWN_UNTIL_PROVEN`，至少覆盖：`sector_rs1/5/20`、Breadth、MA20 width、Base/Seed 行业汇总、B0、Rotation、stock `relative_sector_state`、`relative_market_state`、stock `base_seed_state`、PREWATCH、D0/D2、Focus、Forward、主页板块排名、个股研究展示；不能只写“已禁替代”。
- **成对对照**：9/30 原 accepted TDX 同日板块输入与本轮 CSRC 同期输入，比较 universe `sector_id/sector_type/sector_member_count/member_digest`；对至少 30 个同日不同领域证券比较 TDX 成员下的 LOO 与 CSRC LOO 的可能差异；Seed/PREWATCH 若经依赖证据证明只依赖股票字段，应列 `UNAFFECTED` 并保留不重算。
- 实际回放并断言：改变 CSRC 行业成员不会改变原 V4 任一正式 sector/relative-sector/主线消费者的结果；更改合法 TDX 有效成员（测试夹具）应使其依赖链正确失效/重算；缺 TDX 有效成员时主字段 UNKNOWN 而辅助 CSRC 值可保持。不能把“provenance 标为不同”当作数值链真正隔离。

### 2A.4 专项完成门

- 保留原 9/30 TDX 板块 378/50162 的身份与成员 digest；只在 9/28/29/10/08 的 TDX 日期成员证据被实际验证后推进该日正式板块能力。
- `V4_PRIMARY_SECTOR_TAXONOMY=TDX_INDUSTRY_CONCEPT` 必须由新的版本化字段契约、producer registry 和 consumer adapter 明确校验；`BAO_CSRC` 不能被无声明复用，测试需故意注入错误 namespace 验证拒绝。
- 正式输出与页面不许展示以 CSRC 替代出来的“领先行业、领先概念、主线、相对板块、轮动”的数值。CSRC 辅助视图另名另 namespace、默认不参与 V4 主研究评分。只有确切 TDX 历史成员和必要前驱链通过时，才恢复相应主字段。

## 3. P0-C｜合法候选 Owner 和新发布门，连续修到可验收

- 复用 R4.1 已冻结真实 Core/Profile、prior target-coordinate、结构、**隔离的 CSRC 辅助行业（不得替代原 V4 主板块）**、D0/D2、Focus/Forward 的 source-digest 绑定，检验新的有效增量与既有候选是否一致。若输入变更，追加 corrected version，原始 T0 与旧收据不覆盖。
- 单独验收：官方原始 RAW；当前/T-1 MA20/ATR20；跨复权事件；8-10 个真实异常边界（停牌/上市/代码转移/跨源冲突）；独立脚本不调用生产同一计算内核。`528/528` 只声称已满足相应窗口的候选，不把跨事件长窗口硬认通过。
- 生产 successor 只允许纳入 `OFFICIAL_TDX_RAW_CURRENT_CANONICAL_SUBSET`、经过正式版本批准的 `CORRECTED_CORE_PROFILE` 等**源和算法都完成独立 QA**的域。历史通达信行业/概念成员有效性、原 378 板块轮动、未认证 BJ 身份、无 prior breakout、strict PIT、法律涨跌幅/市场压力缺口明确排除。必要时新版本 typed `source_mode` 标注 corrected/reconstructed，而不能充作当时首次可见。
- 如当前发布合同不授权这些新域，只做已完成的 successor staging、fail injection、stale CAS、same-hash noop、精确 predecessor rollback 测试，提交正式 `SCOPED_ADMISSION_REQUEST`；不要假报线上 10-08 已切换。
- 被新测试证明来源、契约和准入已接受时，再按原子 CAS 安全发布，并验证 `/api/v4/context`、股票/板块/诊断/Focus/Forward 同一 context token 的 10-08 数据。生产回滚机制必须保留 09-30 last-good。

## 4. P1｜与 18 项异常无关的工作必须并行继续

- BJ canonical identity：将当前 `246` 个 BSE stable candidates / `101` 个 unresolved / `1` 个 lifecycle case（加 2 个排除的指数）按身份 source 边界做独立可批准候选，不要统一叫“348 缺行情”。未批准的 identity 不进正式 A 股候选。
- 股票 `basic_breakout_state` 初始事件和 prior episode：单独查源码实现、真历史事件与记录可用性；没有可信的 prior absence 不得 `UNKNOWN→FALSE`。
- **执行 §2A 的板块分类强制纠偏**：TDX 行业/概念是原 V4 唯一正式 taxonomy；83 CSRC 行业仅供独立辅助分析。10/08 当前成员有效日不能凭 10/09 采集或 10/08 文件 mtime 倒推。TDX 有效数据缺失时主字段 UNKNOWN，不得用 CSRC 代入。
- Rotation、价格涨跌限制、Focus/Forward 到期、真实退出/重入等仍需各自 Owner 真样本。**不要求等待未来 20 日样本才推进不依赖这些样本的生产代码。**

## 5. 连续执行和强制收尾标准

只要原始 ZIP 可读、编程所需组件可编辑、目标域 A 股的数值可验证，就必须继续 P0-A → P0-B → P0-C。某域 `BLOCKED_SCOPED_EXTERNAL_OWNER_ADMISSION` 时允许暂停**该域的正式发布**，不允许暂停其他已授权的代码修复；可以按子域提交推送，但不因第一个非 A 股异常或第一个缺 Head Seal 就宣布全轮完成。

本轮需要实打实交付：

1. `ENTRY_SOURCE_AND_RELEASE_HEAD.json`：冻结精确 `fc40acc4` 后启动 HEAD、旧发布指针与合同。
2. `OFFICIAL_ZIP_TYPED_ENTRY_VALIDATION.csv`：全部 18 项 + 目标域正反例 + 来源/hash/类型/实际理由。
3. `TDX_A_STOCK_DELTA_V2_RUNTIME_RECEIPT.json`：真实 TDX 新旧包结果，typed-scope 与独立目标 BAR 核算、历史修订检测。
4. `DM01_TDX_TO_BAOSTOCK_FULL_GATE_TRACE.json`：真正进入后续 BaoStock/GBBQ/Lifecycle 步骤及失败具体栈，source 请求计数和无请求的理由。
5. `NEW_BUILDER_SEAL_AND_SOURCE_CONTRACT_MIGRATION.json`：旧/新参数与 digest、权限、回退、接受矩阵。
6. `OCT08_CORRECTED_OWNER_SOURCE_RECONCILIATION.json`：四日 Core/Profile 对照、原 528 基线不回退、各域 known/unknown 及安全用途。
7. `SCOPED_SUCCESSOR_QA_AND_CAS_READBACK.json`：候选、接受权限、测试与生产状态分开；不得声称未发生的发布。
8. `TDX_V4_SECTOR_TAXONOMY_AND_MEMBERSHIP_RESTORATION.json`、`CSRC_TAXONOMY_POLLUTION_MATRIX.json`：原 9/30 TDX 378/50162 对照、四日 TDX dated member 证据、所有 sector→stock/Focus 依赖、CSRC 辅助隔离、有效/无效差异样本；任何将 83 CSRC 当 V4 板块的验证须失败。
9. `R4_2_CONTINUOUS_EXECUTION_LEDGER.json` 与 `R4_2_EXTERNAL_AUDIT_HANDOFF.md`：每项已改源码/运行命令/真实结果/单项 blocker/下一步；`git status` 和远端 push HEAD。

QA：真实 ZIP 输入、18 例分类、18 例里至少指数/B 股/回购/通达信自定义品种、相似 A 股反例、非法目标 A 股失败、历史缩短/重写/缺记录失败、日期窗口、同源重放、错误码准确；不得用 mocks 冒充真实 A 股 delta 正式通过。全部合法可执行的子域完成后才能提交最终交接。凡单项无法执行，给出**无法继续的实际资源/外部权限/输入证据**，不得仅使用旧泛化 `BLOCKED` 文字。

## 6. Codex 一段式启动指令（直接复制）

请将此 R4.2 卡作为 **fc40acc4 之后的新授权工程阶段** 执行，严格遵守 `AGENTS.md`、TDX 只读和正式生产发布门，但**不要把上一轮的“外部验收 BLOCKED”当作禁止继续修代码**。先处理 `tdx_snapshot_delta.py` 对整包所有 `.day` 一刀切校验导致 18 个指数/B 股/回购/其他非 A 股品种阻断 A 股数据的问题：基于真实 instrument identity 和业务消费域，新增版本化 typed delta V2，保存18项异常的原始字节哈希与分类；目标 A 股的长度、日期、OHLCVA、缩短、重写仍严格 fail-closed，不能静默 skip 或 hard-code 18 个例外。用真实两版 ZIP 重跑 10/08 A 股 delta 及历史四日校验；随后必须连续进入正式 BaoStock 日更、GBBQ、生命周期、builder registry 的 INPUT_DIGEST_MISMATCH successor seal 修复、Core/Profile corrected owner 核验及可授权的 scoped successor CAS 测试。生产准入不获独立许可则停在准确标记的 candidate，但不要停止其余可解工程。旧 528 条与 35 停牌不重做；**优先执行本卡 §2A P0-TAX 板块源一致性纠偏：原 V4 通达信行业+概念成员是唯一正式板块口径；隔离 BaoStock 83 CSRC 行业，不得把其 LOO/板块指标/Rotation/relative_sector 代替通达信正式值；独立 Seed/PREWATCH 以真实依赖图核实，不滥判污染。** BJ 身份、TDX 历史概念、breakout prior/rotation 独立分域追踪。完成所有当前可执行步骤后统一推送实代码、真实运行收据及最终审计交接；严禁无实修只交 BLOCKED 报告。

## 7. R4.2 → R4.2.1 变更治理记录

- **原因**：用户发现四日 `SECTOR_REPLAY` 使用证监会行业分类，违背原 V4 通达信行业／概念板块—成员主体系；代码复核确认不是纯展示差异，而是 CSRC 成员被直接输入原 V4-08 sector native/LOO 和 Rotation 计算。
- **硬订正**：R4.1 审计中的 `relative_sector_known=5129` 等 CSRC 候选结果不得作为原 V4 通达信个股相对板块强弱的恢复证据。R4.1 所述“83 行业完成”应仅视为独立辅助分类样本。
- **边界订正**：股票级 Base Seed 来源于个股 Core/Profile，在 CSRC 行业分组之前计算，因此不应直接判定 PREWATCH/Focus 已受 CSRC 污染；必须以消费者字段级血缘和独立对照证实，不可结果倒推。
- **迁移要求**：旧候选和收据保留，只新增 corrected namespace/明确废止原主口径声明；TDX 主链追溯、可验证后重算并另出版本，不覆写已有 T0、9/30 accepted 主板块及生产指针。
- **本轮优先级**：§2A 与 §1/§2 并行 P0；在 §3 正式 successor 准入之前必须完成 taxonomy 隔离门。
