# 全系统修复与续审 R3

基线 `239fb9b545ac25305af02a645a77d82246cbb71a`，总状态 **AUDIT_INCOMPLETE**。

## AR2-E01 / A1

新有效问题视图逐条保留历史引用，FA-012 通过 effective_location 指向三个真实 Amount A 配套合同。R1/R2 原件及 SHA 保留在 STAGE_CONTRACT；程序读取 EFFECTIVE_AUDIT_ITEMS_R3.json。

首页按 INVALIDATED→EXITED→WEAKENED→UPGRADED→REENTERED→NEW 保留每实体首条，风险与净信息分母从同一选择结果计算。1,956 种非空有序子集通过；五个真实冻结运营日只读重放通过。真实源各日没有多事件类型实体，因此这是潜在缺陷修复，不宣称已发生线上事故。

首次测试夹具漏 source sha256，修正夹具后通过；保留首次失败原件。业务修复仅工程验收，生产进程未重启，不能声称已加载新代码。

## 后续批次

A2/A3/A4/A5/A6及 B 类继续独立执行。B4 不重复既有通过数值；H21仍缺20个合法PIT观察。C等待真实新交易日来源，D等待完整成熟/OOS，E实体Windows验收须另有明确授权。没有外部接受或生产Grant。

## A2 / A3

E2/E3 仅放行解析后位于 G:/codex_tmp 或 G:/codex work/fep_engineering 的工程路径。目录穿越、非工程、生产、TDX及旧E/F路径拒绝；Windows symlink创建因权限1314失败原件保留，采用真实junction验证重解析点内外路径，12项最终通过，未改变权限设置。

比较与详情共用按日期可用对象的唯一别名解析，支持旧/新六位代码及完整代码，歧义/未知不选任意实体。四mode按股票rps5/20、板块sector_rs5/20取值，显示收益与分位单位。五日真实HTTP及四mode Edge DOM通过。浏览器与HTTP服务仅审计GET，未接管28765。
