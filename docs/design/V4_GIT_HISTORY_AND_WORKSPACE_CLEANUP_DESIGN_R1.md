# V4 Git 历史与工作区清理设计 R1

- 合同：`V4-REPOSITORY-GOVERNANCE-RESET-20261015/R3`（2026-10-16 范围更新）
- 设计状态：`PARTIAL / NOT_EXECUTABLE`
- 盘点日期：2026-10-16（Asia/Shanghai）
- 仓库：当前唯一授权的 G: 主仓库
- 治理分支：`codex/v4-workspace-cleanup`，从 `main` 的 `7ae514d5ab8adc0fe2da0e957799dfd2ac4b8136` 创建
- 本文撰写基线 HEAD：`af7360f796512ca0a5d169ca8276c9a63a1d6376`，治理分支已推送至同名远端分支

本文记录当前 Git 历史与忽略工作区的边界、恢复证据和后续执行条件。它不授权历史重写、远端 ref 变更、ignored 文件删除、PG 写入或生产切换。

## 当前事实

| 范围 | 只读结果 | 处理决定 |
|---|---|---|
| 远端分支 | 仅 `main`、`codex/v4-unified-development`、`codex/v4-workspace-cleanup` 三个 heads；本地与远端值相同 | 保护原 refs；未 force push 或删除 |
| Tag | 本地 40 个、远端 35 个；同名对象无差异；5 个仅本地 Tag | 全部保留，尚无处置依据 |
| Codex 与 stash refs | 本地包含 snapshots、turn-diffs、stash 等 refs | 纳入恢复 bundle；不将其自动视为垃圾 |
| dangling 对象 | `git fsck --full --no-reflogs` 返回 497 个 dangling 对象（49 个 commit），没有缺失或损坏对象 | 全部 ID 被独立 recovery pack 覆盖并通过 `git verify-pack`；未运行 GC/prune |
| 可达 Git blob | 69,132 个唯一对象、55,571 个 blob；按 `git rev-list --objects --all` 首次展示路径归类，blob 原始总字节 5,868,585,114。`reports/` 约 3.21 GB、`data/` 约 1.30 GB、`docs/` 约 1.28 GB | 需要先把活跃生产依赖与纯历史证据分开，不能按目录整批移除 |
| Git LFS | 396 个路径、396 个唯一 OID；已有盘点为 0 个缺失本地对象；缓存约 15.67 GB | 保留现有缓存；不重复下载或复制 |
| ignored 工作区 | 280,353 个路径，按文件长度合计 85,479,482,618 字节（约 85.5 GB）；最大类别为 `data/v4` 约 42.96 GB、`data/input_staging` 约 21.42 GB、`runtime/v4_phase0` 约 4.76 GB | 这是本地 Head、来源输入、运行数据库、计算与历史验收材料混合物；没有目录级删除许可或可证明的全目录重建方式 |
| Phase 1 缓存 | `data/.phase1_cache` 约 0.96 GB | 现有 storage 代码声明 `ACCESS_METADATA_ONLY; NEVER_MTIME_DELETE` 且 `deletion_executed=false`；不得用 mtime 或批量缓存清理替代其合同 |
| normalized/输入/计算数据 | `data/normalized` 有多处当前 reader/settlement 消费者；`data/input_staging` 由输入管线和研究构建器引用；`runtime/compute/daily_pipeline.duckdb` 仍存在 | 在替代链、身份、保留要求未闭合前保留 |
| 旧 worktree | C: 有一个 detached 且被 Git 标为 prunable 的 worktree，位于授权的 G: 唯一开发目录之外 | 未读取其业务载荷、未归档或删除 |

blob 分类是唯一 blob 的代表路径统计，不等于各目录当前物理文件字节数，也不证明每个报告仍有业务用途。可达对象总字节数不包含 LFS 实体字节。

## 已完成的恢复冻结

