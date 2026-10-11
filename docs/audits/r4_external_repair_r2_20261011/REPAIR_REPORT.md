# R4 独立复审 R2：本轮隔离工程整改回执

总状态：**EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE**。本轮不是 R4 完成或生产切换许可。

输入是用户指定的 `V4_R4_BATCH2_INDEPENDENT_REAUDIT_R2_20261011.md` 与其上位 PG-only 总卡；入场隔离 HEAD `14a4b61876ce64f77f001623d0b13554da2744a2`。代码实现提交 `4f7e49d22a3f703813c62db0d8132d04eb6f2ae6`；执行时的全部 2839 个 Python 文件字节另见 `EXECUTION_SOURCE_BINDINGS.json`，包括当时尚未提交的能力运行器。后续证据提交不冒充更早的执行版本。

## 已实施和实测

1. **独立问题 R4-EXT-R2-01**：新建 `V4_PG_RESEARCH_SNAPSHOT_R2`，四表逐行摘要、表分母/列序/类型、完整 metadata/source/manifest、schema、PG system_identifier/database name/OID 均进入 root digest。对象 JSON 用类型树与精确有理数表示，拒绝重复 key/非有限数字；NULL、空文本、质量和单位均有身份。seal 前后重算，reader 使用 REPEATABLE READ + READ ONLY 全内容验证。旧 R1 和正式 Head 不改写，不能反向升级其接受等级。
2. **Series / Journal / Shadow 同类硬化**：新 Series 把 bars、新 Journal 把 days/day_inputs 纳入摘要，consumer 字段在封存前绑定；Shadow R2 增加实例身份、完整 facts/storage origin 校验，幂等重用也复验。历史 R1 描述符按原语义保留。最小 verifier 在隔离 PG 实测 SELECT 成功、DML 拒绝、拒绝高权限角色；没有安装生产角色或给正式 Grant。
3. **联合 Head**：新 `V4_JOINT_RELEASE_V2_PG_CONTENT` 在 CAS 前和 health 后重验 Snapshot/Series/Journal；持续发布新候选选择 V2。实际隔离 PG 用例覆盖两个 writer 竞争、stale CAS、health 失败、health 过程中内容篡改、旧版本完整性和 PREPARED 中断恢复。现行 Joint V1 保留原合同，未被声称已获得 V2 身份证明。
4. **旧出版物 R2 无损迁移**：独立只读 SQLite 子进程导出、隔离 PG 新 schema 导入；**6337 objects / 12106 aliases / 50162 members / 1 metadata** 与旧 oracle 的四表分母和规范摘要全部一致，差异 0，源前后 SHA 一致。R2 自身 seal/read 校验同时执行。只证明存储等价，旧字段质量、正式消费者和身份迁移许可仍各自开放。
5. **默认产品五日期目录**：新增 `CORE_PRODUCT_READ_AUTHORITY_R2` 精确选择日期 manifest；未知/串错日期不套用其它 T0。HTTP 使用隔离根正常配置与 `make_product_handler`，没有 constructor history 注入。5 个真实冻结 T0 × 5 只跨行业证券 × D/W/M × RAW/QFQ × 3 组分页，共 **450 图表请求**，另有 **30 产品路由请求**。独立纯逐日源 oracle 对 450 组核对，差异 0。**210 READY、240 SOURCE_INCOMPLETE**；缺失周期 Owner 的缺口保留。较早日期只赋予 CHART_HISTORY，未伪造 market facts；Forward 路由的来源不足不计为功能完成。
6. **反例与容量观测**：错误 token、非法周期、limit/offset、未来日期均拒绝；并发 1/4/8 保持 context。原始 P95/字节记录在结果文件；无已批准容量门，不标性能 PASS。浏览器证据、首遇缺少冻结 UI 依赖的错误及补齐路径另行留证，不隐瞒初次失败。
7. **能力重跑**：显式本轮能力套 **206 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，3 个上轮已有 V4 路径证据的具体旧 V3 节点 deselect，其原件保留。使用不能被业务 ValueError 吸收的 BaseException 数据库护栏。不是裸 pytest，不执行独立 V3/更早历史全套测试。
8. **浏览器**：六入口可见状态、同一只真实证券的五 T0 日线（416/417/418/419/420 根）、RAW、周/月线切换均已记录。首次缺失冻结 UI 发行文件造成空响应，之后按原 source SHA 补齐 8 个 UI 文件；早期日期冷读超出短 locator deadline，保留错误边界，并在页面真正呈现后逐日取证。390×844 下 document_width=487，新增 **R4-R2-UI-MOBILE-OVERFLOW / P2** 独立 OPEN；不宣称小屏幕验收通过。浏览器进程启动于补齐步骤前，初始化后的修复通过独立复制完成，最终源码快照不能冒充初次浏览器进程完整启动字节证明。

