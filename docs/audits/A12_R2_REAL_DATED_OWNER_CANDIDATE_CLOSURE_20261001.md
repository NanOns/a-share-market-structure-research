# A12 R2 候选阶段交付（外部接受待定）

阶段合同：WP-A12-R2-REAL-DATED-STATUS-ST-AUTHORITY。A10 基础设施接受已正式登记；当前 owner registry 仍为空。

唯一选择 Path B：历史 BaoStock 字段作为 reconstructed provider authority 的 amendment candidate；TDX 实际 bar 优先。所有 source observation 时间保留，禁止 AS_RECORDED 回填。观察日常流的候选合同只覆盖实际捕获的 9/28 与 9/30，不授权未捕获日期。

全历史 4,035,729 行：ACTUAL_TRADED 4,026,611、SUSPENDED 9,118、DATA_GAP 0、UNKNOWN 0；ST=0 3,913,800、ST=1 121,929、UNKNOWN 0。4 个 provider=0/TDX 实际 bar 冲突均保留本地实际。既有 9/28 原始捕获与原生 TDX zip 独立证明 12 个停牌缺 bar，均非 DATA_GAP；已有 9/30 provider=1 与冻结于 9/28 的本地输入构成真实捕获滞后缺口样本，不能称历史内部缺 bar；没有为 DM01 重复联网。

原价格 runtime 全历史重跑，business fields 与 accepted R6 全行一致；周/月 RAW/QFQ 逐列一致，另从 source bytes 重算每个 period 的状态计数。V4-03/04/05/07/08/09 使用原算法，12 份 entrypoint 的 AST 可逆路径替换证明与 R1 一致。统计、剩余 UNKNOWN 原因和全量业务 diff 见 A12_R2_PRICE_AND_REMAINING_QUALITY_PROOF_R1.json 与 A12_R2_DOWNSTREAM_CASCADE_AND_FULL_BUSINESS_DIFF_R1.json。Core Profile 的业务质量修复完成尚未声明。

ST 正样本代码变更的限制：唯一 accepted 数字 alias 共 786 行均为非 ST。真实负边界已验证，正样本不存在于本轮 required scope。G01 的历史内部缺口正样本限制与 G02 的 ST 代码变更正样本限制均保留 PENDING_INDEPENDENT_EXTERNAL_AUDIT，必须由外部审查明确处置；没有伪造样本或自行豁免。IPO 延期误标 suspension 的来源语义问题作为独立 OPEN audit 记录在 R5，所有旧 ledger 与 accepted heads 保持字节不变。

最终仅为 A12_R2_REAL_DATED_OWNER_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT。Clean detached 结果与提交绑定见阶段 closure。G17 外部独立接受待定，DM01 final all-nine、owner promotion、production、shadow、focus 均未授权。下一阶段需独立审计，然后另发 promotion/amendment card。

真实 V4-04 replay：{"COMPLETE": 4981, "PARTIAL_UNKNOWN": 241}；V4-05：{"PARTIAL_UNKNOWN": 5222}。价格已知 4035652 行，UNKNOWN 77 行；UNKNOWN 原因逐项保留。
