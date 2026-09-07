from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone,date
import hashlib,html,json,os,shutil,struct,time,traceback,uuid,sys
import pandas as pd
import pyarrow.parquet as pq
from tdx.gbbq_reader import file_sha256
from common.identity import source_identity,computation_identity,render_identity
from common.input_snapshot import (archive_source_revision,build_input_snapshot_manifest,
                                   next_source_revision_id,validate_input_snapshot_manifest,
                                   write_immutable_manifest)
from common.run_lock import RunLock,ActiveRunLock
from common.snapshot_reader import assert_no_future_rows,read_snapshot
from production.release import (RELEASE_FILES,PublicationValidationError,atomic_write_json,
                                atomic_write_bytes,build_pointer,publish_generation,validate_release_generation)
from production.dashboard import render_dashboard

PRODUCTION_VERSION='daily-production-v1.2'
FINGERPRINT_VERSION='production-source-fingerprint-v1.1-full-content'
REQUIRED=('market_summary.html','sectors.csv','stocks.csv','candidates.csv','run_audit.json','PERFORMANCE_AUDIT.json','INPUT_SNAPSHOT_MANIFEST.json','manifest.json','PRODUCTION_RECEIPT.json')
STAGE_ORDER=('PRECHECK','NORMALIZATION_ADJUSTMENT_FACTOR_ENGINE','MARKET_REGIME_SYNTHETIC_SECTOR','SECTOR_SCANNER','STOCK_SCANNER','CANDIDATE_POOL_PRIORITY','REPORTING','END_TO_END_VERIFY','FINAL_RECEIPT')
EXIT_SUCCESS=0;EXIT_FAILURE=1;EXIT_NOT_READY=2;EXIT_BINDING=3;EXIT_PUBLICATION=4

def now():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require_hash(actual,expected):
    if actual!=expected:raise RuntimeError('HASH_MISMATCH')
    return True
def guard_no_future(values,cutoff):
    if values and max(values)>cutoff:raise RuntimeError('FUTURE_SNAPSHOT')
    return True
def json_read(path):return json.loads(Path(path).read_text('utf8'))

def published_release_binding(pointer_value, target, invocation_id):
    """Return the verified release identity separately from the current invocation."""
    target=Path(target);release_id=(pointer_value or {}).get('run_id')
    if not release_id or not target.is_dir():raise RuntimeError('PUBLISHED_RELEASE_BINDING_MISSING')
    receipt=json_read(target/'PRODUCTION_RECEIPT.json')
    computation=(pointer_value or {}).get('computation_identity') or receipt.get('computation_identity')
    if not computation or not computation.get('sha256'):raise RuntimeError('PUBLISHED_RELEASE_COMPUTATION_IDENTITY_MISSING')
    return {'invocation_id':str(invocation_id),'published_release_id':str(release_id),'release_path':str(target),'published_release_exists':True,'published_computation_identity':computation}

def _latest_day_records(tdx):
    files=[]; per_market={}; counts={}
    for market,folder,pattern in (('SH',tdx/'vipdoc/sh/lday','sh*.day'),('SZ',tdx/'vipdoc/sz/lday','sz*.day'),('BJ',tdx/'vipdoc/bj/lday','bj*.day')):
        market_files=list(folder.glob(pattern)); per_market[market]={}; files += market_files
        for p in market_files:
            try:
                with p.open('rb') as fh:
                    if p.stat().st_size<32: continue
                    fh.seek(-32,2);value=struct.unpack('<I',fh.read(4))[0]
                if 19900101<=value<=21001231:
                    counts[value]=counts.get(value,0)+1;per_market[market][value]=per_market[market].get(value,0)+1
            except (OSError,struct.error):pass
    return files,per_market,counts

def _index_date_evidence(tdx):
    result={}
    for market,code in (('sh','000001'),('sz','399001')):
        p=tdx/f'vipdoc/{market}/lday/{market}{code}.day'
        try:
            with p.open('rb') as fh:fh.seek(-32,2);result[f'{market.upper()}.{code}']=struct.unpack('<I',fh.read(4))[0]
        except (OSError,struct.error):pass
    return result

def _local_index_sessions(tdx, after, through):
    """Collect locally observed index dates; index prices are never consumed."""
    calendars=[]
    if tdx is None:return []
    for market,code in (('sh','000001'),('sz','399001')):
        p=Path(tdx)/f'vipdoc/{market}/lday/{market}{code}.day'
        try:
            raw=p.read_bytes();values=[struct.unpack_from('<I',raw,n)[0] for n in range(0,len(raw)-31,32)]
            dates={int(v) for v in values if int(after)<int(v)<=int(through)}
            if dates:calendars.append(dates)
        except (OSError,struct.error):pass
    return sorted(set().union(*calendars)) if calendars else []

def _calendar_snapshot(root, cutoff, tdx=None):
    cal=root/'reports/phase0_1/MASTER_TRADING_CALENDAR.csv'
    frame=pd.read_csv(cal)
    existing=set(frame.calendar_date.astype(int));latest=max(existing)
    additions=_local_index_sessions(tdx,latest,int(cutoff))
    if int(cutoff) not in existing and int(cutoff) not in additions:additions.append(int(cutoff))
    rows=[{'calendar_date':value,'is_market_open':True,'source_basis':'LOCAL_AUDITED_TRADING_DAY_EVIDENCE','confirmation_count':0,'index_confirmation_count':0,'confirming_indices':'','a_stock_confirmation_count':0,'eligible_a_stock_count':0,'a_stock_confirmation_ratio':0.0} for value in sorted(set(additions)-existing)]
    if rows:frame=pd.concat([frame,pd.DataFrame(rows)],ignore_index=True)
    payload=frame.sort_values('calendar_date').to_csv(index=False).encode('utf8')
    return frame,payload,hashlib.sha256(payload).hexdigest()

