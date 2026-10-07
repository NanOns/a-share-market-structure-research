# V4 正式生产切换与全站 UNKNOWN 修复｜总调度卡 R1｜2026-10-07

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 任务制定基线 HEAD: `411c8d35bf3e3e84c766dd3e59e2824f3cfd7d2b`
- 当前页面模式: `V4_SHADOW_PREVIEW_SERVICE_V1`
- 当前生产目标: **V4 作为默认生产研究工作台与当前已接受数据读取权威**
- 任务性质: P0 生产切换 / 读取链修复 / UI 修复 / 服务架构修复 / 回归验收
- 本卡为本轮最高执行调度卡。

---

## 0. 用户本轮明确授权

本轮用户已经明确授权以下事项，不得继续用此前 R25/R26 的“未授权”状态阻止**产品版本与只读研究展示**：

```text
V4_PRODUCT_VERSION_DEFAULT_UI = USER_AUTHORIZED
V4_ACCEPTED_RESEARCH_READONLY_VISIBILITY = USER_AUTHORIZED
V4_CURRENT_ACCEPTED_DATA_READER = USER_AUTHORIZED
V4_DAILY_INCREMENTAL_REFRESH = USER_AUTHORIZED
V4_INTERNAL_ARTIFACT_WRITES = USER_AUTHORIZED_OUTSIDE_TDX
```

但必须遵守已经独立外审通过的 V4-19 / V4-20 合同边界：

```text
config/v4_19_focus_source_cutover_contract_v1.json
config/v4_20_default_ui_cutover_contract_v1.json
```

当前真实状态仍是：

```text
production_permission[*] = false
Focus source cutover = false
```

因此本轮**不得**把“用户要求切换 V4 软件版本”偷换成“所有 capability 已经拿到生产权限”。

本轮允许并要求建立一个新的、版本化的展示模式：

```text
V4_ACCEPTED_RESEARCH_READONLY
```

含义是：

- 默认产品/UI 可以进入 V4；
- 展示当前已接受 V4 数据；
- 不等待真实 Shadow；
- 不把 read-only display 当作 capability production grant；
- 不授予 Focus 算法写入；
- 不绕过 V4-19 的 Shadow/Forward/Migration 三重生产门。

如需改变 V4-20 的 source-mode 规则，必须创建 successor contract（例如 `v4_20_default_ui_cutover_contract_v2.json`），旧 v1 不得改写。

本轮**不需要等待首个真实 Shadow 样本**，也不需要等待未来交易日数据，才能完成 V4 生产读路径与默认 UI 切换。

但以下能力仍不得偷开：

```text
TDX_WRITE = FORBIDDEN
AUTO_TRADING = NOT_AUTHORIZED
BUY_SELL_RECOMMENDATION = NOT_AUTHORIZED
FOCUS_MEMBERSHIP_MUTATION = NOT_AUTHORIZED_UNLESS_ALREADY_SEPARATELY_ACCEPTED
REAL_SHADOW_SAMPLE_FABRICATION = FORBIDDEN
MODEL_EFFECTIVENESS_UPGRADE = FORBIDDEN_WITHOUT_EVIDENCE
```

必须区分：

```text
生产研究工作台 / 当前已接受数据读取
!=
真实 Shadow 新样本已经产生
!=
Forward 成熟度已经验证
!=
交易执行授权
```

---

## 1. 当前已确认根因

当前页面“全部 UNKNOWN”不能归因于“明天还没有交易数据”。

当前仓库事实：

```text
config/v4_17_shadow_ui_source_v1.json
accepted_readback = null
external_acceptance = null
status = NO_REAL_SHADOW_DATA
```

当前 `ShadowContextReader` 只允许读取：

```text
externally accepted SHADOW_V4 publication
+
PIT_OBSERVED real Shadow readback manifest
```

如果不存在上述 readback，直接返回：

```text
NO_REAL_SHADOW_DATA
context = null
real_sample_count = 0
```

前端 `shadow-v4.js` 在 `context_token` 为空时，会给每个组件创建空字段，并统一显示：

```text
UNKNOWN · SOURCE_FIELD_UNAVAILABLE
```

同时当前 preview service：

```text
--v4-shadow-only
```

被明确设计为：

```text
不连接 legacy DB
不连接生产 writer
不读取 current accepted V4 state
只展示 Shadow readback
```

因此现在的页面是**R26 Shadow 工程预览页**，不是正式 V4 生产工作台。

另一方面，当前仓库已经存在：

```text
data/v4/V4_DATA_ACCEPTED_HEAD.json
accepted_trade_date = 2026-09-30
external_acceptance = EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN
```

并存在大量 accepted V4 数据与组件产物。

所以：

> 没有下一交易日 accepted input，只应表现为“当前最新已接受交易日仍为 2026-09-30 / 等待下一 accepted input”，绝不能让整个生产 UI 退化成全站 UNKNOWN。

---

## 2. 架构结论

必须立即拆开两个概念：

### A. Current Accepted V4 Production Context

用途：

```text
正式生产研究工作台
默认首页
当前最新已接受状态
历史最近一次 accepted trade date
板块/个股/雷达/Why Now/健康信息
```

来源：

```text
V4_CURRENT_STAGE_AUTHORITY
V4_DATA_ACCEPTED_HEAD
各已接受 owner/stage artifact
```

不得依赖“今天必须有新数据”。

### B. Real Shadow Context

用途：

```text
真实 Shadow 运行诊断
新 publication
cohort / Forward / settlement
真实样本积累
```

来源仍保持：

```text
externally accepted SHADOW_V4 publication
PIT_OBSERVED readback
```

没有真实 Shadow 时：

