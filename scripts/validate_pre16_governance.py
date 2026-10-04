"""Independent current-status oracle: derives admission from pinned accepted evidence.

Never imports the status builder, business evaluators or status label writer.
"""
import hashlib,json,subprocess
from pathlib import Path
from scripts.pre16_governance_io import ROOT,BASE,HEAD,CONTRACT,R1,R10,R15,DISPOSITION,AUDIT,ARCH
def require(ok,reason):
    if not ok:raise ValueError(reason)
def read(path,root):return json.loads((root/path).read_bytes())
def binding(path,root):
    raw=(root/path).read_bytes();return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def exact(b,root):
    p=(root/b['path']).resolve();require(p.is_relative_to(root.resolve()),'PATH_ESCAPE')
    raw=p.read_bytes();require(hashlib.sha256(raw).hexdigest()==b['sha256'] and len(raw)==b.get('bytes',b.get('byte_count')),'EXACT_EVIDENCE_'+b['path']);return raw
def frozen(path,root):
    old=subprocess.check_output(['git','show',BASE+':'+path],cwd=root)
    if (root/path).read_bytes()!=old:
        literal_required=['V4_STAGE_ACCEPTED_HEAD','V4_DATA_ACCEPTED_HEAD','V4_10_ACCEPTED_HEAD','V4_11_ACCEPTED_HEAD','V4_12_ACCEPTED_HEAD','V4_13_ACCEPTED_HEAD_AMENDED_R1','V4_14_ACCEPTED_HEAD','V4_15_ACCEPTED_HEAD']
        require(Path(path).stem not in literal_required and 'V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_' not in path and path!='config/v4_current_stage_authority_v2.json' and not path.startswith('src/'),'PROTECTED_LITERAL_BYTES_'+path)
        # Only the already accepted, path-specific R20B representations qualify.
        from workbench_analysis.v4_portable_exact import PortableExact
        reader=PortableExact(root);entry=reader.entries.get(path)
        require(entry is not None and entry['mode']=='AUDITED_CRLF_LF_EQUIVALENT_TEXT','PROTECTED_BYTES_'+path)
        require(entry['git_blob_binding']==dict(sha256=hashlib.sha256(old).hexdigest(),bytes=len(old)),'PROTECTED_BASELINE_BLOB_'+path)
        reader.read(dict(path=path,**entry['accepted_bindings'][0]))
        require(subprocess.check_output(['git','diff',BASE,'--name-only','--',path],cwd=root)==b'','PROTECTED_TRACKED_CHANGE_'+path)
    return old
def acyclic(graph):
    done=set();active=set()
    def visit(node):
        require(node not in active,'SUPERSESSION_CYCLE')
        if node in done:return
        active.add(node)
        for other in graph.get(node,[]):visit(other)
        active.remove(node);done.add(node)
    for node in graph:visit(node)
    return True
