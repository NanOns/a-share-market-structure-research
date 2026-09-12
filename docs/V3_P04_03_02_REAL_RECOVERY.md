# V3 P04-03-02：真实保留源包恢复复验

## 结论

**PASS（真实输入验证）**。

本任务对当前保留的 2026-09-10 V3 source bundle 执行了一次完整 resolver 恢复。恢复目标是全新项目内临时目录；验证完成后仅删除本轮新建的临时目录。原始 ZIP、既有 extracted、metadata、TDX、数据库和 backup 均未修改。

## 阶段合同

- 合同：`v3-p04-03-resolver-recovery-v1.0`。
- 输入：封存 receipt `fc26948799b1cd581c6b04c78a34ce732e1b69ab3f46cb3c09a2a9bd57bb1120` 及其保留 package。
- 恢复目标必须是项目目录内全新路径，拒绝 TDX、项目外路径、已存在目标和源包篡改。
- 接受条件：package SHA/尺寸通过，安全解包完成，实际文件数和展开字节数与 receipt 一致，指定实际成员存在。
- 本任务不启用缓存回收，不改变生产 resolver 的既有 extracted，不执行备份或恢复演练。

## 实际证据

| 项目 | 结果 |
|---|---|
| bundle | 2026-09-10，`fc26948799b1...bb1120` |
| package | `data/input_staging/packages/20260910/hsjday.zip` |
| package SHA-256 | `ae1e7b6e8339c9b3b29d048d3224bc32b85ba47d8ce14bb2fe32fcd6cc700909` |
| fallback | `false`，显式 staged path 生效 |
| 恢复文件数 | `12,404` |
| 展开字节数 | `949,487,072` |
| `sh/lday/sh600001.day` | 存在，SHA `bf24cb6ea47d6f4897cc712f6ea11825c9058916b08839e49485617ef172dc95` |
| `sz/lday/sz000001.day` | 存在，SHA `06cfde0f135d7688c2f668344e5edcd76c6fd568780db492d9e4f1354d3ff42b` |
| 临时恢复目录 | 验证后已删除；原始目录未触碰 |

首次使用不适用于真实包的合成成员路径时，resolver 在写入前返回 `SOURCE_REQUIRED_MEMBER_MISSING`，未创建目标目录；改用真实 ZIP 中存在的成员后通过。这证明缺失成员会 fail-closed，而不是伪造恢复成功。

## 验收

- receipt 身份和 package SHA/尺寸核验通过。
- 全量解包计数与封存 receipt 完全一致：`12,404 / 949,487,072`。
- 指定真实成员存在且复算 SHA 完成。
- 恢复目标为一次性新目录，完成后已清理；没有删除任何既有 V3 数据。
- 原有 resolver 定向测试仍通过；本轮 V3/M5/M7 完整回归基线为 `175 passed`。

## 下一任务

进入 `P04-03-03`：刷新最近 2 个已使用 bundle 与 `.phase1_cache` 预算预览；只做保护判断和回收预览，不执行解包或缓存删除。