def latest_resolution(root,tdx,as_of=None):
    cal=root/'reports/phase0_1/MASTER_TRADING_CALENDAR.csv'
    if not cal.exists():raise FileNotFoundError('MASTER_TRADING_CALENDAR_MISSING')
    c=pd.read_csv(cal); opens=c[c.is_market_open.astype(bool)]
    master=str(int(opens.calendar_date.max()));files,per_market,counts=_latest_day_records(tdx)
    if not counts:raise RuntimeError('INPUT_NOT_READY:no_valid_day_records')
    dominant=int(max(counts,key=lambda value:(counts[value],value)))
    local=max(counts); local_count=counts[local]
    market_coverage={m:round(n.get(local,0)/max(1,sum(n.values())),6) for m,n in per_market.items()}
    market_latest={m:(max(n) if n else None) for m,n in per_market.items()}
    evidence={'file_count':len(files),'date_counts':{str(k):v for k,v in sorted(counts.items())},'market_latest':market_latest,'market_coverage':market_coverage,'index_dates':_index_date_evidence(tdx),'dominant_latest_session':str(dominant),'maximum_observed_session':str(local)}
    today=as_of or date.today()
    status='NO_NEW_DATA'
    if str(local)<master: status='INPUT_NOT_READY'
    elif str(local)>master:
        broad=local_count>=max(1,int(len(files)*0.5)) and all(v>=0.5 for v in market_coverage.values())
        any_market_ready=any(v>=0.5 for v in market_coverage.values())
        index_dates=set(evidence['index_dates'].values())
        index_ok=not evidence['index_dates'] or index_dates=={local}
        if broad: status='NORMAL_NEW_TRADING_DAY' if index_ok else 'INVALID_FUTURE_OUTLIER'
        elif any_market_ready: status='PARTIAL_UPDATE'
        else: status='INVALID_FUTURE_OUTLIER'
    elif today.weekday()>=5:
        status='WEEKEND_NO_NEW_DATA'
    else:
        today_rows=c[c.calendar_date.astype(int)==int(today.strftime('%Y%m%d'))]
        if len(today_rows) and not bool(today_rows.iloc[-1].is_market_open):status='HOLIDAY_NO_NEW_DATA'
    frame,payload,calendar_hash=_calendar_snapshot(root,str(local if status=='NORMAL_NEW_TRADING_DAY' and str(local)>master else master),tdx)
    generation=hashlib.sha256(payload).hexdigest()[:24]
    return {'system_date':date.today().strftime('%Y%m%d'),'master_calendar_latest_session':master,'local_tdx_latest_session':str(local),'resolved_cutoff_date':str(local if status=='NORMAL_NEW_TRADING_DAY' and str(local)>master else master),'cutoff_status':status,'evidence_summary':evidence,'calendar_generation':generation,'calendar_sha256':calendar_hash,'run_calendar_rows':frame.to_dict('records')}

def readiness(root,tdx):
    cache=tdx/'T0002/hq_cache';required=[tdx,root/'reports/phase0_1/MASTER_TRADING_CALENDAR.csv',cache/'shs.tnf',cache/'szs.tnf',cache/'bjs.tnf',cache/'gbbq',cache/'tdxhy.cfg',cache/'tdxzs.cfg',cache/'infoharbor_block.dat']
    required += [root/x for x in ('docs/FACTOR_CONTRACT_V1.md','docs/SYNTHETIC_SECTOR_FACTOR_CONTRACT_V1.md','docs/SECTOR_SCANNER_CONTRACT_V1.md','docs/STOCK_SCANNER_CONTRACT_V1.md','docs/CANDIDATE_POOL_CONTRACT_V1.md','docs/RESEARCH_PRIORITY_CONTRACT_V1.md')]
    missing=[str(x) for x in required if not x.exists()]
    if missing:raise FileNotFoundError('READINESS_MISSING:'+','.join(missing))
    resolution=latest_resolution(root,tdx);return resolution,required

def tdx_hashes(tdx):
    cache=tdx/'T0002/hq_cache';files=[cache/x for x in ('gbbq','gbbq.map','tdxhy.cfg','tdxzs.cfg','infoharbor_block.dat','shs.tnf','szs.tnf','bjs.tnf')]
    return {str(x):file_sha256(x) for x in files if x.exists()}

def day_source_fingerprint(tdx):
    """Hash complete local day-file content so metadata-preserving revisions are detected."""
    items=[]; latest_counts={}
    markets=(('SH',tdx/'vipdoc/sh/lday','sh*.day'),('SZ',tdx/'vipdoc/sz/lday','sz*.day'),('BJ',tdx/'vipdoc/bj/lday','bj*.day'))
    for market,folder,pattern in markets:
        for p in folder.glob(pattern):
            stat=p.stat();tail=b'';latest=None
            if stat.st_size>=32:
                with p.open('rb') as fh:fh.seek(-32,2);tail=fh.read(32)
                latest=struct.unpack('<I',tail[:4])[0];latest_counts[str(latest)]=latest_counts.get(str(latest),0)+1
            items.append({'security_id':market+'.'+p.stem[2:],'file_size':stat.st_size,'mtime_ns':stat.st_mtime_ns,'latest_record_date':latest,'latest_record_sha256':hashlib.sha256(tail).hexdigest(),'content_sha256':file_sha256(p)})
    payload=json.dumps(sorted(items,key=lambda x:x['security_id']),sort_keys=True,separators=(',',':')).encode()
    dominant=max(latest_counts,key=latest_counts.get) if latest_counts else None
    return hashlib.sha256(payload).hexdigest(),{'file_count':len(items),'dominant_latest_record_date':dominant,'dominant_latest_record_count':latest_counts.get(dominant,0),'distinct_latest_record_dates':len(latest_counts),'algorithm':'sorted(security_id,file_size,mtime_ns,latest_record_date,latest_record_sha256,content_sha256)'}

