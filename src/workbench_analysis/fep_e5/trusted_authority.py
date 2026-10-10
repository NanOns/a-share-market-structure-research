"""Actual REV4 canonical DB reads; no new signature/grant protocol or activation.

DB snapshots are engineering evidence until the independent production Owner and
approval adapter are admitted. Caller dictionaries/connections never confer rights.
"""
import hashlib
import math
from pathlib import Path
from . import contracts

VERSION='FEP_CANONICAL_AUTHORITY_READ_R1'
IDENTITY=('scope_id','target_id','horizon','feature_contract_id','model_set_id','capability')
HEAD_KEY=('scope_id','target_id','horizon','feature_contract_id','capability')

def _read_prediction_sources(pg,one,request,model,result,at):
    """Read existing first-asof and label authority relationships, never reconstruct."""
    from workbench_analysis.fep_e1.contracts import digest
    required=('predictions','prediction_runs','acceptance_receipts','snapshots',
              'observation_revisions','training_runs','dataset_rows','label_revisions','label_source_bindings')
    missing=[t for t in required if pg.execute('select to_regclass(%s)',('fep.'+t,)).fetchone()[0] is None]
    if missing:
        result['errors'].append('CANONICAL_PREDICTION_SOURCE_TABLES_MISSING:'+','.join(missing));return
    if not request.get('prediction_id'):
        result['errors'].append('EXACT_PREDICTION_OWNER_ID_REQUIRED');return
    pred=one('predictions',('prediction_id',),(request['prediction_id'],))
    if any(pred.get(k)!=request[k] for k in IDENTITY[:-1]) or pred['model_id']!=model['model_id']:
        raise ValueError('PREDICTION_EXACT_MODEL_BINDING_MISMATCH')
    run=one('prediction_runs',('run_id',),(pred['run_id'],))
    accepted=one('acceptance_receipts',('run_id','grant_id'),(pred['run_id'],result['sources']['grant']['grant_id']))
    snap=one('snapshots',('snapshot_id',),(pred['snapshot_id'],))
    revision=one('observation_revisions',('observation_id','revision'),(snap['observation_id'],snap['observation_revision']))
    for key,row in (('prediction',pred),('run',run),('acceptance',accepted),('snapshot',snap),('first_asof',revision)):
        result['sources'][key]=row
    if pred['prediction_evidence']!='FIRST_OBSERVED' or revision['evidence_origin']!='PIT_OBSERVED' or revision['execution_mode']!='PRODUCTION':
        raise ValueError('PREDICTION_OR_INPUT_NOT_AS_RECORDED')
    if revision['dependency_digest']!=digest(revision['dependency_manifest']):
        raise ValueError('FROZEN_INPUT_MANIFEST_DIGEST_MISMATCH')
    cutoff=contracts.utc(revision['feature_cutoff'])
    if cutoff>contracts.utc(at) or contracts.utc(pred['accepted_at'])>contracts.utc(at):
        raise ValueError('FUTURE_PREDICTION_SOURCE')
    # Actual first-availability needs source-owner entries, not only a snapshot clock.
    entries=revision['dependency_manifest'].get('sources')
    if not isinstance(entries,list) or not entries or any(not e.get('source_owner') or not e.get('sha256') or contracts.utc(e['first_available_at'])>cutoff for e in entries):
        raise ValueError('FIRST_AVAILABLE_SOURCE_OWNER_NOT_VERIFIED')
    if accepted['activation_id']!=result['sources']['head']['activation_id'] or run['model_set_id']!=request['model_set_id'] or accepted.get('checks',{}).get('engineering_only'):
        raise ValueError('PREDICTION_ACCEPTANCE_BINDING_NOT_PRODUCTION')
    if snap['observation_id']!=pred['observation_id'] or snap['feature_contract_id']!=request['feature_contract_id'] or run['output_digest']!=pred['output_digest'] or run['publication_id']!=revision['publication_id'] or contracts.utc(run['finished_at'])>contracts.utc(accepted['accepted_at']) or contracts.utc(accepted['accepted_at'])>contracts.utc(at):
        raise ValueError('PREDICTION_RUN_SNAPSHOT_ACCEPTANCE_LINEAGE_MISMATCH')
    if pred['output_digest']!=digest(pred['outputs']):
        raise ValueError('FROZEN_PREDICTION_OUTPUT_MUTATION')
    result['first_asof_verified']=True
    if not model.get('training_run_id'):
        result['errors'].append('REAL_TRAINING_MATURITY_OWNER_MISSING');return
    training=one('training_runs',('training_run_id',),(model['training_run_id'],))
    result['sources']['training_run']=training
    labels=pg.execute('''select to_jsonb(l),to_jsonb(b) from fep.dataset_rows d
        join fep.label_revisions l on l.observation_id=d.observation_id and l.target_id=d.target_id and l.revision=d.label_revision
        join fep.label_source_bindings b on b.binding_id=l.binding_id
        where d.dataset_id=%s and d.scope_id=%s and d.feature_contract_id=%s and d.target_id=%s and d.fold_id=%s and d.partition_name='FIT' ''',
        (training['dataset_id'],request['scope_id'],request['feature_contract_id'],request['target_id'],training['fold_id'])).fetchall()
    if not labels or any(l['horizon']!=request['horizon'] or l['training_allowed'] is not True or contracts.utc(b['label_training_mature_at'])>contracts.utc(training['fit_started_at']) or contracts.utc(b['label_revision_available_at'])>contracts.utc(training['fit_started_at']) for l,b in labels):
        raise ValueError('REAL_MATURE_FIT_SAMPLE_NOT_VERIFIED')
    result['mature_observed_count']=len(labels)
    fields=pred['outputs'].get('fields',{})
    names=('return_expectancy','downside_risk','return_quantiles','prediction_revision','model_display','priority_use')
    if any(fields.get(k,{}).get('status')!='READY' or fields[k].get('value') is None for k in names):
        raise ValueError('PREDICTION_FIELDS_NOT_READY')
    numeric=lambda v:type(v) in (int,float) and math.isfinite(v)
    quantiles=fields['return_quantiles']['value']
    if not numeric(fields['return_expectancy']['value']) or not numeric(fields['downside_risk']['value']) or not isinstance(quantiles,list) or not quantiles or not all(numeric(v) for v in quantiles) or quantiles!=sorted(quantiles) or type(fields['prediction_revision']['value']) is not int or fields['prediction_revision']['value']!=pred['revision'] or type(fields['model_display']['value']) is not bool or type(fields['priority_use']['value']) is not bool:
        raise ValueError('PREDICTION_FIELD_VALUE_SCHEMA_INVALID')
    result['candidate_fields']=fields;result['candidate_output_status']='READY_ENGINEERING_EVIDENCE_ONLY'

