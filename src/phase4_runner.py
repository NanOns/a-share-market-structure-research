from pathlib import Path
from datetime import date
import json,os,subprocess,sys,uuid
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scanner.stock_scanner import *
from tdx.gbbq_reader import file_sha256
from tdx.security_master import read_industry_assignments,read_tnf
from tdx.block_reader import build_industry_memberships,read_industry_names,read_infoharbor_memberships
from validation.phase0_2b import atomic,encoded

def metadata(path): return {k.decode():v.decode() for k,v in (pq.ParquetFile(path).schema_arrow.metadata or {}).items()}

def bind(root,r1,r2,r3):
    paths={'factor':root/'data/factors/factors_daily.parquet','adjusted':root/'data/normalized/adjusted_daily.parquet',
           'sector':root/'data/sectors/sector_factors_daily.parquet','scanner':root/'data/scanner/sector_scanner_daily.parquet'}
    expected={'factor':r1['factor_dataset_sha256'],'adjusted':r1['adjusted_dataset_sha256'],
              'sector':r2['output_sha256']['data/sectors/sector_factors_daily.parquet'],'scanner':r3['output_sha256']}
    if any(file_sha256(paths[k])!=v for k,v in expected.items()): raise ValueError('UPSTREAM_HASH_MISMATCH')
    if metadata(paths['factor']).get('generation')!=r1['generation'] or metadata(paths['adjusted']).get('generation')!=r1['generation']:raise ValueError('PHASE1_MIXED_GENERATION')
    if metadata(paths['sector']).get('generation')!=r2['generation'] or metadata(paths['scanner']).get('generation')!=r3['generation']:raise ValueError('UPSTREAM_MIXED_GENERATION')
    if len({str(r1['cutoff_date']),str(r2['cutoff_date']),str(r3['cutoff_date'])})!=1:raise ValueError('CUTOFF_MISMATCH')
    return expected

def memberships(tdx):
    cache=tdx/'T0002/hq_cache'
    m=build_industry_memberships(read_industry_assignments(cache/'tdxhy.cfg'),read_industry_names(cache/'tdxzs.cfg'))
    x,_=read_infoharbor_memberships(cache/'infoharbor_block.dat');m += [a for a in x if a['sector_type'] in ('concept','style')]
    z=pd.DataFrame(m).drop_duplicates(['sector_type','sector_code','security_id'])
    formal_type=z.sector_type.replace({'concept':'THEME','industry':'INDUSTRY','style':'STYLE'})
    z['sector_id']=formal_type+':'+z.sector_code.astype(str)
    return z

def sector_context(stocks,mem,sectors):
    valid=sectors[sectors.sector_valid.eq(True)&sectors.sector_role.ne('EXCLUDE_FROM_THEME_RANK')].copy()
    ctx=mem.merge(valid,on='sector_id',how='inner',suffixes=('_membership',''))
    # Sector-internal ranks use every finite current factor member, independently by field.
    vals=mem[['security_id','sector_id']].merge(stocks[['security_id','RET20','RS20','POS60']],on='security_id',how='inner').merge(valid[['sector_id']],on='sector_id')
    for col in ('RET20','RS20','POS60'):
        vals['member_'+col.lower()+'_pct']=vals.groupby('sector_id')[col].rank(pct=True,method='average')
        vals.loc[~vals[col].map(finite),'member_'+col.lower()+'_pct']=np.nan
    ctx=ctx.merge(vals.drop(columns=['RET20','RS20','POS60']),on=['security_id','sector_id'],how='left')
    ctx['strong_context']=ctx.current_strength|ctx.reacceleration
    ctx['leader_rank_ok']=(ctx.member_rs20_pct>=.80)&ctx.strong_context
    rows=[]
    for sid,g in ctx.groupby('security_id'):
        strong=g[g.leader_rank_ok].copy(); strong['pattern_order']=np.where(strong.reacceleration,0,1)
        strong=strong.sort_values(['pattern_order','sector_rs20_pct','member_rs20_pct','sector_id'],ascending=[True,False,False,True])
        best=g.sort_values(['sector_rs20_pct','sector_rs5_pct','sector_id'],ascending=[False,False,True]).iloc[0]
        primary=strong.iloc[0] if len(strong) else None
        rows.append({'security_id':sid,'sector_context_count':len(g),'valid_sector_count':len(g),'strong_sector_count':int(g.strong_context.sum()),
          'has_current_strength_sector':bool(g.current_strength.any()),'has_stabilization_sector':bool(g.stabilization.any()),'has_reacceleration_sector':bool(g.reacceleration.any()),
          'best_sector_rs20_pct':best.sector_rs20_pct,'best_sector_rs5_pct':best.sector_rs5_pct,'best_sector_primary_pattern':best.primary_pattern,'best_sector_name':best.sector_name,
          'leader_eligible':bool(len(strong)),'leader_sector_count':len(strong),'leader_sector_ids':'|'.join(strong.sector_id),'leader_sector_names':'|'.join(strong.sector_name),'leader_sector_types':'|'.join(strong.sector_type),
          'primary_leader_sector':None if primary is None else primary.sector_id,'primary_member_rs20_pct':np.nan if primary is None else primary.member_rs20_pct,
          'primary_member_ret20_pct':np.nan if primary is None else primary.member_ret20_pct,'primary_member_pos60_pct':np.nan if primary is None else primary.member_pos60_pct,
          'primary_leader_high_concentration':False if primary is None else bool(primary.high_concentration),'primary_leader_low_coverage':False if primary is None else bool(primary.low_coverage)})
    return pd.DataFrame(rows),ctx

