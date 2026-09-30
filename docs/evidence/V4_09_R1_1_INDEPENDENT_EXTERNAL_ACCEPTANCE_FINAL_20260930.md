# V4-09 R1.1 独立外部复验最终结论｜2026-09-30

**项目**：大A交易 / A-Share Market Structure Research  
**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**审计 HEAD**：`981332582c1982d9da3af922688e682946822119`  
**R1.1 implementation commit**：`5eca56d3555a826c4cca94d6e3d7ae9d11628be6`  
**R1.1 evidence seal commit**：`981332582c1982d9da3af922688e682946822119`  
**上一轮阻断 HEAD**：`e8d50805f4ff53de9e64eaa7938c4625f3cce278`  
**权威合同**：`A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md`

---

# 1. 唯一总状态

```text
V4_09_EXTERNAL_ACCEPTANCE_PASS_R1_1_ENGINEERING_SCOPE
```

本轮上一审计的三个阻断项：

```text
B01 V4-08 Promotion B0 producer lineage 错绑
B02 V4-09 priority state producer contract 未执行
B03 V4-09 candidate artifact 可覆盖旧 T
```

全部完成定点修复并通过独立复验。

因此：

```text
V4-08 Promotion Amendment R1 = PASS
V4-09 R1.1 Engineering       = PASS
V4-09 Production             = NOT AUTHORIZED
V4-09 Real Signal            = DEGRADED
V4-10 Engineering Entry      = AUTHORIZED AFTER V4-09 PROMOTION
```

---

# 2. 增量提交核对

相对 `e8d50805...`：

```text
ahead_by  = 2
behind_by = 0
```

提交：

```text
5eca56d3555a826c4cca94d6e3d7ae9d11628be6
Repair V4-08 B0 lineage and V4-09 priority provenance and immutable artifacts

981332582c1982d9da3af922688e682946822119
Seal R1.1 clean regression and lineage immutability reaudit evidence
```

第二笔 seal commit 只新增：

```text
clean-checkout receipt
closure
external handoff
isolated regression
no-symbol evidence
schema receipt
stage candidate manifest
```

没有在测试完成后再次修改：

```text
runtime
contract
AST
parameters
migration
artifact writer
```

因此实现测试对应关系成立。

GitHub combined status 当前仍为空：

```text
statuses = []
```

这仅记录为仓库 CI 外部状态缺失，不单独阻断本轮验收。

---

# 3. B01｜V4-08 B0 Producer Amendment｜PASS

旧错误 Head 保留：

```text
data/v4/V4_08_ACCEPTED_HEAD.json

SHA256
b9ba34374ce35eefab705469de1e005758b90fa1f58ea5bba96fac08571073bc
```

没有静默覆盖。

新增：

```text
data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json

SHA256
f2a35cebd18e8caf723e7900133333ce4b8df1a8314cb190dade7b0ea7624a3f
```

明确：

```text
contract_id
= V4_08_ACCEPTED_HEAD_AMENDED_R1

amendment_reason
= B0_PRODUCER_LINEAGE_BINDING_CORRECTION
```

真实 B0 producer：

```text
src/sector/rotation_r5.py

SHA256
93c73b431a0fa8af1cf2e0c65a706dc78e390b1d5a2cd821f85e89ec5323968b
```

并验证实际导出：

```text
evaluate_b0
```

Amendment validator 已从“只验证自洽 hash”升级为同时验证：

```text
B0 contract == V4_08_R5_B0_IMPLEMENTATION.contract
B0 producer == V4_08_R5_B0_IMPLEMENTATION.producer
producer SHA exact
producer exports callable evaluate_b0
```

同时有 negative test：

```text
self-consistent wrong producer
→ REJECT

self-consistent wrong B0 contract
→ REJECT
```

上一轮 `SELF-CONSISTENT BUT SEMANTICALLY WRONG` 缺口已闭环。

---

# 4. Global Stage Supersede｜PASS

当前：

```text
accepted_stage_range
= V4_00_TO_V4_08_ACCEPTED
```

正式 binding：

```text
v4_08_binding
→ V4_08_ACCEPTED_HEAD_AMENDED_R1.json
```

同时保留：

```text
v4_08_superseded_binding
→ V4_08_ACCEPTED_HEAD.json
```

