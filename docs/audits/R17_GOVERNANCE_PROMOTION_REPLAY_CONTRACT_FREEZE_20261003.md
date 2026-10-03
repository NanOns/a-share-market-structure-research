# R17：历史治理修复、V4-13 Engineering Promotion、V4-14 合同冻结

唯一执行基线：`f12315bf8e3142aa44e9068c5895004c35c4e23c`。用户明确授权按 R17A → R17B → R17C 连续执行，并在三个阶段完成后统一提交和推送。五份原始调度/外审文件的精确字节保存在 `docs/evidence/r17/`，最高调度卡为 `V4_NEXT_ROUND_EXECUTION_MASTER_R17_20261003.md`。

## R17A：历史状态与当前 accepted state 分别验证

DM01 promotion-time Stage binding `529c532b…` 解析到不可变的 V4-00～V4-10 原始归档；V4-10 的 `f7607601…` 解析到 V4-00～V4-09 归档；V4-12 R10/R11/R12 的 `80c58f2f…` 解析到 V4-00～V4-11 归档。R15 的 `b0e1c240…` 也显式登记，供后续 promotion 后的历史合同路由验证。

注册表以原 namespace、SHA、字节数、语义阶段范围、精确归档路径和 Git 来源提交约束读回。缺失归档、错误 SHA/字节数、正确字节但错误阶段范围、当前 moving head 冒充归档、历史 Head 改绑当前 Stage SHA 均失败。没有扫描目录寻找方便的匹配文件，也没有修改历史 Accepted Head 或冻结合同中的 SHA。

已替换“当前仓库仍必须停留旧阶段”的断言：先验证精确历史归档及 Git 中的历史对象不存在性，再独立验证当前 accepted 状态和权限。原有计算 oracle、价格/坐标、计数器和负例保留。原 22 个失败的测试身份逐项保存在 `reports/r17a/separate_audit_item_closure.json`，没有 deselect 或删除测试。

原 producer/test 源码的历史字节另行归档，并仍与原 Git 提交验证；维护后的治理读器不冒称旧源码 byte-identical。V4-02 更早的静态 Head 的 CRLF 验收字节与 Git LF 表示差异作为独立审计项处理：保存精确验收字节，证明其与固定 Git blob 的换行表示关系，并拒绝当前正文变化。原 Head 文件未改写。

R17A clean detached：828 passed，0 failed / skipped / deselected。该阶段 `AGENTS.md`、Stage Head、Data Head、V4-12 Head 四个 SHA 均与唯一基线一致。独立审计项与阶段完成门分别记录在 `reports/r17a/`。

## R17B：正式 engineering authority

唯一 candidate 为 `reports/v4_13_runtime_r16/real/2026-09-30/r6/manifest.json`，SHA `a02e7918826627c2b496d89e546d3f5a408e4c68a1a89bc93946e152e7ca42ec`。r5/r6 及 R16R1 外审证据保持原始字节。

新建 `data/v4/V4_13_ACCEPTED_HEAD.json`，绑定外审 `65262197…`、审计 seal `f12315bf…`、测试源码 `d3707886…`、r6 全部 artifact / accepted input / runtime source references 和完整 14 项合同包。projection v1.2 的 SHA 为 `567b498c9e0f828dc041d56ab56e79c8a4d34877fd09eef46a9c1f504396b19c`。

替换 Stage 前保存精确 V4-12 parent archive。新 Stage 为 `V4_00_TO_V4_13_ACCEPTED`，旧阶段的全部字段、binding 和 capability scope 逐项保留。Data Head 仍为 2026-09-30，V4-12 Head 与 AGENTS byte-identical。

正式入口 `AcceptedContracts` / `current_contracts` 先读当前 Stage 的 exact V4-13 Head binding，再从 Head 读取 exact r6 合同包；不依赖 informal amendment receipt 的存在。历史 membership route 的旧 Stage binding 通过独立解析回执映射到精确归档；冻结合同原文与 binder / LOO / publication 代码不改写。旧测试仅切换阶段对应的合同入口，原业务向量和断言保留。

