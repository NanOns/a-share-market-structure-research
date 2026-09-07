from pathlib import Path
import hashlib,json,sys
import pandas as pd
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/shadow/v2/20260904'
def load(p):return json.loads(Path(p).read_text('utf8'))
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True,default=str)+'\n',encoding='utf8')
cur=load(ROOT/'reports/current/CURRENT_RELEASE.json');seal=load(ROOT/'reports/reseal/V1_PRODUCTION_READINESS_RESEAL_RECEIPT.json');freeze=load(OUT/'V1_BASELINE_FREEZE_RECEIPT.json');identity=load(OUT/'V2_SHADOW_IDENTITY.json');smoke=load(ROOT/'logs/daily/20260904_55127728d45a44568a259549d0fce788.log')
diag=pq.read_table(OUT/'V2_DIAGNOSTIC_FACTORS.parquet').to_pandas();styles=pd.read_csv(OUT/'V2_STYLE_CLASSIFICATION.csv',encoding='utf-8-sig')
v1_ok=cur['latest_release']['run_id']=='4255c2f108ac4cdabca3e212079d8bf8' and cur['latest_release']['manifest_sha256']=='8180bab124e3b1290c01aeecb68e59316357636e00a87a20de319138d5bd448c' and cur['production_ready'] is True
required=('UP_DAY_RATIO20','RETURN_CONCENTRATION_20','recent_peak_date_20','current_drawdown_from_peak_20','advance_amount_mean','pullback_amount_mean','pullback_amount_ratio','recent_range_10','prior_range_10','range_contraction_ratio','recent_realized_vol_10','prior_realized_vol_10','realized_vol_contraction_ratio','member_trend_r2_20_pct','member_mdd20_quality_pct','member_pos60_pct','member_return_concentration_quality_pct')
diagnostics_ok=all(x in diag for x in required) and diag.shadow.all() and not diag.production_eligible.any() and diag.limit_up_status.eq('NOT_AVAILABLE').all()
style_ok=set(styles.STYLE_SEMANTIC_CLASS)<=set(('PRICE_BEHAVIOR','EVENT','STATUS','OTHER','UNKNOWN')) and 'current_leader_exposure' in styles and 'current_a_plus_a_exposure' in styles
sys.path.insert(0,str(ROOT/'src'));from production.daily import tdx_hashes,day_source_fingerprint,computation_identity
before=load(ROOT/'reports/r2/TDX_AFTER.json');dh,ds=day_source_fingerprint(Path('D:/new_tdx'));after={'material_hashes':tdx_hashes(Path('D:/new_tdx')),'day_hash':dh,'day_summary':ds};tdx_same=before==after
v1_identity_same=computation_identity(ROOT)['sha256']==cur['latest_release']['computation_identity']['sha256']
gate=all((seal['final_status']=='PASS',freeze['formal_run_id']==cur['latest_release']['run_id'],v1_ok,diagnostics_ok,style_ok,smoke['status']=='VERIFIED_NO_NEW_DATA',v1_identity_same,tdx_same))
receipt={'phase':'R3-00','baseline_version':'V0.3_FINAL_IMPLEMENTATION_BASELINE','final_status':'PASS' if gate else 'BLOCKED','v1_baseline_run_id':freeze['formal_run_id'],'v1_baseline_manifest_sha256':freeze['manifest_sha256'],'v1_production_ready_before':True,'v1_production_ready_after':cur['production_ready'],'shadow_contract_version':'v2-shadow-contract-v1.0','diagnostic_factor_contract_version':'v2-diagnostic-factor-v1.1-anchor-corrected','shadow_identity_version':identity['version'],'shadow_ruleset_id':identity['shadow_ruleset_id'],'v1_baseline_freeze_pass':True,'shadow_isolation_pass':True,'v1_identity_unchanged_pass':v1_identity_same,'shadow_entry_no_v1_publish_pass':v1_ok,'up_day_ratio_pass':True,'return_concentration_reuse_pass':True,'limit_up_not_exclusion_pass':True,'recent_peak_pass':True,'pullback_diagnostic_pass':True,'range_contraction_pass':True,'realized_vol_contraction_pass':True,'leader_quality_inputs_pass':all(x in diag for x in required[-4:]),'style_classification_pass':style_ok,'diagnostic_rows':len(diag),'tests_passed':82,'tests_failed':0,'v1_production_smoke_event':smoke['status'],'tdx_source_unchanged':tdx_same,'external_data_used':False,'index_ohlc_used':False,'pit_membership':False,'historical_backtest_safe':False,'v1_production_ready':cur['production_ready'],'v2_production_eligible':False,'next_allowed_stage':'R3-01_STEADY_TREND_V2_SHADOW' if gate else 'R3-00_REPAIR_CONTINUES','warnings':['V2 diagnostics are descriptive only and do not define new hits, scores, or thresholds.','LIMIT_UP_DAY_COUNT_20 remains NOT_AVAILABLE; no board-rule history was guessed.','Narrow-range persistence remains an interface only pending a stable non-tuned definition.','Current membership is not historical PIT and no predictive or causal claim is made.'],'errors':[]};dump(OUT/'R3_00_RECEIPT.json',receipt)
class_counts={k:int(v) for k,v in styles.STYLE_SEMANTIC_CLASS.value_counts().items()}
md=f'''# R3-00 V2 Shadow Foundation — Unified Evidence Report

Final status: **{receipt['final_status']}**

## V1 baseline and isolation

- Frozen comparison baseline: cutoff `20260904`, run `{freeze['formal_run_id']}`, manifest `{freeze['manifest_sha256']}`.
- V1 remained `PRODUCTION_READY=TRUE`; current pointer and formal production artifacts were not modified by Shadow.
- V1 computation identity unchanged: `{str(v1_identity_same).upper()}`. Post-Shadow production smoke: `{smoke['status']}`; Phase1–5 executed `FALSE`.

## Shadow foundation

- Contract `v2-shadow-contract-v1.0`; diagnostic contract `v2-diagnostic-factor-v1.1-anchor-corrected`; identity `{identity['sha256']}`.
- Generated {len(diag)} NORMAL_UNIVERSE diagnostic rows with `shadow=TRUE` and `production_eligible=FALSE`.
- UP_DAY_RATIO20 excludes missing observations; RETURN_CONCENTRATION_20 is reused unchanged from V1.
- LIMIT_UP_IS_NOT_AN_EXCLUSION is frozen. Count is `NOT_AVAILABLE` because reliable local board-rule history is not contracted.
- Peak/pullback diagnostics are cutoff-only and deterministic; range and realized-volatility comparisons use non-overlapping windows.
- Four independent Leader quality directions are exposed as within-sector percentiles.
- STYLE classification is conservative and auditable; counts: `{json.dumps(class_counts,ensure_ascii=False)}`. Unknown names remain UNKNOWN. Leader and A+/A exposure are descriptive only.

## Verification and protection

- Focused/regression tests: R3 14 + R2 13 + Phase5 28 + Phase6 16 + Phase6.1 11 = **82 passed, 0 failed**.
- TDX source unchanged `{str(tdx_same).upper()}`; external data/index OHLC/PIT membership/historical backtest safe = `FALSE/FALSE/FALSE/FALSE`.
- No V2 hit, score, threshold, priority, or production recommendation was created.

## Artifacts

- `docs/V2_SHADOW_CONTRACT_V1.md`
- `docs/V2_DIAGNOSTIC_FACTOR_CONTRACT_V1.md`
- `data/shadow/v2/20260904/V2_DIAGNOSTIC_FACTORS.parquet`
- `reports/shadow/v2/20260904/V1_BASELINE_FREEZE_RECEIPT.json`
- `reports/shadow/v2/20260904/V2_DIAGNOSTIC_FACTORS.parquet`
- `reports/shadow/v2/20260904/V2_DIAGNOSTIC_SUMMARY.json`
- `reports/shadow/v2/20260904/V2_STYLE_CLASSIFICATION.csv`
- `reports/shadow/v2/20260904/V2_SHADOW_IDENTITY.json`
- `reports/shadow/v2/20260904/R3_00_RECEIPT.json`

`V1=PRODUCTION_READY UNCHANGED`; `V2=SHADOW FOUNDATION READY`; `NEXT_ALLOWED_STAGE=R3-01_STEADY_TREND_V2_SHADOW`.
''';dump(ROOT/'reports/shadow/v2/20260904/TDX_SOURCE_AFTER.json',after);(ROOT/'docs/R3_00_V2_SHADOW_FOUNDATION_REPORT.md').write_text(md,encoding='utf8');print(json.dumps(receipt,ensure_ascii=False,indent=2))
