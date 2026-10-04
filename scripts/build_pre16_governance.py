"""Derive separate current status metadata; never mutate accepted runtime authority."""
import json,re,subprocess
from pathlib import Path
from scripts.pre16_governance_io import *
from scripts.pre16_consumer_scan import scan
def inventory(root=ROOT):
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=root).decode('utf8').splitlines()
    selected=[p for p in names if (p.startswith('data/v4/') and len(Path(p).parts)==3 and any(s in p for s in ['ACCEPTED','GOVERNANCE','DISPOSITION'])) or (p.startswith('reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_') and p.endswith('.json')) or (p.startswith('reports/audits/work_packages/') and Path(p).name.startswith('STATUS')) or (p.startswith('docs/evidence/') and any(s in Path(p).name for s in ['AUDIT','EXTERNAL_ACCEPTANCE'])) or p=='reports/r21/OPEN_AUDIT_ITEMS.json']
    selected+=['data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json',ARCH]
    records=[]
    for p in sorted(set(selected)):
        role='SOURCE_EVIDENCE_ONLY'
        if 'CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_' in p:role='HISTORICAL_GOVERNANCE_SNAPSHOT'
        elif '/work_packages/' in p:role='HISTORICAL_WORK_PACKAGE_STATUS_NOT_CURRENT_AUTHORITY'
        elif 'CANDIDATE' in p:role='IMPLEMENTATION_ONLY_NOT_EXTERNAL_ACCEPTANCE'
        elif p.startswith('docs/'):role='EXTERNAL_DOCUMENT_REQUIRES_EXPLICIT_SCOPE' if p!=ARCH else 'APPLICABLE_ARCHITECTURE_REV4'
        elif p in ['data/v4/V4_DATA_ACCEPTED_HEAD.json','data/v4/V4_STAGE_ACCEPTED_HEAD.json','data/v4/V4_15_ACCEPTED_HEAD.json']:role='CURRENT_EXPLICIT_ACCEPTED_HEAD_NOT_AUDIT_PERMISSION'
        elif 'ACCEPTED_HEAD' in p:role='EXACT_ACCEPTED_SCOPE_EVIDENCE_NOT_CURRENT_STAGE_SELECTOR'
        elif 'DISPOSITION' in p:role='SCOPED_DISPOSITION_NOT_GLOBAL_TRUST_ROOT'
        records.append(dict(binding=ref(p,root),classification=role))
    return records
