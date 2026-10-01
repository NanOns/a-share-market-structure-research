# V4 A13 Official Event Semantics 外部验收正式化任务卡｜2026-10-01

**Work Package：** `WP-A13-EXTERNAL-ACCEPTANCE-FORMALIZATION`  
**基线 HEAD：** `d85f815097a09ca2dceda00d0e29d6ff4fe331d4`  
**优先级：** P1  
**外部验收依据：** `V4_A10_A12_R3_AND_A13_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md`

## 1. 外部结论

A13 已通过：

```text
EXTERNAL_ACCEPTANCE_PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT
```

确认：

```text
V4_08_ACCEPTED_HEAD = KEEP
BUSINESS_REBUILD_REQUIRED = false
EVIDENCE_SEMANTICS_AMENDMENT_REQUIRED = true
```

## 2. 加入真实 external audit

把：

```text
V4_A10_A12_R3_AND_A13_INDEPENDENT_EXTERNAL_ACCEPTANCE_20261001.md
```

加入 repo，并绑定 exact：

```text
path
bytes
sha256
audited_head
```

不得绑定 task card 作为 external authority。

## 3. Sidecar 正式化

当前 candidate：

```text
data/v4/source_evidence/a13/
OFFICIAL_NOTICE_EVENT_SEMANTICS_AMENDMENT_R1.json
```

不得原地篡改 raw source。

生成 versioned accepted semantic artifact，例如：

```text
data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_SIDECAR_R1.json
```

必须内容寻址并绑定 candidate exact digest。

## 4. Accepted Head

创建：

```text
data/v4/OFFICIAL_EVENT_SEMANTICS_ACCEPTED_HEAD_R1.json
```

至少包含：

```text
contract_id
external_acceptance = EXTERNALLY_ACCEPTED
external_authority
sidecar binding
runtime binding
config binding
audited_head
accepted_at
business_rebuild_required = false
v4_08_head_action = KEEP
production_permission = false
```

## 5. Runtime readback

使用真实 Accepted Head 调用：

```text
require_trading_event()
```

验证：

```text
IPO_ISSUANCE_POSTPONEMENT
→ cannot become TRADING_SUSPENSION

IPO_LISTING_POSTPONEMENT
→ cannot become TRADING_SUSPENSION

UNKNOWN_EVENT_SEMANTICS
→ cannot enter trading status truth
```

如果 accepted sidecar 当前存在满足完整 identity/effective-date 条件的真实已上市停/复牌事件，验证 positive path。

若没有：

```text
positive trading-event authority 暂不消费
```

不得把测试 fixture 当正式市场事实。

## 6. Counterfactual 保持

重新验证：

```text
SH.603302
SH.688688
SZ.300728
```

移除误命名 notice 后：

```text
V4_08 admission unchanged
PIT 50,162 facts unchanged
V4_07/V4_08/V4_09 business digest unchanged
```

## 7. Cross-stage Registry

下一版 registry 把：

```text
OFFICIAL_NOTICE_FILENAME_VS_EVENT_SEMANTICS
```

更新为：

```text
status = ACCEPTED
external_acceptance =
PASS_EVIDENCE_GOVERNANCE_NO_BUSINESS_IMPACT
```

保留：

```text
formal trading-event truth requires accepted semantic sidecar/head
filename/capture-id inference forbidden
```

## 8. 不移动业务 Head

本任务禁止：

```text
V4_08 Accepted Head rewrite
V4_DATA_ACCEPTED_HEAD movement
V4_STAGE_ACCEPTED_HEAD movement
```

因为反事实已证明业务 digest 无变化。

## 9. Clean Regression

至少复跑：

```text
A13
V4-01
V4-02
V4-08
V4-09
DM01
no-symbol
```

并验证 raw source hashes 全部不变。

## 10. Codex 最大允许结论

```text
A13_EXTERNAL_ACCEPTANCE_FORMALIZATION = PASS
V4_08_ACCEPTED_HEAD = KEEP
```

禁止：

```text
V4_08_REBUILD
DATA_HEAD_PROMOTION
PRODUCTION_READY
```
