# 本轮九工作包候选交接

最高调度 authority 为本轮总调度卡；基线为 `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`。十份任务文件原字节保存在 `docs/evidence/next_round_r1/`。实施任务授权只形成工程候选，不构成独立外部验收。

当前交接入口为 `reports/next_round_r1/BATCH_CANDIDATE_HANDOFF_R1.json`，逐工作包 contract、runtime、实际证据和外部限制均有精确绑定。批次结束状态仅为 `CANDIDATE_READY_FOR_EXTERNAL_REAUDIT`。

V4-11 优先完成精确 legacy source/AST 提取、参数与时间角色冻结、D0 候选、受控 D2 工程接口、冻结前交易日事件、同日三次 revision 回放、append-only 数据库存储、重试幂等、consumer identity、事务回滚及独立 source-AST oracle。migration 026 由统一 allocator 分配，历史 migration 未修改。正式 D0 不可直接写 maturity/validity/tracking。

真实 9/30 accepted 数据全市场 5,224 个身份产出一行/股票。已有 accepted Raw/Identity/Status 的 actual-bar/identity 事实按原字节独立核对；尚无目标日已接受的 common/safety/episode detector publication，因此 5,224 个确认值保留 UNKNOWN。11 个停牌身份也保留在覆盖范围内。未知不是不确认，数量不是调参门。真实 D2/prior-state publication 缺失时，事件和硬失效冲突统计明确标记不可评估，未造出 NONE 或确认事件。正向与事件向量使用单独 synthetic engineering namespace，由未修改的已接受 V4-10 reducer 计算，不能视为真实市场或正式 detector 接受。

A02 六日 RPS 与 T-1/T-3 独立重算零差异；下游 Core/Factor/Seed/PREWATCH 完整 amendment 候选与业务差异保留，旧 publication 不改。A05 找回旧 `phase2.prepare` 的确切 valid-member AST，541 个旧 sector 和 3,553 个真实 member 输出零差异，语义仍限 CURRENT_SNAPSHOT。

A03 完成当前真实 forward ledger 与 payload schema/drift 防线，未来自然积累记 PARTIAL。A04 完成原始官方样本及独立 Amount 算术，但 formal 阈值与 H21 历史 membership authority 仍 BLOCKED。A06 三日 15,634 个真实匹配通过独立算术；官方 generation-rounding 文档缺失与 fresh GET 405 记 PARTIAL，tolerance=null、strict-binding=false。A07 冻结当前只读 GBBQ 的真实捕获与修订 lineage，捕获前历史 AS_RECORDED 永久 BLOCKED。Owner Registry 七字段仅 R4 candidate，不 bulk accept、不切 active root。Historical Reader v2 使用每次调用的显式 DI view，保留旧 validator/source/ROOT，历史完整 parity、并发与错误 hash/path 拒绝均验证。

正式 Data Head 保持 `2026-09-30`，Stage Head 保持 `V4_00_TO_V4_10_ACCEPTED`。Amount-A formal branch 关闭；Production、Shadow、Focus、global mandatory adoption 均为 false。未实现 V4-12，未创建正式 V4-11 Accepted Head。旧文件仅 CRLF/Git LF 表示不同的少量 head 原字节另行归档，原路径与 Git 表示分别精确核对，未放宽 identity。

整批 clean regression 记录于 `reports/next_round_r1/BATCH_CLEAN_CHECKOUT_R1.json`。只使用干净 checkout、临时 PostgreSQL 和原字节 source evidence，禁止读取 config/.env；包含 V4-09/V4-10/V4-11、DM01 historical readback、Data Head V2、A10/A12、全部新包和全仓 No-Symbol。仅保留上一轮已授权的单个历史 deselect，没有新增例外。

统一提交并 push 相关代码和 evidence 后 STOP。下一步仅为分组独立外部审计，不自行外部 PASS 或推进后续门禁。
