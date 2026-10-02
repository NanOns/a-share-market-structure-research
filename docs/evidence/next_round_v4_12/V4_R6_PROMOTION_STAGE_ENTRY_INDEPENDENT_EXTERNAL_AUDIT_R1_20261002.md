# V4 R6 Promotion + V4-12 Stage Entry 独立外部验收 R1｜2026-10-02

**项目：** 大A市场结构研究系统 V4.2.2  
**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**R6 前置审计 HEAD：** `1c46d6681ba1d0540551bcc0f75b35c545ff2769`  
**Promotion validator commit：** `088042cb2b163b346cce932e18f29192913212fd`  
**Promotion commit：** `b0709567fc286b3cedc6e692fdb02bc9b7094d2c`  
**当前远端 HEAD：** `2e3e811eb08d7e350e27c4c1e2767ba91160ef98`

# 1. 唯一总裁决

```text
R6_PROMOTION_STAGE_ENTRY_EXTERNAL_AUDIT =
PARTIAL_PASS_GOVERNANCE_CLEANUP_REQUIRED

V4_11_ACCEPTED_HEAD_PROMOTION = PASS_KEEP
V4_STAGE_ACCEPTED_HEAD = PASS_KEEP_V4_00_TO_V4_11_ACCEPTED
V4_DATA_ACCEPTED_HEAD = PASS_KEEP_2026_09_30
V4_12_STAGE_ENTRY = PASS_SCOPED_KEEP

V4_12_CONTRACT_DESIGN = AUTHORIZED
V4_12_RUNTIME_IMPLEMENTATION = NOT_AUTHORIZED_YET

R6_BATCH_FULL_ACCEPTANCE =
BLOCKED_BY_G01_G02

G01 = UNAUTHORIZED_GLOBAL_AGENTS_GUARDRAIL_MUTATION
G02 = NON_REPLAYABLE_HARDCODED_LOCAL_BUNDLE_PATH

production = false
shadow = false
focus = false
global_mandatory_adoption = false
```

**不得回滚已经正确完成的 V4-11 Accepted Head 和 Stage Head。**  
本轮缺口属于治理/可重放性清理，不是 V4-11 业务能力回归失败。

# 2. Git 变更边界

相对 `1c46d668...`：

```text
ahead_by = 3
behind_by = 0
```

三次提交：

```text
088042cb...
feat(v4): prepare scoped V4-11 promotion validator and V4-12 entry contracts

b0709567...
chore(v4): promote V4-11 accepted head and authorize V4-12 stage entry only

2e3e811e...
docs(v4): seal detached post-promotion verification and stop handoff
```

未新增或修改 V4-12 runtime business implementation、schema migration、Data Head、production/shadow/focus runtime。

# 3. V4-11 Accepted Head｜PASS KEEP

`data/v4/V4_11_ACCEPTED_HEAD.json` 的身份正确：

```text
contract_id = V4_11_ACCEPTED_HEAD_V1
stage = V4-11
status = ENGINEERING_PASS_CAPABILITY_SCOPED
external_acceptance = EXTERNALLY_ACCEPTED
external_acceptance_decision =
V4_11_EXTERNAL_ACCEPTANCE_PASS_R5_CAPABILITY_SCOPED_ENGINEERING

implementation_commit =
a8635c6802dc31e3c879207cd470bd63021e35ca

audited_sealed_head =
1c46d6681ba1d0540551bcc0f75b35c545ff2769
```

capability map 与外审一致：

```text
LAUNCH_CONFIRM = ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY
RECOVERY_TURN = ENGINEERING_ACCEPTED_FORMAL_D0_CAPABILITY
STRONG_PULLBACK = DIAGNOSTIC_ONLY_NOT_FORMAL
TREND_CONTINUE = DIAGNOSTIC_ONLY_NOT_FORMAL
D2_SEALED_OWNER_BRIDGE = ENGINEERING_ACCEPTED
STATE_EVENT_V1 = ENGINEERING_ACCEPTED_RECONSTRUCTED_LEFT_CENSORED_SCOPE
HISTORICAL_AS_RECORDED_EVENT = NOT_PROVEN
FULL_D0_D1_D2_DAG = NOT_IMPLEMENTED
V4_12_STRUCTURE_SUPPORT = NOT_IMPLEMENTED
```

没有 scope expansion。

# 4. Stage Head｜PASS KEEP

前后字段 diff 仅包含：

```text
accepted_stage_range:
V4_00_TO_V4_10_ACCEPTED
->
V4_00_TO_V4_11_ACCEPTED

version:
2.4.0 -> 2.5.0

新增：
global_mandatory_adoption=false
v4_11_binding
v4_11_capabilities
v4_11_external_acceptance
v4_11_status
v4_12_entry
```

其余原有阶段、degraded/scoped/open 字段保留。

因此：

```text
V4_STAGE_ACCEPTED_HEAD =
KEEP_V4_00_TO_V4_11_ACCEPTED
```

# 5. Data Head｜PASS KEEP

`data/v4/V4_DATA_ACCEPTED_HEAD.json` 前后 exact content：