Global Stage SHA：

```text
6620089e9a1ca550e89c2c0bb177887528c8e7d160a44c584664f04b91a1c48e
```

Protected Heads 未改变：

```text
V4_DATA_ACCEPTED_HEAD
186b1c88512a5a92e7c4fbd954e5dcd005a0ad03ecbac9c334b05939d9e12de0

V4_DEV_BASELINE_HEAD
45695460b0147c6ada12e0ebd8e5070ac0a45eebea26603ff5a3daddc4dd5094

V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1
d6374a73b8084ccd383cbb4f75428ed91176e91cc09d87c3329041d57c5bd9ed
```

Capability / OPEN audit / permissions 均未改变。

---

# 5. Superseded Head Runtime Bypass 检查｜PASS

本轮额外做了针对性外部扫描。

检查范围包括当前：

```text
src/v4/*
src/sector/*
V4-08/V4-09 相关 materializer / verifier / promotion scripts
```

在当前 `src/v4` 与 `src/sector` runtime 中：

```text
没有发现代码直接硬读
data/v4/V4_08_ACCEPTED_HEAD.json
```

相关脚本中仅发现：

1. `promote_v4_08_accepted_head.py`
   - 为了历史 Head / Amendment 管理，属于预期引用。

2. `seal_v4_08_r3_stage.py`
   - 历史 R3 封存脚本，用旧 Head 是否存在作为当时门禁；
   - 不属于当前 V4-09 runtime consumer。

因此当前正式 consumer 没有证据绕过 Global Stage 去继续消费 superseded Head。

---

# 6. B02｜Priority Producer Contract Gate｜PASS

新增正式 repair contract：

```text
V4_09_PRIORITY_PROVENANCE_GATE_R1_1
```

三项绑定：

```text
compression_state
contract_id = COMPRESSION_STATE_V1
parameter_set_id = V4_04_CORE_PROFILE_PARAMETER_SET_V1

ma_structure_state
contract_id = MA_STRUCTURE_V1
parameter_set_id = V4_04_CORE_PROFILE_PARAMETER_SET_V1

core_extension_risk
contract_id = EXTENSION_RISK_V1
parameter_set_id = V4_04_CORE_PROFILE_PARAMETER_SET_V1
```

错误 producer：

```text
STATE_PRODUCER_CONTRACT_MISMATCH
```

错误参数实例：

```text
STATE_PARAMETER_SET_MISMATCH
```

处理规则正确：

```text
priority axis → UNKNOWN
priority_bucket → UNKNOWN_BUCKET
raw qualification → 不改变
```

没有把 Priority lineage error 反向变成 eligibility failure。

---

# 7. Priority Negative Vectors｜PASS

新增：

```text
15 producer vectors
```

覆盖三个 state 的：

```text
correct contract
wrong contract
missing contract
wrong parameter_set
missing parameter_set
```

所有 wrong/missing lineage：

```text
raw remains TRUE
affected priority becomes UNKNOWN
bucket becomes UNKNOWN_BUCKET
```

同时 FALSE / UNKNOWN Seed 情况也验证：

```text
priority lineage failure
不会修改原 raw
```

---

# 8. Independent Producer Oracle｜PASS

独立 verifier 新增：

```text
independent_state_reader()
```

它没有调用 runtime 的 `state_field()` 作为 oracle。

独立检查：

```text
contract_id
parameter_set_id
value
unknown_reason
```

全市场 postcheck：

```text
row_count      = 5222
exact_universe = true
mismatch_count = 0
```

因此本轮 producer lineage gate 不是“实现和测试共用同一个 helper 后自证”。

---

# 9. 原 V4-09 算法未被修改｜PASS

冻结内容继续保持：

```text
raw formula
mandatory quality scope
3pp / 10pp
emergence axis
structure axis
risk axis
A/B/C/D
```

当前合同 SHA：

```text
STOCK_PREWATCH_V1
6c090ee9cbc5a7e3c5c86ca9023aa983db41d447388ea1776308a69ecbefadc8

Machine AST
9035548e8e33ea66e1c448b63b017cfa9b1ab2bcf7c08ef0568063a2eac954c6

Parameter Set
3c9b0d658c6e8212c5a6239eecdeece99d54791b97cee45fe4df98de71086c24
```

