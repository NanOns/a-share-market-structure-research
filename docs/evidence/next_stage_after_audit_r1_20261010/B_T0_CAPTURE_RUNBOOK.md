# 2026-10-12 真实 T0 现场运行手册（PENDING）

仅在真实系统日期、官方交易日历与来源实际均满足时执行。预计下个交易日 10/12；不改系统时间，不填未来首获。时区 Asia/Shanghai。

1. 18:35 前只读检查 PID/28765、运行加载提交、DailyJobs AUTO_ON/next_trigger/active_job、当前两个Head SHA、last-good。TMP/TEMP/TMPDIR=G:/codex_tmp；不得向 D:/new_tdx 或任何配置TDX目录写入。
2. 原 DailyJobs 18:35 首次尝试；计划重试 19:05、19:35、20:05、20:35、21:05、22:05。尊重取消/并发/终态；不启动第二个自动调度器或绕过已取消任务。
3. 每次逐项读取 Source expected/actual：目标日期、provider日期、TDX target bars覆盖/计数，BaoStock daily全集/停牌/字段，factor当日变化或带hash无变化证据、TDX GBBQ前后stat+SHA。记录请求/接收/observed/first_available原字段与timestamp_basis，缺失为null。
4. 保留 package、target、native raw、live receipt、immutable runtime manifest 的字节SHA/路径。单源未齐不得删除已经取得的原件；禁止把重试较晚时间覆写首次收到的原件时钟。
5. 合并 daily_freeze → capture：记录 previous Head/Identity/membership绑定，captured_at、原始成员文件SHA、prior membership与preliminary scope。读取 old_head_identity_preflight 的 missing/added codes。若 native相符而旧pool不同，明确为旧Identity依赖失配，保留新源；main DD仍fail-closed，不称BaoStock网络不可用。
6. 有真实合法当天Identity Owner后，单独核对新 lifecycle每行source_security_key/date/security_id、全Universe、当天成员原件、GBBQ角色。仅独立审查通过的合同可修订闸；诊断candidate不是authority。
7. 旧闸通过才进入build/seal/数值QA。同日reconcile的capture SHA必须与原件相同，new Head、owners、membership、added/removed IDs必须逐字段一致。Publisher读取 exact sealed candidate；研究状态不自动成为PIT。
8. State/capture eligibility逐字段审：state/model/member first_available/frozen_at、state_lineage_id/frozen_signal_version/capture_deadline、episode/event/benchmark、AS_RECORDED与当时membership、observed cutoff。缺项SOURCE_GAPS，历史corrected不能补录为当时已知。
9. 发布仍要求独立原有scope policy、数值QA、live readback、CAS、last-good。失败保留旧Head与原件并记录具体阻断；成功后读取新Head SHA、实际accepted日期和Owner绑定。正式State/Cohort/D2及Writer Grant各自外审；无Grant不能enroll。
10. 现场完成后原子写证据、提交推送并回读remote；不得以Git/HTTP200代替外部签收。T+1/T+3/T+5按真实后续会话追加，首日没有成熟统计。

10/12所有现场结果目前 PENDING，不存在本轮真实采集成功声明。
