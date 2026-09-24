# 07C-05：Session Gap Semantics 合同

## 阶段合同

新增 `FOCUS_SESSION_GAP_SEMANTICS_V1`，把每个主交易日划为 `ACTUAL_BAR`、`SUSPENDED`、`DATA_GAP` 或 `SOURCE_UNAVAILABLE`。

| 操作 | `ACTUAL_BAR` | `SUSPENDED` | `DATA_GAP` | `SOURCE_UNAVAILABLE` |
|---|---|---|---|---|
| `CONSECUTIVE` | 参与判断 | 该窗口结果 `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |
| `ROLLING` | 参与固定主日历窗口 | 窗口不可判定，不跳过 | 不可判定 | 不可判定 |
| `PATH` | 参与价格度量 | 仅可桥接首尾实际行情之间且审计标记一致的停牌 | 路径不可用 | 路径不可用 |

停牌必须同时满足 `trade_status_known=true`、`is_synthetic_fill=true` 且无实际 bar；矛盾即失败关闭。`FILE_MISSING`、`NOT_LISTED_YET`、`DELISTED_OR_INACTIVE` 映射为 `SOURCE_UNAVAILABLE`；`MISSING_DATA`、`INFERRED_GAP` 与未登记状态映射为 `DATA_GAP`。缺日记录本身映射为 `SOURCE_UNAVAILABLE`。两种未知原因均不转换为 FALSE，但证据分别保留。`ROLLING` 同样按主日历固定窗口，不压缩停牌或缺口；当前 AST 暂无 ROLLING 运算符，合同先冻结未来解释。

## 实施与证据

- 新模块 `src/focus_tracker/session_gap_semantics.py` 统一状态分类和 CONSECUTIVE / ROLLING / PATH 窗口门。价格路径与连续 AST 共用同一状态分类；CONSECUTIVE 证据区分 `SUSPENDED`、`DATA_GAP`、`SOURCE_UNAVAILABLE`。
- 连续谓词的 lookback 增加 `session_state`。初始依赖版本为 `FOCUS_PREDICATE_REQUIREMENTS_V2`、`FOCUS_PREDICATE_FACTS_BY_DATE_V2`、`FOCUS_INVALIDATION_AST_V2`、`FOCUS_SOURCE_PATH_CAPABILITIES_V3`；Repair R1 新增按日事实中的 RPS20 provider-gap 身份并将该合同升至 `FOCUS_PREDICATE_FACTS_BY_DATE_V3`，tracked V3.3 invalidation 同步升至 `FOCUS_V33_TRACKED_INVALIDATION_V3`。旧版本历史记录不回写。
- `FOCUS_PATH_STATE_V2` 使用显式股票/板块优先级序列解析，不依赖 JSONB object 键顺序。
- 定向测试覆盖分类、审计字段矛盾、停牌连续门、rolling 主日历门、价格路径仅桥接内部确认停牌，以及三类 gap 对连续谓词均返回 UNKNOWN 并保留原因。组合验证共 59 项通过。
- 2026-09-24 accepted publication 对新版 assembler 的只读全批重建：117 来源行、397 tracking key、397 observation，closure 397/397；V2 为 READY 74、PARTIAL 243、UNAVAILABLE 80。manifest `3ef5b6f4810968b6f9d68b88d0cdfd2c5ed17febf1830fe8f36ee6f6f68f5920` 与持久化 V1 manifest 不同，来源身份相同；只读操作，未改动 accepted run/head。
- 本地 24 日标准化数据没有 `CONFIRMED_SUSPENSION` 正样本；真实停牌复牌的正向 Forward 验收等待后续样本。

## 验收与下一阶段

`07C-05 / CONTRACT_AND_SYNTHETIC_PASS / REAL_SUSPENSION_FORWARD_PENDING`。07C 算法合同与代码验收已完成，24 日提供了真实 V2 前向输入只读回算；尚缺新版 observation 的正式落库和真实确认停牌后复牌样本。接下来随下一交易日 accepted publication 重新执行 07A writer、readback 与 V2 evidence 核验；同时积累 07A 五日门、310 个待结算 outcome 的到期结果，以及 07B 真实停牌样本。07D UI 增强仍以后续 07A/07B 真实 forward 总门为前提。

详细量化证据：`reports/upgrade_m3/FOCUS_07C_V2_GAP_SEMANTICS_20260924.json`。
