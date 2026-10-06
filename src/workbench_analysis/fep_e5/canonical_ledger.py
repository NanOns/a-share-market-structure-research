"""Explicit canonical reconstruction fixture adapter; no default production DSN."""
import hashlib, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from psycopg import sql
from psycopg.types.json import Jsonb
from workbench_analysis.fep_e1.contracts import digest

VERSION = 'FEP_E5_CANONICAL_RECONSTRUCTION_V1'
SCOPE = 'FEP_STOCK_ENTRY_CORE'
FEATURE = 'FEP_E2_HISTORICAL_CORE_FEATURE_V1'
TARGET = 'ABS_RETURN_N:T1'
NS = 'FEP_E5_RECONSTRUCTION_ONLY_V1'
AUTH_CONTRACT = 'FEP_E5_HISTORICAL_RECONSTRUCTION_AUTHORITY_V1'
OUTPUT_FIELDS = ('axes','state','OOD_state','quality_state','support_state','backoff_level','backoff_trace',
    'global_OOD_OK','raw_quantiles','coherent_quantiles','coherence_state','threshold_state','baseline_estimand',
    'calibration_state','projection_state','prediction_evidence','evidence_origin','synthetic_only','FIRST_OBSERVED',
    'REAL_OOS','PROMOTION_EVIDENCE','historical_model_applied_after_observation')

def now():
    return datetime.now(timezone.utc).isoformat()

def apply(pg, root, paths):
    """Install an explicit frozen allocation list, atomically per migration."""
    result=[]
    for relative in paths:
        path=Path(root)/relative; raw=path.read_text(encoding='utf8'); checksum=hashlib.sha256(raw.encode()).hexdigest()
        version='FEP_E5_CANONICAL_'+path.stem.upper()
        with pg.transaction():
            pg.execute("select pg_advisory_xact_lock(hashtextextended('v4.fep.migration',0))")
            exists=pg.execute("select to_regclass('v4_meta.schema_migrations')").fetchone()[0]
            old=pg.execute('select checksum_sha256 from v4_meta.schema_migrations where version=%s',(version,)).fetchone() if exists else None
            if old:
                if old[0].strip()!=checksum:raise ValueError('CANONICAL_MIGRATION_CHECKSUM_CONFLICT')
                state='ALREADY_APPLIED'
            else:
                pg.execute(raw)
                pg.execute('insert into v4_meta.schema_migrations values (%s,%s,clock_timestamp(),%s)',(version,checksum,VERSION));state='APPLIED'
            result.append(dict(path=relative,sha256=checksum,status=state))
    return result

def contract(pg, name, body, *, family=None):
    pg.execute('insert into fep.contracts values (%s,%s,%s,%s,%s,clock_timestamp())',
        (name,family or name,'1',Jsonb(body),digest([name,body])))

def authority_entries(rows, frozen_manifest):
    entries=[]
    for row in rows:
        values=row['model_features']; envelopes=row['feature_snapshot']['core_envelopes']
        fields={k:dict(value=v,quality=envelopes[k]['quality_state'],source_digest=envelopes[k]['input_digest'],
                       reason=envelopes[k].get('unknown_reason')) for k,v in values.items()}
        fd=digest(values);qd=digest({k:dict(quality=v['quality'],source_digest=v['source_digest']) for k,v in fields.items()})
        snap='FEP_CANONICAL_SNAPSHOT:'+digest([row['observation_id'],FEATURE,fd,qd])
        manifest=dict(frozen_manifest,source_observation_id=row['observation_id'],entity_id=row['entity_id'],
            source_row_digest=row['original_e2_row_digest'],feature_contract=FEATURE,feature_digest=fd,quality_digest=qd,
            feature_entries=fields,snapshot_id=snap,prediction_input_digest=digest([snap,fd,qd]),
            max_feature_source_trade_date=row['feature_snapshot']['max_feature_source_trade_date'])
        if manifest['max_feature_source_trade_date']>row['trade_date']:raise ValueError('FUTURE_FEATURE_FORBIDDEN')
        entries.append(dict(authority_id='FEP_RECONSTRUCTION_AUTHORITY:'+digest(manifest),scope_id=SCOPE,namespace_id=NS,
            trade_date=row['trade_date'],evidence_origin='RECONSTRUCTED_CORRECTED',feature_contract_id=FEATURE,
            source_manifest=manifest,source_manifest_digest=digest(manifest),accepted_head_identity=frozen_manifest['accepted_head']))
    return entries

