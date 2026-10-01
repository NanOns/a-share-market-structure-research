"""Explicit synthetic *inputs* for real adapters; never substitutes a builder or market evidence."""
from copy import deepcopy
import json
from pathlib import Path
import struct
import zipfile
from workbench_analysis.dm01_incremental_component_builders import ROOT,canonical,digest,sha,artifact_reference_path
from workbench_analysis.daily_source_freeze import build_source_freeze_manifest_v2
from workbench_analysis.dm01_accepted_chain_v1 import resolve_frozen_binding, HEAD_PATH, ANCHOR_SHA

TARGET='2026-09-28'
SID='DM01-ENGINEERING-INPUT-A'
SOURCE_KEY='SH.600001'

def save(root,name,value):
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(canonical(value)+b'\n')
    return dict(path=artifact_reference_path(p),sha256=sha(p),bytes=p.stat().st_size)

def repo_ref(path):
    p=ROOT/path;return dict(path=artifact_reference_path(p),sha256=sha(p),bytes=p.stat().st_size)

def make_inputs(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    archived_parent=resolve_frozen_binding(ROOT,dict(path=HEAD_PATH,sha256=ANCHOR_SHA))
    parent_ref=repo_ref(archived_parent.relative_to(ROOT).as_posix());head=json.loads(Path(parent_ref['path']).read_text(encoding='utf8'))
    record=dict(security_id=SID,source_security_key=SOURCE_KEY,symbol=SOURCE_KEY,board_scope='SH_MAIN',board='SH_MAIN',security_type='A_SHARE',
        list_date='2020-01-02',symbol_effective_from='2020-01-02',symbol_effective_to=None,system_available_at='2026-09-24T08:00:00+00:00')
    identity_ref=save(root,'identity.json',dict(records=[record],fixture_scope='ENGINEERING_INPUT_ONLY'))
    identity=dict(status='ACCEPTED',publication_id=identity_ref['sha256'],binding=identity_ref,records=[record])
    sessions=['2026-09-23','2026-09-24','2026-09-28','2026-09-29','2026-09-30']
    cal=dict(session_dates=sessions,coverage_end='2026-09-30',fixture_scope='ENGINEERING_INPUT_ONLY')
    calref=save(root,'calendar.json',cal);calendar=dict(status='ACCEPTED',publication_id=calref['sha256'],binding=calref,
        payload_digest=digest(cal),session_dates=sessions,coverage_end=cal['coverage_end'])
    member=dict(security_id=SID,source_security_key=SOURCE_KEY,trade_date=head['accepted_trade_date'],board_scope='SH_MAIN')
    components={}
    for cap in ('IDENTITY_UNIVERSE','RAW_DAILY','TRADING_STATUS','ISST','ADJUSTED_DAILY','PERIOD_RAW','PERIOD_ADJUSTED','PRICE_LIMIT','SPECIAL_PHASE'):
        rows=[dict(member)]
        if cap=='PRICE_LIMIT':rows=[dict(member,next_reference_close='10.00',next_reference_blocked_by=None)]
        if cap.startswith('PERIOD_'):
            rows=[]
            for kind,pk,end in [('WEEKLY','2026-W39','2026-09-25'),('MONTHLY','2026-09','2026-09-30')]:
                rows.append(dict(security_id=SID,source_security_key=SOURCE_KEY,trade_date='2026-09-24',as_of_date='2026-09-24',
                    parent_daily_cutoff='2026-09-24',period_type=kind,period_key=pk,period_end_date=end,period_view='AS_OF_PARTIAL',
                    price_basis='QFQ' if cap.endswith('ADJUSTED') else 'RAW',open='10.00',high='10.10',low='9.90',close='10.00',
                    volume=100,amount=1000.0,actual_count=1,suspended_count=0,data_gap_count=0,unknown_count=0,
                    first_source_date='2026-09-24',max_source_date='2026-09-24',source_daily_digest='f'*64))
        components[cap]=save(root,'parent_'+cap+'.json',dict(trade_date='2026-09-24',rows=rows,fixture_scope='ENGINEERING_INPUT_ONLY'))
    parent_manifest=save(root,'parent_components.json',dict(parent_data_head_digest=parent_ref['sha256'],components=components,
        fixture_scope='ENGINEERING_INPUT_ONLY_NOT_ACCEPTED_MARKET_ARTIFACTS'))
    parent=dict(head=head,binding=parent_ref,components=components,component_manifest_binding=parent_manifest)
    package=root/'hsjday.zip'
    with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_STORED) as z:
        z.writestr('sh/lday/sh600001.day',struct.pack('<IIIIIfII',20260928,1010,1030,1000,1020,10200.0,1000,0))
    package_ref=dict(path=artifact_reference_path(package),sha256=sha(package),bytes=package.stat().st_size)
    delta=dict(contract_id='TDX_PACKAGE_DELTA_V1',status='READY',target_date=TARGET,current_snapshot_id='sha256-'+package_ref['sha256'],
        target_bars=[dict(security_id=SOURCE_KEY,trade_date=20260928,open=10.1,high=10.3,low=10.0,close=10.2,amount=10200.0,volume=1000)],
        revision_events=[],fixture_scope='ENGINEERING_INPUT_ONLY')
    delta_ref=save(root,'delta.json',delta)
    bao=dict(status='BAOSTOCK_DAILY_SNAPSHOT_READY',trade_date=TARGET,provider_date=TARGET,snapshot_id='ENGINEERING-ROSTER',
        daily_rows=[dict(date=TARGET,code=SOURCE_KEY.lower(),tradestatus='1',isST='0')],adjustment_factor_rows=[],fixture_scope='ENGINEERING_INPUT_ONLY')
    bao_ref=save(root,'bao.json',bao)
    gbbq=root/'gbbq';gbbq.write_bytes(struct.pack('<I',0));gbbq_ref=dict(path=artifact_reference_path(gbbq),sha256=sha(gbbq),bytes=4)
    classdoc=json.loads((ROOT/'config/v4_02_gbbq_price_impact_classification_v1.json').read_text(encoding='utf8'))
    categories={k:v['formal_disposition'] for k,v in classdoc['dispositions'].items()}
    disp_ref=save(root,'dispositions.json',dict(gbbq_sha256=gbbq_ref['sha256'],first_eligible_formal_trade_date='2026-09-24',
        rows=[dict(security_id=SID,blocking_categories=[])],category_dispositions=categories,fixture_scope='ENGINEERING_INPUT_ONLY'))
    contract=json.loads((ROOT/'config/dm01_incremental_builders_contract_r1.json').read_text(encoding='utf8'))
    life_ref=save(root,'lifecycle.json',dict(contract_id='CURRENT_LIFECYCLE_SNAPSHOT_V1',trade_date=TARGET,active_security_ids=[SID],fixture_scope='ENGINEERING_INPUT_ONLY'))
    phase=dict(contract_id='SPECIAL_PHASE_SOURCE_MANIFEST_V1',trade_date=TARGET,status='READY',
        event_store=contract['accepted_phase_bindings']['event_store'],policy=contract['accepted_phase_bindings']['policy'],
        lifecycle_snapshot=life_ref,active_security_ids=[SID],event_status='NO_NEW_SPECIAL_PHASE_EVENT')
    phase_ref=save(root,'phase.json',phase)
    rules_ref=contract['accepted_phase_bindings']['rules']
    inputs=dict(TDX_PACKAGE_DELTA=delta_ref,BAOSTOCK_DAILY_UPDATE=bao_ref,GBBQ=gbbq_ref,GBBQ_DISPOSITIONS=disp_ref,
        SPECIAL_PRICE_PHASE=phase_ref,PRICE_RULES=rules_ref)
    page_ref=save(root,'page.json',dict(target_date=TARGET,update_date=TARGET,snapshot_id=delta['current_snapshot_id'],
        download=package_ref,status='TDX_PACKAGE_READY',fixture_scope='ENGINEERING_INPUT_ONLY'))
    factors_ref=save(root,'factor_audit.json',dict(rows=[],trade_date=TARGET,fixture_scope='ENGINEERING_INPUT_ONLY'))
    files=dict(TDX_PAGE_CAPTURE=page_ref,TDX_FULL_PACKAGE=package_ref,TDX_PACKAGE_DELTA=delta_ref,OFFICIAL_CALENDAR=calref,
        BAOSTOCK_DAILY_UPDATE=bao_ref,BAOSTOCK_ADJUSTMENT_FACTOR=factors_ref,GBBQ=gbbq_ref,IDENTITY_LIFECYCLE=life_ref,SPECIAL_PRICE_PHASE=phase_ref)
    sources={k:dict(v,source_revision=delta['current_snapshot_id'] if k=='TDX_FULL_PACKAGE' else v['sha256']) for k,v in files.items()}
    freeze=build_source_freeze_manifest_v2(trade_date=TARGET,sources=sources,changed_tdx_files=[],
        observed_at='2026-09-28T09:00:00+00:00',ingested_at='2026-09-28T09:00:00+00:00',system_available_at='2026-09-28T09:00:00+00:00')
    freeze.update(inputs=inputs,parent_data_head_digest=parent_ref['sha256'],calendar_publication_id=calendar['publication_id'],
        identity_publication_id=identity['publication_id'],fixture_scope='ENGINEERING_INPUT_ONLY_NOT_REAL_MARKET',tdx_roots=[str(root/'tdx-read-only')])
    rehash(freeze)
    return dict(parent=parent,freeze=freeze,calendar=calendar,identity=identity,staging=root/'staging',root=root)

