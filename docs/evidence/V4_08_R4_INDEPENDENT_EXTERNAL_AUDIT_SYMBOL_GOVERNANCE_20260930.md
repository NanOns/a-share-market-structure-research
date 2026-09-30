# V4-08 R4 独立外部验收审计｜股票代码特判治理复核

项目：大A交易 / A-Share Market Structure Research  
仓库：NanOns/a-share-market-structure-research  
分支：codex/v4-system-reform  
审计 HEAD：0d959b24a44528265aff4784d8c283902f0abd3e  
上一审计 HEAD：097a22f3fd8f7be405eab6e64a4f513d2ec64413  
实现提交：0eb4669a673bad4694bfe2ac26fc67f2e8920935  
日期：2026-09-30

# 1. 唯一总状态

```text
V4_08_R4_EXTERNAL_ACCEPTANCE_BLOCKED

PRIMARY_BLOCKER =
NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC_GATE_FALSE_PASS

TECHNICAL_PIT_CANDIDATE =
PASS_PENDING_GENERIC_REPLAY

ROTATION_AST_R4 =
PASS_ENGINEERING
```

当前不能创建 `data/v4/V4_08_ACCEPTED_HEAD.json`。全局 Accepted Head 正确保持 `V4_00_TO_V4_07_ACCEPTED`。

# 2. R4 技术链通过部分

Identity / Calendar promotion 已生成，第一张 2026-09-30 PIT candidate 已 materialize：

- source revision: `sha256:190f9647cb8b6b610dd5336a76dc8b483e3a31439bdb0140bd95523c45905386`
- snapshot: `3dd77c68f3f29601b59d09853a70977bfab15f3fba3edeca6737f75ef9d7bcc0`
- formal rows: INDUSTRY 5,224；THEME 44,938；合计 50,162
- raw rows: 85,038
- independent mismatch: 0
- PostgreSQL formal view readback: 50,162
- determinism: PASS_TWO_IDENTICAL_MATERIALIZATIONS
- temporal: PASS_NO_BACKDATING_NO_CARRY_FORWARD

Exclusions：
- BSE_OPTIONAL 438
- NON_FORMAL_SECTOR_TYPE 32,862
- NOT_LISTED_AT_TARGET 11
- OPTIONAL_BOARD_OUTSIDE_REQUIRED_SCOPE 1,565

R4 还完成四态 AST：
`TRUE / FALSE / UNKNOWN / NOT_APPLICABLE`。

`strong_prev=0 -> mature_retained=NOT_APPLICABLE` 已正确实现。五个 retention 参数仍为 null，formal Rotation consumer 仍 disabled。

Clean regression：
- PostgreSQL 18.6 disposable
- config/.env read=false
- 626 tests
- 624 passed
- 2 skipped
- 0 failed/errors

因此 PIT、AST、DB regression 本身不是本轮 blocker。

# 3. P0 表面 PASS 不可信

当前 `V4_08_R4_P0_NO_SYMBOL_SPECIFIC_RUNTIME_SCAN.json` 宣称：

```text
status = PASS
production_runtime_hits = 0
literal_symbol_hits = 1634
audit_only_hits = 307
```

但 scanner 分类本身存在漏洞，因此这是 false pass。

# 4. P0-01｜所有 scripts 被无条件归 AUDIT_ONLY

`scan_no_symbol_specific_runtime_logic.py` 当前包含：

```python
if path.startswith('scripts/') and path.endswith(('.py','.sql')):
    return 'AUDIT_ONLY'
```

这导致 `promote_* / accept_* / materialize_* / apply_*` 即使会创建 Accepted Head、修改 acceptance 或生成正式 runtime artifact，也不进入 hard gate。

结论：

```text
P0-01 = FAIL / HARD BLOCKER
```

# 5. P0-02｜R4 Identity promotion 明确写死两只股票

`scripts/promote_v4_08_r4_inputs.py` 当前存在：

```python
target_new={'SZ.001246','SZ.301716'}
```

以及：

```python
if {x['source_security_key'] for x in changes}!={'SZ.001246','SZ.301716'}:
    ...
```

该脚本实际创建 accepted identity artifact/head，并修改 acceptance，因此不是纯审计。

结论：

```text
P0-02 = FAIL / HARD BLOCKER
```

# 6. P0-03｜Promotion verifier 重复同一硬编码

