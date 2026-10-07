# V4-only 全量测试独立外部验收审计 R1｜2026-10-07

- Repository: `NanOns/a-share-market-structure-research`
- Branch: `codex/v4-system-reform`
- 用户修订范围：只要求 V4 全量测试，不要求 V4 之前版本的全量/历史测试
- 当前远端 HEAD: `d68adc4a17d4546b7dfb486ea37096eb2b79408a`
- 代码提交: `ade080cbe838da90a359ff7fe829af76c539ea06`

## 1. 唯一总裁决

```text
V4_ONLY_FULL_REGRESSION_EXTERNAL_AUDIT =
BLOCKED_ONE_SCOPE_OMISSION

CURRENT_V4_EXECUTED_PROFILE =
PASS_SCOPED

V4_FULL_TEST_COMPLETE =
NOT_YET

REMAINING_BLOCKER =
tests/test_r17a_historical_governance.py
was omitted by V4-only selector
```

当前已执行的 V4 profile 本身结果为：

```text
4759 total
4757 passed
0 failed
0 errors
2 skipped
```

但因为 scope selector 漏掉一个明确属于当前 V4 的测试文件，所以不能称“V4 全量测试完成”。

## 2. 用户范围修订有效

用户明确将执行范围改为：

```text
V4-only
exclude all preceding versions
```

因此此前 60 个 V4 之前历史产物缺失失败：
- 不再作为 V4 regression blocker；
- 不能计为 PASS；
- 不能伪造历史 artifact；
- 旧历史测试仍保留。

当前代码已经撤回此前对旧测试的退役尝试，恢复原文件，并明确将混合版本全量结果标成 prior investigation，而不是 V4 acceptance。

## 3. V4 主回归结果

正式 receipt：

```text
4759 total
4757 passed
0 failed
0 errors
2 skipped
ignored=[]
deselected=[]
new_xfail=[]
```

两个 skip 都是 Windows runner 无法创建真实 symlink：

```text
tests.v4_phase0.test_tdx_local_snapshot::test_symlink_input_is_rejected
tests.v4_phase0.test_tdx_snapshot::test_extracted_symlink_is_rejected
```

同时已有 portable equivalent / reparse / junction / child-process boundary negative proof，因此当前不构成业务 blocker。

## 4. PG replay 合法

首跑出现 PG fixture setup errors，后续使用：
- disposable V4 SQL environment；
- 33 个 migration checksum；
- 空 V4 template；
- exact affected-module replay；

所有原失败/错误节点都有真实 replay PASS，且：
- 原测试断言未修改；
- 没有 ignore/deselect/xfail；
- replay 只覆盖原失败所属 V4_10/V4_11 和明确 closure nodes。

因此：

```text
PG_ENVIRONMENT_REPLAY = PASS
```

## 5. TDX fresh zero-write 闭环

历史事故仍永久保留：

```text
old incident:
5 write calls
4 TDX files
FAILED_RUN_ZERO_WRITE=false
```

本次 fresh V4-only run：
- 测试前后逐文件 SHA/size/mtime fingerprint；
- absolute / drive-letter / UNC / traversal / reparse / child-process guard；
- TDX pre/post exact equal；
- fresh write calls = 0。

因此：

```text
TDX_READ_ONLY_BOUNDARY_CURRENT_RUN = PASS
```

但旧事故不能被改写成“从未写过”。

## 6. V1 CURRENT_RELEASE scope

`reports/current/CURRENT_RELEASE.json` 已被明确冻结为 historical diagnostic binding。

当前 V4 authority：

```text
config/v4_current_stage_authority_v2.json
```

没有 current runtime reader 继续把旧 pointer 当 current authority。

因此：

```text
V1_CURRENT_RELEASE_IDENTITY_DRIFT =
CLOSED_AS_HISTORICAL_SCOPE
```

## 7. IA-08 historical reader

clean checkout 结果：

