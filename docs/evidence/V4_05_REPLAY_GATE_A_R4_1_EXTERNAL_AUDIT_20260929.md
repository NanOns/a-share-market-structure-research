# V4-05 Replay Gate A R4.1 独立外部验收审计

**仓库：** `NanOns/a-share-market-structure-research`  
**分支：** `codex/v4-system-reform`  
**Reviewed HEAD：** `f1e3d2ee4721e4880c043e8ca949e7c1e47dce41`  
**上一轮基线：** `e751c9dc63ba6e6325b50daa15e849091e18f5dc`

## 唯一总状态

`V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R4_1`

R4.1 已关闭上一轮 B05（canonical hash / clean-clone determinism），并真实使用 PostgreSQL 18.6 + 12 个正式 V4 migrations 执行了 G08 I01-I05。

但 G08 仍有一个精确绑定错误：

> 正式 PostgreSQL ledger 绑定的是旧 `V4_05_R4_*` artifact identity，而不是当前待验收的 `V4_05_R4_1_*` candidate identity。

因此当前证明的是：

`R4 identity works on the formal PostgreSQL schema`

而不是：

`R4.1 exact candidate identity works on the formal PostgreSQL schema`

这是当前唯一确认的 V4-05 阶段阻断。

## 已通过

- canonical JSON/text hash policy：PASS
- 历史 CRLF promotion binding compatibility：PASS
- clean-clone deterministic rebuild：PASS
- R4→R4.1 business drift：0
- PostgreSQL 18.6 isolated cluster：PASS
- 12 formal migrations：PASS
- G08 I01-I05 测试逻辑：PASS
- 426 passed / 2 skipped：PASS
- published R4.1 LFS restore：PASS
- Accepted Head discipline：PASS

## B05 已关闭

V4-02 go-forward 历史 frozen binding：

`83fa37ded40337d69ff0e447a0b6a3bc293d2ca95ea9c8aa009f0f104776c4be`

Git blob 未变化；R4.1 证明该值来自历史 CRLF 表示，并把 downstream governance identity 统一切换到：

`CANONICAL_JSON_SHA256_V1`

V4-02 go-forward canonical JSON identity：

`206581adca674841a21a7497a3f73ce22dbedd0f18f2ce38bed003df8f42dac9`

fresh clone 重新构建 10 个输出，全部逐字节一致。

**B05 = PASS**

## R4.1 的 exact lineage 已经变化

### Core Profile

R4 logical digest：

`c0572e7c9d481ee8b1a251779df2bf15bce98f1728a57ff8e96ba7ae2219fb77`

R4.1 logical digest：

`d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74`

R4 artifact：

`2b1f881fc408f044253df617a1ce735e57029bf27f275ec9a8bb159acdc5b3be`

R4.1 artifact：

`9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0`

### Full Scope Factors

R4 artifact：

`85775ffd490853e8483294e5a61e17e842e754dbb7c80c3f096c132771df5df3`

R4.1 artifact：

`17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48`

### Market Reference

R4 1-session output digest：

`c37a73892565b7f019d441be0910cdd726cc83865cc600441085ac48fb2d30c6`

R4.1 1-session output digest：

`80d8ac5cc69e8ae4d165f89324e45d0cc7e49a81d13339b31ff8fbec5e578554`

所以 R4.1 是新的 exact lineage candidate。

## 当前 G08 的实际错误

`scripts/run_v4_05_r4_1_postgres_ledger.py` 中：

`source_specs()` 实际读取：

- `V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json`
- `V4_05_R4_CORE_PROFILE_REPLAY.json`
- `V4_05_R4_MARKET_REFERENCE.json`
- `V4_05_R4_PERIOD_ASOF.json`

`run_ledger()` 同样读取：

- `V4_05_R4_MARKET_REFERENCE.json`
- `V4_05_R4_CORE_PROFILE_REPLAY.json`

因此 PostgreSQL receipt 中：

`logical_output_identity_sha256 = c0572e7c...`

仍是旧 R4 Core Profile logical digest，而不是 R4.1：

`d1955187...`

Formal ledger source manifest 也继续绑定：

- old Core Profile artifact `2b1f...`
- old Full Scope Factors artifact `8577...`
- old Market Reference identity

这与当前 R4.1 candidate manifest 不一致。

## 为什么阻断

Replay Gate A 的 revision/idempotency 是 identity-level gate。

业务值虽然完全相同，但 R4.1 canonical hash 修复后：

- source manifest
- computation identity
- logical output identity
- artifact lineage

都已变化。

不能用“R4 业务值等于 R4.1”代替：

> 当前 R4.1 exact candidate identity 在正式 PostgreSQL schema 下通过 idempotency / revision / rollback。

所以：

**B03-R4.1 = FAIL / BLOCKING**

## G08 测试框架本身无需重做

I01-I05 逻辑质量是合格的：

- identical replay no count/head drift
- changed source revision append
- parent/lineage/revision/core/head/state negative guards
- rollback at 3 injection points
- prior-state freeze

只需要把 baseline source manifest 与 state logical digest 换成 R4.1 exact candidate，并增加 cross-binding assertion。

## 当前阶段纪律

`data/v4/V4_05_ACCEPTED_HEAD.json = ABSENT`

`V4_STAGE_ACCEPTED_HEAD = V4_00_TO_V4_04_ACCEPTED; V4_05_NOT_ACCEPTED`

未发现 V4-06/V4-07/V4-08 正式越级启动。

PASS。

## 最终结论

`V4_05_EXTERNAL_ACCEPTANCE_BLOCKED_R4_1`

唯一 blocker：

`POSTGRES_LEDGER_TESTED_R4_NOT_R4_1_EXACT_IDENTITY`

这是非常小的 targeted repair。

不需要重做 Period、Market Reference 算法、Factors、Core Profile、B05 clean clone、LFS、真实市场样本。

修复 exact candidate binding 后，直接进入 V4-05 最终外部验收。
