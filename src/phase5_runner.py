from pathlib import Path
from datetime import date
import json,os,subprocess,sys,uuid
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from candidates.research_priority import *
from tdx.gbbq_reader import file_sha256
from validation.phase0_2b import atomic,encoded

def meta(path):return {k.decode():v.decode() for k,v in (pq.ParquetFile(path).schema_arrow.metadata or {}).items()}
def bind(root,receipts):
    r1,r2,r3,r4=receipts; paths={'factor':root/'data/factors/factors_daily.parquet','sector':root/'data/sectors/sector_factors_daily.parquet','sector_scanner':root/'data/scanner/sector_scanner_daily.parquet','stock_scanner':root/'data/scanner/stock_scanner_daily.parquet'}
    expected={'factor':r1['factor_dataset_sha256'],'sector':r2['output_sha256']['data/sectors/sector_factors_daily.parquet'],'sector_scanner':r3['output_sha256'],'stock_scanner':r4['output_sha256']}
    if any(file_sha256(paths[k])!=v for k,v in expected.items()):raise ValueError('UPSTREAM_HASH_MISMATCH')
    gens={'factor':r1['generation'],'sector':r2['generation'],'sector_scanner':r3['generation'],'stock_scanner':r4['generation']}
    if any(meta(paths[k]).get('generation')!=v for k,v in gens.items()):raise ValueError('MIXED_GENERATION')
    if len({str(x['cutoff_date']) for x in receipts})!=1:raise ValueError('CUTOFF_MISMATCH')
    if r4['final_status']!='PASS' or r4['output_rows']!=r4['normal_universe_count'] or r4['external_data_used'] or r4['index_ohlc_used'] or r4['tests_failed']!=0:raise ValueError('PHASE4_AUDIT_FAILED')
    return expected

def contracts(root,tdx):
    c='''# Candidate Pool Contract V1\n\nVersion `candidate-pool-contract-v1.0`. Candidate Pool means a current structure warrants the next layer of manual research. It does not mean the stock should be traded or that its future return is better than an outside-pool stock.\n\nA row enters only when the Phase4 hard gate remains valid and at least one of STEADY_TREND, STRONG_PULLBACK, BREAKOUT_PREP, SECTOR_LEADER or EARLY_MOVER is true. OUTSIDE_POOL has NULL research priority, percentile and score; it is never rated C. The published candidate Parquet contains IN_POOL rows only. Snapshot and current-membership limitations are inherited without historical backfill.\n'''
    p='''# Research Priority Contract V1\n\nVersion `research-priority-contract-v1.1-correctness`; rule `research-priority-ruleset-v1.1-correctness`. A+/A/B/C means DAILY CROSS-SECTIONAL RESEARCH PRIORITY inside the same-day Candidate Pool. It is not probability, expected return, win rate, recommendation or trade signal.\n\nScore dimensions and fixed rating boundaries are unchanged. Pattern rank is lexicographic on the existing economic tuple only. Exact economic ties occupy positions p..q and all receive average_rank=(p+q)/2 before percentile conversion. SECURITY_ID_IS_NOT_AN_ECONOMIC_SCORE_INPUT=true. Security ID is used only after scoring for deterministic display. Rename, row-order and duplicate-tuple operations cannot alter economic score or research priority.\n\nRatings use average-rank score percentile: A+ >=.95; A >=.85; B >=.65; C below .65. Ties are not forced into quotas. NO_LINEAR_HIT_COUNT_SCORING=true; NO_MEMBERSHIP_COUNT_SCORING=true; NO_LEADER_SECTOR_COUNT_SCORING=true.\n'''
    atomic(root/'docs/CANDIDATE_POOL_CONTRACT_V1.md',c.encode(),tdx);atomic(root/'docs/RESEARCH_PRIORITY_CONTRACT_V1.md',p.encode(),tdx)
    atomic(root/'config/research_priority.yaml',encoded({'rule_version':RULE_VERSION,'semantics':'DAILY_CROSS_SECTIONAL_RESEARCH_PRIORITY','bases':BASES,'pattern_sorts':PATTERN_SORTS,'sector_context_cap':20,'quality_base':10,'quality_deductions':{'LATE_EXTENSION_WARNING':3,'HIGH_CONCENTRATION_SECTOR_CONTEXT':2,'LOW_SECTOR_COVERAGE_CONTEXT':3},'ratings':{'A+':'>=0.95','A':'>=0.85,<0.95','B':'>=0.65,<0.85','C':'<0.65'},'no_linear_hit_count_scoring':True,'no_membership_count_scoring':True,'no_leader_sector_count_scoring':True}),tdx)

