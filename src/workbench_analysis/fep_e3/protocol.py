"""Frozen scope, dual-clock chronological purge, and append-only experiment guards."""
from collections import Counter
from copy import deepcopy
import json,math,os
from pathlib import Path
from workbench_analysis.fep_e1.contracts import digest,instant

PARTITIONS=('TRAIN','INTERNAL_TUNE','CALIBRATION','OUTER_TEST')
FEATURES=('amount_ratio20','amount_ratio5','atr_ratio','clv','pos60','prior60_percentile',
    'range_ratio','ret1','ret3','ret5','ret20','slope20','slope60','vol20','vol5','vol_ratio',
    'volume_ratio20','volume_ratio5','hh_progress','ll_progress')
SCOPE=dict(observation_scope='FEP_STOCK_ENTRY_CORE',signal_type='FIRST_PREWATCH',target='ABS_RETURN_N:T1',
    horizon=1,feature_variant='CORE',evidence_origin='RECONSTRUCTED_CORRECTED')

def scope(rows):
    for r in rows:
        if any(r[k]!=v for k,v in SCOPE.items()):raise ValueError('E3_SCOPE_NOT_ADMITTED')
        if r.get('FIRST_OBSERVED') or r.get('REAL_OOS') or r.get('AS_RECORDED') or r.get('production') or r.get('shadow'):
            raise ValueError('E3_LINEAGE_OVERCLAIM')

def manifest(core,fep):
    a={r['field_id']:r for r in core['fields']};b={r['field_name']:r for r in fep['fields']};result=[]
    for name in FEATURES:
        if name not in a or name not in b:raise ValueError('E3_UNREGISTERED_FEATURE')
        field=a[name]
        result.append(dict(field_name=name,producer_contract=field['producer_contract_id'],owner_contract='CORE_FACTOR_V1',
            type=field['data_type'],unit=field['unit'],required=True,quality_rule='OBSERVED_ONLY; source owner envelopes retained',
            missingness_rule='NO_IMPUTER; exclude required missing/nonfinite/quality-unavailable rows explicitly',
            encoding_rule='TRAIN_OBSERVED_ONE_HOT_DROP_FIRST_UNKNOWN_REJECTED' if field['data_type']=='boolean' else 'FLOAT64',
            transform_rule='TRAIN_DATE_WEIGHTED_STANDARDIZATION' if field['data_type']=='float64' else 'NONE',
            accepted_core_registry_row_digest=digest(field),fep_registry_row_digest=digest(b[name]),
            fep_current_entry_path_status=b[name]['status'],
            admitted_transport='E2 externally accepted historical Core snapshot; current E1/live path is not promoted'))
    return dict(contract_id='FEP_E3_FEATURE_MANIFEST_V1',fields=result,optional_imputer='NOT_USED',
        category_unknown='FAIL_CLOSED',feature_selection='FIXED_REGISTRY_LIST_NO_OUTCOME_SELECTION')

def features(row,feature_manifest):
    actual=set(f['field_name'] for f in feature_manifest['fields'])
    if actual!=set(FEATURES):raise ValueError('E3_UNREGISTERED_FEATURE')
    values={};issues=[];snapshot=row['feature_snapshot']
    for f in feature_manifest['fields']:
        name=f['field_name'];envelope=snapshot['core_envelopes'].get(name)
        value=None if envelope is None else envelope.get('value')
        if envelope is None or envelope.get('quality_state')!='OBSERVED':issues.append(name+':QUALITY_UNAVAILABLE')
        elif value is None:issues.append(name+':REQUIRED_MISSING')
        elif f['type']=='boolean' and type(value) is not bool:issues.append(name+':SCHEMA_MISMATCH')
        elif f['type']=='float64' and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)):
            issues.append(name+':NONFINITE_OR_SCHEMA_MISMATCH')
        elif envelope.get('window_end_trade_date',row['trade_date'])>row['trade_date']:issues.append(name+':FUTURE_FEATURE')
        elif envelope.get('contract_id')!='CORE_FACTOR_V1':issues.append(name+':OWNER_CONTRACT_MISMATCH')
        values[name]=value
    return values,issues

def blocks(rows):
    end=-1;n=0
    for a,b in sorted({(r['date_ordinal'],r['label_end_ordinal']) for r in rows},key=lambda v:(v[1],v[0])):
        if a>end:n+=1;end=b
    return n

