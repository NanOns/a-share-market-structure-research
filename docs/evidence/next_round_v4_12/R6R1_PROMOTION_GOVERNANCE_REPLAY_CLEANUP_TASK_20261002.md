# R6R1｜Promotion Governance / Replay Cleanup Task｜2026-10-02

**优先级：** P0 Governance  
**当前远端 HEAD：** `2e3e811eb08d7e350e27c4c1e2767ba91160ef98`  
**Stage Head：** KEEP `V4_00_TO_V4_11_ACCEPTED`  
**Data Head：** KEEP `2026-09-30`  
**V4-11 Promotion：** KEEP PASS  
**V4-12 Stage Entry：** KEEP PASS SCOPED

# 1. 目标

只关闭：

```text
G01 unauthorized AGENTS.md mutation
G02 hardcoded local bundle path
```

不得重做或回滚 V4-11 promotion。

# 2. G01｜恢复 AGENTS.md

把：

```text
AGENTS.md
```

恢复为：

```text
git show
1c46d6681ba1d0540551bcc0f75b35c545ff2769:AGENTS.md
```

的 exact bytes。

必须删除 R6 未授权增加的第 10 条。

要求：

```text
business/config/data/stage heads unchanged
```

不得用新的追加规则替代原第 10 条。

# 3. G02｜prepare source portability

修改：

```text
scripts/prepare_v4_11_promotion_r1.py
```

禁止任何固定个人目录，例如：

```text
D:/Users/lps/Desktop/...
C:/Users/...
~/Desktop/...
```

正式行为：

## 3.1 Repo-first

如果：

```text
AUDIT
MASTER
TASK
```

已存在 repo：

```text
只做 exact validation
不覆盖
不从外部重新复制
```

## 3.2 Bootstrap-only explicit source

如果 repo 缺文件：

```text
允许显式：
--bundle-dir <path>
```

只读取：

```text
basename(AUDIT)
basename(MASTER)
basename(TASK)
```

并在写入前记录：

```text
source path
source sha256
source bytes
destination
```

禁止：

```text
递归搜索
latest-file 猜测
Desktop fallback
任意目录自动发现
```

## 3.3 Fail closed

缺 repo bundle 且没有显式参数：

```text
R6_EXTERNAL_BUNDLE_SOURCE_REQUIRED
```

# 4. 不得改变 promotion identity

以下必须 exact unchanged：

```text
data/v4/V4_11_ACCEPTED_HEAD.json
data/v4/V4_STAGE_ACCEPTED_HEAD.json
data/v4/V4_DATA_ACCEPTED_HEAD.json
reports/v4_12/V4_12_STRUCTURE_ANCHOR_SUPPORT_STAGE_ENTRY_R1.json
```

Stage Head 继续：

```text
V4_00_TO_V4_11_ACCEPTED
```

# 5. 测试

新增至少：

```text
test_agents_exact_baseline
test_prepare_repo_first
test_prepare_missing_bundle_fails_closed
test_prepare_explicit_bundle_dir
test_prepare_has_no_absolute_user_path
test_heads_byte_identical
```

`prepare` 测试必须使用临时目录，不得依赖用户真实 Desktop。

# 6. Clean replay

从 clean checkout 验证：

```text
promotion validator post=true PASS
V4_11 head exact
Stage Head exact
Data Head exact
V4-12 Stage Entry exact
AGENTS baseline exact
prepare repo-first PASS
```

# 7. 禁止

```text
重新 promotion
推进 Stage Head
推进 Data Head
执行 V4-12 runtime
开放 production/shadow/focus
修改 R5 business evidence
```

# 8. 完成状态

只允许：

```text
R6R1_GOVERNANCE_REPLAY_CLEANUP_CANDIDATE_READY_FOR_EXTERNAL_AUDIT
```