def expected_entries(root):
    # Explicit source selection, independent of both new authority labels and writer rules.
    states={'A01':'ACCEPTED_SCOPED','A02':'ACCEPTED_SCOPED','A03':'ACCUMULATION_CONTINUES','A04':'ACCEPTED_SCOPED','A04_HISTORICAL_AMOUNT_A':'BLOCKED_AFFECTED_SCOPE','A04_H21_CONSUMER':'ACCUMULATION_CONTINUES','A05':'ACCEPTED_SCOPED','A06':'ACCEPTED_SCOPED','A07':'PERMANENT_CAPABILITY_LIMITATION','A08':'ACCEPTED_SCOPED','A09':'ACCEPTED_SCOPED','OWNER':'ACCEPTED_SCOPED','READER':'ACCEPTED_SCOPED','A08_CURRENT_RUNTIME':'OPEN_EXTERNAL_REAUDIT','HISTORICAL_PIT_EFFECTIVENESS':'PERMANENT_CAPABILITY_LIMITATION','REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME':'NONBLOCKING_VALIDATION_DEBT','REALTIME_ACCEPTED_COHORT_MATURITY':'NONBLOCKING_VALIDATION_DEBT','V4_15_FWD_ADJ_VECTOR_01':'NONBLOCKING_VALIDATION_DEBT','V4_12_REAL_OWNER_CAPABILITY':'NONBLOCKING_VALIDATION_DEBT','V4_13_REAL_OWNER_CAPABILITY':'NONBLOCKING_VALIDATION_DEBT','GOV_PRE16_01':'OPEN_EXTERNAL_REAUDIT'}
    r10=read(R10,root)
    for e in r10['entries']:
        if e.get('work_package','').startswith(tuple('WP-A%02d-'%n for n in range(1,10))) or e['audit_id']=='OWNER_REGISTRY_BOOTSTRAP_FOR_EXISTING_ACCEPTED_FIELDS':continue
        require(e['status'].startswith('ACCEPTED') and e.get('external_acceptance') not in [None,'PENDING'],'EXTRA_ACCEPTANCE_REQUIRED')
        states[e['audit_id']]='ACCEPTED_SCOPED'
    for key in read(R15,root)['independent_audit_items']:
        states[key]='ACCUMULATION_CONTINUES' if key=='AUD_A04_AMOUNT_A_FORWARD_CONSUMER' else 'NONBLOCKING_VALIDATION_DEBT' if key=='AUD_R3_REAL_WINDOW_AND_EPISODE_CAPABILITY' else 'OPEN_EXTERNAL_REAUDIT'
    return states
