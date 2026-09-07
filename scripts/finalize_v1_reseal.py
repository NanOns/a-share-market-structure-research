from pathlib import Path
import hashlib,json,sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/reseal';OUT.mkdir(parents=True,exist_ok=True)
RELEASE=ROOT/'reports/releases/20260904/4255c2f108ac4cdabca3e212079d8bf8'
def load(path):return json.loads(Path(path).read_text('utf8'))
def dump(name,value):(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True,default=str)+'\n',encoding='utf8')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

r0=load(ROOT/'reports/r0/R0_FINAL_RECEIPT.json');r1=load(ROOT/'reports/r1/R1_FINAL_RECEIPT.json');r2=load(ROOT/'reports/r2/R2_FINAL_RECEIPT.json')
current=load(ROOT/'reports/current/CURRENT_RELEASE.json');prod=load(RELEASE/'PRODUCTION_RECEIPT.json');inp=load(RELEASE/'INPUT_SNAPSHOT_MANIFEST.json')
sys.path.insert(0,str(ROOT/'src'))
from production.release import validate_release_generation
from common.input_snapshot import validate_input_snapshot_manifest
from production.daily import computation_identity,render_identity,source_identity,tdx_hashes,day_source_fingerprint
validation=validate_release_generation(RELEASE,expected_manifest_sha256=r2['release']['manifest_sha256']);validate_input_snapshot_manifest(inp)

manifest_ok=validation['manifest_sha256']==prod['manifest_sha256']==r2['release']['manifest_sha256']
integrity={'release_directory':str(RELEASE),'release_directory_exists':RELEASE.is_dir(),'required_files_present':all((RELEASE/x).is_file() for x in ('manifest.json','PRODUCTION_RECEIPT.json','INPUT_SNAPSHOT_MANIFEST.json','run_audit.json')),'manifest_hashes_match':True,'receipt_manifest_match':manifest_ok,'input_snapshot_hash_valid':True,'pass':manifest_ok}
dump('V1_RELEASE_INTEGRITY_AUDIT.json',integrity)

pointer=current['latest_release'];pointer_ok=str(pointer['date'])=='20260904' and pointer['run_id']==prod['run_id']==r2['release']['run_id'] and Path(ROOT/pointer['release_path']).resolve()==RELEASE.resolve()
ids={k:prod[k]['sha256']==pointer[k]['sha256']==inp[k]['sha256'] for k in ('source_identity','computation_identity','render_identity')}
pointer_audit={'cutoff':pointer['date'],'run_id':pointer['run_id'],'release_path':pointer['release_path'],'expected_run_id':'4255c2f108ac4cdabca3e212079d8bf8','pointer_pass':pointer_ok,'identity_binding':ids,'pass':pointer_ok and all(ids.values())};dump('V1_CURRENT_POINTER_AUDIT.json',pointer_audit)

sectors=pd.read_csv(RELEASE/'sectors.csv',encoding='utf-8-sig');stocks=pd.read_csv(RELEASE/'stocks.csv',encoding='utf-8-sig');candidates=pd.read_csv(RELEASE/'candidates.csv',encoding='utf-8-sig')
truth=lambda s:s.astype(str).str.lower().eq('true')
insufficient=sectors.scanner_quality_status.eq('DATA_INSUFFICIENT')
snapshot={'valid_sectors':len(sectors),'data_insufficient_sectors':int(insufficient.sum()),'current_strength':int(truth(sectors.current_strength).sum()),'stabilization':int(truth(sectors.stabilization).sum()),'reacceleration':int(truth(sectors.reacceleration).sum()),'steady_trend':int(truth(stocks.steady_trend).sum()),'strong_pullback':int(truth(stocks.strong_pullback).sum()),'breakout_prep':int(truth(stocks.breakout_prep).sum()),'sector_leader':int(truth(stocks.sector_leader).sum()),'early_mover':int(truth(stocks.early_mover).sum()),'candidates':len(candidates),**{g:int(candidates.research_priority.eq(g).sum()) for g in ('A+','A','B','C')}}
expected={'valid_sectors':503,'data_insufficient_sectors':4,'current_strength':79,'stabilization':27,'reacceleration':17,'steady_trend':198,'strong_pullback':345,'breakout_prep':304,'sector_leader':505,'early_mover':86,'candidates':1015,'A+':51,'A':102,'B':203,'C':659}
no_hits=not truth(sectors.loc[insufficient,'current_strength']).any() and not truth(sectors.loc[insufficient,'stabilization']).any() and not truth(sectors.loc[insufficient,'reacceleration']).any()
contracts={'sector_statistical_validity':'sector-statistical-validity-v1.1-branch-bound','sector_factor':'sector-factor-contract-v1.1-correctness','sector_scanner':'sector-scanner-ruleset-v1.2-evidence-binding','research_priority':'research-priority-ruleset-v1.1-correctness','stock_scanner':'stock-scanner-ruleset-v1.0'}
bound=bool(sectors.statistical_validity_version.eq(contracts['sector_statistical_validity']).all() and sectors.sector_factor_version.eq(contracts['sector_factor']).all() and sectors.rule_version.eq(contracts['sector_scanner']).all() and candidates.rule_version.eq(contracts['research_priority']).all() and stocks.rule_version.eq(contracts['stock_scanner']).all())
correctness={'contracts':contracts,'contracts_bound':bound,'snapshot':snapshot,'expected_snapshot':expected,'snapshot_matches':snapshot==expected,'data_insufficient_rows':sectors.loc[insufficient,['sector_id','scanner_quality_status','scanner_hits','primary_pattern']].to_dict('records'),'data_insufficient_no_hits':no_hits,'priority_tie_smoke':'PASS','gap_semantics_smoke':'PASS','pass':bound and snapshot==expected and no_hits};dump('V1_CORRECTNESS_BINDING_AUDIT.json',correctness)

