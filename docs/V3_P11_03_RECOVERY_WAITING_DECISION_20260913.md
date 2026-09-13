# V3 P11-03 回收范围决策登记（2026-09-13）

## 1. 阶段结论

本阶段按 V3 最新规范 §18.14 P11-03 执行“未取得明确回收授权”的分支：

- 阶段状态：`DEGRADED_PASS`
- 决策状态：`WAITING_DECISION`
- 物理回收：未执行
- 实际回收空间：`0 B`
- 生产 DuckDB：只读打开，size/mtime 前后一致
- TDX：未访问
- 未执行：`DELETE`、`MOVE`、`VACUUM`、新备份、恢复、TDX 写入

当前请求只允许登记精确对象，未授权删除、移动或压缩。机器回执把每一个表、目录、文件都登记为独立目标，不使用 `data`、`runtime` 或 `data/input_staging/extracted` 等宽泛根目录作为目标。

机器回执：[P11-03-RECOVERY-WAITING-DECISION.json](../reports/upgrade_v3/P11-03-RECOVERY-WAITING-DECISION.json)

## 2. 阶段合同与前置证据

合同：`V3_P11_RECOVERY_WAITING_DECISION_V1_0`。

最新主规范：`docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，运行时 SHA-256 为 `52536035F82D4754EDA13241181F2AA8563B9D37E280E2AE39BFBD3A5A6C9D5B`。

前置 P11-02 回执：`reports/upgrade_v3/P11-02-OLD-WRITE-RECOVERY-PREVIEW.json`。P11-02 已证明六个首轮迁移域的旧 writer 非定义调用点为 0、逐 slice 等价通过、旧读兼容可读；同时保留两个独立开放审计：

1. `P11-02-AUD-STORAGE-01`：`storage_objects` stale `referenced` 标志及 tombstone 物理路径需逐对象对账。
2. `P11-02-AUD-AUXILIARY-WRITES-01`：`sector_membership_changes`、`stock_sector_associations_daily` 的辅助旧写入点需迁移或登记有界保留边界。

两项审计均原样带入本阶段，未因“等待选择”而关闭。

## 3. 精确对象登记

| 对象类别 | 精确数量 | 预览估算/规模 | 本阶段决定 | 实际动作 |
|---|---:|---:|---|---|
| 关系旧副本表 | 4 表 | `80,478,208 B` | `WAITING_DECISION` | `NONE` |
| 首轮迁移域旧结果表 | 6 表 | `188,219,392 B` | `WAITING_DECISION` | `NONE` |
| 首轮迁移之外的辅助结果表 | 7 表 | 由 P11-02 逐表登记 | `WAITING_DECISION` | `NONE` |
| 解包目录 | 4 目录；其中 20260907/08 合计 `1,897,433,472 B` 为预览候选 | `WAITING_DECISION` | `NONE` |
| metadata snapshot | 4 目录 | 受保护 | `WAITING_DECISION` | `NONE` |
| 唯一 source package | 4 文件 | 受保护 | `WAITING_DECISION` | `NONE` |
| phase-1 cache | 1 个精确目录，`954,775,668 B`，预算利用率 `44.46%` | 预算内保护 | `WAITING_DECISION` | `NONE` |
| backup 链对象 | 16 个精确文件/目录，`22,737,490,910 B` | 12/12 链完整；受保护 | `WAITING_DECISION` | `NONE` |
| runtime 文件 | 77 个精确文件，`5,531,414,409 B` | owner/reference 范围未确认 | `WAITING_DECISION` | `NONE` |

P11-02 的表级估算仅表示持久 block 估算，不等于可以立即回收的空间；本阶段不把这些估算累计为实际释放量。所有登记条目的必备字段是：精确目标、对象类型、原预览对象、建议动作、所需授权、实际动作和实际回收字节。

## 4. 验收结果

| 验收项 | 结果 | 证据 |
|---|---|---|
| P11-02 前置回执有效 | `FULL_PASS` | 合同及阶段状态核对 |
| 每个对象精确登记且无宽泛目标 | `FULL_PASS` | `register_validation.exact_targets`、`unique_targets` |
| 所有动作均为等待用户选择 | `FULL_PASS` | `proposed_action=WAITING_DECISION`、`actual_action=NONE` |
| 生产库不变 | `FULL_PASS` | read-only；size/mtime 前后一致 |
| 物理回收 | `NOT_AUTHORIZED` | `reclaimed_bytes=0` |
| 存储审计 | `DEGRADED_PASS` | 两个独立审计项保持 `OPEN` |

## 下一阶段

登记完成后进入 **P11-04** 的前置等待状态。P11-04 的新主入口切换仍不得执行，直到 P11-01 的停增长/存储门、上述两个独立审计和明确回收范围决策均有独立证据。若后续授权只覆盖部分对象，必须按本回执中的精确 target 逐项执行，不得扩展为根目录删除或全库 `VACUUM`。
