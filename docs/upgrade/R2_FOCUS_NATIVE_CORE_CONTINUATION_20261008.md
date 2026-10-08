# R2 Focus 原生 Core 谓词接入合同

接续 R2_FOCUS_CONTINUATION 与 R2_AVAILABLE_FIELD_CLOSURE，独立 AUD_R2_FOCUS_NATIVE_CORE。旧日志、旧实现与发布证据冻结。新命名空间只接入实际按观察日绑定的 Core ma20、ret5、severe_extension；值需注册表参数、源摘要、trade_date、窗口截止均一致，价格坐标必须原生截至观察日目标坐标并与实际 RAW 终点一致。未来发布或同日错误参数一律失败关闭。

有实际当日因素绑定才可评估对应谓词。未绑定 9/29 Core 不以 9/30 回填；structure_break、confirmation、历史 RPS 序列和原行业相对强度缺源保持 UNKNOWN。不得用价格损伤替代结构失效。新日志从原有两日真实状态重放，保留事件/周期/锚点身份及每个旧观察价格、Outcome 值，只有新版本路径判断变化。

验收：独立实源值/同坐标 oracle、未来日期和参数反例、两日重放身份/价格/结算保持、新旧差异、实际 IAB 两桌面、联合失败回滚和日更准入后继后方可正式切换；TDX 只读，Phase0 DEGRADED_PASS，strict_pit=false。阶段 IN_PROGRESS。