```text
20 historical binding occurrences
15 unique historical identities
all exact = true
branch moved = false
working tree clean
historical_permission = false
```

所以：

```text
IA-08 = PASS
```

## 8. IA-07

当前 accepted snapshot：

```text
population=5037
RPS20 nonmissing=0
prior20_mean_amount nonmissing=0
vol20 nonmissing=0
hard_safety_pool=0
complete_rank_population=0
```

Codex 没有合成控制池，也没有把 0 eligible rows 写成 FULL_PASS。

正确状态：

```text
IA-07 =
NOT_VERIFIABLE_BY_CURRENT_ACCEPTED_CAPABILITY
```

当前合同明确：

```text
ABSOLUTE_FORWARD_SETTLEMENT
independent from benchmark controls
```

所以 IA-07：
- 阻断 control-matching capability 的接受；
- 不阻断独立股票绝对结算；
- 不授权 shadow/production/focus。

这个 disposition 合理。

## 9. 关键遗漏：V4-only selector 漏掉当前 V4 测试

当前 selector：

```python
(path.name.startswith('test_r') and 'v4_' in path.read_text(encoding='utf8'))
```

这里 `'v4_'` 大小写敏感。

因此：

```text
tests/test_r17a_historical_governance.py
```

没有进入 212 个 selected files。

但这个文件明确测试当前 V4：
- `data/v4/V4_DATA_ACCEPTED_HEAD.json`
- `V4_00_TO_V4_10_ACCEPTED`
- `V4_00_TO_V4_13_ACCEPTED`
- `historical_stage_governance_r17`
- DM01 accepted chain
- V4 current/historical head separation
- historical binding exactness

它不是 pre-V4 test。

所以：

```text
4759 nodes != complete V4 full suite
```

## 10. 其它可疑排除项

对 outside scope 中名字带 forward/V4/r17 的文件复核：

```text
tests/r4_01/*
tests/r4_01a/*
tests/r4_repair/*
tests/upgrade_v3/*
```

这些属于 V4 之前旧体系 / forward_v3.x / live-forward legacy，不属于用户本次 V4-only execution scope。

当前明确漏测的是：

```text
tests/test_r17a_historical_governance.py
```

## 11. 修复要求

只需要小修：

优先改为：

```python
(path.name.startswith('test_r') and 'v4_' in path.read_text(encoding='utf8').lower())
```

或者建立 explicit V4 root test registry。

随后：
1. 重新生成 `V4_ONLY_EXECUTION_SCOPE.json`；
2. 确认 selected file count 增加；
3. 实际执行 `tests/test_r17a_historical_governance.py`；
4. 最好重新执行一次完整 V4-only profile；
5. 重新生成 regression receipt / candidate seal。

不需要重新做 pre-V4 历史考古。

## 12. Protected state

当前保持：

```text
accepted heads unchanged = true
SQL migrations unchanged = true
protected runtime bytes/mtime equal = true

Production=false
Shadow=false
Focus=false
Default UI=false
real samples added=false
```

没有发现权限偷开或 accepted head 漂移。

## 13. 最终结论

```text
V4_ONLY_EXECUTED_PROFILE =
PASS

V4_ONLY_FULL_REGRESSION =
NOT_YET_COMPLETE

BLOCKER =
ONE CURRENT-V4 TEST FILE OMITTED BY CASE-SENSITIVE SCOPE SELECTOR

BUSINESS_ALGORITHM_NEW_BLOCKER =
NONE_FOUND

TDX_CURRENT_ZERO_WRITE =
PASS

PG_REPLAY =
PASS

V1_CURRENT_RELEASE_SCOPE =
PASS

IA-08 =
PASS

IA-07 =
CAPABILITY_DEBT_NOT_BLOCKING_ABSOLUTE_STOCK_SETTLEMENT
```

建议只做一次极小的 scope 修复 + 漏测补跑，不再做历史考古或 pre-V4 全量。

**文档结束**