`scripts/verify_v4_08_r4_input_promotions.py` 又写死：

```text
SZ.001246
SZ.301716
```

用于验证“只有这两只被 promotion”。

这意味着 producer hardcode == verifier hardcode，失去真正独立性。

结论：

```text
P0-03 = FAIL
```

# 7. P0-04｜Phase1 生产 runner 被误标 AUDIT_ONLY

`src/production/daily.py` 明确执行：

```python
from phase1_runner import run as p1
...
```

所以 `src/phase1_runner.py` 属于生产调用图。

但 runtime path policy 把 `src/phase*_runner.py` 放入 audit_only_globs。

这是错误分类。

# 8. Phase1 固定真实股票 QA 样本

`src/phase1_runner.py`：

```python
SAMPLES=(
 'SH.600519',
 'SZ.000001',
 'SZ.000651',
 'SZ.300750',
 'SH.688001'
)
```

运行时仅对这些固定股票收集 context，随后 `sample_pass` 进入 `phase1_gate(checks)`，可以影响 PASS/BLOCKED。

虽然这些股票没有不同因子公式，但它们会影响正式阶段 QA gate，因此仍属于具体股票依赖。

结论：

```text
P0-04 = FAIL / REPO-WIDE GOVERNANCE ISSUE
```

# 9. 其他历史系统代码也有固定股票集合

当前扫描还发现：
- `src/phase0_2_runner.py`
- `src/phase0_2a_runner.py`
- `src/phase0_2b_runner.py`
- `src/tdx/tdx_audit.py`

包含多组固定真实股票代码。

这些可能属于初始化、验收、数据源 QA，不一定改变股票因子，但新硬规则要求：

> 除 tests / evidence / user data / immutable factual artifacts 外，系统功能代码不得依赖具体股票代码。

因此必须治理，不能只因为名字中有 `audit` 或 `phase0` 就自动豁免。

# 10. 合法例外｜Market Index reference

以下可作为 typed reference data 保留：

```text
SH.000001
SZ.399001
SZ.399006
```

前提：
- instrument_type = MARKET_INDEX
- 只用于市场 session / benchmark reference
- 不参与单股 admission、评分、信号或例外
- 应从 `v4_market_reference_instruments_v1.json` 注册表读取

这不是特定股票规则。

# 11. 普通 contract config 当前未发现股票特判

本轮 `CONTRACT_CONFIGURATION` 中 specific stock literal hit = 0。

当前未发现：
- threshold_by_symbol
- stock allowlist
- stock blocklist
- symbol override

藏在普通 V4 contract config 中。

# 12. R3 旧 11-key 硬编码已正确移除

R3 的 `KEYS=[11 specific symbols]` 已经从 admission builder 中移除；
postcheck 也不再复制 11-key set；
原 lifecycle source contract 已移动到 `reports/v4_08/audit_inputs/`，成为 evidence-only。

这一部分修复有效。

# 13. 当前 PIT 主链没有股票特判

`materialize_v4_08_r4_pit_candidate.py`、独立 PIT verifier、PostgreSQL readback 未发现具体股票代码分支。

它们基于：
- accepted identity
- target active catalogue
- lifecycle
- sector type
- board
- listing status
- quality

通用处理。

所以：

```text
PIT_ALGORITHM_DATA_PATH =
NO_SPECIFIC_SYMBOL_BRANCH_FOUND
```

当前 50,162 PIT facts 不需要推翻。

但其 accepted identity 输入由 symbol-hardcoded promotion script 产生，所以最终接受前必须做 generic promotion equivalence replay。

# 14. 当前逐项判定

```text
PIT admission logic             PASS
PIT independent recompute      PASS
PIT PostgreSQL formal view     PASS
PIT determinism                PASS
Temporal no-backdating         PASS
Rotation 4-state AST           PASS
Disposable regression          PASS

NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC governance gate
                               FAIL
```

唯一主 blocker 是：

```text
P0_SYMBOL_SPECIFIC_SYSTEM_LOGIC_GOVERNANCE
```

# 15. Scanner 必须改成真实执行角色分类

至少需要：

```text
PRODUCTION_RUNTIME
SYSTEM_PIPELINE
GOVERNANCE_MUTATION
RUNTIME_CONFIGURATION
REFERENCE_DATA
AUDIT_ONLY
TEST_ONLY
EVIDENCE_ONLY
USER_DATA
UNCLASSIFIED_FAIL_CLOSED
```

