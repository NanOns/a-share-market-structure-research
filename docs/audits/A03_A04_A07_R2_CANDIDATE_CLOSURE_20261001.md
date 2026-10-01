# A03 / A04 / A07 本轮候选工程与真实观测收口

基线 `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`。三包由最高调度卡授权并行执行；Data Head 保持 2026-09-30，Stage Head 保持 V4_00_TO_V4_10_ACCEPTED。所有新产物均是独立外部复审候选，不构成新外部接受，不开放 Production / Shadow / Focus / global mandatory adoption。

## A03：Forward PIT observation ledger

新增 `forward_pit_ledger_r2.py`、版本合同与每日命令。真实读取已接受 9/30 的 RAW_DAILY、ADJUSTED_DAILY、IDENTITY_UNIVERSE、TRADING_STATUS、ISST，验证原字节/日期/合同后形成独立 observation publication。实际观测在 10/1，因此 first_available_at 为实际收到时间，lineage 是 RECONSTRUCTED_CORRECTED；不倒填 9/30 知识时点，不共享 DM01 publication identity。

已实现全部八类 detector、同日 revision 不可变追加、capture ID 幂等重试、source binding 严格重读、latest projection 独立重建、持久 publication 后崩溃恢复、partial source 失败显式保留。相同 source revision 的再观测保留首次实际可用时间。没有当前 accepted calendar 能证明的后续已完成 session，因此真实未来积累是 PARTIAL，工程状态为 `CANDIDATE_READY_FOR_EXTERNAL_REAUDIT`，不等待未来交易日。

每日命令：`E:/python/python.exe scripts/run_a03_forward_pit_daily_r2.py --capture-envelope <actual-receipt-envelope.json>`。恢复：同命令加 `--recover`。命令交由真实 source capture 完成后调用；未擅自安装操作系统定时任务。没有给 V4-05/V4-08/Forward 新 consumer 权限。

## A04：Amount A 严格 authority 候选

新增 `amount_a_authority_r2.py` 与 `AMOUNT_A_FORMAL_AUTHORITY_CANDIDATE_V1`，明确 CNY 元/万元/亿元换算，拒绝 shares 或未声明 native unit。20-session denominator 使用合法 master calendar 精确前 20 session，不以 20 rows 代替；H21 固定共同成员集、实际成交/有明确 dated suspension 的零值、缺口、新股 warmup、成员变化、coverage 分子/分母以及 concentration universe/timestamp/weighting 均显式记录。

全仓 consumer inventory 逐文件绑定生产者、DB/cache、UI/API、合同及消费者。旧算法的 5 成员、0.80 coverage 是既有实现参数，本轮不把它们自动升级为 authority。未获权威 threshold 时 formal Amount A 保持 NULL，候选诊断算术与 formal 值分别输出；V4-11 Amount A branch 继续 disabled，没有注册 accepted owner。

真实证明直接从已绑定官方 TDX ZIP 的 32-byte 原始 day 记录独立 struct 解码，选取 57 个证券、9 组行业/板块及新股/停牌边界，覆盖 110 个实际缺失金额 cell。再次用独立 Fraction 算术计算 numerator、prior20 denominator 和 ratio，与候选结果核对通过；目标日金额还与 accepted RAW_DAILY 核对。金额来源不是旧 Amount A producer 自己的输出。

仅 9/30 的 PIT membership 已接受，前 20 session 的历史 PIT membership 尚不能证明。因此真实算术中的固定当前 membership 明确标记 RECONSTRUCTED_CURRENT_FIXED_SNAPSHOT，不冒充历史 PIT。formal authority 当前是 BLOCKED，工程候选已可复审；不阻塞 V4-11。

一次初始 source capture 的解释性 raw_byte_offset 错用了选中记录的序号。本轮保留原始初次产物并新增 disposition，最终 source artifact 移除该错误元数据。原始金额值未改变，最终证明只引用新版本。

## A07：历史 adjusted-price 知识 lineage

新增 `adjusted_price_lineage_r2.py` 与 versioned lineage/capture 合同。区分 AS_RECORDED、RECONSTRUCTED_CORRECTED、CURRENT_RECOMPUTED；只有 first_available_at、source_revision、knowledge_time、immutable source bytes 和严格核对的 immutable capture receipt 全部具备，并且 knowledge time 不早于实际可用时间，才允许声称已知该 source version。这个 source-version 判断不赋予任何 adjusted-price consumer 权限。

从只读 `D:/new_tdx/T0002/hq_cache/gbbq` 实际捕获 5,608,604 bytes，SHA256 `7bdd146347da1ac6998ddac9e9117feac555bdef086e9451ea416e6c8a7a2292`，实际 observed/received 时间在 immutable receipt 中。source bytes 写到仓库独立目录，TDX 根没有写入。旧 accepted GBBQ、BaoStock supplemental factor、历史本地 adjusted artifact、receipt 与 Git history 均列入 inventory。真实 GBBQ cash dividend、split/bonus、rights issue 样本绑定旧来源；参考价格 100 仅是明确标注的算术 fixture。

pre-capture 历史 AS_RECORDED capability 永久 BLOCKED；今天可查询历史日期不能改变该结论。Go-forward 捕获命令已交付：`scripts/capture_a07_adjustment_source_r2.py --source <actual-source> --source-kind GBBQ --source-identity <identity>`。同日新 revision 追加新源/receipt，不覆盖旧源；未来自然积累不阻塞其他工作。V4-05 Replay / Forward outcome / support-retention 的 price-basis 权限要求显式列入 consumer inventory，V4-12 本轮没有执行。

## 验证与外部复审边界

23 项初次 targeted 测试通过并保存 JUnit，包括工程 detector、currency/session/coverage/concentration、late source、revision/duplicate/crash recovery、真实 accepted baseline、原始 ZIP 独立算术和 GBBQ 历史知识 fail-closed 重读。后续测试补充同日 GBBQ revision 与完整 durable inventory/handoff bindings；最终完整测试及 clean checkout 由 root 批次 seal 记录，本文不以已有测试代替外部接受。

少量旧代码/receipt 在工作区为 CRLF、Git 中为 LF。最终 inventory 以独立原字节 archive 绑定真实观测，不改旧源，不改旧 hash。LFS 原始二进制保持原 SHA。三个最终 `*_R2_CANDIDATE_EXTERNAL_REAUDIT_HANDOFF_R1.json` 绑定版本合同、runtime、真实候选证明、当前 Head 和复审限制，统一提交后 STOP。
