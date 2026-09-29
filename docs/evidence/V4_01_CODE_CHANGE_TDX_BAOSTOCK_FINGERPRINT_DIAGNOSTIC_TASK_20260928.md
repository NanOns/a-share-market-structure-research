# V4-01 股票代码变更｜TDX + BaoStock 源级指纹诊断任务卡

- 日期：2026-09-28
- 任务性质：**只读诊断实验 / 不修改生产 identity**
- 样本：`SZ.300114 → SZ.302132`
- 已知正式变更日：`2025-02-17`
- 关键相邻交易日：`2025-02-14`、`2025-02-17`
- 当前目的：研究真实数据源在证券代码变更前后留下的可机器识别特征，为 V4-01 generic identity-event discovery / candidate generation 提供数据证据。
- **本任务不得直接修改 R7 canonical identity、Historical Universe、V4-02/V4-03 artifacts 或 Accepted Head。**

---

# 1. 背景

人工观察到：

```text
300114 行情截止到 2025-02-14
302132 从 2025-02-17 起作为当前代码

但行情软件中查询 302132
可以看到 300114 时代的历史行情。
```

这说明代码变更在行情源中可能不是简单的：

```text
OLD_CODE history
+
NEW_CODE new history
```

而可能存在：

```text
NEW_CODE file/query
回填或继承 OLD_CODE 的历史价格序列
```

如果这种行为在 TDX / BaoStock 中能被稳定观察，则它可以成为：

```text
IDENTITY RELATION CANDIDATE SIGNAL
```

用于发现“同一证券换代码”，而不需要只依赖代码格式、名称或人工维护。

但必须区分：

```text
候选发现信号
!=
最终 SAME_ENTITY 确认
```

本实验先研究 source fingerprint，不直接修改 identity。

---

# 2. 核心问题

必须回答以下问题。

## Q1｜通达信本地 `.day` 文件

实际本地 TDX root 中是否同时存在：

```text
sz300114.day
sz302132.day
```

分别：

- first_date
- last_date
- record_count
- byte_count
- SHA256

是多少？

重点确认：

```text
300114 last_date 是否 = 2025-02-14
302132 是否包含 2025-02-17 之前的历史
```

---

## Q2｜302132 是否继承了 300114 的历史

若两个 `.day` 文件存在重叠历史：

对所有共同日期逐条比较：

```text
trade_date
open
high
low
close
amount
volume
reserved
```

同时做两种比较：

### A. 解码字段比较

统计：

```text
overlap_session_count
exact_decoded_match_count
decoded_mismatch_count
```

### B. 原始 32-byte record 比较

TDX `.day` 每条记录固定 32 bytes。

统计：

```text
exact_raw_record_match_count
raw_record_mismatch_count
```

必须额外计算：

```text
LONGEST_COMMON_PREFIX_IN_RECORDS
```

判断：

> `sz302132.day` 的前 N 条 raw record 是否和 `sz300114.day` 完全相同。

如果：

```text
300114 全部历史记录
==
302132 前缀历史记录
```

这是非常强的 TDX source fingerprint。

---

# 3. TDX 切换窗口冻结

输出两个代码：

```text
2025-02-10 ~ 2025-02-21
```

范围内所有日线记录。

至少保留：

```text
code
trade_date
open
high
low
close
amount
volume
reserved
raw_record_sha256
```

必须明确显示：

### 2025-02-14

```text
300114 row exists?
302132 row exists?
```

### 2025-02-17

```text
300114 row exists?
302132 row exists?
```

以及 2 月 14 → 2 月 17：

- close/open 连续性
- 是否存在复权差异
- amount/volume 单位是否一致
- 是否存在同时交易 / duplicate actual bar

---

# 4. TDX 当前证券主数据

检查当前 TDX：

- `szm.tnf` / 对应证券主文件
- `tdxhy.cfg`
- 其他项目当前正式读取的 security-master 来源

分别检查：

