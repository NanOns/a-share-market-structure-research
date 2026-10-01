# A02 外部接受正式化 + V4-05/V4-07/V4-09 Amendment Candidate 任务卡 R1｜2026-10-01

**基线 HEAD：** `66ef2e342dd339cc9795c2d1fd774b8edec4c345`  
**外部结论：** `PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE`

## 1. Phase A｜正式化 A02

将本轮独立审计加入 repo，创建 versioned A02 acceptance record。

接受范围：

```text
V4_RPS_PIT_HISTORY_V1
2026-09-22/23/24/28/29/30 publications
RECONSTRUCTED_CORRECTED
delta1/delta3 exact
```

禁止：

```text
AS_RECORDED
历史 first-availability 声明
runtime prior-RPS 现场重算
```

## 2. Accepted RPS Head

创建独立 versioned：

```text
V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1
```

不要复用 V4_DATA_ACCEPTED_HEAD。

## 3. Phase B｜downstream replay

以刚接受的 A02 RPS Head 为唯一 prior-RPS source，重新执行：

```text
V4-05 affected profile/factor projection
V4-07 Base Seed
V4-09 Stock PREWATCH
```

算法/参数保持原 Accepted 版本。

## 4. 必须核对既有大 diff

预期当前 evidence：

```text
V4-07 changed rows = 5222
V4-09 changed rows = 2811
```

若数字变化，必须解释 source/version 原因，不能只更新 expected。

## 5. Amendment candidates

生成：

```text
V4_05_ACCEPTED_HEAD_AMENDMENT_A02_CANDIDATE
V4_07_ACCEPTED_HEAD_AMENDMENT_A02_CANDIDATE
V4_09_ACCEPTED_HEAD_AMENDMENT_A02_CANDIDATE
```

绑定：

```text
old accepted head
A02 accepted RPS head
unchanged algorithm/parameter digests
full business diff
```

## 6. 不 promotion

本卡禁止覆盖 V4-05/V4-07/V4-09 Accepted Head，也不得推进 Stage Head。

业务输出发生实质变化，必须等待下一轮独立验收。

## 7. V4-11 interface

A02 accepted RPS 可以成为未来 V4-11 `rps5_delta3/rps20` source candidate。

但 V4-11 R2 未独立接受前不得自动开启 real confirmation。

## 8. 完成

```text
A02_EXTERNAL_ACCEPTANCE_FORMALIZED = PASS
A02_DOWNSTREAM_AMENDMENTS_READY_FOR_EXTERNAL_REAUDIT
```
