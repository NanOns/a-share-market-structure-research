# A04 R3｜Amount-A Formal Authority Scoped Closure 任务卡｜2026-10-01

**基线 HEAD：** `66ef2e342dd339cc9795c2d1fd774b8edec4c345`  
**当前结论：** `ENGINEERING_PASS_FORMAL_AUTHORITY_BLOCKED_R3`

## 1. Namespace 先冻结

明确：

```text
Amount A = sector amount_a_value
```

不包括：

```text
stock amount_ratio20
stock amr20_mean_prior
ordinary raw AMOUNT
```

生成 machine-readable namespace contract。

## 2. 不寻找“能过测试”的万能 coverage threshold

审计旧 `sector_amount/M10` 中：

```text
min members = 5
coverage = 0.8
```

到底属于：

```text
Amount-A 自身质量门
Sector Core safety 门
或旧实现 convenience default
```

只有存在可验证 authority 才可正式复用。

否则禁止把 5/0.8 直接写成 Amount-A universal threshold。

## 3. Formal value 与 consumer gate 分离

Producer 输出：

```text
amount_a_value
comparable_member_count
target_member_count
coverage
window_coverage
quality reasons
contract_id
```

是否允许具体 consumer 使用，由 consumer-specific accepted gate 决定。

不得因为没有统一 coverage threshold 就把已具备完整 source/membership 的算术值强制 null。

但 source/membership 不足时仍 UNKNOWN。

## 4. H21 membership

历史 20 prior sessions 优先寻找真正可证明的 accepted/PIT membership source。

若无法证明：

```text
historical formal Amount-A = BLOCKED
```

禁止 current snapshot 回填历史。

## 5. Go-forward scoped authority

允许建立：

```text
AMOUNT_A_FORMAL_AUTHORITY_GO_FORWARD_V1
```

从真实 accepted membership observations 开始逐日积累。

不足 H21：

```text
WARMUP / UNKNOWN
```

无需等待 21 个未来交易日才能完成 producer 工程与合同验收。

## 6. Historical limitation

若无 PIT source，正式记录：

```text
PRE_BASELINE_HISTORICAL_AMOUNT_A_NOT_FORMALLY_RECONSTRUCTABLE
```

## 7. V4-11 independence

新增跨模块测试：

```text
A04 status / Amount-A rows 改变
不得改变 V4-11 stock confirmation
```

## 8. V4-08 legacy consumers

列出所有 Amount-A consumer：

```text
继续 diagnostic 的 consumer
未来可用 go-forward authority 的 consumer
consumer-specific quality gate
```

未经外部接受不得启用。

## 9. 完成

若 go-forward contract/evidence 成立：

```text
A04_R3_GO_FORWARD_FORMAL_AUTHORITY_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

历史 capability 可继续 scoped blocked，不阻塞主工程。
