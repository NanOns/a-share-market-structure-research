# Historical Publication Reader Dependency Injection Hardening 任务卡 R1｜2026-10-01

**基线 HEAD：** `bc3e398efb4f4a05c20973ff3cb335a6b101ac87`  
**优先级：** P2 Non-Blocking Hardening  
**当前 accepted 功能：** historical publication readback 已通过 scoped history-only 外部验收

## 1. 背景

当前：

```text
dm01_publication_history_reader_v1.py
```

通过：

```text
RLock
+
临时替换 v4_09/v4_10 module.ROOT
```

执行旧 publication validator 的历史视图。

当前 history-only、安全且串行，但不是长期 production-grade dependency model。

## 2. 目标

改为显式：

```text
ProjectView / FilesystemView / HistoricalBindingResolver
```

dependency injection。

不得修改旧 validator 业务逻辑和历史 acceptance semantics。

## 3. 约束

必须保持旧 validator source bytes：

```text
byte-identical
```

如果必须加 adapter：

```text
在 wrapper 层
```

不能改历史 validator。

## 4. Project View

显式 view 提供：

```text
logical path
→ historical archived exact bytes
```

仅对 exact：

```text
old path
old SHA
accepted archive binding
```

生效。

wrong SHA：

```text
FAIL
```

## 5. Concurrency

必须证明：

```text
两个历史 replay 并发
一个 current validator 并发
```

互不污染。

不能依赖全局变量切换。

## 6. Security boundary

禁止：

```text
arbitrary path remap
directory traversal
candidate artifact masquerading as accepted archive
```

## 7. Parity

新 DI reader 与当前 accepted history-only reader：

```text
V4-09 output/status exact
V4-10 output/status exact
wrong-hash behavior exact
```

## 8. Current business

必须证明：

```text
current movable Data Head 仍为 2026-09-30
旧 validator 直接读 current pointer 仍不被错误视作 old acceptance
```

## 9. Production

本任务完成也不开放 production。

## 10. 验收

结束：

```text
HISTORICAL_PUBLICATION_READER_DI_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT
```

该项不阻断 V4-11/V4-12。
