# FP13 独立全产品审计欠项

状态 OPEN；本审计独立于阶段工程测试，禁止用空列表或不可用说明算完整产品覆盖。

| ID | 范围及证据 | 独立关闭条件 |
| --- | --- | --- |
| QA13-01 | Edge 不可用；CUA inventory 仅 IAB，创建 edge 返回不可用；实际浏览器离线能力未暴露 | 接通真实 Edge，在两指定尺寸重跑必备路径及浏览器离线，不以 IAB/503 代替 |
| QA13-02 | stocks/{id}/timeline 501 ENGINEERING_NOT_READY；HTTP_PERFORMANCE.json；技术图表可用，但结构事件/锚点暂无 owner 产物 | 绑定真实 owner 时序、Anchor/Event、Why Now 与失效条件；完成 API/UI/实值抽测 |
| QA13-03 | 板块成员仅 9/30，轮动/5、10、20 历史缺前日 PIT；sector_detail_members.txt；成熟度/健康/Seed 及部分历史字段不完整 | 真实历史成员和阶段输出、逐字段源时间、完整成员扩散及轮动 Timeline，不用当前成员回填 |
| QA13-04 | Focus 为只读 469 Episode，路径适配未准入；旧 PostgreSQL 不可读；FP08 原有债务；自动写入关闭 | 旧历史独立核对、真实 Observation/Path/Outcome 接入、事务写入准入及增量读回 |
| QA13-05 | 严格 PIT 0 日期可用；历史比较的 T0 篮子/三日前/阶段基准缺失 | 按 FP12_PIT_SOURCE_READINESS_20261008.md 的独立首获与成员基准要求关闭 |
| QA13-06 | H/等待/失效只在部分原始证据展示；FACT 字段中文标签不完整；FEATURE_PRODUCER_API_UI_TEST_MATRIX.json 为 110 项库存，未达到 100% 逐字段浏览器验收 | 将真实可用产物呈现为中文可读产品信息；不可得数据单独建债；逐字段浏览器核验 |
| QA13-07 | 未绑定分钟触板、官方媒体事实源、当前 LOO；V3 数据库退役 | 对批准真实来源分别接入；旧路由明确历史范围，不虚构恢复 |
| QA13-08 | 完整 CSV 下载此前超时，本轮未计通过；新日真实 DM01 全域增量还未用新增已核验输入演练 | 实测完整导出与新增日链、失败回退、Focus/Forward 消费链，不使用合成新日替代 |

样本成熟不足属于正常运营债务，不是上述结构缺失的替代理由，也不是独立阻止其余已具真实输入模块运行的理由。受影响能力仍需安全、真实性和完整性门禁。

已修复 QA13-LINK：事件、Focus、Forward 行提供真实 security_id 的个股详情跳转；event_stock_links_fixed.png 与 event_to_stock_detail.png 确认事件链。此修复不关闭其余审计项。
