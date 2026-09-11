# M14-01 来源验证合同 V1

- 阶段：`M14-01`
- 合同 ID：`M14_SOURCE_VALIDATION_V1_0`
- 设计基线：`docs/WORKBENCH_M7_M15_IMPLEMENTATION_PLAN_V2_1.md` 第 14、14.1 节及第 22.9 节
- 前置阶段：`M13B-03`，当前回执见 `reports/upgrade_m13/m13b_03_display_receipt_20260911.json`
- 本阶段状态：`DEGRADED_PASS`（探测证据已登记；没有 capability 准入）
- 个人研究分支：允许本机私有采集，但不允许发布、共享、生产 API/UI 消费或改变本地快照身份

## 1. 目的与边界

本阶段只建立并核验在线来源注册、逐 dataset 能力状态和准入证据边界，并对候选公开入口做一次有界探测。目标 dataset 为：

- `HOT_RANKINGS`：平台热榜/排名；
- `EXTERNAL_EVIDENCE`：涨停原因或其它有来源的外部证据；
- `QUOTES_LATEST`：可选盘中报价；
- `LH_LIST`：低优先级龙虎榜证据。

本阶段不实现生产抓取器、数据库迁移、批次物化、API37–40 或 UI 接入；只访问注册表中声明的公开候选入口，保存响应元数据与哈希，不保存原始在线正文，不读取凭据。若用户明确选择个人研究分支，下一阶段可以在本机建立隔离的批次/载荷对象，但必须标记 `PERSONAL_RESEARCH_ONLY`，不可进入发布头。

## 2. 状态与准入语义

来源类分为 `ONLINE_A` 和 `ONLINE_B`。网页可访问不等于许可，也不等于字段、日期语义或稳定性已经证明。

每个 source/dataset/capability 组合必须独立记录：

- `terms_state`：`NOT_VERIFIED`、`VERIFIED`、`REJECTED`；
- `status`：`NOT_VERIFIED`、`UNAVAILABLE`、`REJECTED`、`ENABLED`；
- `supports_history`、`supports_quote`、`supports_rank`、`supports_reason`；
- `documentation_ref`、字段证据、时间语义、请求预算和缓存策略。

没有对应证据时保持 `NOT_VERIFIED`，不能由静态 URL、网页可打开或其它 dataset 成功推导。历史与最新能力必须分开声明；不支持历史的端点不得接受日期后返回当天数据。

## 3. 当前工作区的安全决定

当前根目录 `AGENTS.md` 第 4 条已允许受合同约束的 M14 在线增强。因此本阶段：

1. 所有 M14 dataset 初始保持 `NOT_VERIFIED` 或 `UNAVAILABLE`，不能因为 HTTP 200 自动准入；
2. `config/m14_source_registry_v1.json` 中仍不得有 `enabled=true` 的生产来源；
3. 本阶段只写入探测元数据报告，不写入 `online_fetch_runs`、`online_payloads`、`online_batches` 或其它生产在线对象；
4. 本地首屏和 M13 已验收能力不等待、不依赖在线来源；
5. 本阶段只能出具 `DEGRADED_PASS`，不能出具 `PREVIEW_PASS` 或 `release_ready=true`。

这不是对任何第三方来源可用性的判断；它只是当前项目守则下的 fail-closed 阻断。

## 4. 重新开放 M14-01 的验收条件

逐 dataset 完成以下证据后才能进入 M14-02：

1. 记录官方说明或公开网页入口、许可/个人研究可用性、字段与时间语义；B 级条款不明则继续待验证；
2. 证明不需要账号、私有 Token、验证码绕过、动态签名绕过或私有会员服务；
3. 完成目标场景的脱敏固定响应解析样本，分开验证 `fetch_latest` 与 `fetch_history`；
4. 具备代码映射、日期一致性、字段完整性、空响应、乱码、字段漂移、429/超时和重复抓取的证据计划；
5. 明确 10 个交易日观察的分母、成功率和必要字段完整率；
6. 失败时仅将该 capability 置为 `UNAVAILABLE`，不影响本地主流程。

通过上述条件也只允许进入 M14-02，不自动启用热榜、原因、报价或龙虎榜。

个人研究分支不替代来源许可结论：候选来源仍保持 `REJECTED`，个人采集对象必须单独标记 `PERSONAL_RESEARCH_ONLY`、禁止共享/发布、禁止影响本地分析结果，并保留请求、接收和观察时间。

## 5. 独立审计项

`M14-01-SOURCE-AUTHORIZATION-20260911`：当前范围为在线规则/授权前置条件和逐 dataset 证据。接受条件是根目录守则已明确允许在线增强、用户授权范围已登记、每一能力有独立证据；不能以本阶段注册表结构测试代替来源准入。

## 6. M14-01-REVIEW 裁定（2026-09-11）

本次复核检查了候选公开页面、探测载荷和来源服务协议。结论是：当前两个候选均不能证明允许本项目自动采集、缓存、持久化或再展示数据，因此不准入生产适配器。

- `EASTMONEY_HOT_RANK`：页面与编码载荷可达，但服务协议对行情数据复制、向机构/他人提供及开发衍生产品设置限制；在没有书面授权或明确开发者许可前，标记 `REJECTED`。
- `TONGHUASHUN_HOT_RANK`：接口可解析并返回排名字段，但公开服务协议没有证明本项目所需的自动抓取、缓存和再展示权限，且响应没有明确 `source_as_of`；标记 `REJECTED`。

因此 `HOT_RANKINGS` 不可用，`QUOTES_LATEST`、`EXTERNAL_EVIDENCE` 和 `LH_LIST` 继续保持 `UNAVAILABLE` 或 `NOT_VERIFIED`。本裁定不评价来源网页本身的可用性，不把公开访问等同于授权。

下一步只能是：登记来源方明确的书面/开发者许可，或替换为许可范围清晰的来源；在此之前不得进入 M14-02，也不得建立在线生产表或启用 API37–40。
