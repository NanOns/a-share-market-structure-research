# 独立审计事项

这些项目与 DD01–DD07 工程运行验收分开，不能用提交推送或测试绿灯关闭。

| 项目 | 范围与证据 | 当前结论及独立接受门 |
|---|---|---|
| DD-A01 | 官方日历 SHA 与 SSE/SZSE 一致冻结字节；DD01_REAL_CALENDAR_READBACK | 工程读取/缺口计划通过；原日历候选独立签发状态沿用，不伪造更新 |
| DD-A02 | Rotation 全量递归状态机；原 R4.3 独立审计 | VALIDATION_ONGOING；需独立全量 oracle，与非依赖日更门分开 |
| DD-A03 | 请求账本、跨进程 SDK 锁、崩溃恢复；BUDGET_LEDGER_CORRECTION 与 SDK 测试 | 工程恢复通过；请求始终累计，未重置预算；模拟锁测试不是 provider 实测 |
| DD-A04 | 原算法字节绑定与新 IO successor；DD03_OWNER_EQUIVALENCE、DD03_KERNEL_ADMISSION | 原算法保持，12 组全市场数值/质量等价；新日逐日 oracle/CAS 独立记录；外审 NOT_GRANTED |
| DD-A05 | 全匹配 TDX/BaoStock Amount 表示差异；10/08 DD_A05_AMOUNT_REPRESENTATION_AUDIT，10/09 DAY AMOUNT_CROSS_SOURCE_AUDIT 共4946差异（DD03_REAL_NEW_DAY_SOURCE_SCOPE） | 不替换 Native、不套任意容差；整数 CNY 再 float32 只是现有样本推断；需独立表示合同 |
| 历史 Amount A | 原板块/历史成交额综合审计 | 不由 DD-A05 或当前阶段门自动关闭，保留原范围与证据 |
| DD-A06 | 证券身份/代码变更、新上市 canonical 权威 | 已接受身份链保留；无接受证据的新 canonical 证券 fail-closed，禁止按名称合并；日更遇到新身份必须生成明确阻断证据及独立身份准入 |
| DD-A07 | Forward 成熟度、样本与效果验证 | VALIDATION_ONGOING/PENDING/RIGHT_CENSORED 按原产物保留；日更不授予收益证明 |
| DD-A08 | Windows 登录前无人值守 | 当前是当前用户登录触发、Limited 后台任务；已实际服务重启，未执行 Windows 重启；不声称登录前系统服务验收 |

本轮用户直接要求使用默认内置浏览器，Chrome/Edge 验收范围已被该回复替代。两种宽度验收仍执行。