Hard-gated：

```text
PRODUCTION_RUNTIME
SYSTEM_PIPELINE
GOVERNANCE_MUTATION
RUNTIME_CONFIGURATION
```

都必须：

```text
specific_stock_literal_hits = 0
```

# 16. scripts 默认必须 fail-closed

不能再：

```text
scripts/**/*.py -> AUDIT_ONLY
```

默认应是 `SYSTEM_PIPELINE` 或 `UNCLASSIFIED_FAIL_CLOSED`。

只有显式满足：
- runtime_authorized=false
- does_not_write_accepted_heads=true
- does_not_write_runtime_artifacts=true
- not_called_by_production=true

才可成为 AUDIT_ONLY。

# 17. Governance mutation 必须 hard-gate

至少包括：
- scripts/promote_*.py
- scripts/accept_*.py
- scripts/materialize_*.py
- scripts/apply_*.py
- scripts/*accepted_head*.py
- scripts/*publication*.py

以及任何会写：
- data/v4/*ACCEPTED*
- data/v4/artifact_store/
- publication heads
- runtime state heads

的脚本。

# 18. Production call graph 优先于文件名

如果 production runtime import / invoke 某项目模块，该模块不能因名字含：
`qa / audit / runner / helper`
而自动降级。

已知：

```text
src/production/daily.py
→ src/phase1_runner.py
→ src/phase1_qa.py
```

必须纳入 SYSTEM_PIPELINE。

# 19. R4 promotion 泛化

删除：

```text
target_new={'SZ.001246','SZ.301716'}
```

expected promotion set 必须从精确、外部授权 candidate artifact 动态取得：

```text
new_lifecycle_events
+
acceptance=CANDIDATE_PENDING_EXTERNAL_PROMOTION
```

不关心股票代码是什么。

# 20. Promotion verifier 泛化

独立 verifier 应从：
- parent accepted artifact
- candidate artifact
- authorized candidate digest
- accepted artifact

重算：
- candidate additions
- expected accepted additions
- field-level diff

不能复制具体股票代码。

# 21. Phase1 QA 样本泛化

删除固定 `SAMPLES`。

改成 deterministic data-driven sampling，例如：
- current accepted universe
- actual bar at cutoff
- sufficient history
- board-stratified
- stable hash(security_id + contract_seed)

示例可保持五个样本，但具体股票必须由数据决定。

# 22. Phase0 / TDX QA 固定股票治理

对 phase0_2 / phase0_2a / phase0_2b / tdx_audit：

- 若是系统 gate：改为动态确定性 sample；
- 若仅是历史验收复现：迁移至 TEST_ONLY / EVIDENCE_ONLY，runtime_authorized=false。

# 23. 当前 R4 candidate 保留策略

不要删除当前 PIT candidate。

修复后执行：

```text
GENERIC_IDENTITY_PROMOTION_EQUIVALENCE
GENERIC_PIT_EQUIVALENCE
```

如果 generic promotion 得到完全相同：
- accepted identity artifact digest
- source revision id
- snapshot id
- fact logical digest
- fact artifact hash
- row counts
- exclusion inventory

则当前 PIT candidate 可继续使用。

如果 logical digest 不同，则生成 R4.1 candidate revision 并重新 postcheck。

# 24. 当前项目状态

```text
V4_00_TO_V4_07_ACCEPTED
```

保持不变。

V4-08：

```text
PIT_ENGINEERING_CANDIDATE = TECHNICALLY_PASS
ROTATION_AST_ENGINEERING = PASS
P0_SYMBOL_GOVERNANCE = FAIL
FINAL_EXTERNAL_ACCEPTANCE = BLOCKED
```

# 25. 唯一最终结论

```text
V4_08_R4_EXTERNAL_ACCEPTANCE_BLOCKED
P0_NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC_FALSE_PASS
```

当前没有发现 PIT / Rotation 正式算法针对某只股票特殊加分、特殊阈值或特殊状态。

但系统确实仍存在具体股票代码硬编码，并且至少存在于真实治理 mutation path 和生产 QA gate 中。原 P0 scanner 因错误分类而没有阻断。

必须修复并做 generic equivalence replay 后，才能正式接受 V4-08。
