# V3 P09 FULL_PASS 总收口（2026-09-13）

## 阶段合同

依据最新 V3 主文档 SHA-256 `52536035f82d4754eda13241181f2aa8563b9d37e280e2ae39bfbd3a5a6c9d5b` 的 §18.12、§19.3–19.5、§20.8、§22.2–22.3 和 C20-10/C20-11。龙字诀现成功能优先按其 EXE 内 Python 3.12 字节码实现复核；项目增强项不作为 P09 主功能门禁。

## 反查修复

- EXT06 市场概况：反查 `api.ths_market_overview.build_url`，确认必须传 `date=YYYYMMDD`。修复后当前有界复测返回成功，涨跌平、来源成交显示值进入速览。
- EXT01 涨停梯队：反查 `api2.endpoints.ths_flow_api._url_limit_up`，恢复龙字诀数字字段码和 `limit=200`。来源返回 `high_days`；适配器区分首板、连续 N 板和 M 天 N 板，9天5板不作为5连板。分页按来源 `total/count/page` 验证完整，真实 2026-09-10/11 样本均 `AVAILABLE/COMPLETE`。
- 题材金额：反查 `xgt_topic_api._Col/_parse_stock_row/_make_topic_blocks`，按 `circulation_value × turnover_ratio / 1e8` 输出龙字诀亿元估算，题材内和全局按代码去重，保留有效成员数；真实样本 46/46 个成员可计算。
- 跨日晋级：复用龙字诀 EXT05 `yesterday_limit_up` 产品的 `yesterday_limit_up_days`、`limit_up_days` 和当日涨幅，输出成功、未晋级、未知、合格分母及描述性比率；未知不进入分母。页面明确显示来源池口径。
- EXT02–09：修正探测绕过自身能力回执的循环依赖后，所有数据集和枚举变体均通过当前有界复测。热榜继续只在请求时读取，不持久化 raw、row 或 batch。

## 验收结果

- `scripts/audit_p09_v3.py`：`FULL_PASS`，0 findings。
- `scripts/verify_p09_g09_close_out.py`：`FULL_PASS`，全部 5 个门禁检查通过，`release_ready=true`。
- `pytest tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7`：302 passed。
- P09 定向：59 passed；页面 JavaScript `node --check`、Python compileall、`git diff --check` 通过。
- TDX 输入未修改；生产数据库未写入；在线请求有界。

P09/G09 最终状态为 **FULL_PASS**。严格同步逐股盘中报价重排和更多题材到本地板块映射属于后续增强，继续受独立证据门控制，不影响 P09 龙字诀在线主功能验收。下一阶段为 P10-01。
