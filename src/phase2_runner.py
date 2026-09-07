from pathlib import Path
from datetime import date
import json
import os
import statistics
import subprocess
import sys
import uuid
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tdx.gbbq_reader import file_sha256
from tdx.security_master import read_industry_assignments
from tdx.block_reader import build_industry_memberships,read_industry_names,read_infoharbor_memberships
from sector.phase2 import *
from sector.membership_snapshot import build_snapshot,VERSION as MEMBERSHIP_VERSION
from validation.phase0_2b import atomic,encoded


def bind_phase1(root,receipt):
    for rel,key in [('data/normalized/adjusted_daily.parquet','adjusted_dataset_sha256'),('data/factors/factors_daily.parquet','factor_dataset_sha256')]:
        p=root/rel
        if file_sha256(p)!=receipt[key] or pq.ParquetFile(p).schema_arrow.metadata.get(b'generation',b'').decode()!=receipt['generation']:
            raise ValueError('PHASE1_MIXED_GENERATION_OR_HASH_MISMATCH')


def contracts(root,tdx):
    shared='''
Current snapshot only; source date is the Phase1 cutoff. No historical membership backfill, future factor rows, external data, index OHLC, composite score or scanner label.
Numeric finite values only; NULL never becomes zero. Quantiles use linear interpolation. Every numeric aggregate has __valid_count and __valid_ratio. Metadata fields describe date, version, identities, validity and provenance, are not ranked and have no numeric denominator.
Derived above_maN = aligned_close - MA_N with both inputs finite. Derived amount_ratio_5_20 = AMOUNT_MA5/AMOUNT_MA20, denominator>0, otherwise NULL. This is not Phase1 AMOUNT_RATIO20 (today/20D). amount_expansion = amount_ratio_5_20-1. Calendar: MASTER_TRADING_CALENDAR as inherited from Phase1; no new rolling-window calculation.
'''
    for sector,title,filename in [(False,'Market Regime Factor Contract V1','MARKET_REGIME_FACTOR_CONTRACT_V1.md'),(True,'Synthetic Sector Factor Contract V1','SYNTHETIC_SECTOR_FACTOR_CONTRACT_V1.md')]:
        lines=[f'# {title}',f'\nVersion: {VERSION if sector else MARKET_VERSION}',shared]
        if sector:
            lines.append('''Membership basis=CURRENT_TDX_MEMBERSHIP, pit_membership=false, historical_backtest_safe=false. Reuse sector-role-v0.1 without alteration. total_member_count is all unique source member identities, including unresolved/non-A identities. Valid means current factor row with valid identity and a known latest normalized state other than FILE_MISSING or DELISTED_OR_INACTIVE. Per-factor denominator further excludes NULL. coverage=valid/total; tradable_coverage=tradable/total, never interchangeable. Factor valid ratio uses total source members, making poor coverage visible.
Validity: INDUSTRY>=5 total, THEME/STYLE>=8 total; valid>=5 and coverage>=0.70. Excluded theme roles remain visible but are never sector_valid or ranked. Invalid sectors retain descriptive raw aggregates, with sector_valid=false and reason; no formal percentile.
sector_rsN = median(valid member RET_N) - median(same-day NORMAL_UNIVERSE RET_N). Audit equivalence with median(member RS_N); unavailable benchmark yields NULL. Each RS count describes valid member returns.
TOP3_CONCENTRATION follows V0.3 section39, not the task's alternative amount suggestion: sum(top3 max(RET1,0))/sum(all max(RET1,0)); RET1=C_t/C_previous_master_session-1, both closes positive. Minimum8 finite RET1 members, zero positive sum -> NULL. No amount or market-cap substitution. Negative returns contribute zero to this explicitly defined positive-return sum, not to missing-value imputation.
Same-type percentiles: valid sectors with finite factor only; group sector_type; ascending=True, method=average, pct=True. Higher return/breadth/activity and less-negative MDD produce higher percentile. Tie denominator is finite valid sector count for that field/type, stored separately. EXCLUDE_FROM_THEME_RANK has no percentile. No threshold labels.
''')
        else: lines.append('Membership/denominator: same-day NORMAL_UNIVERSE valid stock rows, then field-specific finite count. __valid_ratio divides by full NORMAL_UNIVERSE. No R2 threshold is invented; publish raw R2 medians and slope>0 breadth. RS quartiles describe dispersion, not a direction score. Amount means trading activity, never net inflow.')
        lines+=['\n| Field | Input | Formula | Denominator | Null rule | Ranking |','|---|---|---|---|---|---|']
        for name,(col,op) in specs(sector).items():
            lines.append(f'| {name} | {col} | {op} of finite inputs'+(' (>0 count / valid count)' if op=='positive' else '')+' | finite input count | empty -> NULL | '+('only explicit same-type percentile fields' if sector else 'none')+' |')
        if sector:
            for n in (5,10,20,60): lines.append(f'| sector_rs{n} | RET{n}, NORMAL_UNIVERSE | member median - market median | finite member returns | missing median -> NULL | RS20 only |')
            lines.append('| top3_concentration | positive RET1 | top3 sum / positive sum | positive sum; >=8 finite returns | zero sum or <8 -> NULL | none |')
            for name,col in RANKS.items(): lines.append(f'| {name} | {col} | average rank / count within type | valid finite sectors of same type | invalid -> NULL | ascending |')
        atomic(root/'docs'/filename,'\n'.join(lines).encode('utf8'),tdx)


