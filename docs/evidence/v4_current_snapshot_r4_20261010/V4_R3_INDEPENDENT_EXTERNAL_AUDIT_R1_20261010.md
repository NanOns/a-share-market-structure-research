# 大A V4｜R3 当前快照工程闭环：独立外部验收审计 R1

- 审计日期：2026-10-10（周六，UTC+08）
- 审计目标：`NanOns/a-share-market-structure-research`，分支 `codex/v4-fp14-r2-repair`
- 精确冻结 HEAD：`6b6d5cbd2b115335918aeeafcec9ae5a46f9eb99`（GitHub API 实时核对）
- 对照基线：`d35a82707e332de1231f5a6369460d06abe056df`，比较显示 `ahead_by=19`，`behind_by=0`
- 正式合同：`V4_IMMEDIATE_EXECUTION_MASTER_AND_TASK_CARDS_R3_20261010.md`；`AGENTS.md`、V4.2.2 REV2、REV4 FEP R2 及之前已接受的各分域合同优先
- 冻结运营 T0：`2026-10-09`；报告中声明的运营 Head SHA：`55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e`；严格 PIT Head SHA：`38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40`
- 成员范围：`TDX_INDUSTRY_CONCEPT / TDX_LATEST_MEMBER_RETRO_V1`，截至 10/09 的最新成员回算，`AS_RECORDED=false`、`PIT_ELIGIBLE=false`
- **唯一完整正式外审结论：`EXTERNAL_ACCEPTANCE_BLOCKED`**
- **工程局部结论：`ENGINEERING_EVIDENCE_PASS_SCOPED / FORMAL_OWNER_AND_RELEASE_GATES_OPEN`**；此为外审基于源码、提交、报告和结构化证据的范围化判断，不表示已经在独立环境重跑完整数值套件、运行用户 Windows 工作台或重算数 GB Owner。

## 1. 审计方法与证据等级

**已亲自核对**：通过 GitHub 读取目标分支现行提交、差异、核心源码 `validation_cohort_read_contract_r3.py`、`research_hypotheses_r3.py`、LOO 与金额/质量独立 oracle、前端 BFF 片段、测试及 `docs/evidence/v4_immediate_r3_20261010/` 下 R3、CONTINUATION、DEEPENING 多版报告和 JSON；通过 Google Drive 读取三次正式交付 MD。比较证实 R3 新增 19 次提交，确有代码、回归与证据，而非只提交“已完成”报告。

**尚未亲自实施**：从开发机直接读取本地大体积原始 TDX/Owner、在独立 Python 环境运行小包全部 oracle、独立操纵 `127.0.0.1:28765/28767` 浏览器或服务进程、确认 10/12 未来会话已发布。因此对“开发方报告 x 项零差异”使用 `EVIDENCE_PRESENT / INDEPENDENT_REEXECUTION_NOT_DONE`；独立重新执行门仍单列，不将数值报告等同于本人现场复算。

**证据性质**：`FULL_LOO_INDEPENDENT_ORACLE.py` 与 `AMOUNT_A_BOUNDARY_ORACLE.py` 没有 import 被测生产内核，属于可复算候选，但结果输入由开发侧提取，仍需抽样源级独立复核；测试 fixture 不可作为 2026-10-09 生产实证。`ACTUAL_BROWSER_QA_EXCERPTS.json` 自身明确标示“手工转录的 DOM 摘录而非完整快照”，因此截图/摘录只支持特定场景的工程观察，不足以签 FP13 全量浏览器 PASS。

## 2. R3 按包独立裁决

