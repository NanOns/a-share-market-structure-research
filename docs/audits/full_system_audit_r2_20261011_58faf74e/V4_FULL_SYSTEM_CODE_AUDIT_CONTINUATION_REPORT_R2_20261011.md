# 全系统代码审计续审 R2 · 2026-10-11

结论：**AUDIT_INCOMPLETE**。按用户明确指定的 `58faf74e` 版本 `NEXT_REPAIR_EXECUTION_BATCHES.md` 执行 B1–B4 补证。当前分支与远端原基线一致，未发现额外文档提交；本 R2 更新续审结论和剩余清单，R1 历史证据不覆盖。业务源码仍为原基线；新增内容均为审计证据。

## 批次结果

|批次|本轮新增证据|验收与边界|
|---|---|---|
|B1|§87A 的 29 个族展开为 157 个要求行、156 个不同明确名字；9 个 schema 维度拆出 1,413 条范围内原子要求。保留 47 个 Core machine output 的输入/AST/单位/质量登记，提取 FEP 初始 DDL 33 表、286 列|PARTIAL。斜杠展开以明确上下文为依据，delta 不臆造 rps20_delta1。controls、Focus 内部、profile 组件族仍未展开；词命中只定位，不判语义通过。全系统原子需求/全版本字段分母尚无合法终值，不给覆盖率|
|B2|独立向量 Feistel 解码 193,597 条 GBBQ，并逐条与现有标量解码核对全量明文字节 SHA；12,451 个行情 ZIP 条目 CRC 通过；最新 5,224 股票原生 OHLC/金额/量全历史核对；五个旧日 ret1/3/5/20 与 RPS5/20 独立核对|104,069 个收益及窗口、52,234 个 RPS 比较均通过。原生值 12,977,772 比较通过；复权可用性 2,162,962 次一致。8,636,512 个可用 QFQ OHLC 中 **16 个不符**，登记 FA-016。源为 later reconstructed，不能推出历史 first-available/PIT|
|B2 小集合/状态|n=1/2/6、重叠板块及 FIRST 类别/ANY 多事件聚合静态反例；原版本状态向量、expiry、reentry、非法 prior 和缺确认、持久化原测试重验|15 个静态检查通过、1 个空全板块边界异常，登记 FA-017。状态/持久化测试属于声明的工程事实，不代替真实 D0/D1/D2 Owner 或历史标签生成|
|B3|原 fullscope 文件按 SHA 补入隔离视图；numpy 2.2.6、scipy 1.16.2、sklearn 1.7.2、threadpoolctl 3.6.0、joblib 1.5.2 按已有协议在 G 目标安装；B0 用确切 90cef3e 原 producer 字节复验；历史 bridge 用 7986acdb Head 原件及版本化档案；官方 test DSN 指向身份验证通过的 G 隔离集群，原守卫启用|**151 个不同测试通过**。不修改源码凑测试。先前缺输入/错误 profile 的失败轨迹保留；M14 9/11 原 probe 本地及本地 Git 历史缺失，未制造原件。24 个 named-symbol 命中逐用途分类，原 FAIL 仍保留|
|B4 独立 Amount A|10/09 Bao 原件 5,224 行分母；5,210 可比 Native 行金额与量；5,201 个 OBSERVED 股票 amount_ratio20 精确 prior20 窗口；实际 9/30 Amount observation 全字段源绑定重建|金额 4,849 DIRECT_BINARY32 + 264 DECIMAL_EXACT + 97 INTEGER_HALF_UP_BINARY32，未见无法解释的可比金额差；5,210 量相等。14 行 Native 当日缺行且 Bao 明示停牌/金额空，单列不当零。股票比率全通过。378 板块均因 H21 缺前20个 PIT 观察日而 UNKNOWN，正式 consumer=false；FA-012 仍独立 OPEN|

## 新确认问题

