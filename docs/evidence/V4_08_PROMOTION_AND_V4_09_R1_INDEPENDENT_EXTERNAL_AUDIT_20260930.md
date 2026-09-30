# V4-08 Promotion + V4-09 R1 独立外部审计｜2026-09-30

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**审计 HEAD**：`e8d50805f4ff53de9e64eaa7938c4625f3cce278`  
**V4-09 implementation commit**：`36c987089fb2f79607b1fba6784c208bc2b01758`  
**上一轮正式通过点**：`8200a775d9c4115f479ee60b4c11a16579e86723`

## 1. 唯一总状态

```text
V4_09_EXTERNAL_ACCEPTANCE_BLOCKED_R1
```

阻断原因不是 V4-09 主算法失败，也不是结果为空，而是三项 lineage / immutability 硬错误：

```text
B01 V4-08 Promotion B0 producer lineage 错绑
B02 V4-09 priority state producer contract 未执行校验
B03 V4-09 candidate artifact 真实物化路径可覆盖旧 T
```

因此：

```text
V4-08 R5.2 原算法外部验收      KEEP PASS
V4-08 Promotion                REPAIR_REQUIRED
V4-09 Core Logic               PASS_WITH_LINEAGE_BLOCKERS
V4-09 Final Acceptance         BLOCKED
V4-10 Formal Entry             NOT_AUTHORIZED
```

## 2. 本轮通过项

V4-08 Promotion 的 capability 与权限边界基本正确：

```text
accepted_stage_range = V4_00_TO_V4_08_ACCEPTED
v4_08_status = ENGINEERING_PASS_CAPABILITY_SCOPED
v4_08_external_acceptance = V4_08_EXTERNAL_ACCEPTANCE_PASS_R5_2_ENGINEERING_SCOPE
production_permission = false
shadow_production_permission = false
focus_cutover_permission = false
```

Protected Heads 未移动：

```text
V4_DATA_ACCEPTED_HEAD
186b1c88512a5a92e7c4fbd954e5dcd005a0ad03ecbac9c334b05939d9e12de0

V4_DEV_BASELINE_HEAD
45695460b0147c6ada12e0ebd8e5070ac0a45eebea26603ff5a3daddc4dd5094

V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1
d6374a73b8084ccd383cbb4f75428ed91176e91cc09d87c3329041d57c5bd9ed
```

V4-09 原始资格公式正确：

```text
raw_qualification
=
base_seed_state
AND
mandatory_core_quality_READY
```

没有把 Sector / Rotation / B2 / D2 / Confirmation / Anchor / Support / Radar / Focus / UI / future outcome / forward return / turnover 作为硬资格。

Priority 算法正确：

```text
emergence:
HIGH   delta3 >= 10pp
MEDIUM delta3 >= 3pp
LOW    otherwise

structure:
HIGH   COMPRESSING_STRONG
MEDIUM COMPRESSING or BULL_TRANSITION
LOW    otherwise evaluable

risk:
core_extension_risk
LOW < MEDIUM < HIGH < EXTREME
```

A/B/C/D 规则与主合同一致，未出现 total_score / weighted_score。

参数绑定已验证，3pp/10pp 扰动会改变 runtime axis/bucket；150 个 machine vectors 全部通过。

Full-market engineering replay：

```text
trade_date = 2026-09-28
row_count = 5222
TRUE = 0
FALSE = 2443
UNKNOWN = 2779
A/B/C/D = 0/0/0/0
UNKNOWN_BUCKET = 2779
NOT_ELIGIBLE = 2443
```

0 TRUE 与 V4-07 accepted Seed 当前 Prior-RPS 降级状态一致，未发现阈值放宽、旧 R3 fallback 或 UNKNOWN→FALSE。

Independent postcheck 对 full-market 公式使用独立 oracle，`mismatch_count=0`；数据库 migration 021 的 5222 行 exact readback、revision append-only、UPDATE/DELETE 拒绝、rollback 均通过。

Clean regression：

```text
890 tests
888 passed
2 skipped
0 failed
0 errors
```

NO_SYMBOL 永久 P0：

```text
status = PASS
hard_gated_equity_symbol_hits = 0
unclassified_paths = []
```

未发现任何针对特定股票代码写死资格、阈值或分支。

## 3. HARD BLOCKER B01｜V4-08 Accepted Head 的 B0 producer identity 错误

真实 B0 implementation receipt：

`reports/v4_08/V4_08_R5_B0_IMPLEMENTATION.json`

明确记录：

```text
producer.path = src/sector/rotation_r5.py
producer.sha256 = 93c73b431a0fa8af1cf2e0c65a706dc78e390b1d5a2cd821f85e89ec5323968b
```

B0 的 `evaluate_b0()` 也实际位于 `src/sector/rotation_r5.py`。

但 `scripts/promote_v4_08_accepted_head.py` 当前硬编码：

```text
b0_producer = src/sector/native_r5.py
```

导致正式 `data/v4/V4_08_ACCEPTED_HEAD.json` 记录了错误 producer identity。

这不是显示问题，而是正式 Accepted Head lineage 错误：

