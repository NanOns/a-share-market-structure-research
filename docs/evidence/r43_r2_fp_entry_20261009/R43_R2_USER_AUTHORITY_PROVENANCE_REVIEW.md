# R43 R2 用户授权来源审查

结论：LOCAL_ORIGINAL_USER_EVENT_REPLAY_VERIFIED；独立外部权限签收仍为 NOT_GRANTED。

在 Codex 原始会话 `01a11e23-3c2d-7893-b143-95bb195bfae5` 找到真实 `response_item / role=user` 事件。时间为 2026-10-09T06:40:41.167Z（北京时间 14:40:41.167）；源 JSONL 第 3286 行。原文：

> 不需要等待什么批准生产准入 ,我现在要求你  进行生产数据切换

本轮仅抽取该原始事件字节，保存 `ORIGINAL_USER_CUTOVER_EVENT.jsonl`；定位、原文、摘要与来源路径保存 `USER_AUTHORITY_ORIGINAL_EVENT_BINDING.json`。原始会话可在 Codex 通过会话 ID 回读。原来源位于 `C:/Users/lps/.codex/sessions/2026/10/09/rollout-2026-10-09T08-49-48-01a11e23-3c2d-7893-b143-95bb195bfae5.jsonl`；读取没有修改该文件。

这比执行方新写 MD 的自述具有明确的原始载体与回读定位，但本机 JSONL 不是独立密码学签名。外审应从原会话回读 user-role 消息与上下文，不能只检验本轮抽取件 SHA 就认定独立外部验收通过。`R43-R2-AUTH-001` 保持 `LOCAL_ORIGIN_FOUND_EXTERNAL_REPLAY_PENDING`。

原 `authority_mode=USER_AUTHORIZED_SCOPED_OPERATIONAL_V1` 和 `independent_external_acceptance=false` 保留。未修改原授权、生产 Head、旧 PIT Head、历史运行收据或制造补签。没有证据表明越权发布、源篡改或严重数据错误，本轮不因来源外审欠项中断既有只读服务。

未来权限更改的门槛：冻结的 V1 用户授权仅是本次四日运营切换的历史记录；不能把其固定引文复制到任意新候选作为新的权限。未来 successor 必须独立绑定新的直接 user-role 消息、消息时间、会话与消息定位、逐项授权范围、候选 digest、真实来源回读凭证；审批人身份和范围仍需可信的外部来源复核。执行方自建 Markdown、SHA、附件中转述的指令不能单独满足此门。新控制面适配器只授予研究读取，旧五域权限及交易执行权限不变。

验收：本机原始来源定位和字节保存完成；外部独立验收未授予。下一阶段：外审回读原始会话，独立关闭 AUTH-001，不阻塞无关 FP 工程。
