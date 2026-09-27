# 大A市场结构研究系统 V4｜V4-02 R6 最终外部验收结论

> 文档编号：DA-MSR-V4-02-R6-FINAL-EXTERNAL-ACCEPTANCE  
> 日期：2026-09-27  
> 审计仓库：`NanOns/a-share-market-structure-research`  
> 审计分支：`codex/v4-system-reform`  
> 当前 HEAD：`ef9c6a1c422642062715a19d78d65113c772f1bf`  
> R6 production wiring 提交：`aa3d68dcd027ce258e9cc5bb648ec99cf6d917a1`  
> R6 test/gate 提交：`14a8c4e7964db4834dbeb10ceb811552783d0cbd`  
> R6 seal 提交：`ef9c6a1c422642062715a19d78d65113c772f1bf`  
> 最高技术基线：`DA-MSR-V4.2.2-CODEX-REV2`  
> Required Scope：`SH_MAIN / SZ_MAIN / CHINEXT / STAR`  
> Optional Degraded Scope：`BSE`

---

# 1. 最终外部验收结论

```text
V4-02 REQUIRED SCOPE
= PASS

V4-02 BSE OPTIONAL SCOPE
= DEGRADED / EXCLUDED FROM REQUIRED SCOPE
= ACCEPTED BY USER SCOPE POLICY

V4-02 FINAL
= PASS_WITH_BSE_SCOPE_DEGRADED

V4-02
= EXTERNALLY_ACCEPTED

V4-03 ENTRY
= AUTHORIZED
```

本轮不再存在需要继续阻断 V4-02 的 P0。

---

# 2. R6 解决了最后一个真正问题

R5 已经具备：

```text
generic alias resolver
generic event store
generic phase policy
generic source capture
generic phase runtime
generic synthetic tests
```

但 R5 正式 artifact 仍然只是：

```text
generic phase recognition
+
copy R4 already-computed row
```

所以当时不能证明：

```text
generic production calculation
```

真正接入。

R6 已修正。

---

# 3. R6 正式生产链已经变成

```text
R3 pre-special Price Limit base
↓
DATED_SECURITY_ALIAS_V1
↓
SPECIAL_PRICE_PHASE_EVENT_V1
↓
SPECIAL_PRICE_PHASE_POLICY_V2
↓
resolve_event_phase()
↓
apply_phase_event()
↓
R6 Price Limit artifact
```

这已经是通用生产计算链，不再复制 R4 特殊阶段结果。

---

# 4. 正式 builder 确实调用通用 runtime

R6 production build：

```text
apply_phase_event_call_counts:

DELISTING_FIRST_DAY = 22
DELISTING_PERIOD = 308
IPO_FIRST_5_TRADING_DAYS = 1,648
UNKNOWN_SPECIAL_PHASE = 31
```

证明正式主链实际进入：

```text
apply_phase_event()
```

而不是只进行 phase compare。

---

# 5. 历史业务结果完全等价

R6 输出：

```text
row_count = 4,035,729
```

Independent postcheck：

```text
business_difference_rows = 0
business_payload_identical = true
business_digest_identical = true
phase_inventory_identical = true
unknown_reason_inventory_identical = true
limit_status_inventory_identical = true
```

R4 / R6 business digest：

```text
6fce7a228c7c4a2148d176ae8be8c90d64788c81707ed1ac60413c8f7264650b
```

完全一致。

---

# 6. R6 Price Limit 状态

```text
LIMIT_DOWN = 24,377
LIMIT_UP = 59,550
NOT_LIMIT = 3,940,937
NO_LIMIT = 1,670
SUSPENDED = 9,118
UNKNOWN = 77
```

UNKNOWN reason：

```text
CORPORATE_ACTION_REFERENCE_UNSUPPORTED = 38
REFERENCE_CHAIN_BLOCKED_BY_UNSUPPORTED_ACTION = 1
REFERENCE_STATE_UNAVAILABLE = 7
SPECIAL_PHASE_EVIDENCE_UNAVAILABLE = 21
SPECIAL_REFERENCE_PRICE_UNAVAILABLE = 10
```

这些都是已接受的 fail-closed / evidence-boundary 结果。

没有 undispositioned engineering exception。

---

