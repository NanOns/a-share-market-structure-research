# V4-01 代码变更源级指纹诊断｜独立验收结论

- 日期：2026-09-29
- 仓库：`NanOns/a-share-market-structure-research`
- 分支：`codex/v4-system-reform`
- 当前 HEAD：`d18bdc13607fb1443509208863c8edc5135bc43c`
- 提交：`Add V4-01 code-change source fingerprint diagnostic`
- 样本：`SZ.300114 → SZ.302132`
- 已知代码切换日：`2025-02-17`
- 验收范围：TDX 本地 `.day`、当前 TDX master、BaoStock `query_stock_basic`、`query_all_stock(day)`、`query_history_k_data_plus`、跨源指纹、诊断脚本边界。
- 本轮仅验诊断实验；不授权修改 production identity。

---

# 1. 总结论

```text
DIAGNOSTIC_EXECUTION = PASS

SOURCE_DATA_CAPTURE = PASS

PRODUCTION_BOUNDARY = PASS

CODEX_PATTERN_CLASSIFICATION = FAIL

CODEX_FINAL_INTERPRETATION = FAIL

OVERALL =
PASS_WITH_CONCLUSION_CORRECTION_REQUIRED
```

这次 Codex **把真实数据抓对了，也基本按照任务卡完整回答了问题**，但最终把结果归类为：

```text
PATTERN_D_UNRESOLVED_IDENTITY_RELATION
candidate_signal_strength = BLOCKED_FAIL_CLOSED
```

这个结论不成立。

更合理的外部判断是：

```text
STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT

candidate_strength =
STRONG_GENERIC_IDENTITY_RELATION_CANDIDATE

auto_merge_allowed =
NO

independent_confirmation_still_required =
YES
```

也就是说：

> 这个实验不是证明“无法识别”，反而非常强地证明了 TDX 和 BaoStock 都在以“新旧代码别名共享/继承同一历史”的方式暴露数据。

但单一样本仍不足以直接制定自动 SAME_ENTITY merge 规则。

---

# 2. 提交范围验收

本提交只有：

- 诊断脚本；
- 大型冻结 JSON；
- Markdown 诊断报告；
- BaoStock request ledger 增量。

没有修改：

- `security_entity_map_R7`
- Historical Universe
- dated alias
- V4-02 artifacts
- V4-03 artifacts
- Accepted Head
- production identity runtime

因此：

```text
READ_ONLY_DIAGNOSTIC_BOUNDARY = PASS
```

TDX source hash 前后不变：

```text
tdx_root_write_count = 0
tdx_sources_unchanged = true
```

BaoStock：

```text
PUBLIC_ANONYMOUS
package = 0.9.3
request_count_delta = 10
query_failures = []
```

数据采集可信。

---

# 3. TDX｜真实结果比 Codex 的 Pattern D 更强

## 3.1 文件边界

### 旧代码

```text
SZ.300114
first = 2010-08-27
last  = 2025-02-14
records = 3421
```

### 新代码

```text
SZ.302132
first = 2010-08-27
last  = 2026-09-24
records = 3816
```

因此：

```text
F1 old file ends previous market session = TRUE
F2 new file contains full pre-effective history = TRUE
```

这是非常强的 alias migration 特征。

---

# 4. “raw prefix 不完全相同”被过度解读

Codex 报告：

```text
common dates = 3421
raw exact = 2976
raw mismatch = 445
full raw prefix = FALSE
```

表面看似不够强，但拆开字段后完全不同。

`mismatch_field_counts`：

```text
reserved = 445
volume   = 54
```

没有：

```text
open mismatch
high mismatch
low mismatch
close mismatch
amount mismatch
```

也就是说：

> **3421 个共同交易日里，OHLC 和 amount 全部一致。**

445 个 raw mismatch 主要由 `.day` 结构里的：

```text
reserved
```

造成。

例如 2025-02-14：

```text
300114 reserved = 65536
302132 reserved = 0
```

但：

```text
open   = 71.89
high   = 73.98
low    = 71.07
close  = 72.18
amount = 1181995904
volume = 16359576
```

全部业务行情一致。

因此：

```text
RAW_32_BYTE_PREFIX != exact
```

不能解释成：

```text
market_history != same
```

`reserved` 是非行情业务字段。

## 4.1 TDX 更合理的结论

从数据支持：

```text
TDX_NEW_CODE_BACKFILLS_OLD_HISTORY = TRUE

TDX_OVERLAPPING_OHLC_AMOUNT_EQUIVALENCE = 100%

TDX_VOLUME_EXACT_MATCH =
3367 / 3421
≈ 98.42%
```

且 volume 只有 54 日存在差异。

样本中可见的 volume 差异通常很小，但当前冻结 JSON 没保存全部 54 日 delta 分布，因此不能进一步断言全部都在某个固定容差内。

正确结论应是：

```text
TDX_STRONG_SEMANTIC_HISTORY_CONTINUITY
```

而不是因为 raw bytes 不是完整 prefix 就弱化成 unresolved。

