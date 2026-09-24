# 07C-04：UNKNOWN 保留已确认事实并接入观察链路

## 阶段合同

`FOCUS_PATH_STATE_V2` 与 `FOCUS_OBSERVATION_ASSEMBLY_V2` 为新 observation 附带解析字段和 predicate evidence。V1 `current_path_state` 原字段保持原样；不得覆写 23/24 日 accepted observation。V2 字段必须进入 observation digest、core input closure 校验和 items API。

## 实施

- Observation assembler 同时运行原 V1 分类和 V2 resolver；在 `facts.path_state_v2` 保存 `resolved_primary_state`、`best_confirmed_state`、阻断 UNKNOWN、解析状态、所有已确认状态和谓词证据。
- Core input closure 校验 V2 合同、predicate evidence 一致性、解析枚举及主状态约束。
- Focus items API 从 observation facts 返回 `path_state_v2`；历史 observation 没有该字段时返回 null。episode API 原本返回完整 facts，因此无需另改字段映射。
- 定向验证：path state V2、observation assembly、core input closure 共 59 项通过（含 07C-05 session-gap 套件）；生产 PostgreSQL items API 读取 2026-09-24 返回 HTTP 200 / AVAILABLE，并含兼容字段。

## 24 日只读回查

对 run `focus-run-2a6378107492da723111cc78394a1248` 的 397 条历史 predicate evidence 执行 V2 解析，无数据库写入：317 条 `READY`、80 条 `UNAVAILABLE`，`PARTIAL`/`AMBIGUOUS` 均为 0。此回算直接使用已存 V1 predicate evidence，不代表在新版 assembler 下重建的结果。新版 assembler 对同一 24 日 accepted publication 做全批只读重建后，manifest `3ef5b6f4810968b6f9d68b88d0cdfd2c5ed17febf1830fe8f36ee6f6f68f5920`、source identity 不变、closure 397/397；V2 结果为 READY 74、PARTIAL 243、UNAVAILABLE 80。manifest 与已持久化 V1 运行不同，是版本化 observation/gap 证据变化；没有改写数据库。该日旧 observation 的 V2 API 值为 null，符合不回填历史合同的要求。synthetic / unit examples separately cover PARTIAL and AMBIGUOUS. 详细结果见 `reports/upgrade_m3/FOCUS_PATH_STATE_V2_20260924_READBACK.json` 与 `reports/upgrade_m3/FOCUS_07C_V2_GAP_SEMANTICS_20260924.json`。

## 验收与下一阶段

`07C-04 / INTEGRATED_CODE_PASS / LIVE_INPUT_READBACK_PASS`。24 日 V2 仅为只读推导；新版本代码未来创建的 observation 才持久化 V2 facts。接下来冻结 `FOCUS_SESSION_GAP_SEMANTICS_V1`，分别定义 confirmed suspension、unverified data gap 和 source unavailable 对价格路径、rolling 与 consecutive predicates 的影响。