| 范围 | 本轮提交支持的结果 | 本次外部裁决 | 不可扩大声称的内容 |
|---|---|---|---|
| P0-ALG：D0/D2/Rotation | 22,452 项旧 R3 比较、6,021 项结构补强、两个真实 pulse 240 项、五会话案例和 153 字段血缘、325 项质量原因复核 | **PASS_SCOPED / EXTENDED_ALGORITHM_DOMAIN_OPEN** | 不能视为所有 detector、完整历史 episode、从未发布的独立 rank 全面正式通过；325 项不重复计算为新增独立数值 |
| 当前已发布 LOO | 50,214 证券-板块组合、401,544 项；独立脚本使用实际成员集合与剔除自身中位数重算，报告零差异 | **EVIDENCE_STRONG_PASS_CANDIDATE（已发布字段范围）** | 脚本从源行直接读取部分 RPS 与原生状态，仅核当前 operational LOO，不证明未发布的全 LOO rank、递归 episode 或历史 PIT |
| P0-OWNER / 成员 | 400 个板块日期化隔离候选、322 个已映射成员、201 个 overlap；6 个精确 sector-D2 输入门、合同提案和浏览器专项 | **PASS_SCOPED（现有读域） / FORMAL_SECTOR_OWNER_NOT_GRANTED** | `CONFIRMED/WARM/frozen_invalidation` 等未有正式接纳 Producer/Owner，隔离候选不可包装为已发布成熟度/健康度 |
| 27 个成员异常 | 349 原始、322 已映射、27 未映射逐条台账；26 北交所已按既有用户指令暂缓；`SZ.001235` 在既有本地/指定 Bao 查询缺行 | **DISPOSITION_RECORDED / IDENTITY_FULL_CLOSURE_NOT_GRANTED** | 缺数据不证明该股未上市/退市；用户范围调整不等于独立 identity authority；原始成员行不许删除 |
| P0-AMOUNT 跨源表示 | 三日期共 15,981 行；15,632 可比较、349 源不全。可比较中 14,292 直接 binary32、995 十进制相等、345 经整元 HALF_UP→binary32 复现（报告值） | **REPRESENTATION_PASS_SCOPED** | 金额表示路径拟合≠供应商实际内部算法证明、经济统计等价、正式 Amount A 权限通过 |
| 正式 Amount A（H21） | 14 fixture/112 项比较零差异；378 真实候选均 UNKNOWN；21 会话要求仅 9/30 的一个正式历史成员观测日，另 20 日缺失 | **FORMAL_AMOUNT_A_BLOCKED / HISTORICAL_SOURCE_NOT_VERIFIABLE** | 不能拿 10/09 最新成员回填此前 20 日并写为 PIT；fixture 通过不能升格为真实 H21 PASS |
| Cohort / Forward | 15 字段能力定位，新增独立 `validation_cohort_read_contract_r3.py` 校验、合法首次可用禁止后填、14 定点回归；报告合计 135 项测试 | **ENGINEERING_PASS_SCOPED / NO_AUTHORIZED_ENROLLMENT_OWNER** | 没有真实获准的 as-recorded enrollment；API `SOURCE_NOT_PRESENT` 不是“零样本”；不能用 Focus 数量代替 Cohort |
| FEP | 具体模型、grant、revision 的缺失及 fail-closed 路由有证据 | **CAPABILITY_NOT_READY（合规）** | 不能把缺失权限伪修复、让测试模型成为生产预测或用未来结果改写 T0 |
| 六入口/FP13 | 报告 23 个真实 HTTP 场景、1366/1920 双尺寸 DOM、历史日期和故障恢复；代码确有页面/路由定点修改 | **UI_SCOPED_PASS_CANDIDATE / FP13_FULL_NOT_GRANTED** | 摘录是手工转录，未由审计者亲自重演全功能；业务 `SOURCE_INCOMPLETE` 不计有效字段覆盖；浏览器验证发生在隔离端口 |
| 实际生产加载 | JSON 明示 `28765` 未加载 R3 竞争解释；`28767` 为独立 QA 服务；本轮未改正式 Head | **PROD_RESTART_PENDING / PRODUCTION_RUNTIME_NOT_VERIFIED** | 代码已推送或隔离浏览器通过都不代表用户实际服务已运行新版本 |
| 历史 PIT | 88 条分域原始 Owner/成员/身份/生命周期目录及缺首次获取时刻台账 | **INVENTORY_PASS_SCOPED / STRICT_PIT_NOT_VERIFIABLE** | 9/28、9/29、9/30、10/08、10/09 以 10/09 最新成员回算无法证明历史当时可见 |
| Git/Drive | Git 实际有 19 次提交；三份 Drive R3 报告已读取；仓库留有 Delivery/Offline receipt | **GIT_SYNC_VERIFIED；DRIVE_REPORTS_VERIFIED；全部 ZIP 字节级外审待单独完成** | 只据自报 SHA 不签全部归档附件 bytes/CRC 与离线重算通过 |

