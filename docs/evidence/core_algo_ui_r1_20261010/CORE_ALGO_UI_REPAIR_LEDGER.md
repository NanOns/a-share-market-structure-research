# R1 修复账

BASE_SHA 64a0e31390765027f96b6a537bbf7f044abf6c83；算法审计阶段cbe8140f；工程修复阶段86c2ff8b。每阶段已commit/push，最终交付SHA另见DELIVERY_RECEIPT.json。

| 实证问题 | 修复文件 | 前→后及证据 |
|---|---|---|
| stock/chart已有真实历史但路由缺源 | core_product_bff_r1.py、stock.js、build_core_product_read_pack_r1.py | SOURCE_INCOMPLETE→6组合真实RAW/QFQ；13.59、420/91/22根；历史页有更早/更新控件 |
| 周线末根一律被当形成中 | BFF/chart | 10/09真实正式period_owner CLOSED_ONLY_READY；月线仍AS_OF_PARTIAL_READY |
| 成员源数量混入研究分母展示 | BFF/project、members、components.js | T0706列表349 vs成员页322→源349/映射322/未映射27/有行情322；322完整分页 |
| sector timeline/overlap缺适配 | BFF、app.js | 5个实际dated点、201重叠、PITfalse，成员页继续可用 |
| 首页缺真实变化且存在去重范围风险 | BFF/home、app.js | 实际Focus456唯一变化、风险19、持续645；仅10展示板块覆盖去重，独立365/显示30 |
| Focus各子域语义不明确 | BFF、components.js、app.js | 三一重能1Episode/2Anchor/4Observation/10Outcome，独立层数组与来源；不冒充Cohort |
| market四子路由缺适配 | BFF、物化脚本 | 真实2989/2107/113/15，分母5224；5指数、涨停72跌停11、梯队72 |
| 一子域失败会阻断后续区块 | app.js/section | breadth503实际IAB四轴与指数仍在；撤销故障+3秒慢请求后真实数值恢复 |
| 显示名称、轮动状态隐藏、缺源卡空白 | BFF/project、labels.js、components.js | 绑定显示权威中文名；明确轮动进入/退出/扩散；null显示来源未接入 |
| 筛选板块类型丢失既有query | app.js | 更新type同时保留URL筛选/排序，offset归零 |
| 诊断与corrected比较缺dated适配 | BFF、replay.js | source/health/contracts与stock/sector/market比较绑定同token，明确非严格PIT |
| 默认服务仍旧进程 | run_workbench_service.py、core_product_server_r1.py | 新默认入口正常重启后用继承既有DailyJobs的reader；未改用户进程、未修改冻结registry |

回归：REGRESSION_RECEIPT.json含17pytest、退出码0；API38路由、6图表、成员322、负例409/400；独立oracle840/0差异；IAB八图/六域双宽/数字回读。合成unit fixtures只验负例，不用于生产数值PASS。

P0剩余验证：全Market trend/breadth path、全部detector和Rotation递归、完整退市/重入边界、生产重启后真实端口联合QA、真实OS离线和新日期切换。未以截图绿灯关闭。当前发布核心候选仅工程范围，外审未授予。

P1 OPEN_NEXT_BATCH：历史别名/池外解释、27未映射身份明细、10/20日扩散和cluster、H竞争解释全Owner、legacy/Shadow诊断迁移、严格PIT、Validation Cohort/Forward/FEP。AmountA等综合问题单独见CROSS_CUTTING_AUDIT_ITEMS.md。

本地历史SQLite426196992字节留G盘，未提交/上传；构建脚本和小物化manifest可复现。旧数据Head、PITHead、TDX与旧receipt均未改。用户原28765生产页面最终确认需要正常重启一次；隔离28767页面使用真实接受数据，不是mock业务。