def seed_identity(pg, rows, entries, model_catalog):
    from .metadata_binding import register, verify_signal, SIGNAL_CONTRACT
    metadata = register(pg, contract)
    contract(pg,FEATURE,dict(version=VERSION,source='EXACT_ACCEPTED_E2_CORE_VECTOR'))
    contract(pg,'FEP_E5_OBSERVATION_V1',dict(signal='FIRST_PREWATCH',source='ACCEPTED_HISTORICAL_E2_POPULATION'))
    contract(pg,'FEP_E5_WINDOW_V1',dict(source=entries[0]['source_manifest']['historical_population']))
    contract(pg,'FEP_E5_ENGINEERING_POLICY_V1',dict(champion=False,display=False,priority=False))
    contract(pg,AUTH_CONTRACT,dict(namespace_id=NS,exact_authorities=entries),family='FEP_RECONSTRUCTION_AUTHORITY_V1')
    pg.execute("insert into v4.model_namespaces values (%s,%s,'SHADOW',%s)",(NS,AUTH_CONTRACT,NS))
    pg.execute("insert into fep.scopes values (%s,'STOCK','ENTRY','FIRST_PREWATCH','CORE',%s,'FEP_E5_OBSERVATION_V1',%s)",(SCOPE,NS,digest([SCOPE,NS])))
    target = metadata['target_row']
    pg.execute('insert into fep.targets values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        tuple(Jsonb(target[k]) if k in ('risk_set','allowed_quality') else target[k] for k in
              ('target_id','contract_id','scope_id','horizon','unit','value_kind','formula','risk_set','allowed_quality','enabled')))
    for field in rows[0]['model_features']:
        pg.execute("insert into fep.field_registry values (%s,%s,'ACCEPTED_CORE_OWNER','model_features',%s,'SOURCE_FEATURE_CONTRACT',true,false,'SOURCE_DATE_LE_OBSERVATION_DATE',%s,'FEP_E5_WINDOW_V1')",
            (FEATURE,field,'BOOLEAN' if field in ('hh_progress','ll_progress') else 'NUMERIC',Jsonb(['OBSERVED','UNKNOWN'])))
        pg.execute('insert into fep.field_scope values (%s,%s,%s)',(FEATURE,field,SCOPE))
    mapping=[]
    for row,e in zip(rows,entries):
        verify_signal(dict(core_signal_contract_id=SIGNAL_CONTRACT, scope_id=SCOPE,
                           signal_key='FIRST_PREWATCH:'+row['observation_id']), metadata['signal_body'])
        cutoff=datetime.fromisoformat(row['trade_date']+'T07:00:00+00:00')
        pg.execute('insert into fep.observations values (%s,%s,%s,%s,%s,%s,%s,%s)',
            (row['observation_id'],SCOPE,row['entity_id'],row['trade_date'],'FIRST_PREWATCH:'+row['observation_id'],row['episode_id'],SIGNAL_CONTRACT,cutoff))
        recorded=pg.execute('select clock_timestamp()').fetchone()[0]
        pg.execute('insert into fep.reconstruction_authorities values (%s,%s,%s,%s,%s,%s,\'REPLAY\',%s,%s,%s,%s,%s,\'NOT_HISTORICALLY_OBSERVED\',false,false,false)',
            (e['authority_id'],AUTH_CONTRACT,SCOPE,NS,e['trade_date'],e['evidence_origin'],Jsonb(e['source_manifest']),e['source_manifest_digest'],FEATURE,Jsonb(e['accepted_head_identity']),recorded))
        manifest=dict(e['source_manifest'],reconstruction_authority=e['authority_id'])
        pg.execute("insert into fep.observation_revisions(observation_id,revision,publication_id,feature_cutoff,dependency_manifest,dependency_digest,enrichment_token,evidence_origin,execution_mode,created_at,authority_kind,reconstruction_authority_id) values (%s,1,null,%s,%s,%s,'NONE','RECONSTRUCTED_CORRECTED','REPLAY',clock_timestamp(),'HISTORICAL_RECONSTRUCTION',%s)",
            (row['observation_id'],cutoff,Jsonb(manifest),digest(manifest),e['authority_id']))
        snap=e['source_manifest']['snapshot_id']
        pg.execute('insert into fep.snapshots values (%s,%s,1,%s,%s,%s,clock_timestamp())',(snap,row['observation_id'],FEATURE,e['source_manifest']['feature_digest'],e['source_manifest']['quality_digest']))
        for field,v in e['source_manifest']['feature_entries'].items():
            pg.execute('insert into fep.feature_values values (%s,%s,%s,%s,%s,%s,%s)',(snap,FEATURE,field,Jsonb(v['value']),v['quality'],v['reason'],v['source_digest']))
        mapping.append(dict(source_observation_id=row['observation_id'],source_evidence_digest=row['original_e2_row_digest'],observation_id=row['observation_id'],scope_id=SCOPE,entity_id=row['entity_id'],trade_date=row['trade_date'],authority_kind='HISTORICAL_RECONSTRUCTION',reconstruction_authority_id=e['authority_id'],publication_id=None,observation_revision=1,snapshot_id=snap,feature_digest=e['source_manifest']['feature_digest'],quality_digest=e['source_manifest']['quality_digest'],feature_cutoff=cutoff.isoformat(),reconstructed_at=recorded.isoformat(),execution_mode='REPLAY',evidence_origin='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,FIRST_OBSERVED=False,REAL_OOS=False))
    models=[]
    for m in model_catalog:
        role='BASELINE' if m['stage']=='E2' else 'CHALLENGER';mid=m['model_id'];setid='FEP_CANONICAL_SET:'+digest([mid,role,VERSION])
        manifest=dict(source_artifact_bindings=m['artifact_references'],canonical_role=role,evidence_class=m['evidence_class'],new_training=False,
            upstream_diagnostics=m['canonical_import_diagnostics'])
        name='IMPORT:'+m['stage'];body=dict(model_id=mid,model_digest=m['artifact_digest'],model_family=m['model_family'],feature_contract_id=FEATURE,scope_id=SCOPE,target_id=TARGET,horizon=1,exact_import_manifest=manifest)
        contract(pg,name,body)
        pg.execute("insert into fep.models(model_id,training_run_id,scope_id,target_id,horizon,feature_contract_id,family,transform_digest,calibration_digest,ood_digest,model_digest,accepted_at,artifact_origin,import_contract_id,import_manifest) values (%s,null,%s,%s,1,%s,%s,%s,%s,%s,%s,clock_timestamp(),'ACCEPTED_ARTIFACT_IMPORT',%s,%s)",
            (mid,SCOPE,TARGET,FEATURE,m['model_family'],digest(manifest['upstream_diagnostics']['transform']),digest(manifest['upstream_diagnostics']['calibration']),digest(manifest['upstream_diagnostics']['OOD']),m['artifact_digest'],name,Jsonb(manifest)))
        pg.execute("insert into fep.model_sets values (%s,'FEP_E5_ENGINEERING_POLICY_V1',%s,clock_timestamp())",(setid,digest([setid,manifest])))
        pg.execute('insert into fep.model_set_members values (%s,%s,%s,1,%s,%s,%s)',(setid,SCOPE,TARGET,FEATURE,mid,role))
        gid='FEP_SHADOW_GRANT:'+digest([SCOPE,TARGET,FEATURE,setid,role])
        pg.execute("insert into fep.permission_keys values (%s,%s,%s,1,%s,%s,%s,'SHADOW_INFERENCE')",(gid,SCOPE,TARGET,FEATURE,setid,role))
        models.append(dict(m,canonical_model_set_id=setid,canonical_role=role,grant_id=gid))
    return mapping,models

def head(pg):
    row=pg.execute("select head_version,activation_id,grant_id from fep.deployment_heads where scope_id=%s and capability='SHADOW_INFERENCE' and target_id=%s and horizon=1 and feature_contract_id=%s",(SCOPE,TARGET,FEATURE)).fetchone()
    return row or (0,None,None)

def cas(pg, grant, action, request, *, expected=None, prior=None):
    h=head(pg);expected=h[0] if expected is None else expected;prior=h[1] if prior is None else prior
    aid='FEP_CANONICAL_ACTIVATION:'+request
    version=pg.execute('select fep.cas_deploy(%s,%s,%s,%s,%s,%s,%s,%s)',(grant,aid,action,expected,prior,request,digest([request,action]),Jsonb(dict(engineering_only=True)))).fetchone()[0]
    return dict(activation_id=aid,grant_id=grant,version=version,action=action,request_id=request)

def plan(pg, prior_record, mapping, model, cutoff, activation):
    slot='FEP_CANONICAL_SLOT:'+digest([prior_record['slot_id'],VERSION]);pid='FEP_CANONICAL_PREDICTION:'+digest([slot,model['model_id'],1]);rid='FEP_CANONICAL_RUN:'+digest(pid)
    deadline=(datetime.fromisoformat(cutoff)+timedelta(hours=1)).isoformat()
    pg.execute("insert into fep.prediction_slots values (%s,%s,%s,%s,1,%s,%s,%s,'SELECTED')",
        (slot,mapping['observation_id'],SCOPE,TARGET,model['model_family'],cutoff,deadline))
    pg.execute('insert into fep.slot_model_bindings values (%s,%s,%s,%s,1,%s,%s,%s)',(slot,mapping['observation_id'],SCOPE,TARGET,model['canonical_model_set_id'],cutoff,digest([slot,model['model_id'],activation])))
    return slot

def accept(pg, prior_record, mapping, model, cutoff, activation, *, fail_before_receipt=False):
    slot='FEP_CANONICAL_SLOT:'+digest([prior_record['slot_id'],VERSION]);pid='FEP_CANONICAL_PREDICTION:'+digest([slot,model['model_id'],1]);rid='FEP_CANONICAL_RUN:'+digest(pid)
    outputs={k:prior_record[k] for k in OUTPUT_FIELDS if k in prior_record};output_sha=digest(outputs)
    started=now()
    with pg.transaction():
        accepted=now()
        pg.execute("insert into fep.prediction_runs(run_id,publication_id,model_set_id,input_digest,started_at,finished_at,output_digest,counts,authority_kind,reconstruction_authority_id) values (%s,null,%s,%s,%s,%s,%s,%s,'HISTORICAL_RECONSTRUCTION',%s)",
            (rid,model['canonical_model_set_id'],digest([mapping['snapshot_id'],mapping['feature_digest'],mapping['quality_digest']]),started,accepted,output_sha,Jsonb(dict(expected=1,produced=1)),mapping['reconstruction_authority_id']))
        pg.execute("insert into fep.predictions values (%s,%s,1,%s,%s,%s,1,%s,%s,%s,%s,%s,'HISTORICAL_SIMULATION',%s,%s,%s,%s,%s,%s,null)",
            (pid,slot,mapping['observation_id'],SCOPE,TARGET,model['canonical_model_set_id'],model['model_id'],FEATURE,mapping['snapshot_id'],rid,prior_record['quality_state'],None if prior_record['projection_state']=='READY' else prior_record['projection_state'],Jsonb(outputs),Jsonb(dict(state=prior_record['support_state'])),output_sha,accepted))
        if fail_before_receipt:raise ValueError('FEP_INJECTED_ACCEPTANCE_FAILURE')
        pg.execute("insert into fep.acceptance_receipts values (%s,%s,%s,%s,%s,'FEP_E5_ENGINEERING_POLICY_V1',%s)",
            ('ACCEPT:'+pid,rid,accepted,model['grant_id'],activation['activation_id'],Jsonb(dict(engineering_only=True,model_display=False,priority_use=False))))
        payload=dict(source_slot_id=prior_record['slot_id'],prediction_id=pid,projection_state=prior_record['projection_state'])
        pg.execute("insert into fep.slot_receipts values (%s,%s,%s,'ACCEPTED',%s,%s)",(slot,'RECEIPT:'+pid,accepted,Jsonb(payload),digest(payload)))
    return dict(prediction_id=pid,run_id=rid,slot_id=slot,model_id=model['model_id'],model_set_id=model['canonical_model_set_id'],source_prediction_id=prior_record['prediction_id'],source_slot_id=prior_record['slot_id'],output_digest=output_sha,outputs=outputs,**mapping)

def inventory(pg):
    return {n:pg.execute(sql.SQL('select count(*) from fep.{}').format(sql.Identifier(n))).fetchone()[0] for n, in pg.execute("select tablename from pg_tables where schemaname='fep' order by tablename")}
