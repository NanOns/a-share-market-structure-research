# R3 任务卡逐项完成情况核对

核对日期：2026-10-10。合同：V4-IMMEDIATE-R3-20261010。依据：用户提供的 R3 任务卡及本目录原始、09_CONTINUATION 追加证据。核对基线代码：2733c51cdb73d5f11fbd373986b03a25930a87dd；核对时远端同 SHA、工作树干净。本文件是独立的任务覆盖审计，不替代任何正式 Owner 接纳或外部验收。

总判定：PARTIAL_COMPLETE。已完成的数值核查可分别维持 PASS_SCOPED；不能据此宣布 ENGINEERING_SCOPE_COMPLETE。未完成工程、缺源、权限、用户暂缓、未来日期及外部复核分别列示。

## 逐项对照

|任务卡要求|实际完成及证据（相对本目录）|判定与剩余工作|
|---|---|---|
|§0 前置合同、基线及只读边界|STAGE_LEDGER.json、09_CONTINUATION/STAGE_CONTRACT.json；未改变 TDX 输入及保护 Head|已记录；旧验收证据仅作为绑定基线，不算本轮重验|
|§1 六个独立验收维度|01_SCOPE_AND_AUTHORITY_MATRIX.json 已区分工程、历史 PIT、未来结果|部分完成；矩阵仍有通用引用，未做到每个字段六维逐项完整核对|
|§1.3 缺失字段完整追踪表|合同绑定、缺口 JSON、剩余清单分散存在|部分完成；需补齐逐字段 producer/版本/精确 Owner/首次可用/window/unit/null/BFF/UI/SHA/next_action，不能以通用占位替代|
|§2 D0 原始公式及分类独立复算|02_P0_ALG：45只证券、223个 D0 和223个 D2 日期行，原 oracle 22,452项比较零差异；09_CONTINUATION/UPSTREAM_ORACLE_RESULT.json：6,021项零差异|数值及未知窗口范围完成；未证明全部上游质量原因、每个 detector 全链；RPS 既有证明为绑定复用|
|§2 D2 状态、前态、计数器、失效优先级|02_P0_ALG/P0_ALG_ORACLE_RESULT.json，实际五个交易日递归及具名反例|范围化完成；真实再入场未观察到，不能用 fixture 代替|
|§2 三个实际多日案例与竞争解释|223行真实轨迹存在；P0_ALG_TRANSITION_CASES.md 只有总体说明和反例列表|未全部完成；需写出三个具名多日案例、事实/前态/计数器/下一状态及竞争解释|
|§2 Rotation 首 pulse、冻结篮子及价格|09_CONTINUATION/PULSE_SOURCE_ORACLE_RESULT.json：两个真实 pulse，240项零差异；原 oracle 含递归|范围化完成；有限窗口重置与 latest-member corrected replay 已标明，不是历史 as-recorded 证明|
|§2 当前 LOO 独立复算|09_CONTINUATION/FULL_LOO_ORACLE_RESULT.json：50,214组合、401,544项比较零差异，445个未知上下文|当前已发布 Owner 的剔除自身中位数/相对状态完成；全 LOO 截面排名和历史递归 episode 不在该 Owner，独立域仍缺源|
|§2 字段到公式及输入 lineage|P0_ALG_ALGORITHM_INPUT_LINEAGE.json、各 oracle 输入和 source hash|部分完成；需统一补齐字段级映射及更新旧报告中已被追加证据覆盖的 OPEN 描述|
|§3 349 raw/322 mapped/27 unmapped 守恒及逐行原因|03_P0_OWNER 的成员处置 CSV、合同绑定；09_CONTINUATION/BSE_DEFERRED_SCOPE.json|处置记录完成，身份映射未全部闭环；保留 raw，不扩池|
|§3 北交所成员身份|27个缺口中26个北交所成员|按用户指令暂缓；需要额外公开网络求证时本阶段略过，不再作为本地工程阻塞|
|§3 SZ.001235 身份|SZ001235_LOCAL_DATA_DISPOSITION.json、SZ001235_BAOSTOCK_DIAGNOSTIC.json：冻结 TDX 包/身份池无记录，baostock 两次查询成功但空结果|当前两类数据源缺源已查明；SOURCE_NOT_PRESENT，身份未解决，不能推定未上市|
|§3 板块正式 D2/maturity/health Owner|SECTOR_D2_EXACT_CONTRACT_GAPS.json；400行日期化 readiness 隔离候选|未完成正式 Owner；候选不可发布。需正式字段合同/extraction/entry及接纳，不可把 STOCK adapter 改名冒充|
|§3 why-now/risk/H层竞争解释、观察池语义|现有 UNKNOWN/source-gap 说明及 stock qualification 检查|部分完成；正式来源及条件性 H 层两种竞争解释未交付完整核对|
|§3 timeline、Home变化、全量筛选/排序/返回状态|已有历史切换、成员分页及若干 API/DOM 检查|部分完成；完整 timeline 重叠、变化对象分解、筛选排序及返回状态组合仍需补验|
|§4 三日期原始金额、单位/价格基准/身份比对|04_P0_AMOUNT/P0_AMOUNT_SOURCE_COMPARISON.json：15,981条，15,632可比，349无 Bao；无新增容差或金额权威切换|原始数据比对完成；缺源单列|
|§4 345条金额残差|09_CONTINUATION/AMOUNT_REPRESENTATION_RESULT.json：345条全部由按元 HALF_UP 后 binary32 精确复现；全部15,632可比记录有精确表示路径|表示差异闭环；未证明供应商内部算法或经济等价，不能等同正式 Amount A 通过|
|§4 stock/sector/market Amount A 公式、窗口及绑定链|已有部分独立公式及原始权威比较|未完成综合正式审计；需单独完成各层 source/formula/window/null/authority/BFF/UI 绑定及验收，AMOUNT_A 正式域保持 OPEN|
|§5 15项 Cohort/FEP 能力盘点|05_P1_COHORT/P1_COHORT_CAPABILITY_INVENTORY.json|部分完成；各字段仍重复列同一组 producer，需精确逐字段 Owner/能力映射，不能将全部 Forward 能力笼统判缺失|
|§5 冻结身份、去重、首次可用及只读边界|validation_cohort_read_contract_r3.py V2；14项针对性测试通过；晚于 T0 首次可用不可回填、缺 Owner 数量未知|纯读取契约范围完成；尚未接入实际 Cohort 统计 BFF/API/UI|
|§5 T+1/3/5、删失、停牌退市、MFE/MAE/benchmark 与分母隔离|交易日调度及既有 Forward/settlement 回归有证据；原组合测试73项通过，新增后针对性14项通过|部分完成；不能将两批测试相加冒称新全套验收；完整 Cohort 成熟结果/基准/分母链仍需补齐|
|§5 真实 enrollment、AS_RECORDED 与 FEP 授权|P1_FEP_NOT_READY_CONTRACT.md；缺合法历史入组、model/grant|缺源/权限未完成；不能从 corrected 行情伪造。允许继续工程实现，不能启用预测|
|§6 六入口、双分辨率实际浏览器|06_P1_PRODUCT_QA：42个 API 路由、六种图表合同、23条真实 DOM 记录；1366×768及1920×1080|范围化完成；不等于每入口全部交互组合或完整视觉验收|
|§6 强达301628失效退出、旧日期价格、322成员守恒|API_UI_NUMERIC_SAMPLES.json、API_FIELD_CONTRACT_AUDIT.json、BROWSER_DOM_RECORDS.json|已覆盖相应断言；无真实再入场/Shadow 就不作成功声明|
|§6 搜索/点击/筛选/排序/分页/返回/刷新/切日及每入口源值对照|已有搜索、详情、分页、刷新/切日和数值样本|部分完成；完整组合矩阵和每入口 source/unit/basis/context 数值绑定未全部证明|
|§6 stale409、未来日期、单路由故障及慢加载恢复|实际 API 负例及隔离代理 DOM 记录，单路由 indices503|范围化完成；任务指定 breadth503 的本轮覆盖不能由 indices503替代，需补验或明确引用合格旧证据|
|§6 生产服务及独立 FP13/FP14 复核|隔离 QA 服务验证，未重启用户28765；离线复核包可重跑|生产加载最新代码未确认，PROD_RESTART_PENDING；外部复核未完成|
|§7 PIT 原件/版本/首次可用/日志/缺失日期盘点|07_PIT_INVENTORY：五日期88个 Owner 记录及未来采集缺口|范围化盘点完成；首次可用未知，完整原件/ingest日志逐类映射仍不足，不构成严格历史 PIT 通过|
|未来交易日及成熟结果|当前 T0=2026-10-09，未来实际交易日尚未发生|WAIT_REAL_DAY；不可伪造，不阻塞已授权当前工程|

