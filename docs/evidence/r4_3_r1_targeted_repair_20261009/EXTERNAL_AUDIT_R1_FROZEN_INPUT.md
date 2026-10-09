# 大A V4｜R4.3 四交易日数据及生产切换独立外审 R1

- 审计日期：2026-10-09（北京时间）
- 审计目标：`NanOns/a-share-market-structure-research`，`codex/v4-fp14-r2-repair`
- 精确 HEAD：`52f097f82cb1dfee58b20b1a93e3339b1dc37eac`（`Record verified R4.3 full Drive archive and Git delivery receipts`）
- 继承上轮：`1053f07afa9c5d16940c9aa7483eb1bad8690b3d`；未变动 `codex/v4-system-reform` 的已知 HEAD：`c010b818811689ed3056c6500ca5caa5cbadde4e`
- Drive 任务依据：《V4_R4_3_四交易日基础数据全闭环_通达信最新成员统一回算_正式验收与前端顺序门_20261009.md》；仓库 `AGENTS.md`；`docs/evidence/r4_3_four_session_closeout_20261009/R4_3_TASK_CONTRACT.md`
- **唯一总判定：`EXTERNAL_ACCEPTANCE_BLOCKED`**。
- 分层：`FOUR_SESSION_RAW_ENGINEERING_PASS`、`LATEST_TDX_RETRO_CANDIDATE_MATERIALIZED`、`CORE_PROFILE_REBUILD_REPORTED_PASS`、`SNAPSHOT_REPARSE_ASSERTION_CONTRADICTION_FAIL`、`LIVE_CUTOVER_FAIL`、`UI_COMPATIBILITY_CUTOVER_BLOCKER`、`FULL_EXTERNAL_BINARY_ORACLE_NOT_VERIFIED`。

> 本轮通过实际 GitHub 分支 HEAD、已提交代码和冻结 JSON/MD 证据、Google Drive 最新任务与归档信息进行独立审计，对部分数字口径、跨日求和及版本关系独立交叉核对。大型 Git LFS ZIP/Owner 二进制未在外部审计运行环境中全部下载并复算；开发方的本地 SHA、数值、测试“PASS”不能自动升级成外部二进制验收。本审计不修改生产指针和旧版收据。

## 1. 总体结论：与 R4.2.1 相比，真正完成了什么

本次**实质完成**了一份 2026-10-09 09:44:01+08:00 采集的最新 TDX 行业＋概念成员快照 S，四个交易日均使用同一成员集合回算，原 CSRC 83 行业不再作为 V4 正式板块主对象。源码和材料显示新 `owner_v3` Core/Profile、行业/概念 Native、LOO、Rotation、Market、Focus/Forward、日 K 涨跌幅限制、事后突破观察均有实际生成的候选，而不是只有等待源数据的状态。候选 `/api/v4/` 同 context token 读取已进行工程验证。

**尚未完成**：本轮新版本真实来源→快照 S 的复解析有可证明的代码矛盾；生产新 operational Head 未写入、线上仍 9 月 30 日；当前新版本发布后 `/v4` 将被替换成 R4.3 调试页面，违反保留产品主工作台的兼容性要求；外部真实二进制独立复核及最终生产准入未完成。因此不得以开发方 `FOUR_SESSION_OPERATIONAL_RECONSTRUCTED_PASS` 替代完整 R4.3 外部通过，也不能启动 FP-01～FP-14 的全面前端修复阶段。

## 2. 四日对账

| 目标交易日 | T-1 | T-3 | canonical 股票身份数 | 真实 RAW BAR | 经核对停牌无 BAR | 最新 S 可计算板块 | 相对 TDX 板块 known | Rotation 结果计数合计 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 2026-09-28 | 09-24 | 09-22 | 5,222 | 5,210 | 12 | 400 | 5,134 | 400 |
| 2026-09-29 | 09-28 | 09-23 | 5,223 | 5,211 | 12 | 400 | 5,136 | 400 |
| 2026-09-30 | 09-29 | 09-24 | 5,224 | 5,213 | 11 | 400 | 5,134 | 400 |
| 2026-10-08 | 09-30 | 09-28 | 5,224 | 5,209 | 15 | 400 | 5,128 | 400 |

