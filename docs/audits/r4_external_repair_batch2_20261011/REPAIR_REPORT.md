# R4 外审 R1 修复第二批工程回执

状态：SCOPED_ENGINEERING_PROGRESS；EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE。
隔离分支 codex/r4-pg-only-20261011，入场 HEAD 1521f9cca72c3a5a4ff127105be56cc90ec0d2b3。未合并目标分支，未切生产 authority/PID，未写 TDX 或修改旧接受产物。

## 本批结果

1. **DB12 / Shadow**：发现并修复候选代码误用研究快照 PG reader 的契约错误。新增 V4_PG_SHADOW_READBACK_R1 原生不可变导出，独立 storage_identity/facts/shadow_readback_identity；读事务 REPEATABLE READ + READ ONLY，manifest 精确绑定 descriptor 字节。保留既有 publication/slot/state/daily_input/fact digest/quality/context 校验，无 SQLite 回退。
2. **测试范围补证**：迁移10个原生 SQLite Shadow 用例到PG。实际 V4 Shadow HTTP 覆盖六组件、重复参数、四种写法拒绝、无授权/坏合同阻断。最终显式能力套60 PASS/0 FAIL/0 ERROR/0 SKIP；3个 app.py/V3 AST及旧服务兼容节点有逐节点调用证据不纳入本批，原件与原失败保留，V4子义务已迁入新HTTP测试。这60不是全系统合法分母；原4568账继续保留。
3. **E02 默认产品 handler**：G盘复制/冻结依赖；正常 config/core_product_read_authority_r1.json 绑定本隔离根命名空间的PG索引，无 isolated_history_authority constructor 注入。实际 make_product_handler 的 context及 home/stocks/sectors/focus/events/forward 返回200；一股×最新冻结T0×RAW/QFQ×D/W/M六图表均READY；六结果与独立只读SQLite原产品 oracle 无差异。错误token409，默认非PG authority400且无回退。输出明确 production_accepted=false。
4. **E03 字段差异溯源**：对740703条股票/板块字段差异，精确绑定原源和registry后，未解释项0：板块分母5670，股票分母26065，原始amount/volume新投影10426，单位/坐标投影688116，字面UNKNOWN质量修正10426。只说明候选投影变更，不能宣布原接受出版物与新生产者相同，也不替代 Amount A 独立审计。
5. **独立 Focus ID 审计**：469实体逐一对应，无实体增删；328个ID变更完全由字面UNKNOWN质量修正解释，两边生产者内容哈希重建无差异。episode_id/T0/end_date/parent_episode_id 全部无差异。身份正式准入仍独立OPEN，不改写旧记录。
6. **旧出版物直接无损迁移**：另以独立只读SQLite oracle进程导出旧接受快照，再在护栏下原生PG导入，不经过新生产者投影。四表6337 objects、12106 aliases、50162 members、1 metadata，全量摘要与计数零差异；PG修改拒绝负例通过，旧源前后SHA一致。只证明存储等价，未绑定默认Snapshot消费者、Series、联合Head或正式接受指针。

## 失败时间链与证据边界

默认HTTP准备的首次外部路径、两次8GB预算拒绝、缺日历及命名空间不匹配日志均保留；随后收敛/补依赖、为隔离根迁建PG命名空间后通过。没有放松reader的根/身份检查。

冻结图中未消费的大文件hash没有全部重新证明；部分大文件以G盘源的硬链接只读输入共享，进程内写拒绝不能代替OS/子进程保护。未消费深层provenance没有递归完毕。这些限定写入原始冻结清单；不是完整动态范围或全量保护证明。原E05保护清单晚冻结限定继续有效。

PIT-shaped Shadow测试向量位于隔离根且真实样本数0；测试receipt不是正式Grant/外部签收。旧接受快照直接迁移保留原值/质量，不能倒推其所有字段质量正确。

## 验收与下一步

- DB12 原生consumer工程 SCOPED_PASS，真实Shadow来源/Grant仍OPEN。
- E02 最新单T0正常产品HTTP/原图表oracle SCOPED_PASS；正式PG authority、五T0广样本、浏览器和容量仍OPEN。
- E03 全字段/Focus差异规则已解释、旧出版物四表无损迁移已补证；采纳投影变化、完整consumer/Series、joint CAS/rollback仍OPEN。
- E04 只有本能力分母60明确；全V4动态图谱、全回归合法分母和DB06/08/09仍OPEN。
- 调度真实执行器恢复、Journal/Series真实日更消费、56类复权消费者、性能阈值和全字段/Forward/FEP工程仍须继续；时间/实体/生产权限门不由本批解除。

## 重现入口

TMP/TEMP/TMPDIR=G:/codex_tmp，PYTHONDONTWRITEBYTECODE=1；V4_NATIVE_PG_DSN仅指向经data_directory核验的G盘隔离PG。测试需R4_NATIVE_ISOLATION=1、R4_PG_DATA_DIRECTORY=G:/codex_tmp/full_system_r4_fbd23a6b/pg_data。显式文件和三个逐节点排除见 SHADOW_CAPABILITY_SCOPE.json。

- scripts/audit_r4_default_product_http.py（首次冻结；已有冻结根可 --reuse-frozen）
- scripts/audit_r4_focus_identity_delta.py
- scripts/audit_r4_snapshot_delta_provenance.py
- scripts/migrate_r4_old_snapshot_exact.py（oracle独立进程；新G命名空间）

实际执行文件字节保存在 executed_source/；源码绑定、原始JUnit、逐节点账、原始日志及压缩连接意图见本目录。原始连接账解压SHA见 COMPRESSED_LEDGER_BINDINGS.json。commit/push不构成外部验收。
