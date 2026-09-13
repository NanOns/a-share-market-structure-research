# V3 P10-03：记录前瞻结果与简单基线

## 阶段合同

执行前读取最新适用升级文档 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，适用范围为 §8.2、§14.1–§14.2、§18.13 P10-03、§20.3–§20.8；本阶段合同为 `V3_P10_SIGNAL_EVALUATION_V1_0`，主文档 SHA-256 由机器回执运行时读取。

目标是把 POTENTIAL 的首次信号封存为只读输入，在 3/5 个交易日到期时记录 CURRENT 首次确认和固定信号日成员的复权收盘收益诊断；历史重建与真实前瞻分开，尚未到期为 `PENDING`，证据缺失为 `DATA_GAP`。收益只用于描述性观察，不是回测、可成交收益或概率结论。

## 实现

- `src/workbench_service/research_signal_evaluation.py` 提供版本化合同、信号日 hash、episode 首次去重、3/5 交易日 due date、CURRENT 确认、固定成员收益覆盖、三组等量基线、样本门槛和独立 outcome writer。
- `research_signal_outcomes` 由 `src/workbench_db/migrations/034_v3_signal_outcomes.sql` 注册，`ResearchRunStore` 的本地研究 schema 同步声明；outcome upsert 只写 outcome 表，不更新 `research_sector_signal_state`。
- `research_builder.py` 为新生成的首个 POTENTIAL episode 写入由板块和首次日期派生的稳定 `episode_id`；当前状态仍不回写历史信号。
- `ResearchQueries.signal_evaluation` 和 `GET /api/v3/research/evaluation` 为只读查询；V3 页面增加“规则观察·效果验证中”状态、PENDING/OBSERVED/DATA_GAP 数量和三组基线数量展示。

## 输入、计算与落点

| 能力 | 输入 | 计算/规则 | 落点 |
|---|---|---|---|
| 首次信号 | `research_sector_signal_state` 与对应 `research_sector_states` | 只保留 `potential_eligible=true` 的 episode 首行；信号日已 CURRENT 不进入提前样本；重复列表日不增加独立 episode | `episode_id`、`signal_hash`；不改信号行 |
| 到期确认 | 同一合同的未来 CURRENT 状态和主交易日历 | t+1..t+3/t+5 首次 CURRENT，记录 `confirmed_date` 和 `lead_sessions`；缺未来日期不是失败 | outcomes 的 `confirmed_*`、`PENDING/DATA_GAP` |
| 固定成员诊断 | 信号日固定成员集、信号日和 due date `adj_close` | due date 复权收盘收益中位；覆盖率 ≥ 0.70 才填中位数；不把收益当交易绩效 | outcomes 的 `member_forward_*` |
| 基线 | 同日同类型非 CURRENT 总体、q20 非 CURRENT、dq5_3 非 CURRENT | 先按目标信号数量等量截取，再稳定排序；不跨日期/类型借样本 | 只读 API `baseline_summary` |
| 效果门槛 | 去重后的信号日与 episode 数 | `<20` 信号日或 `<50` 独立 episode => `EFFECT_INSUFFICIENT`，页面显示“规则观察·效果验证中” | API `sample_gate`、机器回执 |

## 证据与验收

阶段脚本：`scripts/verify_p10_03_signal_evaluation.py`；机器回执：`reports/upgrade_v3/P10-03-SIGNAL-EVALUATION.json`。

验收覆盖：

1. 合成首次信号重复日只产生一个 episode，PENDING 在 due date 尚未可见时正常存在。
2. 已观察的 3/5 日记录 CURRENT 首次确认和固定成员收益；未来日期缺失、成员依据缺失和行情缺失进入 `DATA_GAP`，不转成负确认。
3. 给同一信号附加 t+5 未来字段不会改变 `signal_hash`；future fields 不在 hash 白名单内。
4. 三组基线按同日、同类型和目标等量选择；不足 20 信号日/50 episode 时不输出效果通过。
5. outcomes upsert 可重复执行且无重复行；研究信号状态行保持不变；V3 页面和只读 API 显示观察状态。
6. 真实库仅做只读检查：本次当前真实 run 为 1 个 COMPLETE 日期，当前封存 episode 为 0，因此真实效果状态保持观察中，不作效果结论。

## 阶段结论与下一步

本阶段功能链可以 `FULL_PASS`：评估规则、PENDING/DATA_GAP、未来信息隔离、基线和只读展示均有代码与测试证据。真实样本门槛未达到，`effect_status=EFFECT_OBSERVATION_PENDING`；这不是算法效果通过。下一阶段为 P11-01，继续做整体内部验收、真实性能和存储审计。