def verify_entries(h,root):
    states=expected_entries(root);require(set(h['entries'])==set(states),'COMPLETE_CURRENT_ITEM_SET')
    required_authorities={'A01':['data','data_acceptance'],'A02':['a02','a02_acceptance'],'A04':['a04','a04_payload','a04_payload_acceptance'],'A04_HISTORICAL_AMOUNT_A':['a04_payload'],'A04_H21_CONSUMER':['a04_payload'],'A05':['a05','a05_payload','a05_payload_acceptance'],'A08':['a08','a08_acceptance'],'A09':['a09','a09_acceptance'],'A08_CURRENT_RUNTIME':['a08','a08_acceptance'],'HISTORICAL_PIT_EFFECTIVENESS':['v15','audit'],'REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME':['v15','maturity','audit'],'REALTIME_ACCEPTED_COHORT_MATURITY':['v15','maturity','audit'],'V4_15_FWD_ADJ_VECTOR_01':['v15','open_items','audit'],'V4_12_REAL_OWNER_CAPABILITY':['v12','audit'],'V4_13_REAL_OWNER_CAPABILITY':['v13','audit'],'GOV_PRE16_01':['audit']}
    for key in ['A03','A06','A07','OWNER','READER']:required_authorities[key]=['dispositions',key+'_external',key+'_record']
    for key in read(R15,root)['independent_audit_items']:required_authorities[key]=['r15','audit']
    for key in states:
        if key not in required_authorities:required_authorities[key]=['r10',key+'_external']
    for key,state in states.items():
        e=h['entries'][key];require(e['audit_id']==key and e['current_state']==state,'DERIVED_STATE_'+key)
        require(e['scope'] and e['limitations'] and e['current_authority'] and e['evidence_bindings'],'REQUIRED_ENTRY_FIELDS_'+key)
        require(e['blocks_engineering_stage'] is (key=='GOV_PRE16_01'),'ENGINEERING_BLOCK_SCOPE_'+key)
        require(e['blocks_shadow_entry'] is (key in ['A04_HISTORICAL_AMOUNT_A','A04_H21_CONSUMER','A08_CURRENT_RUNTIME','GOV_PRE16_01']),'SHADOW_BLOCK_SCOPE_'+key)
        require(e['blocks_production_cutover'] is True and e['formal_consumer_permission_granted_by_this_head'] is False,'NO_CONSUMER_PERMISSION_'+key)
        require(e['requires_real_observation_accumulation'] is (key in ['A03','A04','A07','A04_H21_CONSUMER','REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME','REALTIME_ACCEPTED_COHORT_MATURITY','AUD_A04_AMOUNT_A_FORWARD_CONSUMER']),'ACCUMULATION_SCOPE_'+key)
        for b in e['evidence_bindings']:exact(b,root)
        require(sorted(e['evidence_bindings'],key=lambda b:b['path'])==sorted(e['current_authority'].values(),key=lambda b:b['path']),'ENTRY_EVIDENCE_SET_'+key)
        require(e['current_authority']=={k:h['sources'][k] for k in required_authorities[key]},'EXACT_REQUIRED_AUTHORITY_'+key)
        for old in e['superseded_historical_statuses']:
            require(old['classification']=='SUPERSEDED_HISTORICAL_STATUS' and old['registry'] in h['historical_registries'],'HISTORICAL_STATUS_CLASSIFICATION')
            historical=read(old['registry']['path'],root).get('entries',{})
            prior=historical.get(key) if isinstance(historical,dict) else next((item for item in historical if item.get('audit_id')==key or item.get('work_package','').startswith('WP-'+key+'-')),None)
            require(prior is not None and old['status']==prior.get('status',prior.get('current_state')),'EXACT_HISTORICAL_STATUS_'+key)
    data=read('data/v4/V4_DATA_ACCEPTED_HEAD.json',root);record=json.loads(exact(data['external_acceptance_record'],root))
    require(data['contract_id']=='V4_DATA_ACCEPTED_HEAD_V2' and data['external_acceptance']=='EXTERNALLY_ACCEPTED_REAL_CONTINUOUS_CHAIN' and data['accepted_trade_date']=='2026-09-30','ACTUAL_A01_AUTHORITY')
    require(record['accepted_scope']['all_nine_each_day'] is True and record['accepted_scope']['AS_RECORDED'] is False,'A01_SCOPED_EXTERNAL_ACCEPTANCE')
    require(h['entries']['A01']['capability_dimensions']==dict(external_acceptance=data['external_acceptance'],accepted_trade_date=data['accepted_trade_date'],AS_RECORDED=False),'A01_NOT_STALE_R1')
    a02=read('data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json',root)
    require(a02['status']=='EXTERNALLY_ACCEPTED_SCOPED_PRODUCER' and a02['AS_RECORDED'] is False and a02['historical_first_availability_proven'] is False and a02['knowledge_lineage']=='RECONSTRUCTED_CORRECTED','A02_EXACT_SCOPED_ADMISSION')
    require(h['entries']['A02']['capability_dimensions']=={k:a02[k] for k in ['AS_RECORDED','historical_first_availability_proven','knowledge_lineage']},'A02_AS_RECORDED_OVERCLAIM')
    exact(a02['acceptance_record'],root);exact(a02['external_authority'],root)
    a04=read('data/v4/A04_AMOUNT_A_GO_FORWARD_PRODUCER_ACCEPTED_HEAD_R1.json',root);p=json.loads(exact(a04['payload'],root))
    require(p['producer_accepted'] is True and p['formal_consumer_enabled'] is False and p['historical_formal_capability']=='BLOCKED' and p['missing_H21']==20 and p['known_amount_a']==0 and p['consumer_auto_activation_after_H21'] is False,'A04_PRODUCER_NOT_CONSUMER')
    require(h['entries']['A04']['capability_dimensions']=={k:p[k] for k in ['producer_accepted','formal_consumer_enabled','historical_formal_capability','accepted_sessions','missing_H21','known_amount_a','consumer_auto_activation_after_H21']},'A04_SCOPE_OVERCLAIM')
    require(h['entries']['A04']['scope']=='Go-forward Amount-A producer engineering only' and 'Historical Amount A BLOCKED' in h['entries']['A04']['limitations'] and 'Stock AMR20 not granted' in h['entries']['A04']['limitations'],'A04_EXPLICIT_LIMITATIONS')
    external=exact(p['external_authority'],root).decode('utf8');require('PASS_ENGINEERING_GO_FORWARD_SCOPE' in external and 'FORMAL_CONSUMER_DISABLED' in external,'A04_EXTERNAL_GRANT')
    for key,name in [('A08','V4_09_N01_HARDENING_ACCEPTED_RECORD_R1.json'),('A09','V4_09_N02_CONSUMER_IDENTITY_HARDENING_ACCEPTED_RECORD_R1.json')]:
        r=read('reports/audits/'+name,root);doc=exact(r['external_authority']['document'],root).decode('utf8')
        require(r['external_acceptance']=='PASS' and key+'_EXTERNAL_ACCEPTANCE = PASS' in doc,'EXACT_'+key+'_EXTERNAL_ACCEPTANCE')
        require(h['entries'][key]['scope']==r['acceptance_scope'],'EXACT_ACCEPTANCE_SCOPE_'+key)
        require(h['entries'][key]['capability_dimensions']==dict(current_runtime_accepted=False,production_database_deployed=False),'A08_A09_IMPLEMENTATION_NOT_RUNTIME')
    a08=read('reports/audits/V4_09_N01_HARDENING_ACCEPTED_RECORD_R1.json',root)
    require(a08['current_runtime_accepted'] is False and a08['current_runtime_external_acceptance']=='PENDING_INDEPENDENT_EXTERNAL_AUDIT','A08_CURRENT_STILL_OPEN')
    a09=read('reports/audits/V4_09_N02_CONSUMER_IDENTITY_HARDENING_ACCEPTED_RECORD_R1.json',root);require(a09['production_database_deployed'] is False,'A09_NOT_DEPLOYED')
    disp=read(DISPOSITION,root)
    for key in ['A03','A06','A07','OWNER','READER']:
        d=disp['scoped_dispositions'][key];exact(d['external_authority']['document'],root);exact(d['prior_acceptance_record'],root)
        require(h['entries'][key]['limitations']==d['capability_limitations'] and h['entries'][key]['scope']==d['disposition'],'SCOPED_LIMITATIONS_'+key)
        require(h['entries'][key]['capability_dimensions']==dict(engineering_task=d['engineering_task'],active_global_trust_root=False,global_mandatory_adoption=False,formal_consumer_cutover=False),'INACTIVE_OWNER_NO_CUTOVER_'+key)
    b2=read('data/v4/V4_08_B2_CURRENT_SNAPSHOT_CAPABILITY_AMENDMENT_R1.json',root);p=json.loads(exact(b2['payload'],root))
    require(p['scope']=='CURRENT_SNAPSHOT_ONLY' and p['AS_RECORDED'] is False and p['historical_PIT_equivalent'] is False and p['amount_a_warm_branch_enabled'] is False,'A05_SNAPSHOT_ONLY')
    require(h['entries']['A05']['capability_dimensions']=={k:p[k] for k in ['scope','AS_RECORDED','historical_PIT_equivalent','amount_a_warm_branch_enabled']},'A05_OVERCLAIM')
    require(h['entries']['A05']['scope']=='Current snapshot 2026-09-24 B2 exact scoped amendment','A05_DATE_SCOPE')
    v15=read('data/v4/V4_15_ACCEPTED_HEAD.json',root);m=read('reports/r20r1r2/MATURITY_DEBT_READBACK.json',root)
    require(v15['CURRENT_REAL_MATURITY_EVIDENCE']=='NONE' and v15['PROVED_HORIZONS']==m['proved_horizons']==[] and v15['UNPROVED_HORIZONS']==m['unproved_horizons']==[1,3,5,10,20],'REAL_MATURITY_NONE')
    require(v15['HISTORICAL_PIT_EFFECTIVENESS']=='NOT_GRANTED' and h['entries']['HISTORICAL_PIT_EFFECTIVENESS']['capability_dimensions']=={'capability':'NOT_GRANTED'},'HISTORICAL_PIT_NOT_GRANTED')
    for key in ['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME','REALTIME_ACCEPTED_COHORT_MATURITY']:
        require(h['entries'][key]['capability_dimensions']==dict(capability=v15[key],PROVED_HORIZONS=[],UNPROVED_HORIZONS=[1,3,5,10,20]),'NONBLOCKING_DEBT_NOT_PASS')
    return True
