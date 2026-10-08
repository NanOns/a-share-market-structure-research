# R2 独立跨域审计台账

各项关闭范围独立于发布范围；测试和推送均不等于外部接受。

| ID | 范围与证据 | 接受及剩余条件 |
|---|---|---|
| AUD-R2-SNAPSHOT-PREDECESSOR-MUTABLE-REF | 紧邻前驱 ccbe6c 的 replay_operational 期望摘要 1110399985f39b031210ea0c1856626e5c0f5b6428d7c8d94de4c4df41016e83，当前文件和该路径 Git 历史不能恢复精确字节。 | OPEN：恢复精确源并验证完整前驱；本轮演练使用完整真实前驱 7699745a，不冒充紧邻前驱全部源可回滚。联合发布器新候选逐源摘要校验。 |
| AUD-R2-CURRENT-CORE | 全量5213股票/378板块/四轴，168字段来源分组；10股票×5因子、5板块×3值、四轴69项相等比对及原生QFQ均线独立算术。 | SCOPED_VERIFIED：9/30 successor 当前值；历史9/28 owner不改。复杂状态正确性沿用 owner，非全算法重新外审。 |
| AUD-R2-IDENTITY-11 | R2_OWNER_DATE_MATRIX 三个真实日身份/交易状态；11额外身份9/30全部SUSPENDED且actual_bar_present=false。 | SCOPED_RECONCILED：身份域5224，RAW行情5213，不扩池；first_available_at_target_proven=false，严格历史首获仍未证。 |
| AUD-R2-FOCUS-DAILY | 独立journal真实9/29→9/30重放、幂等、事务回滚，旧PG不可读。 | OPEN：当前只准入读投影；真实Path/Outcome owner和每日全链编排及新journal生产CAS待补，不能称迁移成功。 |
| AUD-R2-PIT-FIRST-AVAILABLE | 严格0/3；10/8开始真实首次观察冻结，保留真实捕获时间。 | OPEN：模型known_at、成员、权重、冻结篮子首获证据；corrected永不改名PIT。 |
| AUD-R2-FIELD-COVERAGE | 110行逐项保留source/UI/oracle/browser/debt维度，值不存在不刷true。 | OPEN：全功能字段未全部完成；scoped只按明确可见字段验收。 |
| AUD-R2-EXTENDED-SOURCES | 分钟触板/炸板、官方事实消息、当前LOO/FEP无合法当前绑定。 | OPEN_SOURCE：单域降级，不能补新闻传闻或fixture。 |
| AUD-R2-FORWARD-DUE | 117入组均T0=9/30，585计划在冻结日历外；5已发布记录仍PENDING。 | PENDING正常：仅以已接收日判断到期，不要求所有样本成熟。 |