```text
300114 是否仍作为 current security 出现
302132 是否作为 current security 出现
当前证券名称
板块
行业 assignment
```

记录 source file SHA。

这里只记录事实。

不要因为：

```text
300114 不在当前 TNF
302132 在当前 TNF
```

就直接推断 SAME_ENTITY。

---

# 5. BaoStock｜四类诊断

使用项目现有：

`BaoStockClient`

并遵守 request ledger / budget。

本实验请求数量很小。

---

## 5.1 query_all_stock(day)

分别查询：

```text
2025-02-14
2025-02-17
```

检查：

```text
sz.300114 present?
sz.302132 present?
```

形成矩阵：

| Trade Date | sz.300114 | sz.302132 |
|---|---|---|
| 2025-02-14 | ? | ? |
| 2025-02-17 | ? | ? |

若存在：

```text
02-14 old-only
02-17 new-only
```

则记录为：

`ATOMIC_ROSTER_ALIAS_SWITCH_SIGNAL`

但仍然只是 candidate signal。

---

## 5.2 query_stock_basic

分别：

```text
query_stock_basic(code="sz.300114")
query_stock_basic(code="sz.302132")
```

完整保存 provider 返回字段，包括但不限于：

```text
code
code_name
ipoDate
outDate
type
status
```

特别比较：

- ipoDate 是否相同/连续
- code_name
- outDate
- provider status
- old/new 是否都还能被查询

不要修改 provider raw fact。

---

## 5.3 query_history_k_data_plus｜切换窗口

分别查询：

```text
sz.300114
sz.302132

2025-02-10 ~ 2025-02-21
```

本诊断不要只使用项目目前 `FIELDS` 中的 close。

建议直接调用 SDK diagnostic fields：

```text
date,
code,
open,
high,
low,
close,
preclose,
volume,
amount,
adjustflag,
turn,
tradestatus,
isST
```

使用与当前项目一致的：

```text
frequency = d
adjustflag = 3
```

原始 provider rows必须保留到诊断 artifact。

回答：

```text
300114 最后一条返回日期？
302132 第一条返回日期？

300114 在 2025-02-17 是否还有 row？
302132 在 2025-02-14 是否已经有 row？
```

---

## 5.4 BaoStock｜长历史查询

这是本任务最关键的 BaoStock 测试。

分别查询：

```text
sz.300114
sz.302132
```

建议窗口：

```text
2010-08-27 ~ 2025-02-21
```

如果一次查询返回过大，可拆年/月，但不得改变 query identity。

必须回答：

### OLD query

`sz.300114`：

```text
first row
last row
row_count
```

### NEW query

`sz.302132`：

```text
first row
last row
row_count
```

核心问题：

> 查询 `sz.302132` 时，BaoStock 是否返回 2025-02-17 以前、甚至 2010 年起的历史行情？

如果是：

```text
NEW_CODE_QUERY_BACKFILLS_PRE_CHANGE_HISTORY = TRUE
```

如果不是：

```text
NEW_CODE_QUERY_STARTS_AT_EFFECTIVE_DATE = TRUE
```

这两种行为对 generic detector 的设计完全不同。

---

# 6. BaoStock OLD / NEW 历史重叠比较

如果两个 query 在 2025-02-17 之前存在相同日期：

逐日期比较：

```text
open
high
low
close
preclose
volume
amount
tradestatus
isST
```

输出：

```text
common_date_count
exact_business_field_match_count
mismatch_count
mismatch_samples
```

注意：

`code` 字段本身允许不同。

必须同时记录：

```text
query_code
provider_returned_code
```

检查 BaoStock 是否会：

```text
query 302132
但返回 code = 300114
```

或：

```text
query 302132
并将历史 code 统一返回成 302132
```

这是非常重要的 source semantics。

---

# 7. TDX ↔ BaoStock 交叉验证

生成冻结矩阵。

至少包括：

