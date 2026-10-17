"""Real dated source admission, frozen algorithm replay and successor sealing."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import hashlib,json
from .operational_daily_storage_v1 import atomic_json
from .r43_owner_replay import checked,ref,gzrows,gzwrite,load
from .market_source_acquisition import official_sessions,is_stock_code
from .r43_operational_sources import date_valid_identity
from .operational_owner_adapter_v1 import replay
from .operational_daily_periods_v1 import derive_periods
from .operational_successor_v1 import CONTRACT
from .tdx_official_daily_source import _atomic_write,sha256_file

BASE='docs/evidence/r4_3_four_session_closeout_20261009'
ACQUISITION='docs/evidence/source_acquisition_r4_20261009/capture/acquisition.json'


def prepare(root,freeze_binding,*,replay_current=False):
    root=Path(root).resolve();freeze=load(checked(root,freeze_binding));day=freeze['target_session']
    parent=load(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    sessions=official_sessions(root);previous=parent['accepted_trade_date']
    if not replay_current and sessions.index(day)!=sessions.index(previous)+1:
        raise ValueError('OWNER_NEXT_OFFICIAL_SESSION_REQUIRED')
    if replay_current and day!=previous:raise ValueError('CURRENT_REPLAY_TARGET_REQUIRED')
    dates=parent.get('published_sessions',parent['dates'])+[day] if day>previous else parent['dates']
    required=sorted(set(dates)|{sessions[sessions.index(d)-k] for d in dates for k in (1,3,4,5)})
    identity_binding=load(checked(root,parent['owners'][previous]['lifecycle']))['identity']
    identities=load(checked(root,identity_binding))['rows'];bycode={r['source_security_key'].upper():r for r in identities}
    bao=freeze['normalized']['daily']['rows'];barsdoc=load(Path(freeze['tdx']['path']));amount_differences=[]
    if sha256_file(Path(freeze['tdx']['path']))!=freeze['tdx']['sha256']:raise ValueError('NATIVE_TARGET_DIGEST_MISMATCH')
    bars={r['source_security_key']:r for r in barsdoc['target_bars']};observations=[];errors=[]
    for row in bao:
        code=row['code'].upper();ident=bycode.get(code);bar=bars.get(code)
        if not date_valid_identity(ident,day):errors.append(dict(code=code,reason='DATED_CANONICAL_IDENTITY_REQUIRED'));continue
        state='ACTUAL_TRADED' if bar else 'SUSPENDED' if row['tradestatus']=='0' else 'DATA_GAP'
        if state=='DATA_GAP' or (bar and row['tradestatus']!='1'):errors.append(dict(code=code,reason='BAR_STATUS_CONFLICT'))
        if bar:
            for field in ('open','high','low','close','volume'):
                if float(row[field])!=float(bar[field]):errors.append(dict(code=code,field=field,reason='EXACT_NATIVE_BAOSTOCK_MISMATCH'))
            if float(row['amount'])!=float(bar['amount']):
                amount_differences.append(dict(code=code,native_amount=bar['amount'],baostock_amount=row['amount'],
                    handling='NATIVE_PRIMARY_UNCHANGED; CROSS_SOURCE_REPRESENTATION_AUDIT_OPEN',tolerance_applied=False))
        observations.append(dict(security_id=ident['security_id'],source_security_key=code,trade_date=day,status=state))
    if errors:raise ValueError('DATED_SOURCE_RECONCILIATION_FAILED:'+json.dumps(errors[:10]))
    if not observations:raise ValueError('DATED_SOURCE_EMPTY')
    snapshot=load(checked(root,parent['membership_snapshot']))
    current_gbbq=Path('D:/new_tdx/T0002/hq_cache/gbbq')
    before=current_gbbq.stat();blob=current_gbbq.read_bytes();after=current_gbbq.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('GBBQ_CHANGED_DURING_CAPTURE')
    member_source_hashes={source['address']:sha256_file(Path(source['address'])) for source in snapshot['sources']}
    generation=dict(contract_id='DYNAMIC_DAILY_OWNER_GENERATION_SCOPE_V1',source_freeze=freeze_binding['sha256'],
        parent_head=sha256_file(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),identity=identity_binding['sha256'],
        gbbq=hashlib.sha256(blob).hexdigest(),member_sources=member_source_hashes,
        producer={name:sha256_file(root/'src/workbench_analysis'/name) for name in ('operational_daily_owner_v1.py','operational_owner_adapter_v1.py')})
    generation_key=hashlib.sha256(json.dumps(generation,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    folder=root/'data/v4/dynamic_daily_owners'/day/generation_key
    folder.mkdir(parents=True,exist_ok=True)
    scope_path=folder/'GENERATION_SCOPE.json'
    if scope_path.is_file() and load(scope_path)!=generation:raise ValueError('OWNER_GENERATION_SCOPE_COLLISION')
    if not scope_path.is_file():atomic_json(root,scope_path,generation)
    phase_path=root/'reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json'
    phase=load(phase_path)
    if phase['phase0_status'] not in ('FULL_PASS','DEGRADED_PASS'):raise ValueError('PHASE0_GATE_REQUIRED')
    atomic_json(root,folder/'STAGE_ENTRY.json',dict(contract_id='DYNAMIC_DAILY_OWNER_ENTRY_V1',
        phase0_status=phase['phase0_status'],phase0_evidence=ref(root,phase_path),
        upgrade_document=ref(root,root/'docs/upgrade/DYNAMIC_DAILY_DD03_SUCCESSOR_V1_20261009.md'),
        task_contract=ref(root,root/'docs/evidence/dynamic_daily_20261009/TASK_CONTRACT_V1_1.md'),
        acceptance='IN_PROGRESS',target_session=day,source_freeze=freeze_binding,
        next_stage='UNCHANGED_KERNEL_REPLAY_AND_FULL_NUMERIC_DAY_QA'))
    atomic_json(root,folder/'AMOUNT_CROSS_SOURCE_AUDIT.json',dict(contract_id='DD_A05_DATED_AMOUNT_AUDIT_V1',
        target_session=day,scope='Every matched native/BaoStock amount row',evidence=freeze_binding,
        differences=amount_differences,acceptance='INDEPENDENT_NOT_GRANTED',native_primary_replaced=False,
        next_stage='SEPARATE_CROSS_CUTTING_AMOUNT_AUDIT'))
    # A prior accepted GBBQ cannot substitute for a changed current local action source.
    oldcore=load(root/BASE/'owner_v3/CORE_REPLAY.json')['owners'][0]
    oldgbbq=oldcore['sources']['gbbq']
    gb=folder/'sources/gbbq';_atomic_write(gb,blob,tdx_root=Path('D:/new_tdx'))
    from tdx.gbbq_reader import read_gbbq
    events=read_gbbq(gb)
    if hashlib.sha256(blob).hexdigest()!=oldgbbq['sha256']:
        # Revision is captured immutably; it cannot borrow the old algorithm/source QA.
        atomic_json(root,folder/'ACTION_QA_REQUIRED.json',dict(old=oldgbbq,new=ref(root,gb),records=len(events),target_session=day))
        # The unchanged affine oracle below must accept every rebuilt target
        # window before a revision becomes derived-ready.
    membership_changed=False
    for source in snapshot['sources']:
        address=Path(source['address'])
        if sha256_file(address)!=source['sha256']:
            membership_changed=True
    if membership_changed:
        from .tdx_member_retro_r43 import normalize_member_rows,digest as member_digest
        from sector.membership_snapshot import build_snapshot
        observed=datetime.now(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Shanghai')).isoformat()
        sources=[];parse=folder/'latest_member_parse'
        for source in snapshot['sources']:
            address=Path(source['address']);before=address.stat();data=address.read_bytes();after=address.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('MEMBER_SOURCE_CHANGED_DURING_CAPTURE')
            if hashlib.sha256(data).hexdigest()!=member_source_hashes[source['address']]:raise ValueError('MEMBER_GENERATION_SCOPE_MOVED')
            frozen=folder/'latest_member_raw'/hashlib.sha256(data).hexdigest()/address.name
            _atomic_write(frozen,data,tdx_root=Path('D:/new_tdx'))
            _atomic_write(parse/'T0002/hq_cache'/address.name,data,tdx_root=Path('D:/new_tdx'))
            sources.append(dict(address=str(address),observed_at=observed,**ref(root,frozen)))
        frame,_=build_snapshot(parse,observed)
        rows=normalize_member_rows(frame.to_dict('records'),bycode)
        digest=member_digest(rows)
        snapshot=dict(snapshot,membership_snapshot_id='TDX_OPERATIONAL_MEMBER_SNAPSHOT_V2_'+digest,
            membership_observed_at=observed,member_set_asof=observed,member_digest=digest,sources=sources,
            memberships=gzwrite(root,folder/'latest_member_S.jsonl.gz',rows),identity_source=identity_binding,
            relation_count=len(rows),mapped_count=sum(r['security_id'] is not None for r in rows),
            unmapped_count=sum(r['security_id'] is None for r in rows))
    atomic_json(root,folder/'MEMBER_SNAPSHOT_S.json',snapshot)
    acquisition=load(root/ACQUISITION);queries=list(acquisition['queries'])
    daily_path=folder/'sources/daily.json';atomic_json(root,daily_path,dict(rows=bao,observed_at=freeze['observed_at']))
    queries=[q for q in queries if not (q.get('method')=='query_daily_history_k_AStock' and q['params'].get('date',q['params'].get('day'))==day)]
    queries.append(dict(method='query_daily_history_k_AStock',params={'date':day},path=str(daily_path),
                        requested_at=freeze['observed_at'],received_at=freeze['observed_at']))
    for prior_day,registry in parent.get('source_registry',{}).items():
        if prior_day==day or 'freeze' not in registry:continue
        prior_freeze=load(checked(root,registry['freeze']))
        prior_daily=folder/'sources/prior_daily'/ (prior_day+'.json')
        atomic_json(root,prior_daily,dict(rows=prior_freeze['normalized']['daily']['rows'],source_freeze=registry['freeze']))
        queries=[q for q in queries if not(q.get('method')=='query_daily_history_k_AStock' and q['params'].get('date',q['params'].get('day'))==prior_day)]
        queries.append(dict(method='query_daily_history_k_AStock',params={'date':prior_day},path=str(prior_daily),
            requested_at=prior_freeze['observed_at'],received_at=prior_freeze['observed_at']))
    present={q['params'].get('date',q['params'].get('day')) for q in queries if q.get('method')=='query_all_stock' and q.get('path')}
    missing=[d for d in required if d not in present]
    if missing:
        from .baostock_supplemental import RequestBudget
        from .operational_baostock_client_v1 import BaoStockClient
        from .operational_runtime_acceptance_v2 import load as load_runtime_acceptance_manifest
        manifest=load_runtime_acceptance_manifest(checked(root,freeze['runtime_manifest']),project_root=root)
        with BaoStockClient(RequestBudget(root/'reports/v4_baostock/request_ledger.json'),auth_mode=manifest['auth_mode'],runtime_acceptance_manifest=manifest) as client:
            for target in missing:
                cache=root/'data/v4/dynamic_daily_sources/dated_universe'/target/'query_all_stock.json'
                if cache.is_file():payload=load(cache)
                else:
                    requested=datetime.now(timezone.utc).isoformat()
                    rows,metadata=client.query_rows('dynamic_dated_universe','query_all_stock',day=target,max_rows=12000,max_pages=3)
                    if not rows or metadata.get('error_code')!='0':raise ValueError('DATED_UNIVERSE_RESPONSE_NOT_READY')
                    payload=dict(contract_id='DYNAMIC_DATED_UNIVERSE_SOURCE_V1',target_session=target,rows=rows,metadata=metadata,
                                 requested_at=requested,received_at=datetime.now(timezone.utc).isoformat(),AS_RECORDED=False)
                    atomic_json(root,cache,payload)
                if payload['target_session']!=target:raise ValueError('DATED_UNIVERSE_CACHE_DATE_MISMATCH')
                unknown=[r['code'] for r in payload['rows'] if is_stock_code(r['code']) and r['code'].upper() not in bycode and not r['code'].lower().startswith('bj.')]
                if unknown:raise ValueError('NEW_CANONICAL_IDENTITY_REQUIRED:'+','.join(unknown[:10]))
                queries.append(dict(method='query_all_stock',params={'day':target},path=str(cache),requested_at=payload['requested_at'],received_at=payload['received_at']))
    acquisition=dict(acquisition,queries=queries);ap=folder/'sources/acquisition.json';atomic_json(root,ap,acquisition)
    package=freeze.get('effective_package') or load(root/'data/v4/dynamic_daily_sources/tdx_latest_v2.json')
    if package['download']['sha256']!=barsdoc['source_sha256']:raise ValueError('LATEST_PACKAGE_REVISION_MOVED')
    cp=folder/'sources/package_capture.json'
    atomic_json(root,cp,dict(official_publication_date=package['provider_package_date'],package=ref(root,Path(package['download']['path']))))
    pp=folder/'sources/package_pointer.json';atomic_json(root,pp,dict(capture_receipt=ref(root,cp)))
    atomic_json(root,folder/'sources/frozen_previous.json',dict(owners=[dict(oldcore,sources=dict(oldcore['sources'],gbbq=ref(root,gb)))]))
    lifecycle=folder/'sources'/day/'lifecycle.json'
    atomic_json(root,lifecycle,dict(contract_id='DYNAMIC_DATED_LIFECYCLE_V1',trade_date=day,identity=identity_binding,
                 source_rows=observations,rows=observations,active_security_ids=[r['security_id'] for r in observations],
                 status='READY',observed_at=freeze['observed_at'],AS_RECORDED=False,PIT_ELIGIBLE=False))
    # Exact accepted event/policy bindings, with new target-dated lifecycle.
    from .daily_source_manifests import build_special_phase_source_manifest
    acceptance=root/'reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json'
    stage=root/load(acceptance)['evidence']['manifest']['path'];components=load(stage)['components']
    special=build_special_phase_source_manifest(trade_date=day,project_root=root,v402_external_acceptance_path=acceptance,
        v402_stage_manifest_path=stage,event_store_path=root/components['R6_EVENTS']['path'],policy_path=root/components['R6_POLICY']['path'],
        lifecycle_snapshot=dict(contract_id='CURRENT_LIFECYCLE_SNAPSHOT_V1',status='READY',trade_date=day,
            artifact_path=lifecycle.relative_to(root).as_posix(),artifact_sha256=sha256_file(lifecycle),source_revision=freeze_binding['sha256'],
            active_security_ids=[r['security_id'] for r in observations]),observed_at=freeze['observed_at'],tdx_root=Path('D:/new_tdx'))
    specialpath=folder/'sources'/day/'special_phase.json';atomic_json(root,specialpath,special)
    trace=load(root/BASE/'04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json')
    trace['dates']=[r for r in trace['dates'] if r['trade_date']!=day]+[dict(trade_date=day,baostock=ref(root,daily_path))]
    trace['dates'].sort(key=lambda r:r['trade_date'])
    atomic_json(root,folder/'04_TDX_BAOSTOCK_GBBQ_LIFECYCLE_AND_DELTA_SOURCE_TRACE.json',trace)
    mappings={str((root/ACQUISITION).resolve()):str(ap),
              str((root/'reports/audits/DM01_A01_R3_TDX_SOURCE_CAPTURE_R1.json').resolve()):str(pp),
              str((root/'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/CORE_REPLAY.json').resolve()):str(folder/'sources/frozen_previous.json'),
              str((root/BASE/'MEMBER_SNAPSHOT_S.json').resolve()):str(folder/'MEMBER_SNAPSHOT_S.json'),
              str((root/BASE/'sector_v3/SECTOR_REPLAY.json').resolve()):str(folder/'sector_v3/SECTOR_REPLAY.json')}
    seed_registry=load(root/'docs/evidence/source_acquisition_r4_20261009/owner_repair_v1/SECTOR_REPLAY.json')
    if day not in {r['trade_date'] for r in seed_registry['owners']}:
        seed=gzwrite(root,folder/'sources/UNKNOWN_SEED_COMPARATOR.jsonl.gz',[dict(security_id=r['security_id'],base_seed_state='UNKNOWN',
                contract_id='EXPLICIT_NO_PRIOR_TARGET_SEED_COMPARATOR_V1') for r in observations])
        seed_registry=dict(seed_registry,owners=seed_registry['owners']+[dict(trade_date=day,seed=seed)])
    return dict(folder=folder,dates=dates,mappings=mappings,snapshot=snapshot,seed_registry=seed_registry,
                lifecycle=ref(root,lifecycle),special_phase=ref(root,specialpath),parent=parent,freeze=freeze_binding,
                source_counts=dict(Counter(r['status'] for r in observations)))


def build(root,freeze_binding,*,replay_current=False):
    context=prepare(root,freeze_binding,replay_current=replay_current)
    return replay(root,context['folder'],context['dates'],context['mappings'],
                  membership_snapshot=context['snapshot'],seed_registry=context['seed_registry'],
                  observed_at=load(checked(root,context['freeze']))['observed_at']),context


def seal(root,context):
    root=Path(root);folder=context['folder'];day=context['dates'][-1];out=folder/'owner_v3'
    core_replay=load(out/'CORE_REPLAY.json')
    owner=next(r for r in core_replay['owners'] if r['trade_date']==day)
    profile_replay=load(out/'PROFILE_STRUCTURE_REPLAY.json')
    profile=next(r for r in profile_replay['owners'] if r['owner']['trade_date']==day)
    sector_replay=load(folder/'sector_v3/SECTOR_REPLAY.json')
    sector=next(r for r in sector_replay['owners'] if r['trade_date']==day)
    market=next(r for r in load(out/'MARKET_REPLAY.json')['owners'] if r['trade_date']==day)
    focus_replay=load(out/'FOCUS_FORWARD_REPLAY.json')
    focus=next(r for r in focus_replay['owners'] if r['trade_date']==day)
    statuses={r['security_id']:r['status'] for r in gzrows(checked(root,profile['owner']['status']))}
    lifecycle=load(checked(root,context['lifecycle']))
    expected=set(lifecycle['active_security_ids'])
    if set(statuses)!=expected:raise ValueError('FULL_OWNER_LIFECYCLE_CONSERVATION_FAILED')
    if owner['actual_raw_rows']!=context['source_counts'].get('ACTUAL_TRADED',0):raise ValueError('FULL_OWNER_ACTUAL_BAR_CONSERVATION_FAILED')
    if any(r['result']!='PASS' for r in core_replay['oracle']):raise ValueError('FULL_CORE_NUMERIC_ORACLE_FAILED')
    action=folder/'ACTION_QA_REQUIRED.json'
    if action.is_file():
        audit=load(action)
        atomic_json(root,folder/'ACTION_QA_ACCEPTANCE.json',dict(audit,acceptance='PASS_REBUILT_AFFINE_NUMERIC_ORACLE',
            oracle=ref(root,out/'CORE_REPLAY.json'),future_events_policy='Ignored after target date by unchanged transform_window',
            unsupported_categories='Preserve field-local ADJUSTMENT_UNKNOWN; no fabricated crossing price'))
    sessions=official_sessions(root)
    verified={}
    historical=load(root/'config/v4_sector_operational_authority_v1.json')['sources']['historical_status']
    for r in gzrows(checked(root,historical)):
        if r['status']=='SUSPENDED':verified.setdefault(r['security_id'],{})[r['trade_date']]='SUSPENDED'
    acquisition=load(folder/'sources/acquisition.json');identities=load(checked(root,owner['sources']['identity']))['rows']
    ids={r['source_security_key'].lower():r for r in identities}
    for query in acquisition['queries']:
        if query.get('method')=='query_daily_history_k_AStock' and query.get('path'):
            d=query['params'].get('date',query['params'].get('day'))
            for row in load(query['path'])['rows']:
                if row['code'].lower() in ids and row.get('tradestatus')=='0':verified.setdefault(ids[row['code'].lower()]['security_id'],{})[d]='SUSPENDED'
    period_rows={'PERIOD_RAW':[],'PERIOD_ADJUSTED':[]}
    # Current week/month require complete daily input since their official start.
    # Original earlier periods remain in immutable predecessor publications.
    first_month=min(d for d in sessions if d[:7]==day[:7])
    import gzip
    with gzip.open(checked(root,owner['history']),'rt',encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line);sid=row['security_id'];identity=next(i for i in identities if i['security_id']==sid)
            start=max(first_month,identity['list_date'])
            start=next(d for d in sessions if start<=d<=day)
            window=[b for b in row['bars'] if b['trade_date']>=start]
            periods=derive_periods(dict(security_id=sid,source_security_key=identity['source_security_key']),window,
                                   verified.get(sid,{}),sessions,day,sessions[-1],start_session=start)
            for cap,rows in periods.items():period_rows[cap].extend(rows)
    periods={cap:gzwrite(root,out/'owners'/day/(cap+'.jsonl.gz'),rows) for cap,rows in period_rows.items()}
    owners=dict(raw=owner['raw'],adjusted=owner['adjusted'],core=owner['core'],profile=sector['enriched_profiles'],
                base_profile=profile['owner']['profiles'],sector=sector['native'],relative_sector=sector['relative_sector'],
                rotation=sector['rotation'],seed=sector['seed'],sector_receipt=ref(root,folder/'sector_v3/SECTOR_REPLAY.json'),
                market=market['market'],focus=focus['D2'],forward=focus_replay['focus'],prewatch=focus['calculations'],
                lifecycle=context['lifecycle'],special_phase=context['special_phase'],
                period_raw=periods['PERIOD_RAW'],period_adjusted=periods['PERIOD_ADJUSTED'],
                diagnostic=ref(root,out/'owners'/day/'PROFILE_STRUCTURE_OWNER.json'),
                events=ref(root,out/'owners'/day/'structure/events.jsonl'))
    receipt=folder/'DAY_RECEIPT.json'
    atomic_json(root,receipt,dict(contract_id='DYNAMIC_DAILY_DERIVED_DAY_RECEIPT_V1',target_session=day,acceptance='DERIVED_READY',
        owners=owners,source_counts=context['source_counts'],numeric_core_oracle=ref(root,out/'CORE_REPLAY.json'),
        sector_oracle=owners['sector_receipt'],period_kernel=ref(root,root/'src/workbench_analysis/dm01_incremental_component_builders_r3_3.py'),
        source_freeze=context['freeze'],AS_RECORDED=False,PIT_ELIGIBLE=False,external_acceptance='NOT_GRANTED',
        generation_scope=ref(root,folder/'GENERATION_SCOPE.json'),
        affected_history='Every saved rolling window and prior coordinate rebuilt from bound native package and GBBQ',
        rotation_validation='VALIDATION_ONGOING',next_stage='AUTHORIZED_CAS_HTTP_READBACK'))
    parent=context['parent'];parentpath=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    if load(parentpath)!=parent:raise ValueError('OPERATIONAL_PARENT_MOVED_DURING_BUILD')
    predecessor=root/'data/v4/predecessors'/(sha256_file(parentpath)+'.json')
    _atomic_write(predecessor,parentpath.read_bytes(),tdx_root=Path('D:/new_tdx'))
    candidate=dict(parent,contract_id=CONTRACT,authority_mode='USER_AUTHORIZED_READ_ONLY_DAILY_V1',
        accepted_trade_date=day,data_cutoff_date=day,published_sessions=context['dates'],dates=context['dates'],
        predecessor=ref(root,predecessor),day_receipt=ref(root,receipt),observed_at=datetime.now(timezone.utc).isoformat(),
        AS_RECORDED=False,PIT_ELIGIBLE=False,historical_PIT_permission=False,
        release_policy=ref(root,root/'config/read_only_operational_daily_release_policy_v1_1.json'))
    candidate.update(membership_snapshot=ref(root,folder/'MEMBER_SNAPSHOT_S.json'),
                     membership_snapshot_id=context['snapshot']['membership_snapshot_id'],
                     membership_observed_at=context['snapshot']['membership_observed_at'],
                     snapshot_membership_asof=context['snapshot']['member_set_asof'])
    candidate['owners']=dict(parent['owners'],**{day:owners})
    candidate['source_registry']=dict(parent.get('source_registry',{
        d:dict(lifecycle=parent['owners'][d]['lifecycle'],membership=parent['membership_snapshot']) for d in parent['dates']}),
        **{day:dict(freeze=context['freeze'],generation=ref(root,folder/'GENERATION_SCOPE.json'),lifecycle=context['lifecycle'],gbbq=owner['sources']['gbbq'],membership=ref(root,folder/'MEMBER_SNAPSHOT_S.json'))})
    policy=load(root/'config/read_only_operational_daily_release_policy_v1_1.json')
    candidate['accepted_algorithm_bindings']=policy.get('accepted_algorithm_bindings',[])
    original_registry=load(checked(root,parent['registry']))
    registry=folder/'BUILDER_REGISTRY.json'
    atomic_json(root,registry,dict(original_registry,contract_id='DYNAMIC_DAILY_BUILDER_REGISTRY_V1',owner_bindings=candidate['owners'],
        bindings=original_registry['bindings']+[ref(root,root/'src/workbench_analysis/operational_owner_adapter_v1.py'),
                                                  ref(root,root/'src/workbench_analysis/operational_daily_owner_v1.py')]))
    candidate['registry']=ref(root,registry)
    candidate['external_review_contract']='DYNAMIC_DAILY_EXTERNAL_ACCEPTANCE_SEPARATE_V1'
    path=folder/'SUCCESSOR_CANDIDATE.json';atomic_json(root,path,candidate)
    entry=load(folder/'STAGE_ENTRY.json');entry.update(acceptance='DERIVED_READY',evidence=ref(root,receipt),next_stage='AUTHORIZED_CAS_HTTP_READBACK')
    atomic_json(root,folder/'STAGE_ENTRY.json',entry)
    return candidate,ref(root,path)
