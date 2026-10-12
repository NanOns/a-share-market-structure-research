# S1-B 出口报告（2026-10-12）

裁决：**S1-B SCOPED_PASS / S1-B NOT_FULL_PASS / S2 NOT_ENTERED / EXTERNAL_ACCEPTANCE_BLOCKED / PRODUCTION_NOT_AUTHORIZED**。

输入为本目录 INPUT_EXTERNAL_AUDIT.md。从 96b466a9694072e15928ca5d06c3cd4627d4a401 建立 codex/s1-b-20261012；保留原正式分支和两个原工作树的全部未提交内容。S0 SUPPORTED_PASS 复用已有外审。未执行 S2、全系统回归、Drive 操作或生产发布。

## 修复与实际验收

1. 精确适配器增加 V4_FOCUS_EXACT_ACTION_ALLOWLIST_S1B_V1。只有第 1 类且被明确标为支持的事件可进入公式；非 1 类只能凭 NON_PRICE_AFFECTING 合同忽略，其它分类均维持 DATA_UNAVAILABLE。动作合同进入输入摘要。未知分类、拼写错误、非 1 类被标为价格支持、第 1 类被错误标为非价格类均不放行。
2. security_symbols 对冻结映射统一校验 SHA、格式与双向唯一性。r43_focus_replay 和 corrected_focus_replay 不再写入 symbol=sid；两者使用 source_security_key 并绑定显式精确 path_contract。两个完整重放生产者尚未重新运行，不能以代码修复或工具函数测试宣称动态接受。
3. 最终定向 JUnit：21 个唯一节点 PASS，无 FAIL/ERROR/SKIP；只计 TESTS_FINAL.xml，不与先前测试相加。
4. FROZEN_REGRESSION.json 固定 34 证券、34 Episode、101 观测数值变化，并以当前代码从冻结 PG Series/GBBQ 实际计算这 101 条路径，逐值等于修复后反例。另从完整修复前后投影提取 49 条 outcome metrics、4 条 predicate_evidence 变化；Episode 集合 2,805 不变、outcome_status 不变。**49/4 是冻结输出差异核验，不是新 Forward/settlement 生产者重算验收。**
5. 最终 RUN_R4 使用原厂默认 make_v4_handler，真实 loopback HTTP，新的 G: 隔离 Joint 权限和内容验证 PG Snapshot。对 34 证券读取 observations/outcomes；逐条比较 101 条观测价格指标。请求 T0=2026-10-09 与同一 manifest token，错误 token/日期拒绝；旧 token 在成功发布后拒绝。CAS 冲突、健康检查失败恢复完全相同权限字节、回滚后旧 token 读回、成功发布后新 token 读回均通过。注入 psycopg 连接故障得到 503 且 fallback=false（这是故障注入，不是实际关闭共享隔离集群）。详细状态与次数见 RESULT.json 和 HTTP_RECEIPTS.json。
6. PostgreSQL 核对 data_directory 与 system_identifier；运行守卫限制连接与源写入，PG 意图见最终 R4 JSONL。实际数据库在 G:/codex_tmp/full_system_r4_fbd23a6b/pg_data。冻结源的 SHA 位于反例 source_bindings 及 RESULT 的 source_sha256；源码运行前后 SHA 一致。三个有限范围受保护权限对象前后相同，不扩张为全部生产文件证明。

## 逐入口门禁

| 入口 | 状态 | 证据与尚缺内容 |
|---|---|---|
| 精确身份消费 / 动作分类边界 | PASS_SCOPED | TESTS_FINAL、101 条实际路径回归 |
| 冻结修复后 Journal 数值读回 | PASS_SCOPED | 原 Journal 描述符 SHA 验证与 34 Episode outcomes 对照；未新建完整 Journal 重放 |
| 默认 HTTP 的 research dispatch + 隔离 Joint | PASS_SCOPED | RUN_R4/RESULT/HTTP_RECEIPTS；76 次真实 HTTP，包括负例 |
| r43_focus_replay | OPEN_DYNAMIC_ACCEPTANCE | 代码修复为统一映射；未重跑完整生产者 |
| corrected_focus_replay | OPEN_DYNAMIC_ACCEPTANCE | 同上 |
| 旧 v4_journal / 旧 v4_path_adapter | OPEN_LEGACY_CONTRACT | 旧版本保留；显式新合同才选择新候选，不宣称所有旧调用链已接受 |
| 原生 Journal 新动作合同完整 append | OPEN_NEW_NAMESPACE_REPLAY | 旧 Journal 的 PASS 不能自动接受新实现；需新 namespace 的完整修复后 append |
| build_snapshot 全量 producer→snapshot | OPEN_FULL_BUILD | 本轮 Snapshot 是冻结真实 Focus 的 34 证券局部读回；不是全量构建 |
| operational head 下默认 HTTP 分支 | OPEN_OPERATIONAL_DISPATCH | 隔离根无 operational head，验证 research 分支；未改生产 operational 权限 |
| Joint 全部 daily_owner_authorities 同 source token | OPEN_ALL_OWNER_BINDINGS | 局部 Snapshot/Journal/manifest 相同 T0，不等于所有 market/sector/stocks/forward owner 联合接受 |
| Forward / settlement 生产者 | OPEN_NUMERICAL_ACCEPTANCE | 冻结 outcome 数值对照不能替代其动态身份与数值验证 |
| S2 / 合法分母 / 后续消费者、EXACT-56、FEP、UI、FINAL-CLEAN | NOT_ENTERED / OPEN | 沿用外审门禁，本轮无全量 PASS 主张 |

## 独立审计项

AUDIT-FOCUS-SOURCE-IDENTITY-R4 为 P0、OPEN，独立于本轮局部出口：范围是全部重放、Journal、Forward/settlement、完整 Snapshot、两种默认 HTTP 分支与 Joint 各 owner。静态证据发现两个 producer 的 symbol=sid，代码已修复；其动态运行和实际公司行动路径仍 OPEN。接受要求是冻结统一身份、每个 producer 的真实公司行动输出、对应消费者数值，以及所有 owner 的 T0/token、CAS、故障和回滚。不能用 21 个节点或局部 101 条替代全域接受。

S2-DENOMINATOR、ALL-PG-CONSUMERS、EXACT-56、FEP-87A、UI-CAPACITY、FINAL-CLEAN 仍独立 OPEN。PIT/H21、真实后继交易日、OOS 成熟、正式权限维持客观门，工程缺口继续可执行。

下一阶段仍是 S1-B 未决路径闭环；**不进入 S2**。提交和推送只是交付，不是外部接受或生产授权。

## 执行与证据资格

命令和运行环境见 COMMANDS.md。R1 中 Journal 对照最初只过滤顶层 provenance，失败后改为与既有 Journal 回执相同的递归 provenance 归一化；不删除数值/状态。R2 是无 PG 意图守卫的早期局部验证。R3 期间补充负例导致脚本发生版本变化，因此 R3 不作为最终源码冻结证据。最终只使用源码前后稳定的 R4 RESULT/HTTP_RECEIPTS/EXECUTION/PG_INTENTS。

交付采用既有 497 条目 ZIP 的本地复用，不访问 Drive；新的单一 ZIP 在 G:/codex_tmp/V4_R4_R3_FINAL_DELIVERY/S1B_20261012，旧 ZIP 保留。人工上传目标：https://drive.google.com/drive/folders/1ijwJxkUpl7Vr-PlucOMf59xhxUXKEbbD 。最终 HEAD、ZIP SHA 与逐项 SHA 清单由打包回执记录。