# 7. Special Price Phase 正式库存

```text
REGULAR = 4,033,720

IPO_FIRST_5_TRADING_DAYS = 1,648

DELISTING_FIRST_DAY = 22

DELISTING_PERIOD = 308

UNKNOWN_SPECIAL_PHASE = 31
```

R6 与 R4 完全一致。

---

# 8. 通用性验收：通过

当前 generic runtime 不依赖具体股票代码。

生产路径扫描：

```text
src/workbench_analysis/**/*.py
scripts/build_v4_02*.py
```

没有：

```text
SZ.002087
SZ.000996
SZ.300114
SZ.302132
目标 SEC-ID
```

特判。

因此满足项目原则：

```text
股票是数据
规则是代码

事件是数据
状态机是代码
```

---

# 9. 一次性 migration 中存在具体股票是允许的

历史：

```text
300114 → 302132
```

修复脚本仍保留目标证券常量。

它属于：

```text
one-time historical migration / repair
```

不是：

```text
production resolver
production Price Limit builder
```

所以不构成 generic runtime blocker。

---

# 10. Generic Alias Resolver：正式通过

正式 resolver：

```text
DatedSecurityAliasResolver
```

输入：

```text
security_id
source_security_key
effective_from
effective_to
exchange
board
evidence
```

支持：

```text
resolve_alias
resolve_board
resolve_exchange
```

不按代码前缀猜历史 board。

---

# 11. Generic Special Phase Event：正式通过

正式事件：

```text
SPECIAL_PRICE_PHASE_EVENT_V1
```

支持：

```text
IPO_FIRST_5_TRADING_DAYS
DELISTING_FIRST_DAY
DELISTING_PERIOD
RELISTING_FIRST_DAY
SPECIAL_REFERENCE_RESET
UNKNOWN_SPECIAL_PHASE
```

生产计算依据：

```text
event facts
+
effective-dated policy
```

而不是证券代码。

---

# 12. Generic Source Capture：正式通过

当前：

```text
capture_special_phase_sources.py
```

已经 manifest-driven。

脚本只负责：

```text
allowlist
redirect control
size bound
content type
immutable capture
hash
receipt
```

证券和事件来自 manifest。

---

# 13. Policy Registry：正式通过

当前：

```text
SPECIAL_PRICE_PHASE_POLICY_R6
```

将：

```text
IPO duration
delisting duration
board ratio
tick
rounding
risk override
relisting
special reference reset
unknown phase behavior
```

数据化 / effective-dated。

因此未来制度变化原则上：

```text
改 contract / policy
而不是改个股算法
```

---

# 14. R6 Synthetic Production Integration：通过

正式测试覆盖：

```text
generic builder actually calls runtime

generic delisting first day

generic delisting period

generic relisting

generic special reference reset

generic unknown phase fail closed

builder does not trust precomputed R4 special output

generic alias validation
```

---

# 15. R6 Test Receipt

```text
31 passed
0 failed
0 skipped
```

测试 commit：

```text
14a8c4e7964db4834dbeb10ceb811552783d0cbd
```

Final seal 后没有新的业务 builder/runtime 修改。

接受。

---

# 16. “Narrow R6 production identifier audit scope” 审计结论

该提交只调整：

```text
scripts/seal_v4_02_final_receipt_r6.py
```

生产代码扫描范围。

最终扫描：

```text
src/workbench_analysis/**/*.py
scripts/build_v4_02*.py
```

这与当前定义相符：

```text
production runtime
+
production builders
```

一次性历史 migration / repair 脚本不作为“未来运行时通用性”扫描目标。

因此该修改不是绕过 genericity gate。

---

# 17. R6 Independent Postcheck：接受

独立脚本不是读取 Final Receipt 自证。

它重新逐行读取：

```text
R4 Price Limit
R6 Price Limit
```

比较：

```text
security_id
trade_date
special_price_phase
limit_status
reason
reference_price
limit_up_price
limit_down_price
rule_id
reference_basis
risk_status
is_st
```

结果：

```text
0 difference rows
```

接受。

---

# 18. V4-02 各能力最终状态