## 交付物与门控核对

|门控|本轮判定|
|---|---|
|G01 前置依据|已记录，需保留旧验收与本轮重验的区别|
|G02 ALG|PASS_SCOPED；案例/lineage/未发布独立域仍开放|
|G03 OWNER|PARTIAL；北交所用户暂缓，正式板块 Owner 及部分产品语义未完成|
|G04 AMOUNT|表示差异 PASS_SCOPED；正式 Amount A OPEN|
|G05 COHORT|契约测试 PASS_SCOPED；能力映射/API/UI/成熟链未全部完成，FEP 不可激活|
|G06 PIT|INVENTORY_SCOPED；严格历史证据未通过|
|G07 PRODUCT|QA_SCOPED；完整矩阵及生产加载待完成|
|G08 保护 Head|已核查保持不变，未做权威/池/阈值切换|
|G09 Git|核对基线本地与远端 SHA 相同；本核对报告另行提交推送|
|G10 Drive|既有两批报告/压缩包已实际下载，字节数及 SHA 相符；09_CONTINUATION/DRIVE_RECEIPT.json 是最新收据。本核对报告不冒称已归档 Drive|
|G11 外部复核|证据包准备完成；尚无独立复核结论，不能自签通过|

任务卡要求的以下具名交付物尚未按该结构交付：P0_OWNER_BROWSER_QA.md、P1_FORWARD_FREEZE_AND_MATURITY_TESTS.json、P1_FORWARD_API_UI_QA.md、P1_PRODUCT_FP_REGRESSION_MATRIX.json、P1_PRODUCT_REAL_BROWSER_QA.md、P1_PRODUCT_NEGATIVE_TESTS.json、09_EVIDENCE_MANIFEST.json、10_DRIVE_READBACK_RECEIPT.json。已有部分同义文件，缺文件名本身不等于能力失败；但字段覆盖、场景覆盖及统一索引也尚有上述实质缺口，不能只重命名即判完成。

## 应继续执行的工程闭环

1. 补齐逐字段六维矩阵及精确 producer→Owner→BFF→UI lineage，统一更新原报告和追加证据的最新判定。
2. 补齐三个真实多日算法案例及竞争解释；逐项处理当前实际算法域尚未覆盖的质量/状态证据。
3. 完成正式 Amount A 独立审计；345条表示残差不再计为未解释金额差异。
4. 按确切合同缺口完善板块 Owner 提案/隔离候选及可执行 adapter；正式接纳另列，26个北交所暂缓不扩池。
5. 完成 Cohort 逐字段能力映射、合法冻结数据的只读 API/UI 与成熟链测试；真实历史入组/模型/权限不伪造。
6. 完成产品交互/数值/负例矩阵、Owner 专项浏览器证据、统一交付索引及生产加载状态确认。

以上工程缺口没有因“等待权限”而整体停止的理由。真正需要外部事实、正式接纳、未来日期或独立复核的事项维持明确边界，分别追踪。