独立根据 `03_RECONCILIATION_ACCEPTANCE.json` 复核，四个日期分别满足 `canonical_rows=actual_raw+verified_suspension`；独立根据 `06_FOUR_SESSION_RETRO_TDX_SECTOR_NATIVE_ROTATION_LOO.json` 加总各日 Rotation/B0 类别均为 400。上述是**已提交 JSON 的独立逻辑一致性核对**，不等于重新读取所有股票 `.day` 二进制。国庆 10/01～10/07 无伪造完整日线；10/09 未计入四日。

最新快照 S：

- 身份 `TDX_MEMBER_SNAPSHOT_S_20261009_44f6d2c7cfd4eaf4b218bf237b7776aad81ab11b54b2c01175e6eebf9a65b0ca`。
- 源 `tdxhy.cfg`、`tdxzs.cfg`、`infoharbor_block.dat`；均有原始文件字节尺寸和 SHA 声明。
- 133 行业（110 叶级＋23 个父级解释层），268 概念，合计 401 个源 sector ID；其中 `INDUSTRY:T00` 无合法映射被隔离，四日均有 400 个实际可计算板块。
- 55,136 条 TDX 关系 = 52,912 已映射 + 2,224 未映射。未映射主要是北交所 2,206，另沪市 6、深市 12；未映射不是“没有这一天的 K 线”的同义词。成员主集合与旧 9/30 已接受的 378 板块/50,162 关系**属于不同快照口径**，原 Head/digest 不能覆盖。
- 新 S 是 `RECONSTRUCTED_LATEST_MEMBERSHIP`，`AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`survivorship_bias_risk=true`。允许运营回算，**严禁**将其当作原时点信号、历史真实成分和已验证历史绩效。

## 3. 子系统验收矩阵

| Gate | 证据及审计判断 | 状态 |
|---|---|---|
| G01 任务范围、冻结与交付 | R4.3 已独立任务卡，HEAD 及证据真实增加，Git 当前分支与 Drive 归档索引存在 | **PASS** |
| G02 四日 TDX RAW／状态 | typed RAW 5210/5211/5213/5209；12/12/11/15 停牌；18 个非 A 股异常按 V2 分类隔离，不污染股票目标域 | **PASS_ENGINEERING_SCOPED** |
| G03 GBBQ、复权与数值 | 报告源 GBBQ 193,554 事件、128 真实跨场景数值样本、全量当日 RPS 41,786 次及部分前驱 26,119 次、涨跌幅限制 103,680 次，零误差声明；无外部全部二进制重执行 | **DEGRADED_PASS／NOT_VERIFIABLE_EXTERNAL** |
| G04 Core/Profile 新版本 | 新 `owner_v3/W3_W5_RECEIPT.json` 明确 `corrected_candidate_rebuilt=true`，与 R4.2.1 的 `false` 相比是实际进展；严格历史可用性和部分 prior episode 仍保留 UNKNOWN | **PASS_CANDIDATE_BUILD／正式待验** |
| G05 最新 TDX 成员回算 | 一份 S 应用于全部四日；行业叶/父/概念分类；真实 Sector、LOO、B0、Rotation 有四日计数；与 CSRC 辅助空间分离 | **PASS_CANDIDATE_SCOPE，来源复验 FAIL** |
| G06 证券覆盖 | 已映射关系 52,912，未映射 2,224 单列；BSE 继承 optional degraded，不可宣称全部沪深北全覆盖 | **DEGRADED_PASS** |
| G07 Focus、Forward、市场与特殊字段 | 提交 2477 episodes／7524 events、3418 OBSERVED／9742 PENDING，真实后验研究和日 K 风险可用；日内触板、历史首见等不得补造 | **PASS_CANDIDATE_SCOPE** |
| G08 自动运行／回滚 | 37 项定向测试自报 PASS；独立 E 盘 CAS、NOOP、陈旧锁、坏源、回滚与拒绝 PIT 升级演练 | **PASS_STAGING_ONLY** |
| G09 真正外部数值与成员复验 | LFS 对象尚未在本外审运行环境里完整读取复算；**发现来源快照复解析的代码/收据硬矛盾** | **FAIL＋NOT_VERIFIABLE** |
| G10 同版本候选 UI/API | 工程候选四日期同 token API 可读；候选 R4.3 页面只是 debug preview，非现有 V4 主产品 | **PASS_CANDIDATE／主站兼容 FAIL** |
| G11 真正生产接收 | `11_FOUR_SESSION_LIVE_API_SAME_CONTEXT_AND_UI_READBACK.json` 标记 `production_cutover=false`；原已接受 `/api/v4/context` 仍 9/30 | **FAIL** |
| G12 前端 FP 续接门 | R4.3 W7 尚未通过，W8 未启动，符合既定顺序控制 | **NOT_STARTED_AS_REQUIRED** |

## 4. 两个必须修复的 P0 硬问题

### R43-P0-01：最新 TDX 快照“重新解析逐行相等”证明自相矛盾

同一个 Git SHA 下：

- `src/workbench_analysis/tdx_member_retro_r43.py` 的 `capture()`（约 103～113 行）构造原始成员字典时写入 `industry_level`、`primary_industry_rank_eligible`。
- 同文件的 `reparse_verification()`（约 65～73 行）构造新的成员字典时**未写入上述两字段**，随后执行 `assert rows==original and digest(rows)==s['member_digest']`。
- `src/workbench_analysis/corrected_owner_replay.py` 的 `gzwrite()` 直接对每一整行进行 JSON 序列化，不会默默剔除这两个字段。
- `SOURCE_CAPTURE_REPARSE_VERIFICATION.json` 仍报告 `exact_names_identity_members_equal=true`、`FROZEN_SOURCE_REPARSE_PASS`，并将已执行 verifier 绑定到相同源码 hash `6883083416f887b2c0fa193c3bd9bac736c48d667efe03b46cdb28b38fd1a629`。

**判定**：在当前提交的同一段代码下，若快照包含捕获端新增的两字段，复解析端生成的字典无法与它逐行相等。冻结后的快照本身未被证明错误，但这一项复验 PASS **与源码不一致**，不能直接签发来源独立验收。必须以实际完整行样本复核字段差异，修复复解析端的字段构建并重新运行，给出准确执行命令、退出码和新 SHA/收据，旧错版留档；不得手改 `true`。

### R43-P0-02：正式数据切换将错误替换现有 `/v4` 主界面

`src/workbench_service/v4_server.py` 约 24～29 行在 `accepted_api(root)` 有效后，直接返回 `src/workbench_service/static/r43-operational-preview.html`，抢占 `/`、`/v4`、`/v4/` 原 UI 路由；后面的正式 `research/index.html`／`v4-workbench.html` 路由不能再到达。

该 preview HTML 只是单页下拉框＋少量 JSON 输出，**不是**已有产品主站，也不是目标六入口/完整前端。因此若 W7 放行就直接切 Head，用户可能看到页面反向降级。这是**发布前最低兼容门**，与后续尚未授权实施的 FP-01～FP-14 页面完整开发不是同一任务。

修复条件：维持 `/v4` 原已接受页面/现有导航入口，R4.3 预览仅置于 `/v4/operational-preview` 之类独立路由；新 operational 数据通过经过版本治理的 BFF/adapter 与旧页面兼容，至少验证 context token、API envelope、列表分页、详情、来源标签与无数据降级。若旧页面需要改造，最小必要兼容桥须纳入 W7，而非等 W8 后再解决。正式发布前模拟操作新 Head 进行服务路由回归，比较切前切后的页面和 API，证明未丢原入口；旧 9/30 last-good 可回退。

## 5. 尚未阻断独立可用计算、但必须标明范围的缺口

1. **BSE／无身份 2,224 成员关系**：BJ 2,206 / SH 6 / SZ 12。影响分母或板块覆盖度，必须逐板块可解释并隔离，不得把未知身份视作真正不存在。
2. **部分后验字段仍 UNKNOWN**：Breakout 首次事件、历史 prior episode、真实日内触板、严格 T0 首见等不能凭 10/09 最新成员集填补。
3. **原产品成员体系与新回算并存**：9/30 原 accepted 378/50,162 和 S 回算 400／55,136 不能混用做 T-1、T-3；只对四日 S 作同口径运营比较。
4. **外部原始大字节门**：17 段 Drive 归档和 Git LFS receipt 证明归档动作发生，但本次没有实际合并 1.13GB 全量文件、按独立解码器重新核算；外部 full-binary 验收仍是 `NOT_VERIFIABLE`。不要把打包成功当算法完成。
5. **新规范的外部准入文件不可自签**：`r43_operational_publication.cas()` 对生产要求精确 candidate_digest 的独立 `EXTERNALLY_ACCEPTED_R43_OPERATIONAL`；当前并无此项可证明审计。签署要基于修复后源码和真实输入，不得写入伪造授权记录。

## 6. 唯一下一轮执行顺序与升级条件

1. **先补 R43-P0-01 的可复现来源断言矛盾**；保留原冻结成员 S 与全部源，不擅改真实身份。核查独立 verifier 重新解析同三份文件，可被外部复算，并保留一负例（一成员变更）必失败。
2. **并行修 R43-P0-02 的路由与消费者兼容**。预览与正式 UI 分离；最小 E2E 验证候选启用与回退的原 V4 页面和 `/api/v4/*`；不能让生产发布变成调试页发布。
3. 根据新验证结果完成真实二进制/source oracle 独立范围复核（至少原始 ZIP、最新 S、四日 Core、跨除权 128 个样本中的高风险对照、四天行业/概念 40+ 分层 LOO）；对未核实的范围独立降级、不能假装全部通过。
4. 修复后生成**新的**版本化 candidate digest／新的工程证据/独立审计记录，重新验证 staging CAS、stale、bad source、回滚。
5. 达到本次四日运营研究独立验收条件后，执行合法 production CAS，并实际访问线上 `/api/v4/context` 检查 `2026-10-08`、四日期同 token、各域有可用数据、正式 V4 页面未退化；保留原 9/30 Head。
6. **只有生产 readback 和四日运营数据正式验收通过**才启动此前已归档 FP-01～FP-14 的其余页面补全任务；Forward 统计显著性和 strict PIT 历史真相仍按独立范围滚动验证，不应无限阻塞本阶段可用域。

## 7. 证据入口（精确 SHA）

- [R4.3 Git commit](https://github.com/NanOns/a-share-market-structure-research/commit/52f097f82cb1dfee58b20b1a93e3339b1dc37eac)
- [R4.3 handoff](https://github.com/NanOns/a-share-market-structure-research/blob/52f097f82cb1dfee58b20b1a93e3339b1dc37eac/docs/evidence/r4_3_four_session_closeout_20261009/R4_3_EXTERNAL_AUDIT_HANDOFF.md)
- [成员源复核代码](https://github.com/NanOns/a-share-market-structure-research/blob/52f097f82cb1dfee58b20b1a93e3339b1dc37eac/src/workbench_analysis/tdx_member_retro_r43.py)
- [成员复解析声明](https://github.com/NanOns/a-share-market-structure-research/blob/52f097f82cb1dfee58b20b1a93e3339b1dc37eac/docs/evidence/r4_3_four_session_closeout_20261009/SOURCE_CAPTURE_REPARSE_VERIFICATION.json)
- [V4 入口与路由](https://github.com/NanOns/a-share-market-structure-research/blob/52f097f82cb1dfee58b20b1a93e3339b1dc37eac/src/workbench_service/v4_server.py)
- [快照 S 元数据](https://github.com/NanOns/a-share-market-structure-research/blob/52f097f82cb1dfee58b20b1a93e3339b1dc37eac/docs/evidence/r4_3_four_session_closeout_20261009/MEMBER_SNAPSHOT_S.json)
- [四日板块、Rotation 和 LOO](https://github.com/NanOns/a-share-market-structure-research/blob/52f097f82cb1dfee58b20b1a93e3339b1dc37eac/docs/evidence/r4_3_four_session_closeout_20261009/06_FOUR_SESSION_RETRO_TDX_SECTOR_NATIVE_ROTATION_LOO.json)
- [同版 API 与 UI 候选/生产区别](https://github.com/NanOns/a-share-market-structure-research/blob/52f097f82cb1dfee58b20b1a93e3339b1dc37eac/docs/evidence/r4_3_four_session_closeout_20261009/11_FOUR_SESSION_LIVE_API_SAME_CONTEXT_AND_UI_READBACK.json)

**正式签署**：`EXTERNAL_ACCEPTANCE_BLOCKED`。不能声称“R4.3 四日全链正式验收通过”或“10/08 已上线”；认可四日真实行情＋最新通达信 S 回算的工程候选成果，但当前来源复验与生产发布兼容门尚未关闭。
