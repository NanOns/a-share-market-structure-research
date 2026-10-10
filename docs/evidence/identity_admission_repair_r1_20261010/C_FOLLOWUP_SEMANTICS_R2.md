# D2 随访分类 R2

核对冻结 config/v4_10_input_provenance_r1_2.json 与 D2 admission：followup_complete 保留 TRI TRUE/FALSE/UNKNOWN；无 Episode 为 null。该生产者全部完成才 TRUE，其余 UNKNOWN，不把未到期填成失败。

新增 followup_status：无合法 Episode 为 NO_PRIOR_EPISODE；全部未到期或已完成与未到期混合、且无缺源为 PENDING；任一到期缺合法 settlement 或日历不覆盖 horizon 为 UNKNOWN；所有 horizon 完成为 COMPLETE。next_due_date 为仍待到期且已知日历日期的最早值。unknown_due_reasons 逐 horizon 列出缺日历或到期缺/错 Episode 来源。停牌、退市、旧事件不能替代创建绑定的 settlement；合法迟到来源可使对应 horizon 完成。

C_FRONTEND_INTERFACE_SAMPLES.json 提供前端可直接读取的真实函数输出形状，全部明确合成测试；本轮未把字段接入生产 HTTP，不宣称生产页面已显示。Python 验证单/混合 horizon、迟到完成、日历断档、无 Episode/Owner、停牌与退市；Genesis 无历史回填。
