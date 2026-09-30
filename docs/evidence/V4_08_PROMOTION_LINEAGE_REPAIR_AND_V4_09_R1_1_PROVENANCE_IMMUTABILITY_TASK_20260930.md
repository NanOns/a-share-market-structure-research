# V4-08 Promotion Amendment R1 + V4-09 R1.1 定点修复任务卡｜2026-09-30

**仓库**：`NanOns/a-share-market-structure-research`  
**分支**：`codex/v4-system-reform`  
**输入 HEAD**：`e8d50805f4ff53de9e64eaa7938c4625f3cce278`  
**外部状态**：`V4_09_EXTERNAL_ACCEPTANCE_BLOCKED_R1`  
**性质**：三项 lineage / immutability 定点修复，禁止重做算法

## 0. 只修三个 blocker

```text
B01 V4-08 B0 producer lineage 错绑
B02 V4-09 priority state producer contract 未 enforce
B03 V4-09 candidate artifact 可覆盖旧 T
```

已通过内容全部冻结：

```text
STOCK_PREWATCH_V1 raw formula
base_seed_state AND mandatory_core_quality_READY

mandatory_core_quality 当前 scope
base_seed_state
core_price_damage observability

delta3_medium = 3pp
delta3_high   = 10pp

emergence / structure / risk axes
A/B/C/D rules

V4-07 Base Seed
V4-08 Sector Native
V4-08 B0/B1 algorithm
B2 capability downgrade
Amount A diagnostic
migration 021 current semantic columns
```

## A. B01｜V4-08 Promotion Lineage Amendment

真实 B0 producer 权威来自：

```text
reports/v4_08/V4_08_R5_B0_IMPLEMENTATION.json
```

必须绑定：

```text
src/sector/rotation_r5.py
sha256 = 93c73b431a0fa8af1cf2e0c65a706dc78e390b1d5a2cd821f85e89ec5323968b
```

不得继续绑定 `src/sector/native_r5.py`。

不要静默覆盖旧 `data/v4/V4_08_ACCEPTED_HEAD.json`。保留旧头作为历史错误版本，新增：

```text
data/v4/V4_08_ACCEPTED_HEAD_AMENDED_R1.json
```

至少包含：

```text
contract_id = V4_08_ACCEPTED_HEAD_AMENDED_R1
supersedes = exact binding to old V4_08_ACCEPTED_HEAD.json
amendment_reason = B0_PRODUCER_LINEAGE_BINDING_CORRECTION
```

更新 `V4_STAGE_ACCEPTED_HEAD.v4_08_binding` 指向 amended head，同时保留：

```text
v4_08_superseded_binding
```

绑定旧头。

不得改变：

```text
accepted_stage_range = V4_00_TO_V4_08_ACCEPTED
```

不得移动：

```text
V4_DATA_ACCEPTED_HEAD
V4_DEV_BASELINE_HEAD
V4_08_PIT_MEMBERSHIP_ACCEPTED_HEAD_R1
```

Promotion validator 必须新增语义检查：

```text
B0 contract binding
= V4_08_R5_B0_IMPLEMENTATION.contract

B0 producer binding
= V4_08_R5_B0_IMPLEMENTATION.producer

producer source exports evaluate_b0
```

至少校验 path、sha256、callable symbol。

Formal evidence：

```text
reports/v4_joint/V4_08_ACCEPTED_HEAD_AMENDMENT_R1_RECEIPT.json
reports/v4_joint/V4_08_ACCEPTED_HEAD_AMENDMENT_R1_VALIDATION.json
docs/evidence/V4_08_ACCEPTED_HEAD_AMENDMENT_R1_20260930.md
```

必须证明：旧 head preserved、新 head correct、global head 指向 new head、superseded binding exact、Data/Dev/PIT unchanged、capability unchanged、permissions false、idempotent。

## B. B02｜V4-09 Priority Producer Identity Enforcement

三个 priority state 必须 enforce producer：

```text
compression_state
contract_id = COMPRESSION_STATE_V1

ma_structure_state
contract_id = MA_STRUCTURE_V1

core_extension_risk
contract_id = EXTENSION_RISK_V1
```

并建议 enforce：

```text
parameter_set_id = V4_04_CORE_PROFILE_PARAMETER_SET_V1
```

Wrong producer 处理：

```text
compression value=COMPRESSING_STRONG + wrong contract
→ structure_quality_axis = UNKNOWN

ma wrong contract
→ affected structure = UNKNOWN

risk wrong contract
→ risk_axis = UNKNOWN
```

使用稳定 reason，例如：

```text
STATE_PRODUCER_CONTRACT_MISMATCH
STATE_PARAMETER_SET_MISMATCH
```

Priority lineage 错误只能影响 priority axis/bucket。若 raw 已 TRUE：