---

# 5. BaoStock｜新代码明显回填旧代码历史

## 5.1 stock_basic

旧代码：

```text
code      = sz.300114
code_name = 中航电测
ipoDate   = 2010-08-27
outDate   = 2025-02-17
status    = 0
```

新代码：

```text
code      = sz.302132
code_name = 中航成飞
ipoDate   = 2010-08-27
outDate   = ""
status    = 1
```

非常重要：

```text
old.ipoDate == new.ipoDate == 2010-08-27
```

新代码没有把 IPO date 设为 2025-02-17。

这说明 BaoStock 的生命周期模型本身就在表达：

> 新代码继承原上市实体的历史生命周期。

这不是单纯两个独立上市对象的典型表现。

---

# 6. BaoStock 新代码查询确实能看到旧历史

`query_history_k_data_plus("sz.302132")`：

```text
first_date = 2010-08-27
pre_effective_history_visible = true
```

并且 provider 返回行中的：

```text
code = sz.302132
```

即 BaoStock 会把 2010~2025-02-14 的历史：

**重新标记为新代码 302132 返回。**

旧代码查询：

```text
first_date = 2010-08-27
last_date  = 2025-02-17
```

所以在 BaoStock 中：

```text
同一历史同时可由 OLD alias 查询
同一历史也可由 NEW alias 查询
```

这是非常强的：

```text
PROVIDER_ALIAS_BACKFILL
```

---

# 7. 3510 个 BaoStock overlap 被错误解释成“81 个矛盾”

Codex 报告：

```text
common dates = 3510
exact = 3429
mismatch = 81
```

但 81 个 mismatch 细分为：

```text
79 = SUSPENDED_BLANK_VS_ZERO_ONLY
1  = ACTUAL_BAR_VALUE_DIFF
1  = TRADING_STATUS_DIFF
```

## 7.1 79 个 suspended mismatch

只是：

```text
old query: volume=0 amount=0
new query: volume="" amount=""
```

或反向。

这种属于 provider representation difference。

不是证券 identity contradiction。

## 7.2 唯一 ACTUAL_BAR_VALUE_DIFF

日期：

```text
2019-02-20
```

实际差异只有：

```text
amount:
old = 63016557.4800
new = 63016557.0000
```

差：

```text
0.48 CNY
```

OHLC、volume、status 并没有差异。

这明显更接近数值格式/精度差异，不足以否定历史等价。

## 7.3 唯一 TRADING_STATUS_DIFF

日期：

```text
2025-02-17
```

旧代码：

```text
tradestatus = 0
OHLCV blank
```

新代码：

```text
tradestatus = 1
close = 68.01
```

这恰好就是代码正式切换日。

这是**边界切换证据**，不是异常。

## 7.4 正确的 normalized overlap

在 effective date 之前共有：

```text
3509 个共同历史日期
```

其中：

- 3429 日严格完全一致；
- 79 日只是停牌空值 vs 0；
- 1 日成交额差 0.48 元。

因此在合理语义归一化后：

```text
pre-effective semantic equivalence
≈ 3509 / 3509
```

接近完整一致。

这个证据极强。

---

# 8. 最大的解释错误：把 alias duplication 当成“双代码同时交易”

Codex 将 2025-02-14 判为：

```text
OVERLAPPING_DUAL_ACTUAL_TRADING
```

因为：

- `query_all_stock(2025-02-14)` 同时返回 300114 / 302132；
- 对两个代码分别查询 history；
- 两个 query 都返回 `tradestatus=1`。

但原始行情是：

### old query

```text
code = sz.300114
date = 2025-02-14
open = 71.89
high = 73.98
low = 71.07
close = 72.18
volume = 16359576
amount = 1181995873.47
```

### new query

```text
code = sz.302132
date = 2025-02-14
open = 71.89
high = 73.98
low = 71.07
close = 72.18
volume = 16359576
amount = 1181995873.47
```

业务字段**完全一致**。

这更合理的解释是：

```text
BAOSTOCK_ALIAS_DUPLICATION_OF_ONE_HISTORICAL_BAR
```

而不是：

```text
TWO_DISTINCT_SECURITIES_BOTH_TRADED
```

尤其还同时存在：

```text
same IPO date
old outDate = effective date
new status active
new alias backfills old history
TDX new file backfills old history
```

综合后，所谓“dual actual trading”恰恰更像 provider alias virtualization。

---

# 9. query_all_stock 不能再直接解释成唯一历史代码 roster

当前结果证明：

```text
2025-02-14:
300114 present
302132 present

2025-02-17:
300114 present
302132 present
```

但 2025-02-17：

```text
300114 tradeStatus = 0
302132 tradeStatus = 1
```

因此 BaoStock：

```text
query_all_stock(day)
```

对发生代码变更的证券可能保留多个 alias。

它不能简单解释为：

```text
每个返回 code = 一个独立历史证券实体
```

这是对 V4-01 非常有价值的新事实。