def run(root,tdx):
    receipt_path=root/'reports/phase1/PHASE1_FINAL_RECEIPT.json'
    r=json.loads(receipt_path.read_text('utf8')); assert r['final_status']=='PASS'
    receipt_hash=file_sha256(receipt_path)
    bind_phase1(root,r)
    cutoff=r['cutoff_date']; ds=str(cutoff); d=date(int(ds[:4]),int(ds[4:6]),int(ds[6:]))
    stocks=pq.read_table(root/'data/factors/factors_daily.parquet',filters=[('date','=',d)]).to_pandas()
    snapshot_guard([int(x.strftime('%Y%m%d')) for x in stocks.date],cutoff,cutoff)
    if len(stocks)!=stocks.security_id.nunique(): raise ValueError('DUPLICATE_STOCK_ROW')
    cal_path=Path(os.environ.get('TDX_RUN_CALENDAR',root/'reports/phase0_1/MASTER_TRADING_CALENDAR.csv'))
    cal=pd.read_csv(cal_path); sessions=cal.loc[cal.is_market_open,'calendar_date'].tolist()
    if cutoff not in sessions: raise ValueError('MASTER_CALENDAR_EXTENSION_REQUIRED')
    prev=str(sessions[sessions.index(cutoff)-1]); previous=date(int(prev[:4]),int(prev[4:6]),int(prev[6:]))
    cols=['security_id','date','aligned_close','tradable','missing_state','raw_amount','is_synthetic_fill']
    latest=pq.read_table(root/'data/normalized/adjusted_daily.parquet',columns=cols,filters=[('date','in',[previous,d])]).to_pandas()
    today=latest[latest.date==d].drop(columns='date'); old=latest[latest.date==previous].set_index('security_id').aligned_close
    today['previous_close']=today.security_id.map(old)
    today['RET1']=(today.aligned_close/today.previous_close-1).where((today.aligned_close>0)&(today.previous_close>0))
    stocks=prepare(stocks,today)
    assert stocks.universe_status.eq('IN_NORMAL_UNIVERSE').sum()==r['normal_universe_count']
    cache=tdx/'T0002/hq_cache'; paths=[cache/n for n in ('tdxhy.cfg','tdxzs.cfg','infoharbor_block.dat')]
    source_hashes={str(p):file_sha256(p) for p in paths}
    member=build_industry_memberships(read_industry_assignments(paths[0]),read_industry_names(paths[1]))
    extra,meta=read_infoharbor_memberships(paths[2]); member += [v for v in extra if v['sector_type'] in ('concept','style')]
    present={(m['sector_type'],m['sector_code']) for m in member}
    for header in meta['sector_headers']:
        if header['sector_type'] in ('concept','style') and (header['sector_type'],header['sector_code']) not in present:
            member.append({**header,'security_id':None,'membership_basis':BASIS,'source':'infoharbor_block.dat'})
    membership=pd.DataFrame(member).drop_duplicates(['sector_type','sector_code','security_id'])
    membership_snapshot,_=build_snapshot(tdx,cutoff)
    contracts(root,tdx)
    market=market_vector(stocks); market.update(date=d,snapshot_basis='CURRENT_SNAPSHOT_ONLY',phase1_generation=r['generation'],index_ohlc_used=False)
    sector,member_frames=sectors(stocks,membership)
    sector['date']=d; sector['membership_asof_date']=d; sector['phase1_generation']=r['generation']
    # Duplicate source header identities would make the snapshot ambiguous.
    assert not sector.sector_id.duplicated().any()
    qa=qa_outputs(root,tdx,stocks,market,sector,member_frames)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/phase2'],cwd=root,capture_output=True,text=True)
    checks={'phase1_bound':True,'qa':qa,'tests':tests.returncode==0,
            'source_unchanged':all(file_sha256(Path(p))==h for p,h in source_hashes.items()),
            'excluded_not_ranked':sector.loc[sector.sector_role=='EXCLUDE_FROM_THEME_RANK',list(RANKS)].isna().all().all()}
    if phase2_gate(checks)!='PASS': raise ValueError(str(checks)+tests.stdout+tests.stderr)
    if file_sha256(receipt_path)!=receipt_hash: raise ValueError('PHASE1_RECEIPT_CHANGED')
    # Check source artifacts have not changed during aggregation.
    bind_phase1(root,r)
    generation=uuid.uuid4().hex; staged=[]; output_hashes={}
    for rel,frame,keys in [('data/market/market_regime_daily.parquet',pd.DataFrame([market]),['date']),('data/sectors/sector_factors_daily.parquet',sector,['date','sector_id']),('data/sectors/sector_membership_daily.parquet',membership_snapshot,['date','sector_id','security_id'])]:
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():
            old=pq.read_table(p).to_pandas()
            if (old.date>d).any(): raise ValueError('FUTURE_SNAPSHOT_IN_EXISTING_OUTPUT')
            frame=pd.concat([old[old.date<d],frame],ignore_index=True)
        assert not frame.duplicated(keys).any()
        table=pa.Table.from_pandas(frame,preserve_index=False).replace_schema_metadata({b'generation':generation.encode(),b'phase1_generation':r['generation'].encode()})
        tmp=p.with_name('.'+p.name+'.'+generation+'.tmp'); pq.write_table(table,tmp,compression='zstd')
        assert pq.read_table(tmp).num_rows==len(frame)
        with tmp.open('r+b') as f: os.fsync(f.fileno())
        staged.append((tmp,p));output_hashes[rel]=file_sha256(tmp)
    for tmp,p in staged: os.replace(tmp,p)
    out=root/'reports/phase2'; nvalid=int(sector.sector_valid.sum())
    result={'phase':'PHASE2','baseline_version':'V0.3_FINAL_IMPLEMENTATION_BASELINE','final_status':'PASS','cutoff_date':cutoff,
        'generation':generation,'phase1_generation':r['generation'],'phase1_factor_sha256':r['factor_dataset_sha256'],
        'phase1_adjusted_sha256':r['adjusted_dataset_sha256'],'market_regime_status':'GENERATED','market_regime_rows':1,
        'sector_factor_contract_version':VERSION,'sector_factor_status':'GENERATED','sector_factor_rows':len(sector),
        'sector_membership_snapshot_version':MEMBERSHIP_VERSION,'sector_membership_rows':len(membership_snapshot),
        'sector_count_total':len(sector),'sector_count_valid':nvalid,'sector_count_invalid':len(sector)-nvalid,
        **{k.lower()+'_valid_count':int(((sector.sector_type==k)&sector.sector_valid).sum()) for k in ('INDUSTRY','THEME','STYLE')},
        'membership_basis':BASIS,'pit_membership':False,'historical_backtest_safe':False,
        'index_ohlc_used':False,'external_data_used':False,'same_type_ranking':True,'coverage_gate':True,
        'tests_passed':int(tests.stdout.split(' passed')[0].split()[-1]),'tests_failed':0,'test_output':tests.stdout,
        'source_hashes':source_hashes,'tdx_source_unchanged':True,'output_sha256':output_hashes,
        'warnings':['CURRENT_SNAPSHOT_ONLY; current membership is not historical PIT',
                    'TOP3_CONCENTRATION uses V0.3 positive RET1 concentration, minimum8; not amount concentration',
                    'amount_ratio_5_20 derived from Phase1 amount MAs; not AMOUNT_RATIO20'],
        'errors':[],'next_allowed_phase':'PHASE_3_SECTOR_SCANNER','phase1_latest_factor_rows':len(stocks),
        'normalized_selected_rows':len(latest),'normalized_query_scope':'latest two master dates, seven columns; no full historical table materialization'}
    atomic(out/'PHASE2_FINAL_RECEIPT.json',encoded(result),tdx)
    report=f'''# Phase 2 Report

PASS, cutoff {cutoff}. Phase1 generation and both canonical SHA256 values verified before consumption and again before publication. No index OHLC, external data, raw .day scan or adjustment recalculation.

Market vector: one latest row from {r['normal_universe_count']} NORMAL_UNIVERSE members. Sector factors: {len(sector)} current sectors, {nvalid} valid. INDUSTRY/THEME/STYLE rankings are separate; excluded theme roles never ranked. coverage=valid/total unique source members, not tradable/total. Each aggregate carries finite-value counts and ratios to total source membership. NULL not imputed.

TOP3_CONCENTRATION follows baseline section39: top3 positive one-session returns / total positive returns, minimum8 finite RET1 values, zero positive sum -> NULL. Phase1 lacks RET1 and current close, so only two latest master dates and seven columns were queried from normalized Parquet ({len(latest)} selected rows); no historical dataframe loaded. Amount activity uses AMOUNT_MA5/AMOUNT_MA20, not the distinct today/20D metric.

No subjective trend-quality threshold, market state, composite score, sector classification or concentration tag was introduced. Market and sector layers each aggregate stock inputs independently. All membership carries CURRENT_TDX_MEMBERSHIP, pit=false, historical_backtest_safe=false. Old years are never backfilled.

QA: independent market breadth/median checks, sector RS equivalence, at least 3 samples per role with raw member inputs and direct recalculations, same-type percentile checks. Tests {result['tests_passed']} passed,0 failed. See audit JSON and SECTOR_SAMPLE_CALC.md.

Future latest snapshots append by date and preserve existing older rows. Publication uses staged validation/fsync/replace; receipt last. Consumers validate both output hashes/generation. Phase1 inputs and TDX membership unchanged.

NEXT_ALLOWED_PHASE=PHASE_3_SECTOR_SCANNER. Phase3 not started.
'''
    atomic(root/'docs/PHASE2_REPORT.md',report.encode('utf8'),tdx)
    p=root/'PROJECT_SPEC.md'; s=p.read_text('utf8'); marker='\n## Current production status — Phase 2\n'
    if marker in s:s=s.split(marker)[0]
    s+=marker+'\nPHASE2_STATUS = PASS\nSNAPSHOT_BASIS = CURRENT_SNAPSHOT_ONLY\nSECTOR_MEMBERSHIP_BASIS = CURRENT_TDX_MEMBERSHIP\nNEXT_PHASE = PHASE_3_SECTOR_SCANNER\n\nThis section supersedes earlier next-phase pointers. No Phase3 scanner is implemented.\n'
    atomic(p,s.encode('utf8'),tdx)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result


