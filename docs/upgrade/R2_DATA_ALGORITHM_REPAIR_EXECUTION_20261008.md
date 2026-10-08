# R2 数据算法修复执行合同 V1

用户授权：按桌面 01_NEXT_ROUND_DATA_ALGORITHM_REPAIR_CARD.md 与 00_R2_C68964EE_INDEPENDENT_DATA_ALGORITHM_AUDIT.md 执行相关修复。文档作为用户指定的工作范围及验收依据；其中历史审计结论不视为本机新验收。

入口：c68964eecc3653e3fb588113f615c925696959f9，干净工作区，当前分支 codex/v4-fp14-r2-repair。A0 首先冻结固定 SHA 与当前联合发布；保留全部旧收据。Phase 0 沿用 reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json 的正式结果，不启动 scanner。

阶段合同：R2_DATA_ALGORITHM_REPAIR_V1。按 A0→A1/A2→A3/A4→A5/A6→A7 记录真实输入、独立计算、缺失原因与接受范围。当前 operational 与历史严格 PIT 分离；没有日期归属的前日成员不得回填。Owner 无输出不推测状态或 H1/H2。每阶段提交推送；推送不等于外部验收。取消多浏览器、多分辨率专项。

证据目录：docs/evidence/r2_data_algorithm_repair_20261008。每项 PASS 必须限定范围，未取得的真实数据标 NOT_VERIFIABLE，实际未实现标 FAIL。跨域缺口独立记账。原始 T0、入组、锚点不改。所有新写入原子进行且位于项目或 E:/codex_tmp；TDX 全部只读。

A0 验收：CLI 已确认 origin/codex/v4-fp14-r2-repair 与入口 SHA 一致，指定 system-reform 远端仍为 682ed2d779e33d5cef24188ff5fa727d41626f70；需以正常 fast-forward 同步指定交付分支并回读。下一步：冻结 source/owner/read/Focus/Forward 联合矩阵与逐域债务定位。
