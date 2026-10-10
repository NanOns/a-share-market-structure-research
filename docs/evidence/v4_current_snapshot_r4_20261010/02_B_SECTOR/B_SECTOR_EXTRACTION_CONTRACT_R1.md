# SECTOR D2 extraction 候选 R4 R1

Status: PROPOSAL_NOT_ACCEPTED。对象固定 SECTOR；保留原 research_state.reduce_state 和正式参数，不将STOCK入口改名。来源哈希、T0 cutoff、唯一成员分母、member_set_asof、质量、first_available、window_identity、producer_parameter_set全部必须有源；schema migration仅新增隔离候选，旧Owner和Head不迁移。

CONFIRMED复用版本化 legacy B2 AST，仅其diagnostic可研究；正式valid-member/normal-rank/coverage receipts缺源则UNKNOWN。WARM复用warm AST的SETUP/RECOVERY和q20/dq5_3，Amount A分支要求strict H21。Native dq5与legacy dq5_3不能互换。frozen_invalidation只来自入组时真实contract ID/version/hash冻结的Episode和精确T-1，禁止默认常量。observe_episode按session_index单调、同会话同事件幂等，冲突拒绝、失效当日不可重入。followup_complete要求due_plan、真实到期且settled Owner，右删失不完成。scenario仅正式V4-11/V4-12源；Rotation/B0不作替代。

当前400板块全部有独立SECTOR入口，dq5可单独读取；六字段无Owner，D2 readiness精确缺源。完整入力且合同正式独立接纳后才能接原D2 reducer；本轮候选不发行。正负例、真实源数量守恒见oracle与receipt。