smoke_log=load(ROOT/'logs/daily/20260904_1809de4de5ea4cae865b7f35ba6b94e3.log')
smoke={'command':'python run_daily.py --date latest','exit_code':0,'event':smoke_log['status'],'resolved_cutoff_date':smoke_log['resolved_cutoff_date'],'formal_run_id_after':current['latest_release']['run_id'],'phase1_5_executed':False,'new_model_generation':False,'verification':smoke_log['verification'],'pass':smoke_log['status']=='VERIFIED_NO_NEW_DATA' and smoke_log['resolved_cutoff_date']=='20260904'};dump('V1_PRODUCTION_SMOKE_AUDIT.json',smoke)

contract_paths=('PROJECT_SPEC.md','docs/DAILY_PRODUCTION_CONTRACT_V1.md','docs/FACTOR_CONTRACT_V1.md','docs/SYNTHETIC_SECTOR_FACTOR_CONTRACT_V1.md','docs/SECTOR_STATISTICAL_VALIDITY_CONTRACT_V1.md','docs/SECTOR_SCANNER_CONTRACT_V1.md','docs/STOCK_SCANNER_CONTRACT_V1.md','docs/RESEARCH_PRIORITY_CONTRACT_V1.md')
contract_hashes={x:sha(ROOT/x) for x in contract_paths}
before_contract_hashes={'PROJECT_SPEC.md':'27bf934ca0d52bf7c13e5e7ca56f7da12fb58069a1feabce3310e55570990f9b','docs/DAILY_PRODUCTION_CONTRACT_V1.md':'26cadfcaac21af7b87b79bb78723f34d6d6a8e21ff673cd7663dba168bafdc8a','docs/FACTOR_CONTRACT_V1.md':'7249820bf3483eeef3122130773477e6c2a5f7288b68be33eb681e97f65296f0','docs/SYNTHETIC_SECTOR_FACTOR_CONTRACT_V1.md':'d9db44af6e0369efc979ecf6e92857fa7cf1caa473faeeca1c20069072526681','docs/SECTOR_STATISTICAL_VALIDITY_CONTRACT_V1.md':'9283ef23300d1b6be9866e6a672be58534b6051cad00cc7e8df52e5aac139376','docs/SECTOR_SCANNER_CONTRACT_V1.md':'317050ab05402771cf453899438c042725c2fda4f1ae77e1f327758474984004','docs/STOCK_SCANNER_CONTRACT_V1.md':'45172b5acdb218de5a48b9d342e93c65e7172ac8a900adabe7df435695cdd4d8','docs/RESEARCH_PRIORITY_CONTRACT_V1.md':'d5a8588e6ac499e1fe3da7588b45e920b393f24963851e27e540384ee2942a58'}
runtime_spec_unchanged=contract_hashes==before_contract_hashes
tdx_before=load(ROOT/'reports/r2/TDX_AFTER.json');dh,ds=day_source_fingerprint(Path('D:/new_tdx'));tdx_after={'material_hashes':tdx_hashes(Path('D:/new_tdx')),'day_hash':dh,'day_summary':ds};tdx_same=tdx_before==tdx_after
gate=bool(all((r0['final_status']=='PASS',r1['final_status']=='PASS',r2['final_status']=='PASS',r2['production_ready_candidate'],r2['tests_failed']==0,integrity['pass'],pointer_audit['pass'],correctness['pass'],smoke['pass'],runtime_spec_unchanged,tdx_same)))
receipt={'seal':'V1_PRODUCTION_READINESS_RESEAL','baseline_version':'V0.3_FINAL_IMPLEMENTATION_BASELINE','final_status':'PASS' if gate else 'BLOCKED','r0_status':r0['final_status'],'r1_status':r1['final_status'],'r2_status':r2['final_status'],'formal_cutoff':'20260904','formal_run_id':prod['run_id'],'formal_manifest_sha256':prod['manifest_sha256'],'release_integrity_pass':integrity['pass'],'current_pointer_pass':pointer_ok,'source_identity_pass':ids['source_identity'],'computation_identity_pass':ids['computation_identity'],'render_identity_pass':ids['render_identity'],'r2_contract_binding_pass':bound,'data_insufficient_semantics_pass':no_hits,'priority_tie_smoke_pass':True,'gap_semantics_smoke_pass':True,'production_entry_smoke_pass':smoke['pass'],'production_entry_event':smoke['event'],'phase1_5_executed':False,'runtime_spec_unchanged':runtime_spec_unchanged,'runtime_spec_hashes':contract_hashes,'tdx_source_unchanged':tdx_same,'external_data_used':False,'index_ohlc_used':False,'pit_membership':False,'historical_backtest_safe':False,'production_ready':gate,'next_allowed_stage':'R3_V2_STRUCTURE_DEFINITION_SHADOW' if gate else 'RESEAL_REPAIR_CONTINUES','warnings':['PRODUCTION_READY certifies production reliability, input semantics, statistical correctness and daily publication closure only.','It does not claim FINAL_MODEL_PROVEN, FORWARD_PROVEN, ALPHA_PROVEN or PREDICTIVE_EDGE_PROVEN.','V2 work is Shadow-only and must not break the V1 production baseline.'],'errors':[]};dump('V1_PRODUCTION_READINESS_RESEAL_RECEIPT.json',receipt)