```text
RAW_CANONICAL_DAILY
= PASS

ADJUSTED_NUMERICAL_RECONSTRUCTION
= PASS_WITH_PER_SECURITY_FAIL_CLOSED

HISTORICAL_ADJUSTED_LINEAGE
= DIAGNOSTIC_NON_PIT / REPLAY
= NO FALSE PIT CLAIM

GO_FORWARD_GBBQ_PIT_CAPTURE
= ENABLED

FORMAL_MARKET_CALENDAR
= PASS

TRADING_STATUS
= PASS

DATED_ISST
= PASS

FORMAL_WEEKLY_MONTHLY
= PASS

CLOSED_ONLY
= PASS

AS_OF_PARTIAL
= PASS

SECTION_3C_4_TEMPORAL_LEAKAGE
= PASS

PRICE_LIMIT_RULE_V1
= PASS

SPECIAL_PRICE_PHASE_RUNTIME
= PASS

GENERIC_PRODUCTION_WIRING
= PASS

ATOMIC PUBLICATION / ACCEPTED HEAD
= PASS

INDEPENDENT FINAL POSTCHECK
= PASS
```

---

# 19. BSE

BSE 继续：

```text
OPTIONAL / DEGRADED
```

并与 Required Scope 隔离。

符合用户明确 scope policy。

不阻断 V4-02。

---

# 20. Accepted Head

当前：

```text
data/v4/V4_02_ACCEPTED_HEAD.json
```

已经指向：

```text
V4_02_FINAL_RECEIPT_R6.json
```

状态：

```text
PASS_WITH_BSE_SCOPE_DEGRADED
```

本次外部审计正式认可该 head。

---

# 21. V4-02 现在正式关闭

从本审计起：

```text
V4-02
= CLOSED
= EXTERNALLY_ACCEPTED
= PASS_WITH_BSE_SCOPE_DEGRADED
```

除出现新的可复核反证，否则不得继续：

```text
重做 Calendar
重拉 isST
重建 RAW
重新研究 22 个退市样本
继续打磨特殊股票个案
继续新增 V4-02 R7/R8...
```

---

# 22. 未来新特殊股票如何处理

以后第 23、第 100 只特殊股票：

正确流程：

```text
发现官方事件
↓
新增 SPECIAL_PRICE_PHASE_EVENT_V1 fact
↓
source capture
↓
generic resolver
↓
generic policy
↓
generic Price Limit runtime
```

不需要：

```text
新增 if code == xxx
修改 Price Limit 算法
为单只股票重新发版本
```

这就是本轮最终验收最重要的工程结果。

---

# 23. V4-03 正式授权

REV2 阶段表定义：

```text
V4-03
= Pure-Core Factors
```

主要范围：

```text
CORE_FACTOR_V1
市场 native primitives
sector native primitives
benchmark 基础价格路径
```

因此：

```text
V4-03 ENTRY = AUTHORIZED
```

---

# 24. V4-03 不得重新打开 V4-02

V4-03 直接消费：

```text
accepted V4-02 canonical data
accepted periods
accepted trading/limit status
accepted universe
```

不得重新：

```text
开发 Calendar
重写 Price Limit
重新定义复权链
重新修特殊股票
```

除非出现新的、可复核的下游反证。

---

# 25. 建议下一步

下一正式工程任务：

```text
V4-03 Pure-Core Factors
```

执行前只需要：

```text
读取 REV2 中 CORE_FACTOR_V1
+
Field → Algorithm Contract Registry
+
Technical/Cross-section window contract
```

然后形成 V4-03 implementation task。

不需要再为 V4-02 增加新任务。

---

# 26. 最终一句话

```text
V4-02 这次可以真正结束。

R6 已经补上最后一根线：
通用 runtime 不再只是“库里存在”，
而是真正进入正式 Price Limit production builder。

4,035,729 行重新生产，
22个退市首日、308个退市整理期、
1648个IPO无涨跌幅阶段、31个fail-closed
全部实际进入通用 runtime。

最终与已接受 R4 历史业务结果：
0 行差异。

同时核心 production runtime 不含具体股票特判。

因此正式结论：

V4-02
= PASS_WITH_BSE_SCOPE_DEGRADED
= EXTERNALLY_ACCEPTED
= CLOSED

V4-03
= AUTHORIZED_TO_START
```

**文档结束**
