# M7B-06 Snapshot Activation Contract v1

版本：`history-snapshot-activation-v1.0`。

## 预计算与身份

激活前从成功的 `HISTORY_ANALYSIS` job 读取已完成 `slice_id`，校验每个 slice、日期上限、domain/date 唯一性和 SourceManifest。随后原子写入不可变分析清单，并以清单内容生成 `manifest_hash` 和 `snapshot_id`；`analysis_snapshots` 先登记为 `PREPARED`，不把准备状态当成可查询结果。

清单包含 cutoff/query_start、范围合同、`OBSERVED`/`RECONSTRUCTED` basis、来源身份、合同包和每个分片的 input/dependency/logical hash。快照 ID 不依赖“当前 head 查询结果”生成；head 只在最后的激活事务中做 compare-and-swap。

## 激活事务

API09 要求 `expected_head_id` 与 `idempotency_key`。事务校验目标发布仍为成功且 head 未变化，创建确定性的新 publication revision，复制旧发布的已封存业务引用，写入 `analysis_snapshots=SUCCESS` 和 `publication_analysis_snapshots`，再更新该交易日 head。旧 publication、旧 head 绑定和旧快照不更新。

重复相同激活身份返回原结果；同一 job 使用不同内容或身份再次激活返回冲突。任一步失败整体回滚，不留下新 head。API09 不会覆盖旧发布，也不会删除分片或对象。

绑定域由 basis 显式决定：`OBSERVED → LOCAL_OBSERVED`，`RECONSTRUCTED → LOCAL_RECONSTRUCTED`。当前分析 job 可以只绑定已经准备的域；没有完成分片时激活被拒绝。