| Source | Query/File Code | 2025-02-14 | 2025-02-17 | Pre-change history visible under 302132? |
|---|---|---:|---:|---|
| TDX `.day` | 300114 | ? | ? | N/A |
| TDX `.day` | 302132 | ? | ? | ? |
| BaoStock history | 300114 | ? | ? | N/A |
| BaoStock history | 302132 | ? | ? | ? |
| BaoStock roster | 300114 | ? | ? | N/A |
| BaoStock roster | 302132 | ? | ? | N/A |

同时比较：

```text
2025-02-14
2025-02-17
```

TDX 与 BaoStock：

- OHLC
- volume
- amount

单位差异必须明确记录，不得因为单位差异误判 mismatch。

---

# 8. 强指纹测试

必须明确检验下面这些候选信号。

## F1｜OLD file terminates immediately before switch

```text
old_last_session = previous_market_session(effective_date)
```

本样本应测试：

```text
300114 last = 2025-02-14
effective = 2025-02-17
```

---

## F2｜NEW file contains pre-effective-date history

```text
new_file_first_date < effective_date
```

---

## F3｜OLD history == NEW history prefix

最强 TDX 信号：

```text
old_day_raw_records
==
prefix(new_day_raw_records)
```

或者达到极高一致率。

必须给：

```text
record_count_old
common_prefix_records
common_prefix_ratio
exact_raw_overlap_ratio
```

---

## F4｜Roster atomic flip

BaoStock：

```text
previous session: old present / new absent
effective session: old absent / new present
```

---

## F5｜Provider metadata continuity

例如：

- ipoDate continuity
- company/name continuity

只能作为辅助 signal。

---

## F6｜No overlapping dual trading

确认切换附近不存在：

```text
old_code ACTUAL_TRADED
AND
new_code ACTUAL_TRADED
```

同一交易日同时出现。

若出现，必须 BLOCK candidate auto-link。

---

## F7｜Historical price continuity

检查：

```text
old 2025-02-14 close
new 2025-02-17 preclose
```

是否有合理的 corporate-action / reference relationship。

只能记录，不可单独作为 SAME_ENTITY 证据。

---

# 9. 非常重要：不要只检查两天

`2025-02-14 / 2025-02-17`

是切换边界。

但为了判断 source fingerprint，必须同时比较：

```text
完整 OLD file vs NEW file
或
足够长的历史重叠区间
```

否则无法发现“302132 本地文件已经把 300114 全历史搬过来”这个最重要的特征。

---

# 10. 结果分类

实验最终必须落入以下类型之一。

## Pattern A｜强 alias migration fingerprint

例如：

```text
TDX:
300114 ends 2025-02-14
302132 contains full pre-change history
OLD raw file == NEW prefix

BaoStock:
roster 02-14 old-only
roster 02-17 new-only
new query also exposes historical continuity
```

结论：

```text
STRONG_GENERIC_ALIAS_CANDIDATE_SIGNAL
```

可用于后续 generic discovery。

仍需独立正式 evidence 作为 SAME_ENTITY confirmation，至少在第一版规则中如此。

---

## Pattern B｜TDX backfill，但 BaoStock split

例如：

```text
TDX new code has full old history
BaoStock old/new history按代码切开
BaoStock roster原子切换
```

结论：

```text
TDX_HISTORY_BACKFILL
+
BAOSTOCK_ROSTER_SWITCH
```

组合成高质量 candidate signal。

---

## Pattern C｜两边都按代码切开

结论：

只能依赖：

- roster adjacency
- issuer/name metadata
- official event
- other generic signal

不能靠历史 prefix。

---

## Pattern D｜源之间矛盾

例如：

- 双代码同日交易；
- 日期不一致；
- old/new history overlap mismatch严重；
- provider metadata不连续。

结论：

```text
UNRESOLVED_IDENTITY_RELATION
```

fail closed。

---

# 11. 不允许做的事情

本任务严格禁止：

