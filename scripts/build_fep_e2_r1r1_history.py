"""Freeze and reconstruct the maximal real-source historical engineering window."""
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime,timezone
import gzip,hashlib,json,os
from pathlib import Path
import subprocess,sys,time
import duckdb
from workbench_analysis.fep_e1.contracts import atomic_json,digest
from workbench_analysis.fep_e1.feature_owner import verify_file
from workbench_analysis.fep_e2.historical_dataset import feature_worker,freeze_window,LINEAGE,read_gzip,write_gzip

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/fep_e2_r1r1'
TEMP=Path('E:/codex_tmp/fep_e2_r1r1_history')


def now():return datetime.now(timezone.utc).isoformat()


def binding(path):
    path=Path(path);path=path if path.is_absolute() else ROOT/path
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=h.hexdigest())


def prepare():
    REPORT.mkdir(parents=True,exist_ok=True);TEMP.mkdir(parents=True,exist_ok=True)
    tmp=REPORT/'.gitattributes.tmp';tmp.write_bytes(b'* -text\n');tmp.replace(REPORT/'.gitattributes')
    docs=['V4_FEP_EXECUTION_MASTER_V4_15E2_R1R1_REPAIR_20261005.md',
          'V4_15E2_R1R1_HISTORICAL_DATASET_AND_SCOPED_POLICY_REPAIR_TASK_20261005.md',
          'V4_15E2_R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261005.md']
    for name in docs:
        tmp=REPORT/(name+'.tmp');tmp.write_bytes((Path('D:/Users/lps/Desktop/阶段任务')/name).read_bytes());tmp.replace(REPORT/name)
    owner=json.loads((ROOT/'config/fep_feature_owner_contract_v1.json').read_bytes())
    sources={k:owner[k] for k in ('calendar','universe','adjustment_identity')}
    for key,path in [('v4_15_head','data/v4/V4_15_ACCEPTED_HEAD.json'),('data_head','data/v4/V4_DATA_ACCEPTED_HEAD.json'),
        ('identity','data/v4/source_evidence/dm01_a01_r3/chain_inputs_r1/identity_projection_dc4b72168585944ca0925e806ebaff0a7785d180a85802e320c4973c1cc898f8.json'),
        ('status','data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz')]:sources[key]=binding(path)
    for b in sources.values():verify_file(ROOT,b)
    sessions=json.loads((ROOT/sources['calendar']['path']).read_bytes())['session_dates']
    numerical=duckdb.connect().execute('select min(trade_date),max(trade_date),count(*),count(distinct trade_date) from read_parquet(?)',
                 [str(ROOT/sources['adjustment_identity']['path'])]).fetchone()
    assert sessions[0].replace('-','')==str(numerical[0]) and sessions[-1].replace('-','')==str(numerical[1]) and len(sessions)==numerical[3]
    runtimes=['src/v4/factors/core.py','src/v4/factors/relative.py','src/v4/profile_primitives.py','src/v4/profile_core.py',
        'src/v4/base_seed.py','src/v4/stock_prewatch.py','src/v4/confirmation.py','src/v4/confirmation_candidate_r4.py',
        'src/v4/confirmation_d2_candidate_r5.py','src/v4/research_state.py','src/v4/target_fact_producers_r4.py',
        'src/workbench_analysis/v4_15_radar_cohort.py','src/workbench_analysis/v4_15_settlement.py']
    contract=dict(contract_id='FEP_E2_HISTORICAL_DATASET_V1',version='1.0.0',scope='FEP_STOCK_ENTRY_CORE',
        source_bindings=sources,owner_runtime_bindings=[binding(p) for p in runtimes],
        parameter_bindings=[binding(p) for p in ['config/v4_03_parameter_set_v1.json','config/v4_04_parameter_set_v1.json',
            'config/v4_07_parameter_set_v1.json','config/v4_09_parameter_set_v1.json','config/v4_10_parameter_set_r1_2.json',
            'config/v4_11_confirmation_parameter_set_v1.json','config/research_attention_v3.yaml']],
        target='ABS_RETURN_N:T1',target_kind='CONTINUOUS',horizon=1,feature_contract_id='FEP_E2_HISTORICAL_CORE_FEATURE_V1',
        label_quality_policy='ENGINEERING_HISTORICAL_REPLAY',lineage=LINEAGE,
        unavailable_dimensions=['sector','regime'],unavailable_fact_policy='UNKNOWN_NEVER_IMPUTE',
        reconstructed_adjustment_limitation='Final accepted corrected affine coordinate; historical first availability NOT_PROVEN',
        membership_limitation='Accepted R6.2 dated reconstructed universe; no historical AS_RECORDED claim')
    atomic_json(ROOT/'config/fep_e2_historical_dataset_contract_v1.json',contract)
    discovery=dict(source_bindings=sources,sessions=sessions,warmup_sessions=250,maximum_enabled_horizon=1,
        owner_capability='Accepted 250-actual-bar profile warmup, Core/Seed/Prewatch/confirmation/reducer business owners; engineering adapters only')
    window=freeze_window(discovery)
    atomic_json(REPORT/'ENTRY_BASELINE.json',dict(actual_head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),
        execution_baseline='87e5b36b32aafd73101f21225703228353d12140',maintenance_only_successor='6aaff0b',entered_at=now(),
        stage_contract=contract['contract_id'],expected_acceptance='CAPABILITY_SCOPED_OR_BLOCKED',next='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT',
        authority=[binding(REPORT/name) for name in docs]))
    atomic_json(REPORT/'HISTORICAL_WINDOW_DISCOVERY.json',dict(discovery=discovery,source_summary=list(numerical),
        rule='Maximal contiguous coverage after accepted 250-bar warmup; retain right-edge censored targets',
        performance_inputs_read=False,settlement_started=False,statistics_started=False))
    atomic_json(REPORT/'HISTORICAL_WINDOW_FREEZE.json',dict(window=window,discovery_digest=digest(discovery),
        frozen_at=now(),settlement_started=False,statistics_started=False))
    heads=json.loads((ROOT/'reports/fep_e2_r1/PROTECTED_STATE_READBACK.json').read_bytes())['heads']
    atomic_json(REPORT/'R1_PASS_KEEP_READBACK.json',dict(status='PASS_KEEP',heads=heads,
        r1_policy=binding('config/fep_e2_support_policy_v1.json'),r1_diagnostic=binding('reports/fep_e2_r1/DIAGNOSTIC_BASELINE.json'),
        migrations=[binding(p) for p in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('0[23][0-9]_*.sql')) if 28<=int(p.name[:3])<=31],
        feature_owner=binding('config/fep_feature_owner_contract_v1.json'),three_time=binding('config/v4_15_fep_label_time_authority_v1.json')))
    return contract,discovery,window