P01–P15 独立 promotion gate 全部通过，包含审计、seal、源码、r6、合同包、v1.2 lineage、R17A 完成门、parent archive、Stage predecessor、保护文件和降级范围。authority / package / parent / stage / permission 的 mutation 在相应门失败。R17B clean detached：860 passed，0 failed / skipped / deselected。

`real_signal` 保持 DEGRADED，真实 sector support / relative state 不升格 READY，historical LOO 保持 NOT_VERIFIABLE，legacy B2 保持 NOT_IMPLEMENTED。production / shadow / focus / global mandatory adoption 全部 false。

## R17C：只冻结合同与向量

读取 V4.2.2 正式基线 §53、§54、§78、§80、§81；基线 SHA `203ff46075b4039d1e2d45d54fd76ce09509535739cd6aaef4dc394de1015205`。读取区间及摘要记录在阶段合同中。

五份机器合同覆盖 17 个维度，包括全部 11 项 Replay Gate B 要求，以及 same-day predecessor、跨进程 previous-session readback、未来 publication、append-only revision、确定性和 historical PIT 等级。冻结 60 个手写正反向量，并额外保存 40 项已有独立 owner oracle 的完整 input / expected 原始记录。期望值没有通过未来 V4-14 runtime helper 生成。

DAG 使用原有 owner registry：D0/D1 是进入 D2 的并行事实分支，D3 是只读 profile/context 投影。EVENT_DIFF 在 D2 之后比较 exact previous-session state；Gate B observation join 不是 raw qualification feedback。PROFILE / CONTEXT 等实际名称有显式规范映射，负门也检验别名反馈及间接反馈路径。

跨日合同要求：T-1 持久化 publication → producer exit → T fresh process → exact T-1 readback → T transition，必须记录 PID、退出/启动时间、路径/SHA/字节数、publication/calendar identity 和读回摘要。T r1/r2 共用同一 exact previous accepted market session 和冻结 manifest；civil-day subtraction、同日 r1→r2 前驱、内存 continuity、错误读回 SHA 或日期均不能通过。

Synthetic、Real Accepted Source Capability Scoped、Historical PIT Effectiveness 分别冻结。历史 price / universe / membership / source identity / availability / AS_RECORDED adjustment 证明不足，保留 UNKNOWN / DEGRADED / NOT_VERIFIABLE；current membership reconstruction 不得声称历史 PIT。§80 的 Forward 项仅保留阶段边界引用，不执行 V4-15 工作。

验收以 `reports/r17c/completion_gate.json` 和 clean detached 回执为准。本轮只可声明 `V4_14_CONTRACT_COMPLETENESS = PASS_READY_FOR_EXTERNAL_AUDIT`；`V4_14_RUNTIME = NOT_IMPLEMENTED`，`ALGORITHM_STATE_REPLAY_PASS = NOT_GRANTED`。没有 V4-14 Accepted Head、正式 DB migration、Radar/Cohort/Settlement 或生产权限。

## 审计入口与最终边界

- `reports/r17a/completion_gate.json`：历史治理门、原 22 项 closure 和四份保护文件。
- `reports/r17b/completion_gate.json`：P01–P15、r6、正式 Head 和 promotion clean receipt。
- `reports/r17c/contract_freeze_manifest.json`：五份冻结机器合同及 SHA。
- `reports/r17c/owner_oracle_witnesses.json`：预先冻结的独立完整 oracle 记录。
- `reports/r17c/KEEP_integrity.json`：原算法、合同和 r5/r6 未修改证明。
- `reports/r17c/final_handoff.json`：唯一允许的十项最终状态和完整证据链。

干净检出使用固定源码快照；工作分支和远端只在三个阶段完成后统一推进。已有其他跨阶段开放审计项不因本轮修复自动关闭。NEXT：`STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT`。