def split_discovery(rows,p,knowledge_cutoff):
    """Right-to-left minimum-support reservation; never reads outcome magnitude."""
    dates=sorted({r['trade_date'] for r in rows});d=len(dates);n=sum(r['status']=='ELIGIBLE' and not r['feature_issues'] for r in rows)
    minimum=dict(dates=max(2,math.ceil(math.sqrt(d))),rows=2*(p+1))
    minimum['blocks']=max(2,math.ceil(math.sqrt(minimum['rows'])))
    groups={};stop=len(dates)
    for part in reversed(PARTITIONS[1:]):
        selected=[];found=False
        for start in range(stop-1,-1,-1):
            selected.insert(0,dates[start]);boundary=None if stop==len(dates) else min(r['date_ordinal'] for r in rows if r['trade_date']==dates[stop])
            feasible=[r for r in rows if r['trade_date'] in selected and r['status']=='ELIGIBLE' and not r['feature_issues']
                and (boundary is None or r['label_end_ordinal']<boundary)]
            if len({r['trade_date'] for r in feasible})>=minimum['dates'] and len(feasible)>=minimum['rows'] and blocks(feasible)>=minimum['blocks']:
                groups[part]=selected;stop=start;found=True;break
        if not found:raise ValueError('E3_FOUR_PART_SPLIT_BLOCKED')
    groups['TRAIN']=dates[:stop]
    eligible=[r for r in rows if r['trade_date'] in groups['TRAIN'] and r['status']=='ELIGIBLE' and not r['feature_issues']]
    if len(groups['TRAIN'])<2*minimum['dates'] or len(eligible)<4*(p+1):raise ValueError('E3_TRAIN_SUPPORT_BLOCKED')
    return dict(rule='RIGHT_TO_LEFT_MINIMUM_SUPPORT_CHRONOLOGICAL_V1',groups=groups,minimum=minimum,
        train_minimum=dict(dates=2*minimum['dates'],rows=4*(p+1)),support_heuristic_only=True,
        derivation='Evaluation rows >=2*(maximum encoded feature dimension+intercept); TRAIN rows >=4*(dimension+intercept). Dates >=ceil(sqrt(available date groups)), TRAIN dates twice that; independent blocks >=ceil(sqrt(minimum evaluation rows)). Feasibility heuristic, not statistical power.',
        outcome_performance_consumed=False,knowledge_cutoff=knowledge_cutoff)

def validate_dates(groups,rule):
    if rule!='RIGHT_TO_LEFT_MINIMUM_SUPPORT_CHRONOLOGICAL_V1':raise ValueError('E3_RANDOM_SPLIT_REJECTED')
    seen=set();previous=None
    for part in PARTITIONS:
        dates=groups[part]
        if not dates or set(dates)&seen or (previous is not None and min(dates)<=previous):raise ValueError('E3_DATE_SPLIT_LEAKAGE')
        seen.update(dates);previous=max(dates)

def leakage(row,boundary,cutoff,shared_episodes=()):
    reasons=[]
    if boundary is not None and row['label_end_ordinal']>=boundary:reasons.append('LABEL_EVENT_END_CROSSES_BOUNDARY')
    # Actual engineering receipt times are checked against the fixed pre-phase
    # knowledge snapshot; event timestamps are checked against event boundaries.
    # This grants no historical first availability or PIT interpretation.
    for field in ('source_fact_available_at','label_revision_available_at','label_training_mature_at'):
        if instant(row[field])>instant(cutoff):reasons.append(field.upper()+'_AFTER_FROZEN_KNOWLEDGE_CUTOFF')
    if row['feature_snapshot']['max_feature_source_trade_date']>row['trade_date']:reasons.append('FUTURE_FEATURE_SOURCE')
    if (row['entity_id'],row['episode_id']) in shared_episodes and boundary is not None and row['episode_end']>=boundary:
        reasons.append('SHARED_OVERLAPPING_EPISODE_BOUNDARY')
    return reasons

