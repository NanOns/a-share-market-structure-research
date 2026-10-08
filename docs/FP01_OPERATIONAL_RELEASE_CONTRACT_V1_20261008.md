# V4 运营生产发布合同 V1｜可审阅迁移说明

机器权威：config/v4_operational_production_release_policy_v1.json；运行注册权威：config/v4_production_runtime_authority_v2.json；准入/发布实现：src/v4/operational_release.py。权限来源是本轮用户总卡及FP-01，不是旧收据被重新解释为PASS。

|维度/状态|精确定义|消费行为|
|---|---|---|
|operational_state / OPERATIONAL_PRODUCTION_ACTIVE|本范围具真实产物、精确代码/合同/输入及独立QA，运营注册发布回查通过|允许正常研究读取；不自动获得Focus写入或其他域权限|
|operational_state / DATA_PENDING|请求日比最后实际成功交易日晚，下一输入未接收|上一真实结果继续可见，显示实际交易日；不得补造今天行情|
|operational_state / SOURCE_INCOMPLETE|本范围所需来源实证不完整|阻断受影响字段/能力，保留精确原因；其他域继续|
|operational_state / QUALITY_DEGRADED|范围能运行，但指定质量维度存在已解释降级|降级字段按原quality/reason显示，禁止变KNOWN|
|operational_state / ENGINEERING_NOT_READY|本范围的新发布适配、实现或工程QA没有满足完整准入|给出定向修复责任，不据此推断所有旧代码不存在|
|evidence_state / VALIDATION_ONGOING|正在积累真实样本/效果检验，或历史可用时点未证明|不阻塞已过完整性QA的运营读取；明确样本量和不确定性|
|evidence_state / HISTORICALLY_ACCEPTED_SCOPED|已有独立历史验收的精确范围|只允许复述绑定范围，不推导全系统PASS|
|evidence_state / STATISTICALLY_VALIDATED_SCOPED|需另立统计证明合同和证据|本V1准入函数明确拒绝产生该证明，防止伪造统计优势|
|data_quality_state / KNOWN|当前确有源和原生产器定义的可判定事实|保留单位、窗口、原来源路径及as-of|
|data_quality_state / QUALITY_DEGRADED|真实产物存在，但有明确质量限制|不能升级底层UNKNOWN或掩盖缺口|
|data_quality_state / SOURCE_INCOMPLETE|必需来源不可用|不能通过本V1运营准入|
|data_quality_state / PENDING、RIGHT_CENSORED|真实Forward生命周期尚未到期/右删失|可作为真实生命周期结果消费，不标成熟/收益已证明|

状态三维独立：例如运行ACTIVE、验证ONGOING、质量DEGRADED可以同时成立；请求下一日时呈现DATA_PENDING，但真实结果可访问。非已准入域的矩阵质量可为null并标NOT_ASSESSED，不用SOURCE_INCOMPLETE冒充未经检查的质量结论。

每次准入必带 owner、release_id、source_snapshot、contract_version、source_as_of、trading_date、input_digest、published_at、evidence_origin、evidence_state、data_quality_state、knowledge_lineage，并精确绑定input/output/code/contract/qa。字段单位/窗口/复权坐标、source_refs和原始quality留在原生产产物，不由本准入器重新计算或删改。跨日期/跨source snapshot不得拼成同次发布；未来来源、缺时区、未知feature、自我QA、QA字节变动、缺QA检查、未准入依赖都拒绝。

旧Shadow20会话/Forward收益证明改记历史验证维度，不作为运营部署全局门；旧schema/身份/前视/价格坐标/字段消费/依赖完整性仍是工程准入要求。旧五类production_permission、V4-19/20 v1/v2、全部已冻结收据不动。旧Focus历史和Forward cohort保留；自动持续观察在FP08通过独立真实源/事务/重入工程验收，再由FP14切路由；不能把Cohort当Focus。

蓝绿发布使用新的runtime/operational_release_v1目录；release内容按SHA不可变命名，并发发布锁内做expected digest CAS，保留原指针原字节，交换后重做准入和来源readback。回查失败立即恢复原指针；rollback先核验预期当前digest及所保留前版本，再重新验证来源；过时或损坏rollback失败且恢复当前，不回退假值。校验器源码和QA收据按内容寻址固化，冻结后的合同用successor扩展。HTTP原v1权威作为已存在回滚基线保留；本卡不承担FP14完整服务切换。

本轮只有 V4_13_PROFILE_ADVANCED 真实已有投影获得运营注册准入，所有原UNKNOWN/降级继续保留。其它42范围已经盘点、进入逐域适配/定向修复列表，不把合同存在当作所有算法已投产。FP02/03将此准入/三维语义接入统一真实数据与API，FP04建设六入口，FP13验收完整交互，FP14发布。FP01本地PASS不代替这些阶段。