```text
byte-identical = true
sha256 =
38e7c9b69aa1b47224aa367bcc58bd3e9963d7c80185c180b5ce02ab48ff3e40
```

所以：

```text
V4_DATA_ACCEPTED_HEAD = KEEP 2026-09-30
```

# 6. Promotion Validator｜PASS

post-promotion `P01...P33` 全 PASS，重新覆盖了：

```text
R5A parity
owner oracle
R5A sealed publications
D2 AST
D2 owner oracle
residual UNKNOWN attribution
R4→R5 business diff
D2/Event readback
scenario capability matrix
clean checkout
Data/Dev/PIT/scoped heads
permissions
historical AS_RECORDED boundary
diagnostic scenario boundary
M14/M2 unresolved classification
idempotence
clean detached validation
expected V4-10 fail-closed boundary
validator hash binding
V4-12 no-runtime entry boundary
post-entry exactness
```

Promotion idempotence：

```text
repeat_mutations = 0
```

# 7. V4-12 Stage Entry｜PASS SCOPED

正式 entry：

```text
stage = V4-12
stage_name = Structure / Anchor / Support
status = AUTHORIZED
scope = STAGE_ENTRY_ONLY_RUNTIME_NOT_IMPLEMENTED
runtime_implemented = false
runtime_implementation_authorized = false
```

并明确：

```text
CONTRACT_INCOMPLETE_UNTIL_VERSIONED_REGISTRIES_AST_PARAMETERS_CAPABILITY_AND_INDEPENDENT_VECTORS_ARE_FROZEN
```

DAG：

```text
allowed:
F0[t]
t-1 frozen Anchor/event

forbidden:
D2[t]
same-day Final State
same-day Event diff
Focus
UI
future outcome
same-day newly-created Anchor as confirmation evidence

new Anchor self-confirm = false
earliest support/path test = t+1
```

坐标 identity：

```text
price_basis + adjustment_source_revision
```

且 `qfq coefficient equality is identity = false`。

# 8. 未偷跑 V4-12 runtime

R6 compare 中不存在 V4-12 runtime `src/v4` 实现或 schema migration，entry 也明确 runtime 未授权。

因此：

```text
V4_12_RUNTIME_SCOPE_VIOLATION = NO
```

# 9. G01｜越权修改 AGENTS.md

R6 前 `AGENTS.md` 只有 1–9 条。

R6 新增了永久项目规则：

```text
10. When the user supplies this project's external audit, execution master,
and task-card bundle, execute the master directly even if the message's
My request section is blank...
```

该修改不属于 V4-11 Promotion，也不属于 V4-12 Stage Entry，且永久改变未来 Codex 的项目级执行行为。

裁决：

```text
G01 =
UNAUTHORIZED_GLOBAL_AGENTS_GUARDRAIL_MUTATION
```

修复：

```text
恢复 AGENTS.md 为
1c46d6681ba1d0540551bcc0f75b35c545ff2769
中的 exact bytes。
```

不得用追加说明替代真正删除未授权第 10 条。

该问题不要求回滚 V4-11 promotion，但进入 V4-12 runtime implementation 前必须关闭。

# 10. G02｜prepare 脚本硬编码本机目录

`scripts/prepare_v4_11_promotion_r1.py` 当前包含固定目录：

```text
D:/Users/lps/Desktop/阶段任务/新建文件夹
```

clean repository 无法独立执行初始 prepare。

裁决：

```text
G02 =
NON_REPLAYABLE_HARDCODED_LOCAL_BUNDLE_PATH
```

要求改为：

```text
repo-first:
正式 bundle 已在 repo 时，只 exact validate，不覆盖。

bootstrap:
repo 缺文件时，只允许显式：
--bundle-dir <path>

缺 repo bundle 且无参数：
FAIL_CLOSED:
R6_EXTERNAL_BUNDLE_SOURCE_REQUIRED
```

禁止 Desktop 自动搜索、latest folder 猜测和固定个人路径。

# 11. Preflight failed attempt

第一次 preflight 因 M14 collector：

```text
CRLF worktree representation
!=
Git LF representation
```

触发 P26，并记录：

```text
No head mutation occurred
```

随后保留 original-byte representation proof 再继续。失败记录未覆盖，audit trail 合格。

# 12. M14 / M2

继续：

```text
PREEXISTING_NON_MAINLINE
resolution_claim=false
full_repository_runtime_pass_claim=false
```

KEEP separate，不进入本轮修复。

# 13. 下一步

不回滚：

```text
V4_11_ACCEPTED_HEAD
V4_STAGE_ACCEPTED_HEAD=V4_00_TO_V4_11_ACCEPTED
V4_12 Stage Entry
```

下一轮：

```text
R6R1 Governance / Replay Cleanup
→ close G01 + G02

V4-12A Contract Freeze
→ registries / AST / parameter set / source-time semantics /
   UNKNOWN / schema / independent vectors
```

V4-12A 合同设计可继续，但：

```text
V4_12 runtime implementation =
NOT AUTHORIZED
```

必须等 Contract Freeze 外审通过后再进入实现。