def context():
    contract=json.loads((ROOT/'config/fep_e2_historical_dataset_contract_v1.json').read_bytes())
    for ref in contract['source_bindings'].values():verify_file(ROOT,ref)
    discovery=json.loads((REPORT/'HISTORICAL_WINDOW_DISCOVERY.json').read_bytes())['discovery']
    window=json.loads((REPORT/'HISTORICAL_WINDOW_FREEZE.json').read_bytes())['window']
    sessions=discovery['sessions'];index={d:i for i,d in enumerate(sessions)}
    members=defaultdict(set);statuses=defaultdict(dict)
    with gzip.open(ROOT/contract['source_bindings']['universe']['path'],'rt',encoding='utf-8') as f:
        for line in f:
            row=json.loads(line);members[row['security_id']].add(index[row['trade_date']])
    with gzip.open(ROOT/contract['source_bindings']['status']['path'],'rt',encoding='utf-8') as f:
        for line in f:
            row=json.loads(line)
            if row['status']!='ACTUAL_TRADED':statuses[row['security_id']][index[row['trade_date']]]=row['status']
    return contract,sessions,members,statuses,window


def price_groups(contract):
    connection=duckdb.connect();connection.execute("set memory_limit='2GB'")
    connection.execute('set threads=2');connection.execute('set preserve_insertion_order=false')
    connection.execute('set temp_directory=?',[str(TEMP/'duckdb')])
    cur=connection.execute('select * from read_parquet(?) order by canonical_security_id,trade_date',
                           [str(ROOT/contract['source_bindings']['adjustment_identity']['path'])])
    columns=[d[0] for d in cur.description];sid=None;rows=[]
    while batch:=cur.fetchmany(2048):
        for values in batch:
            row=dict(zip(columns,values));current=row['canonical_security_id']
            # Preserve exact decimal evidence as strings; price/amount owners accept these.
            row={k:(str(v) if hasattr(v,'as_tuple') else v) for k,v in row.items()}
            if sid is not None and current!=sid:yield sid,rows;rows=[]
            sid=current;rows.append(row)
    if sid is not None:yield sid,rows