```text
FORMAL_ACCEPTED_LINEAGE_WRONG_PRODUCER_IDENTITY
```

当前 promotion validator 只做“head 写了什么文件→该文件 hash 是否匹配”，没有比较 B0 Accepted Head binding 与真实 B0 implementation receipt，因此形成：

```text
SELF-CONSISTENT BUT SEMANTICALLY WRONG
```

判定：

```text
V4_08_PROMOTION_LINEAGE = FAIL
```

V4-08 R5.2 原外部算法验收不回滚；只修 Promotion metadata。

## 4. HARD BLOCKER B02｜V4-09 priority state producer contract 未执行

V4-09 priority 输入：

```text
compression_state
ma_structure_state
core_extension_risk
```

Field registry 已明确 producer：

```text
compression_state   -> COMPRESSION_STATE_V1
ma_structure_state  -> MA_STRUCTURE_V1
core_extension_risk -> EXTENSION_RISK_V1
```

V4-04 state envelope 本身保存：

```text
contract_id
parameter_set_id
input_digest
source_digest
contract_digest
output_digest
unknown_reason
```

但当前 `src/v4/stock_prewatch.py` 的 state reader 只看：

```text
value
unknown_reason
```

没有校验 `contract_id` 或 `parameter_set_id`。

因此理论上：

```text
field name = compression_state
value = COMPRESSING_STRONG
contract_id = WRONG_PRODUCER
```

仍可能被解释成：

```text
structure_quality_axis = HIGH
```

当前 2026-09-28 数值结果来自已接受 V4-05 artifact，因此没有证据证明本次 5222 行已经被错误 producer 污染；但 generalized consumer contract 尚未真正 enforce producer identity，而 priority primitives 是 V4-09 正式交付的一部分。

判定：

```text
V4_09_PRIORITY_LINEAGE_GATE = FAIL
```

修复只影响 priority provenance；不得修改 raw formula 或阈值。

## 5. HARD BLOCKER B03｜V4-09 candidate artifact 会覆盖旧 T

当前 materializer 固定写：

```text
data/v4/artifact_store/v4_09/V4_09_STOCK_PREWATCH_CANDIDATE.jsonl.gz
```

其底层写入最终使用：

```text
os.replace(temp, path)
```

这意味着未来 T+1 / 同日新 revision 如果继续调用正式 materializer，可以直接替换旧 T 文件。

当前 `future_input_mutation_frozen_T_unchanged=true` 证据只是在内存中 `build(T+1)`，然后检查已有 T 文件没有变化；它没有真实 materialize T+1，因此不能证明 artifact store append-only。

正确要求：输出改成不可变版本路径，例如：

```text
V4_09_STOCK_PREWATCH_<trade_date>_<publication_digest>.jsonl.gz
```

或等价 content/revision-addressed identity。

写入语义必须：

```text
path absent + new bytes      -> create
path exists + same bytes     -> idempotent PASS
path exists + different bytes-> APPEND_ONLY_ARTIFACT_CONFLICT
```

禁止覆盖旧版本。

判定：

```text
V4_09_ARTIFACT_IMMUTABILITY = FAIL
```

## 6. 当前正式判定矩阵

| 项目 | 结论 |
|---|---|
| V4-08 R5.2 algorithm acceptance | KEEP PASS |
| V4-08 capability classification | PASS |
| V4-08 protected heads | PASS |
| V4-08 production permissions | PASS |
| V4-08 B0 producer lineage | **FAIL** |
| V4-09 raw formula | PASS |
| V4-09 mandatory quality scope | PASS |
| V4-09 emergence/structure/risk formula | PASS |
| V4-09 A/B/C/D | PASS |
| parameter binding | PASS |
| machine vectors | PASS |
| 5222 full-market replay | PASS_ENGINEERING |
| independent formula postcheck | PASS |
| migration 021 | PASS |
| clean regression | PASS |
| no-symbol | PASS |
| priority producer contract enforcement | **FAIL** |
| artifact append-only identity | **FAIL** |
| V4-09 Accepted Head | CORRECTLY ABSENT |
| V4-10 formal entry | NOT AUTHORIZED |

## 7. 唯一总裁决

```text
V4_09_EXTERNAL_ACCEPTANCE_BLOCKED_R1
```

精确原因：

```text
V4_08_PROMOTION_LINEAGE_REPAIR
AND
V4_09_PRIORITY_PROVENANCE_GATE_REPAIR
AND
V4_09_ARTIFACT_IMMUTABILITY_REPAIR
REQUIRED
```

下一轮只执行：

```text
V4-08 Promotion Amendment R1
+
V4-09 R1.1
```

禁止修改：

```text
3pp / 10pp
raw qualification formula
mandatory quality scope
priority bucket formula
V4-07 Seed
V4-08 Sector/Rotation algorithms
migration 021 semantic schema
Prior-RPS
Amount A
```

V4-10 可以提前做只读合同设计，但 R1.1 外部通过前不得创建 V4-09 Accepted Head、不得将 Stage Head 推到 V4-09、不得正式进行 V4-10 integrated implementation/acceptance。

**审计结束**
