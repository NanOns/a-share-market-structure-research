# V4-01 Source Fingerprint Candidate Blind Study｜独立验收 R1

- 日期：2026-09-29
- 仓库：`NanOns/a-share-market-structure-research`
- 分支：`codex/v4-system-reform`
- 当前 HEAD：`d1fe4e6e2b44457b9cc58104b7ecc7575fd3a2bf`
- 提交：`[V4-01] Add source fingerprint candidate blind study`
- 审计范围：上一轮 source-fingerprint 解释修正、多样本冻结、candidate detector、label-separated evaluator、测试、官方标签证据、生产边界。
- 不包含：V4-01 owner gate 最终接受、production identity mutation、Historical Universe 重建。

---

# 1. 最终裁决

```text
SOURCE_FINGERPRINT_CORRECTION = PASS
GENERIC_CANDIDATE_DETECTOR = PASS_RESEARCH_ONLY
BOUNDED_BLIND_VALIDATION = PASS
LABEL_EVIDENCE = PASS
PRODUCTION_BOUNDARY = PASS
V4_01_OWNER_GATE = STILL_BLOCKED
V4_01_FULL_PASS = NOT_GRANTED
```

本轮 Codex 正确修复了上一轮的主要解释错误，并完成了一个有限但有效的 2 正 + 2 负标签分离验证。

仓库自报：

```text
PASS_BOUNDED_BLIND_VALIDATION
TP=2
FN=0
FP=0
TN=2
```

本次外部审计接受这个有限范围结论。

但不能把它升级为：

```text
GENERIC_RULE_PROVEN
SAME_ENTITY_CONFIRMATION_CONTRACT
V4_01_GATE_A_PASS
V4_01_FULL_PASS
```

---

# 2. 上一轮解释错误是否修正

**PASS**

`300114 → 302132` 不再被 candidate detector 判为：

```text
PATTERN_D_UNRESOLVED_IDENTITY_RELATION
```

而是：

```text
STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE
```

新 detector 正确处理：

- `reserved` 不参与 TDX 业务行情连续性 veto；
- raw 32-byte prefix 不再作为必要条件；
- 停牌时 volume/amount `0` vs blank 可按限定规则归一；
- 完全相同的 old/new BaoStock actual bar 被识别为 alias duplication；
- 只有实际业务字段不同的双边 actual bar 才触发 substantive conflict；
- amount 非等值仍严格保留，不使用隐性金额容差。

---

# 3. Generic detector 是否存在证券特判

**PASS**

`src/v4_01/source_fingerprint_candidate.py`：

- 以 `old_code/new_code/effective_date` 参数化；
- 未发现 `300114/302132/000022/...` 等样本代码分支；
- 不读取旧 diagnostic classifier 结论；
- 不读取 label 文件；
- 输出永远：
  - `candidate_auto_link_allowed = false`
  - `production_identity_mutation_authorized = false`
  - `owner_gate_cleared = false`

因此当前 detector 是研究型候选器，不是隐式 production merge rule。

---

# 4. 盲测流程

## 4.1 程序执行顺序

**PASS**

`validate_v4_01_source_fingerprint_candidates.py` 明确：

1. 读取 case manifest；
2. 加载冻结 diagnostic inputs；
3. 对全部 case 先运行 `analyze_source_fingerprint()`；
4. 将 predictions 冻结在内存；
5. **之后才读取 label file**；
6. 计算 TP/FN/FP/TN。

因此：

```text
labels_used_by_detector = false
detector_function_called_before_label_file_open = true
```

程序意义上的 label separation 成立。

## 4.2 但不是严格外部双盲

Codex 自己也正确披露：

```text
independent_external_reviewer_blinding = false
```

样本挑选、候选规则设计、阈值设定仍来自同一开发流程。

所以准确理解是：

```text
BOUNDED LABEL-SEPARATED VALIDATION
```

而不是可以估算泛化误报率的独立 blind benchmark。

---

# 5. 样本标签独立核验

## BLIND-01：300114 → 302132

**正样本标签 PASS**

既有深圳交易所正式代码变更公告支持 same listed entity code change。

## BLIND-02：000022 → 001872

**正样本标签 PASS**

官方公告明确：

- 证券代码 `000022/200022 → 001872/201872`；
- 2018-12-26 启用；
- 公司法人主体存续；
- 上市主体没有发生实质变化；
- 旧代码信息、权利义务平移至新代码；
- T-1 股份在 T 日直接变更为新代码；
- 投资者持有股份数量不变。

因此作为“same listed entity security code renumbering”正样本合理。

## BLIND-03：000024 → 001979

**负样本标签 PASS**

官方年报明确：

- 招商蛇口发行股份；
- 吸收合并招商地产；
- 招商地产 A 股终止上市；
- 招商蛇口 `001979` 于 2015-12-30 上市。

属于 merger-successor，不是纯 same-entity code renumbering。

## BLIND-04：000562 → 000166

**负样本标签 PASS**

官方上市公告明确：

- 申万宏源发行股份换股吸收合并宏源证券；
- `000562` 终止上市；
- 按换股比例转换为 `000166`；
- `000166` 作为申万宏源上市。

因此负样本合理。

---

# 6. 四案结果

```text
BLIND-01  300114→302132  POSITIVE -> POSITIVE
BLIND-02  000022→001872  POSITIVE -> POSITIVE
BLIND-03  000024→001979  NEGATIVE -> NEGATIVE
BLIND-04  000562→000166  NEGATIVE -> NEGATIVE
```

因此：

```text
TP=2
FN=0
FP=0
TN=2
```

这个结果真实存在，不是 label 直接驱动 detector。

---

# 7. 阈值审计

当前：

