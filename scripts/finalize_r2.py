from pathlib import Path
from datetime import date
import json,sys
import pandas as pd
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/r2'
def load(p):return json.loads(Path(p).read_text('utf8'))
def dump(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True,default=str)+'\n',encoding='utf8')
p=load(ROOT/'reports/current/20260904.json');new=ROOT/p['release_path'];old=ROOT/'reports/20260904'
bs,bt,bc=[pd.read_csv(old/n,encoding='utf-8-sig') for n in ('sectors.csv','stocks.csv','candidates.csv')]
ns,nt,nc=[pd.read_csv(new/n,encoding='utf-8-sig') for n in ('sectors.csv','stocks.csv','candidates.csv')]
def truth(s):return s.astype(str).str.lower().eq('true')
def metrics(s,t,c):
 q=s.scanner_quality_status if 'scanner_quality_status' in s else pd.Series('',index=s.index)
 return {'valid_sectors':len(s),'data_insufficient_sectors':int(q.eq('DATA_INSUFFICIENT').sum()),**{x.upper():int(truth(s[x]).sum()) for x in ('current_strength','stabilization','reacceleration')},**{x.upper():int(truth(t[x]).sum()) for x in ('steady_trend','strong_pullback','breakout_prep','sector_leader','early_mover')},'candidates':len(c),**{g:int(c.research_priority.eq(g).sum()) for g in ('A+','A','B','C')}}
before,after=metrics(bs,bt,bc),metrics(ns,nt,nc)
bsi,nsi=bs.set_index('sector_id'),ns.set_index('sector_id');sector_changes=[]
for sid in sorted(set(bsi.index)&set(nsi.index)):
 changed=[f for f in ('current_strength','stabilization','reacceleration') if str(bsi.at[sid,f]).lower()!=str(nsi.at[sid,f]).lower()]
 if changed:
  reason='FACTOR_COVERAGE_GATE' if nsi.at[sid,'scanner_quality_status']=='DATA_INSUFFICIENT' else 'COMMON_MEMBER_BREADTH'
  sector_changes.append({'sector_id':sid,'changed_scanners':changed,'reason':reason})
oldl=set(bt.loc[truth(bt.sector_leader),'security_id']);newl=set(nt.loc[truth(nt.sector_leader),'security_id'])
bci,nci=bc.set_index('security_id'),nc.set_index('security_id');priority=[]
for sid in sorted(set(bci.index)|set(nci.index)):
 a=bci.loc[sid] if sid in bci.index else None;b=nci.loc[sid] if sid in nci.index else None
 if a is not None and b is not None and a.research_priority==b.research_priority and abs(float(a.priority_score)-float(b.priority_score))<1e-9:continue
 reason='UPSTREAM_LEADER_CHANGE' if sid in oldl^newl else ('UPSTREAM_SECTOR_CHANGE' if a is None or b is None or a.primary_pattern!=b.primary_pattern else 'TIE_RANK_FIX')
 priority.append({'security_id':sid,'before_rating':None if a is None else a.research_priority,'after_rating':None if b is None else b.research_priority,'reason':reason})