原 150 algorithm vectors 继续通过。

---

# 10. B03｜Immutable Artifact Store｜PASS

旧固定 R1 artifact 保留且未覆盖：

```text
data/v4/artifact_store/v4_09/
V4_09_STOCK_PREWATCH_CANDIDATE.jsonl.gz

SHA256
ca88956bfedf38356c07a0c2a9b275c2e4d2bf4e5f6744cfd498abb9e35b8900
```

R1.1 正式 candidate 使用版本化地址：

```text
V4_09_STOCK_PREWATCH_<trade_date>_<logical_digest>.jsonl.gz
```

当前正式 engineering artifact：

```text
data/v4/artifact_store/v4_09/
V4_09_STOCK_PREWATCH_2026-09-28_edb35a7b7aa382add631d80d105575c00274b638cef112b58e7e2687510e9a6e.jsonl.gz
```

SHA256：

```text
8b92cbd96a8145005bad89374349582c075cf367722b956a75243d59aa64d18d
```

logical digest：

```text
edb35a7b7aa382add631d80d105575c00274b638cef112b58e7e2687510e9a6e
```

---

# 11. Immutable Writer 语义｜PASS

当前 writer：

```text
path absent
→ CREATED

path exists + identical bytes
→ IDEMPOTENT_PASS

path exists + different bytes
→ APPEND_ONLY_ARTIFACT_CONFLICT
```

正式写入不再：

```text
os.replace(old_artifact)
```

而是：

```text
complete temp write
fsync
exclusive hard-link create
```

并有 concurrent conflicting create 测试：

```text
一个完整 payload 创建成功
另一个 conflict
最终 artifact 必须等于其中一个完整 payload
```

没有 partial overwrite。

---

# 12. 真正 T / T+1 / Same-Day Revision Materialization｜PASS

这一轮不再只做：

```text
build(T+1) in memory
```

而是通过同一个正式：

```text
materialize_records()
```

真实写文件验证：

```text
T
2030-01-02

T+1
2030-01-03

T revision-2
2030-01-02 / another source revision
```

结果：

```text
三个不同 immutable path
T 原 path 不变
T 原 SHA 不变
T 原 bytes 不变
same context retry idempotent
different payload conflict rejected
```

这些明确标记为：

```text
SYNTHETIC_CONTRACT_VECTORS
NOT ACCEPTED FUTURE MARKET DATA
```

没有伪造真实未来市场。

---

# 13. Accepted Engineering Replay｜PASS

正式回放仍是：

```text
trade_date = 2026-09-28
row_count  = 5222
```

结果没有因为修复而改变：

```text
TRUE     = 0
FALSE    = 2443
UNKNOWN  = 2779
```

Priority：

```text
A/B/C/D        = 0/0/0/0
UNKNOWN_BUCKET = 2779
NOT_ELIGIBLE   = 2443
```

说明 Codex 没借 lineage 修复偷偷：

```text
调 Seed
调 Prior-RPS
调 3pp/10pp
调 eligibility
UNKNOWN → FALSE
```

---

# 14. Real Signal Capability 仍然 DEGRADED

本轮通过的是：

```text
V4-09 engineering scope
```

不是：

```text
真实正式交易信号能力已完整
```

当前 0 TRUE 的主要上游限制仍然是 accepted Prior-RPS bootstrap UNKNOWN。

因此继续保持：

```text
REAL SIGNAL = DEGRADED
```

这不阻断后续工程开发，但必须继续独立积累/修复 accepted Forward inputs。

---

# 15. Migration 021｜PASS / SEMANTICS UNCHANGED

原 SQL SHA 保持：

```text
dcbcd468b7651c233a636c81e81bdbd1dc5b7ca85c42d4769c52b42ef5b7dc1c
```

没有为了 R1.1 修改已通过的表语义。

Disposable PostgreSQL：

```text
full-market exact readback 5222
same publication retry
additional revision append
same-publication payload conflict rejection
UPDATE rejection
DELETE rejection
rollback only 021
rollback restore
```

全部 PASS。

---

# 16. Clean Detached Regression｜PASS

测试：

```text
912 total
910 passed
2 skipped
0 failures
0 errors
```

环境：