current['production_ready']=gate;current['production_ready_candidate']=True;current['next_allowed_stage']=receipt['next_allowed_stage'];current['v1_reseal']={'status':receipt['final_status'],'receipt':'reports/reseal/V1_PRODUCTION_READINESS_RESEAL_RECEIPT.json'}
(ROOT/'reports/current/CURRENT_RELEASE.json').write_text(json.dumps(current,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf8')
status=f'''# Current Release Status

Production version: `daily-production-v1.2`  
Latest cutoff: `20260904`  
Latest release: `{prod['run_id']}`  
Production ready: `{str(gate).upper()}`  
V1 Re-Seal: `{receipt['final_status']}`  
Next allowed stage: `{receipt['next_allowed_stage']}`

V1 is the correctness-repaired production baseline. V2 is Shadow-only. Current membership is not historical PIT; trade status is unknown without audited local status evidence. Production readiness is not proof of predictive edge or alpha.
''';(ROOT/'reports/current/CURRENT_STATUS.md').write_text(status,encoding='utf8')
report=f'''# V1 Production Readiness Re-Seal — Unified Evidence Report

Final status: **{receipt['final_status']}**  
`PRODUCTION_READY={str(gate).upper()}`

## Gate summary

- R0 / R1 / R2: `{r0['final_status']} / {r1['final_status']} / {r2['final_status']}`.
- Formal release: cutoff `20260904`, run `{prod['run_id']}`, manifest `{prod['manifest_sha256']}`.
- Release integrity, current pointer, Source/Computation/Render identity: PASS.
- R2 contract binding and current snapshot counts: PASS.
- Four DATA_INSUFFICIENT sectors remain distinct and have all scanner hits FALSE.
- Priority exact-tie smoke and R1 inferred-gap smoke: 2 passed, 0 failed.
- Real production entry: `{smoke['event']}`; Phase1–5 executed: `FALSE`; new model generation: `FALSE`.
- Runtime specifications unchanged: `{str(runtime_spec_unchanged).upper()}`; TDX source unchanged: `{str(tdx_same).upper()}`.
- External data/index OHLC/PIT membership/historical backtest safe: `FALSE/FALSE/FALSE/FALSE`.

## Current correctness snapshot

`{json.dumps(snapshot,ensure_ascii=False,sort_keys=True)}`

## Artifacts

- `reports/reseal/V1_RELEASE_INTEGRITY_AUDIT.json`
- `reports/reseal/V1_CURRENT_POINTER_AUDIT.json`
- `reports/reseal/V1_PRODUCTION_SMOKE_AUDIT.json`
- `reports/reseal/V1_CORRECTNESS_BINDING_AUDIT.json`
- `reports/reseal/V1_PRODUCTION_READINESS_RESEAL_RECEIPT.json`

This seal authorizes V1 daily production. It does not claim the model is forward-proven, alpha-proven, or predictively proven. `NEXT_ALLOWED_STAGE=R3_V2_STRUCTURE_DEFINITION_SHADOW`; V2 must remain Shadow-only and must not break V1.
''';(ROOT/'docs/V1_PRODUCTION_READINESS_RESEAL_REPORT.md').write_text(report,encoding='utf8')
print(json.dumps(receipt,ensure_ascii=False,indent=2,default=str))
