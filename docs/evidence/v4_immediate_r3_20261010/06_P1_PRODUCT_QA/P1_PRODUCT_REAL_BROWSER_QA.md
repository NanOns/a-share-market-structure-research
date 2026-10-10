# P1-PRODUCT 真实浏览器核验

真实只读 QA 服务 127.0.0.1:28767；使用冻结生产 Head，而非生成假 Owner。实际 DOM 摘录见 11_DEEPENING/ACTUAL_BROWSER_QA_EXCERPTS.json；数值与完整集合比对见 P1_PRODUCT_FP_REGRESSION_MATRIX.json。

六入口各在1920×1080和1366×768完成真实读取；另外核验来源抽屉、板块搜索/排序/UNKNOWN过滤/成员翻页/刷新返回、H两竞争解释、9/30历史画像、宽度503局部隔离及重试恢复。发现并修复 history.replaceState 清空返回上下文的问题；历史画像缺 adjusted Owner 引发的异常已修复，旧日期保留13.240并缺源降级。

23路实际API验证无差异：400板块、322成员、201重叠关系的完整来源比较及6入口数值抽样；负例陈旧token409、未来日期400、非法sort400、负offset400。DOM证据仅声明上述观察，不声称所有表格单元均经过浏览器数值核验。生产运行态另见 PRODUCTION_LOADING_AND_HEAD_PROTECTION.json。
