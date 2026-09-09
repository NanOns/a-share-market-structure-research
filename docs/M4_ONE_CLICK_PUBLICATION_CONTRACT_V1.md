# M4 一键发布合同 V1

版本：`m4-one-click-publication-contract-v1.1`

任务幂等键只包含目标交易日、`source_bundle_id`、经济模型身份和计算合同身份；展示代码变化不生成新观察。提交操作把正式结果、不可变 Forward 观察、到期结算、发布头以及任务成功状态放入同一个数据库事务。

提交前中断必须整体回滚，不得出现发布头或业务行；重试建立新 attempt。提交后确认丢失时，以确定性 `publication_id` 检查正式库，恢复任务为成功，不重复写观察或结算。同一观察的结算以 `(observation_id, horizon, target_revision)` 唯一。

后台提交立即返回 `job_id`；查询通过任务状态和按 attempt 排序的事件恢复进度。计算回调不得改变输入、模型或计算合同身份。

发布前强制调用 M3 bundle 消费校验；不存在、身份不符或内容被改动的 bundle 一律阻断。任务请求完整持久化，启动恢复把无有效执行者的 RUNNING attempt 标为 INTERRUPTED，并建立新 attempt。Forward outcome 必须引用事务内或既存的 observation；全部工作台核心结果与发布头在一个事务提交。