```text
config/.env absent
config/.env not read
configured / production database not used
PROCESS_ENVIRONMENT_DISPOSABLE_CLUSTER
temporary cluster destroyed
```

R1 是 890 tests；
R1.1 增加到 912 tests，
新增门禁确实进入正式 regression。

---

# 17. NO_SYMBOL 永久门｜PASS

```text
status = PASS

hard_gated_equity_symbol_hits = 0

unclassified_paths = []
```

本轮仍然没有：

```text
股票代码特判
symbol whitelist
个股专属参数
为了样本通过写死股票
```

---

# 18. V4-09 Accepted Head｜当前正确地不存在

R1.1 candidate 明确：

```text
accepted_head_written = false

external_acceptance
= PENDING_INDEPENDENT_EXTERNAL_REAUDIT
```

Codex 没有提前把自己的候选变成 accepted。

这是正确的。

---

# 19. 两个非阻断 Hardening Note

以下不阻断本轮工程验收，但建议在 Production/Shadow 前继续硬化。

## N01. Repair Freeze Runtime Self-Validation

`load_package()` 已验证 repair 中 `new_bindings` 的 hash，
但可以进一步显式校验：

```text
repair.status == PASS_REPAIR_SCOPE_FREEZE
repair.authority exact
expected new binding set exact
CONSUMER_CONTRACT == repair immutable_writer_contract.consumer_contract_id
```

当前 exact candidate 文件、manifest、clean replay 均一致，所以不构成本轮 blocker。

## N02. DB Explicit Consumer Contract Identity

当前 R1.1 producer-lineage repair 会进入：

```text
publication_id derivation
input_digest
artifact manifest
source implementation binding
```

但 migration 021 的 publication row 没有单独的：

```text
consumer_contract_id
```

这不影响当前 exact readback，
但在未来多版本消费者并存时，显式列会更易审计。

建议 V4-10/V4-14 integration governance 时处理，
不要为此回滚 migration 021。

---

# 20. 当前正式状态矩阵

| 项目 | 结论 |
|---|---|
| V4-08 R5.2 original engineering acceptance | KEEP PASS |
| V4-08 Amendment R1 | PASS |
| B0 producer identity | PASS |
| Global Stage supersede | PASS |
| Protected Heads | PASS |
| V4-09 raw formula | PASS |
| mandatory quality boundary | PASS |
| priority formula | PASS |
| priority producer contract gate | PASS |
| 15 producer negative vectors | PASS |
| 150 original algorithm vectors | PASS |
| immutable artifact identity | PASS |
| T/T+1/same-day revision materialization | PASS |
| 5222 full-market replay | PASS_ENGINEERING |
| independent postcheck | PASS |
| migration 021 | PASS |
| clean regression | PASS |
| no-symbol | PASS |
| V4-09 production permission | FALSE |
| V4-09 real signal capability | DEGRADED |
| V4-09 Accepted Head | NOT YET WRITTEN |

---

# 21. 唯一外部裁决

```text
V4_09_EXTERNAL_ACCEPTANCE_PASS_R1_1_ENGINEERING_SCOPE
```

允许下一步：

```text
1. 建立 V4-09 Accepted Head
2. 将 Global Stage 推到 V4_00_TO_V4_09_ACCEPTED
3. 保持 production / shadow / Focus cutover = false
4. 正式进入 V4-10 State Reducer engineering
```

但依据 REV4 FEP R2 §78：

```text
V4-10
可以实现 reducer interface + 独立 machine vectors

完整 reducer DAG 运行
必须等待 V4-11 Confirmation
和 V4-12 Structure/Anchor/Support

完整 integrated acceptance
放到 V4-14 Replay Gate B
```

因此禁止在 V4-10 单阶段：

```text
宣称完整 State Reducer 已真实闭环
宣称完整 Final State 已验收
启动 Focus/UI cutover
```

---

# 22. 仍独立 OPEN 的能力

继续保留：

```text
V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01
AUD-AMOUNT-A-06
DM01_REAL_INCREMENTAL_BUILDERS
LEGACY_VALID_MEMBER_EXACT_PRODUCER
FORWARD_PIT_HISTORY_ACCUMULATION
```

这些不阻断 unrelated engineering，
但各自 capability 不得提升为正式已解决。

---

**独立外部复验结束。**
