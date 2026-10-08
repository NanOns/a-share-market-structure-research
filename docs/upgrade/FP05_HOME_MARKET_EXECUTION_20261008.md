# FP05 今日总览与市场四轴执行记录

合同：任务卡 05、REV2 §62B/63、FP01 successor 研究运营政策；FP02/03/04 已交付基础接口。当前处理日 2026-09-30，知识谱系 RECONSTRUCTED_CORRECTED，不宣称历史 AS_RECORDED。

旧成果沿用：V4-03 四轴 primitives / trend 与 V4-04 市场环境 hysteresis、V4-11 真实状态事件。新适配：9/30 真实行情和涨跌停 owner facts，20 前序会话成交额比例中位数，同成员 T-3 上涨宽度差及 T-1 压力变化。新路径版本明确保留 frozen prefix、逐日 start universe、覆盖率及 bridge，不改旧 path/head。

已补算四轴：WEAK / IMPROVING / THIN / LOW，压力 DECLINING。合成环境 NEUTRAL 为连续会话规则保留的上次接受标签，当前候选 RECOVERY_ATTEMPT，未伪造中间日期 axes。UI 独立展示四轴、环境候选、数值/分母/来源；独立个股变化 33 条符合 / 展示 30，完整事件列表未截断。风险变化与 PERSISTENT 分离，板块/轮动无充分 prior PIT 数据时逐域说明。

核验：20,148 个 OHLC 与 current accepted ADJUSTED_DAILY 完全对照；27 项定向测试通过，包含纯风险、无变化、零信号和首页上限；实际 IAB 总览/中文四轴及来源按钮已检查，控制台无错误。Edge 未连接，独立 Edge 验收保留到 FP13。

命令：`python -B scripts/build_fp05_market.py`、`python -B scripts/run_fp02_research_snapshot.py`；测试 `python -B -m pytest -q -p no:cacheprovider --basetemp E:/codex_tmp/test_temp/fp05_20261008 tests/test_fp05_home.py tests/test_fp02_research_snapshot.py tests/test_fp04_ui_authority.py`。

Acceptance：DEGRADED_PASS，市场四轴当期可消费；板块阶段变化/成员预览待 FP06 补入可用源，不能以真实缺 prior PIT 历史伪造变化。跨日 PIT 回放仍属 FP12。下一阶段 FP06：定向补算当期 Core 因子供板块原生算子使用，同时为 FP07 画像复用，禁止当前成员回填历史。
