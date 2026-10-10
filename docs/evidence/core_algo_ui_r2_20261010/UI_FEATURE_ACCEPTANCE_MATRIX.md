# 六入口续做验收矩阵 R2

日期：2026-10-10；统一实际 T0：2026-10-09。前一轮冻结证据保留在 `../core_algo_ui_r1_20261010`。状态只覆盖下面列出的具体功能，不授予 FP13/14 外部发布通过。

| 入口/任务 | 本轮结果 | 真实证据与数值 | 精确未完成范围 |
|---|---|---|---|
| ALG01 字段盘点 | PASS_SCOPED | CORE_ALGO_UI_LINEAGE_MATRIX.json：18 必填属性、6 独立裁决维度 | 各字段不继承模块级整体 PASS |
| ALG02 独立数值 | PASS_SCOPED | oracle/OUTPUT.json：20,276 比较、0 差异；25 股票、4 板块、3 Episode | 原始 D0 全公式、完整 D2 递归、Rotation 篮子/保持输入链另列 OPEN |
| BFF03 数据字段 | PASS_SCOPED | API_FIELD_CONTRACT_AUDIT.json：42 路由、6 种图表组合、322 个唯一板块成员 | 缺少 Owner 的字段仍 SOURCE_INCOMPLETE |
| 今日总览 FP05 | PASS_SCOPED | 5,224 股票、400 板块；弱趋势/宽度恶化/正常参与度/低压力；实际变化去重和显示上限 | 完整结构风险变化 Owner 不齐；不签完整首页合同 |
| 板块研究 FP06 | PASS_SCOPED | 全量行业筛选 132；成熟度/健康 UNKNOWN 筛选；强度降序未知值置末；实际 Why-now 前序/当前状态和原生输入 | 板块 D2 成熟度/健康 Owner 不存在；逐个解释 27 个未映射成员 OPEN |
| 个股研究 FP07 | PASS_SCOPED | 全量搜索、冻结身份历史别名、430017 OUT_OF_UNIVERSE；三一重能历史 09/30 收盘 13.240，T0 月线末根 13.59；RAW/QFQ D/W/M 接口通过 | 高级 H 假设及完整无资格观察池 OPEN；历史图表 T0 专用素材缺口不伪造 |
| 关注跟踪 FP08 | PASS_SCOPED_REPAIR | 强达电路 301628 已失效，Episode 结束日 10/09；未结束唯一对象 2,804，电气设备 176/2,804=6.3%；子资源分层 | 新增/自动写入独立授权门未开；不以 Focus 替代验证样本池 |
| 市场与事件 FP09/10 | PASS_SCOPED | 上涨 2,989、下跌 2,107、平盘 113、未知 15；分母 5,224，行情 5,210，成交额 19,003.65 亿元；涨停 72、跌停 11、停牌 14 | 分钟首封/炸板及正式新闻事实源不存在；同日多锚点保留，不当重复删除 |
| 数据与诊断 FP11 | PASS_SCOPED_REPAIR | 质量按每字段 value/quality 统计；实际任务状态、旧模块目录、Shadow 无真实数据状态；日期切换并跨入口保留 | 严格 PIT 首获历史不足；Shadow 不激活 |
| Replay/Compare FP12 | RESTRICTED_READ | 5 个实际发布日期可选；研究日期与最后接收日分别显示；非严格 PIT 明示 | T0 专用图表/市场读包不能冒充旧日；严格 PIT 外部准入未获 |
| QA05 浏览器 | PASS_SCOPED_OBSERVATIONS | iab/BROWSER_DOM_RECORDS.json：1366×768 与 1920×1080；真实搜索/跨页日期/故障隔离/恢复 | 只给已记录路径判定，不给未观察功能继承 PASS |
| FP02 下一交易日 | WAIT_REAL_DAY | 当前 10/10 周六；没有伪造 10/12 行情 | 首个合法后继输入后执行真实日更 |
| Forward 验证池/V4-15 | SOURCE_NOT_PRESENT | 旧 Focus price path 可读取，但没有独立全合格信号 enrollment/cohort Owner | Owner 入场、结算及统计验证独立验收 |
| FEP | CAPABILITY_NOT_READY | 原始模型/数据授权与首获时间事实不足，保持原门 | 不新增预测，不回填未来数据 |
| FP13/FP14 | EXTERNAL_ACCEPTANCE_NOT_GRANTED | 工程证据可供复核；当前用户重启后加载代码 | 独立外审和联合原子发布门不自授 |

CSV 保留已有同快照全量分页导出及中断恢复，移除了没有后端支持的“浏览器原生下载 CSV”链接；未将移除链接视为新增服务端 CSV 能力。

Browser DOM 记录是实际页面观察。传输故障仅在自建 28768 代理施加，28767 读取真实 Owner，用户 28765 服务未重启。截图最多 8 张，完整 Owner 和本地数据库不进入交付包。
