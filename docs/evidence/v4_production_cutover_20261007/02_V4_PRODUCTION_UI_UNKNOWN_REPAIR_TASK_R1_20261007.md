# P0-2｜V4 正式生产 UI / 全站 UNKNOWN 修复任务卡 R1｜2026-10-07

- Priority: P0
- Depends on: P0-1
- Parent: `00_V4_PRODUCTION_CUTOVER_MASTER_R1_20261007.md`

## 1. 目标

把目前的 R26 Shadow 工程预览页与正式生产 V4 页面拆开。

新增正式页面：

```text
src/workbench_service/static/v4-workbench.html
src/workbench_service/static/v4-workbench.js
```

生产页面使用：

```text
/api/v4/current/*
```

当前 capability 尚未满足 V4-19 生产门时，页面模块必须标识：

```text
V4_ACCEPTED_RESEARCH_READONLY
```

而不是伪称：

```text
PRODUCTION_V4_PROVISIONAL
```

而不是：

```text
/api/v4/shadow/*
```

---

## 2. 默认生产页面

最终路由：

```text
/      -> V4 Production Workbench
/v4    -> V4 Production Workbench
```

Shadow 诊断保留：

```text
/v4/shadow
```

V3 保留为：

```text
/v3 -> legacy/historical diagnostic
```

正式首页不得再把以下 R26 Shadow 工程状态作为整页主状态：

```text
R26 工程预览
V4-17 最终验收未授权
V4-17G 未授权
```

这些仍可在 `/v4/shadow` 或 Data / Diagnostics 中展示。

首页标题允许：

```text
V4 工作台
```

但禁止无条件显示全局：

```text
V4_PRODUCTION
```

模块必须按 V4-20 v2 单独显示 source mode。

这些可以保留在 Shadow 诊断页，但不能作为正式首页 footer。

---

## 3. 页面第一屏必须显示

至少：

```text
V4 PRODUCTION
最新已接受交易日
数据更新时间 / freshness
当前 stage
data head digest 短码
stage head digest 短码
当前数据状态
下一 accepted input 状态
```

当目前 accepted_trade_date 仍是 2026-09-30 时，应显示类似：

```text
当前展示：2026-09-30 已接受 V4 状态
状态：WAIT_NEXT_ACCEPTED_INPUT
```

不是：

```text
UNKNOWN
```

---

## 4. 模块要求

至少保留并修复：

```text
今日变化 / Why Now
研究雷达
股票 / 板块状态
Cohort / Forward
结算与修订
运行健康 / 来源质量
```

其中每个模块必须有 module-level status：

```text
READY
EMPTY_VALID
PENDING
NOT_AUTHORIZED
DEGRADED
BLOCKED
```

不能因为一项字段 UNKNOWN 就把整个卡片渲染为 UNKNOWN。

---

## 5. UNKNOWN 新规则

禁止现在这种行为：

```javascript
if (!current.context_token) {
  renderFields(section, null, labels)
}
```

导致所有字段统一：

```text
UNKNOWN · SOURCE_FIELD_UNAVAILABLE
```

生产 UI 必须按 module status 渲染。

例：

### Radar 真正有 accepted 数据

展示真实 accepted rows。

### Radar 合法 0 行

显示：

```text
当前 accepted context 无符合条件对象
```

### Forward 没有成熟结果

显示：

```text
PENDING / 当前无到期样本
```

### Shadow 没真实样本

只在 Shadow 页面显示：

```text
NO_REAL_SHADOW_DATA
```

---

## 6. Today / Why Now

必须读取最近 accepted state transition。

如果当天没有新 accepted trade date：

```text
today change = NO_NEW_ACCEPTED_TRADE_DATE
```

仍展示：

```text
last accepted state
last accepted Why Now
last accepted observable evidence
```

页面应明确：

```text
这些是最近一次已接受状态，不是今天新生成的数据
```

禁止伪装成当前交易日新信号。

---

## 7. 数据来源可见性

每个可展开来源至少显示：

```text
owner_stage
artifact path
sha256 short
accepted_trade_date
quality
```

用户能直接区分：

```text
KNOWN
DEGRADED
PENDING
UNKNOWN
```

---

## 8. 搜索与筛选

正式页至少支持：

```text
股票代码/名称搜索
板块搜索
雷达筛选
状态筛选
当前 context 固定
```

筛选不允许改变 data head / accepted_trade_date。

---

## 9. 视觉验收

必须产出真实页面截图：

```text
HOME_TOP.png
WHY_NOW.png
RADAR.png
ENTITY_STATE.png
FORWARD_PENDING.png
HEALTH.png
SHADOW_NO_REAL_DATA.png
```

要求：

- 中文可读；
- 不大面积 UNKNOWN；
- 无重叠；
- 不泄漏测试 fixture；
- production 与 shadow 标识明显不同。

---

## 10. E2E

至少测试：

```text
production page with 2026-09-30 accepted context
future input missing
valid empty radar
non-empty radar
entity search
forward pending
shadow no-real-data
refresh stability
deep-link stability
context digest stability
```

核心断言：

```text
NO_NEXT_INPUT -> production modules remain readable
NO_REAL_SHADOW_DATA -> only shadow page affected
```

---

## 11. 退出条件

```text
V4_PRODUCTION_UI = PASS_LOCAL
UNKNOWN_FLOOD = ELIMINATED
CURRENT_ACCEPTED_DATA_VISIBLE = PASS
SHADOW_DIAGNOSTIC_SEPARATION = PASS
```

## 12. V4-20 source mode badge

每个生产页面模块必须有明确 badge：

```text
PRODUCTION_V4_PROVISIONAL
V4_ACCEPTED_RESEARCH_READONLY
LEGACY_PRODUCTION
SHADOW
NO_PERMISSION
```

当前最常见状态预期：

```text
V4_ACCEPTED_RESEARCH_READONLY
```

这就是“让用户现在看见 V4 效果”的合法路径：真实 accepted V4 可见，但不伪造 capability production permission。
