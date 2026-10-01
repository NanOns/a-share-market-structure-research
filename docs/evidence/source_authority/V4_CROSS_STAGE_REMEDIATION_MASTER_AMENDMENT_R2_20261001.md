# V4 Cross-Stage Remediation Master Amendment R2｜新增 A10-A12｜2026-10-01

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**基线 HEAD：** `4e5284f74c5275e28d75985d1c3e60eaf96e4103`  
**Supersedes / Extends：** `V4_CROSS_STAGE_INDEPENDENT_AUDIT_REMEDIATION_MASTER_TASK_R1_20261001.md`  
**性质：** Master Card 增量修订，不删除 A01-A09，不重写已存在 work package。

---

# 1. 为什么需要 R2 Amendment

DM-01 A01 实施暴露出：

```text
LOCAL_ACCEPTED_FREEZE_MISSING
被描述成
provider data unavailable
```

并发现：

```text
BaoStock supplemental / cross-check
在部分 runtime 中被抬成 Core hard gate / formal producer
```

因此对 V4-00～V4-09 做专项回溯后，新发现三条正式 remediation：

```text
A10 SOURCE_AUTHORITY_AVAILABILITY_SEMANTICS_GOVERNANCE
A11 V4_01_IDENTITY_SOURCE_AUTHORITY_RECONCILIATION
A12 V4_02_STATUS_ST_AUTHORITY_AND_DOWNSTREAM_CASCADE
```

A01-A09 继续有效。

---

# 2. 当前 remediation 总数

原：

```text
A01-A09 = 9
```

新增：

```text
A10-A12 = 3
```

总计：

```text
12
```

---

# 3. A10

```text
Audit ID:
SOURCE_AUTHORITY_AVAILABILITY_SEMANTICS_GOVERNANCE

Work Package:
WP-A10-SOURCE-AUTHORITY-GOVERNANCE

Priority:
P0 Governance
```

目标：

```text
统一 Source Role
统一 Availability State
统一 historical retrieval / PIT semantics
禁止 NOT_QUERIED → PROVIDER_UNAVAILABLE
禁止 supplemental 静默阻断 Core
```

任务卡：

```text
V4_A10_SOURCE_AUTHORITY_AVAILABILITY_GOVERNANCE_TASK_R1_20261001.md
```

---

# 4. A11

```text
Audit ID:
V4_01_IDENTITY_SOURCE_AUTHORITY_RECONCILIATION

Work Package:
WP-A11-V4-01-IDENTITY-AUTHORITY

Priority:
P1
```

目标：

```text
核对 V4-01 5351 identities 的字段级正式 source owner
```

重点：

```text
BaoStock lifecycle facts
TDX security master / day boundary
official exchange evidence
stable security_id anchor
SH.600018 listing anchor discrepancy
```

任务卡：

```text
V4_A11_V4_01_IDENTITY_SOURCE_AUTHORITY_RECONCILIATION_TASK_R1_20261001.md
```

---

# 5. A12

```text
Audit ID:
V4_02_STATUS_ST_SOURCE_AUTHORITY_DIVERGENCE

Work Package:
WP-A12-V4-02-STATUS-ST-AUTHORITY

Priority:
P0
```

目标：

```text
修复 V4-02 tradestatus/isST formal producer 与 master contract 的冲突
```

并按真实 diff：

```text
V4-04
→ V4-05
→ V4-07
→ V4-08
→ V4-09
```

做最小 cascade revalidation。

任务卡：

```text
V4_A12_V4_02_STATUS_ST_AUTHORITY_AND_CASCADE_REPAIR_TASK_R1_20261001.md
```

---

# 6. 对 A01 DM01 的修订依赖

原 A01 工程 adapter 结果：

```text
KEEP_PASS_ENGINEERING_SCOPE
```

不推倒。

但 A01 R2 source-path 修复新增依赖：

```text
A10 governance contract
+
A12 status/ST producer contract freeze
```

因此：

```text
DM01 runtime capability / historical target-date catch-up
可以先做

DM01 TRADING_STATUS / ISST final formal binding
必须等待 A12 producer contract freeze

DM01 all-nine real candidate
必须绑定 A12 accepted/candidate authority contract
并等待外部复审
```

A01 不得自己再次定义另一套：

```text
suspension
ST
BaoStock missing fallback
```

---

# 7. 对 A06 BaoStock 的关系

A06 仍是：

```text
strict binding / turnover / fingerprint tolerance
```

A12 是：

```text
tradestatus/isST field authority
```

两者不能混在一起。

A06 通过不自动意味着：

```text
BaoStock tradestatus/isST 成为 formal owner
```

A12 若希望走 provider authority amendment，必须单独做 field semantics acceptance。

---

# 8. 对 A07 Historical AS_RECORDED 的关系

A10/A12 支持：

```text
T+n 查询 provider date=T
```

只得到：

```text
RECONSTRUCTED_CORRECTED target-date fact
```

不会自动得到：

```text
first_available_at=T
```

所以：

```text
A07 继续 OPEN
```

