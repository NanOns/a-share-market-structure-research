# V4 Forward R2 Final Blocker Repair R3 — V4 限定范围

执行基线：a775383eabb94e97a6022f34a30de7aa55e3a39c。用户后续明确：全量执行和历史测试仅包括 V4，不包括 V4 之前的版本。该指令覆盖任务卡中旧版本全量、60 个旧产物节点及 V3 UI 的执行要求。

## 本次验收结果

V4 专用回归归并验收：4759 个节点，4757 通过，0 失败，0 错误，2 跳过。范围清单列出全部 212 个测试文件及绑定，包含 V4 各阶段、Forward/Settlement、治理、DM01、隔离与接入 V4 的 FEP。没有收集后的 ignore、deselect 或新增 xfail。

这不是单次全量零错误的声明：首跑 PG fixture 尝试随机端口，被隔离保护拒绝，出现环境 setup errors；在已有私有集群校验全套 33 个 migration 校验和后，从空 V4 模板克隆专用数据库，并重跑受影响 V4_10/V4_11 的全部测试。首跑和重跑原始 XML/log 均保留，逐节点归并必须保持完整首跑节点集合，且每个原失败/错误都对应真实重跑 PASS。详见 `V4_PG_ENVIRONMENT_REPLAY_RECEIPT.json`。迁移、隔离保护与原测试断言均未改变。

首跑另外两个 PG capability 跳过已在正确 upgrade 实例和显式私有 DSN 上实际补跑通过。最终仅保留两个 Windows symlink 权限限制跳过，原测试不删除、不改断言；另有两项 V4 原 snapshot owner 的 link/reparse 判定等价负向验证通过，以及真实 junction/子进程路径边界验证通过。

阶段结论：CANDIDATE_READY_FOR_INDEPENDENT_EXTERNAL_AUDIT。测试通过不构成外部验收，也不授权 production/shadow/focus/default UI 或进入后续门禁阶段。

## 代码与输入保护

统一输出路径解析在任何写入前拒绝绝对路径、盘符、UNC、穿越、ADS、配置源目录与重解析逃逸。私有冻结代码的 helper 通过独立模块加载，避免历史 common 命名空间覆盖当前保护。子 Python 进程安装源目录写入审计，临时输出使用 G 盘。

TDX 本次全量前后逐文件内容、字节数和 mtime 比较见 `TDX_FRESH_ZERO_WRITE_RECEIPT.json`。原事故仍永久保留 5 次写调用、4 个文件、原运行 zero-write=false。事故前独立内容完整性没有恢复为可验证，不改写时间戳或旧记录。

保护的运行目录完整指纹相等：True；已接受头与 SQL migration 绑定相等：True。没有迁移、发布或增加真实样本。

研究 HTTP 读取修复缺失 json 导入与并发 DuckDB 读写连接冲突，采用已有数据库锁。网络 hot-rank 与主流隔离约束保持。独立审计见 `CROSS_AUDIT_RESEARCH_HTTP_READ_BOUNDARY.json`。

## 范围更正与历史事实

混合版本全量 D 已中止，其失败流仅保留为此前调查，不能作为 V4 验收。旧版本 60 个历史节点不再阻断 V4 回归；没有伪造缺失产物，没有把它们计为通过。此前对 22 个旧历史测试的退役处理已撤回，恢复原始文件，新建历史退役配置移入撤回证据。相应旧版本重放脚本明确拒绝继续执行。

GOV-1 将旧 CURRENT_RELEASE 明确为历史诊断绑定，当前授权由 V4 CurrentStageAuthority 校验；原指针及旧 identity 保持。V4 的历史兼容性 reader 测试只验证 V4 版本合同的精确读取边界，不执行旧版本算法验收。

M7 历史任务并发 sequence 冲突属于 V4 前版本，记录为独立范围外审计项，本次未修复或宣称通过。

## 保留能力债务

IA-07：NOT_VERIFIABLE_BY_CURRENT_ACCEPTED_CAPABILITY。真实 accepted universe 为 5037，完整控制特征池为 0，100/1000/5037 实际人口检查不能建立控制匹配性能结论。没有复制或合成控制池、没有将零 eligible rows 判为 FULL_PASS。该债务仅阻断控制匹配接受，不阻断合同允许的独立股票绝对结算。

E3/E4 8 个实际模型重训与原 frozen population 的 parity 证据保留，不构成 champion、REAL_OOS 或运行授权。Git 提交和 push 仅交付本次代码及证据；后续仍须独立 V4 外审及 IA-07 独立能力接受。
