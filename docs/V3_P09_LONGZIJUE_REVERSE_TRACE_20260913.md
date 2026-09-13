# P09 龙字诀实现反查与修复记录（2026-09-13）

阶段合同：V3 §19.5、§20.8、§22.3、C20-10、C20-11；P09 题材分布 API `v3-p09-events-distribution-v1.2`。输入 EXE 为 `D:/Users/lps/Desktop/龙字诀v2.1.2.exe`，仅静态读取；TDX 根目录未写入。字节码证据为 `runtime/py312_embed_analysis/marshal/api2.endpoints.xgt_topic_api.marshal` 与 `api2.endpoints.ths_flow_api.marshal`，由 Python 3.12 反汇编核对，未执行第三方程序。

## 实际实现证据

- `xgt_topic_api._Col` 源数组列 4 为 `FREE_FLOAT`，列 10 为 `TURNOVER`；`_parse_stock_row` 第 288 行先将流通市值除以 1e8、换手率乘 100，随后计算 `amount = turnover_percent / 100 * free_float_yi`。`_make_topic_blocks` 第 404 行把成员 `amount` 求和并保留两位小数，字段为 `amount_total`。这是一项以流通市值和换手率推算的亿元展示值，不能等同于源直接提供的成交额。
- `ths_flow_api._parse_limit_up_row` 第 245 行也用 `turnover_rate / 100 * currency_value_yi` 生成展示 `amount`；不是读取响应里的同名原始成交额。
- `ths_flow_api._parse_header_rate` 第 405 行读取 `data.limit_up_count.today/yesterday`、`limit_down_count.today/yesterday` 的 `num/history_num/rate`。该路径是来源给出的今日/昨日封板、炸板等顶部比率；未发现按相邻交易日完整股票池计算“前 n 板→当日 n+1 板”的晋级分母。不能把顶部 `rate` 改名为跨日晋级率。

## 本次处理与验收

`p09_products.py` 按已查明公式增设 `dragon_estimated_amount_yi`、有效成员数、公式口径；题材内按股票代码去重，全局跨题材再去重，缺失字段保持 `null`。API 和页面单列标为“龙字诀算法估算”，严格 `amount_sum` 继续不可用，避免把推算金额冒充成交额。用户可直接看到估算值及覆盖人数。跨日晋级率仍需同源相邻日完整池及停牌/未知分类证据；现有本地 `limit_promotion_history` 是独立本地估算链，不充当在线事实。

验收：P09 相关单测 19 项通过；Python 编译、`git diff --check` 通过；G09 关闭核验仍为 `DEGRADED_PASS`，其余在线源限制未变。下一阶段是取得相邻日完整池并按 V3 C20-10 建立晋级转移，届时才开放在线晋级率。