def build(root=ROOT):
    inv=inventory(root);registries=[x['binding'] for x in inv if x['classification']=='HISTORICAL_GOVERNANCE_SNAPSHOT']
    atomic('reports/pre16_governance/CURRENT_STATUS_SOURCE_INVENTORY.json',dict(execution_baseline=BASE,records=inv,selection='EXHAUSTIVE_PINNED_BASELINE_CATALOG_NOT_LATEST_AUTHORITY_DISCOVERY'),root)
    atomic('reports/pre16_governance/HISTORICAL_REGISTRY_CLASSIFICATION.json',dict(registries=[dict(binding=b,classification='HISTORICAL_GOVERNANCE_SNAPSHOT') for b in registries],stage_r1_pointer_semantics='HISTORICAL_PROVENANCE_ONLY; CURRENT_STATUS_COMES_FROM_SEPARATE_EXACT_HEAD'),root)
    sources={k:ref(p,root) for k,p in dict(data='data/v4/V4_DATA_ACCEPTED_HEAD.json',stage='data/v4/V4_STAGE_ACCEPTED_HEAD.json',a02='data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json',a04='data/v4/A04_AMOUNT_A_GO_FORWARD_PRODUCER_ACCEPTED_HEAD_R1.json',a05='data/v4/V4_08_B2_CURRENT_SNAPSHOT_CAPABILITY_AMENDMENT_R1.json',dispositions=DISPOSITION,a08='reports/audits/V4_09_N01_HARDENING_ACCEPTED_RECORD_R1.json',a09='reports/audits/V4_09_N02_CONSUMER_IDENTITY_HARDENING_ACCEPTED_RECORD_R1.json',r10=R10,r15=R15,v12='data/v4/V4_12_ACCEPTED_HEAD.json',v13='data/v4/V4_13_ACCEPTED_HEAD_AMENDED_R1.json',v15='data/v4/V4_15_ACCEPTED_HEAD.json',maturity='reports/r20r1r2/MATURITY_DEBT_READBACK.json',audit=AUDIT,architecture=ARCH,open_items='reports/r21/OPEN_AUDIT_ITEMS.json').items()}
    entries={};r1=read(R1,root)
    def add(key,state,scope,keys,limitations,accumulate=False,shadow=False,eng=False,priority='P1',dimensions=None):
        history=[]
        for b in registries:
            obj=read(b['path'],root);es=obj.get('entries',{})
            if isinstance(es,dict):old=es.get(key)
            else:old=next((e for e in es if e.get('work_package','').startswith('WP-'+key+'-') or e.get('audit_id')==key),None)
            if old:history.append(dict(registry=b,status=old.get('status',old.get('current_state')),classification='SUPERSEDED_HISTORICAL_STATUS'))
        evidence={k:sources[k] for k in keys}
        entries[key]=dict(audit_id=key,current_state=state,scope=scope,priority=priority,blocks_engineering_stage=eng,blocks_shadow_entry=shadow,blocks_production_cutover=True,requires_real_observation_accumulation=accumulate,current_authority=evidence,evidence_bindings=list(evidence.values()),limitations=limitations,superseded_historical_statuses=history,capability_dimensions=dimensions or {},formal_consumer_permission_granted_by_this_head=False)
    data=read(sources['data']['path'],root);a02=read(sources['a02']['path'],root)
    a04=read(read(sources['a04']['path'],root)['payload']['path'],root);a05=read(read(sources['a05']['path'],root)['payload']['path'],root)
    sources['a04_payload']=ref(read(sources['a04']['path'],root)['payload']['path'],root);sources['a05_payload']=ref(read(sources['a05']['path'],root)['payload']['path'],root)
    for key,obj in [('data',data),('a02',a02),('a04_payload',a04),('a05_payload',a05),('a08',read(sources['a08']['path'],root)),('a09',read(sources['a09']['path'],root))]:
        b=obj.get('external_acceptance_record') or obj.get('acceptance_record') or obj.get('external_authority')
        if b:
            if 'path' not in b:b=b['document']
            sources[key+'_acceptance']=ref(b['path'],root)
    add('A01','ACCEPTED_SCOPED','DM01 accepted all-nine continuous chain 2026-09-28/29/30; anchor 2026-09-24',['data','data_acceptance'],['AS_RECORDED=false','historical_first_availability=false','RECONSTRUCTED_CORRECTED'],priority='P0',dimensions={'external_acceptance':data['external_acceptance'],'accepted_trade_date':data['accepted_trade_date'],'AS_RECORDED':data['AS_RECORDED']})
    add('A02','ACCEPTED_SCOPED','Accepted RPS producer and separately scoped downstream amendments',['a02','a02_acceptance'],['Not historical AS_RECORDED','Not historical first-availability proof'],dimensions={k:a02[k] for k in ['AS_RECORDED','historical_first_availability_proven','knowledge_lineage']})
    disp=read(DISPOSITION,root)
    for key,state in [('A03','ACCUMULATION_CONTINUES'),('A06','ACCEPTED_SCOPED'),('A07','PERMANENT_CAPABILITY_LIMITATION'),('OWNER','ACCEPTED_SCOPED'),('READER','ACCEPTED_SCOPED')]:
        d=disp['scoped_dispositions'][key];sources[key+'_external']=ref(d['external_authority']['document']['path'],root);sources[key+'_record']=ref(d['prior_acceptance_record']['path'],root)
        add(key,state,d['disposition'],['dispositions',key+'_external',key+'_record'],d['capability_limitations'],accumulate=key in ['A03','A07'],dimensions={'engineering_task':d['engineering_task'],'active_global_trust_root':False,'global_mandatory_adoption':False,'formal_consumer_cutover':False})
    add('A04','ACCEPTED_SCOPED','Go-forward Amount-A producer engineering only',['a04','a04_payload','a04_payload_acceptance'],['Historical Amount A BLOCKED','H21 consumer UNKNOWN; no auto activation','Stock AMR20 not granted'],accumulate=True,dimensions={k:a04[k] for k in ['producer_accepted','formal_consumer_enabled','historical_formal_capability','accepted_sessions','missing_H21','known_amount_a','consumer_auto_activation_after_H21']})
    add('A04_HISTORICAL_AMOUNT_A','BLOCKED_AFFECTED_SCOPE','Historical Amount-A formal consumer',['a04_payload'],['Historical reconstruction not accepted; no backfill first availability'],shadow=True)
    add('A04_H21_CONSUMER','ACCUMULATION_CONTINUES','Consumer-specific H21 acceptance remains pending',['a04_payload'],a04['consumer_external_acceptance_requires'],accumulate=True,shadow=True,dimensions={'accepted_sessions':1,'missing_H21':20,'formal_consumer_enabled':False})
    add('A05','ACCEPTED_SCOPED','Current snapshot 2026-09-24 B2 exact scoped amendment',['a05','a05_payload','a05_payload_acceptance'],['CURRENT_SNAPSHOT_ONLY','AS_RECORDED=false','historical_PIT_equivalent=false','Amount-A WARM branch disabled'],dimensions={k:a05[k] for k in ['scope','AS_RECORDED','historical_PIT_equivalent','amount_a_warm_branch_enabled']})
    for k in ['A08','A09']:
        record=read(sources[k.lower()]['path'],root)
        add(k,'ACCEPTED_SCOPED',record['acceptance_scope'],[k.lower(),k.lower()+'_acceptance'],['No broader current runtime acceptance' if k=='A08' else 'No production database deployment; separate deployment gate'],dimensions={'current_runtime_accepted':record.get('current_runtime_accepted',False),'production_database_deployed':record.get('production_database_deployed',False)})
    add('A08_CURRENT_RUNTIME','OPEN_EXTERNAL_REAUDIT','Current V4-09 runtime distinct from historical hardening audit',['a08','a08_acceptance'],['Accepted historical publication does not accept current runtime'],shadow=True)
    add('HISTORICAL_PIT_EFFECTIVENESS','PERMANENT_CAPABILITY_LIMITATION','Unproven pre-capture historical PIT effectiveness',['v15','audit'],['NOT_GRANTED','Reconstructed evidence cannot prove AS_RECORDED'],dimensions={'capability':'NOT_GRANTED'})
    for k in ['REAL_MATURED_ACCEPTED_SOURCE_SETTLEMENT_RUNTIME','REALTIME_ACCEPTED_COHORT_MATURITY']:
        add(k,'NONBLOCKING_VALIDATION_DEBT','Real forward maturity proof only; independent engineering may continue',['v15','maturity','audit'],['CURRENT_REAL_MATURITY_EVIDENCE=NONE','T0 observation scope RECONSTRUCTED_ASOF'],accumulate=True,dimensions={'capability':read(sources['v15']['path'],root)[k],'PROVED_HORIZONS':[],'UNPROVED_HORIZONS':[1,3,5,10,20]})
    add('V4_15_FWD_ADJ_VECTOR_01','NONBLOCKING_VALIDATION_DEBT','Supported corporate-action nonidentity engineering test enhancement',['v15','open_items','audit'],['OPEN_NONBLOCKING_TEST_ENHANCEMENT','Engineering vector cannot grant real maturity or PIT'])
    add('V4_12_REAL_OWNER_CAPABILITY','NONBLOCKING_VALIDATION_DEBT','Accepted D1 engineering; real target-date owner-dependent signals remain degraded',['v12','audit'],['DO_NOT_RECONSTRUCT_FROM_RAW_BARS','DEGRADED_BY_ACCEPTED_OWNER_CAPABILITY'])
    add('V4_13_REAL_OWNER_CAPABILITY','NONBLOCKING_VALIDATION_DEBT','Accepted integration; upstream real signal/LOO/B2 limitations remain',['v13','audit'],['historical_LOO NOT_VERIFIABLE','legacy_B2 NOT_IMPLEMENTED','algorithmic_support_sector UNKNOWN_REAL_ACCEPTED_CAPABILITY','relative_sector_state UNKNOWN_REAL_ACCEPTED_CAPABILITY'])
    # Keep every additional audit from the externally accepted R10 ledger visible.
    for e in read(R10,root)['entries']:
        k=e['audit_id']
        if e.get('work_package','').startswith(tuple('WP-A%02d-'%n for n in range(1,10))) or k=='OWNER_REGISTRY_BOOTSTRAP_FOR_EXISTING_ACCEPTED_FIELDS':continue
        authority=e.get('external_authority',{}).get('document')
        if not authority:authority=read(R10,root)['external_authority']['document']
        sources[k+'_external']=ref(authority['path'],root)
        add(k,'ACCEPTED_SCOPED',e.get('acceptance_scope','Accepted audit-only scope; no deployment'),['r10',k+'_external'],[e.get('next_step','Preserve affected scope')],priority=e.get('priority','P1'))
    # Unnamed/general stage acceptance is not used to auto-close a separately pending item.
    for k,e in read(R15,root)['independent_audit_items'].items():
        add(k,'ACCUMULATION_CONTINUES' if k=='AUD_A04_AMOUNT_A_FORWARD_CONSUMER' else 'NONBLOCKING_VALIDATION_DEBT' if k=='AUD_R3_REAL_WINDOW_AND_EPISODE_CAPABILITY' else 'OPEN_EXTERNAL_REAUDIT',e['scope'],['r15','audit'],['Historical pending item retained until exact item/scope closure; accepted V4-10..15 remain PASS_KEEP_NO_REOPEN',e['external_acceptance']],accumulate=k=='AUD_A04_AMOUNT_A_FORWARD_CONSUMER')
    add('GOV_PRE16_01','OPEN_EXTERNAL_REAUDIT','This new governance reconciliation requires independent external audit before V4-16 entry',['audit'],['Local reconciliation is not external acceptance','V4-16 entry HOLD'],eng=True,shadow=True,priority='P0')
    edges={HEAD:[b['path'] for b in registries]}
    for b in registries:
        o=read(b['path'],root);edges[b['path']]=[v['path'] for k,v in o.items() if k in ['extends','supersedes','parent_registry','accepted_parent_registry','candidate_parent_registry'] and isinstance(v,dict) and v.get('path') in {x['path'] for x in registries}]
    head=dict(contract_id='V4_CROSS_STAGE_CURRENT_AUDIT_HEAD_V1',version='1.0.0',execution_baseline=BASE,status='READY_FOR_INDEPENDENT_EXTERNAL_AUDIT',audit_status_authority=True,business_runtime_authority=False,formal_consumer_cutover=False,production=False,shadow=False,focus=False,V4_16=False,V4_16_entry='HOLD_PENDING_INDEPENDENT_GOVERNANCE_AUDIT',stage_action='KEEP_EXACT_BYTES',data_action='KEEP_EXACT_BYTES',entries=entries,sources=sources,historical_registries=registries,supersession_graph=edges,rollback='Remove only the new governance head/config in a separate explicitly authorized revision; all accepted pointers and algorithms are untouched.',NEXT='STOP_WAIT_INDEPENDENT_EXTERNAL_AUDIT')
    scan_result=scan(root);assert not scan_result['repair_required'];atomic('reports/pre16_governance/CONSUMER_SCAN.json',scan_result,root)
    atomic(HEAD,head,root);atomic('reports/pre16_governance/CURRENT_CROSS_STAGE_AUDIT_STATUS.json',head,root)
    contract=dict(contract_id='V4_CROSS_STAGE_CURRENT_AUDIT_AUTHORITY_V1',version='1.0.0',current_head=ref(HEAD,root),execution_baseline=BASE,business_runtime_authority=False,requires_explicit_future_stage_binding=True,automatic_stage_permission=False,production=False,shadow=False,focus=False,V4_16=False,taxonomy=['ACCEPTED_SCOPED','ACCEPTED_FULL_REQUIRED_SCOPE','OPEN_ENGINEERING','OPEN_EXTERNAL_REAUDIT','ACCUMULATION_CONTINUES','PERMANENT_CAPABILITY_LIMITATION','BLOCKED_AFFECTED_SCOPE','NONBLOCKING_VALIDATION_DEBT','SUPERSEDED_HISTORICAL_STATUS'],admission_rule='ACCEPTED status requires exact accepted authority and independent external scope; implementation or tests alone never grant acceptance.',historical_registry_semantics='HISTORICAL_GOVERNANCE_SNAPSHOT',stage_current_authority_unchanged=ref('config/v4_current_stage_authority_v2.json',root))
    atomic(CONTRACT,contract,root);print(json.dumps({'entries':len(entries),'registries':len(registries),'inventory':len(inv),'consumer_scan':scan_result['counts']}))
if __name__=='__main__':build()