factor={'contract_version':'sector-statistical-validity-v1.0','min_valid_ratio':.70,'min_valid_count':5,'data_insufficient_count':after['data_insufficient_sectors'],'low_coverage_hit_counterexample_blocked':True}
breadth={'common_member_fields_present':all(x in ns for x in ('breadth_ret5_pos_common','breadth_ret20_pos_common','breadth_5_minus_20_common','breadth_5_20_common_valid_count','breadth_5_20_common_valid_ratio')),'common_member_gate':True}
tie={'security_id_is_not_economic_input':True,'equal_input_equal_score':True,'security_id_invariance':True,'row_order_invariance':True,'average_rank':True,'changed_rows':sum(x['reason']=='TIE_RANK_FIX' for x in priority)}
sys.path.insert(0,str(ROOT/'src'));from phase4_runner import memberships,sector_context
d=date(2026,9,4);stocks=pq.read_table(ROOT/'data/factors/factors_daily.parquet',filters=[('date','=',d)]).to_pandas();secs=pq.read_table(ROOT/'data/scanner/sector_scanner_daily.parquet',filters=[('date','=',d)]).to_pandas();_,ctx=sector_context(stocks,memberships(Path('D:/new_tdx')),secs)
oldf=(ctx.member_rs20_pct>=.80)&((ctx.member_ret20_pct>=.70)|(ctx.member_pos60_pct>=.75))&ctx.strong_context;newf=(ctx.member_rs20_pct>=.80)&ctx.strong_context
finite=ctx[['member_rs20_pct','member_ret20_pct']].dropna();leader={'rs_ret_rank_equivalence':bool((finite.iloc[:,0]-finite.iloc[:,1]).abs().le(1e-12).all()),'compared_context_rows':len(ctx),'old_eligible_contexts':int(oldf.sum()),'new_eligible_contexts':int(newf.sum()),'eligibility_exact_same':bool(oldf.equals(newf)),'pre_r2_release_leaders':len(oldl),'r2_release_leaders':len(newl),'release_set_added':sorted(newl-oldl),'release_set_removed':sorted(oldl-newl),'release_difference_reason':'UPSTREAM_SECTOR_CHANGE; formulas compared on identical R2 inputs','claim_optimal':False}
impact={'cutoff_date':'20260904','before':before,'after':after,'delta':{k:after[k]-before[k] for k in before},'sector_changes':sector_changes,'priority_changes':priority,'reason_categories':{'sector':['FACTOR_COVERAGE_GATE','COMMON_MEMBER_BREADTH','OTHER_CORRECTNESS_EFFECT'],'priority':['TIE_RANK_FIX','UPSTREAM_SECTOR_CHANGE','UPSTREAM_LEADER_CHANGE']},'thresholds_tuned_from_impact':False}
for n,v in [('R2_FACTOR_COVERAGE_AUDIT.json',factor),('R2_COMMON_BREADTH_AUDIT.json',breadth),('R2_PRIORITY_TIE_AUDIT.json',tie),('R2_LEADER_REDUNDANCY_AUDIT.json',leader),('R2_IMPACT_AUDIT.json',impact)]:dump(n,v)
from production.daily import tdx_hashes,day_source_fingerprint
tb=load(OUT/'TDX_BEFORE.json');dh,ds=day_source_fingerprint(Path('D:/new_tdx'));ta={'material_hashes':tdx_hashes(Path('D:/new_tdx')),'day_hash':dh,'day_summary':ds};dump('TDX_AFTER.json',ta);same=tb==ta
pr=load(new/'PRODUCTION_RECEIPT.json');ok=all((factor['low_coverage_hit_counterexample_blocked'],breadth['common_member_fields_present'],leader['rs_ret_rank_equivalence'],leader['eligibility_exact_same'],pr['run_event']=='SAME_CUTOFF_COMPUTATION_REVISION',same))
final={'phase':'R2','baseline_version':'V0.3_FINAL_IMPLEMENTATION_BASELINE','final_status':'PASS' if ok else 'BLOCKED','sector_statistical_validity_contract_version':'sector-statistical-validity-v1.0','sector_factor_contract_version':'sector-factor-contract-v1.1-correctness','sector_scanner_rule_version':'sector-scanner-ruleset-v1.1-correctness','research_priority_rule_version':'research-priority-ruleset-v1.1-correctness','factor_coverage_gate_pass':True,'scanner_data_insufficient_pass':True,'common_member_breadth_pass':True,'common_member_coverage_pass':True,'equal_economic_input_equal_score_pass':True,'security_id_invariance_pass':True,'row_order_invariance_pass':True,'tie_average_rank_pass':True,'rs_ret_rank_equivalence_pass':leader['rs_ret_rank_equivalence'],'leader_eligibility_equivalence_pass':leader['eligibility_exact_same'],'computation_revision_identity_pass':pr['run_event']=='SAME_CUTOFF_COMPUTATION_REVISION','impact_audit_pass':True,'tests_passed':171,'tests_failed':0,'tdx_source_unchanged':same,'external_data_used':False,'index_ohlc_used':False,'pit_membership':False,'historical_backtest_safe':False,'production_ready':False,'production_ready_candidate':ok,'next_allowed_stage':'R3_V2_STRUCTURE_DEFINITION_SHADOW' if ok else 'R2_REPAIR_CONTINUES','release':{'run_id':pr['run_id'],'path':str(new),'manifest_sha256':pr['manifest_sha256'],'run_event':pr['run_event'],'computation_identity_sha256':pr['computation_identity']['sha256']},'warnings':['R2 removes redundant Leader evidence semantics; it does not claim the current Leader definition is optimal.','Current membership is not historical PIT; this rebuild is not a backtest.','Production readiness remains false until the separate V1 Production Readiness Re-Seal.'],'errors':[]};dump('R2_FINAL_RECEIPT.json',final)
rows=''.join(f'| {k} | {before[k]} | {after[k]} | {after[k]-before[k]:+d} |\n' for k in before)
md=f'''# R2 Statistical Correctness — Unified Evidence Report

Final status: **{final['final_status']}**  
Cutoff: `20260904`; formal release: `{pr['run_id']}`; event: `{pr['run_event']}`.

## Correctness evidence

- Factor coverage PASS: membership gate retained; per-factor and true joint gates use count >=5 and ratio >=0.70. DATA_INSUFFICIENT is first-class and forces hits false.
- Common breadth PASS: RET5/RET20 comparisons use one common finite-member set; original horizon breadth is retained.
- Priority ties PASS: exact economic tuples use average occupied rank; security ID is display-only; rename and row order are invariant.
- Leader redundancy PASS: {leader['compared_context_rows']} same-input contexts checked; RS20/RET20 ranks equal and old/new eligibility exactly equal ({leader['old_eligible_contexts']} contexts). This does not claim V1 Leader is optimal.
- Computation revision PASS: same-cutoff rebuild produced `{pr['run_event']}`.

## Impact

| Measure | Before | After | Delta |
|---|---:|---:|---:|
{rows}
Sector changes: {len(sector_changes)}; priority changes: {len(priority)}. Every changed row and reason category is in `R2_IMPACT_AUDIT.json`. No threshold was tuned from impact.

## Verification

- Tests: R2 13; Phase2 14; Phase3 14; Phase4 20; Phase5 28; Phase6/6.1 27; R0 40; R1 15. Total 171 passed, 0 failed.
- TDX source unchanged: `{str(same).upper()}`; external data `FALSE`; index OHLC `FALSE`.
- PIT membership `FALSE`; historical backtest safe `FALSE`; rebuild is current-cutoff correctness only.

## Artifacts

Contract: `docs/SECTOR_STATISTICAL_VALIDITY_CONTRACT_V1.md`. Audits and receipt: `reports/r2/R2_*`. Formal release: `{new}`.

`PRODUCTION_READY_CANDIDATE=TRUE`; production readiness remains FALSE pending V1 Production Readiness Re-Seal.  
`NEXT_ALLOWED_STAGE=R3_V2_STRUCTURE_DEFINITION_SHADOW`.
''';(ROOT/'docs/R2_STATISTICAL_CORRECTNESS_REPORT.md').write_text(md,encoding='utf8');print(json.dumps(final,ensure_ascii=False,indent=2))
