"""Path A engineering projection of exact historical accepted V4-03 owner."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

from workbench_analysis.fep_e1.contracts import atomic_json, digest, instant
from workbench_analysis.fep_e1 import feature_owner, observation, snapshots

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports/fep_e1_r2_final'


def bind(path):
    p=ROOT/path; sha=hashlib.sha256(); size=0
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            sha.update(chunk); size+=len(chunk)
    return dict(path=path,bytes=size,sha256=sha.hexdigest())


def load(path):
    return json.loads((ROOT/path).read_bytes())


def run():
    head_path='data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json'
    head=load(head_path)
    receipt_ref=head['evidence_bindings']['reports/v4_03/V4_03_FINAL_STAGE_RECEIPT_R1_20260928.json']
    receipt=load(receipt_ref['path'])
    owner='reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz'
    schema=load('config/v4_03_output_schema_v1.json')
    fields=[dict(field_name=f['field_id'],owner_stage='V4-03',
                 value_path=['fields',f['field_id'],'value'],quality_path=['fields',f['field_id'],'quality_state'],
                 source_digest_path=['fields',f['field_id'],'output_digest'],window_identity_path=['fields',f['field_id'],'window_identity'],
                 data_type=f['type'],unit=f['unit'],nullable=f['nullable'],required=True,
                 entity_key_path=['security_id'],trade_date_path=['trade_date'],
                 mapping_status='IMPLEMENTED_EXACT_MAPPING_ENGINEERING',unit_transform='IDENTITY',
                 evidence_origin='RECONSTRUCTED_ASOF',availability='Exact engineering read receipt only; historical first availability NOT_PROVEN')
            for f in schema['fields']]
    contract=dict(contract_id=feature_owner.CONTRACT,version='1.0.0',engineering_path='A_ACCEPTED_HISTORICAL_OWNER',
                  owner_head=bind(head_path),owner_receipt=bind(receipt_ref['path']),owner_artifact=bind(owner),
                  field_registry=bind('config/v4_03_field_registry_v1.json'),output_schema=bind('config/v4_03_output_schema_v1.json'),
                  algorithm_contract=bind('config/v4_03_algorithm_contracts_v1.json'),parameter_contract=bind('config/v4_03_parameter_set_v1.json'),
                  calendar=bind('data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/calendar_sse_20230704_20260924.json'),
                  universe=bind('data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz'),
                  adjustment_identity=bind('data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet'),
                  trade_date='2026-09-24',evidence_origin='RECONSTRUCTED_ASOF',
                  AS_RECORDED=False,FIRST_OBSERVED=False,production=False,shadow=False,
                  registry_acceptance_basis='Exact registry plus field/type/unit parity with accepted V4-03 output schema; no formula implementation',
                  historical_source_available_at='NOT_PROVEN',real_first_observed='NOT_GRANTED_WAIT_REAL_SESSION',fields=fields)
    for field in fields:
        field.update(owner_head=contract['owner_head'],owner_artifact=contract['owner_artifact'],
                     owner_publication_identity=dict(receipt=contract['owner_receipt'],
                                                     accepted_candidate_commit=receipt['accepted_candidate_commit']),
                     trade_date=contract['trade_date'])
    atomic_json(ROOT/'config/fep_feature_owner_contract_v1.json',contract)
    feature_owner.validate_contract(ROOT,contract)
    selected=None; rows=0; quality_counts={f['field_name']:dict(OBSERVED=0,UNKNOWN=0) for f in fields}
    with gzip.open(ROOT/owner,'rt',encoding='utf8') as f:
        for line in f:
            row=json.loads(line)
            projection=feature_owner.project_row(row,contract)
            for name,value in projection['values'].items():quality_counts[name][value['quality']]+=1
            if selected is None and all(v['quality']=='OBSERVED' for v in projection['values'].values()):selected=row
            rows+=1
    if selected is None:raise ValueError('FEP_ENGINEERING_COMPLETE_NUMERIC_VECTOR_NOT_FOUND')
    projection=feature_owner.read(ROOT,contract,entity_id=selected['security_id'],trade_date=selected['trade_date'])
    projection_path='reports/fep_e1_r2_final/OWNER_ROW_PROJECTION.json'
    atomic_json(ROOT/projection_path,projection)
    # Capture time proves this engineering materialization is readable now. It
    # does not claim historical owner publication availability or PIT observation.
    capture=datetime.now(timezone.utc).isoformat()
    receipt=dict(contract_id='FEP_ENGINEERING_OWNER_READ_RECEIPT_V1',
                 available_at=capture,origin='LOCAL_EXACT_ENGINEERING_READ',
                 historical_first_availability='NOT_PROVEN',source_artifact=contract['owner_artifact'],
                 source_row_digest=projection['source_row_digest'],projection=bind(projection_path),
                 AS_RECORDED=False,FIRST_OBSERVED=False,production=False,shadow=False)
    receipt_path='reports/fep_e1_r2_final/OWNER_ENGINEERING_READ_RECEIPT.json'
    atomic_json(ROOT/receipt_path,receipt)
    deps={k:'NONE' for k in snapshots.DEPENDENCIES}
    sources=dict(publication=projection_path,accepted_head=head_path,
                 algorithm_contract=contract['algorithm_contract']['path'],
                 parameter_contract=contract['parameter_contract']['path'],
                 calendar=contract['calendar']['path'],feature_contract='config/fep_feature_owner_contract_v1.json')
    for k in ('universe','adjustment_basis'):
        ref=contract['universe' if k=='universe' else 'adjustment_identity']
        path=f'reports/fep_e1_r2_final/{k.upper()}_EXACT_SOURCE_READBACK.json'
        atomic_json(ROOT/path,dict(contract_id='FEP_EXACT_UPSTREAM_READBACK_V1',source=ref,
                                  engineering_read_receipt=bind(receipt_path),
                                  universe_snapshot_id=selected['universe_snapshot_id'],
                                  source_row_digest=projection['source_row_digest']))
        sources[k]=path
    for k,path in sources.items():
        deps[k]=bind(path)|dict(system_available_at=datetime.now(timezone.utc).isoformat())
    cutoff=max((b['system_available_at'] for b in deps.values() if b!='NONE'),key=instant)
    scope=dict(scope_id='FEP_STOCK_ENTRY_CORE',status='ENGINEERING_ENABLED')
    obs=observation.build(scope,entity_id=selected['security_id'],trade_date=selected['trade_date'],
                          signal_key='ENGINEERING_OWNER_READ:'+projection['source_row_digest'],
                          episode_key='ENGINEERING_HISTORICAL_ROW',slot_deadline=cutoff,
                          core_signal_contract_id='FEP_ENGINEERING_OWNER_READ_V1')
    registry=dict(fields=[dict(field_name=f['field_name'],status='IMPLEMENTED_EXACT_MAPPING',
                              required=f['required'],nullable=f['nullable'],data_type=f['data_type'],
                              allowed_scopes=['FEP_STOCK_ENTRY_CORE'],quality_allowlist=['OBSERVED','UNKNOWN'],
                              dependency_key='publication',field_path=['values',f['field_name'],'value'],
                              quality_path=['values',f['field_name'],'quality']) for f in fields])
    created=datetime.now(timezone.utc).isoformat()
    snapshot=snapshots.build(ROOT,obs,1,deps,projection['values'],registry,
                             feature_cutoff=cutoff,created_at=created,evidence_origin='RECONSTRUCTED_ASOF',execution_mode='REPLAY')
    repeated=snapshots.build(ROOT,obs,1,deps,projection['values'],registry,
                             feature_cutoff=cutoff,created_at=datetime.now(timezone.utc).isoformat(),
                             evidence_origin='RECONSTRUCTED_ASOF',execution_mode='REPLAY')
    assert snapshot['feature_digest']==repeated['feature_digest']
    atomic_json(REPORT/'ENGINEERING_OBSERVATION.json',obs)
    atomic_json(REPORT/'ENGINEERING_SNAPSHOT.json',snapshot)
    atomic_json(REPORT/'ENGINEERING_MAPPING_REGISTRY.json',registry)
    atomic_json(REPORT/'FEATURE_47_FIELD_READBACK.json',dict(status='PASS',owner_contract=bind('config/fep_feature_owner_contract_v1.json'),
                row_count=rows,field_count=47,quality_counts=quality_counts,full_inventory='ALL_OWNER_ROWS_47_ENVELOPES_VALIDATED',
                selected_entity=selected['security_id'],selected_trade_date=selected['trade_date'],
                source_row_digest=projection['source_row_digest'],values=projection['values'],adapter_readback='EXACT_OWNER_ENVELOPES_NO_RECALCULATION'))
    atomic_json(REPORT/'ENGINEERING_SNAPSHOT_READBACK.json',dict(status='PASS',evidence_origin='RECONSTRUCTED_ASOF',
                execution_mode='REPLAY',AS_RECORDED=False,FIRST_OBSERVED=False,
                observation=bind('reports/fep_e1_r2_final/ENGINEERING_OBSERVATION.json'),
                snapshot=bind('reports/fep_e1_r2_final/ENGINEERING_SNAPSHOT.json'),
                consumed_owner_row_digest=projection['source_row_digest'],feature_count=47,
                deterministic_same_capture=True,feature_digest=snapshot['feature_digest'],dependency_manifest=deps,
                slot_boundary_semantics='ENGINEERING_READ_CEILING_ONLY_NOT_PREDICTION_DEADLINE',prediction_deadline='NOT_ENABLED'))
    atomic_json(REPORT/'FEATURE_OWNER_ADAPTER_GATE.json',dict(status='PASS',contract_id=feature_owner.CONTRACT,
                FEP_FEATURE_MAPPING_ENGINEERING='PASS',FEP_FEATURE_COUNT=47,engineering_path='A_ACCEPTED_HISTORICAL_OWNER',
                guessed_aliases=0,latest_or_mtime=0,factor_reimplementation=False,historical_cutoff='2026-09-24',
                current_2026_09_30_47_field_owner='NOT_CREATED_NOT_REQUIRED_FOR_ENGINEERING',
                contract=bind('config/fep_feature_owner_contract_v1.json')))
    atomic_json(REPORT/'REAL_FIRST_OBSERVED_GATE.json',dict(status='NOT_GRANTED_WAIT_REAL_SESSION',
                CURRENT_REAL_MATURITY_EVIDENCE='NONE',PROVED_HORIZONS=[],real_training_bindings=0,
                AS_RECORDED=False,FIRST_OBSERVED=False,production=False,shadow=False,focus=False,
                accepted_head_promotion=False,E2='NOT_AUTHORIZED_UNTIL_EXTERNAL_AUDIT'))
    print('Historical accepted owner engineering:',rows,'rows x 47; deterministic reconstructed snapshot PASS')


if __name__=='__main__':run()
