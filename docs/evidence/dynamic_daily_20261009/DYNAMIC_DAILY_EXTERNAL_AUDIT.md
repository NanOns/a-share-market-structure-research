# V4-DYNAMIC-DAILY-R1.1 — 全部七项工程验收记录

当前总门：IN_PROGRESS_REAL_20261009_OWNER_BUILD。独立外审 NOT_GRANTED，不能以工程测试或 Git 推送替代。用户明确将 Chrome/Edge 改为默认内置浏览器；1366/1920 两种宽度保留。

| 任务 | 已实现和实测证据 | 下一验收门 |
|---|---|---|
| DD01 | 官方日历任意缺口、独立时间/源门；1/2/5/10/20日和跨节/跨月受控时钟测试；真实日历字节回读 | 原日历独立签发不改 |
| DD02 | 官网最新包/历史抽取、可信fallback、每日期真实SDK/runtime、双系列响应、零变化证明、预算锁 | 10/08通过；10/09真实5224日线、8因子、新ZIP5559原生行，继续数值验收 |
| DD03 | 独立IO adapter/successor；旧算法字节不改；生命周期/Core/Profile/Native/LOO/Market/Focus/Forward及历史窗口 | 两次真实10/08计算，最终IO独立12组全市场比较0错；10/09计算中 |
| DD04 | SQLite WAL Job/Day/Event、AUTO默认ON、调度/持久重试/启动恢复、锁、取消边界、受限策略、CAS/WAL/回滚 | 真实无浏览器18:35启动、服务重启持久通过；隔离事务负测通过；真实新日CAS待数值门 |
| DD05 | 正式28765真实按钮/API、诊断入口、补齐/预检/重试/开关/取消/日志/版本 | IAB真实点击和1366/1920通过；新截止页待CAS |
| DD06 | 原PERIOD_RAW/PERIOD_ADJUSTED/正式聚合合同；本地RAW/QFQ周月；事件/边界/停牌/UNKNOWN | 实际当前月全证券146272独立求和/极值检查0错；10/09 oracle待生成 |
| DD07 | 最新Drive合同回读、冻结SHA、实际源/服务/浏览器证据、多缺口/负向事务测试、六HTTP rehearsal | 真实10/09 CAS后六入口/页面/重启及最终Git/Drive归档继续 |

## 同页面日期、不同包文件的实际修订

旧实测官网页面已标注2026-10-09 15:58:53，但551544006字节ZIP SHA 5e973fa2b8919635f7f5f10212ef4c4c33e7a05503c01e58650a2ac376d99ca4只含至10/08。18:35自动任务因此保留last-good并安排19:05。
用户再次提醒后18:40重新完整下载：551726664字节，SHA 635c775940b2efdb8c9779c9898306c475822517f072c0eddcec8273b14e7ad6，含10/09实际5559行。页面metadata SHA仍相同。已修复缓存仅凭页面摘要误复用：必须匹配当前官方HEAD ETag/Last-Modified/Content-Length、页面摘要和本地SHA；缺可靠validator则新捕获，前后修订竞态fail-closed。旧包保留，新包独立版本。同页面摘要且同大小、ETag变化的回归测试覆盖。
真实页面重试已将同一AUTO Job推进10/09 DERIVING。来源修订不能把首次缺失的观察写成当前仍缺失。

## 24门证据映射与实测范围

1：实读官方日历，1/2/5/10/20日跨节/跨月/恢复时钟为明确模拟。
2/8：真实最新ZIP提取旧日及新日，provider/target/content/observed分列，PIT=false。
3/4/5：16:00、18:34、18:35、WAIT及19:05恢复是受控时钟；真实18:35关浏览器启动另存。
6/7：逐日期真实SDK和响应日期SHA；实际因子非空；合法空因子逐证券成功覆盖为模拟，不冒充provider实测零变化。
9/10：真实身份/Bar/停牌守恒，继承已接受身份链；新canonical无准入证据fail-closed，独立DD-A06。
11：immutable源/generation、32次周期确定性重放；两次真实Owner等价但输入时间/GBBQ不同，不冒称两者SHA相同。
12/13：GBBQ/成员源冻结，修订独立generation；原算法重建坐标/rolling及动作oracle；成员reconstructed/PIT=false。
14/15/16：持久多日已发布日保持/失败重试/锁/预算；真实UI补齐复用AUTO Job；隔离CAS错误与回滚标记模拟。
17/18：实际关闭页面18:35启动、服务重启保留Job/暂停设置；Windows任务当前用户AtLogon，未执行Windows重启，不声称登录前系统服务。
19：HTML/SDK/缺源fail-closed且last-good保留，TLS验证不关闭。
20：strict PIT原SHA、独立context/token/权限；stale-token负测，新日实际读回待CAS。
21：实际六HTTP rehearsal同token/日期PASS（真实产物加显式模拟前驱）；正式新日六入口与两宽度待CAS。
22：Rotation/Forward原VALIDATION_ONGOING/UNKNOWN/RIGHT_CENSORED保留，不授予收益/PIT权限。
23：实际当前月RAW/QFQ全证券146272独立检查；跨周月/事件/停牌隔离测试；无BaoStock周月或分钟接口。
24：分阶段代码和证据已commit/push；最终新Owner/源SHA清单、Drive上传回读继续。

独立事项详见INDEPENDENT_AUDIT_ITEMS.md。DD-A05 Amount表示差异保持独立开放，Native不替换、不任意容差，不关闭历史Amount A。原FP页面缺口、Rotation/Forward外审仍沿用原状态，不声称FP01–FP14整体PASS。
正式last-good 10/08 SHA e751fb6ebee81baa3fd213515800e220135738d485118828bc6c81fe9dd853c8；strict9/30 PIT SHA 38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40。D:/new_tdx只读；不增scanner、分钟、财务、外部复权、概率或交易权限。真实新日成功后更新本记录并完成归档。