如果系统历史 Universe 直接按 code 去重、不先做 alias normalization，就可能重复计算同一实体。

---

# 10. TDX + BaoStock 联合指纹

这个样本实际给出了非常强的联合 fingerprint：

```text
TDX:
OLD file ends exactly on previous session
NEW file starts at original IPO history
NEW file contains OLD entire calendar history
OHLC/amount overlap = 100%
current master only keeps NEW code

BaoStock:
OLD and NEW ipoDate identical
OLD outDate = switch effective date
OLD status = inactive
NEW status = active
NEW query backfills entire OLD history
OLD/NEW pre-effective market history is semantically identical
effective date OLD becomes inactive row / NEW becomes actual trade
```

因此合理分类：

```text
STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT
```

而不是：

```text
PATTERN_D_UNRESOLVED_IDENTITY_RELATION
```

---

# 11. 但仍不能从一个样本直接自动 merge

这一点 Codex 的保守边界是正确的：

```text
candidate_auto_link_allowed = false
production_change_authorized = false
```

保留。

这个样本已经足以证明：

> 可以设计一个 generic candidate detector。

但还不足以证明：

> 某一套阈值在全市场不存在误合并。

所以正确下一步不是回到“继续穷举官方关键词”。

而是：

```text
MULTI-SAMPLE BLIND VALIDATION
```

---

# 12. 下一版 generic candidate detector 应研究的信号

建议先作为 candidate signals，不作为 final confirmation：

## G1

```text
old TDX file last session
==
session immediately before effective switch
```

## G2

```text
new TDX file contains long pre-effective history
```

## G3

TDX semantic overlap：

```text
OHLC exact
amount exact / source-format tolerance
volume high agreement
reserved ignored
```

不要再用完整 32-byte raw equality 作为必要条件。

## G4

BaoStock：

```text
old.ipoDate == new.ipoDate
```

## G5

```text
old.outDate ≈ effective_date
old.status = inactive
new.status = active
```

## G6

```text
new-code history query exposes pre-effective history
```

## G7

old/new pre-effective history：

```text
normalized semantic equivalence extremely high
```

需定义：

- suspended `0` vs blank normalization；
- amount source precision tolerance；
- volume tolerance必须先通过多样本研究再冻结。

## G8

Current TDX master：

```text
old absent
new present
```

---

# 13. 不应再使用的错误判断

### 错误 1

```text
raw bytes not 100% prefix
=> not strong alias signal
```

错误。

`reserved` 字段就足以破坏 byte equality。

### 错误 2

```text
query_all_stock 同时出现两个代码
=> 两只证券同时真实交易
```

错误。

这个样本已经证明 provider 会同时暴露旧/new alias。

### 错误 3

```text
old/new history query 都有同日实际 bar
=> identity contradiction
```

当两个 bar 业务字段完全一致、且伴随 alias backfill/lifecycle continuity 时，更可能是 provider alias virtualization。

### 错误 4

```text
任何 overlap mismatch > 0
=> Pattern D
```

错误。

必须先区分：

- representation difference
- precision difference
- boundary state difference
- substantive market-data difference

---

# 14. 对 V4-01 Gate A 的影响

本实验没有直接清除 V4-01 owner gate。

但它改变了我们应走的路径。

此前 Gate A 过度依赖：

```text
exhaustive official code-change event index
```

本实验说明存在更有希望的通用数据驱动 discovery：

```text
TDX historical alias fingerprint
+
BaoStock lifecycle / history alias fingerprint
+
official evidence for final confirmation
```

因此下一步应优先：

1. 选取多个已知代码变更样本；
2. 冻结真实旧/新代码与 effective date；
3. 盲测上述 fingerprint；
4. 同时加入 DISTINCT counterexamples；
5. 评估 false positive / false negative；
6. 再决定是否把它纳入 `SECURITY_IDENTITY_EVENT_LINKAGE` candidate generation。

---

# 15. 最终验收状态

```text
REMOTE_HEAD =
d18bdc13607fb1443509208863c8edc5135bc43c

DIAGNOSTIC_SCRIPT =
PASS_WITH_CLASSIFIER_DEFECT

DATA_CAPTURE =
PASS

TDX_FINDINGS =
PASS

BAOSTOCK_FINDINGS =
PASS

SOURCE_IMMUTABILITY =
PASS

PRODUCTION_MUTATION =
NONE

CODEX_PATTERN_D_CONCLUSION =
REJECTED

EXTERNAL_INTERPRETATION =
STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT

AUTO_MERGE =
NOT_AUTHORIZED

NEXT_STEP =
DESIGN_GENERIC_CANDIDATE_DETECTOR
AND BLIND_TEST_MULTIPLE_KNOWN_CODE_CHANGES
```

这次实验非常有价值。

它不是证明“这条路走不通”，反而证明了：

> TDX 和 BaoStock 本身都留下了非常明显的代码变更 alias fingerprint。

下一步应该验证它的泛化性，而不是继续把全部希望放在官方关键词穷举上。
