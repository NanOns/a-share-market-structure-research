# State 可信审查边界

旧 state_publisher_bridge_v1.py 完全保留，其合成成功通道不升级为正式批准。新 state_trusted_review_candidate_v1.review_candidate 只进入独立 resolver，不接受 caller 传入 trust anchor/服务/签发密钥；部署的 accepted review service 为缺失，故 NOT_ADMITTED、UNTRUSTED_REVIEW_CANDIDATE，bridge_executed=false，STATE_SOURCE_ADMITTED=false，formal_cohort_enabled=false。

普通工作区 reviewer_role/decision、伪造 Grant、时间、revision、旧日 Member、缺 Episode、Focus Top-K、错误 benchmark、伪造 Head 均不能打开入口，实际结果及原件绑定见 A_AUTHORITY_NEGATIVE_ORACLE.json。签名运输合同的正反例额外验证 issuer/scope/有效期/撤销/原件/Head 绑定，但仅为隔离 Identity 合成协议测试，不能称为已部署可信 State adapter。

State/Membership/Model/Episode/Benchmark 真源要求与缺口见 STATE_REAL_SOURCE_REQUIREMENTS.json。将来仅在独立服务部署和接受后，才允许服务解析出的绑定进入 Bridge；本轮不能演示真实 accepted State Review 的成功通道，此项明确待真实源和独立验收。
