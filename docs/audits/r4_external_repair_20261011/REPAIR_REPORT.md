# R4 外审 R1 修复首批工程回执

当前状态：PARTIAL_ENGINEERING_REPAIR；EXTERNAL_ACCEPTANCE_BLOCKED / AUDIT_INCOMPLETE。

执行隔离分支 codex/r4-pg-only-20261011，入场 HEAD 5f67ce474d0b1ed474a8b8bb02b8e794df10629e。目标分支未合并，生产 authority、PID、TDX 目录未切换或写入。依据本目录保存的独立外审与总任务卡；原报告、4568 节点原账与失败保留。

## 已执行

- E01：删除未绑定 sqlite3.Error；psycopg.Error 独立映射 SHADOW_PG_UNAVAILABLE，输入异常映射 SHADOW_SOURCE_INVALID，契约异常原样传播。7 个真实错误边界/无授权负例通过。
- 全 src 的数据库异常引用 AST 盘点：没有发现同类未绑定数据库模块引用。仅为静态线索，不是所有 V4 动态路径排除证明。
- E02：正常 config/core_product_read_authority_r1.json 路径在临时根完成 3 个 PG 读回、SQLite 无回退、manifest 篡改验证。没有 constructor history 注入；没有形成正式 accepted PG authority，也没有声称完成默认真实产品 HTTP 全端点。
- E03：旧 accepted research.sqlite 完整 SHA 与大小核验；隔离 PG 逐对象逐字段比较。6337 旧对象中 5591 个相同 ID 有字段变化（5213 stocks/378 sectors）；另 328 个旧 Focus ID 消失、328 个新 ID 增加。6247 是差异记录数，不是 6247 个旧对象。旧源前后 SHA 一致。完整差异压缩归档，不采纳任何字段变化。
- Focus ID 变化独立登记 R4-E03-FOCUS-ID，不能被同源构建器通过冲销；源码 production_v4.build_snapshot 的对象 ID 包含行内容 digest，仅是溯源线索，未宣称已解释全部变化。
- E04：保留首轮 7 PASS/44 ERROR（旧 autouse 夹具）和 native clean-slate 38 PASS/13 FAIL。逐运行逐节点登记112条记录。native 的10个旧SQLite原生夹具需PG迁移，3个共享旧服务/AST兼容测试范围待审，均没有静默排除。
- 最终定向 native PG 验证10/10通过。测试分母仍 null；定向通过不等于合法 V4 全回归通过。
- E05：原基线限定继续有效；没有宣称10171个保护对象在所有时刻原字节未变。

## 验收与下一批

E01 错误边界 SCOPED_PASS；DB12 实际 PG Shadow contract/consumer 仍 OPEN。E02 正常绑定定向探针 SCOPED_PASS，默认真实 handler、广样本五T0、周期Owner、容量、正式接受绑定仍 OPEN。E03 字段/Focus身份溯源、联合CAS与回滚仍 OPEN。E04 合法分母、动态可达性和完整PG夹具/全回归仍 OPEN。DB06/08/09动态探针及第二批任务未在本批关闭。

生产切换、Windows实体安装、正式Grant、时间/成熟门须按原合同另行满足；本批没有申请或获得此类权限。

## 可复现

设置 TMP/TEMP/TMPDIR=G:/codex_tmp，PYTHONDONTWRITEBYTECODE=1，R4_NATIVE_ISOLATION=1，V4_NATIVE_PG_DSN 指向核验 data_directory 的隔离PG；R4_PG_DATA_DIRECTORY=G:/codex_tmp/full_system_r4_fbd23a6b/pg_data。

`python -B -m pytest -q tests/test_v4_shadow_error_r4.py tests/test_v4_default_history_authority_r4.py --basetemp=G:/codex_tmp/test_temp/r4_external_focused -o cache_dir=G:/codex_tmp/pytest_cache_r4`

`python -B scripts/audit_r4_external_snapshot_delta.py --source-root "G:/codex work/大A交易" --output docs/audits/r4_external_repair_20261011/E03_OBJECT_FIELD_DIFF.json.gz`

执行源绑定见 EXECUTION_SOURCE_BINDINGS.json；原始JUnit、连接意图、日志与逐节点账见本目录。所有源码绑定使用实际文件SHA，避免将历史回执追挂最新Git SHA。