```text
minimum_shared_sessions = 20
tdx_volume_exact_ratio_minimum = 0.95
baostock_active_exact_ratio_minimum = 0.99
```

本轮判断：

```text
ALLOWED_AS_RESEARCH_THRESHOLD
NOT_ACCEPTED_AS_PRODUCTION_THRESHOLD
```

原因：

- 只有一个正样本具备 old/new TDX pair；
- `0.95` volume threshold 实际主要由一个样本支撑；
- 两个正样本均为深市；
- 没有 SH_MAIN / STAR 正样本；
- 只有两类 merger-successor negative controls；
- 尚未覆盖更困难的 distinct-issuer / code-reuse / same-IPO-like metadata counterexamples。

Codex 已在 calibration audit 中把该项保持 OPEN，这个处理正确。

---

# 8. 发现的 P1 语义残留

`scripts/diagnose_v4_01_code_change_source_fingerprint.py` 中仍存在：

```text
F6_no_overlapping_dual_actual_trading
```

当前赋值：

```python
not (dual_trade_days or identical_provider_alias_bar_days)
```

这意味着：

当只有**完全相同的 provider alias duplicate bar**时，

```text
F6_no_overlapping_dual_actual_trading = false
```

但新合同已经明确：

```text
identical_dual_actual_bars =
ALIAS_DUPLICATION_SIGNAL_NOT_A_CONTRADICTION
```

所以 F6 名称和计算语义已经不一致。

这目前不影响 generic detector，因为 detector 独立计算：

```text
duplicate_identical_bar_days
substantive_dual_trade_days
```

并只把 substantive conflict 当 veto。

但后续人工读报告或其他脚本如果继续使用旧 F6，会再次产生误解。

建议改成：

```text
F6_no_substantive_dual_actual_trading =
not dual_trade_days
```

另保留：

```text
F6_identical_provider_alias_bar_dates
```

这是 **P1 cleanup**，不是当前 bounded study 的 blocker。

---

# 9. 测试覆盖

当前新增测试：

1. 四个冻结样本输出；
2. `reserved` / identical dual bar 不 veto；
3. empty old TDX 不被误认为 full prefix。

这些测试有价值，但仍缺少 synthetic boundary tests：

- substantive different dual actual bar -> conflict；
- 0.99 下/上边界；
- 0.95 volume 下/上边界；
- suspended blank/zero normalization；
- provider returned code mismatch；
- duplicate-date fail-closed；
- query incomplete；
- same IPO metadata alone不能产候选。

因此：

```text
CURRENT_TESTS = SUFFICIENT_FOR_BOUNDED_STUDY
NOT_SUFFICIENT_FOR_PRODUCTION_RULE_ACCEPTANCE
```

---

# 10. GitHub 外部执行状态

当前 HEAD：

```text
commit status checks = 0
workflow runs = 0
```

没有 GitHub CI 独立运行证据。

因此：

```text
SOURCE TESTS PRESENT = PASS
REPO-REPORTED STUDY RECEIPT = PRESENT
EXTERNAL_CURRENT-HEAD_TEST_EXECUTION = NOT_VERIFIED
```

不影响本轮 bounded research acceptance，但生产化前必须补。

---

# 11. 对 V4-01 Gate A 的影响

当前 owner receipt 仍：

```text
identity_discovery = PASS
independent_algorithm_postcheck = PASS
official_event_index_coverage = BLOCKED
owner_gate = BLOCKED
status = BLOCKED
```

且：

```text
V4_STAGE_ACCEPTED_HEAD
v4_01_external_acceptance = PENDING_EXTERNAL_REVIEW
```

本轮没有修改 canonical identity 或 accepted head，这一点正确。

因此：

```text
V4_01_FULL_PASS = NO
```

但 source-fingerprint 路线已经从“单样本猜想”升级为：

```text
BOUNDED MULTI-SAMPLE EVIDENCE
```

下一步有资格继续扩展，而不是退回旧 classifier。

---

# 12. 下一步最小要求

下一轮不应重新做 300114/302132。

只需要：

## A. 修 F6 语义残留

小修，不重跑 production。

## B. 扩展样本集

至少：

- 再增加 ≥2 个拥有 old/new TDX pair 的纯代码变更正样本；
- 尽量覆盖 SH_MAIN / STAR；
- 增加 harder negatives：
  - code reuse；
  - 不同实体但历史/名称相似；
  - merger 后 provider 可能回填部分历史；
  - same IPO-like metadata 但非 same listed entity。

## C. 冻结 detector v1.0，不边看新样本边调阈值

更好的验证方式：

```text
当前 v1.0 参数冻结
→ 跑新增样本
→ 先记录 FP/FN
→ 再决定是否产生 v1.1
```

不能每加入一个样本就调参数直到全对，否则会过拟合。

## D. 增加 synthetic contract tests

覆盖上述 boundary/fail-closed cases。

---

# 13. 最终状态

```text
REMOTE_HEAD =
d1fe4e6e2b44457b9cc58104b7ecc7575fd3a2bf

SOURCE_FINGERPRINT_R2_CORRECTION = PASS

FOUR_CASE_BOUNDED_VALIDATION =
PASS_BOUNDED_BLIND_VALIDATION

LABEL_TRUTH =
PASS

GENERIC_CANDIDATE_DETECTOR =
RESEARCH_PASS

PRODUCTION_AUTO_LINK =
PROHIBITED

V4_01_OWNER_GATE =
BLOCKED

V4_01_FULL_PASS =
NOT_GRANTED

OPEN_ITEMS =
1. SOURCE_FINGERPRINT_CALIBRATION
2. OFFICIAL_EVENT_INDEX / ALTERNATIVE COMPLETENESS GATE
3. F6 semantic cleanup
4. broader frozen validation set
```
