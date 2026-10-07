# P0-4｜V4 Production Authority + Daily Refresh 任务卡 R1｜2026-10-07

- Priority: P0
- Depends on: P0-1/P0-2/P0-3

## 1. 目标

正式建立 V4 **产品版本 / 当前已接受研究读取** runtime authority。

注意：

> 本轮“生产版本切换”首先指默认软件版本、默认 UI、日常 accepted-data reader 进入 V4。

它**不能**绕过 V4-19 对 capability production permission 的证据门。

因此必须把两类 authority 分离：

```text
PRODUCT_VERSION_AUTHORITY = V4
CAPABILITY_PRODUCTION_PERMISSION = V4-19 exact receipts
```

它不自动等于：

```text
Forward effectiveness validated
real Shadow sample exists
auto trading
Focus mutation
```

---

## 2. 新 production authority

创建：

```text
config/v4_production_runtime_authority_v1.json
```

至少包含：

```text
contract_id
version
mode = V4_DEFAULT_PRODUCT
product_version = V4
default_ui = V4
read_authority
data_head_binding
stage_authority_binding
last_accepted_trade_date
daily_refresh_contract
rollback_binding
legacy_default = false
shadow_diagnostics = true
ui_read_only = true
trading_action_authorized = false
tdx_write_authorized = false
```

不得直接修改历史 accepted head 的旧 bytes 来伪造 production。

如需升级 stage authority，创建 successor：

```text
config/v4_current_stage_authority_v3.json
```

旧 v2 保留。

---

## 3. Production scope

正式授权：

```text
V4_CURRENT_ACCEPTED_READ = true
V4_DEFAULT_UI = true
V4_DAILY_PIPELINE = true
V4_INTERNAL_PRODUCTION_STORE_WRITE = true
```

仍然：

```text
TDX_WRITE = false
UI_WRITE = false
AUTO_TRADE = false
FOCUS_MEMBERSHIP_WRITE = false
```

---

## 4. 日更语义

daily refresh 必须：

1. 判断是否存在新的**已完成交易日**输入；
2. 只有数据采集与 owner gates 成功才生成 candidate；
3. candidate 通过 acceptance gate 后再原子更新 current production pointer；
4. 失败时保留上一次 accepted head；
5. UI 显示 last accepted + freshness；
6. 不因失败/休市/未来日期把 production pointer 清空。

---

## 5. 没有下一交易日数据

这是必须单独测试的生产场景。

输入：

```text
accepted_trade_date = 2026-09-30
no newer accepted daily input
```

期望：

```text
production service = READY
production UI = READY_CURRENT_ACCEPTED
last accepted data remains visible
freshness = WAIT_NEXT_ACCEPTED_INPUT
```

禁止：

```text
all UNKNOWN
NO_REAL_SHADOW_DATA
production unavailable
pointer = null
```

---

## 6. 新交易日到来

当下一 accepted input 到来时：

```text
capture
validate
build
candidate
accept
atomic publish
readback
```

然后 UI 自动切到新的：

```text
accepted_trade_date
data_head_digest
state context
```

不需要手工改前端。

---

## 7. Shadow 与 daily production 的关系

真实 Shadow 新 publication 可以由新 accepted input 驱动，但：

```text
Shadow publish failure
```

不得自动撤销已经接受的 current V4 production state。

应表现为：

```text
Production Current = READY
Shadow = NO_REAL_SHADOW_DATA / BLOCKED_SHADOW_SCOPE
```

---

## 8. Rollback

生产切换必须具备：

```text
PRE_CUTOVER_AUTHORITY.json
POST_CUTOVER_AUTHORITY.json
ROLLBACK_POINTER.json
```

回滚只允许：

```text
恢复上一个已接受 V4 production pointer
```

禁止：

```text
自动回滚到 V3 作为 silent fallback
```

如果 V4 production authority 损坏，应：

```text
fail closed + 显式报错
```

---

## 9. Daily launcher

现有 daily scanner / updater 必须接到 V4 production authority。

要求：

```text
一次执行
-> 更新数据
-> 构建 candidate
-> 验证
-> 原子 publish
-> 生成 receipt
-> 前端下一刷新可读
```

不需要人工改 JSON pointer。

---

## 10. Evidence

至少：

```text
PRODUCTION_AUTHORITY_PRE.json
PRODUCTION_AUTHORITY_POST.json
CURRENT_DATA_READBACK.json
NO_NEW_TRADING_DAY_BEHAVIOR.json
NEXT_ACCEPTED_INPUT_SIMULATION.json
ATOMIC_PUBLISH_TEST.json
ROLLBACK_TEST.json
TDX_ZERO_WRITE.json
LEGACY_FALLBACK_NEGATIVE.json
```

---

## 11. 退出条件

```text
V4_PRODUCTION_AUTHORITY = CANDIDATE_READY
DAILY_REFRESH = PASS
NO_NEW_DAY_PRESERVES_CURRENT = PASS
ROLLBACK = PASS
TDX_ZERO_WRITE = PASS
```

进入 P0-5。

## 12. V4-19 / V4-20 不变量

本轮完成后允许出现：

```text
product_version = V4
default_ui_shell = V4
current module source_mode = V4_ACCEPTED_RESEARCH_READONLY
production_permission[*] = false
Focus source cutover = false
```

这不是矛盾。

它表示：

> 系统正式使用 V4 软件和 V4 accepted research 数据进行日常观察，但 capability 仍处于未完成长期真实 Shadow / Forward 验证的只读研究状态。

不得为了满足“生产版本切换”修改 V4-19 permission formula。
