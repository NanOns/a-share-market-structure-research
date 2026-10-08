# FP06 板块研究与轮动全景执行记录

合同：06 卡、REV2 §62C/64。沿用 V4-03 Core Factor、V4-04 Core Profile 和 V4-08 native 算子，以 9/30 真实接受数据重新计算当期输入；不改旧 heads、输入收据或权限。

真实补算 5,224 个 Core/Profile 与 378 板块。378 板块已具当期 ret1/5/20 中位相对强度、上涨宽度、参与度、位置、集中度；373 板块具有效类型内排名。原本全面缺少当期 Core 的缺口已定向补齐。行业/概念筛选、强度/宽度数值排序、完整成员检索、同日 Jaccard/交并集/唯一成员占比及跨板块跳转已实现。

历史依据：最早接受成分股快照 2026-09-30；不拿当前成员反算旧板块状态。5/10/20 日因子线与轮动历史仅展示真实单点和缺口，原 rotation 的 UNKNOWN 不硬改成 CONFIRMED。base seed upstream 未有可消费完整真实真值，种子宽度局部 UNKNOWN；sector stage/lifecycle owner 当前发布缺失，单独诊断。Overlap cluster 没有已绑定版本化 engine 输出，Jaccard 不冒充 cluster。

独立对账 12 板块 × 3 期限中位值共 36 项全匹配。定向测试 29 项通过，覆盖冻结分母交并集、排序、上下文和首页边界；IAB 截图已归档。命令 `python -B scripts/build_fp06_sector.py`、`python -B scripts/run_fp02_research_snapshot.py`；测试 `python -B -m pytest -q -p no:cacheprovider --basetemp E:/codex_tmp/test_temp/fp06_final_20261008 tests/test_fp06_sector.py tests/test_fp05_home.py tests/test_fp02_research_snapshot.py tests/test_fp04_ui_authority.py`。

Acceptance：DEGRADED_PASS；真实当期非 seed 原生数值已接通，历史/阶段/seed 仍按具体源能力隔离。Next FP07 复用这批现算 Core/Profile，发布股票画像与历史真实 OHLC 索引。不得将本执行结果当作独立外部验收或全产品完成。
