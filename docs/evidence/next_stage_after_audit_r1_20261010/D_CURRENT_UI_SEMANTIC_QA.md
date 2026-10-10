# 当前研究UI语义核验

本轮68真实HTTP请求无HTTP状态/日期绑定错误；原始回执见D_HTTP_READBACK.json。当前事实：5224股票、400板块、2805条Focus受限研究清单；这些是研究对象/标签，不能表述为正式观察分母或提前捕捉成功。

实际六种图表：D/W/M × RAW/QFQ，行情非空、真实数值、末日不晚于10/09；历史10/08和9/30请求逐项绑定所选日期，中文名/代码搜索找到相同实体。Focus Episode/anchor/逐日路径/outcome各接口可读，不证明正式Cohort入组或独立成熟样本。市场和首页变化路径可读；个股timeline EMPTY_VALID不代表完整结构/Anchor事件功能已补齐。

旧token返回409 CONTEXT_TOKEN_MISMATCH；10/12股票与Cohort请求400 TARGET_DATE_NOT_GRANTED。10/08候选缺源保持NOT_CAPTURED；10/09 cohort research_signal_count=20896、research_eligible_count=300，observed_count/matured_count=null、正式写入false。缺源Forward/统计/结算/FEP仍SOURCE_INCOMPLETE，HTTP200不算计算READY。

当前JS原字节与服务返回一致。D_MODULE_SEMANTICS_JUNIT.xml的5项实际模块测试确认：HTTP200缺Owner转组件503、临时503只允许显式重试、未失败区块继续读取、409/400保持错误类别、日期/token绑定、AbortError不回退陈旧数据。app.js各section独立ErrorState提供“重试”，读源失败不默认全页面UNKNOWN；模块测试不等于浏览器交互。

来源时钟：旧生产Python未加载新字段，候选冻结/来源再观察时间仍不能用当前UI证明。isolated Python加载见B_ISOLATED_PYTHON_LOAD_HTTP.json；源截止日期不能充当历史first_available。该加载没有重启28765。

浏览器证据限制：本轮IAB打开localhost被net::ERR_BLOCKED_BY_CLIENT拦截；inventory仅IAB/MCP Apps，Chrome不可用。1366和1920真实布局、截图、浏览器503点击重试/组件隔离、跨日实际DOM切换和离线路径仍PENDING_BROWSER_SURFACE。未借旧截图补本轮PASS，也未绕过浏览器限制。

下一阶段：独立审核可读业务scope；接通本机浏览器表面后补双视口DOM/截图与交互验收。FP13整体和FP14全量发布保持未获准。