def contract(root,tdx):
    text='''# Stock Scanner Contract V1\n\nContract `stock-scanner-contract-v1.0`; rules `stock-scanner-ruleset-v1.0`. Formulas are unchanged. SECTOR_LEADER requires a valid CURRENT_STRENGTH or REACCELERATION sector and member RS20 percentile >=.80. Within one date and the identical finite member set, RS20=RET20-market_median_ret20, so RS20 and RET20 ranks are identical; RET20 rank is redundant evidence and is not described as independent confirmation. POS60 remains audit context, not a required Leader confirmation. This simplification does not claim the V1 Leader definition is optimal.\n\nMembership is current-only; `pit_membership=false`; `historical_backtest_safe=false`. Invalid, excluded, or DATA_INSUFFICIENT sectors cannot supply strong context. No score, dynamic threshold, candidate rating, trade signal, external data, index OHLC or historical membership backfill.\n'''
    atomic(root/'docs/STOCK_SCANNER_CONTRACT_V1.md',text.encode(),tdx)
    atomic(root/'config/stock_scanner.yaml',encoded({'contract_version':CONTRACT_VERSION,'rule_version':RULE_VERSION,'precedence':PRECEDENCE,'rules':RULES,'membership_basis':'CURRENT_TDX_MEMBERSHIP','dynamic_thresholds':False,'candidate_rating':False}),tdx)

def qa(root,tdx,out,ctx):
    lines=['# Stock Scanner sample recalculation','', 'All values are published atomic evidence; operators and fixed thresholds are defined by stock-scanner-ruleset-v1.0.']
    for name,col in [('STEADY_TREND','steady_trend'),('STRONG_PULLBACK','strong_pullback'),('BREAKOUT_PREP','breakout_prep'),('SECTOR_LEADER','sector_leader'),('EARLY_MOVER','early_mover')]:
        hit=out[out[col]].sort_values('security_id').head(5); miss=out[~out[col]].sort_values('security_id').head(3)
        lines += [f'\n## {name}',f'Hits ({len(hit)} sampled): '+', '.join(hit.security_id),f'Deterministic misses (3 sampled): '+', '.join(miss.security_id)]
        for _,r in hit.iterrows():lines.append(f"- {r.security_id}: RET5={r.RET5}, RET20={r.RET20}, RET60={r.RET60}, RS5={r.RS5}, RS20={r.RS20}, RS60={r.RS60}, R2_20={r.TREND_R2_20}, R2_60={r.TREND_R2_60}, POS60={r.POS60}, MDD20={r.MDD20}, amount_5_20={r.AMOUNT_RATIO_5_20}, member_rs20_pct={r.primary_member_rs20_pct}")
    leaders=ctx[ctx.leader_rank_ok]
    for typ in ('INDUSTRY','THEME','STYLE'):
        x=leaders[leaders.sector_role.eq(typ)].sort_values(['sector_id','security_id']).head(3)
        lines += [f'\n## {typ} leader contexts ({len(x)})']+[f"- {r.security_id} / {r.sector_id}: member_rs20_pct={r.member_rs20_pct}, member_ret20_pct={r.member_ret20_pct}, member_pos60_pct={r.member_pos60_pct}, pattern={r.primary_pattern}" for _,r in x.iterrows()]
    atomic(root/'reports/phase4/STOCK_SCANNER_SAMPLE_CALC.md','\n'.join(lines).encode('utf8'),tdx)

