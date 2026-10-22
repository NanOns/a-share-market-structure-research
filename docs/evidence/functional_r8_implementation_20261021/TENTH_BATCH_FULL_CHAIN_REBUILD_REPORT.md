# 第十批：10/21 全模块整链重建执行报告

- **状态：** `BATCH10_FULL_CHAIN_PARTIAL_OR_FAIL`
- **记录时间：** 2026-10-22T12:28:38.769076+08:00（Asia/Shanghai）
- **分支 / 基线：** `codex/v4-unified-development` / `23b77e39abce5b78c321122ee418da94cc2ad320`（与用户指定审计基线一致）
- **阶段 0：** `DEGRADED_PASS`；通用 Scanner 状态为 `NOT_APPLICABLE_UNTIL_V4_05`，本轮未启动通用扫描器。
- **证据：** [TENTH_BATCH_FULL_CHAIN_REBUILD_EVIDENCE.json](TENTH_BATCH_FULL_CHAIN_REBUILD_EVIDENCE.json)

## 结论

本轮没有达到第十批的 A–E 硬门，不能宣称全模块整链通过。开发 PG 中仍是上一版四日 R8 token；已修正的成员、RPS/Core、D0 结果没有形成新的四日顺序发布链。28766 六入口 API 均返回 HTTP 200，但回读的仍是旧 10/21 token `c8b6b32f…49d3c528`，首页仍报 Forward `DATA_MISSING`、Radar `PARTIAL`。没有进行浏览器 DOM/关键字段验收。

28765 未监听且未触碰。PG 核查均在 `market_research`（OID `646711`，`127.0.0.1:5432`）只读事务中完成。

## 阶段结果

| 门 | 状态 | 证据与断点 |
|---|---|---|
| P0-A 来源与日期成员 | `PARTIAL` | 10/16 现存 R8 Owner token 为 `33cf6cdb…b5fc440`，其候选成员引用仍有日期范围问题。ReadIndex 配置记录过 superseding token `ab13eb13…694ea6`，但 PG 无对应 R8 发布；后续日期仍以旧 10/16 token 为 predecessor。|
| P0-B Core/因子/周期/Profile | `PARTIAL` | 10/20 的完整 5,226 行 corrected Core 对照有 5,202 个 RPS5-delta 精确匹配、24 个端点 UNKNOWN、0 个数值差异；仍是候选文件。缺少四日全因子族质量分母表及 10/21 同版 PG/页面读回。|
| P0-C D0/D2/Focus/Forward/Priority | `PARTIAL` | 正式两场景重算候选计数：10/16 `90/5084/52`、10/19 `152/5018/54`、10/20 `141/5033/52`、10/21 `99/5076/49`（TRUE/FALSE/UNKNOWN）。开发 PG 当前发布仍绑旧 token；最新独立 D0 PG 读回为 `PG_BINDING_INVALID`：10/16 的旧 Owner Publisher 源码和四日 `SCENARIO_DETECTOR` 都与当前源码字节不一致。其余事实摘要、来源入口、时间链、闭包、权限及行数检查通过；校验器按源码绑定 fail-closed，须由新候选以当前源码生成并重发，不能改写旧绑定。D2 失效价位依合同要求继续 `CONTRACT_BLOCKED`；Forward 统计 Owner 缺失。|
| P0-D Market/Sector/Rotation/RS | `PARTIAL` | 页面 Market 为 `SOURCE_INCOMPLETE`；首页当前板块总数 400、Priority 可排名 8。任务要求的指数历史参考、宽度/趋势及板块来源同版验证没有完成；缺失来源不能用 CSRC 替代 TDX 行业/概念成员。|
| P0-E PG 发布 / 28766 六入口 | `FAIL` | PG R8 发布仍为 10/16 `33cf…`、10/19 `f9c4…`、10/20 `dba3…`、10/21 `c8b6…`。六入口 API 的网络层都 200，但全部返回旧 token；纠正结果未在页面消费。|
| P1 故障注入 / 性能 | `NOT_RUN` | 正确性候选尚未在统一新 token 页面链生效，本轮未启动压测或故障注入。|

## PG 与时间身份

R8 PG 读取确认上述四个旧 token 均有既有发布记录，10/20 还保留失败的 `38507…` 交易记录及最终 `dba313…` 版本。D0 PG 保留既有修订，均仍绑定相同旧候选 token；10/19、10/20、10/21 有 `DEV_ASOF_SOURCE_VERIFIED` 修订，但 `as_recorded=false`、`pit_eligible=false`、`production_admission=false`。这些状态不把晚采输入转成原交易日 PIT。

本轮未改写历史 Owner、旧 R8/D0 发布、原始来源或 NON_PIT 标记；未切正式 Head；没有数据库写入或服务重启。

## 下一断链节点

1. 以新 10/16 日期成员权限生成 superseding Owner，并让 R8/D0 受限读回对精确 Owner/来源闭包返回 PASS。
2. 按 predecessor 顺序重新生成并发布 10/19、10/20、10/21；把 10/20 corrected RPS/Core/D0 和 10/21 两场景正式 D0 纳入新 Owner，而不是只留修订文件。
3. 逐日重建 ReadIndex/Priority 并执行开发 Head/CAS、D0 PG、读回。
4. 仅在同 token PG 读回成功后切换 28766，再验六入口业务字段、分页、搜索、日期、日周月与三类证券路径。
5. 保留真实缺源 UNKNOWN，补足指数/TDX 板块/Forward Owner 可用来源；D2 价位仅在 S05-D 合同明确后解锁。
6. 完成 P0 后再按任务卡执行 P1 故障注入和性能记录。

本报告是当前开发方执行记录，不构成独立外审、生产准入或正式发布。