## 分母、保护和失败时间链

原 4568 节点及原 3810/237/209/312 原状态完整保留在追加列台账；本能力套只与其中 **119** 个稳定节点相交，另外 87 个属于新增/独立能力节点。不得与此前 60/103 的不同套相加、相减或替换总体结论。全 V4 合法分母仍 NULL，real reachability × normative capability × exact IDs 尚未关闭。

首次身份测试 16 PASS/1 FAIL：测试把按新 schema 重新合法签出的 descriptor 当成串错，纠正断言后通过，原 JUnit 保留。目录硬化首次组合重跑 92 PASS/3 FAIL：旧测试夹具缺正式 authority contract 和真实 head-token；补为正确 R1 合同和 head SHA，未降低 reader 验证。最终 206 项 clean run 原 JUnit/日志保存。源绑定读回 2839/2839 字节一致。

仅对两个原生产 Head 和旧研究 snapshot 进行本轮有界 SHA 前后对照，3/3 未变。TDX 没有写入、在役 PID/端口/正式数据库及 authority 未切换，主工作区未提交内容保留。本轮不声称重证所有 10171 保护对象或所有硬链接的 OS/子进程只读；继承晚采集和深层未消费限制。Stage entry 文件在初稿代码后写入，此时间边界明确保留。

## 独立仍开放的问题

- DB01 真实 executor/Windows 恢复、Snapshot/Series/Journal 全部真实消费者与长期恢复、DB06/08/09 所有受支持动态入口、唯一全 V4 分母和原残留失败继续 OPEN。
- 精确复权 56 类真实消费、FA-009 全规范语义分母、FA-012 原生有效 PIT/Amount A 独立审计未关闭。本轮未伪造历史 PIT、成熟样本或新交易日。
- 新增 **R4-R2-CONTENT-VERIFY-PERFORMANCE / P2** 独立跟踪：全内容复验的成本需在完整消费者、缓存/版本签名方案与授权阈值下另验，不能用局部回归代替吞吐准入。
- 生产角色/authority、跨实例恢复、Windows 实体安装和在役切换均需要独立正式接受和另行授权。2026-10-12 后首获及 Forward/FEP 成熟按事实时间门验证。
- 正式 Drive 归档收据独立追加；commit/push/upload 都不签外部验收。

## 复现

所有 TMP/TEMP/TMPDIR 指向 `G:/codex_tmp`、测试目录指向 `G:/codex_tmp/test_temp`，设置 `PYTHONDONTWRITEBYTECODE=1`。`V4_NATIVE_PG_DSN` 只指向经 data_directory 核验的 G 盘隔离 PG，禁止生产 DSN。

- `python -B scripts/run_r4_reaudit_r2.py`
- `python -B scripts/migrate_r4_old_snapshot_exact_r2.py`
- `python -B scripts/audit_r4_default_five_dates_r2.py`
- `python -B scripts/r4_dated_chart_source_oracle_r2.py`
- `python -B scripts/preview_r4_default_catalog_r2.py`（只读隔离浏览器服务）

下一批从 `R2_DISPOSITION.json` 和上述 OPEN 项恢复，按上位总卡继续推进；不合并正式目标分支、不解锁外部总门。