def source_fingerprint(root,tdx,resolved_cutoff):
    started=time.perf_counter();day_started=time.perf_counter();day_hash,day_summary=day_source_fingerprint(tdx);day_seconds=time.perf_counter()-day_started
    cache=tdx/'T0002/hq_cache';paths={'gbbq':cache/'gbbq','gbbq_map':cache/'gbbq.map','tdxhy':cache/'tdxhy.cfg','tdxzs':cache/'tdxzs.cfg','infoharbor_block':cache/'infoharbor_block.dat','sh_tnf':cache/'shs.tnf','sz_tnf':cache/'szs.tnf','bj_tnf':cache/'bjs.tnf','master_calendar':root/'reports/phase0_1/MASTER_TRADING_CALENDAR.csv'}
    components={'day':day_hash,**{k:sha(v) for k,v in paths.items()},'resolved_cutoff_date':resolved_cutoff}
    canonical=json.dumps(components,sort_keys=True,separators=(',',':')).encode()
    return {'source_fingerprint_version':FINGERPRINT_VERSION,'source_fingerprint':hashlib.sha256(canonical).hexdigest(),'source_fingerprint_components':components,'day_fingerprint_summary':day_summary,'source_fingerprint_seconds':round(time.perf_counter()-started,6),'day_fingerprint_seconds':round(day_seconds,6)}

def changed_components(old,new):
    a=(old or {}).get('source_fingerprint_components',{});b=new.get('source_fingerprint_components',{})
    return sorted(k for k in set(a)|set(b) if a.get(k)!=b.get(k))

def assert_source_stable(source_identity_before,source_identity_after):
    if (source_identity_before or {}).get('sha256')!=(source_identity_after or {}).get('sha256'):
        raise RuntimeError('SOURCE_CHANGED_DURING_RUN')
    return True

def freshness_decision(report_exists,cutoff,existing_receipt,current):
    if not report_exists:return 'FRESH_CUTOFF'
    if str((existing_receipt or {}).get('cutoff_date'))!=str(cutoff):return 'FRESH_CUTOFF'
    existing=existing_receipt or {}
    if existing.get('source_fingerprint')!=current.get('source_fingerprint'):return 'SAME_CUTOFF_SOURCE_REVISION'
    # Legacy receipts predate R0 identities.  They remain readable, but a
    # current run must not classify them as no-new-data once formal identities
    # are available.
    for key in ('computation_identity','render_identity'):
        if key in current and key not in existing:return 'SAME_CUTOFF_'+key.split('_')[0].upper()+'_REVISION'
        if key in current and existing.get(key,{}).get('sha256')!=current.get(key,{}).get('sha256'):
            return 'SAME_CUTOFF_'+key.split('_')[0].upper()+'_REVISION'
    if current.get('source_identity') and existing.get('source_identity') and existing['source_identity'].get('sha256')!=current['source_identity'].get('sha256'):
        return 'SAME_CUTOFF_SOURCE_REVISION'
    return 'VERIFIED_NO_NEW_DATA'

def receipt_chain(root,cutoff):
    rs={i:json_read(root/f'reports/phase{i}/PHASE{i}_FINAL_RECEIPT.json') for i in range(1,6)}
    if any(str(x['cutoff_date'])!=cutoff or x['final_status']!='PASS' for x in rs.values()):raise RuntimeError('PHASE_CHAIN_STATUS_OR_CUTOFF_MISMATCH')
    paths={1:[('data/factors/factors_daily.parquet','factor_dataset_sha256'),('data/normalized/adjusted_daily.parquet','adjusted_dataset_sha256')],2:[('data/market/market_regime_daily.parquet',None),('data/sectors/sector_factors_daily.parquet',None),('data/sectors/sector_membership_daily.parquet',None)],3:[('data/scanner/sector_scanner_daily.parquet','output_sha256')],4:[('data/scanner/stock_scanner_daily.parquet','output_sha256')],5:[('data/candidates/candidate_pool_daily.parquet','output_sha256')]}
    hashes={}
    for i,items in paths.items():
        for rel,key in items:
            actual=sha(root/rel); expected=(rs[i][key] if key else rs[i]['output_sha256'][rel])
            try:require_hash(actual,expected)
            except RuntimeError:raise RuntimeError(f'PHASE{i}_HASH_MISMATCH:{rel}')
            hashes[rel]=actual
            tab=pq.read_table(root/rel,columns=['date']).to_pandas()
            try:guard_no_future(tab.date.tolist(),date(int(cutoff[:4]),int(cutoff[4:6]),int(cutoff[6:])))
            except RuntimeError:raise RuntimeError(f'FUTURE_SNAPSHOT:{rel}')
        generation=pq.ParquetFile(root/items[-1][0]).schema_arrow.metadata.get(b'generation',b'').decode()
        if generation!=rs[i]['generation']:raise RuntimeError(f'PHASE{i}_GENERATION_MISMATCH')
    return rs,hashes

def timed_step(name,fn,perf,rows_read=0,cache_reused=False):
    start=now();tick=time.perf_counter();result=fn();elapsed=time.perf_counter()-tick
    perf.append({'step':name,'start_time':start,'end_time':now(),'elapsed_seconds':round(elapsed,6),'rows_read':rows_read,'rows_written':0,'cache_reused':cache_reused})
    return result

