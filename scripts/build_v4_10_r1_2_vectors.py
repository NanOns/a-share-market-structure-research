"""Static authority expectations; actual prior fixture generation is not the oracle."""
from copy import deepcopy
from pathlib import Path
import json
from scripts.v4_10_r1_2_fixtures import *
ROOT=Path(__file__).resolve().parents[1]

def sector_unknown_bundle():
    x,ms=accepted_bundle();x['entity_type']='SECTOR'
    dates={s['session_index']:s['trade_date'] for s in ms[0]['sessions']}
    definitions=json.loads((ROOT/'config/v4_10_input_provenance_r1_2.json').read_text())['fields']
    for field,d in definitions.items():
        if d['implemented'] and d['accepted_entity_types']==['STOCK']:
            x['input_provenance'][field]=envelope(field,'UNKNOWN','NOT_APPLICABLE',d,20,dates)
    x['input_provenance']['WARM']=envelope('WARM','UNKNOWN','NOT_IMPLEMENTED',definitions['WARM'],20,dates)
    x['input_provenance']['dq5']=envelope('dq5','UNKNOWN','IMPLEMENTED',definitions['dq5'],20,dates)
    m=ms[1];m.update(entity_type='SECTOR',fields={k:{n:v for n,v in f.items() if n!='publication_id'} for k,f in x['input_provenance'].items() if f['status']=='IMPLEMENTED'})
    pub='V4_10_INPUT:'+digest(m)
    for f in x['input_provenance'].values():
        if f['status']=='IMPLEMENTED':f['publication_id']=pub
    x['input_publication_ids']=[pub]
    return refresh(x),ms