def features():
    contract,sessions,members,statuses,window=context();output=TEMP/'features';output.mkdir(exist_ok=True)
    receipts=[];pending=set();started=time.monotonic();total=0
    with ProcessPoolExecutor(max_workers=8) as pool:
        for sid,rows in price_groups(contract):
            cached=output/(sid+'.jsonl.gz')
            if cached.exists():
                records=list(read_gzip(cached))
                if records and records[-1]['date']==sessions[-1] and records[0]['ordinal']==window['start_ordinal']-23:
                    receipts.append(dict(entity_id=sid,rows=len(records),sha256=hashlib.sha256(cached.read_bytes()).hexdigest()))
                    if len(receipts)%500==0:print('FEATURE_CACHE_VERIFIED',len(receipts),flush=True)
                    continue
            job=(sid,rows,sessions,list(members[sid]),statuses[sid],window['start_ordinal'],str(output))
            pending.add(pool.submit(feature_worker,job))
            if len(pending)>=16:
                done,pending=wait(pending,return_when=FIRST_COMPLETED)
                for future in done:receipts.append(future.result());total+=1
                if total%100<8:print('FEATURES',total,'entities elapsed',round(time.monotonic()-started),'seconds',flush=True)
        for future in pending:receipts.append(future.result())
    atomic_json(REPORT/'HISTORICAL_FEATURE_SCAN.json',dict(status='PASS',entities=len(receipts),
        date_rows=sum(r['rows'] for r in receipts),receipts=sorted(receipts,key=lambda r:r['entity_id']),
        sealed_at=now(),no_outcomes_read=True,cache_root=str(output)))


def ranks():
    import numpy as np
    from workbench_analysis.fep_e2.historical_dataset import rank_worker
    contract,sessions,members,statuses,window=context()
    entities=sorted(p.stem.removesuffix('.jsonl') for p in (TEMP/'features').glob('*.jsonl.gz'))
    returns=np.full((2,len(entities),len(sessions)),np.nan)
    for index,sid in enumerate(entities):
        for r in read_gzip(TEMP/'features'/(sid+'.jsonl.gz')):
            for n,h in enumerate((5,20)):
                value=r['values'].get('ret'+str(h))
                if value is not None:returns[n,index,r['ordinal']]=value
    result=np.full_like(returns,np.nan)
    positions={sid:j for j,sid in enumerate(entities)};pending=set();count=0;cross_section_receipts=[]
    def save(done):
        nonlocal count
        for f in done:
            n,i,scores,coverage=f.result()
            cross_section_receipts.append(dict(horizon=(5,20)[n],trade_date=sessions[i],ordinal=i,
                scores_digest=digest(scores),coverage=coverage,universe='ACCEPTED_DATED_RECONSTRUCTED',
                source_feature_scan_digest=binding(REPORT/'HISTORICAL_FEATURE_SCAN.json')['sha256']))
            for sid,value in scores.items():
                if value is not None:result[n,positions[sid],i]=value
            count+=1
        if count%50<12:print('RANK',count,'cross-sections',flush=True)
    with ProcessPoolExecutor(max_workers=12) as pool:
        for i in range(window['start_ordinal']-23,len(sessions)):
            universe=[sid for sid in entities if i in members[sid]]
            for n in range(2):
                mapping={sid:(float(returns[n,j,i]) if np.isfinite(returns[n,j,i]) else None) for j,sid in enumerate(entities)}
                pending.add(pool.submit(rank_worker,(n,i,mapping,universe)))
                if len(pending)>=24:
                    done,pending=wait(pending,return_when=FIRST_COMPLETED);save(done)
        save(pending)
    np.save(TEMP/'ranks.tmp.npy',result);(TEMP/'ranks.tmp.npy').replace(TEMP/'ranks.npy')
    atomic_json(TEMP/'rank_index.json',dict(entities=entities,calendar=sessions,owner='RPS_MIDRANK_V1'))
    atomic_json(REPORT/'RPS_CROSS_SECTION_RECEIPTS.json',dict(rows=sorted(cross_section_receipts,key=lambda r:(r['trade_date'],r['horizon'])),
        feature_scan=binding(REPORT/'HISTORICAL_FEATURE_SCAN.json'),source_contract=binding('config/fep_e2_historical_dataset_contract_v1.json')))
    atomic_json(REPORT/'HISTORICAL_RPS_GATE.json',dict(status='PASS',owner=binding('src/v4/factors/core.py'),
        rows=len(entities)*len(sessions),algorithm='rps_midrank',current_membership_used=False,
        sha256=hashlib.sha256((TEMP/'ranks.npy').read_bytes()).hexdigest(),no_outcomes_read=True))