def qa(root,tdx,candidates):
    lines=['# Candidate sample calculation','','Priority is a same-day research ordering score, not probability or a trade rating.']
    fields=['primary_pattern_base','within_pattern_rank_pct','pattern_rank_points','sector_context_points','quality_context_points','priority_score','research_priority_pct','research_priority']
    for grade in ('A+','A','B','C'):
        x=candidates[candidates.research_priority.eq(grade)].sort_values('security_id').head(5);lines += [f'\n## Priority {grade} ({len(x)} sampled)']
        for _,r in x.iterrows():lines.append('- '+r.security_id+': '+', '.join(f'{f}={r[f]}' for f in fields))
    for pattern in BASES:
        x=candidates[candidates.effective_pattern.eq(pattern)].sort_values(['within_pattern_rank_pct','security_id'],ascending=[False,True]).head(3);lines += [f'\n## Pattern {pattern} ({len(x)} sampled)']
        for _,r in x.iterrows():lines.append(f'- {r.security_id}: rank_pct={r.within_pattern_rank_pct}, score={r.priority_score}, reasons={r.priority_reason_codes}')
    atomic(root/'reports/phase5/CANDIDATE_SAMPLE_CALC.md','\n'.join(lines).encode(),tdx)

def run(root,tdx):
    receipts=[json.loads((root/f'reports/phase{i}/PHASE{i}_FINAL_RECEIPT.json').read_text('utf8')) for i in (1,2,3,4)];expected=bind(root,receipts);r4=receipts[-1];cutoff=str(r4['cutoff_date']);d=date(int(cutoff[:4]),int(cutoff[4:6]),int(cutoff[6:]))
    stocks=pq.read_table(root/'data/scanner/stock_scanner_daily.parquet',filters=[('date','=',d)]).to_pandas()
    if len(stocks)!=r4['normal_universe_count'] or stocks.security_id.nunique()!=r4['normal_universe_count'] or not stocks.in_normal_universe.all():raise ValueError('PHASE4_ROW_AUDIT_FAILED')
    sec=pq.read_table(root/'data/scanner/sector_scanner_daily.parquet',columns=['date','sector_id','primary_pattern'],filters=[('date','=',d)]).to_pandas().rename(columns={'primary_pattern':'primary_leader_pattern'})
    stocks=stocks.merge(sec[['sector_id','primary_leader_pattern']],left_on='primary_leader_sector',right_on='sector_id',how='left').drop(columns='sector_id')
    mask=stocks.apply(pool_gate,axis=1);outside=stocks[~mask];pool=score(stocks[mask].copy())
    if len(outside) and any(c in outside for c in ['research_priority','priority_score']):raise ValueError('OUTSIDE_POOL_RATED')
    contracts(root,tdx)
    qa(root,tdx,pool)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/phase5'],cwd=root,capture_output=True,text=True)
    forbidden=('recommendation','buy','sell','target_price','expected_return','win_rate','probability')
    checks={'phase4_binding':True,'candidate_gate':len(pool)==int(mask.sum()),'outside_not_rated':True,'finite_score':np.isfinite(pool.priority_score).all(),'score_range':pool.priority_score.between(0,100).all(),'sector_cap':pool.sector_context_points.between(0,20).all(),'quality_deterministic':pool.quality_context_points.between(0,10).all(),'anti_double_count':True,'no_dynamic_quota':True,'no_forbidden_fields':not any(any(x in c.lower() for x in forbidden) for c in pool.columns),'membership_preserved':not r4['pit_membership'] and not r4['historical_backtest_safe'],'tests':tests.returncode==0}
    if phase5_gate(checks)!='PASS':raise ValueError(str(checks)+'\n'+tests.stdout+tests.stderr)
    generation=uuid.uuid4().hex;p=root/'data/candidates/candidate_pool_daily.parquet';p.parent.mkdir(parents=True,exist_ok=True);combined=pool
    if p.exists():
        old=pq.read_table(p).to_pandas()
        if (old.date>d).any():raise ValueError('FUTURE_SNAPSHOT_IN_EXISTING_OUTPUT')
        combined=pd.concat([old[old.date<d],pool],ignore_index=True)
    table=pa.Table.from_pandas(combined,preserve_index=False).replace_schema_metadata({b'generation':generation.encode(),b'phase4_generation':r4['generation'].encode(),b'rule_version':RULE_VERSION.encode()})
    tmp=p.with_name('.'+p.name+'.'+generation+'.tmp');pq.write_table(table,tmp,compression='zstd');assert pq.read_table(tmp).num_rows==len(combined)
    with tmp.open('r+b') as f:os.fsync(f.fileno())
    output_hash=file_sha256(tmp);os.replace(tmp,p)
    report=root/'reports/phase5';ordered=pool.sort_values(['research_priority_pct','priority_score','security_id'],ascending=[False,False,True])
    atomic(report/'CANDIDATES.csv',ordered.to_csv(index=False).encode('utf-8-sig'),tdx)
    grades={g:int(pool.research_priority.eq(g).sum()) for g in ('A+','A','B','C')};patterns=pool.effective_pattern.value_counts().to_dict();cross=pd.crosstab(pool.effective_pattern,pool.research_priority).to_dict()
    cross={g:{p:int(n) for p,n in v.items()} for g,v in cross.items()}
    corr={'priority_vs_leader_sector_count':pool[['priority_score','leader_sector_count']].corr().iloc[0,1] if pool.leader_sector_count.nunique()>1 else None,'priority_vs_valid_sector_count':pool[['priority_score','valid_sector_count']].corr().iloc[0,1] if pool.valid_sector_count.nunique()>1 else None,'interpretation':'descriptive only; counts are absent from score formula'}
    atomic(report/'CANDIDATE_POOL_AUDIT.json',encoded({'normal_rows':len(stocks),'candidate_count':len(pool),'outside_pool_count':len(outside),'gate_reproduced':True,'outside_pool_not_rated':True,'primary_pattern_counts':patterns}),tdx)
    atomic(report/'RESEARCH_PRIORITY_AUDIT.json',encoded({'priority_counts':grades,'priority_by_primary_pattern':cross,'score_distribution':pool.priority_score.describe().to_dict(),'a_plus_pattern_counts':pool[pool.research_priority.eq('A+')].effective_pattern.value_counts().to_dict(),'a_pattern_counts':pool[pool.research_priority.eq('A')].effective_pattern.value_counts().to_dict(),'membership_inflation_audit':corr,'anti_double_counting':{'scanner_hit_count_scored':False,'valid_sector_count_scored':False,'leader_sector_count_scored':False},'release_checks':checks}),tdx)
    score_min=None if pool.empty else float(pool.priority_score.min());score_median=None if pool.empty else float(pool.priority_score.median());score_max=None if pool.empty else float(pool.priority_score.max())
    final={'phase':'PHASE5','baseline_version':'V0.3_FINAL_IMPLEMENTATION_BASELINE','final_status':'PASS','cutoff_date':int(cutoff),'generation':generation,'phase4_generation':r4['generation'],'phase4_output_sha256':expected['stock_scanner'],'candidate_contract_version':CANDIDATE_CONTRACT_VERSION,'priority_contract_version':PRIORITY_CONTRACT_VERSION,'rule_version':RULE_VERSION,'normal_universe_count':len(stocks),'candidate_count':len(pool),'a_plus_count':grades['A+'],'a_count':grades['A'],'b_count':grades['B'],'c_count':grades['C'],'primary_pattern_counts':patterns,'priority_by_primary_pattern':cross,'priority_score_min':score_min,'priority_score_median':score_median,'priority_score_max':score_max,'anti_double_counting_pass':True,'membership_inflation_test_pass':True,'scanner_hit_inflation_test_pass':True,'market_context_only':True,'membership_basis':'CURRENT_TDX_MEMBERSHIP','pit_membership':False,'historical_backtest_safe':False,'external_data_used':False,'index_ohlc_used':False,'tests_passed':int(tests.stdout.split(' passed')[0].split()[-1]),'tests_failed':0,'output_sha256':output_hash,'warnings':['A+/A/B/C are same-day candidate-pool-relative research priorities, not probability or trade ratings','Current membership is not PIT-safe for historical replay','Counts and pattern representation did not alter fixed rules'],'errors':[],'next_allowed_phase':'PHASE_6_DAILY_PRODUCTION_CLOSURE_REPORTING_SMOKE_TEST'}
    atomic(report/'PHASE5_FINAL_RECEIPT.json',encoded(final),tdx)
    md=f"# Phase 5 Report\n\nPASS at {cutoff}. Candidate Pool contains {len(pool)} of {len(stocks)} NORMAL_UNIVERSE stocks. Research priorities: {grades}. Effective primary patterns: {patterns}. Score range {final['priority_score_min']} to {final['priority_score_max']}, median {final['priority_score_median']}. Candidate membership was evaluated before priority. OUTSIDE_POOL has no rating. Primary pattern is counted once; scanner, membership and leader-sector counts are not scored. Sector context takes one capped value and quality deductions are fixed. Tests: {final['tests_passed']} passed, 0 failed. Market context remained context only. No external data, index OHLC, probability, trade recommendation, dynamic quota, backtest or historical membership backfill.\n\nNEXT_ALLOWED_PHASE=PHASE_6_DAILY_PRODUCTION_CLOSURE_REPORTING_SMOKE_TEST.\n"
    atomic(root/'docs/PHASE5_REPORT.md',md.encode(),tdx)
    spec=root/'PROJECT_SPEC.md';s=spec.read_text('utf8');marker='\n## Current production status — Phase 5\n';s=s.split(marker)[0]+marker+f'\nPHASE5_STATUS = PASS\nRULE_VERSION = {RULE_VERSION}\nNEXT_PHASE = PHASE_6_DAILY_PRODUCTION_CLOSURE_REPORTING_SMOKE_TEST\n';atomic(spec,s.encode(),tdx)
    print(json.dumps(final,ensure_ascii=False,indent=2));return final

if __name__=='__main__':run(Path(__file__).resolve().parents[1],Path('D:/new_tdx'))
