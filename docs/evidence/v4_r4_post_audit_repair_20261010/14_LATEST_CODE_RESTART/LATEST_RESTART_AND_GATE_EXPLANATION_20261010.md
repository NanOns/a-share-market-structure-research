# 最新代码重启与剩余门说明（2026-10-10）

已按用户直接授权重启真实28765：旧PID51368结束，新PID34900。启动加载代码8ae571b850c1ab139455409d78c3a26ce9124b2d，12个模块源SHA与启动导入字节码已取证；真实FEP API返回FEP_CANONICAL_AUTHORITY_READ_R2。六业务入口及breadth/Cohort/FEP正确token200，空/旧token409。200+SOURCE_INCOMPLETE仍按缺源处理。T0=2026-10-09、两个Head字节不变，AUTO_ON保留、无active job。没有正常停服endpoint，结束精确旧PID属于本次明确重启授权下的强制停止，不描述为正常退出。

这些门并非都无法继续开发。此前任务范围是修复候选入口、状态语义与证据，未完成或准入正式生产者；不能把SOURCE_NOT_PRESENT一概当作外部原因无限停工。

| 门 | 实际缺口 | 可继续做的事 | 不能由本次重启取得 |
|---|---|---|---|
| 板块正式源 | 10/09 exact legacy有效成员、q20/dq5_3原排名、SETUP/RECOVERY、原Episode冻结、due/settlement、scenario原publication | 独立阶段实现/验收正式Producer，在真实新T0发布六字段逐原件SHA、成员版本和窗口 | 不把9/24 A05授权改成10/09，不伪造旧Episode首次冻结 |
| Cohort正式源 | accepted Head无state cohort_signals producer、独立Validation Cohort Owner和write grant | 实现/准入完整State信号Producer，未来真实T0冻结所有eligible/ineligible并经DD候选消费 | 旧2290历史事件不能补首次入组；write与read grant不互代 |
| FEP源和权限 | 正式生产DB Owner/模型版本、独立精确能力approval、合法as-recorded prediction Owner及成熟FIT labels | 独立阶段接入真实registry/Head-CAS/approval适配器；准备按model/scope/target/horizon/capability的授权与源验收 | 全局“已授权”、caller bool、工程CAS不能替代具体正式原件；不能自行签独立批准 |
| H21严格历史 | 原搜索账本缺20个历史成员首次观测日；不是缺价格文件 | 原历史文件有真实线索时定点核验；未来DD逐实际会话捕获后，连续21合法会话再验收对应新窗口 | 今天或未来成员不能证明9月当时成员；新窗口不能修复旧历史 |
| FP14完整发布 | FP14合同要求完整FP13、产品范围、源/Owner精确摘要及UI/read authority联合回滚；当前只有scoped产品QA | 准备完整QA/候选/联合回滚演练及独立审查材料；不等到全部样本成熟才推进不相关模块 | 任务卡明确FP14另行授权、Codex不得自签EXTERNAL_ACCEPTANCE_PASS；服务重启不等于完整发布批准 |

授权来源和工程能力缺口必须分开。用户可以授权具体下一阶段开发或能力使用；原件真实性、真实时间和独立审批证据仍需各自成立。当前日更已正常运行，缺样本或H21不能阻塞RAW/市场/股票等已获准功能。

现行运行状态见SCOPE_GATE_RUNTIME_R3_APPEND.json；R2“D磁盘修复尚未加载”已由该R3追加覆盖，历史收据保留。下一阶段要围绕真实正式Producer/Owner形成可验收产物，而不是重复生成全空值列表。