def _empty():
    return dict(contract_id=VERSION,status='TRUSTED_AUTHORITY_UNAVAILABLE',production_authorized=False,
        formal_owner=None,registry_verified=False,first_asof_verified=False,deployment_head_verified=False,
        cas_receipt_verified=False,independent_approval_verified=False,errors=[],sources={})

def resolve_current_sources(root):
    """Discover real design/engineering artifacts, never implicitly select a DSN."""
    root=Path(root).resolve();result=_empty()
    for relative in ('reports/fep_e5_r1/MODEL_CATALOG.json','config/fep_scope_registry_v1.json',
                     'config/fep_target_registry_v1.json','config/fep_e5_model_evidence_class_v1.json'):
        path=root/relative
        if path.is_file():
            raw=path.read_bytes()
            result['sources'][relative]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                evidence_role='DESIGN_OR_HISTORICAL_ENGINEERING_ONLY')
    result['errors']=['FORMAL_PRODUCTION_DB_OWNER_NOT_ADMITTED',
        'CURRENT_INDEPENDENT_CAPABILITY_APPROVAL_SOURCE_MISSING',
        'MODEL_REVISION_PRODUCTION_REGISTRY_MISSING','AS_RECORDED_MATURE_PREDICTION_OWNER_MISSING']
    return result