def qa_outputs(root,tdx,stocks,market,sector,frames):
    out=root/'reports/phase2'; normal=stocks[stocks.universe_status=='IN_NORMAL_UNIVERSE']
    checks={}
    for field,col,op in [('breadth_ret20_pos','RET20','positive'),('breadth_above_ma20','above_ma20','positive'),('mdd20_median','MDD20','median'),('amount_ratio_5_20_median','amount_ratio_5_20','median')]:
        v=normal[col].dropna().tolist(); ref=sum(x>0 for x in v)/len(v) if op=='positive' else statistics.median(v)
        checks[field]=bool(np.isclose(market[field],ref,atol=1e-12))
    errors=sector[[f'sector_rs{n}__equivalence_error' for n in (5,10,20,60)]]
    rs=bool((errors.abs().fillna(0)<1e-10).all().all())
    # NA in equivalence audit means both forms unavailable, never a factor zero.
    assert all(checks.values()) and rs
    atomic(out/'MARKET_REGIME_AUDIT.json',encoded({'checks':checks,'vector':market,'index_ohlc_used':False}),tdx)
    audit={'total_sectors':len(sector),'valid_sectors':int(sector.sector_valid.sum()),
        **{k.lower()+'_sectors':int((sector.sector_role==k).sum()) for k in ('INDUSTRY','THEME','STYLE')},
        'excluded_sectors':int((sector.sector_role=='EXCLUDE_FROM_THEME_RANK').sum()),
        'invalid_by_min_member':int(sector.invalid_reason.str.contains('MIN_TOTAL_MEMBERS|MIN_VALID_MEMBERS').sum()),
        'invalid_by_coverage':int(sector.invalid_reason.str.contains('LOW_COVERAGE').sum()),
        'membership_basis':BASIS,'pit_membership':False}
    atomic(out/'SECTOR_MEMBERSHIP_AUDIT.json',encoded(audit),tdx)
    selected=[]
    for typ in ('INDUSTRY','THEME','STYLE'):
        x=sector[sector.sector_role==typ].sort_values(['total_member_count','sector_id'])
        nonempty=x[x.total_member_count >= (5 if typ=='INDUSTRY' else 8)]
        for i in (0,len(nonempty)//2,len(nonempty)-1): selected.append(nonempty.iloc[i].sector_id)
        for c in ('coverage','tradable_coverage'):
            worst=x.sort_values([c,'sector_id']).iloc[0].sector_id
            if worst not in selected:selected.append(worst)
    lines=['# Sector sample recalculation','\nCurrent member inputs exported per sample. Valid member rows identified explicitly; NULL values excluded per factor.']
    count=0
    for sid in selected:
        row=sector[sector.sector_id==sid].iloc[0]; m=frames[sid]; v=m[m.valid_member.eq(True)]
        safe=sid.replace(':','_')
        cols=['security_id','valid_member','missing_state','tradable','RET1','RET20','RS20','above_ma20','MDD20','amount_ratio_5_20']
        atomic(out/f'SAMPLE_MEMBERS_{safe}.csv',m[cols].to_csv(index=False).encode('utf-8-sig'),tdx)
        vals=v.RET20.dropna().tolist(); expected=statistics.median(vals) if vals else np.nan
        assert (pd.isna(expected) and pd.isna(row.sector_ret20_median)) or np.isclose(expected,row.sector_ret20_median)
        rr=v.RET1.dropna().tolist(); pos=sorted([max(float(a),0) for a in rr],reverse=True)
        top=sum(pos[:3])/sum(pos) if len(rr)>=8 and sum(pos)>0 else np.nan
        assert (pd.isna(top) and pd.isna(row.top3_concentration)) or np.isclose(top,row.top3_concentration)
        count+=2
        lines += [f'\n## {sid} {row.sector_name} ({row.sector_role})',
            f'Input: SAMPLE_MEMBERS_{safe}.csv; total={len(m)}, valid={len(v)}, coverage={row.coverage:.8f}, tradable={row.tradable_member_count}, suspended={row.suspended_member_count}.',
            f'RET20 median: sorted finite member returns, n={len(vals)}, independent={expected}, output={row.sector_ret20_median}.',
            f'TOP3: valid RET1 n={len(rr)}, top3 positive sum={sum(pos[:3])}, all positive sum={sum(pos)}, independent={top}, output={row.top3_concentration}.']
    atomic(out/'SECTOR_SAMPLE_CALC.md','\n'.join(lines).encode('utf8'),tdx)
    for pct,col in RANKS.items():
        eligible=sector.sector_valid & sector[col].notna()
        assert sector.loc[~eligible,pct].isna().all()
        for _,group in sector[eligible].groupby('sector_type'):
            values=group[col].tolist()
            for _,row in group.iterrows():
                below=sum(v<row[col] for v in values); tied=sum(v==row[col] for v in values)
                expected=(below+(tied+1)/2)/len(values)
                assert np.isclose(expected,row[pct],atol=1e-12)
    fields=list(specs(True))+[f'sector_rs{n}' for n in (5,10,20,60)]+['top3_concentration']+list(RANKS)
    dist=[]
    for typ,x in sector.groupby('sector_type'):
        for name in fields:
            v=x.loc[x.sector_valid,name].dropna(); q=v.quantile([0,.01,.05,.5,.95,.99,1]).tolist() if len(v) else [None]*7
            dist.append(dict(sector_type=typ,factor=name,valid_sector_count=int(x.sector_valid.sum()),non_null_count=len(v),null_count=int(x.sector_valid.sum())-len(v),**dict(zip(['min','p01','p05','median','p95','p99','max'],q))))
    atomic(out/'SECTOR_FACTOR_DISTRIBUTION.csv',pd.DataFrame(dist).to_csv(index=False).encode('utf-8-sig'),tdx)
    atomic(out/'SECTOR_FACTOR_AUDIT.json',encoded({'rs_equivalence_pass':rs,'sample_sectors':selected,'independent_sample_checks':count,'same_type_ranking':True,'sector_factor_count':len(fields)}),tdx)
    return True
