# V3 P02-03 树语义复用与父成员去重阶段报告

## 阶段合同

| 字段 | 值 |
|---|---|
| task_id | P02-03 |
| 输入代码版本 | `9bbdb0c`（P02-02 完成）+ 本阶段工作区变更 |
| 适用主实施文档 | `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` |
| 主实施文档 SHA-256 | `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24` |
| 适用条款 | §17.5、§17.11、§18.5 P02-03、S02 |
| 关系 source_scope | `TDX-MEMBERSHIP:direct-members-v3-v1` |
| 树语义合同 | `TDX_SECTOR_HIERARCHY_V1_1`；`H(contract, sorted node/parent/level/relation_basis)` |
| 父成员缓存合同 | `hierarchy-parent-members-v3-v1`；`(relation_revision,hierarchy_version,semantic_version,display_universe_version)` |

本阶段先完成只读审计和合成验收，再在维护窗口绑定已有固定树版本。未访问、未修改
`D:/new_tdx` 或其他 TDX 输入；没有新建第二套行业树表，没有修改旧
`analysis_snapshot_hierarchy` 绑定，也没有改写旧 `membership_snapshots/entries`。

## 实现

### 树语义与源观测分离

`src/workbench_analysis/hierarchy.py` 现在分别计算：

- `hierarchy_semantic_digest`：只使用合同、节点 ID、父 ID、层级和关系依据；名称、路径、
  source hash、observed_at 不参与树版本内容。
- `source_digest`：保留 source hashes、source path 和观测节点数作为源观测证据。
- `ensure_hierarchy`：当新观测与已有节点语义相同，复用已有固定树版本，不重复写入节点。
  合同变化仍会产生不同语义摘要，不会静默改老树。

生产已有两份 V1.1 树节点内容相同但旧版本号不同。本阶段没有删除旧版本；按创建时间选取
最新固定版本 `tdx-hierarchy-v1.1-dd0b726a256dae0a`，其语义摘要为
`4c72c64d328cae8efe6c093dd4fe111216ec8292a7cbab8bf33d93c930d9ac92`，节点数 554。

### 父成员 resolver

`HierarchyMembershipResolver` 读取固定树的 INDUSTRY 叶节点：

- 对同一父板块下多个叶行业的直接成员做 `UNION DISTINCT`；
- 源直接父成员保留 `DIRECT` 依据；
- 叶成员派生关系记录 `DERIVED`；
- 未知来源在关系边中保留 `LEGACY_EXPLICIT`，不强行改写；
- THEME 等没有可靠父树的节点不参与父成员推导；
- 结果默认只存在内存，缓存键不包含 `trade_date`，并支持
  `display_universe_version` 使当天退市/ST过滤变化显式失效。

## 合成验收证据

新增 `tests/upgrade_v3/test_p02_03_hierarchy.py`，3 项全部通过：

1. 更换源路径、源 hash 和名称时，语义版本不变、源观测摘要改变；更换合同则语义摘要改变。
2. 两个叶行业含同一股票时，父成员只返回一次；同股票同时有直接父边和派生边时同时保留
   `DIRECT`/`DERIVED`；未知来源保留 `LEGACY_EXPLICIT`；概念节点无父成员。
3. `ensure_hierarchy` 对语义相同的新观测不新增版本或节点，节点仍为 4/4；缓存键四元组
   与文档一致。

## 生产只读审计与绑定

维护前服务为 READY、活动任务为 0。生产只读审计结果：

| 项目 | 结果 |
|---|---:|
| 固定树节点 | 554 |
| 父行业数 | 22 |
| 9/10 派生父成员并集 | 2,892 |
| 9/10 legacy `DERIVED_PARENT` 行 | 2,892 |
| 9/10 legacy 总行数 | 75,028 |
| 9/10 直接边 | 72,136 |
| 父成员集合不一致 | 0 |

`scripts/bind_v3_hierarchy.py` 默认只读，`--apply` 才允许写入。脚本在写入前重新执行
固定树、关系 revision 和父成员集合核验；本次维护窗口使用备份
`backup-20260911T233048Z-45d7b3c1bed2`，状态 `VERIFIED`，备份校验中
`membership_entries=435472`、`outcomes=2030`。

实际只更新 2026-09-10 对应的 `relation_snapshot_bindings.hierarchy_version` 和
`relation_observations.hierarchy_version`，绑定到
`tdx-hierarchy-v1.1-dd0b726a256dae0a`。9/4、9/7、9/8、9/9 仍为 NULL，避免用未来树
解释旧日期；`legacy_payload_basis` 保留原始 2,892 行派生证据。

绑定后的生产对照：

- 6/6 个旧快照 `direct_edges_match=true`、`payload_semantics_match=true`、`status=PASS`；
- relation revisions 3、edge intervals 74,086、observations/bindings 6；
- 旧 `membership_entries` 仍为 435,472；树版本仍为 3 份、节点仍为 1,662；
- 服务恢复为 READY，活动任务 0。

## 回归与阶段验收

- `python -m pytest -q tests/upgrade_v3 tests/upgrade_m14 tests/upgrade_m7`：**126 passed**。
- `python -m py_compile src/workbench_analysis/hierarchy.py scripts/bind_v3_hierarchy.py`：通过。
- `git diff --check`：通过。
- 生产只读复核脚本：绑定后 `status=PASS`、`mismatch_count=0`。

## 阶段结论

**PASS。** P02-03 已复用既有行业树语义，未重造树；无关源观测变化不重存 554 节点；父成员
按固定树直接叶成员并集去重；源直接父关系和未知来源保守保留；9/10 的 2,892 条派生父成员
被解释为父成员，而不是把 75,028 条旧行全部伪装成新增关系。旧日期关系和旧树绑定未被未来
观测回填。下一阶段进入 **P02-04：接入旧读路径，再关闭旧全量新写**。

## 独立未决项

- `relation_publication_bindings` 尚未切入；按 P02-04 处理。
- 旧 API/read path 尚未全面切换到 V3 resolver；按 P02-04 逐调用方对照。
- 旧全量 `membership_entries` 新写尚未关闭；按 P02-04 在新旧对照通过后处理。
- 工作区原有的 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md` 未提交修改仍保留，
  本阶段未覆盖、回退或提交该文件。