def read_canonical_candidate(pg,request,*,at):
    """Read actual registry/Head/activation/CAS in a single readonly DB snapshot.

    Always engineering candidate only. No accepted Head, grant, frozen row or
    scoring operation is written. Caller must provide a fresh idle connection;
    externally admitted production connection/approval remain separate boundaries.
    """
    from psycopg import sql, Error
    from psycopg.pq import TransactionStatus
    result=_empty();result['evidence_trust']='ACTUAL_DB_READ_ENGINEERING_CANDIDATE'
    if any(request.get(k) is None for k in IDENTITY) or type(request.get('model_revision')) is not int or request['model_revision']<=0:
        result['errors']=['EXACT_REQUEST_AND_MODEL_REVISION_REQUIRED'];return result
    if request['capability'] not in ('MODEL_DISPLAY','PRIORITY_USE'):
        result['errors']=['SHADOW_CAPABILITY_CANNOT_AUTHORIZE_PRODUCTION'];return result
    def one(table,keys,values):
        query=sql.SQL('select to_jsonb(t) from fep.{} t where {}').format(sql.Identifier(table),
            sql.SQL(' and ').join(sql.SQL('{}=%s').format(sql.Identifier(k)) for k in keys))
        rows=pg.execute(query,tuple(values)).fetchall()
        if len(rows)!=1:raise ValueError('CANONICAL_OWNER_NOT_UNIQUE:'+table)
        return rows[0][0]
    try:
        if pg.info.transaction_status!=TransactionStatus.IDLE:
            raise ValueError('FRESH_READ_ONLY_CONNECTION_REQUIRED')
        with pg.transaction():
            pg.execute('set transaction isolation level repeatable read read only')
            meta=pg.execute("select current_database(),current_user,current_setting('transaction_read_only'),current_setting('transaction_isolation'),txid_current_snapshot()::text").fetchone()
            result['read_snapshot']=dict(database=meta[0],role=meta[1],read_only=meta[2],isolation=meta[3],snapshot=meta[4])
            head=one('deployment_heads',HEAD_KEY,[request[k] for k in HEAD_KEY])
            grant=one('permission_keys',('grant_id',),(head['grant_id'],))
            activation=one('activations',('activation_id',),(head['activation_id'],))
            receipt=one('deployment_change_receipts',('activation_id',),(head['activation_id'],))
            member_keys=('model_set_id','scope_id','target_id','horizon','feature_contract_id')
            member=one('model_set_members',member_keys+('role',),[request[k] for k in member_keys]+['CHAMPION'])
            model=one('models',('model_id',),(member['model_id'],))
            model_set=one('model_sets',('model_set_id',),(request['model_set_id'],))
            for name,row in (('head',head),('grant',grant),('activation',activation),('cas_receipt',receipt),('model',model),('model_set',model_set),('model_member',member)):
                result['sources'][name]=row
            if any(grant.get(k)!=request[k] or head.get(k)!=request[k] for k in IDENTITY):
                raise ValueError('EXACT_GRANT_HEAD_BINDING_MISMATCH')
            if grant.get('model_role')!='CHAMPION' or member.get('role')!='CHAMPION':
                raise ValueError('ACCEPTED_CHAMPION_REQUIRED')
            if activation['action']!='ALLOW' or contracts.utc(activation['effective_at'])>contracts.utc(at):
                raise ValueError('CURRENT_HEAD_REVOKED_OR_FUTURE')
            if activation['grant_id']!=head['grant_id'] or receipt['grant_id']!=head['grant_id'] or receipt['new_head_version']!=head['head_version'] or receipt['expected_head_version']+1!=head['head_version'] or activation['expected_head_version']!=receipt['expected_head_version'] or receipt.get('expected_prior_activation_id')!=activation.get('prior_activation_id'):
                raise ValueError('CURRENT_HEAD_CAS_RECEIPT_MISMATCH')
            result.update(registry_verified=True,deployment_head_verified=True,cas_receipt_verified=True)
            # model_id/model_digest are immutable; prediction.revision is not model_revision.
            if model.get('import_manifest',{}).get('model_revision')!=request['model_revision']:
                raise ValueError('MODEL_REVISION_PRODUCTION_REGISTRY_MISSING')
            if receipt.get('checks',{}).get('engineering_only'):
                result['errors'].append('ENGINEERING_CAS_NOT_PRODUCTION_APPROVAL')
            _read_prediction_sources(pg,one,request,model,result,at)
            result['errors'].append('CURRENT_INDEPENDENT_CAPABILITY_APPROVAL_SOURCE_MISSING')
            result['status']='CANONICAL_AUTHORITY_CANDIDATE_VERIFIED'
    except (ValueError,KeyError,TypeError,AttributeError) as exc:
        result['errors'].append(str(exc))
    except Error as exc:
        result['errors'].append('CANONICAL_DB_READ_FAILED:'+type(exc).__name__)
    return result
