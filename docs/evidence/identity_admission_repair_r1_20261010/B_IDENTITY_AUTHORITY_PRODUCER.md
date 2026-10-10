# 同日 Identity 候选与主 DD 分类修复

实际 verify_source_gate 的原始提供方日期、数值和 active 覆盖先独立核对。旧身份集合失配单列 dated_identity_authority，提供方正常时返回 WAIT_DATED_IDENTITY_AUTHORITY，DailyJobs 对保存的证据重算也保留此状态。正常同范围仍按原门处理；提供方矛盾/缺行仍拒绝。受保护 last-good Head 不变。

dated_identity_candidate_v1 输入五份原始版本化绑定：roster（含与原始 BaoStock 对应的行情和身份）、TDX、GBBQ 原件、官方时态身份事件、同日 AS_RECORDED 成员。全部需实际目标日及请求/接收/首次可用时钟。未知上市/退市/改代码事实不猜测；缺成员时钟时 first_available 为 null。候选不自行准入，不改变主 DD scope。

真实独立审查服务不存在。默认 admission_candidate 永远 NOT_ADMITTED。IsolatedReviewAuthority 仅为明确合成测试运输合同：固定签发者、签名、能力/范围、有效期、撤销、原件版本/时钟、Head CAS；仅允许 docs/evidence 测试 Head，生产 Head 路径拒绝。CAS 后回读失败恢复原始字节，重试幂等。它不构成生产信任锚。

8 个实际门函数差异样本见 B_IDENTITY_CROSS_DAY_ORACLE.json。合法同日候选、未知新增、退市、改代码、停牌、成员绑定/版本、缺行、矛盾、非法回建、CAS/回滚见定点 JUnit。真实运行中的 28765 未重启，本轮源码不代表生产已加载。

唯一实际新日结论：WAIT_REAL_T0_WITH_IDENTIFIED_BLOCKER。阻断为真实新日来源尚未发生、独立 Identity 审查服务未部署、生产模块加载另需明确授权和独立验收；工程接口已有可重复验证，不列无限等待。