def protected(root):
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'--','data/v4','config','src','reports/audits'],cwd=root).decode('utf8').splitlines()
    paths=[p for p in names if (p.startswith('data/v4/') and len(Path(p).parts)==3 and 'ACCEPTED_HEAD' in p and 'CANDIDATE' not in p) or 'V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_' in p]
    paths+=['config/v4_current_stage_authority_v2.json','src/workbench_analysis/v4_current_stage_authority.py','src/workbench_analysis/v4_14_authority.py','src/workbench_analysis/v4_15_radar_cohort.py','src/workbench_analysis/v4_15_settlement.py']
    for p in paths:frozen(p,root)
    require(subprocess.check_output(['git','diff',BASE,'--name-only','--','src'],cwd=root)==b'','BUSINESS_SOURCE_KEEP_ALL')
    return [binding(p,root) for p in sorted(set(paths))]
def validate(root=ROOT,head=None):
    root=Path(root).resolve();h=read(HEAD,root) if head is None else head
    source_paths={'data':'data/v4/V4_DATA_ACCEPTED_HEAD.json','stage':'data/v4/V4_STAGE_ACCEPTED_HEAD.json','a02':'data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json','a04':'data/v4/A04_AMOUNT_A_GO_FORWARD_PRODUCER_ACCEPTED_HEAD_R1.json','a05':'data/v4/V4_08_B2_CURRENT_SNAPSHOT_CAPABILITY_AMENDMENT_R1.json','dispositions':DISPOSITION,'a08':'reports/audits/V4_09_N01_HARDENING_ACCEPTED_RECORD_R1.json','a09':'reports/audits/V4_09_N02_CONSUMER_IDENTITY_HARDENING_ACCEPTED_RECORD_R1.json','r10':R10,'r15':R15,'v12':'data/v4/V4_12_ACCEPTED_HEAD.json','v13':'data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json','v15':'data/v4/V4_15_ACCEPTED_HEAD.json','maturity':'reports/r20r1r2/MATURITY_DEBT_READBACK.json','audit':AUDIT,'architecture':ARCH,'open_items':'reports/r21/OPEN_AUDIT_ITEMS.json'}
    for key,path in source_paths.items():require(h['sources'].get(key)==binding(path,root),'SOURCE_SELECTION_'+key)
    for b in h['sources'].values():
        raw=exact(b,root)
        if b['path']!=AUDIT:require(raw==frozen(b['path'],root),'PINNED_ACCEPTED_SOURCE')
    require(binding(AUDIT,root)['sha256']=='13ba5c07daf51c6f244f347acab6cbfa99f7511f1dff65c344974960ce522b99','EXACT_PRE16_AUDIT')
    require(h['execution_baseline']==BASE and h['status']=='READY_FOR_INDEPENDENT_EXTERNAL_AUDIT','CANDIDATE_ONLY')
    require(h['audit_status_authority'] is True and h['business_runtime_authority'] is False and h['formal_consumer_cutover'] is False,'STATUS_NOT_RUNTIME_AUTHORITY')
    require(all(h[k] is False for k in ['production','shadow','focus','V4_16']) and h['V4_16_entry']=='HOLD_PENDING_INDEPENDENT_GOVERNANCE_AUDIT','PERMISSIONS_FALSE')
    verify_entries(h,root);acyclic(h['supersession_graph'])
    for b in h['historical_registries']:require(exact(b,root)==frozen(b['path'],root),'HISTORICAL_IMMUTABLE')
    required_regs={p for p in subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'--','reports/audits'],cwd=root).decode().splitlines() if Path(p).name.startswith('V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_')}
    require({b['path'] for b in h['historical_registries']}==required_regs,'ALL_REGISTRIES_CLASSIFIED')
    require(h['supersession_graph'][HEAD]==[b['path'] for b in h['historical_registries']],'CURRENT_EXPLICIT_SUPERSESSION')
    c=read(CONTRACT,root);require(json.loads(exact(c['current_head'],root))==h and c['current_head']['path']==HEAD,'UNIQUE_EXACT_CURRENT_HEAD')
    require(c['requires_explicit_future_stage_binding'] is True and c['business_runtime_authority'] is False and c['automatic_stage_permission'] is False and all(c[k] is False for k in ['production','shadow','focus','V4_16']),'CONTRACT_NOT_PERMISSION')
    p=protected(root)
    stage=read('data/v4/V4_STAGE_ACCEPTED_HEAD.json',root);require(stage['accepted_stage_range']=='V4_00_TO_V4_15_ACCEPTED','CURRENT_STAGE_15')
    require(read('config/v4_current_stage_authority_v2.json',root)['current_head']['path']=='data/v4/V4_15_ACCEPTED_HEAD.json','CURRENT_AUTHORITY_15_KEEP')
    scan=read('reports/pre16_governance/CONSUMER_SCAN.json',root)
    require(scan['execution_baseline']==BASE and scan['current_runtime_consumers']==0 and scan['unresolved']==0 and scan['repair_required'] is False,'STALE_RUNTIME_CONSUMER_P0')
    # Independently rescan baseline token locations; labels cannot omit matches.
    result=subprocess.run(['git','grep','-n','-I','-E','V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R1([^0-9A-Za-z_]|$)',BASE,'--'],cwd=root,capture_output=True)
    require(result.returncode in [0,1],'SCAN_COMMAND')
    observed={(line.split(':',3)[1],int(line.split(':',3)[2])) for line in result.stdout.decode('utf8').splitlines()}
    require(observed=={(e['path'],e['line']) for e in scan['matches']},'EXHAUSTIVE_CONSUMER_SCAN')
    require(not any(e['path'].startswith('src/') for e in scan['matches']),'UNREVIEWED_RUNTIME_HIT')
    counts={k:sum(e['classification']==k for e in scan['matches']) for k in ['HISTORICAL_EVIDENCE_ONLY','GOVERNANCE_REFERENCE_ONLY','CURRENT_RUNTIME_CONSUMER','UNKNOWN']}
    require(scan['counts']==counts and counts['CURRENT_RUNTIME_CONSUMER']==counts['UNKNOWN']==0,'CONSUMER_CLASSES_FAIL_CLOSED')
    for e in scan['indirect_runtime_data_flow_review']:exact(e['binding'],root)
    return dict(PRE16_CROSS_STAGE_GOVERNANCE_RECONCILIATION='PASS_LOCAL',CURRENT_CROSS_STAGE_AUDIT_AUTHORITY='READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',V4_10_TO_V4_15='PASS_KEEP_NO_REOPEN',V4_STAGE_ACCEPTED_HEAD=stage['accepted_stage_range'],CURRENT_STAGE_AUTHORITY='V4_15',V4_DATA_ACCEPTED_HEAD='2026-09-30',Production=False,Shadow=False,Focus=False,V4_16=False,entries_verified=len(h['entries']),historical_registries_verified=len(required_regs),protected_bytes=p,NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
if __name__=='__main__':
    from scripts.pre16_governance_io import atomic
    r=validate();atomic('reports/pre16_governance/INDEPENDENT_CURRENT_STATUS_ORACLE.json',r)
    atomic('reports/pre16_governance/PROTECTED_BYTES.json',dict(status='PASS_LOCAL',bindings=r['protected_bytes'],baseline=BASE,business_sources_unchanged=True))
    print(json.dumps({k:v for k,v in r.items() if k!='protected_bytes'}))
