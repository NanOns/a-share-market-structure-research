# 当前研究产品范围 QA

审查对象为已部署 127.0.0.1:28765 的研究读域。现场实际 HTTP 原始响应 SHA、内容和状态位于 final/PRODUCTION_HTTP_READBACK.json。10/09 板块 AVAILABLE、Cohort RESEARCH_CANDIDATE_FROZEN，5224/20896/300；正式 observed_count=null、formal_consumer_enabled=false。10/08 候选 NOT_CAPTURED，没有用新日补算；10/12 HTTP400；旧 token HTTP409。10/08 股票两页均 HTTP200，分页不同原件独立记录。

浏览器现场打开真实研究工作台，并查看 Focus 及来源详情：显示“当前成员重建，非严格 PIT”“独立运营候选 · 最新成员回算 · 非正式 D2 / 非严格 PIT / 不计入胜率”“正式 Cohort 观察数：未获准来源；成熟样本数：尚不可判定”。详情原 JSON 为 RECONSTRUCTED_RESEARCH_ONLY、HISTORICAL_RESEARCH_ONLY，并明确列出 REQUEST_TIME_UNKNOWN。正式 Cohort、结算、FEP 的中文原因与候选研究区分开，用户新增与自动写入保持只读。

发现并修复源码展示缺口：candidate_research_read_v2 新增源截止数据日、历史 first_available=null、原候选 first frozen 时间及 source capture 实際 recapture 时间；前端明确展示 RECONSTRUCTED_RESEARCH_ONLY，并区分再观察和历史首次可用。源码未以现在时钟创造过去时钟。当前 Python 进程未重启，新增 BFF 字段仍待单独授权加载；前端对旧字段缺失明确显示“当前读域未提供”。不声称此轮新 Python 字段已经生产加载。

bad archive SHA、未接受 Head、旧 token、错误日期、三次 synthetic Head 变化由隔离精确原件测试验证，不篡改实际生产 archive。原版本 Dependency bytes 与已接受历史 Head 链冻结不变。

回滚边界：本轮不改运营/strict Head，不替换现有服务端口、进程或权限；工程改动由独立 Git 提交可逆。候选目录不属于正式权限源，显示区失败只让候选不可用。实际产品切换与运行回滚仍须另行授权及独立 QA。isolated successor release 测试验证 CAS 失败/回滚，不将 synthetic receipt 冒充生产回滚收据。

验收：当前研究只读范围 PASS_SCOPED，外部范围化签收未发放。新增时间字段运行验收单列 PRE-T0-AUDIT-RESEARCH-CLOCK-DISPLAY，不能借此宣称正式 D2/Cohort/FEP/FP14 已开放。