def universe_snapshot(stocks,cutoff,generation=None):
    """Create the run-local exact Universe contract; count is descriptive only."""
    ids=[str(x) for x in stocks.security_id.tolist()]
    if len(ids)!=len(set(ids)):raise RuntimeError('DYNAMIC_UNIVERSE_DUPLICATE_ID')
    ids=sorted(ids);payload='\n'.join(ids).encode('utf8')
    return {'cutoff_date':str(cutoff),'generation':generation,'security_ids':ids,'count':len(ids),
            'sha256':hashlib.sha256(payload).hexdigest(),
            'quality_summary':{'unique_ids':len(ids)==len(set(ids)),'valid_id_count':sum(len(x)==9 and x[3]=='.' for x in ids)}}

def validate_universe_binding(snapshot, downstream_ids, downstream_generation=None):
    expected=list(snapshot.get('security_ids',[]));actual=[str(x) for x in downstream_ids]
    if len(actual)!=len(set(actual)):raise RuntimeError('DYNAMIC_UNIVERSE_DOWNSTREAM_DUPLICATE_ID')
    if set(actual)!=set(expected):raise RuntimeError('DYNAMIC_UNIVERSE_IDENTITY_MISMATCH')
    if downstream_generation is not None and snapshot.get('generation') not in (None,downstream_generation):
        raise RuntimeError('DYNAMIC_UNIVERSE_GENERATION_MISMATCH')
    return True

def _failure_hook(label):
    if os.environ.get('R0_FAILURE_INJECTION','').strip().upper()==label:
        raise PublicationValidationError('INJECTED_FAILURE:'+label)

def run_phases(root,tdx,perf,resolved_cutoff_date):
    from phase1_runner import run as p1
    from phase2_runner import run as p2
    from phase3_runner import run as p3
    from phase4_runner import run as p4
    from phase5_runner import run as p5
    outputs=[]
    outputs.append(timed_step(STAGE_ORDER[1],lambda:p1(root,tdx,'latest',resolved_cutoff_date=resolved_cutoff_date),perf))
    perf[-1].update(rows_written=outputs[-1]['factor_dataset_rows']+outputs[-1]['adjusted_dataset_rows'],cache_reused=bool(outputs[-1].get('cache_reused')),cache_reused_count=outputs[-1].get('cache_reused',0),full_build_reason='Canonical single-file Parquet publication; per-security adjustment cache reused')
    outputs.append(timed_step(STAGE_ORDER[2],lambda:p2(root,tdx),perf,rows_read=outputs[-1]['normal_universe_count']))
    perf[-1].update(rows_written=outputs[-1]['market_regime_rows']+outputs[-1]['sector_factor_rows'])
    outputs.append(timed_step(STAGE_ORDER[3],lambda:p3(root,tdx),perf,rows_read=outputs[-1]['sector_factor_rows']))
    perf[-1].update(rows_written=outputs[-1]['output_rows'])
    outputs.append(timed_step(STAGE_ORDER[4],lambda:p4(root,tdx),perf,rows_read=outputs[-1]['output_rows']))
    perf[-1].update(rows_written=outputs[-1]['output_rows'])
    outputs.append(timed_step(STAGE_ORDER[5],lambda:p5(root,tdx),perf,rows_read=outputs[-1]['output_rows']))
    perf[-1].update(rows_written=outputs[-1]['candidate_count'])
    return outputs

def f(v,d=4):
    try:return f'{float(v):.{d}f}'
    except:return ''
def table_html(df,cols):
    head=''.join(f'<th>{html.escape(c)}</th>' for c in cols);rows=[]
    for _,r in df.iterrows():rows.append('<tr>'+''.join(f'<td>{html.escape(str(r.get(c,"")))}</td>' for c in cols)+'</tr>')
    return '<table><thead><tr>'+head+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table>'

