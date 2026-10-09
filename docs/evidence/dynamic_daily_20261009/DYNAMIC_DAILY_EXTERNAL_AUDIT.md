# V4-DYNAMIC-DAILY-R1.1 — 全部七项工程验收记录

当前总门：PASS_ALL_SEVEN_ENGINEERING_KEY_DELIVERY_USER_MANUAL_UPLOAD。独立外审 NOT_GRANTED，不能以工程测试或 Git 推送替代。用户明确将 Chrome/Edge 改为默认内置浏览器；1366/1920 两种宽度保留。

| 任务 | 已实现和实测证据 | 下一验收门 |
|---|---|---|
| DD01 | 官方日历任意缺口、独立时间/源门；1/2/5/10/20日和跨节/跨月受控时钟测试；真实日历字节回读 | 原日历独立签发不改 |
| DD02 | 官网最新包/历史抽取、可信fallback、每日期真实SDK/runtime、双系列响应、零变化证明、预算锁 | 10/08与10/09通过；10/09真实5224日线、8因子、新ZIP5559原生行，正式新日已发布 |
| DD03 | 独立IO adapter/successor；旧算法字节不改；生命周期/Core/Profile/Native/LOO/Market/Focus/Forward及历史窗口 | 10/08最终IO独立12组全市场比较0错；固定输入完整重算155文件SHA一致；10/09全部Owner实算完成 |
| DD04 | SQLite WAL Job/Day/Event、AUTO默认ON、调度/持久重试/启动恢复、锁、取消边界、受限策略、CAS/WAL/回滚 | 真实无浏览器18:35启动、服务重启持久通过；隔离事务负测通过；真实10/09 CAS COMMITTED，六HTTP与发布后服务重启通过 |
| DD05 | 正式28765真实按钮/API、诊断入口、补齐/预检/重试/开关/取消/日志/版本 | IAB真实点击和1366/1920通过；新截止10/09页与工作台实际验收通过 |
| DD06 | 原PERIOD_RAW/PERIOD_ADJUSTED/正式聚合合同；本地RAW/QFQ周月；事件/边界/停牌/UNKNOWN | 实际当前月全证券146272独立求和/极值检查0错；10/09真实全市场146272独立检查0错 |
| DD07 | 最新Drive合同回读、冻结SHA、实际源/服务/浏览器证据、多缺口/负向事务测试、六HTTP rehearsal | 真实10/09 CAS、六入口、双宽度、发布后重启通过；用户改为关键文件本地交付，自行网页上传 |

## 同页面日期、不同包文件的实际修订

旧实测官网页面已标注2026-10-09 15:58:53，但551544006字节ZIP SHA 5e973fa2b8919635f7f5f10212ef4c4c33e7a05503c01e58650a2ac376d99ca4只含至10/08。18:35自动任务因此保留last-good并安排19:05。
用户再次提醒后18:40重新完整下载：551726664字节，SHA 635c775940b2efdb8c9779c9898306c475822517f072c0eddcec8273b14e7ad6，含10/09实际5559行。页面metadata SHA仍相同。已修复缓存仅凭页面摘要误复用：必须匹配当前官方HEAD ETag/Last-Modified/Content-Length、页面摘要和本地SHA；缺可靠validator则新捕获，前后修订竞态fail-closed。旧包保留，新包独立版本。同页面摘要且同大小、ETag变化的回归测试覆盖。
真实页面重试将同一AUTO Job推进10/09全量数值计算，19:57:28完成PUBLISHED_FULL。来源修订不能把首次缺失的观察写成当前仍缺失。

## 24门证据映射与实测范围

1：实读官方日历，1/2/5/10/20日跨节/跨月/恢复时钟为明确模拟。
2/8：真实最新ZIP提取旧日及新日，provider/target/content/observed分列，PIT=false。
3/4/5：16:00、18:34、18:35、WAIT及19:05恢复是受控时钟；真实18:35关浏览器启动另存。
6/7：逐日期真实SDK和响应日期SHA；实际因子非空；合法空因子逐证券成功覆盖为模拟，不冒充provider实测零变化。
9/10：真实身份/Bar/停牌守恒，继承已接受身份链；新canonical无准入证据fail-closed，独立DD-A06。
11：immutable源/generation、32次周期确定性重放；另做相同冻结原始输入完整数值重算，155个全部产物SHA完全一致（DD07_FULL_FROZEN_REBUILD_DETERMINISM）；不同源版本的等价验收不冒称SHA相同。
12/13：GBBQ/成员源冻结，修订独立generation；原算法重建坐标/rolling及动作oracle；成员reconstructed/PIT=false。
14/15/16：持久多日已发布日保持/失败重试/锁/预算；真实UI补齐复用AUTO Job；隔离CAS错误与回滚标记模拟。
17/18：实际关闭页面18:35启动、服务重启保留Job/暂停设置；Windows任务当前用户AtLogon，未执行Windows重启，不声称登录前系统服务。
19：HTML/SDK/缺源fail-closed且last-good保留，TLS验证不关闭。
20：strict PIT原SHA、独立context/token/权限；新日实际六HTTP读回和旧token409负测PASS。
21：实际六HTTP rehearsal同token/日期PASS（真实产物加显式模拟前驱）；正式新日六入口同token/日期PASS，实际IAB两宽度PASS。
22：Rotation/Forward原VALIDATION_ONGOING/UNKNOWN/RIGHT_CENSORED保留，不授予收益/PIT权限。
23：实际当前月RAW/QFQ全证券146272独立检查；跨周月/事件/停牌隔离测试；无BaoStock周月或分钟接口。
24：分阶段代码和证据已commit/push；最终新Owner/源SHA清单已生成，用户最新要求仅交付关键数据，不继续全量API上传。

独立事项详见INDEPENDENT_AUDIT_ITEMS.md。DD-A05 Amount表示差异保持独立开放，Native不替换、不任意容差，不关闭历史Amount A。原FP页面缺口、Rotation/Forward外审仍沿用原状态，不声称FP01–FP14整体PASS。
正式last-good 10/09 SHA 55d78be5a773c1c7d0475b1a0d755bfa6f4cefb14cc28e273945cc3acf4dc83e；前驱10/08 SHA e751fb6ebee81baa3fd213515800e220135738d485118828bc6c81fe9dd853c8；strict9/30 PIT SHA 38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40。D:/new_tdx只读；不增scanner、分钟、财务、外部复权、概率或交易权限。真实新日已发布，工程绿不替代独立外审。


最终真实证据：DD07_REAL_20261009_RELEASE_READBACK.json、DD07_REAL_POST_CAS_SERVICE_RESTART.json、DD07_REAL_20261009_PERIOD_NUMERIC_ORACLE.json、DD07_FULL_FROZEN_REBUILD_DETERMINISM.json，以及PUBLISHED_1366/1920与WORKBENCH截图。60项回归全部通过。实际计算仍沿用已接受5224证券池；349包内额外证券不冒称新增Owner准入。独立Amount差异4946项继续开放。


用户最终归档范围：只要关键数据，大文件不通过API上传，提供散文件供用户网页端自行上传。大批量传输已停止；此前全量分卷仅部分上传/回读，不宣称全量云端归档PASS。最终报告DYNAMIC_DAILY_FINAL_DELIVERY.md、关键数字DD07_KEY_DATA.json、本地小包验收DD07_KEY_DELIVERY_LOCAL_RECEIPT.json。工程七项已完成，独立外审NOT_GRANTED。