不得因为 historical catch-up 成功而关闭。

---

# 9. 对 A08/A09 的关系

既有：

```text
WP-A08-V4-09-N01
WP-A09-V4-09-N02
```

任务卡已经存在。

不重复创建。

仍属于：

```text
Production / Shadow 前必须关闭的 hardening
```

---

# 10. 新执行顺序

用户明确要求当前已有三张本地文档暂不执行，待本轮设计完成后统一执行。

因此推荐：

## Batch 0｜先冻结根规则

```text
A10 Source Authority Governance
A11 V4-01 Identity Authority Reconciliation
A12 V4-02 Status/ST Authority Repair
```

其中：

```text
A10 首先开始
A11/A12 可在 A10 schema freeze 后并行
```

A11 是 audit-first，不要求先大改数据。

A12 是 P0。

## Batch 1｜DM01

执行已有：

```text
DM01_A01_R2_BAOSTOCK_CATCHUP_SUPPLEMENTAL_GATE_REPAIR_TASK_20261001.md
```

但遵循本 Amendment：

```text
runtime/catch-up 可并行开发
status/ST final producer 必须消费 A12
```

## Batch 2｜V4-09 hardening

执行已有：

```text
WP-A08-V4-09-N01
WP-A09-V4-09-N02
```

## Batch 3｜原 Master 其他能力

```text
A02 Prior-RPS
A03 Forward PIT
A04 Amount A
A05 Legacy Valid Member
A06 BaoStock Strict Binding
A07 Historical AS_RECORDED
```

---

# 11. 主工程线是否停止

```text
NO
```

V4-11/V4-12 等 unrelated engineering：

```text
继续
```

但正式集成 / Replay Gate B 必须读取修复后的 authority state。

不得：

```text
等 A01-A12 全部关闭才写后续代码
```

---

# 12. Stage 状态治理

本次回溯不允许直接删除历史 PASS。

新增三个状态概念：

```text
HISTORICALLY_ACCEPTED
AUTHORITY_REVALIDATION_REQUIRED
BUSINESS_REPLAY_REQUIRED
```

例如：

```text
V4-02 historical acceptance record
= PRESERVED

V4-02 status/ST capability
= AUTHORITY_REVALIDATION_REQUIRED

V4-04 accepted result
= BUSINESS_REPLAY_REQUIRED
```

只有独立修复验收后再产生 Amendment。

---

# 13. Cascade Stop Rule

任何下游级联必须逐级判断：

```text
INPUT_IDENTITY_CHANGED?
BUSINESS_OUTPUT_CHANGED?
LOGICAL_DIGEST_CHANGED?
```

若：

```text
INPUT rebinding only
业务值完全等价
```

允许停止业务重算，只做 lineage amendment。

若业务值变化：

```text
继续向直接 consumer 传播
```

禁止一发现 foundation 问题就无差别重跑 V4-03～V4-09。

---

# 14. 新 Registry 条目

后续 Codex 执行时应：

```text
保留原 V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1.json

新增：
V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R2.json
```

R2：

```text
entries = A01-A12
```

并保留：

```text
R1 binding
supersedes / extends relation
```

不得覆盖 R1。

---

# 15. 新增状态建议

```text
A10 = OPEN
A11 = OPEN
A12 = OPEN
```

production gate：

```text
A10 = true
A11 = true for identity authority finalization
A12 = true
```

does_not_block_unrelated_engineering_stage：

```text
true
```

---

# 16. 本轮文件集

新增加：

```text
V4_00_TO_V4_09_SOURCE_AUTHORITY_RETROSPECTIVE_AUDIT_R1_20261001.md

V4_A10_SOURCE_AUTHORITY_AVAILABILITY_GOVERNANCE_TASK_R1_20261001.md

V4_A11_V4_01_IDENTITY_SOURCE_AUTHORITY_RECONCILIATION_TASK_R1_20261001.md

V4_A12_V4_02_STATUS_ST_AUTHORITY_AND_CASCADE_REPAIR_TASK_R1_20261001.md

V4_CROSS_STAGE_REMEDIATION_MASTER_AMENDMENT_R2_20261001.md
```

---

# 17. 当前统一执行包

用户下一次决定让 Codex 一起执行时，建议把以下作为一个“治理 + 修复启动批次”：

```text
1. Master R2 Amendment
2. A10
3. A11
4. A12
5. 原 DM01 A01 R2
6. WP-A08 N01
7. WP-A09 N02
```

其中：

```text
A10 schema/guard 先落地
A11/A12 再按 guard 执行
DM01 final source binding 等 A12 producer freeze
```

---

# 18. 唯一当前状态

```text
CROSS_STAGE_REMEDIATION_MASTER_R2 = DESIGNED_NOT_EXECUTED

A01-A09 = PRESERVED
A10-A12 = NEW_NOT_EXECUTED

THREE_EXISTING_USER_HELD_DOCS = NOT_EXECUTED

MAIN_ENGINEERING_LANE = CONTINUE
PRODUCTION/SHADOW = STILL_NOT_AUTHORIZED
```