def build_reports(root,stage,cutoff,run_id,started,perf,resolution,fingerprint,run_event,changed,tdx=None):
    d=date(int(cutoff[:4]),int(cutoff[4:6]),int(cutoff[6:]));rs,hashes=receipt_chain(root,cutoff)
    market=pq.read_table(root/'data/market/market_regime_daily.parquet',filters=[('date','=',d)]).to_pandas()
    sectors=pq.read_table(root/'data/scanner/sector_scanner_daily.parquet',filters=[('date','=',d)]).to_pandas()
    stocks=pq.read_table(root/'data/scanner/stock_scanner_daily.parquet',filters=[('date','=',d)]).to_pandas()
    candidates=pq.read_table(root/'data/candidates/candidate_pool_daily.parquet',filters=[('date','=',d)]).to_pandas()
    run_universe=universe_snapshot(stocks,cutoff,rs[4]['generation'])
    if len(sectors)!=sectors.sector_id.nunique() or len(candidates)!=candidates.security_id.nunique():raise RuntimeError('DUPLICATE_REPORT_IDENTITIES')
    stage.mkdir(parents=True,exist_ok=False)
    _failure_hook('FAIL_BEFORE_REPORT_BUILD')
    sectors.to_csv(stage/'sectors.csv',index=False,encoding='utf-8-sig');_failure_hook('FAIL_AFTER_SECTORS_CSV')
    stocks.to_csv(stage/'stocks.csv',index=False,encoding='utf-8-sig');_failure_hook('FAIL_AFTER_STOCKS_CSV')
    leader=sectors[['sector_id','sector_name','sector_type','primary_pattern']].rename(columns={'sector_id':'primary_leader_sector','sector_name':'primary_leader_sector_name','sector_type':'primary_leader_sector_type','primary_pattern':'primary_leader_pattern_report'})
    candidates=candidates.merge(leader,on='primary_leader_sector',how='left')
    candidates['primary_leader_sector_id']=candidates.primary_leader_sector
    candidates['primary_leader_pattern']=candidates.primary_leader_pattern_report.combine_first(candidates.primary_leader_pattern)
    candidates=candidates.drop(columns='primary_leader_pattern_report')
    leaders=candidates.effective_pattern.eq('SECTOR_LEADER')
    required_leader=['primary_leader_sector_id','primary_leader_sector_name','primary_leader_sector_type','primary_leader_pattern']
    if candidates.loc[leaders,required_leader].isna().any().any():raise RuntimeError('PRIMARY_LEADER_JOIN_INCOMPLETE')
    candidates.sort_values(['research_priority_pct','priority_score','security_id'],ascending=[False,False,True]).to_csv(stage/'candidates.csv',index=False,encoding='utf-8-sig');_failure_hook('FAIL_AFTER_CANDIDATES_CSV')
    grades=candidates.research_priority.value_counts().to_dict()
    doc=render_dashboard(cutoff,rs[5]['generation'],market,sectors,candidates)
    (stage/'market_summary.html').write_text(doc,encoding='utf8');_failure_hook('FAIL_AFTER_HTML')
    sector_counts=sectors.primary_pattern.value_counts().to_dict();stock_counts={x:int(stocks[x].sum()) for x in ('steady_trend','strong_pullback','breakout_prep','sector_leader','early_mover')}
    same=int((leaders & candidates.best_sector_name.eq(candidates.primary_leader_sector_name)).sum());different=int((leaders & candidates.best_sector_name.ne(candidates.primary_leader_sector_name)).sum())
    audit={'run_id':run_id,'started_at':started,'finished_at':now(),'status':'SUCCESS','run_event':run_event,'changed_source_components':changed,**fingerprint,'requested_date':'latest',**resolution,'tdx_root':'D:/new_tdx','project_price_basis':'FORWARD_ADJUSTED','adjustment_identity':'TDX_NATIVE_AFFINE_QFQ','membership_basis':'CURRENT_TDX_MEMBERSHIP','pit_membership':False,'historical_backtest_safe':False,'normal_universe_count':len(stocks),**{f'phase{i}_generation':rs[i]['generation'] for i in range(1,6)},'phase1_hashes':{k:v for k,v in hashes.items() if k.startswith(('data/factors','data/normalized'))},'phase2_hashes':{k:v for k,v in hashes.items() if k.startswith(('data/market','data/sectors'))},'phase3_hashes':{'data/scanner/sector_scanner_daily.parquet':hashes['data/scanner/sector_scanner_daily.parquet']},'phase4_hashes':{'data/scanner/stock_scanner_daily.parquet':hashes['data/scanner/stock_scanner_daily.parquet']},'phase5_hashes':{'data/candidates/candidate_pool_daily.parquet':hashes['data/candidates/candidate_pool_daily.parquet']},'sector_counts':sector_counts,'stock_scanner_counts':stock_counts,'candidate_count':len(candidates),'priority_counts':grades,'leader_join_resolved_count':int(leaders.sum()),'leader_join_expected_count':int(leaders.sum()),'best_vs_primary_leader_same_count':same,'best_vs_primary_leader_different_count':different,'current_priority_concentration_by_pattern':pd.crosstab(candidates.effective_pattern,candidates.research_priority).to_dict(),'external_data_used':False,'index_ohlc_used':False,'tests_or_verification':'pending final directory readback','warnings':['Current membership is not historical PIT','A+/A/B/C are research priority only'],'errors':[]}
    if tdx is not None:audit['tdx_root']=str(tdx)
    audit['run_universe_snapshot']=run_universe
    (stage/'run_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2,default=str),encoding='utf8')
    atomic_write_json(stage/'RUN_UNIVERSE_SNAPSHOT.json',run_universe)
    perf.append({'step':'REPORTING','start_time':started,'end_time':now(),'elapsed_seconds':0,'rows_read':len(market)+len(sectors)+len(stocks)+len(candidates),'rows_written':len(sectors)+len(stocks)+len(candidates),'cache_reused':True})
    (stage/'PERFORMANCE_AUDIT.json').write_text(json.dumps({'cutoff_date':cutoff,'steps':perf,'no_hard_sla':True},ensure_ascii=False,indent=2),encoding='utf8')
    return rs,hashes,{'market':len(market),'sectors':len(sectors),'stocks':len(stocks),'candidates':len(candidates),'grades':grades}

def semantic_guard(stage):
    forbidden={'recommendation','buy','sell','watch','probability','win_rate','expected_return','target_price'}
    for name in ('sectors.csv','stocks.csv','candidates.csv'):
        cols={x.lower() for x in pd.read_csv(stage/name,nrows=0).columns}
        if cols&forbidden:raise RuntimeError('FORBIDDEN_REPORT_SCHEMA:'+name)
    text=(stage/'market_summary.html').read_text('utf8')
    if 'http://' in text or 'https://' in text or '<script src=' in text or '<link ' in text:raise RuntimeError('HTML_EXTERNAL_RESOURCE')
    return True

def verify_directory(root,target,cutoff):
    missing=[x for x in REQUIRED if not (target/x).exists()]
    if missing:raise RuntimeError('REPORT_FILES_MISSING:'+','.join(missing))
    d=date(int(cutoff[:4]),int(cutoff[4:6]),int(cutoff[6:]));sector=pd.read_csv(target/'sectors.csv',encoding='utf-8-sig');stock=pd.read_csv(target/'stocks.csv',encoding='utf-8-sig');cand=pd.read_csv(target/'candidates.csv',encoding='utf-8-sig')
    canonical_sector=pq.read_table(root/'data/scanner/sector_scanner_daily.parquet',filters=[('date','=',d)]).to_pandas();canonical_stock=pq.read_table(root/'data/scanner/stock_scanner_daily.parquet',filters=[('date','=',d)]).to_pandas();canonical_cand=pq.read_table(root/'data/candidates/candidate_pool_daily.parquet',filters=[('date','=',d)]).to_pandas()
    if set(sector.sector_id)!=set(canonical_sector.sector_id):raise RuntimeError('SECTOR_REPORT_MISMATCH')
    if set(stock.security_id)!=set(canonical_stock.security_id):raise RuntimeError('STOCK_REPORT_MISMATCH')
    if len(stock)!=stock.security_id.nunique():raise RuntimeError('STOCK_REPORT_DUPLICATE_ID')
    validate_universe_binding(json_read(target/'RUN_UNIVERSE_SNAPSHOT.json') if (target/'RUN_UNIVERSE_SNAPSHOT.json').exists() else {'security_ids':list(canonical_stock.security_id)},stock.security_id.tolist())
    if set(cand.security_id)!=set(canonical_cand.security_id):raise RuntimeError('CANDIDATE_ID_MISMATCH')
    a=cand.set_index('security_id');b=canonical_cand.set_index('security_id')
    if not a.research_priority.equals(b.loc[a.index].research_priority) or not pd.Series(a.priority_score-b.loc[a.index].priority_score).abs().fillna(0).le(1e-9).all():raise RuntimeError('CANDIDATE_VALUE_MISMATCH')
    for name in ('sectors.csv','stocks.csv','candidates.csv'):
        if not (target/name).read_bytes().startswith(b'\xef\xbb\xbf'):raise RuntimeError('CSV_BOM_MISSING')
    manifest_value=json_read(target/'manifest.json')
    for item in manifest_value['files']:
        if sha(target/item['filename'])!=item['sha256']:raise RuntimeError('MANIFEST_HASH_MISMATCH:'+item['filename'])
    production=json_read(target/'PRODUCTION_RECEIPT.json')
    if sha(target/'manifest.json')!=production['manifest_sha256']:raise RuntimeError('PRODUCTION_MANIFEST_MISMATCH')
    validate_input_snapshot_manifest(json_read(target/'INPUT_SNAPSHOT_MANIFEST.json'))
    semantic_guard(target);receipt_chain(root,cutoff);return {'sector_consistency':True,'stock_consistency':True,'candidate_consistency':True,'semantic_guard':True,'utf8_bom':True,'html_local':True,'manifest':True}

def manifest(stage,rows,generations):
    files=[]
    for name in ('market_summary.html','sectors.csv','stocks.csv','candidates.csv','run_audit.json','PERFORMANCE_AUDIT.json'):
        p=stage/name;files.append({'filename':name,'sha256':sha(p),'bytes':p.stat().st_size,'rows':rows.get(name.split('.')[0]),'source_generations':generations})
    if (stage/'RUN_UNIVERSE_SNAPSHOT.json').exists():
        p=stage/'RUN_UNIVERSE_SNAPSHOT.json';files.append({'filename':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'rows':None,'source_generations':generations})
    if (stage/'INPUT_SNAPSHOT_MANIFEST.json').exists():
        p=stage/'INPUT_SNAPSHOT_MANIFEST.json';files.append({'filename':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'rows':None,'source_generations':generations})
    value={'production_version':PRODUCTION_VERSION,'files':files};atomic_write_json(stage/'manifest.json',value);return sha(stage/'manifest.json')

def publish_directory(stage,target):
    target.parent.mkdir(parents=True,exist_ok=True);backup=target.with_name('.'+target.name+'.backup')
    if backup.exists():shutil.rmtree(backup)
    if target.exists():os.replace(target,backup)
    try:os.replace(stage,target)
    except Exception:
        if backup.exists() and not target.exists():os.replace(backup,target)
        raise
    if backup.exists():shutil.rmtree(backup)

class FailureRecord:
    def __init__(self, *, stage, exc, run_id, cutoff=None, exit_code=EXIT_FAILURE):
        self.stage=stage;self.exception_type=type(exc).__name__;self.message=str(exc)
        self.traceback=traceback.format_exc();self.exit_code=exit_code;self.run_id=run_id;self.cutoff=cutoff;self.timestamp=now()
    def as_dict(self):
        return {'status':'FAILED','stage':self.stage,'exception_type':self.exception_type,'message':self.message,
                'traceback':self.traceback,'exit_code':self.exit_code,'run_id':self.run_id,'cutoff':self.cutoff,'timestamp':self.timestamp}

def _safe_failure_write(root,run_id,failure,stage=None):
    errors=[]
    try:
        target=root/'logs/failures'/f'{run_id}.json';atomic_write_json(target,failure)
    except Exception as exc:errors.append(f'failure_log_write:{type(exc).__name__}:{exc}')
    if stage and stage.exists():
        try:atomic_write_json(stage/'FAILED.json',failure)
        except Exception as exc:errors.append(f'failed_generation_write:{type(exc).__name__}:{exc}')
    return errors

def _write_runtime_status(root,pointer_payload,source_revision_id):
    """Write runtime status only; formal specifications are never touched."""
    current=root/'reports/current'
    status={
        'current_production_version':PRODUCTION_VERSION,
        'current_ruleset_versions':{
            'sector_scanner':'sector-scanner-ruleset-v1.2-evidence-binding',
            'stock_scanner':'stock-scanner-ruleset-v1.0',
            'research_priority':'research-priority-ruleset-v1.1-correctness'},
        'latest_release':pointer_payload,
        'latest_revision':int(source_revision_id),
        'production_ready':True,
        'production_ready_candidate':True,
        'next_allowed_stage':'R3_V2_STRUCTURE_DEFINITION_SHADOW',
        'known_limitations':['CURRENT_TDX_MEMBERSHIP is not historical PIT','trade_status is unknown without audited local status evidence']}
    atomic_write_json(current/'CURRENT_RELEASE.json',status)
    markdown=(f"# Current Release Status\n\nProduction version: `{PRODUCTION_VERSION}`  \n"
              f"Latest cutoff: `{pointer_payload['date']}`  \nLatest release: `{pointer_payload['run_id']}`  \n"
              f"Latest source revision: `{source_revision_id}`  \nProduction ready: `TRUE`  \n"
              "Next allowed stage: `R3_V2_STRUCTURE_DEFINITION_SHADOW`\n\n"
              "Known limitations: current membership is not PIT; trade status is unknown without audited local status evidence.\n")
    atomic_write_bytes(current/'CURRENT_STATUS.md',markdown.encode('utf8'))
    return status

def _run_daily_unlocked(root,tdx,requested='latest',dry_run=False,verify_only=False,force=False,run_id=None):
    if requested!='latest':return EXIT_NOT_READY,{'status':'INPUT_NOT_READY','error':'Only --date latest is supported'}
    run_id=run_id or uuid.uuid4().hex;started=now();perf=[];log_dir=root/'logs/daily';log_dir.mkdir(parents=True,exist_ok=True);stage=None;cutoff=None;failure_stage='PRECHECK'
    try:
        tick=time.perf_counter();resolution,required=readiness(root,tdx);fingerprint=source_fingerprint(root,tdx,resolution['resolved_cutoff_date']);perf.append({'step':'PRECHECK','start_time':started,'end_time':now(),'elapsed_seconds':round(time.perf_counter()-tick,6),'rows_read':0,'rows_written':0,'cache_reused':True,'source_fingerprint_seconds':fingerprint['source_fingerprint_seconds'],'day_fingerprint_seconds':fingerprint['day_fingerprint_seconds']})
        cutoff=resolution['resolved_cutoff_date'];
        cal_dir=root/'reports/r0/run_calendars';cal_dir.mkdir(parents=True,exist_ok=True)
        calendar_path=cal_dir/f'{cutoff}_{run_id}.csv';calendar_path.write_text(pd.DataFrame(resolution['run_calendar_rows']).to_csv(index=False),encoding='utf8')
        fingerprint['calendar_generation']=resolution['calendar_generation'];fingerprint['calendar_sha256']=resolution['calendar_sha256']
        src_id=source_identity(fingerprint);comp_id=computation_identity(root);rend_id=render_identity(root)
        fingerprint['source_identity']=src_id
        pointer=root/'reports/current'/f'{cutoff}.json';pointer_value=json_read(pointer) if pointer.exists() else None
        target=Path(pointer_value['release_path']) if pointer_value and pointer_value.get('release_path') else root/'reports'/cutoff
        old_receipt=json_read(target/'PRODUCTION_RECEIPT.json') if (target/'PRODUCTION_RECEIPT.json').exists() else None
        current_identity={'source_identity':src_id,'computation_identity':comp_id,'render_identity':rend_id}
        decision=freshness_decision(target.exists(),cutoff,old_receipt,{**fingerprint,**current_identity});changed=changed_components(old_receipt,fingerprint) if decision=='SAME_CUTOFF_SOURCE_REVISION' else []
        if decision=='VERIFIED_NO_NEW_DATA' and not force:
            verification=verify_directory(root,target,cutoff)
            binding=published_release_binding(pointer_value,target,run_id)
            result={'status':'VERIFIED_NO_NEW_DATA','run_id':run_id,**binding,'input_snapshot_manifest_sha256':old_receipt.get('input_snapshot_manifest_sha256'),**resolution,**fingerprint,'changed_source_components':[],'verification':verification,'source_identity':src_id,'computation_identity':binding['published_computation_identity'],'current_computation_identity':comp_id,'render_identity':rend_id};(log_dir/f'{cutoff}_{run_id}.log').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');return EXIT_SUCCESS,result
        if verify_only:return EXIT_NOT_READY,{'status':'INPUT_NOT_READY','error':'No existing publication to verify',**resolution}
        if dry_run:return EXIT_SUCCESS,{'status':'DRY_RUN_READY','run_id':run_id,**resolution,'readiness_file_count':len(required)}
        if resolution.get('cutoff_status') in ('PARTIAL_UPDATE','INVALID_FUTURE_OUTLIER','INPUT_NOT_READY'):raise RuntimeError(resolution['cutoff_status'])
        failure_stage='PHASES';source_before=tdx_hashes(tdx)
        if decision!='SAME_CUTOFF_RENDER_REVISION':
            old_env=os.environ.get('TDX_RUN_CALENDAR');os.environ['TDX_RUN_CALENDAR']=str(calendar_path)
            try:
                run_phases(root,tdx,perf,cutoff)
            finally:
                if old_env is None:os.environ.pop('TDX_RUN_CALENDAR',None)
                else:os.environ['TDX_RUN_CALENDAR']=old_env
        source_after=tdx_hashes(tdx)
        if source_before!=source_after:raise RuntimeError('TDX_SOURCE_CHANGED_DURING_RUN')
        run_event='FORCED_SAME_CUTOFF_REBUILD' if force else decision
        stage=root/'reports/releases'/cutoff/run_id;failure_stage='RELEASE_BUILD';rs,hashes,counts=build_reports(root,stage,cutoff,run_id,started,perf,resolution,fingerprint,run_event,changed,tdx)
        # Full R1 source-stability gate runs after all phases and reporting but
        # before manifest, receipt, archive, or release-pointer publication.
        source_after_full=source_fingerprint(root,tdx,cutoff)
        source_after_full['calendar_generation']=resolution['calendar_generation'];source_after_full['calendar_sha256']=resolution['calendar_sha256']
        source_identity_after=source_identity(source_after_full)
        assert_source_stable(src_id,source_identity_after)
        source_revision_id=next_source_revision_id(root,cutoff,src_id['sha256'])
        run_universe=json_read(stage/'RUN_UNIVERSE_SNAPSHOT.json')
        input_snapshot=build_input_snapshot_manifest(run_id=run_id,cutoff_date=cutoff,
            source_revision_id=source_revision_id,source_identity=src_id,source_fingerprint=fingerprint,
            computation_identity=comp_id,render_identity=rend_id,run_universe=run_universe)
        write_immutable_manifest(stage/'INPUT_SNAPSHOT_MANIFEST.json',input_snapshot)
        generations={f'phase{i}':rs[i]['generation'] for i in range(1,6)};_failure_hook('FAIL_BEFORE_MANIFEST');manifest_hash=manifest(stage,{'sectors':counts['sectors'],'stocks':counts['stocks'],'candidates':counts['candidates']},generations);_failure_hook('FAIL_AFTER_MANIFEST')
        production={'production_version':PRODUCTION_VERSION,'run_id':run_id,'status':'SUCCESS','run_event':run_event,'cutoff_date':cutoff,'manifest_sha256':manifest_hash,**fingerprint,'source_identity':src_id,'source_identity_after':source_identity_after,'source_revision_id':source_revision_id,'input_snapshot_manifest_sha256':input_snapshot['snapshot_manifest_sha256'],'computation_identity':comp_id,'render_identity':rend_id,'changed_source_components':changed,'generations':generations,'counts':counts,'tdx_source_unchanged':True,'external_data_used':False,'index_ohlc_used':False}
        _failure_hook('FAIL_BEFORE_RECEIPT');atomic_write_json(stage/'PRODUCTION_RECEIPT.json',production);_failure_hook('FAIL_AFTER_RECEIPT')
        semantic_guard(stage);validate_release_generation(stage,expected_manifest_sha256=manifest_hash);verification=verify_directory(root,stage,cutoff);failure_stage='POINTER_SWAP'
        revision_archive=archive_source_revision(root,input_snapshot,release_id=run_id,changed_source_components=changed)
        pointer_payload=build_pointer(cutoff_date=cutoff,run_id=run_id,release_path=stage,manifest_sha256=manifest_hash,production_version=PRODUCTION_VERSION,source_identity=src_id,computation_identity=comp_id,render_identity=rend_id)
        publish_generation(stage,pointer,pointer_payload,failure_hook=_failure_hook)
        try:runtime_status=_write_runtime_status(root,pointer_payload,source_revision_id)
        except Exception as status_exc:
            # Runtime status is a non-authoritative convenience view.  It may
            # never veto a release after the atomic publication commit.
            runtime_status={'status':'STATUS_WRITE_FAILED','error':f'{type(status_exc).__name__}:{status_exc}'}
        result={'status':'SUCCESS','run_event':run_event,'run_id':run_id,'invocation_id':run_id,'published_release_id':run_id,'release_path':str(stage),**resolution,**fingerprint,'changed_source_components':changed,'report_dir':str(stage),'release_pointer':str(pointer),'source_revision_id':source_revision_id,'input_snapshot_manifest_sha256':input_snapshot['snapshot_manifest_sha256'],'computation_identity':comp_id,'render_identity':rend_id,'revision_archive':revision_archive,'runtime_status':runtime_status,'counts':counts,'generations':generations,'manifest_sha256':manifest_hash,'verification':verification,'tdx_source_unchanged':True}
        (log_dir/f'{cutoff}_{run_id}.log').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');return EXIT_SUCCESS,result
    except FileNotFoundError as exc:code=EXIT_NOT_READY;failure=FailureRecord(stage=failure_stage,exc=exc,run_id=run_id,cutoff=cutoff,exit_code=code).as_dict()
    except PublicationValidationError as exc:code=EXIT_PUBLICATION;failure=FailureRecord(stage=failure_stage,exc=exc,run_id=run_id,cutoff=cutoff,exit_code=code).as_dict()
    except RuntimeError as exc:code=EXIT_BINDING if any(x in str(exc) for x in ('HASH','GENERATION','UNIVERSE')) else (EXIT_NOT_READY if any(x in str(exc) for x in ('PARTIAL_UPDATE','INVALID_FUTURE','INPUT_NOT_READY','AMBIGUOUS_CUTOFF')) else EXIT_FAILURE);failure=FailureRecord(stage=failure_stage,exc=exc,run_id=run_id,cutoff=cutoff,exit_code=code).as_dict()
    except Exception as exc:code=EXIT_FAILURE;failure=FailureRecord(stage=failure_stage,exc=exc,run_id=run_id,cutoff=cutoff,exit_code=code).as_dict()
    write_errors=_safe_failure_write(root,run_id,failure,stage)
    if write_errors:failure['failure_log_write_errors']=write_errors
    try:(log_dir/f'failed_{run_id}.log').write_text(json.dumps(failure,ensure_ascii=False,indent=2),encoding='utf8')
    except Exception:pass
    return code,failure

def run_daily(root,tdx,requested='latest',dry_run=False,verify_only=False,force=False):
    if requested!='latest':return EXIT_NOT_READY,{'status':'INPUT_NOT_READY','error':'Only --date latest is supported'}
    root=Path(root);run_id=uuid.uuid4().hex;lock=RunLock(root/'runtime/locks/daily_production.lock',run_id=run_id)
    try:lock.acquire()
    except ActiveRunLock as exc:return EXIT_FAILURE,{'status':'FAILED','stage':'LOCK','exception_type':type(exc).__name__,'message':str(exc),'run_id':run_id,'exit_code':EXIT_FAILURE}
    try:return _run_daily_unlocked(root,tdx,requested,dry_run,verify_only,force,run_id)
    finally:lock.release()

def phase6_gate(checks):return 'PASS' if all(checks.values()) else 'BLOCKED'
