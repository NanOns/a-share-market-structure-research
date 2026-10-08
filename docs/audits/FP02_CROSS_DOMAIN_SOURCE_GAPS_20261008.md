# FP02 跨域独立审计

以下审计的关闭条件独立于 FP02/03/04 基础工程门，不因测试通过而自动关闭。

| 审计 | 范围 / 证据 | 状态与独立验收 |
|---|---|---|
| AUD-FP02-CURRENT-CORE-CHAIN | 当前 accepted 日为 2026-09-30，但 V4-05 owner Core 产物首行及窗口为 2026-09-28；V4-08 产物明确上游 Core/历史能力不足；影响 Core、板块、市场与 LOO 相关结果 | OPEN：按当前数据身份定点重算并发布 Core/四轴及实际依赖产物；逐域字段与原始输入核对，禁止跨日冒充 |
| AUD-FP02-FOCUS-PROJECTION | 现有 Focus 代码不等于当前日有可绑定 Episode 生产投影；117 个 Forward cohort 不等于 Focus Episode | OPEN：发布真实 Episode/事件/观察/退出投影，证明来源和跨日延续，由 FP-08 具体执行 |
| AUD-FP02-NAME-ENCODING | 旧 identity/membership 名称含替换字符；显示层已只读捕获 GB18030 TNF/板块名称，另标观察时间；原产物不改 | DISPLAY_REPAIRED / HISTORICAL_SOURCE_OPEN：历史身份源修订需独立 owner 验收；显示修复不升级历史 PIT 安全性 |
| AUD-FP02-PROFILE-UNIVERSE | 高级画像 5,224 行，当前 RAW 池 5,213；11 个额外身份隔离 | OPEN_SCOPED：核对身份和当日可用性后，由 owner 发布修订；不能用扩池隐藏差异 |
| AUD-FP02-FIELD-REASON-GAPS | 沿用 AUD-FP01-FIELD-REASON-GAPS：高级画像部分 UNKNOWN 原因为空，但来源身份仍存在 | ADAPTER_EXPLAINED / OWNER_OPEN：适配层明确原 owner 原因缺失，保留原字段定位；原 owner 修订及独立验收后关闭 |
| AUD-FP04-EDGE-COVERAGE | 当前可用内置浏览器，未连接 Edge | OPEN：真实 Edge 下六入口、详情、键盘、1366/1920 独立验收；不以截图尺寸替代浏览器类型证明 |

证据索引：`docs/evidence/fp02_20261008/SNAPSHOT_DICTIONARY.json`、`REAL_READBACK_AND_ROLLBACK.json`、`DISPLAY_NAMES_QA.json`、`BROWSER_READBACK.json`。

AUD-FP02-EXPECTED-CURRENT-BINDING：OPEN。E5 工程分支已完成的事实保留；已检查的 API_READBACK 明确在 fixtures 与历史 reconstruction 下，当前正式推断输出尚未绑定。关闭要求当前日特征/模型/真实推断与独立 QA；不得拿历史 fixture 结果填充当前页，也不以旧 UNGRANTED 或长期样本不足代替该工程核查。证据：REAL_ALGORITHM_SOURCE_AUDIT.json。
