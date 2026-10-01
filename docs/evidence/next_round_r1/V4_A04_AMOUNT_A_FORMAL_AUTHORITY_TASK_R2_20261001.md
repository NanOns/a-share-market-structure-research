# A04 Amount-A Formal Authority 任务卡 R2｜2026-10-01

**基线 HEAD：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`  
**Audit：** `AUD-AMOUNT-A-06`  
**优先级：** P1 Parallel  
**重要：** V4-11 本轮 Amount-A formal branch 继续 DISABLED，直到 A04 外部接受。

## 1. 目标

把 Amount A 从模糊字段升级为严格合同：

```text
source
unit
denominator
20-session window
coverage
concentration
UNKNOWN
```

## 2. Source archaeology

全仓找出：

```text
Amount A 的生产者
缓存/DB 字段
旧算法公式
UI/consumer
```

输出 repo-wide consumer inventory。

## 3. 单位

明确：

```text
元 / 万元 / 亿元
shares / currency
raw provider unit
canonical internal unit
```

禁止隐式换算。

## 4. Denominator

明确 20-session denominator：

```text
exact session list
actual/evaluable requirements
suspension treatment
data gap treatment
listing warm-up
```

禁止“20 rows”代替 20 个合法 market sessions。

## 5. Coverage

必须定义：

```text
coverage numerator
coverage denominator
coverage quality
UNKNOWN threshold semantics
```

阈值若无权威合同，不得擅定。

## 6. Concentration

如 Amount A 参与 concentration：

```text
分子/分母
成员 universe
timestamp
weighting
```

全部显式。

## 7. Independent arithmetic

选真实跨板块/新股/停牌/缺口样本，从原始金额独立重算。

不能直接对照 producer 自己结果。

## 8. Consumer isolation

在外部接受前：

```text
V4-11 formal Amount-A branch DISABLED
其他 formal consumers 不得启用
```

## 9. Candidate

可以形成：

```text
AMOUNT_A_FORMAL_AUTHORITY_CANDIDATE_V1
```

但不注册 accepted owner。

## 10. 验收

至少覆盖：

```text
unit conversion
20-session exactness
listing warmup
suspension
real data gap
coverage
concentration
consumer inventory
no fallback 0/FALSE
clean regression
```

结束：

```text
A04_AMOUNT_A_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```
