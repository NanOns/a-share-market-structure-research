# M7B-05 History Job Contract v1

版本：`history-job-state-v1.0`；任务类型固定为 `HISTORY_ANALYSIS`。

## 任务身份与存储

API06 使用现有 `jobs`、`job_attempts`、`job_events`，不创建第二套 `analysis_jobs`。`jobs.payload_json` 保存 `job_kind`、`request_identity`、`planned_domains`、`completed_slice_ids`、进度和错误；大结果只保存分片 ID 引用。请求必须绑定成功发布和已验证的 `SourceManifest`，`basis` 只能是 `OBSERVED` 或 `RECONSTRUCTED`（`AUTO` 在服务端解析为 `OBSERVED`）。

同一规范请求和幂等键复用原任务。`slice_id` 是可选的已准备工作单元；服务校验分片存在且属于计划域，不在本步骤计算技术/结构因子，也不改变 publication head。

## 状态和恢复

- `QUEUED`：请求与 attempt 已持久化。
- `RUNNING`：worker 正在批次边界之间推进。
- `SUCCESS`：所有已计划分片完成；无分片时明确标记 `PLANNED_ONLY`。
- `CANCELLED`：收到取消请求并在批次边界停止；已完成分片保留。
- `INTERRUPTED`：进程恢复时将无执行者的运行 attempt 标记为中断。
- `FAILED`：错误和最后进度写入 job/attempt/event。

API08 需要 `expected_attempt`，终态任务不可取消。取消只设置持久化 `cancel_requested` 和内存取消点，不删除 `analysis_slices`、`storage_objects` 或已经 seal 的结果。恢复通过新 attempt 继续读取 `completed_slice_ids`，跳过已完成分片。

## 接口

- `POST /api/history/jobs`：返回 HTTP 202 和 `JobStatus`。
- `GET /api/history/jobs/{job_id}`：返回 `JobStatus`，不存在返回 404。
- `POST /api/history/jobs/{job_id}/cancel`：返回取消请求后的 `JobStatus`；attempt 不匹配或终态返回 409。