- 所有 refs 已打包并经 `git bundle verify` 验证为完整历史；bundle 为 2,152,353,627 字节，SHA-256 `A3783DF7BCFE2D172EA1C871C9C24D4571CAD0A425E9A28FB7D4CF78CA38B644`。
- 另行打包 fsck 返回的 497 个 dangling 对象，pack 共 69,504 个对象，大小 2,515,182,695 字节，SHA-256 `0714988144E9C8A081E5E3D16E990DE71E8FB8B9DD629540C93E89F937EC23AA`；497 个原始 ID 全部出现在通过校验的 pack 中。
- 初始 bundle 之后，当前治理分支增量 bundle 覆盖到本文 HEAD，并以初始 bundle HEAD 为 prerequisite；增量 bundle 已验证。上述 bundle、pack、ref/fsck/LFS 清单和机器可读统计均保存在 G: 临时治理证据目录，目录索引见进度记录。
- Owner 源恢复补查在 49 个 dangling commits 中发现 4 个精确历史 sector-lifecycle 路径；Git LFS 指针对应本地缓存实体与 PG Owner 元数据 SHA/字节数一致。4 个 gzip JSONL 各 400 行。18 个唯一源路径/摘要绑定中，另 14 个尚无精确缓存匹配；未还原项目文件或写 PG。

## WP-4 历史重写门禁

当前没有可执行的历史过滤清单。原因是 42 个 `src/` 文件被策略扫描标为潜在历史报告/证据读取；已映射的 producer、Owner 与 BFF 路径仍依赖部分旧输入。剩余静态命中尚未完成调用图和 `ACTIVE_REACHABLE / HISTORICAL_ONLY / RETIRED / NOT_REACHABLE_WITH_PROOF` 分类。Owner 源、研究快照与 canonical publication Head 仍有身份缺口。若此时从历史中删除 `reports/`、`docs/evidence/`、`data/` 或相关 blobs，可能破坏仍可调用的生产/回放路径，且无法证明可恢复到同一业务身份。

历史改写前必须形成并审核：

1. 逐路径过滤清单和保留例外；明确当前 Head、生产入口、测试夹具、Owner 输入和证据归档的保留规则。
2. 三个远端 heads、五个本地独有 Tag、Codex refs、stash、所有 dangling 对象与全部 LFS 对象的恢复矩阵；平台不可见 refs 的边界说明。
3. 固定 filter 工具版本/参数、准确 rewrite refs 范围、恢复步骤与 dry-run 对照；确认不会造成部分历史或混合历史误用。
4. 对确认不再被生产、回放、验收和独立审计引用的 blobs，逐类比较重写前后路径、体积、提交拓扑和必要证据可读性。

当前只完成恢复冻结和只读大对象盘点；没有安装重写工具、没有重写 Git 历史、没有移动或删除 refs，也没有 GC/prune。

## WP-6 工作区清理门禁

85.5 GB ignored 文件包含数据库、Head/快照、输入包、运行产物和隔离证据。目录名为 cache、runtime、quarantine 或 report 并不能单独证明文件可删。现有 storage 合同明确禁止 Phase 1 cache 的 mtime 删除；用户约束还要求不删 TDX 只读输入，并将临时/测试文件留在 G:。

在每个候选路径可执行清理前，需要有：路径级归属、当前进程/数据库/Head 引用检查、内容身份与可重建来源、保留/恢复期限、精确删除范围及清理后的验证。当前没有已达到这些条件的大体积目录，因此本轮未删除 ignored 文件。小型解释器/pytest 缓存不改变主要空间占用，且尚未作为独立清理范围验证。

## 阶段结论

- WP-1 准入策略已实现并推送；本地目标检查此前 15 项通过，完整托管 CI 尚未运行。
- WP-2 PG 依赖整改仍为 `DESIGN_IN_PROGRESS / NOT_EXECUTABLE / NO DDL`：没有 canonical accepted Head；14 个 Owner 源路径/摘要未精确恢复；研究快照 authority 与现有 PG schema/release 不一致。禁止迁移写入、Owner 提升或 Head 移动。
- WP-3 恢复冻结为 `COMPLETED / VERIFIED`。
- WP-4 历史重写、WP-5A 远端 ref 切换、WP-5B 生产切换、WP-6 物理清理均未执行。

继续方向：完成 remaining `src/` 命中分类和 Owner/source identity 映射；只在确认业务替代链、逐路径过滤合同、恢复矩阵及阶段门满足后推进本地重写。远端 refs、生产 Head、运行服务和大体积 ignored 数据继续保持原状。