**FA-016（P2，跨模块复权舍入）**：7 只证券的 16 个历史 OHLC 值在精确半分处少 0.01 元。独立整数/有理数 HALF_UP 和 Decimal40 按事件递推得到同一差异；重跑现有 affine producer 得到原记录。示例 SH.688553 / 2025-04-14 open：raw 15.13，经两次事件应得 `391/40=9.775`，HALF_UP 应为 9.78；系数计算在当前 Decimal 上下文得到 `9.774999999999999999999999997`，记录 9.77。全部事件、系数、原价格、SHA、准确日期和字段保存在 `b2_rounding_counterexamples.json`。差异日期范围 2025-02-12–2025-06-20；本轮五个 session 的收益/RPS 端点未发现差异，不外推其它历史消费者无影响。不能仅提高 Decimal 精度后宣布完成，精确 tie 处理及消费者重放必须独立验收。

**FA-017（P2，候选 LOO 空集合）**：排除目标后成员 frame 全空、market 仍有其它股票时，`recompute_full_current_loo` 在下层报 `CURRENT_REQUIRES_ONE_TRADE_DATE`，未走自身的 `SECTOR_EMPTY_AFTER_EXCLUSION` 结果分支。同一个 singleton 加入无关板块后返回 support=null，作为反例对照。范围是 V3.3 candidate 的合成合法字段输入；没有据此声称当前全板块生产查询发生故障，也没有提升 formal LOO 权限。

**FA-015（审计文档勘误）**：R1 正文/字段公式中的 CLV 应为 `(C-L)/(H-L)`，范围0..1，H=L为UNKNOWN；R1实际独立脚本本来使用正确公式，原数值通过结论仍有效。另订正 Amount A 的实际合同位置及 named-symbol 的用途归因，见 `ERRATA_R2.md`。

## 失败归因与测试范围

B0 原历史绑定 SHA 为 `93c73b...`，当前 producer SHA 为 `921c7c...`，当前文件不能冒充该历史字节。使用确切 Git 原件恢复测试上下文后，4个 positive binding 检查通过，错误 producer/contract 两种反例拒绝；没有重绑 accepted Head。历史发布测试先因错误的当前 stage projection、缺测试源文件失败，补齐确切 profile 后16项通过；再加2个B0反例和2个状态DB测试，共20项通过。依赖/fullscope 7项、状态/LOO/Amount/持久化123项、真实Amount原件1项，去重总151。运行轨迹与最终 JUnit 均可查，不把旧运行里的76个 failed/error 等同76个产品故障，也不宣布全库回归全部通过。

named-symbol 的24命中是：15审计/QA样本、5用户范围证据、1合成向量、2指数身份排除、1实际 source acquisition smoke fallback。最后一项会选择 sh.600000 做有限 probe，属于真实采集路径的显式命中；无证据称其为股票评分特例。政策 FAIL 保留，需具体版本化分类与路径边界审查，不能无边界豁免，也没有证明任意动态 import 全图。

## 运行和权威边界

28765 的 listener 仍为 PID22956；startup attestation Head 为 be2a3d6，当前源为58faf74e，沿用先前已核验12模块，不能把整个进程等同新的 Git Head。三份受保护 Head 的 SHA 与开工记录完全一致。55547 是自身 G 隔离集群，使用官方 test DSN 和目录身份守卫；测试后已停止。未改变 TDX、生产数据库、数据 Head、权限、模型Grant、Focus或DD任务。旧日审计没有生成未来交易日事实。

现行 R4 next-acceptance 和 Amount-A R3 合同用于确定准入边界；本轮用户选择 B 类审计清单，因此没有执行其中业务修复、Windows安装/接管或外部批准动作。测试通过不是 release readiness，也不是下一门批准。

## 剩余与交付

B1 全文规范原子化、完整多版本字段 producer→consumer→UI/quality/permission，B2 全五日其它字段和独立资格/真实DAG/合法 prior 路径、M14历史原件、named-symbol具体治理继续 OPEN。Amount A 正式 H21、Cohort真实首获、FEP成熟OOS与Windows现场批准仍分门登记，不能由本轮数学通过代签。A1/A2/A3原问题保持未修；新增舍入和空集合各有独立最小修复/反例清单。

本轮更新的执行清单为 `NEXT_REPAIR_EXECUTION_BATCHES_R2.md`，统一入口为上级 `FULL_SYSTEM_AUDIT_CURRENT.md`。原R1文件SHA保留在续审ledger；本包SHA在 `EVIDENCE_MANIFEST_R2.json`。提交与push仅交付审计证据，不构成外部接受。