### 2.1 三项不应再重复修复的内容

1. **原 345 条金额残差的表示层解释**：已提供可执行独立 oracle 及逐项路径；外部字节重算可定向抽样，但不要机械再开“345 条原因不明”的相同任务。仍需独立处理 H21 正式输入及消费者授权。
2. **已发布的 current operational LOO**：已补出完整成员上下文候选证明，不得继续将“LOO 完全未实现”当根因；要区分未发布的 full rank、历史 episode 与已发布的 LOO 替代值。
3. **Focus INVALIDATED 退出及页面常规搜索/分页**：此前修复代码和测试仍在，不应要求全站重写；需做定向复验与生产加载确认。

### 2.2 两处源码级可见、应补充负例的风险（不认定已经发生生产事故）

- `validation_cohort_read_contract_r3.py::read_statistics` 作为纯函数仅检查传入 `owner.get('authorized_read')` 布尔值；它本身不验证授权来源的签名、发行 manifest 或真实 immutable enrollment 对象。现阶段因为没有正式 Owner 而保持 fail-closed 是合理的；**下一阶段生产接线时**必须在调用前经正式 Accepted Head/Grant/Owner SHA 检查，不能让请求 JSON 或内部临时 dict 任意设置 `authorized_read=True` 就成为正式授权。
- 同文件 `REQUIRED` 主要检查字段“存在”，没有对 `publication_id`、`benchmark`、`frozen_signal_version` 的非空与契约身份进行完整语义约束；单测以完整 fixture 为主。正式候选接纳前应补空值、错 benchmark、冲突 revision、错误时区/边界时间、截面重复 T0、重复发布等负例；不能仅凭“字段在 dict 中”认定合法冻结。

## 3. 四类未闭环的本质与现在能不能修

| 缺口 | 根因分类 | 10/12 之前现在可做 | 什么时候可以正式通过 |
|---|---|---|---|
| Amount A 缺 20 个历史成员观测日 | **历史 as-recorded 原始事实缺失 + H21 数据门** | 扫描所有本地归档/旧 ZIP/源日志是否确有当时观测；导出可复核 first-capture SHA/时刻；构建 corrected 运营实验与严格 PIT 两套独立读域，禁止互相提升；修消费者合法入口但不运行未授权正式值 | 仅找回真实原件并核准 21 个成员观测，才能给该历史 H21 as-recorded PASS；若原件永远不存在，应永远标 NOT_VERIFIABLE，并从未来真实日期起正常连续积累，而非无限阻塞非依赖功能 |
| 板块成熟度/健康度 | **正式契约、Producer、真实上游 Owner 与候选接纳未完** | 版本化 `CONFIRMED/WARM/frozen_invalidation`、scenario、due 等 exact extraction 规则；复用已有真实 Native facts 构造隔离候选，做独立 AST/负例与完整分母 QA；仅对真的合法字段准入，缺字段保持 UNKNOWN | 正式合同及授权、合法输入 Owner、episode 前态、数据和 API 逐字段通过后才发布此能力；不由五天新样本是否有涨跌决定 |
| Validation Cohort 入组 | **缺当时独立冻结的合格事件及获准发布** | 校验旧原始 T0 event log 的实际 first-availability，设计真正独立 enrollment publisher、幂等键、准入检查与无前视测试；可以准备“从下一个真实合法 T0 开始”的全量合格信号采集，不必等未来收益成熟 | 某真实 T0 已有授权、真实 signal/入组事件、hash/first-available/revision 全部通过才能正式入组；历史缺首获不可补造；统计成熟另行等待 |
| FEP 生产预测与权限 | **合法模型、模型 revision、grant 与当时输入未具备** | 盘点 FEP 既有正式模型训练产物与已接受能力，不重复建设模型；把模型注册、数据哈希、审核、授权、只读消费界面和负例流程准备好 | 在存在合规冻结模型、首获、数据/版本、真实明确授权以及既定外审门后才启动；不因工程测试通过自动授权 |
| 用户生产服务没加载新代码 | **部署/运行时版本差异** | 已可执行安全正常退出再启动、核对新 PID/模块 source path /业务回归 /Head SHA；如果没有合法停止途径由用户自行正常关闭，Codex 不得 force kill | 新进程实际加载了 R3 新代码，六入口真实 `28765` 验证、同日同 token、原正式 Head 与 PIT 不变；无需等待下一个交易日 |