def entries(limit=None):
    from workbench_analysis.fep_e2.historical_owners import entry_worker
    contract,sessions,members,statuses,window=context();pending=set();receipts=[];started=time.monotonic()
    phase=REPORT/('ENTRY_SAMPLE_PHASE_START.json' if limit else 'ENTRY_PHASE_START.json')
    if not phase.exists():atomic_json(phase,dict(started_at=now(),window=binding(REPORT/'HISTORICAL_WINDOW_FREEZE.json'),
        rank=binding(REPORT/'HISTORICAL_RPS_GATE.json'),source_contract=binding('config/fep_e2_historical_dataset_contract_v1.json')))
    cutoff=json.loads(phase.read_bytes())['started_at']
    with ProcessPoolExecutor(max_workers=12) as pool:
        for n,(sid,raw) in enumerate(price_groups(contract)):
            if limit is not None and n>=limit:break
            target=REPORT/'sample' if limit else REPORT
            scan=target/'state_scan'/(sid+'.jsonl.gz');pop=target/'population'/(sid+'.jsonl.gz');bundle=target/'owner_records'/(sid+'.jsonl.gz')
            if not limit and all(p.exists() for p in (scan,pop,bundle)):
                states=list(read_gzip(scan));observations=list(read_gzip(pop))
                if (len(states)==len(sessions)-window['start_ordinal'] and states[0]['date_ordinal']==window['start_ordinal']
                    and states[-1]['date_ordinal']==len(sessions)-1 and all('upstream_derivation' in r for r in states)):
                    from collections import Counter
                    receipts.append(dict(entity_id=sid,rows=len(observations),state_counts=dict(Counter(r['eligibility'] for r in states)),
                        bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),population_sha256=hashlib.sha256(pop.read_bytes()).hexdigest(),
                        state_scan_sha256=hashlib.sha256(scan.read_bytes()).hexdigest(),state_rows=len(states)))
                    continue
            job=(sid,raw,sessions,list(members[sid]),statuses[sid],window['start_ordinal'],str(TEMP),str(REPORT/'sample' if limit else REPORT),
                 list(contract['source_bindings'].values()),cutoff)
            pending.add(pool.submit(entry_worker,job))
            if len(pending)>=24:
                done,pending=wait(pending,return_when=FIRST_COMPLETED)
                for future in done:receipts.append(future.result())
                if len(receipts)%50<8:print('ENTRY',len(receipts),'entities elapsed',round(time.monotonic()-started),flush=True)
        for future in pending:receipts.append(future.result())
    atomic_json(REPORT/('ENTRY_SAMPLE.json' if limit else 'HISTORICAL_OBSERVATION_POPULATION.json'),
        dict(status='PASS_COMPLETE_OWNER_REPLAY' if not limit else 'SAMPLE_NOT_ACCEPTANCE',entities=len(receipts),
            rows=sum(r['rows'] for r in receipts),state_rows=sum(r['state_rows'] for r in receipts),
            receipts=sorted(receipts,key=lambda r:r['entity_id']),lineage=LINEAGE,source_bindings=contract['source_bindings'],
            full_population=limit is None,no_top_k=True,no_focus=True,no_performance_selection=True,labels_started=False,sealed_at=now()))


def labels():
    from workbench_analysis.fep_e2.historical_labels import label_worker
    contract,sessions,members,statuses,window=context();receipts=[];pending=set()
    population=json.loads((REPORT/'HISTORICAL_OBSERVATION_POPULATION.json').read_bytes())
    if not population['full_population']:raise ValueError('E2_INCOMPLETE_POPULATION')
    phase=REPORT/'LABEL_PHASE_START.json'
    if not phase.exists():atomic_json(phase,dict(started_at=now(),population=binding(REPORT/'HISTORICAL_OBSERVATION_POPULATION.json'),
        window=binding(REPORT/'HISTORICAL_WINDOW_FREEZE.json'),statistics_started=False))
    knowledge=json.loads(phase.read_bytes())['started_at']
    with ProcessPoolExecutor(max_workers=8) as pool:
        for sid,raw in price_groups(contract):
            job=(sid,raw,sessions,list(members[sid]),statuses[sid],str(REPORT),contract['source_bindings']['adjustment_identity'],knowledge)
            pending.add(pool.submit(label_worker,job))
            if len(pending)>=16:
                done,pending=wait(pending,return_when=FIRST_COMPLETED)
                for f in done:receipts.append(f.result())
        for f in pending:receipts.append(f.result())
    atomic_json(REPORT/'V4_15_HISTORICAL_LABEL_ADAPTER_GATE.json',dict(status='PASS',rows=sum(r['rows'] for r in receipts),
        eligible=sum(r['eligible'] for r in receipts),receipts=sorted(receipts,key=lambda r:r['entity_id']),
        owner_runtime=binding('src/workbench_analysis/v4_15_settlement.py'),owner_head=contract['source_bindings']['v4_15_head'],
        arithmetic_reimplemented=False,engineering_only=True,real_time_authority_unchanged=True,sealed_at=now()))


if __name__=='__main__':
    if sys.argv[1:] == ['prepare']:prepare()
    elif sys.argv[1:] == ['features']:features()
    elif sys.argv[1:] == ['ranks']:ranks()
    elif sys.argv[1:] == ['entries']:entries()
    elif sys.argv[1:] == ['entry-sample']:entries(1)
    elif sys.argv[1:] == ['labels']:labels()