def rehash(freeze):
    freeze['manifest_sha256']=digest({k:v for k,v in freeze.items() if k!='manifest_sha256'})

def replace_input(env,name,value):
    ref=save(env['root'],name+'_'+digest(value)+'.json',value);env['freeze']['inputs'][name]=ref
    family={'TDX_PACKAGE_DELTA':'TDX_PACKAGE_DELTA','BAOSTOCK_DAILY_UPDATE':'BAOSTOCK_DAILY_UPDATE','SPECIAL_PRICE_PHASE':'SPECIAL_PRICE_PHASE'}.get(name)
    if family:env['freeze']['source_families'][family]=dict(ref,source_revision=ref['sha256'])
    rehash(env['freeze']);return ref

def advance_engineering_inputs_to_month_boundary(env):
    """A future parent/session fixture tests the same runtime; it is never market evidence."""
    target='2026-10-08';parent_date='2026-09-30';root=env['root'];parent=env['parent'];f=env['freeze']
    head=deepcopy(parent['head']);head['accepted_trade_date']=parent_date
    for permission in head['component_permissions'].values():permission['cutoff']=parent_date
    head['fixture_scope']='ENGINEERING_INPUT_ONLY';parent['head']=head;parent['binding']=save(root,'month_parent_head.json',head)
    for cap,ref in list(parent['components'].items()):
        value=json.loads(Path(ref['path']).read_text(encoding='utf8'));value['trade_date']=parent_date
        for r in value['rows']:
            r['trade_date']=parent_date
            if cap.startswith('PERIOD_'):
                r.update(as_of_date=parent_date,parent_daily_cutoff=parent_date,first_source_date=parent_date,max_source_date=parent_date,
                    period_key='2026-W40' if r['period_type']=='WEEKLY' else '2026-09',period_end_date='2026-10-02' if r['period_type']=='WEEKLY' else parent_date)
        parent['components'][cap]=save(root,'month_parent_'+cap+'.json',value)
    parent['component_manifest_binding']=save(root,'month_parent_components.json',dict(parent_data_head_digest=parent['binding']['sha256'],components=parent['components'],fixture_scope='ENGINEERING_INPUT_ONLY'))
    cal=dict(session_dates=[parent_date,target,'2026-10-09','2026-10-30'],coverage_end='2026-10-31',fixture_scope='ENGINEERING_INPUT_ONLY')
    ref=save(root,'month_calendar.json',cal);env['calendar'].update(binding=ref,payload_digest=digest(cal),publication_id=ref['sha256'],**cal)
    package=root/'month_hsjday.zip'
    with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_STORED) as z:
        z.writestr('sh/lday/sh600001.day',struct.pack('<IIIIIfII',20261008,1010,1030,1000,1020,10200.0,1000,0))
    pkg=dict(path=str(package),sha256=sha(package),bytes=package.stat().st_size)
    delta=json.loads(Path(f['inputs']['TDX_PACKAGE_DELTA']['path']).read_text(encoding='utf8'))
    delta.update(target_date=target,current_snapshot_id='sha256-'+pkg['sha256']);delta['target_bars'][0]['trade_date']=20261008
    replace_input(env,'TDX_PACKAGE_DELTA',delta)
    bao=json.loads(Path(f['inputs']['BAOSTOCK_DAILY_UPDATE']['path']).read_text(encoding='utf8'));bao.update(trade_date=target,provider_date=target);bao['daily_rows'][0]['date']=target
    replace_input(env,'BAOSTOCK_DAILY_UPDATE',bao)
    phase=json.loads(Path(f['inputs']['SPECIAL_PRICE_PHASE']['path']).read_text(encoding='utf8'));phase['trade_date']=target
    replace_input(env,'SPECIAL_PRICE_PHASE',phase)
    page=save(root,'month_page.json',dict(target_date=target,update_date=target,snapshot_id=delta['current_snapshot_id'],download=pkg))
    f['source_families']['TDX_PAGE_CAPTURE']=dict(page,source_revision=page['sha256'])
    f['source_families']['TDX_FULL_PACKAGE']=dict(pkg,source_revision=delta['current_snapshot_id'])
    f['source_families']['OFFICIAL_CALENDAR']=dict(ref,source_revision=ref['sha256'])
    f.update(trade_date=target,parent_data_head_digest=parent['binding']['sha256'],calendar_publication_id=env['calendar']['publication_id'],
        observed_at='2026-10-08T09:00:00+00:00',ingested_at='2026-10-08T09:00:00+00:00',system_available_at='2026-10-08T09:00:00+00:00')
    rehash(f)
