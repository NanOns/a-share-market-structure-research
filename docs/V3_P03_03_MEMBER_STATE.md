# V3 P03-03-member_state 阶段报告

## 结论

`P03-03-member_state`：**PASS**。本阶段只处理 `member_state`，没有开始 `structure` 或 `summary`。

执行依据为工作区当时的最新 V3 主实施文档 `docs/WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md`，SHA-256 为 `912FE6DD25CCAC5BB9CCD4EA6216C7DBB88433CEBC406D33C538A71CD3AA0A24`。依据第 17.6、18.7 节，成员日期/排名动态结果与静态板块属性分开，结果对象通过 slice binding 读取，证据 JSON 不能未经证明地剥离。

## 阶段合同

- 新增 `member_state_result_rows`，物理主键为 `(result_object_id, sector_id, security_id, trade_date)`。
- 结果列沿 `sector_member_state_daily` 保留成员存在、排名、有效分母、分位、三值强状态、结构/新高命中、变更状态、前值/变化、证据 JSON、历史基准和合同字段。
- `strong_predicates`、`queue_refs`、`high_refs` 参与值 hash；静态板块属性仍由 `sector_base_daily` 提供，不复制进成员结果。
- 新增 `member_state_result_daily` 兼容视图：优先读取绑定的 V3 result object；未绑定 slice 才允许回退旧表。
- M8/M9 preview writer、M10 mainline reader、M11 association/attribute/linkage reader 和 API 均切换到 V3 view；旧 `sector_member_state_daily` 保留为不可变兼容/审计来源。
- `sector_membership_changes` 属于独立 domain，本阶段未迁移、未改写。

## 生产证据

- 维护备份：`backup-20260912T020156Z-638bdba5a42e`，状态 `VERIFIED`。
- 备份 SHA-256：`638bdba5a42ed684ecb5c22e2a994cd3851ac1a9f546b5eb5d9da42890b194bf`。
- 迁移：`030_v3_member_state_result_rows`。
- 迁移 SQL SHA-256：`1C4740EBE4AE4E9039973BDF4896731CC742324CEC97D12FA395B7D18930CDD3`。
- 迁移回执：`migration-030_v3_member_state_result_rows-032e933362f745d7ae33ee65ac990c5b`。
- 31/31 member_state slice 完成 binding；16 个 result objects；V3 去重物理行 1,783,166。
- 旧表 3,365,740 行；新兼容视图回读 3,365,740 行；未绑定回退行 0。
- old→new 与 new→old 逐行 `EXCEPT ALL` 差集均为 0；重复结果业务键 0；对象 metadata 行数不匹配 0。
- 旧表存在 DuckDB `NaN` 而非 SQL NULL 的历史表示：`member_rank/member_percentile` 各 60,053 行，`previous_rank` 1,162,420 行，`rank_delta` 1,178,562 行。V3 物理列保留该值；hash 采用 `HASH_AS_NULL_PRESERVE_LEGACY_STORAGE` canonical policy，并已在 result semantics/evidence 中记录，未静默改写为 NULL。
- 静态属性未混入 member_state result；`sector_base_daily` 仍是属性来源。
- API smoke：成员历史、股票成员关系、linkage history 均成功返回同一 publication snapshot；服务恢复 `READY/0`，storage objects 为 46。

## 测试与验收

- member_state V3 定向测试：`2 passed`，覆盖同内容共享、同输入三次重跑、JSON 语义变化不共享和 NaN 可 hash。
- member_state/既有相关回归：`264 passed in 128.23s`，覆盖 V3、M9、M10、M11、M14、M7、M8、M13、M2、M4、M1、M15。
- `py_compile` 与 `git diff --check` 通过。
- TDX 输入目录未访问、未修改；主 V3 实施文档的既有工作区修改未触碰。

## 下一阶段

按 V3 文档下一任务为 `P03-03-structure`；本阶段未执行、未预先实现 `structure` 或 `summary`。
