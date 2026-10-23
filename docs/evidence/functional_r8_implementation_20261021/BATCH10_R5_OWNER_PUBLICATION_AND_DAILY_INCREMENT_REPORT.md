# BATCH10-R5 Owner 发布与日增量报告

日期：2026-10-23（Asia/Shanghai）<br>
分支：`codex/v4-unified-development`<br>
请求基线：`e5b499fc23faaf21a6c819d8f0bd18fa611952e6`<br>
起始远端 HEAD：`37f104bf8c0d40152e8c9c11b8445dca9a5a84bd`。R5 已提交并推送为 `9d68ad114d86a77964e68946126f63481e236ab9`，当时通过 GitHub API 核对为分支 HEAD。直接 `git fetch` 曾遇到 TLS 握手失败，推送通过备用 TLS 后端完成。

## 更正前次审计判断

10/20、10/21 候选 JSON、每天 20 份目标日 Owner payload 和对应 PG Owner facts 均位于 `G:/codex_tmp/v4_daily_candidate_chain_20261020`。此前因只查仓库根目录而报告“候选/Owner 缺失”，判断错误。Token 是候选内容的 SHA-256 指纹，绑定日期、前序版本、来源和 Owner 字节、算法合同及 NON_PIT 状态，不是接入凭据。ReadIndex R1 与 R2 是不同合同；已有 10/21 R1 记录不能证明 R2 或 R8/D0 精确 Token 发布已经完成。

## 开发 PG 精确 Token 发布

两个候选均通过验证；每天 20/20 份 Owner 文件与候选记录的字节数和摘要一致。为每个精确 Token 准备了 ReadIndex R2。10/20 首次 28766 回调返回 `READ_INDEX_TOKEN_NOT_PREPARED`，候选 CAS 已回滚；准备 R2 后，同一 Token 重试并完成发布。失败尝试保留在追加式事件历史中。重试必须有已验证的 callback-only abort、PG pending 行和精确前序版本恢复证据。

| 日期 | 候选 Token | R8 | D0 | ReadIndex R2 | 个股/板块 Priority Owner | D0 读回 |
|---|---|---|---|---|---|---|
| 2026-10-20 | `a5b169a8cde60cc6ba86f1efbb7714020e578264bfea33634532ab407df70b70` | `PUBLISHED` | `PUBLISHED_DEV_ASOF_SOURCE_VERIFIED` | `REAL_PG_PASS` | PG 读回通过；因精确输入缺失或无效，个股可排序 0/5,224，板块可排序 0/400 | 10,452 facts；5,226 predicates；摘要通过；TRUE 141 / FALSE 5,033 / UNKNOWN 52 |
| 2026-10-21 | `14ee0cf87a46f810b52295a8d42c4bbda391fd0fe49f4cb3457a1620067ad378` | `PUBLISHED` | `PUBLISHED_DEV_ASOF_SOURCE_VERIFIED` | `REAL_PG_PASS` | PG 读回通过；个股可排序 936/5,224；因当前带日期输入门禁，板块可排序 0/400 | 10,448 facts；5,224 predicates；摘要通过；Launch TRUE 78 / FALSE 5,098 / UNKNOWN 48；Recovery TRUE 28 / FALSE 5,147 / UNKNOWN 49 |

写入仅作用于 `127.0.0.1:5432/market_research` 的候选 schema。两个候选仍为 `AS_RECORDED=false`、`PIT_ELIGIBLE=false`、`production_accepted=false`。未触碰正式 Head、调度器和 28765。

## Lifecycle 实际行情边界

当前分支的 `conserve_lifecycle_status_rows` 已从同日 RAW Owner 身份推导 `actual_bar_present`，因此没有重复修改已正确的源代码。使用 PG 读回的 10/21 Owner 行重放：RAW 5,216、lifecycle 5,224、正常实际行情数量 5,216。内存负例中撤掉一条真实 RAW 身份后，状态仍为 `ACTUAL_TRADED`，但 `actual_bar_present=false`、`status_conflict=true`、原因是 `RAW_BAR_RECEIPT_NOT_FOUND_FOR_DATE_AND_SECURITY`。错误日期的 RAW 行被拒绝。此次复核没有发现真实来源行错误声称存在行情。

## Focus Priority、Forward 与 10/22

- `V4_DAILY_RESEARCH_PRIORITY_R1` 是已有的个股/板块排序合同；10/20 与 10/21 的精确 Token Owner 已物化并从 PG 读回。10/20 没有可排序行：5,217 只个股的价格坐标证明无效，79 个板块的带日期轮动/lifecycle 输入无效，其余未知。10/21 有 936 只个股可排序，板块仍因缺失或无效的带日期 lifecycle 输入而不可排序。`/priority` 兼容 API 仍没有运行 Owner。该合同不定义 Focus 排序，不能代替 Focus 规则。28766 的 `focus/priority` 对 10/21 返回 `SOURCE_INCOMPLETE / NO_OPERATIONAL_FOCUS_SUBPAGE_OWNER`。当前 Focus 合同没有版本化排序规则，因此正式 Focus Priority 仍为 `CONTRACT_BLOCKED`，没有臆造排序。
- 独立 Forward 验证 cohort 仍为 `WAIT_TRUE_FIRST_CAPTURE`。可见的 10/21 页面显示首次采集截止时没有 T0 capture，并禁止回溯补录；as-of 信号来源、cohort Owner 和首次冻结收据仍缺失。
- 未找到 10/22 SourceIngress 收据。只读扫描 11,884 个配置的 TDX `.day` 文件，最新末条记录日期为 2026-10-08（2 个文件为空或格式异常）。没有伪造 10/22 增量。

## 28766 与页面读回

28766 服务于 10/21 Token `14ee…`；已读取 context、Focus（3,975 个对象）、home、Priority 和 Forward 路由。Focus Priority 显示 Owner 缺失；Forward 返回 `NO_AUTHORIZED_COHORT_OWNER`。`/v4/research/focus` 的浏览器可访问性检查显示所选日期为 10/21、3,975 行 Focus、历史 NON_PIT 提示和首次采集警告。PostgreSQL 使用 5432；唯一网页监听为 28766；28765 未监听。

## 代码范围、临时脚本与后续工作

R5 代码改动是：已证明回调回滚后的安全 R8 重试并保留失败尝试；补齐候选发布命令声明的 R8→D0 发布和读回顺序。`py_compile` 与 `git diff --check` 通过。聚焦 bridge 回归在最终 D0 编排改动前通过。Lifecycle 修正原已存在，并通过精确 PG Owner 行复核。

本次按新增脚本生命周期规则，移除了两个仅用于 R5 取证的 `audit_batch10_r5_*.py` 一次性脚本；PG 读回、fixture 和结果证据保留。R6 市场趋势日期泛化、S02 来源与计算期间性能、D2 冻结价位规则仍按任务卡后续推进。正式 Focus Priority 在制定版本化业务规则前不能发布。此次开发不代表生产验收或外部审计签字。

按设计稿最后更新时间划定的代码扫描范围、发现项和限制见[设计稿之后提交的代码通用性扫描报告](POST_DESIGN_CODE_GENERALITY_SCAN_20261023.md)。机器可读证据见 `BATCH10_R5_OWNER_PUBLICATION_AND_DAILY_INCREMENT_EVIDENCE.json`。