## 4. 必须明确隔离的时间与权限

- 2026-10-10 是周六；预期下一 A 股交易日为 **2026-10-12（周一）**。尚不存在该日真正 T0 已发行行情、日更 Receipt 或 T+1 结果；DD R2.2 负责实际 10/12 三源 SOURCE_READY→Owner QA→CAS→六 API，新旧日不能混写。
- `CORRECTED_LATEST_MEMBER_RETRO` 可用于受限研究展示，但不自动转成 `PIT_OBSERVED`。原 20 个历史日如果无法找到当时成员原件，未来再交易二十天也不能神奇证明过去的历史首获；未来采集只能改善未来 PIT 合法性。
- `Amount A H21`、`sector D2 readiness`、`Validation Cohort`、`FEP` 是四种不同的能力/来源门，不能互相替代，也不能由一张“全站最终通过”覆盖其各自的审计。

## 5. 本次唯一总状态与下一动作

**唯一完整总状态：`EXTERNAL_ACCEPTANCE_BLOCKED`。**

**允许继承：** 前述已提交当前日运营数据范围的数值/页面工程证据，保留 `PASS_SCOPED` 或 `EVIDENCE_READY_FOR_EXTERNAL_RERUN`，不重跑未变的全部旧历史。**不允许继承：** 正式 Amount A、板块 D2 成熟度 Owner、独立 Cohort、FEP 权限、生产加载、严格历史 PIT、FP13/FP14 完整签发。

直接执行同轮签发的下一张《V4 R4 当前可推进定点修复任务卡》；以“补历史原件/精确门、版本化合法输入、上线前负测、安全运行时验证”为主，不展开 Windows 运维、重写前端、量化预测/自动交易，不等 10/12 才开始。

### 关键源链接

- [GitHub 冻结提交](https://github.com/NanOns/a-share-market-structure-research/commit/6b6d5cbd2b115335918aeeafcec9ae5a46f9eb99)
- [R3 证据目录](https://github.com/NanOns/a-share-market-structure-research/tree/codex/v4-fp14-r2-repair/docs/evidence/v4_immediate_r3_20261010)
- [Drive R3 深度推进报告](https://drive.google.com/file/d/1RDc0CDk7dBHZjN1M0_4A8GlB4hV0y8hE/view)
- [Drive R3 续做报告](https://drive.google.com/file/d/1c_DhFhtPLTV95FUJny_c9QWdpp1J0knc/view)
- [Drive R3 初始执行报告](https://drive.google.com/file/d/1XcXgBVSzjS1oqxVKX9jSEYC9lMbGT3Aa/view)
- [Drive R3 原任务合同](https://drive.google.com/file/d/1I5e09hhzKhmSwBMxrAFCeV9wi9W_RD5M/view)

> 审计不可替代独立执行证据的限制：独立数值回放、压缩包的 CRC/每项 SHA、用户本机 28765 真浏览器现场和正式数据 Head 的本机原始字节，当前未在审计环境亲自重验。上述结论因此有意保持分域、范围化，不把 Codex 自报结果包装成完整外审 PASS。