def build_vectors():
    import psycopg
    from scripts.run_v4_08_r3_isolated_verification import disposable_cluster,apply_migrations
    original=json.loads((ROOT/'config/v4_10_machine_vectors_r1_1.json').read_text())['vectors'];rows=deepcopy(original)
    with disposable_cluster(Path(r'E:\Postgres\bin')) as (dsn,temp):
        with psycopg.connect(dsn) as pg:
            apply_migrations(pg);actual,ms=current_prior_fixture(pg)
    historical,_=accepted_prior_fixture()
    for v in rows:
        if v['kind']=='SQL':continue
        x=v['input'];setup=v.get('ledger_setup')
        if setup and setup.get('prior'):setup['prior']=deepcopy(actual)
        if x['mode']=='ACCEPTED_FACT_INTERFACE' and x['prior_state']:
            old=x['prior_state'];r=deepcopy(actual)
            for k in historical:
                if k not in old:r.pop(k,None)
                elif old[k]!=historical[k] and k!='publication_id':r[k]=deepcopy(old[k])
            old_mismatch=old['publication_id']!=state_id(old)
            r['publication_id']=old['publication_id'] if old_mismatch else state_id(r)
            x['prior_state']=r;x['prior_state_binding'].update(publication_id=r['publication_id'],payload_digest=digest(r))
        if v['id']=='model_boundary':
            p=x['prior_state'];p.update(model_contract_id='OLD_RESEARCH_STATE_V0',parameter_set_id='OLD_PARAMETER_SET_V0');p['publication_id']=state_id(p)
            x['prior_state_binding'].update(publication_id=p['publication_id'],payload_digest=digest(p))
            x['model_boundary'],x['synthetic_boundary_manifest']=boundary_descriptor(p,x['trade_date'])
        if v['id']=='authorized_boundary_pass':v['input'],v['ledger_setup']=real_boundary_bundle(False)
    def add(name,x,tag,error=None,expected=None,setup=None):
        rows.append(dict(id=name,kind='API',input=x,expected=expected or {},expected_error=error,coverage=[tag],ledger_setup=setup))
    real,setup=real_boundary_bundle()
    add('real_old_to_current_preserves_followup',deepcopy(real),'real_model_boundary_transition',expected=dict(parent_episode_id=None,preserved_followup_episode_ids=['OLD_AUTHORITY_EPISODE'],maturity='NONE'),setup=deepcopy(setup))
    add('real_boundary_current_episode_namespace_separate',deepcopy(real),'real_model_boundary_transition',expected=dict(episode_id=None,final_eligibility='UNKNOWN'),setup=deepcopy(setup))
    x=deepcopy(real);x['model_boundary']={'status':'NONE'}
    add('old_model_prior_without_boundary_rejected',x,'real_model_boundary_transition','MODEL_BOUNDARY_REQUIRED',setup=deepcopy(setup))
    for name,field,value,error in [
        ('wrong_real_from_model','from_model_contract_id','WRONG_OLD','BOUNDARY_FROM_MODEL_MISMATCH'),
        ('wrong_real_from_parameter','from_parameter_set_id','WRONG_PARAMS','BOUNDARY_FROM_MODEL_MISMATCH'),
        ('wrong_real_to_model','to_model_contract_id','WRONG_CURRENT','BOUNDARY_TO_MODEL_MISMATCH'),
        ('wrong_real_effective_date','effective_trade_date','2026-09-29','BOUNDARY_EFFECTIVE_DATE_MISMATCH'),
        ('missing_old_source_publication','source_publication_id','OLD_STATE:absent','BOUNDARY_PRIOR_NOT_IN_IMMUTABLE_AUTHORITY'),
        ('old_payload_digest_mismatch','source_payload_digest','a'*64,'BOUNDARY_PRIOR_NOT_IN_IMMUTABLE_AUTHORITY')]:
        x=deepcopy(real);s=deepcopy(setup);m=s['manifests'][-1];m[field]=x['model_boundary'][field]=value
        if field.startswith('source_'):x['prior_state_binding'][field]=value
        x['model_boundary'].update(publication_id='V4_10_INPUT:'+digest(m),migration_manifest_sha256=digest(m))
        add(name,x,'real_model_boundary_transition',error,setup=s)
    x=deepcopy(real);s=deepcopy(setup);m=s['manifests'][-1];x['prior_state_binding']['source_authority_digest']=m['source_authority_digest']=x['model_boundary']['source_authority_digest']='b'*64
    x['model_boundary'].update(publication_id='V4_10_INPUT:'+digest(m),migration_manifest_sha256=digest(m))
    add('old_source_authority_digest_mismatch',x,'real_model_boundary_transition','BOUNDARY_PRIOR_NOT_IN_IMMUTABLE_AUTHORITY',setup=s)
    x,ms=accepted_bundle(prior=actual);b,m=boundary_descriptor(actual,x['trade_date'],False);x['model_boundary']=b
    add('noop_model_boundary_rejected',x,'noop_model_boundary_rejected','MODEL_BOUNDARY_NOOP_FORBIDDEN',setup=dict(manifests=ms+ms[:1]+[m]+[accepted_bundle(19)[1][1]],prior=actual))
    for field in ['SEED','PREWATCH','core_price_damage','suspended','risk','delta3']:
        x,ms=accepted_bundle();f=x['input_provenance'][field]
        if field in ['SEED','PREWATCH','core_price_damage','suspended']:
            f.update(value='TRUE',quality='KNOWN');f['source_field_payload']['value']='TRUE';f['source_output_digest']=digest(f['source_field_payload'])
            ms[1]['fields'][field]={k:v for k,v in f.items() if k!='publication_id'}
            pub='V4_10_INPUT:'+digest(ms[1]);x['input_publication_ids']=[pub]
            for ff in x['input_provenance'].values():
                if ff['status']=='IMPLEMENTED':ff['publication_id']=pub
        f.update(status='NOT_IMPLEMENTED',value='UNKNOWN',quality='UNKNOWN',publication_id=None,source_output_digest=None,source_field_payload={},system_available_at=None)
        add(field+'_cannot_suppress_trusted_fact',refresh(x),'trusted_fact_cannot_be_suppressed','STATE_IMPLEMENTED_FIELD_CANNOT_BE_NOT_IMPLEMENTED',setup=dict(manifests=ms,prior=None))
    x,ms=sector_unknown_bundle();f=x['input_provenance']['dq5'];f.update(status='NOT_IMPLEMENTED',publication_id=None,source_output_digest=None,source_field_payload={},system_available_at=None)
    add('dq5_cannot_claim_not_implemented',refresh(x),'implemented_field_status_authority','STATE_IMPLEMENTED_FIELD_CANNOT_BE_NOT_IMPLEMENTED',setup=dict(manifests=ms,prior=None))
    x,ms=sector_unknown_bundle();add('dq5_implemented_unknown_publication_pass',x,'implemented_field_status_authority',expected=dict(final_eligibility='UNKNOWN'),setup=dict(manifests=ms,prior=None))
    x,ms=accepted_bundle();f=x['input_provenance']['delta3'];f.update(value='UNKNOWN',quality='UNKNOWN');f['source_field_payload']['value']='UNKNOWN';f['source_output_digest']=digest(f['source_field_payload']);ms[1]['fields']['delta3']={k:v for k,v in f.items() if k!='publication_id'}
    pub='V4_10_INPUT:'+digest(ms[1]);x['input_publication_ids']=[pub]
    for ff in x['input_provenance'].values():
        if ff['status']=='IMPLEMENTED':ff['publication_id']=pub
    add('delta3_implemented_unknown_publication_pass',refresh(x),'implemented_field_status_authority',expected=dict(health='UNKNOWN'),setup=dict(manifests=ms,prior=None))
    x,ms=accepted_bundle();f=x['input_provenance']['core_price_damage'];f.update(status='NOT_APPLICABLE',value='UNKNOWN',quality='UNKNOWN',publication_id=None,source_output_digest=None,source_field_payload={},system_available_at=None)
    add('stock_core_cannot_use_not_applicable',refresh(x),'implemented_field_status_authority','FIELD_NOT_APPLICABLE_UNAUTHORIZED',setup=dict(manifests=ms,prior=None))
    x,ms=accepted_bundle();f=x['input_provenance']['core_price_damage'];f.update(value='TRUE',quality='KNOWN');f['source_field_payload']['value']='TRUE';f['source_output_digest']=digest(f['source_field_payload']);ms[1]['fields']['core_price_damage']=deepcopy({k:v for k,v in f.items() if k!='publication_id'})
    pub='V4_10_INPUT:'+digest(ms[1]);x['input_publication_ids']=[pub]
    for ff in x['input_provenance'].values():
        if ff['status']=='IMPLEMENTED':ff['publication_id']=pub
    f.update(value='UNKNOWN',quality='UNKNOWN');f['source_field_payload']['value']='UNKNOWN';f['source_output_digest']=digest(f['source_field_payload'])
    add('trusted_true_cannot_be_relabelled_implemented_unknown',refresh(x),'trusted_fact_cannot_be_suppressed','FIELD_NOT_IN_TRUSTED_PUBLICATION',setup=dict(manifests=ms,prior=None))
    for field in ['PREWATCH','SEED']:
        x,ms=accepted_bundle();x['input_provenance'][field]['producer_contract_id']='WRONG_CALLER_OWNER'
        add(field+'_owner_mismatch_cannot_hide_fact',refresh(x),'trusted_fact_cannot_be_suppressed','FIELD_PRODUCER_LINEAGE_MISMATCH',setup=dict(manifests=ms,prior=None))
    for name in ['ordinary_semantic_forge_insert_blocked','ordinary_publication_insert_blocked','ordinary_select_allowed','controlled_publisher_positive_path','direct_sql_implemented_status_suppression','direct_sql_noop_boundary','direct_sql_not_applicable_scope']:
        rows.append(dict(id=name,kind='SQL',coverage=['controlled_state_publisher_authority','semantic_forge_direct_sql_blocked_by_permission'],expected_rejected='blocked' in name or name.startswith('direct_sql_')))
    return rows