- 修改 `security_entity_map_R7`
- 修改 Historical Universe
- 修改 dated alias fact
- 修改 R8.3 canonical logic
- 修改 V4-02
- 修改 V4-03
- 新建 Accepted Head
- 把 300114/302132 特判加入 production runtime
- 因为这个单一样本就宣称通用规则已经成立
- 用当前 TDX 302132 全历史回填结果当历史 PIT identity 事实

这是 source-behavior study。

---

# 12. 代码实现要求

建议新增单一诊断脚本：

```text
scripts/diagnose_v4_01_code_change_source_fingerprint.py
```

参数必须通用：

```text
--old-code SZ.300114
--new-code SZ.302132
--effective-date 2025-02-17
--previous-session 2025-02-14
```

禁止在核心算法里硬编码这两个代码。

测试脚本可以以本样本作为 fixture。

---

# 13. 输出产物

建议：

```text
reports/v4_01/
V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_300114_302132_R1.json

docs/audits/
V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_300114_302132_R1.md
```

JSON 至少包含：

```text
TDX:
  paths
  file hashes
  first/last dates
  record counts
  switch window rows
  overlap count
  exact raw overlap count
  longest common raw prefix
  mismatch samples
  current TNF presence

BaoStock:
  package/runtime identity
  query_stock_basic raw rows
  02-14 roster presence
  02-17 roster presence
  old daily query summary
  new daily query summary
  long-history boundaries
  overlap stats
  provider returned-code behavior

CrossSource:
  switch matrix
  OHLCV comparisons
  unit notes

Conclusion:
  detected_signals
  contradictions
  pattern_class
  candidate_signal_strength
  production_change_authorized = false
```

---

# 14. 最终报告必须回答

Codex 最后不要只说“发现相似”。

必须明确回答：

1. 本地是否同时有 `sz300114.day` 和 `sz302132.day`？
2. `300114.day` 最后日期是什么？
3. `302132.day` 第一日期是什么？
4. `302132.day` 是否包含 2025-02-17 以前历史？
5. 两文件共有多少日期？
6. 共有日期中多少 raw 32-byte record 完全相同？
7. `300114.day` 是否等于 `302132.day` 的完整历史前缀？
8. BaoStock `query_all_stock(2025-02-14)` 两代码出现情况？
9. BaoStock `query_all_stock(2025-02-17)` 两代码出现情况？
10. BaoStock 查 `sz.302132` 是否返回 2025-02-17 以前历史？
11. BaoStock 查旧代码是否仍返回旧历史？
12. BaoStock old/new 重叠行情是否一致？
13. BaoStock 返回 row.code 是 query code 还是历史 alias code？
14. 两套数据源是否共同形成稳定 alias-migration fingerprint？
15. 当前结果只够产生 candidate，还是已经足以建议新的 confirmation contract？
16. 是否发现任何反例/矛盾？

---

# 15. 下一步条件

本实验完成之前：

```text
V4_01_IDENTITY_GENERIC_MERGE_RULE =
DO_NOT_CHANGE
```

如果得到 Pattern A/B：

下一任务才是：

```text
设计 generic source-fingerprint candidate detector
+
用至少多个已知代码变更样本做盲测
```

不是立即 merge。

如果得到 Pattern C/D：

保留现有 R8.3 evidence-policy 路线，并重新评估 official-event completeness gate。

---

# 16. 当前研究假设

本轮只允许检验，不允许预设为真：

```text
H1:
TDX 新代码 .day 文件可能携带旧代码完整历史，
形成 raw-record prefix fingerprint。

H2:
BaoStock dated roster 可能在相邻交易日表现为 old→new 原子切换。

H3:
BaoStock new-code history query 可能回填旧代码时期行情。

H4:
H1/H2/H3 的组合可能比“代码格式猜测”更适合作为 generic
identity-relation candidate discovery signal。
```

任何 H 都必须由真实输出支持后才保留。
