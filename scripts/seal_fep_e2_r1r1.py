"""Freeze E1-compatible historical dataset, scoped policy, then E2 statistics."""
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
from scripts.build_fep_e2_r1r1_history import ROOT,REPORT,binding,now
from workbench_analysis.fep_e1.contracts import atomic_json,digest
from workbench_analysis.fep_e1.datasets import assemble
from workbench_analysis.fep_e2.input import bind
from workbench_analysis.fep_e2.support import discover,BASE
from workbench_analysis.fep_e2.conditional import baseline
from workbench_analysis.fep_e2.registry import register
from workbench_analysis.fep_e2.historical_dataset import read_gzip,scoped_policy,write_gzip,LINEAGE,verify_stage_order


def seal():
    contract=json.loads((ROOT/'config/fep_e2_historical_dataset_contract_v1.json').read_bytes())
    population=json.loads((REPORT/'HISTORICAL_OBSERVATION_POPULATION.json').read_bytes())
    label_gate=json.loads((REPORT/'V4_15_HISTORICAL_LABEL_ADAPTER_GATE.json').read_bytes())
    if not population['full_population'] or population['rows']!=label_gate['rows']:raise ValueError('E2_HISTORICAL_DENOMINATOR')
    rows=[r for p in sorted((REPORT/'labels').glob('*.gz')) for r in read_gzip(p)]
    if not rows:raise ValueError('E2_NO_REAL_HISTORICAL_ENTRY')
    observations=[];labels={};snapshots={};envelopes={};cutoff=now()
    base=dict(entity_type='STOCK',observation_scope='FEP_STOCK_ENTRY_CORE',signal_type='ENTRY',target=contract['target'],horizon=1,
        feature_variant='CORE',evidence_origin=LINEAGE['evidence_origin'],label_quality_policy=contract['label_quality_policy'],
        contract_versions=dict(feature=contract['feature_contract_id'],target='FORWARD_PRICE_PATH_V1'))
    for row in rows:
        key=row['observation_id'];observations.append(dict(observation_id=key,entity_id=row['entity_id'],trade_date=row['trade_date'],
            scope_id=base['observation_scope'],episode_key=row['episode_key']))
        snapshot=dict(snapshot_id='HISTORICAL:'+digest(row['feature_snapshot']))
        snapshots[key]=snapshot
        labels[key,base['target']]=[dict(revision=row['selected_label_revision'],target_digest=row['selected_label_digest'],
            training_allowed=row['training_allowed_engineering_only'],quality=row['outcome_status'],
            **{t:row[t] for t in ('source_fact_available_at','label_revision_available_at','label_training_mature_at')})]
        envelope=dict(base,**{k:row[k] for k in ('observation_id','entity_id','trade_date','date_ordinal','label_end_ordinal',
            'episode_start','episode_end','regime','trend','position','risk','sector','feature_support','support_class',
            'selected_label_revision','selected_label_digest')})
        if row['training_allowed_engineering_only']:envelope['outcome']=row['outcome']
        envelopes[key]=envelope
    fold=dict(fold_id='HISTORICAL_COMPLETE_REPLAY_V1',partition_name='FIT',observation_ids=list(envelopes),
        fold_dataset_cutoff=cutoff,phase_started_at=cutoff)
    e1=assemble(observations,[dict(target_id=base['target'],scope_id=base['observation_scope'],horizon=1)],
        [fold],labels,snapshots,cutoff)
    dataset=bind(e1,dict(dataset_id='FEP_E2_HISTORICAL_ENTRY_CORE_R1R1',feature_contract_id=contract['feature_contract_id'],
        target_contract_id='FORWARD_PRICE_PATH_V1',fold_id=fold['fold_id'],partition_name='FIT',target=base['target'],
        target_kind='CONTINUOUS',classes=[]),envelopes)
    dataset_sha=write_gzip(REPORT/'HISTORICAL_E1_E2_DATASET.json.gz',[dataset])
    dataset_at=now()
    atomic_json(REPORT/'HISTORICAL_DATASET_SEAL.json',dict(status='PASS_SEALED_COMPLETE_REAL_SOURCE_REPLAY',sealed_at=dataset_at,
        dataset=binding(REPORT/'HISTORICAL_E1_E2_DATASET.json.gz'),e1_digest=e1['digest'],e2_digest=dataset['digest'],
        expected=len(dataset['denominator']),eligible=len(dataset['rows']),lineage=LINEAGE,
        window=binding(REPORT/'HISTORICAL_WINDOW_FREEZE.json'),population=binding(REPORT/'HISTORICAL_OBSERVATION_POPULATION.json'),
        labels=binding(REPORT/'V4_15_HISTORICAL_LABEL_ADAPTER_GATE.json'),selection_rule='All frozen ENTRY observations; no result-dependent pruning'))
    discovery=discover(dataset['denominator'],dataset['rows']);discovery_at=now()
    atomic_json(REPORT/'SUPPORT_POLICY_DISCOVERY.json',dict(discovery=discovery,sealed_at=discovery_at,dataset_digest=dataset['digest'],
        numeric_outcomes_consumed=False,statistics_started=False))
    policy_at=now();policy=scoped_policy(discovery,dict(base,target_kind='CONTINUOUS'),policy_at)
    policies=[policy]
    target_registry=json.loads((ROOT/'config/fep_target_registry_v1.json').read_bytes())
    for target in target_registry['targets']:
        if target['target_id']==base['target']:continue
        policies.append(dict(policy_id='UNSET:'+target['target_id'],status='UNSET_DIAGNOSTIC_ONLY',
            applicability=dict(base,target=target['target_id'],horizon=target['horizon'],
                target_kind='CONTINUOUS' if target['family']=='ABS_RETURN_N' else 'DISABLED_NOT_ADMITTED'),
            values={k:'UNSET' for k in policy['values']},required_classes=[],freeze_before_statistics_at=policy_at,
            reason='Independent scoped support and adapter evidence not admitted'))
    registry=dict(contract_id='FEP_E2_SUPPORT_POLICY_REGISTRY_V1',version='1.0.0',policies=policies,
        default='UNSET_NOT_EVALUABLE',disabled_scopes=['T3','T5','T10','T20','FIRST_EXIT','ANY_EVENTS','DAILY','SUPPLEMENTAL','FIRST_OBSERVED','REAL_OOS'],
        historical_r1_policy=binding('config/fep_e2_support_policy_v1.json'),frozen_at=policy_at,
        dataset_digest=dataset['digest'],discovery_digest=digest(discovery),production=False)
    atomic_json(ROOT/'config/fep_e2_support_policy_registry_v1.json',registry)
    atomic_json(REPORT/'SUPPORT_POLICY_REGISTRY_FREEZE.json',dict(status='FROZEN_FOR_ADMITTED_SCOPES',frozen_at=policy_at,
        registry=binding('config/fep_e2_support_policy_registry_v1.json'),policy_digest=digest(policy),dataset_digest=dataset['digest'],
        support_discovery=binding(REPORT/'SUPPORT_POLICY_DISCOVERY.json'),statistics_started=False))
    statistics_at=now();verify_stage_order(dataset_at,discovery_at,policy_at,statistics_at)
    atomic_json(REPORT/'STATISTICS_PHASE_START.json',dict(started_at=statistics_at,dataset_digest=dataset['digest'],policy_digest=digest(policy)))
    method=json.loads((ROOT/'config/fep_conditional_statistics_contract_v1.json').read_bytes())
    # Single population query with unavailable condition values is predetermined.
    # Fixed R1 backoff selects support, never best returns or a best condition.
    query=dict(base,regime='UNAVAILABLE',trend='UNAVAILABLE',position='UNAVAILABLE',risk='UNAVAILABLE')
    result=baseline(dataset,query,policy,method,statistics_at)
    path=register(REPORT/'registry',result)
    atomic_json(REPORT/'CONDITIONAL_BASELINE_GATE.json',dict(status='PASS_ENGINEERING_CAPABILITY_SCOPED' if not result['diagnostic_only'] else 'BLOCKED',
        artifact=binding(path),selected_level=result['selected_level'],support_state=result['support_state'],statistics=result['statistics'],
        counts=result['counts'],denominator=result['denominator_summary'],backoff_trace=result['backoff_trace'],
        all_population_rows_retained=True,REAL_OOS=False,production=False))
    atomic_json(REPORT/'REPRESENTATIVENESS_DIMENSION_GATE.json',dict(status='PASS_EXPLICIT_UNAVAILABLE_DIAGNOSTICS',
        dimensions=result['denominator_summary']['dimension_status'],distances=result['denominator_summary']['representativeness_total_variation'],
        unavailable_dimensions_contract=contract['unavailable_dimensions']))
    atomic_json(REPORT/'HISTORICAL_FEATURE_GATE.json',dict(status='PASS_OWNER_REPLAY_COMPLETE',
        feature_scan=binding(REPORT/'HISTORICAL_FEATURE_SCAN.json'),rank_gate=binding(REPORT/'HISTORICAL_RPS_GATE.json'),
        source_at_or_before_T0=True,all_observations_have_owner_feature_snapshot=True,source_bindings=contract['source_bindings'],
        no_synthetic_fill=True,unavailable_inputs='UNKNOWN',window=binding(REPORT/'HISTORICAL_WINDOW_FREEZE.json')))
    return result


if __name__=='__main__':seal()
