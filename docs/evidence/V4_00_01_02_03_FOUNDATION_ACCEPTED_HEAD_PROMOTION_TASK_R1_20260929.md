# V4-00~V4-03 Foundation Accepted-Head Promotion Task R1

- 日期：2026-09-29
- 基线 candidate HEAD：`8eb0bfeb0ec2eca7bfb3a3c5c2ca016160151b90`
- 性质：仅 Accepted Head / seal promotion，禁止继续业务开发。

## Authority

已取得：

```text
V4_00_01_02_03_FOUNDATION_FULL_CHAIN = EXTERNAL_ACCEPTANCE_PASS
```

## 1. V4-01 Accepted Head

将 candidate promotion 为：

```text
data/v4/V4_01_ACCEPTED_HEAD.json
```

保持 canonical hashes不变：

```text
identity =
e33294fb8d1d71732fdc3df903258b5617345811ecbdb649af8056ccd91427e0

universe =
3c4669d3b6ba9f4017c69bfcb12256b2b64144ad816ac3e7e055a8caf37ba77b
```

正式状态：

```text
status = FULL_PASS_REQUIRED_SCOPE
external_acceptance = EXTERNALLY_ACCEPTED
```

绑定 Gate V2、full-scope scan R1、resolution R2、postcheck R2、final candidate R10 和本次最终外部验收文件。

## 2. V4-03 amended-scope seal

不重算业务 artifact。

新增 amended-scope accepted seal 或 versioned update：

```text
status = FULL_PASS_AMENDED_SCOPE
external_acceptance = EXTERNALLY_ACCEPTED
```

Required capabilities：
- STOCK_CORE PASS
- RELATIVE_RPS PASS
- MARKET_REFERENCE PASS
- MARKET_REGIME PASS
- SECTOR_NATIVE_CONTRACT PASS

V4-08 继续：

```text
BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION
```

## 3. V4-02

不改 existing accepted artifacts。

保持：

```text
FULL_PASS_REQUIRED_SCOPE
EXTERNALLY_ACCEPTED
BSE_OPTIONAL_DEGRADED
```

## 4. V4-00

保持 FULL_PASS，不重跑 00A~00H。

## 5. 更新 global accepted head

更新：

```text
data/v4/V4_STAGE_ACCEPTED_HEAD.json
```

清理 current authority 中旧：
- `v4_01_external_acceptance=PENDING_EXTERNAL_REVIEW`
- R8.1 pending 作为 current authority
- `v4_03_status=PASS_WITH_SECTOR_SCOPE_DEGRADED`
- 旧 capability-scoped V4-04 authorization

新状态至少：

```text
status = FOUNDATION_FULL_PASS

v4_00_status = FULL_PASS

v4_01_status = FULL_PASS_REQUIRED_SCOPE
v4_01_external_acceptance = EXTERNALLY_ACCEPTED

v4_02_status = FULL_PASS_REQUIRED_SCOPE
v4_02_external_acceptance = EXTERNALLY_ACCEPTED

v4_03_status = FULL_PASS_AMENDED_SCOPE
v4_03_external_acceptance = EXTERNALLY_ACCEPTED

v4_04_entry = AUTHORIZED_FULL_CHAIN

v4_08_sector_entry =
BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION

incremental_update = DEFERRED_NON_BLOCKING
```

历史 receipt 不删除。

## 6. Promotion validator

只读验证：
- V4-01 accepted head hashes exact
- V4-02 accepted head exact
- V4-03 amended seal exact
- global pointers unique/current
- no required stage PENDING
- no 00–03 required capability BLOCKED
- V4-08 block preserved
- canonical artifacts unchanged
- TDX write=0
- scanner/trading=0
- promotion diff 只含 accepted-head/seal/evidence

## 7. 最终 receipt

生成：

```text
reports/v4_joint/V4_00_01_02_03_FOUNDATION_PROMOTION_RECEIPT_R1.json
```

记录：
- external acceptance authority
- candidate head = 8eb0bf...
- promotion commit
- accepted head hashes
- canonical hashes unchanged
- `v4_04_entry = AUTHORIZED_FULL_CHAIN`

## 8. 禁止事项

禁止修改业务算法、Gate V2、source fingerprint thresholds、R7 canonical、V4-02/V4-03业务产物；禁止做 Incremental/Sector PIT；禁止在同一任务里开始 V4-04。

完成 promotion 后停止。
