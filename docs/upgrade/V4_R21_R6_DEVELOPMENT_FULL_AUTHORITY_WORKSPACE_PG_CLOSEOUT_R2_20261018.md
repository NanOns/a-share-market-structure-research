# V4 R21 R6 开发全权限与 PG 全链路实修报告 R2

- 阶段状态：`DEGRADED_PASS`（开发候选链路可运行；工作空间别名迁移、正式 Owner/Head 和全功能验收未完成）
- 授权依据：Drive 最新任务卡 `V4_R21_R6_开发全权限_工作空间清理_PG全链路与全模块连续实修总任务卡_R2_20261018.md` 与长期开发授权 SOT R2。
- 范围：现役 V4 文件引用、PG 候选快照读取、28766 前端和接口实测；未重复此前 53 次提交/205 个文件审计。

## 实修

- 历史 SourceIngress 合同升至 1.1.0，拒绝超过 64 MiB 的内联源文件，避免将大 TDX ZIP 读入内存并 base64 写入 PG；兼容读取既有 1.0.0 记录。
- Corrected Owner 与 R43 Owner 的核心物化改从 PG DM01 accepted Data Head 取快照和 SHA，不再读本地 `V4_DATA_ACCEPTED_HEAD.json`。
- 个股历史图表移除非 PG 文件路径读取分支；没有 PG 历史绑定时返回 `SOURCE_INCOMPLETE / PG_HISTORY_BINDING_REQUIRED`。
- 更新 `AGENTS.md` 中与最新 SOT 冲突的 PG 只读和清理条款，保留开发/生产隔离及单库约束。

## PG 与运行实测

- 使用现有 `127.0.0.1:5432/market_research`（database OID `646711`）；本轮未执行 DDL/DML、Owner/Head 写入或合同注册。当前 PG 有 16 个合同版本和 16 个合同批准事件，但 publications、publication heads、operational research heads 均为 0。未伪造发布或接受状态。
- 唯一完整候选快照 schema `v4_research_e30350bf444bbb9980cf3e2c`：T0 `2026-09-30`，股票 5,213、身份全集 5,224、板块 378、Focus 469、Forward 117、事件 33。更新日期 2026-10-01 20:25:10（北京时间）；快照仍为候选，未代表正式 Head。
- 在 `127.0.0.1:28766` 运行候选服务，28765 未启动/触碰。浏览器实测：总览、股票搜索与详情/周线、板块搜索与详情、Focus、市场与事件、诊断、Forward、日更只读预览均读取候选 PG 数据。示例股票中华企业 SH.600675 展示 253 根日线和 54 根周线；区域地产返回 43 个成员。
- Forward 显示候选样本 117、计划期限 585、已发布期限状态 5（覆盖 1 个样本）、成熟合格 0。日更预览显示未接受市场日历，worker 未启动，写操作按钮禁用。
- PIT 回放与比较 API 返回 HTTP 200，但状态分别为 `PIT_NOT_AVAILABLE` 和无 T0 首次可得证明；未输出未来状态。浏览器回放/比较页未能完成可视化结果验证。
- 全程保持本地候选投影，不改动 Data Head 身份；未启动采集器或后台写进程。

## 验收、清理与遗留

- 已通过：涉及的 Python 文件 `py_compile`；SourceIngress 超限拒绝 smoke；无 PG 图表绑定时降级 smoke；`git diff --check`。
- pytest `tests/test_corrected_owner_replay_r4.py` 在收集阶段被项目隔离插件拒绝连接共享 PG（`DISPOSABLE_PG_CLUSTER_REQUIRED`），未绕过隔离插件。
- 本轮没有删除文件：未发现经过证明可安全删除、无消费者的重建产物。TDX 源目录及已有未跟踪用户文件保持原状。
- `v4_native.workspace_schema()` 仍以绝对根路径散列生成 schema；多个历史 schema 尚未建立数据保全和调用方切换映射，故本轮未改名/删除。更近日期的部分行情 schema 缺少唯一 metadata snapshot manifest，不能作为完整快照。
- 28766 上回归的 replay/compare 可视化、T0 证明、正式 Owner/operational Head、完整 PIT/Forward 成熟结果、工作空间逻辑身份与安全 alias 迁移、可删产物盘点及全模块正式验收仍待处理。
- GitHub fetch 曾遇 Schannel TLS 握手错误；提交和推送结果以本报告随后的 Git 命令回执为准。

## 下一阶段

持续在现役 V4 开发分支修复工作空间逻辑身份及 PG alias 迁移方案、PIT/Owner 证据链与回放 UI，补齐一致的完整快照和日更业务链，再运行全模块验收。正式切换至 28765 与最终生产打包继续等待用户另行明确启动。
