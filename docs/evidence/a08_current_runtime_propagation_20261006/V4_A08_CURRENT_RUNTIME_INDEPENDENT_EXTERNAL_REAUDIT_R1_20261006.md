# V4 A08 Current Runtime｜独立外部复审 R1｜2026-10-06

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 审计 HEAD: `b7ca247745976aa390387a0701601b00ac0d8498`
- Audit ID: `A08_CURRENT_RUNTIME`
- Capability: `V4_09_N01_CURRENT_RUNTIME_PREWATCH`

## 1. 唯一结论

```text
A08_CURRENT_RUNTIME_EXTERNAL_REAUDIT =
PASS_CURRENT_RUNTIME_ENGINEERING_SHADOW_DEPENDENCY_SCOPE

CURRENT_RUNTIME_CODE_REPAIR_REQUIRED = false

PRODUCTION_PERMISSION = false
FOCUS_CUTOVER_PERMISSION = false
DEFAULT_UI_CUTOVER_PERMISSION = false
FIRST_REAL_SHADOW_PERMISSION = false
```

本结论接受的是：

> 当前 V4-09 PREWATCH runtime 作为后续 Shadow capability dependency 的当前实现身份。

不等于生产、Focus、默认 UI 或真实 Shadow 激活授权。

## 2. 为什么此前是 OPEN

`V4_09_N01_HARDENING_ACCEPTED_RECORD_R1` 明确：

```text
acceptance_scope = REPAIR_FREEZE_AUTHORITY_HARDENING_AUDIT_ONLY
current_runtime_accepted = false
current_runtime_external_acceptance = PENDING_INDEPENDENT_EXTERNAL_AUDIT
```

2026-10-01 的 A08 外审接受的是：

```text
accepted historical publication hardening
```

并明确不拿 historical runtime archive 给 current runtime 洗白。

因此 `A08_CURRENT_RUNTIME = OPEN_EXTERNAL_REAUDIT` 是当时正确的 scope 分离，不代表当前 runtime 存在已知算法错误。

## 3. Current producer exact identity

当前：

```text
src/v4/stock_prewatch.py
bytes = 22817
sha256 = a57a4413b56cd81f43a06611f4dec328ef6ac35486f4a4b56e5b5938e2db60ce
```

与 2026-10-01 A08 evidence 中记录的 current producer 完全一致。

并且与 clean-checkout tested commit：

```text
37928d065af62ae41ecbf5cd9da20089017ad9d8
```

逐字节相同。

本轮未出现“旧证据审的是 A、现在运行的是 B”的问题。

## 4. Supporting contracts exact preserved

以下 current runtime 关键绑定与 2026-10-01 tested runtime 保持 exact same bytes：

```text
reports/v4_09/V4_09_R1_1_REPAIR_CONTRACT_FREEZE.json
config/v4_09_priority_provenance_contract_r1_1.json
config/v4_09_priority_producer_vectors_r1_1.json
```

当前 `V4_STAGE_ACCEPTED_HEAD` 仍 exact bind：

```text
V4_09_ACCEPTED_HEAD.json
sha256 = 641ef9e2e6fe8f461a9b765262e739791a6d3fdd220b0eff7947e2690de3a87d
```

并保持：

```text
v4_09_status = ENGINEERING_PASS_CAPABILITY_SCOPED
production_permission = false
```

## 5. Algorithm boundary

2026-10-01 A08 evidence 已确认：

```text
all_algorithm_function_asts_unchanged = true
```

current runtime 相对 historical accepted implementation 的主要新增是：

```text
repair-freeze exact authority validation
accepted head / amended parent validation
consumer identity / provenance hardening
immutable publication behavior
```

不是重新定义 PREWATCH 业务公式。

现行代码继续保持：
- whitelist inputs
- tri-state fail closed
- future/forbidden field isolation
- parameter identity validation
- exact identity/universe coverage
- immutable artifact writer
- no production permission

## 6. Tests / evidence

A08 clean checkout：

```text
1312 passed
2 skipped
0 failed
```

且 producer 与当前 HEAD exact same bytes。

后续 full-chain scoped regression 再次覆盖 `tests/v4_09`；出现的 V4-09 known-debt 节点是：

```text
test_production_and_v4_09_acceptance_stay_disabled
```

该节点本质是治理状态仍未从 historical-only scope 晋升 current runtime acceptance，而不是 current runtime 计算错误。

P0-02 R1R1 后没有修改 V4-09 producer / core contracts。

## 7. tests/v4_a08 的后续变化

A08 test 文件相对 10 月 1 日只把历史校验入口：

```text
scripts.promote_v4_09_accepted_head.validate
```

切换为：

```text
dm01_publication_history_reader_v1.validate_v4_09_history
```

用于适配后续 publication-history 治理。

这不改变 current PREWATCH producer 算法，也不构成 current runtime blocker。

## 8. External verdict

因此：

```text
A08_CURRENT_RUNTIME.current_state
可从：
OPEN_EXTERNAL_REAUDIT

晋升候选为：
ACCEPTED_SCOPED
```

对应 Shadow blocker：

```text
blocks_affected_capability_in_shadow
true -> false
```

但仍必须保持：

```text
blocks_production_cutover_for_scope = true
formal_consumer_permission_granted_by_audit_head = false
```

原因：Current Audit Head 只负责 blocker 状态，不直接授予 runtime permission；真实 Shadow 激活仍必须走独立 activation authority / R25。

## 9. 当前仍被旧机器状态阻断

尽管本外审结论为 PASS，仓库当前：

```text
V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V3
v4_16_runtime_capability_resolution_v1
V4_16_RUNTIME_DEPENDENCIES_V5
```

仍 exact bind 旧的：

```text
A08_CURRENT_RUNTIME = OPEN_EXTERNAL_REAUDIT
```

所以机器行为当前继续 WAIT/BLOCK 是正确的。

不得手改旧 accepted/candidate bytes。

下一步必须走版本化治理传播。

**最终状态：`PASS_CURRENT_RUNTIME_ENGINEERING_SHADOW_DEPENDENCY_SCOPE`**
