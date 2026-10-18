"""Explicit canonical reconstruction fixture adapter; no default production DSN."""
import json
from datetime import datetime, timezone, timedelta
from psycopg.types.json import Jsonb
from workbench_analysis.fep_e1.contracts import digest
from workbench_analysis.fep_e1.db import TABLES

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
    """Verify the centrally registered fixed-v4 migration; never run legacy SQL."""
    if paths:
        raise ValueError('FEP_MIGRATIONS_MUST_USE_CENTRAL_V4_RUNNER')
    row=pg.execute("select checksum_sha256 from v4.schema_migrations where version='V4_FEP_FIXED_SCHEMA_STORAGE_R1'").fetchone()
    if not row:
        raise RuntimeError('V4_FEP_FIXED_SCHEMA_MIGRATION_REQUIRED')
    return [dict(version='V4_FEP_FIXED_SCHEMA_STORAGE_R1',sha256=row[0].strip(),status='ALREADY_APPLIED')]

def contract(pg, name, body, *, family=None):
    pg.execute('insert into v4.contracts values (%s,%s,%s,%s,%s,clock_timestamp())',
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
    contract(pg,FEATURE,dict(version=VERSION,source='EXACT_ACCEPTED_E2_CORE_VECTOR'))
    contract(pg,'FEP_E5_OBSERVATION_V1',dict(signal='FIRST_PREWATCH',source='ACCEPTED_HISTORICAL_E2_POPULATION'))
    contract(pg,'FEP_E5_WINDOW_V1',dict(source=entries[0]['source_manifest']['historical_population']))
    contract(pg,'FEP_E5_ENGINEERING_POLICY_V1',dict(champion=False,display=False,priority=False))
    contract(pg,AUTH_CONTRACT,dict(namespace_id=NS,exact_authorities=entries),family='FEP_RECONSTRUCTION_AUTHORITY_V1')
    pg.execute("insert into v4.model_namespaces values (%s,%s,'SHADOW',%s)",(NS,AUTH_CONTRACT,NS))
    pg.execute("insert into v4.scopes values (%s,'STOCK','ENTRY','FIRST_PREWATCH','CORE',%s,'FEP_E5_OBSERVATION_V1',%s)",(SCOPE,NS,digest([SCOPE,NS])))
    pg.execute("insert into v4.targets values (%s,'FEP_E5_OBSERVATION_V1',%s,1,'ratio','NUMERIC','accepted V4-15 ABS_RETURN_N:T1',%s,%s,true)",
        (TARGET,SCOPE,Jsonb({'contract':'FORWARD_PRICE_PATH_V1'}),Jsonb(['OBSERVED','UNKNOWN'])))
    for field in rows[0]['model_features']:
        pg.execute("insert into v4.field_registry values (%s,%s,'ACCEPTED_CORE_OWNER','model_features',%s,'SOURCE_FEATURE_CONTRACT',true,false,'SOURCE_DATE_LE_OBSERVATION_DATE',%s,'FEP_E5_WINDOW_V1')",
            (FEATURE,field,'BOOLEAN' if field in ('hh_progress','ll_progress') else 'NUMERIC',Jsonb(['OBSERVED','UNKNOWN'])))
        pg.execute('insert into v4.field_scope values (%s,%s,%s)',(FEATURE,field,SCOPE))
    mapping=[]
    for row,e in zip(rows,entries):
        cutoff=datetime.fromisoformat(row['trade_date']+'T07:00:00+00:00')
        pg.execute('insert into v4.observations values (%s,%s,%s,%s,%s,%s,%s,%s)',
            (row['observation_id'],SCOPE,row['entity_id'],row['trade_date'],'FIRST_PREWATCH:'+row['observation_id'],row['episode_id'],AUTH_CONTRACT,cutoff))
        recorded=pg.execute('select clock_timestamp()').fetchone()[0]
        pg.execute('insert into v4.reconstruction_authorities values (%s,%s,%s,%s,%s,%s,\'REPLAY\',%s,%s,%s,%s,%s,\'NOT_HISTORICALLY_OBSERVED\',false,false,false)',
            (e['authority_id'],AUTH_CONTRACT,SCOPE,NS,e['trade_date'],e['evidence_origin'],Jsonb(e['source_manifest']),e['source_manifest_digest'],FEATURE,Jsonb(e['accepted_head_identity']),recorded))
        manifest=dict(e['source_manifest'],reconstruction_authority=e['authority_id'])
        pg.execute("insert into v4.observation_revisions(observation_id,revision,publication_id,feature_cutoff,dependency_manifest,dependency_digest,enrichment_token,evidence_origin,execution_mode,created_at,authority_kind,reconstruction_authority_id) values (%s,1,null,%s,%s,%s,'NONE','RECONSTRUCTED_CORRECTED','REPLAY',clock_timestamp(),'HISTORICAL_RECONSTRUCTION',%s)",
            (row['observation_id'],cutoff,Jsonb(manifest),digest(manifest),e['authority_id']))
        snap=e['source_manifest']['snapshot_id']
        pg.execute('insert into v4.snapshots values (%s,%s,1,%s,%s,%s,clock_timestamp())',(snap,row['observation_id'],FEATURE,e['source_manifest']['feature_digest'],e['source_manifest']['quality_digest']))
        for field,v in e['source_manifest']['feature_entries'].items():
            pg.execute('insert into v4.feature_values values (%s,%s,%s,%s,%s,%s,%s)',(snap,FEATURE,field,Jsonb(v['value']),v['quality'],v['reason'],v['source_digest']))
        mapping.append(dict(source_observation_id=row['observation_id'],source_evidence_digest=row['original_e2_row_digest'],observation_id=row['observation_id'],scope_id=SCOPE,entity_id=row['entity_id'],trade_date=row['trade_date'],authority_kind='HISTORICAL_RECONSTRUCTION',reconstruction_authority_id=e['authority_id'],publication_id=None,observation_revision=1,snapshot_id=snap,feature_digest=e['source_manifest']['feature_digest'],quality_digest=e['source_manifest']['quality_digest'],feature_cutoff=cutoff.isoformat(),reconstructed_at=recorded.isoformat(),execution_mode='REPLAY',evidence_origin='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,FIRST_OBSERVED=False,REAL_OOS=False))
    models=[]
    for m in model_catalog:
        role='BASELINE' if m['stage']=='E2' else 'CHALLENGER';mid=m['model_id'];setid='FEP_CANONICAL_SET:'+digest([mid,role,VERSION])
        manifest=dict(source_artifact_bindings=m['artifact_references'],canonical_role=role,evidence_class=m['evidence_class'],new_training=False,
            upstream_diagnostics=m['canonical_import_diagnostics'])
        name='IMPORT:'+m['stage'];body=dict(model_id=mid,model_digest=m['artifact_digest'],model_family=m['model_family'],feature_contract_id=FEATURE,scope_id=SCOPE,target_id=TARGET,horizon=1,exact_import_manifest=manifest)
        contract(pg,name,body)
        pg.execute("insert into v4.models(model_id,training_run_id,scope_id,target_id,horizon,feature_contract_id,family,transform_digest,calibration_digest,ood_digest,model_digest,accepted_at,artifact_origin,import_contract_id,import_manifest) values (%s,null,%s,%s,1,%s,%s,%s,%s,%s,%s,clock_timestamp(),'ACCEPTED_ARTIFACT_IMPORT',%s,%s)",
            (mid,SCOPE,TARGET,FEATURE,m['model_family'],digest(manifest['upstream_diagnostics']['transform']),digest(manifest['upstream_diagnostics']['calibration']),digest(manifest['upstream_diagnostics']['OOD']),m['artifact_digest'],name,Jsonb(manifest)))
        pg.execute("insert into v4.model_sets values (%s,'FEP_E5_ENGINEERING_POLICY_V1',%s,clock_timestamp())",(setid,digest([setid,manifest])))
        pg.execute('insert into v4.model_set_members values (%s,%s,%s,1,%s,%s,%s)',(setid,SCOPE,TARGET,FEATURE,mid,role))
        gid='FEP_SHADOW_GRANT:'+digest([SCOPE,TARGET,FEATURE,setid,role])
        pg.execute("insert into v4.permission_keys values (%s,%s,%s,1,%s,%s,%s,'SHADOW_INFERENCE')",(gid,SCOPE,TARGET,FEATURE,setid,role))
        models.append(dict(m,canonical_model_set_id=setid,canonical_role=role,grant_id=gid))
    return mapping,models

def head(pg):
    row=pg.execute("select head_version,activation_id,grant_id from v4.deployment_heads where scope_id=%s and capability='SHADOW_INFERENCE' and target_id=%s and horizon=1 and feature_contract_id=%s",(SCOPE,TARGET,FEATURE)).fetchone()
    return row or (0,None,None)

def cas(pg, grant, action, request, *, expected=None, prior=None):
    h=head(pg);expected=h[0] if expected is None else expected;prior=h[1] if prior is None else prior
    aid='FEP_CANONICAL_ACTIVATION:'+request
    version=pg.execute('select v4.cas_deploy(%s,%s,%s,%s,%s,%s,%s,%s)',(grant,aid,action,expected,prior,request,digest([request,action]),Jsonb(dict(engineering_only=True)))).fetchone()[0]
    return dict(activation_id=aid,grant_id=grant,version=version,action=action,request_id=request)

def plan(pg, prior_record, mapping, model, cutoff, activation):
    slot='FEP_CANONICAL_SLOT:'+digest([prior_record['slot_id'],VERSION]);pid='FEP_CANONICAL_PREDICTION:'+digest([slot,model['model_id'],1]);rid='FEP_CANONICAL_RUN:'+digest(pid)
    deadline=(datetime.fromisoformat(cutoff)+timedelta(hours=1)).isoformat()
    pg.execute("insert into v4.prediction_slots values (%s,%s,%s,%s,1,%s,%s,%s,'SELECTED')",
        (slot,mapping['observation_id'],SCOPE,TARGET,model['model_family'],cutoff,deadline))
    pg.execute('insert into v4.slot_model_bindings values (%s,%s,%s,%s,1,%s,%s,%s)',(slot,mapping['observation_id'],SCOPE,TARGET,model['canonical_model_set_id'],cutoff,digest([slot,model['model_id'],activation])))
    return slot

def accept(pg, prior_record, mapping, model, cutoff, activation, *, fail_before_receipt=False):
    slot='FEP_CANONICAL_SLOT:'+digest([prior_record['slot_id'],VERSION]);pid='FEP_CANONICAL_PREDICTION:'+digest([slot,model['model_id'],1]);rid='FEP_CANONICAL_RUN:'+digest(pid)
    outputs={k:prior_record[k] for k in OUTPUT_FIELDS if k in prior_record};output_sha=digest(outputs)
    started=now()
    with pg.transaction():
        accepted=now()
        pg.execute("insert into v4.prediction_runs(run_id,publication_id,model_set_id,input_digest,started_at,finished_at,output_digest,counts,authority_kind,reconstruction_authority_id) values (%s,null,%s,%s,%s,%s,%s,%s,'HISTORICAL_RECONSTRUCTION',%s)",
            (rid,model['canonical_model_set_id'],digest([mapping['snapshot_id'],mapping['feature_digest'],mapping['quality_digest']]),started,accepted,output_sha,Jsonb(dict(expected=1,produced=1)),mapping['reconstruction_authority_id']))
        pg.execute("insert into v4.predictions values (%s,%s,1,%s,%s,%s,1,%s,%s,%s,%s,%s,'HISTORICAL_SIMULATION',%s,%s,%s,%s,%s,%s,null)",
            (pid,slot,mapping['observation_id'],SCOPE,TARGET,model['canonical_model_set_id'],model['model_id'],FEATURE,mapping['snapshot_id'],rid,prior_record['quality_state'],None if prior_record['projection_state']=='READY' else prior_record['projection_state'],Jsonb(outputs),Jsonb(dict(state=prior_record['support_state'])),output_sha,accepted))
        if fail_before_receipt:raise ValueError('FEP_INJECTED_ACCEPTANCE_FAILURE')
        pg.execute("insert into v4.acceptance_receipts values (%s,%s,%s,%s,%s,'FEP_E5_ENGINEERING_POLICY_V1',%s)",
            ('ACCEPT:'+pid,rid,accepted,model['grant_id'],activation['activation_id'],Jsonb(dict(engineering_only=True,model_display=False,priority_use=False))))
        payload=dict(source_slot_id=prior_record['slot_id'],prediction_id=pid,projection_state=prior_record['projection_state'])
        receipt_id='RECEIPT:'+pid
        pg.execute("insert into v4.slot_receipts values (%s,%s,%s,'ACCEPTED',%s,%s)",(slot,receipt_id,accepted,Jsonb(payload),digest(payload)))
    return dict(prediction_id=pid,run_id=rid,slot_id=slot,model_id=model['model_id'],model_set_id=model['canonical_model_set_id'],source_prediction_id=prior_record['prediction_id'],source_slot_id=prior_record['slot_id'],output_digest=output_sha,outputs=outputs,**mapping)

def inventory(pg):
    row=pg.execute("""SELECT (SELECT count(*) FROM v4.acceptance_receipts) AS acceptance_receipts, (SELECT count(*) FROM v4.activations) AS activations, (SELECT count(*) FROM v4.contracts) AS contracts, (SELECT count(*) FROM v4.dataset_eligibility_ledger) AS dataset_eligibility_ledger, (SELECT count(*) FROM v4.dataset_fold_cutoffs) AS dataset_fold_cutoffs, (SELECT count(*) FROM v4.dataset_fold_label_selection) AS dataset_fold_label_selection, (SELECT count(*) FROM v4.dataset_rows) AS dataset_rows, (SELECT count(*) FROM v4.datasets) AS datasets, (SELECT count(*) FROM v4.deployment_change_receipts) AS deployment_change_receipts, (SELECT count(*) FROM v4.deployment_heads) AS deployment_heads, (SELECT count(*) FROM v4.feature_values) AS feature_values, (SELECT count(*) FROM v4.field_registry) AS field_registry, (SELECT count(*) FROM v4.field_scope) AS field_scope, (SELECT count(*) FROM v4.label_revisions) AS label_revisions, (SELECT count(*) FROM v4.label_source_bindings) AS label_source_bindings, (SELECT count(*) FROM v4.model_set_members) AS model_set_members, (SELECT count(*) FROM v4.model_sets) AS model_sets, (SELECT count(*) FROM v4.models) AS models, (SELECT count(*) FROM v4.observation_revisions) AS observation_revisions, (SELECT count(*) FROM v4.observations) AS observations, (SELECT count(*) FROM v4.permission_keys) AS permission_keys, (SELECT count(*) FROM v4.prediction_runs) AS prediction_runs, (SELECT count(*) FROM v4.prediction_slots) AS prediction_slots, (SELECT count(*) FROM v4.predictions) AS predictions, (SELECT count(*) FROM v4.priority_projection) AS priority_projection, (SELECT count(*) FROM v4.priority_projection_grants) AS priority_projection_grants, (SELECT count(*) FROM v4.reconstruction_authorities) AS reconstruction_authorities, (SELECT count(*) FROM v4.reports) AS reports, (SELECT count(*) FROM v4.scopes) AS scopes, (SELECT count(*) FROM v4.signal_contract_registry) AS signal_contract_registry, (SELECT count(*) FROM v4.slot_model_bindings) AS slot_model_bindings, (SELECT count(*) FROM v4.slot_receipts) AS slot_receipts, (SELECT count(*) FROM v4.snapshots) AS snapshots, (SELECT count(*) FROM v4.targets) AS targets, (SELECT count(*) FROM v4.training_runs) AS training_runs""").fetchone()
    return dict(zip(TABLES,row))
