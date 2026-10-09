# V4-DYNAMIC-DAILY-R1.1 执行总合同与进度

用户授权执行全部 DD01–DD07；默认 AUTO=ON，只读运营研究，不写 TDX、不增加分钟/财务/外部复权或交易/PIT权限。原冻结R4.3、原Owner与严格9/30 PIT保留。
基线Git 6f0cf3c5a983eab481283d0436e050d70b77fe29。最新Drive FP/DRIVER回读已保存contracts/DD07_FP_CURRENT_READBACK.md与DD07_DRIVER_CURRENT_READBACK.md。Phase0继承FULL_PASS，来源reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json。

阶段具体合同、证据、验收与下一门：
- DD01：V4_OPERATIONAL_DAILY_CALENDAR_V2、V4_DAILY_SOURCE_READINESS_V2；实际官方日历回读、任意缺口受控时钟测试通过；日历独立签发状态不升级。
- DD02：TDX_LATEST_PACKAGE_TARGET_SESSION_V2；实际10/08抽取与10/08、10/09每日期真实BaoStock双响应通过；10/09页面metadata不变但ZIP替换，已加入HEAD ETag/Last-Modified/Content-Length缓存验证；详见DD02_FRESH_OFFICIAL_PACKAGE_RECHECK与DD02_SAME_METADATA_ZIP_REVISION_FIX。
- DD03：DYNAMIC_DAILY_DD03_SUCCESSOR_V1_20261009.md；独立IO适配复用原算法，immutable generation绑定真实源/GBBQ/成员/producer；10/08真实全市场最终IO12组数值和质量等价0错；10/09源真实冻结后正在完整Owner与动作/rolling重算。
- DD04：DYNAMIC_DAILY_DD04_20261009.md；持久Job、默认ON、18:35/重试/恢复/去重/锁/安全取消、受限publication策略与CAS/WAL回滚实现；真实浏览器关闭18:35启动、服务重启/暂停恢复通过，真实新日CAS待DD03数值门。
- DD05：DYNAMIC_DAILY_DD05_20261009.md；正式28765实际按钮与持久API，用户将Chrome/Edge改为内置IAB；1366/1920真实验收通过，新日期刷新待CAS。
- DD06：DYNAMIC_DAILY_DD06_20261009.md；原本地日线聚合RAW/QFQ周月，当前月实际全市场146272独立检查0错；边界/事件/停牌/UNKNOWN受控测试；10/09独立oracle待生成。
- DD07：阶段入口DD07_STAGE_ENTRY.json；最新合同/冻结SHA/六HTTP rehearsal/真实服务与IAB、多缺口和负向事务证据齐备；下一门真实10/09 CAS、六入口同token/UI、发布后重启、最终Git/Drive逐payload回读。

总状态IN_PROGRESS_REAL_20261009_OWNER_BUILD。全部七项已经实施，但不能把新日CAS前的工程证据写成全门PASS。实时24门范围与真实/模拟分别记录于docs/evidence/dynamic_daily_20261009/DYNAMIC_DAILY_EXTERNAL_AUDIT.md；独立事项INDEPENDENT_AUDIT_ITEMS.md。EXTERNAL_ACCEPTANCE始终NOT_GRANTED；提交推送不授予下一未授权门，当前全部七项用户已授权。
