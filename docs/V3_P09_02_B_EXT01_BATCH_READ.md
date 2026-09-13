# V3 P09-02-B-EXT01：有界批次读取

## 阶段合同

本小任务依据最新 V3 主实施文档 SHA-256 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B` 的 §8.3、§19.4、§19.5、§22.3 执行，批次合同为 `v3-lz-ext01-batch-read-v1.0`，适配器为 `v3-lz-ext01-event-adapter-v1.0`。

范围仅限 EXT01 涨停池的内存批次读取：

- 复用 EXT01 合同 URL，页大小硬上限 20，最多读取 4 页，单源请求沿用 8 秒/2 MiB/零重试，并受 12 秒总预算约束。
- 每页只保留状态、URL、HTTP、字节数、raw 哈希和行数等脱敏证据；不保留响应 body。
- 明确分页元信息后才标记 `complete_pagination=true`；缺失元信息或达到边界时标 `PARTIAL_OR_UNVERIFIED`，不声称全市场。
- 同一批次按 `(pool_type, source_code)` 去重；相同行计为 duplicate，冲突行保留首条并增加 `DUPLICATE_CONFLICT`，不静默拼接。
- 首页失败返回 `UNAVAILABLE`；后续页失败保留已成功页并返回 `DEGRADED`，不把部分数据替换为空成功。
- 生成的 `batch_id` 仅为内存逻辑批次标识，不改变本地 run 身份；头统计仍与成员行分离。

当前 EXT01 字段倍率、金额单位和梯队语义仍未确认，因此成功读取的源能力保持 `DEGRADED`，不连接 API/UI，不写 `online_payloads`、`online_batches` 或事件生产表。

## 验收证据

机器回执：[P09-02-B-EXT01_BATCH_READ.json](../reports/upgrade_v3/P09-02-B-EXT01_BATCH_READ.json)。验证命令：

```text
python -m pytest -q tests/upgrade_v3/test_p09_02_b_ext01_batch_read.py
python scripts/verify_p09_02_b_ext01_batch_read.py
python -m compileall -q src/workbench_online/event_batch.py scripts/verify_p09_02_b_ext01_batch_read.py
git diff --check
```

本小任务的代码合同验收为 `FULL_PASS`；数据源/产品切片仍为 `DEGRADED`，后续需单独完成允许收盘批次存储和 API/页面验收。

## 下一步

下一小任务为 `P09-02-C-EXT01-CLOSE-BATCH-STORE`：仅为允许归档的收盘事件建立版本化批次/头/成员表绑定，继续禁止 raw 热榜或本地 run 身份写入。