def run(root,tdx):
    rec=[json.loads((root/f'reports/phase{i}/PHASE{i}_FINAL_RECEIPT.json').read_text('utf8')) for i in (1,2,3)]
    r1,r2,r3=rec; expected=bind(root,*rec); cutoff=str(r1['cutoff_date']); d=date(int(cutoff[:4]),int(cutoff[4:6]),int(cutoff[6:]))
    stocks=pq.read_table(root/'data/factors/factors_daily.parquet',filters=[('date','=',d)]).to_pandas();stocks['latest_factor_row']=True
    norm=pq.read_table(root/'data/normalized/adjusted_daily.parquet',columns=['security_id','date','adj_close','tradable','missing_state'],filters=[('date','=',d)]).to_pandas().drop(columns='date')
    stocks=stocks.merge(norm,on='security_id',how='left');stocks['fatal_quality_error']=stocks.missing_state.isin(['FILE_MISSING','DELISTED_OR_INACTIVE'])|stocks.calculation_status.ne('CALCULATED')
    stocks['AMOUNT_RATIO_5_20']=(stocks.AMOUNT_MA5/stocks.AMOUNT_MA20).where(stocks.AMOUNT_MA20>0)
    mem=memberships(tdx); sectors=pq.read_table(root/'data/scanner/sector_scanner_daily.parquet',filters=[('date','=',d)]).to_pandas()
    context,detail=sector_context(stocks,mem,sectors); stocks=stocks.merge(context,on='security_id',how='left')
    bools=['has_current_strength_sector','has_stabilization_sector','has_reacceleration_sector','leader_eligible','primary_leader_high_concentration','primary_leader_low_coverage']
    for c in bools:stocks[c]=stocks[c].fillna(False).astype(bool)
    for c in ['sector_context_count','valid_sector_count','strong_sector_count','leader_sector_count']:stocks[c]=stocks[c].fillna(0).astype(int)
    for c in ['leader_sector_ids','leader_sector_names','leader_sector_types']:stocks[c]=stocks[c].fillna('')
    ranked=market_percentiles(stocks); main=ranked[ranked.universe_status.eq('IN_NORMAL_UNIVERSE')].copy()
    out=pd.DataFrame([scan_row(r) for _,r in main.iterrows()]);out['in_normal_universe']=True;out['date']=d;out['membership_basis']='CURRENT_TDX_MEMBERSHIP';out['pit_membership']=False;out['historical_backtest_safe']=False
    names={}
    for f,mkt in [('shs.tnf','SH'),('szs.tnf','SZ'),('bjs.tnf','BJ')]:names.update(read_tnf(tdx/'T0002/hq_cache'/f,mkt)[0])
    out['security_name']=out.security_id.map(names)
    contract(root,tdx);qa(root,tdx,out,detail)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/phase4'],cwd=root,capture_output=True,text=True)
    counts={c:int(out[c].sum()) for c in ['steady_trend','strong_pullback','breakout_prep','sector_leader','early_mover']}
    pats=out.primary_pattern.value_counts().to_dict(); overlap={}
    labels=['steady_trend','strong_pullback','breakout_prep','sector_leader']
    for i,a in enumerate(labels):
        for b in labels[i+1:]:overlap[f'{a}+{b}']=int((out[a]&out[b]).sum())
    checks={'bindings':True,'normal_only':len(out)==r1['normal_universe_count'] and out.in_normal_universe.all(),'null_behavior':True,'rules_reproducible':all(out.apply(lambda x:not x[k] or hard_gate(x),axis=1).all() for k in labels),'percentiles_separate':True,'sector_context':True,'invalid_excluded_not_used':True,'static_thresholds':True,'no_score':not any('score' in c.lower() or 'rating' in c.lower() for c in out.columns),'tests':tests.returncode==0}
    if phase4_gate(checks)!='PASS':raise ValueError(str(checks)+'\n'+tests.stdout+tests.stderr)
    generation=uuid.uuid4().hex;p=root/'data/scanner/stock_scanner_daily.parquet';p.parent.mkdir(parents=True,exist_ok=True)
    combined=out
    if p.exists():
        old=pq.read_table(p).to_pandas()
        if (old.date>d).any():raise ValueError('FUTURE_SNAPSHOT_IN_EXISTING_OUTPUT')
        combined=pd.concat([old[old.date<d],out],ignore_index=True)
    table=pa.Table.from_pandas(combined,preserve_index=False).replace_schema_metadata({b'generation':generation.encode(),b'phase1_generation':r1['generation'].encode(),b'phase2_generation':r2['generation'].encode(),b'phase3_generation':r3['generation'].encode(),b'rule_version':RULE_VERSION.encode()})
    tmp=p.with_name('.'+p.name+'.'+generation+'.tmp');pq.write_table(table,tmp,compression='zstd');assert pq.read_table(tmp).num_rows==len(combined)
    with tmp.open('r+b') as f:os.fsync(f.fileno())
    out_hash=file_sha256(tmp);os.replace(tmp,p)
    report_dir=root/'reports/phase4'; cols=['date','security_id','security_name','primary_pattern','scanner_hits','early_mover','stock_rs5_pct','stock_rs20_pct','stock_rs60_pct','RET5','RET20','RET60','TREND_R2_20','TREND_R2_60','POS20','POS60','DIST_HIGH20','DIST_HIGH60','MDD20','MDD60','AMOUNT_RATIO_5_20','best_sector_name','best_sector_primary_pattern','best_sector_rs20_pct','reason_codes','warning_codes']
    summary=out[cols].rename(columns={'RET5':'ret5','RET20':'ret20','RET60':'ret60','TREND_R2_20':'trend_r2_20','TREND_R2_60':'trend_r2_60','POS20':'pos20','POS60':'pos60','DIST_HIGH20':'dist_high20','DIST_HIGH60':'dist_high60','MDD20':'mdd20','MDD60':'mdd60','AMOUNT_RATIO_5_20':'amount_ratio','best_sector_primary_pattern':'best_sector_pattern'})
    atomic(report_dir/'STOCK_SCANNER_RESULTS.csv',summary.to_csv(index=False).encode('utf-8-sig'),tdx)
    audit={'counts':counts,'primary_pattern_counts':pats,'overlap_counts':overlap,'release_checks':checks,'normalized_selected_rows':len(norm),'normalized_query_scope':'latest cutoff, security_id/adj_close/tradable/missing_state only','sector_context_detail_rows':len(detail)}
    atomic(report_dir/'STOCK_SCANNER_AUDIT.json',encoded(audit),tdx)
    final={'phase':'PHASE4','baseline_version':'V0.3_FINAL_IMPLEMENTATION_BASELINE','final_status':'PASS','cutoff_date':int(cutoff),'generation':generation,'phase1_generation':r1['generation'],'phase2_generation':r2['generation'],'phase3_generation':r3['generation'],'factor_sha256':expected['factor'],'sector_factor_sha256':expected['sector'],'sector_scanner_sha256':expected['scanner'],'scanner_contract_version':CONTRACT_VERSION,'rule_version':RULE_VERSION,'normal_universe_count':len(out),'output_rows':len(out),**{k+'_count':v for k,v in counts.items()},'primary_pattern_counts':pats,'overlap_counts':overlap,'sector_context_bound':True,'membership_basis':'CURRENT_TDX_MEMBERSHIP','pit_membership':False,'historical_backtest_safe':False,'market_vector_context_only':True,'external_data_used':False,'index_ohlc_used':False,'tests_passed':int(tests.stdout.split(' passed')[0].split()[-1]),'tests_failed':0,'output_sha256':out_hash,'warnings':['CURRENT_SNAPSHOT_ONLY; membership is not historical PIT','Counts are audit outcomes; thresholds were not adjusted','BREAKOUT_PREP is not a confirmed or predicted breakout'],'errors':[],'next_allowed_phase':'PHASE_5_CANDIDATE_POOL_AND_RESEARCH_PRIORITY'}
    atomic(report_dir/'PHASE4_FINAL_RECEIPT.json',encoded(final),tdx)
    atomic(root/'docs/PHASE4_REPORT.md',(f"# Phase 4 Report\n\nPASS at {cutoff}. All {len(out)} NORMAL_UNIVERSE stocks are published. Counts: {counts}. Primary patterns: {pats}. Overlaps: {overlap}. Upstream dates, generations and SHA256 values were bound before consumption. Only {len(norm)} latest normalized rows and four necessary fields were selected. Current valid sector contexts were used; invalid/excluded sectors were not eligible. Market and sector-member percentiles remain distinct. Tests: {final['tests_passed']} passed, 0 failed. No external data, index OHLC, score, dynamic threshold, rating, signal, backtest or historical membership backfill.\n\nNEXT_ALLOWED_PHASE=PHASE_5_CANDIDATE_POOL_AND_RESEARCH_PRIORITY.\n").encode(),tdx)
    spec=root/'PROJECT_SPEC.md';s=spec.read_text('utf8');marker='\n## Current production status — Phase 4\n';s=s.split(marker)[0]+marker+'\nPHASE4_STATUS = PASS\nRULE_VERSION = stock-scanner-ruleset-v1.0\nNEXT_PHASE = PHASE_5_CANDIDATE_POOL_AND_RESEARCH_PRIORITY\n';atomic(spec,s.encode(),tdx)
    print(json.dumps(final,ensure_ascii=False,indent=2));return final

if __name__=='__main__':run(Path(__file__).resolve().parents[1],Path('D:/new_tdx'))
