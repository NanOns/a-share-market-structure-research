# DM01 A01-R3 连续候选阶段交付｜2026-10-01

最终交付状态：`READY_FOR_EXTERNAL_REAUDIT`。本工作包 Phase A 正式化验证 PASS，Phase B 三日真实全九组件候选完成；DM01 外部验收仍 PENDING。

唯一 formal acceptance authority 是 `docs/evidence/source_authority/V4_A10_A12_R3_AND_A13_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md`，exact SHA-256 `a23789d9de4eb48831125cbb9165964a8dacacb33e9dd30dba0f3bfced681d3a`，10868 bytes，audited HEAD `d85f815097a09ca2dceda00d0e29d6ff4fe331d4`。两份任务卡仅定义执行范围。原 Registry R2、Head R2、R3 config 与错误 task-as-authority disposition 原样保留；新增 R4 config、Registry R3、Head R3，四项历史/daily authority 均绑定真实独立验收。

Phase A 在真实仓库读取六个日期/字段 gate，9/28、9/30 PASS，9/29 SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE。历史显式 revision 覆盖起点、2024 ST撤销边界、2025代码变更边界及9/24终点，全文 row oracle exact，无 AS_RECORDED/first availability。全部条件通过后直接进入 Phase B，中间无人为确认停顿。

Accepted calendar resolver 从 Data Head 9/24 解析连续 completed sessions 9/28、9/29、9/30。9/29真实 BaoStock 单次全市场 bounded query 返回5223行，保存raw、receipt、provider日期、实际时间、schema/revision和accepted identity/calendar bindings。同一已验收 producer/registry unchanged，新实例自动验证PASS。抓取晚于目标日，所有候选仅 RECONSTRUCTED_CORRECTED，AS_RECORDED=false、first_available_at_target_proven=false。

TDX本地目录未更新到目标日，官网已滚到10/1。保留页面与初次非ZIP响应拒绝证据，公开下载静态cookie校验后取得真实官方ZIP；严格选取目标日期，独立逐条二进制验证，future rows consumed=0。9/28复用既有externally accepted官方包，9/29/9/30用新官方包真实目标行。绝不拿BaoStock OHLC或adjustment作canonical authority，不插值/forward fill。BaoStock adjustment为optional supplemental，可用性独立记录；QFQ仅本地已接受GBBQ与原native adjustment kernel，unsupported逐证券 fail closed。

九组件每日期完整执行，独立postcheck全部PASS：9/28身份5222/真实日线5210，9/29身份5223/日线5211，9/30身份5224/日线5213；缺少日线的证券分别12/12/11，均为目标日provider停牌。各日 FULL_PASS/DEGRADED_PASS 明确保留unknown理由，不把降级证券补成正常。候选parent精确链为9/24 accepted→9/28 candidate→9/29 candidate→9/30 candidate，逐日记载九组件、source instance、identity/calendar、parent digest与创建时间。

候选父状态使用明确 CANDIDATE_PARENT namespace，并递归验证全九组件marker、postcheck及固定accepted anchor。内部旧kernel日期字段只是兼容视图，不写新accepted head。开放period状态由accepted weekly/monthly真实聚合投影；已闭历史通过原archive exact bindings保留，不复制或回放整个历史。PRICE_LIMIT previous close由最后真实accepted raw close及其后native corporate actions得出，无合成0价格。

真实输入的晚期PRICE_LIMIT失效探针完成7项后拒绝发布marker，未产生部分可消费候选，dispatcher first-failure停止后续session。相同冻结source+parent的重复执行 logical digest一致，新的source revision生成新candidate，旧三日候选不可覆盖；强化 fresh namespace/genuine dated recapture 证据由独立determinism receipt记录。

Data Head仍2026-09-24；Data/Stage及所有既有业务Accepted Heads exact保持，TDX目录写入次数0，production/shadow/focus均false。A13为独立P1证据治理，DM01只消费structured dated field instances。Cross-stage Registry R8记录A12 authority scope accepted、DM01 ready且未accepted；R9追加A13 formal disposition。

代码与真实源/候选/evidence经过 clean detached regression（隔离PostgreSQL、无config/.env、global NoSymbol），实际tested commit和数量记录于 CLEAN_CHECKOUT_R1。提交push只代表阶段交付，不代表DM01 external acceptance或新的gated stage准入。下一阶段仅独立外部复审。

Git 字节耐久复核发现既有 GO-FORWARD PIT Head 的本地 CRLF 原字节与 Git LF 表示差异。业务 Head 未改写；将原字节冻结至独立 accepted_metadata_bytes 输入，新增 R3_2 / 3.1.0 契约和独立运行时，使用同一真实源重新完成连续九组件链。最终候选、postcheck、atomicity、determinism、handoff 采用 R2 receipt；原 R3 契约、运行时、三日 R1 候选及所有 R1 proof 原样保留。该问题单独登记为 DM01_R3_ACCEPTED_METADATA_GIT_REPRESENTATION，engineering PASS 不视为外部验收。
