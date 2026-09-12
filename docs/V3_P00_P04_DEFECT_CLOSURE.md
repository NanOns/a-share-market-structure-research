# V3 P00–P04 已执行阶段缺陷收口

## 结论

依据当前工作区最新 V3 主实施文档（SHA-256：`3395AE2895F749DD5764998451363BF24024BAAA481AC7E644FE1AF941137851`），本轮只修复已执行的 P00–P04 代码、测试和产物缺口，没有启动 P05–P11，也没有修改主实施文档。

代码与临时库范围的验收结果：**FULL_PASS**。

`pytest -q tests/upgrade_v3 tests/upgrade_m5 tests/upgrade_m7`：`170 passed`；`compileall` 与 `git diff --check` 通过。

## 已收口缺陷

| 缺陷 | 修复 | 验收 |
|---|---|---|
| R19-01 / C20-12：NOT_BUILT、纯在线 context 与旧分页别名无法共存 | 增加 `ResearchContextReady`、`ResearchContextNotBuilt`、`OnlineContext`；PageEnvelope 接受 `eligible_total` 或兼容的 `total_eligible`，冲突即拒绝；分页 context 按状态校验 | P00-03 合同反例通过 |
| P02-03 source scope 串缓存 | `HierarchyMembershipResolver` 缓存键加入 `source_scope` | 两个同 revision、不同 namespace 的隔离反例通过 |
| P02-04 多 source namespace 随机取第一条 | publication 未指定 source scope 且存在多个绑定时 fail-closed | 多 namespace 反例通过 |
| R19-05 / C20-16：历史修订只写受影响股票，整日 slice 丢未受影响行 | V3 daily entry 从已绑定技术结果源重组完整交易日 slice；仅计算受影响股票；旧日源不完整时拒绝绑定 | 历史价量修订验证 A 修订后 A/B 整日回读，`reassembled_rows` 有证据 |
| P04-03 后续输入仍不登记 source_files | 新 sealed bundle 的输入验收改为统一登记 package、metadata、source_files、bundle，幂等且不复制源文件 | source catalog 临时库测试通过 |
| P00-02 / P04-03 存储引用和源目录缺口不可定位 | 新增只读 source catalog audit、storage reference audit，原子生成 JSON 产物 | 当前生产库审计产物已生成；无数据库/文件物理变更 |

## 当前只读审计产物

- `reports/upgrade_v3/P00-02_STORAGE_REFERENCE_AUDIT.json`
- `reports/upgrade_v3/P04-03-03_SOURCE_CATALOG_AUDIT.json`
- 原有 P04-03-05～07 备份链审计产物保持不变。

当前数据库读数仍显示：8 份物理 source bundle 回执中 3 份不在 `source_bundles` catalog；`source_files` 仍为 0；多个 `storage_objects.referenced=true` 尚未出现在当前 publication reference graph。这些已被只读审计固化，但没有自动回填、清除标志、删除或移动，因为最新 V3 文档要求先做来源/归属决定，自动修改会破坏历史证据链。

## 放行边界

- 代码、合同、测试和临时库范围：FULL_PASS。
- 生产 daily：入口已接入并有临时库全链测试，但本轮没有执行真实生产 daily job，也没有写生产数据库。
- 历史源包/备份链：保留证据并 fail-closed，仍需 owner 对 3 份未登记回执、31 条缺数据库 body 的 catalog 链和 6 个孤立对象作独立取舍；这不是代码修复权限。
- P05–P11 的 C20-02～C20-15 属于尚未执行模块，不在本轮冒充已修复。