```text
raw_qualification 保持 TRUE
priority_bucket → UNKNOWN_BUCKET
```

不得反向修改 raw。

现有 synthetic fixture 必须补：

```text
contract_id
parameter_set_id
```

至少新增 negative vectors：

```text
compression correct/wrong/missing contract
ma correct/wrong/missing contract
risk correct/wrong/missing contract
correct contract + wrong parameter_set_id
```

Independent postcheck 必须独立执行相同 producer/parameter-set 校验，不得调用 runtime state reader 作为 oracle。

## C. B03｜Artifact Store Append-Only Identity

禁止继续用唯一固定正式输出：

```text
V4_09_STOCK_PREWATCH_CANDIDATE.jsonl.gz
```

改为版本化 immutable path，例如：

```text
data/v4/artifact_store/v4_09/
V4_09_STOCK_PREWATCH_<trade_date>_<publication_digest>.jsonl.gz
```

或等价 trade_date/revision-addressed path。

V4-09 专用 writer 语义：

```text
path not exists
→ write

path exists + bytes identical
→ idempotent PASS

path exists + bytes different
→ APPEND_ONLY_ARTIFACT_CONFLICT
```

不得依赖通用 `atomic_write_gzip_jsonl()` 的 overwrite 语义覆盖历史文件。

必须做真实 materialized multi-context：

```text
materialize T
记录 T path/SHA/bytes

materialize T+1
必须生成另一个 path

重新读 T
path/SHA/bytes 完全未改变
```

还要做同日不同 accepted revision：

```text
T-r1
T-r2
```

必须得到不同 immutable artifact identity，T-r1 保持不变。

重建 V4-09 Stage Candidate Manifest，绑定 exact immutable：

```text
artifact path
sha256
logical_digest
publication_id
trade_date
```

## D. Acceptance Boundary

修复后仍禁止：

```text
创建 V4_09_ACCEPTED_HEAD
Stage Head 推到 V4_09
```

Codex 最终只能到：

```text
V4_09_R1_1_ENGINEERING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

## E. Regression / P0 Gates

重新执行：

```text
full required V4 regression
V4-09 targeted tests
disposable PostgreSQL
promotion amendment validation
no-symbol permanent gate
clean detached checkout
```

要求：

```text
hard_gated_equity_symbol_hits = 0
unclassified_paths = []
```

相同 accepted 9/28 输入下，修复 lineage 后原则上 raw counts 应保持：

```text
TRUE = 0
FALSE = 2443
UNKNOWN = 2779
```

不能为验证修复而改阈值、Seed、Prior-RPS 或 UNKNOWN 语义。

## F. Formal Evidence

至少输出：

```text
reports/v4_joint/V4_08_ACCEPTED_HEAD_AMENDMENT_R1_RECEIPT.json
reports/v4_joint/V4_08_ACCEPTED_HEAD_AMENDMENT_R1_VALIDATION.json

reports/v4_09/V4_09_R1_1_PRIORITY_PRODUCER_CONTRACT_GATE.json
reports/v4_09/V4_09_R1_1_ARTIFACT_IMMUTABILITY.json
reports/v4_09/V4_09_R1_1_MATERIALIZED_MULTI_CONTEXT.json
reports/v4_09/V4_09_R1_1_INDEPENDENT_POSTCHECK.json
reports/v4_09/V4_09_R1_1_DETERMINISM.json
reports/v4_09/V4_09_R1_1_NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN.json
reports/v4_09/V4_09_R1_1_SCHEMA_MIGRATION_RECEIPT.json
reports/v4_09/V4_09_R1_1_ISOLATED_REGRESSION.json
reports/v4_09/V4_09_R1_1_CLEAN_CHECKOUT_RECEIPT.json
reports/v4_09/V4_09_R1_1_STAGE_CANDIDATE_MANIFEST.json
reports/v4_09/V4_09_R1_1_CLOSURE.md
reports/v4_09/V4_09_R1_1_EXTERNAL_REAUDIT_HANDOFF.json
```

## G. Handoff

Codex 必须报告：

```text
pushed HEAD

V4-08:
old accepted head SHA
amended head SHA
correct B0 producer path/SHA
global head SHA
Data/Dev/PIT unchanged proof
amendment validation

V4-09:
runtime SHA
contract/AST/parameter SHA
immutable artifact path/SHA/logical digest
raw counts
bucket counts
priority producer negative tests
materialized T/T+1 proof
same-day revision proof
independent postcheck
migration readback
no-symbol
clean regression
```

然后停止等待独立复验。

## H. V4-10

允许只读合同设计和字段/AST草拟；R1.1 外部通过前不允许 formal integrated implementation、Accepted Head 或 Stage promotion。

**任务结束**
