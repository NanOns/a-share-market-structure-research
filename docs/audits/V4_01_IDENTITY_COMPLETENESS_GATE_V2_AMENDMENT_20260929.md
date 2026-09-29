# V4-01 Identity Completeness Gate V2｜Amendment Candidate

- 日期：2026-09-29
- 合同：`V4_01_IDENTITY_COMPLETENESS_GATE_V2 v2.0.0-candidate`
- 状态：`AMENDMENT_CANDIDATE_PENDING_EXTERNAL_ACCEPTANCE`
- 基线：R7 canonical identity/universe；R8.3 atomic boundary inventory
- 外部验收：待审；本文不自签 V4-01 owner gate

## 迁移理由

现有 `OFFICIAL_SECURITY_CODE_CHANGE_EVENT_INDEX_V1` 已明确记录：CNINFO bounded full-text 查询可以证明查询执行与返回结果，但不能证明 2023-07-04 至 2026-09-24 全窗口、四个 required boards 的事件穷尽性。继续把该索引作为唯一 completeness 门，无法由公开检索接口提供可验证的停止条件。

本 amendment candidate 将索引从“唯一穷尽性门”调整为 `KNOWN_EVENT_CROSS_CHECK / CONFIRMATION_SOURCE`，并组合完整 Required Scope 原子边界、generic relation candidate discovery、source-fingerprint candidate discovery、已知正式事件交叉核验、逐候选 fail-closed resolution 和独立 postcheck。原 V1 索引、coverage receipt 及 `official_index_coverage=BLOCKED` 历史事实保留不删、不改，不声称穷尽覆盖。

## 门语义

1. 以 hash-bound R7 Required Scope 行和 786 个 accepted session 为边界输入，逐相邻 session 扫描 source security key 的进入与退出。首个 session 是左删失基线，不伪装成当日 IPO 边界。与 R8.3 已有 917 个原子边界及零 unlinked anomaly 独立核对。
2. 对每个 source-key entry 读取同 key TDX `.day` 首记录。若 `first_date < entry_date`，登记 `NEW_CODE_PRE_EFFECTIVE_HISTORY_ANOMALY`。
3. 只从同交易所且退出日期为 entry 日或前一 market session 的 old-key 集合配对；不构造全量 exits × entries 笛卡尔积。对配对文件比较日期交集上的 OHLC、amount、volume：OHLC/amount 严格相等，volume exact ratio 使用冻结的 v1.0 研究阈值 0.95，至少 20 个 shared sessions；`reserved` 与 raw prefix 仅作描述。
4. BaoStock 仅用于上述 TDX-first 缩小后的 pair。能复用 hash-bound 冻结报告时复用；否则必须走现存有界请求合同。查询失败、provider row code 不符或数据重复都保持 unresolved。
5. Source fingerprint 只能产生 candidate。`CONFIRMED_SAME_ENTITY_CODE_CHANGE` 还必须绑定独立正式证据；merger-successor、code-reuse 以独立发行人/正式事件证据分类。没有独立证据时记 `UNRESOLVED_IDENTITY_RELATION`。
6. `unresolved_identity_relations != 0` 或未链接边界异常不为零时，V4-01 仍为 BLOCKED。没有新 same-entity relation 时保留 R7 hash；若出现新的正式确认关系，另建 R9，不覆盖 R7。

## Calibration audit 的阶段归属

`AUDIT-V4-01-SOURCE-FINGERPRINT-CALIBRATION-20260929` 保留为 `DEFERRED_NON_BLOCKING_RESEARCH`：paired TDX、SH/STAR 与 harder negative 的阈值研究继续开放；它不阻断本轮 completeness gate。它不授予 candidate SAME_ENTITY confirmation、canonical identity mutation 或 production authority。

## 当前运行证据与接收状态

扫描脚本、R1 scan、relation resolution、独立 postcheck 与 final-stage candidate 由同一 amendment 版本化绑定；完整 Required Scope 的运行结果及 hash 在对应 JSON receipts 中。外部 acceptance 尚未发生，因此所有相关 stage receipt 只使用 `*_CANDIDATE` / `PENDING_EXTERNAL_ACCEPTANCE`，不写 `EXTERNALLY_ACCEPTED`，也不修改 global `V4_STAGE_ACCEPTED_HEAD`。

## 阶段记录

- 阶段合同：本文件与 `config/v4_01_identity_completeness_gate_v2.json`。
- 证据：R7 identity/universe hashes、R8.3 boundary inventory/postcheck、只读 TDX-first scan、候选对原始 BaoStock 压缩报告、版本化 alias 事实与官方证据 hash、独立 postcheck。
- 验收结果：`FULL_PASS_CANDIDATE` 仅在所有边界完成扫描、候选均经独立证据分类、unresolved=0、unlinked anomaly=0 且 postcheck 通过时成立；否则 `BLOCKED`。
- 下一阶段：取得独立外部验收；其前不得升级 global accepted head、生产身份或 V4-04 入场授权。