```text
/api/v4/shadow/* -> NO_REAL_SHADOW_DATA
```

这是合法状态，但**不能再控制整个生产首页**。

---

## 3. 本轮目标状态

最终必须形成：

```text
/                       -> V4 默认工作台（产品版本 V4）
/v4                     -> V4 默认工作台
/v4/shadow              -> V4 Shadow diagnostics
/v3                     -> legacy diagnostic / historical page only
```

模块来源必须逐模块标识，允许：

```text
PRODUCTION_V4_PROVISIONAL        # 仅 capability permission 真正成立时
V4_ACCEPTED_RESEARCH_READONLY    # 当前主要目标：展示 accepted V4，但无生产写权限
LEGACY_PRODUCTION
SHADOW
NO_PERMISSION
```

禁止用一个全局 `V4_PRODUCTION` 标签掩盖 capability 权限差异。

默认 V4 页面在没有新交易日数据时仍必须展示：

```text
last_accepted_trade_date
data freshness
current accepted state
current accepted radar
current accepted entity/sector state
known capability status
waiting-next-input status
```

禁止：

```text
因为 next trade date 不存在 -> 整页 UNKNOWN
因为 Shadow sample = 0 -> 整页 UNKNOWN
因为 Forward outcome 尚未成熟 -> 整页 UNKNOWN
```

---

## 4. 本轮任务卡

按以下任务卡执行：

```text
P0-1
01_V4_CURRENT_ACCEPTED_READER_AND_NO_DATA_SEMANTICS_TASK_R1_20261007.md

P0-2
02_V4_PRODUCTION_UI_UNKNOWN_REPAIR_TASK_R1_20261007.md

P0-3
03_V4_UNIFIED_SERVICE_V4_DEFAULT_TASK_R1_20261007.md

P0-4
04_V4_PRODUCTION_AUTHORITY_AND_DAILY_REFRESH_TASK_R1_20261007.md

P0-5
05_V4_PRODUCTION_E2E_AND_CUTOVER_ACCEPTANCE_TASK_R1_20261007.md
```

---

## 5. 执行顺序

### Batch A：先冻结正式生产读取合同

只执行：

```text
P0-1
```

完成 Current Accepted V4 Reader 和状态语义。

### Batch B：并行修

在 P0-1 合同稳定之后，可并行：

```text
P0-2 UI
P0-3 Service
```

### Batch C：生产 authority 与日更

执行：

```text
P0-4
```

### Batch D：一次完整生产验收并原子切换

执行：

```text
P0-5
```

只有 P0-5 全部通过，才正式把 `/` 默认入口切到 V4 production。

不得因为等待下一交易日而停止 Batch A/B/C/D。

---

## 6. 关键状态语义

生产页面必须至少区分：

```text
READY_CURRENT_ACCEPTED
WAIT_NEXT_ACCEPTED_INPUT
NO_ELIGIBLE_OBJECTS
PENDING
RIGHT_CENSORED
NOT_AUTHORIZED
SOURCE_FIELD_UNAVAILABLE
SOURCE_INVALID
NO_REAL_SHADOW_DATA
```

其中：

- `WAIT_NEXT_ACCEPTED_INPUT`：当前没有更晚交易日 accepted input，但最近 accepted state 有效。
- `NO_REAL_SHADOW_DATA`：只属于 Shadow 诊断域。
- `SOURCE_FIELD_UNAVAILABLE`：某个应该存在的具体字段确实缺失。
- `UNKNOWN` 不能再被当作“没新交易日”的通用占位符。

---

## 7. 不允许的修法

禁止：

```text
把 2026-09-30 数据复制成 2026-10-08
伪造 publication
伪造 Shadow sample
模拟数据冒充真实数据
用 V3 数据偷偷填 V4
用 latest file / mtime 猜 authority
重新引入已清理的 legacy workbench DB 作为主生产源
把 null 改成假 KNOWN
删除来源质量与 digest 校验
为了页面好看屏蔽 UNKNOWN
直接把 production=true 改掉而没有 runtime/readback 验收
```

---

## 8. 最终必须交付

代码 + 证据至少包括：

```text
config/v4_current_accepted_read_contract_v1.json
config/v4_production_runtime_authority_v1.json

src/workbench_service/current_v4_context.py
src/workbench_service/v4_server.py
src/workbench_service/static/v4-workbench.html
src/workbench_service/static/v4-workbench.js

reports/v4_production_cutover_20261007/
```

并保留：

```text
/v4/shadow
ShadowContextReader
R26 Shadow tests
```

Shadow 不删除，只从“整个 V4 页面唯一数据源”降为其正确的诊断子域。

---

## 9. 最终状态

目标：

```text
V4_PRODUCT_VERSION_DEFAULT = PASS
V4_DEFAULT_UI_SHELL = PASS
V4_ACCEPTED_RESEARCH_READONLY = PASS
V4_CURRENT_ACCEPTED_READER = PASS
V4_DAILY_REFRESH = PASS
V4_SHADOW_DIAGNOSTIC = PRESERVED
CAPABILITY_PRODUCTION_PERMISSION = PRESERVED_BY_V4_19_RULES
TDX_ZERO_WRITE = PASS
V4_ONLY_REGRESSION = PASS
```

可以同时保持：

```text
REAL_SHADOW_SAMPLE_COUNT = 0
V4_16_REAL_SHADOW = WAIT_INPUT
FORWARD_MATURITY = CAPABILITY_SCOPED
```

这不阻断生产研究工作台上线。

---

**执行要求：严格按 01 -> (02 + 03) -> 04 -> 05。全部任务完成后 commit + push，一次性交给独立外部验收。**
