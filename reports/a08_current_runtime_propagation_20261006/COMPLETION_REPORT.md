# A08 current runtime 治理传播候选 — 2026-10-06

A08_CURRENT_RUNTIME_PROPAGATION = CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT。
R25_REENTRY = READY_FOR_PACKET_REBUILD_OR_EXTERNAL_ACTIVATION_AUDIT。

依据用户提供的两份独立外审，归档 exact 原始字节。Current Audit V4 的 canonical issue 仅 A08 从 OPEN_EXTERNAL_REAUDIT 变为 ACCEPTED_SCOPED，两个 Shadow blocker 变 false；生产 blocker 保持 true，audit authority 不授予业务运行或自动阶段权限。其他 issue 保持不变。编号按已有 V3 → V4 / V5 → V6 增量命名，不分配或新增数据库 migration。

capability v2 保留 PURE_CORE_STOCK → PREWATCH 的原依赖图，同时 exact 校验当前 producer 和 supporting contracts。PURE_CORE_STOCK 无 A08 blocker，两个 Amount-A capability 继续分别被 A04 阻断，permission_granted 始终 false。

V6 / R4R4、disabled activation v5、settlement contract v3、R25 preflight v4 和 builder/validator successor 均为新增版本。明确的 active selector 是 config/v4_16_current_runtime_entrypoints_v1.json；新使用者须选 V6 facade / CLI。旧 dispatcher、V5/R4R3 和 settlement v2 保留原字节，用于历史绑定及既有 obligation。新 settlement CLI 用 --dependency-generation V5 显式选择旧路径；不通过猜测、最新文件或重绑迁移历史 obligation。新旧 publication、DB、future-authority、settlement-cycle AST 完全相同，constructor 只增加治理版本门。

新增定向 15 项通过；PASS_KEEP 回归 314 项通过，2 项既有 historical-stage-reader 治理债务与基线节点及 CURRENT_STAGE_NOT_ACCEPTED 原因一致，已独立跟踪。新增失败为 0。所有 V4-09 业务向量、P0-02 A01/A02/Q01/Q05 及队列、DB integrity 回归通过。工程 R25 包构建/校验往返已测试；未创建或选择真实目标日包。

不可变 V3/v1/V5/v4、P0-02 final evidence、V4-09 producer/artifact、全部旧 migration 和受保护 Head 均保持入口字节。真实计数为 0，V4-16–22 formal Accepted Head 缺失。生产、Focus、默认 UI、FEP、display、Priority、Champion、REAL_OOS 均未授权。TDX 没有写操作，未运行 scanner。

当前 R25 selection 仍为 WAIT_ACCEPTED_DAILY_INPUT，原因是缺少 exact real target-session 输入，而非 A08 blocker。下一步是独立验收此次传播，再按明确输入重建 R25 packet 或进行外部激活审计。Git push 不授予 First Real Shadow。