def purge(rows,discovery):
    groups=discovery['groups'];validate_dates(groups,discovery['rule']);partition={d:p for p,ds in groups.items() for d in ds}
    retained={p:[] for p in PARTITIONS};ledger=[]
    for r in rows:
        part=partition[r['trade_date']];idx=PARTITIONS.index(part)
        later=[x for x in rows if PARTITIONS.index(partition[x['trade_date']])>idx]
        boundary=min((x['date_ordinal'] for x in later),default=None)
        shared={(x['entity_id'],x['episode_id']) for x in later}
        reasons=leakage(r,boundary,discovery['knowledge_cutoff'],shared)
        if r['status']!='ELIGIBLE':reasons.append('E2_LABEL_'+r['status'])
        reasons.extend(r['feature_issues'])
        if not reasons:retained[part].append(r)
        ledger.append(dict(observation_id=r['observation_id'],trade_date=r['trade_date'],partition=part,
            entity_id=r['entity_id'],episode_id=r['episode_id'],label_event_end=r['label_end_ordinal'],
            episode_interval=[r['episode_start'],r['episode_end']],next_boundary_ordinal=boundary,
            actual_availability={k:r[k] for k in ('source_fact_available_at','label_revision_available_at','label_training_mature_at')},
            episode_interval_crosses_boundary=boundary is not None and r['episode_end']>=boundary,
            shared_episode_in_later_partition=(r['entity_id'],r['episode_id']) in shared,
            action='RETAIN' if not reasons else 'EXCLUDE',reasons=reasons))
    for part in PARTITIONS:
        target=discovery['train_minimum'] if part=='TRAIN' else discovery['minimum']
        if len(retained[part])<target['rows'] or len({r['trade_date'] for r in retained[part]})<target['dates'] or blocks(retained[part])<target.get('blocks',discovery['minimum']['blocks']):
            raise ValueError('E3_POST_PURGE_SUPPORT_BLOCKED:'+part)
    return retained,ledger

def fit_authority(partition,ids,allowed_ids,object_type):
    if partition!='TRAIN' or set(ids)!=set(allowed_ids):raise ValueError('E3_NON_TRAIN_'+object_type.upper()+'_FIT')

def tuning_authority(partition):
    if partition!='INTERNAL_TUNE':raise ValueError('E3_OUTER_OR_CALIBRATION_TUNING_REJECTED')

def rearrange(raw,rule):
    if rule!='PRE_REGISTERED_INCREASING_REARRANGEMENT_V1':raise ValueError('E3_SILENT_QUANTILE_SORT_REJECTED')
    return sorted(raw)

def calibration_role(role):
    if role!='NOT_APPLICABLE_REGRESSION':raise ValueError('E3_PROBABILITY_CALIBRATION_REJECTED')

def same_population(model_ids,baseline_ids):
    if list(model_ids)!=list(baseline_ids):raise ValueError('E3_OUTER_POPULATION_MISMATCH')

def immutable(directory,kind,payload):
    directory=Path(directory).resolve()
    if not str(directory).lower().startswith(('e:\\','f:\\')):raise ValueError('E3_ENGINEERING_STORAGE_REQUIRED')
    clean={k:v for k,v in payload.items() if k not in ('logical_digest','artifact_id','artifact_type','kind')}
    semantic=dict(artifact_type=kind,**{k:v for k,v in clean.items() if k not in ('created_at','run_id')});sha=digest(semantic)
    artifact=dict(clean,artifact_type=kind,logical_digest=sha,artifact_id='FEP_E3:'+sha,kind=kind)
    directory.mkdir(parents=True,exist_ok=True);path=directory/(kind+'_'+sha+'.json')
    raw=(json.dumps(artifact,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    tmp=path.with_suffix('.tmp')
    with tmp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    try:
        try:os.link(tmp,path)
        except FileExistsError:
            old=json.loads(path.read_bytes())
            if {k:v for k,v in old.items() if k not in ('created_at','run_id')}!={k:v for k,v in artifact.items() if k not in ('created_at','run_id')}:
                raise ValueError('E3_REGISTRY_MUTATION')
    finally:tmp.unlink()
    return artifact,path

def ledger_integrity(expected,actual):
    if list(expected)!=list(actual):raise ValueError('E3_TRIAL_DELETE_OR_REORDER_REJECTED')

def open_outer(path,dependencies):
    path=Path(path)
    if path.exists():raise ValueError('E3_OUTER_ALREADY_OPEN_NEW_LINEAGE_REQUIRED')
    tmp=path.with_suffix('.tmp')
    try:
        with tmp.open('x',encoding='utf-8',newline='\n') as f:json.dump(dependencies,f,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
        os.link(tmp,path)
    except FileExistsError:raise ValueError('E3_OUTER_ALREADY_OPEN_NEW_LINEAGE_REQUIRED')
    finally:
        if tmp.exists():tmp.unlink()
