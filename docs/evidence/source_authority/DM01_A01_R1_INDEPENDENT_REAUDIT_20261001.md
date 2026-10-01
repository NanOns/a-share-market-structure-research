# DM-01 A01 R1 独立复审｜2026-10-01

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**审计 HEAD：** `4e5284f74c5275e28d75985d1c3e60eaf96e4103`  
**主要实现提交：** `60e5c5eecbf0ef311397bff1ac6e7b6086bd4a77`

## 唯一总状态

```text
DM01_A01_ENGINEERING_ADAPTERS = KEEP_PASS_ENGINEERING_SCOPE
DM01_A01_REAL_SOURCE_ACCEPTANCE = BLOCKED_R2
WP_A01_EXTERNAL_ACCEPTANCE = NOT_GRANTED
V4_DATA_ACCEPTED_HEAD_PROMOTION = NOT_AUTHORIZED
REPAIR_REQUIRED = YES
```

本轮不是“9 个 adapter 全部失败”。9 个 target-session adapter 的工程实现、独立 component/cross-component postcheck、clean regression 可以保留。

真正需要打回的是 **Real Next Session source-authority / source-recovery 设计**。

---

# 1. 当前“BaoStock 9/28 缺数据”结论表述不成立

当前 evidence：

```text
BAOSTOCK_EXACT_TARGET_RUNTIME_ACCEPTANCE_MISSING
BAOSTOCK_TARGET_DAILY_ROSTER_STATUS_ST_AND_FACTOR_FREEZE_MISSING
runtime_live_smoke_request_count = 0
baostock_daily_artifacts = []
```

这只能证明：

> 仓库/本地没有 2026-09-28 已冻结的 BaoStock runtime acceptance 和 daily snapshot。

不能证明：

> BaoStock 服务端不提供 2026-09-28 数据。

仓库本轮甚至没有向 BaoStock 发起 2026-09-28 的历史查询。

BaoStock 官方 DailyUpdates 页面当前明确说明：

```text
获取指定日期A股、ETF的日K线数据，指定日期复权因子数据。
```

因此 failure reason 应从含混的“BaoStock 数据缺失”改成：

```text
LOCAL_ACCEPTED_FREEZE_MISSING
/
HISTORICAL_CATCHUP_PATH_NOT_AUTHORIZED_BY_CURRENT_CONTRACT
```

---

# 2. 根因：runtime acceptance 被错误绑成“目标日当天 smoke”

`scripts/accept_v4_dm01_baostock_runtime.py` 当前硬门：

```python
if local_now.date().isoformat() != args.target_date
    or local_now.time() < 15:00:
    return WAIT_MARKET_CLOSE
```

因此：

```text
2026-10-01
补跑
target = 2026-09-28
```

必然无法产生 runtime acceptance。

这不是 provider capability 失败，而是我们的合同把：

```text
运行时能力验证
```

错误耦合到：

```text
目标交易日当天
```

---

# 3. 根因二：BaoStock supplemental 被提升成 DM-01 全局硬门

当前主合同及 BaoStock contract 明确：

```text
TDX = Core authority
BaoStock = supplemental / cross-check

BaoStock supplemental failure:
does_not_block_or_invalidate_accepted_core_publication = true

core_flow_waits_for_supplement = false
```

但当前 DM-01 实现：

```text
_context()
→ requires source_freeze_complete_v2

source freeze
→ requires BAOSTOCK_DAILY_UPDATE

build_identity_universe()
→ hard reads BAOSTOCK_DAILY_UPDATE

build_trading_status()
→ hard reads BaoStock

build_isst()
→ hard reads BaoStock
```

结果变成：

```text
BaoStock snapshot 不存在
→ 9 components 全部不能形成 real atomic candidate
```

这与冻结的 source-authority 边界不一致。

---

# 4. 正确的补抓语义

允许在 2026-10-01 查询 BaoStock 的 2026-09-28 指定日期数据，但必须明确：

```text
provider_date = 2026-09-28
target_trade_date = 2026-09-28

observed_at = 实际补抓时间
received_at = 实际补抓时间

origin = DELAYED_HISTORICAL_RETRIEVAL
```

禁止把补抓数据伪装成：

```text
2026-09-28 当天已观察
AS_RECORDED_AT_2026_09_28_CLOSE
first_available_at = 2026-09-28
```

这是“延迟取得的历史指定日期数据”，不是回写历史知识时间。

---

# 5. runtime acceptance 应与 target data capture 分离

应拆成两个版本化合同：

```text
A. Runtime Capability Acceptance
   SDK/auth/endpoint/method/schema capability
   不绑定某一个交易日

B. Target-Date Capture
   query_daily_history_k_AStock(date=T)
   query_daily_adjust_factor(date=T)
   返回 T 的 provider rows
```

Runtime acceptance 可通过一个可查询的已完成日期进行 bounded smoke。

之后对任意允许 catch-up 的目标日：

```text
使用同一 accepted runtime capability
+
exact target date query
```

不应要求：

```text
live_smoke.target_date == target_trade_date
```

---

# 6. BaoStock 对 Core 的正确 gate

必须拆成：

```text
CORE_REQUIRED_SOURCE_FAMILIES
SUPPLEMENTAL_SOURCE_FAMILIES
```

Core required：

```text
TDX package/delta
official calendar
accepted identity/lifecycle authority
GBBQ / adjustment authority
special-phase authority
```

BaoStock：

```text
status cross-check
isST cross-check
supplemental factor audit
```

若 BaoStock 当日/补抓失败：

```text
supplement_quality = UNAVAILABLE
crosscheck = UNKNOWN
```

但只要本地正式 authority 足够：

```text
不得阻断 RAW_DAILY
不得阻断 ADJUSTED_DAILY
不得阻断 Core Data Head
```

若某个字段确实缺本地 accepted authority，只阻断该字段/能力，不得把全 9 components 一刀切。

---

# 7. 9 个 adapter 工程实现裁决

当前工程证据：

```text
1247 passed
2 skipped
0 failures
0 errors
```

9 个 adapter 的 synthetic/engineering contract、postcheck 和 atomic failure mechanics 已建立。

因此：

```text
ENGINEERING_ADAPTER_IMPLEMENTATION = KEEP_PASS
```

但不能提升为：

```text
REAL_MARKET_ACCEPTED
```

因为 real-source path 尚未按正确 authority/catch-up 语义跑通。

---

# 8. Real Next Session 当前裁决

目标：

```text
2026-09-28
```

本轮已经具备：

```text
TDX 2026-09-28 official frozen package = PASS
GBBQ target-eligible frozen snapshot = PASS
calendar = PASS
```

当前 BaoStock 应归类为：

```text
local accepted freeze missing
+
catch-up contract blocked by design
```

而不是：

```text
provider confirmed unavailable
```

`BLOCKED_MISSING_INTERMEDIATE_SESSION` 可以继续作为“不允许跨过 9/28”的 Data Head 门，但 failure classification 必须修订。

---

# 9. 最终结论

```text
A01 不关闭
Data Head 不推进
9 adapters 不推倒重写
Source Authority / BaoStock Catch-up / Supplemental Gate 必须 R2 修复
```

R2 通过后必须真正：

```text
query 2026-09-28
→ freeze with delayed-observation lineage
→ run real all-nine candidate
→ independent postcheck
→ external acceptance
→ separate Data Head promotion
```
