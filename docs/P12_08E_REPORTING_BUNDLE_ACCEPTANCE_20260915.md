# P12-08E 市场强弱与波动 bundle 验收

## 阶段合同

依据升级文档 §17.2，在不改变资格、类别和排序的前提下，为活动研究结果补充同一交易日的市场强弱与个股波动。市场强弱采用既有市场因子 `market_ret20_median`，合同为 `MARKET_RET20_MEDIAN_V1`；波动采用既有因子库 `VOLATILITY20`，合同为 `FACTOR_VOLATILITY20_V1`。来源分别绑定受管 market 与 factors Parquet 的完整摘要，日期必须与 bundle 交易日一致，任何候选缺波动时 fail closed。

bundle 合同升级为 `TODAY_RESEARCH_BUNDLE_V3_3_CANDIDATE_02`，维度合同为 `TODAY_RESEARCH_REPORTING_DIMENSIONS_V3_3_CANDIDATE_01`。旧 bundle 和旧前向观测保持不可变，新 bundle 使用新 run、参数摘要及输出摘要，并经原子指针切换后才可见。

## 验收结果

**DEGRADED_PASS**。2026-09-14 的113条结果均具市场强弱与波动。市场20日中位收益为 -0.017740987871920688；候选 `VOLATILITY20` 范围0.008105008069609235至0.07027156463929313，中位数0.0387508434184502。活动 bundle 摘要为 `dc8ca188b15e1c4b0ee339e797b5273e746e71a6d766383a6f6801db475f0d66`，指针回读通过。

P12-06/07/08/08B/08C/08E 定向回归24 passed，compileall 与 `git diff --check` 通过。新观测合同下仍为1个真实信号日、113个 episode；452条后验计划仍全部 `NOT_DUE`。没有修改通达信目录或生产数据库，效果状态保持 `EFFECT_OBSERVATION_PENDING`。

## 下一步

等待下一真实收盘 publication，沿新 bundle 合同构建并封存第二个交易日，首次验证真实跨日进入、退出、类别和模式迁移。达到20个真实信号日前不进入V3校准。
