"""Seal the seven authorized tasks; external acceptance remains a later gate."""
from scripts.next_round_execution_r3 import *
from copy import deepcopy
import json

REGISTRY='reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R15_BATCH_R3_FINAL.json'

def close():
    entry=verify_protected()
    summary=read('reports/v4_11_r3/V4_11_R3_FULL_MARKET_SUMMARY.json')
    oracle=read('reports/v4_11_r3/V4_11_R3_INDEPENDENT_ORACLE.json')
    scoped=read('reports/audits/next_round_r3/scoped_promotions/HANDOFF_R2.json')
    if oracle['status']!='PASS' or summary['eligible_universe']!=5224:raise ValueError('REAL_SOURCE_ORACLE_AND_MARKET_SCOPE_REQUIRED')
    receipts={
        'R3A':'reports/v4_11_r3a/R3A_STAGE_CLOSURE.json',
        'R3B':'reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json',
        'R3C':'reports/v4_11_r3/V4_11_R3_EXTERNAL_REAUDIT_HANDOFF.json',
        'A02/A05/A04':'reports/audits/next_round_r3/scoped_promotions/HANDOFF_R2.json',
        'Parallel Consolidation':'reports/next_round_r3/scoped_consolidation/STAGE_CLOSURE_R4.json',
    }
    statuses={k:read(p).get('status',read(p).get('acceptance_result')) for k,p in receipts.items()}
    stages=dict(R3A=statuses['R3A'],R3B=statuses['R3B'],R3C=statuses['R3C'],
        **scoped['task_statuses'],Parallel_Consolidation=statuses['Parallel Consolidation'])
    parent='reports/audits/V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R13_CONSOLIDATION_R3.json'
    registry=deepcopy(read(parent));registry['parent_registry']=bind(parent)
    registry['batch_contract']='V4_NEXT_ROUND_EXECUTION_R3_SEVEN_TASK_CLOSURE_V1'
    for item in ('A02','A05','A04'):
        registry['entries'][item].update(current_batch_status=scoped['task_statuses'][item],current_batch_handoff=bind(receipts['A02/A05/A04']))
    registry['independent_audit_items']={
        'AUD_R3C_D2_ADMISSION_AND_PRIOR_AUTHENTICITY':dict(scope='Real sealed-file candidate admission, exact V4-10 business AST, actual prior 9/29 bootstrap; independent of scoped promotions',
            evidence=[bind('reports/v4_11_r3/V4_11_R3_D2_ADAPTER_AST_EVIDENCE.json'),bind('reports/v4_11_r3/V4_11_R3_D2_READBACK.json')],
            engineering_acceptance='REAL_REEXECUTION_PASS_CANDIDATE_ONLY',external_acceptance='PENDING_NEXT_INDEPENDENT_AUDIT',blocks_authorized_mainline=False),
        'AUD_R3C_EVENT_PRIOR_UNKNOWN_01':dict(scope='Prior UNKNOWN must never imply known not-confirmed; raw exact predicates retained, effective events fail closed',
            evidence=[bind('reports/v4_11_r3/INDEPENDENT_CODE_REVIEW.json'),bind('reports/v4_11_r3/V4_11_R3_EVENT_REPLAY.json')],
            engineering_acceptance='FIXED_AND_REAL_REPLAY_VERIFIED',external_acceptance='PENDING_NEXT_INDEPENDENT_AUDIT',blocks_authorized_mainline=False),
        'AUD_R3C_ACCEPTED_SUSPENSION_STATE_ADMISSION_01':dict(scope='Accepted dated SUSPENDED states admitted explicitly; absent historical states remain UNKNOWN',
            evidence=[bind('src/v4/confirmation_d2_upstream_r3.py'),bind('config/v4_11_r3c_candidate_d2_contract_v3.json')],
            engineering_acceptance='EXPLICIT_ACCEPTED_STATE_ADMISSION_R2',external_acceptance='PENDING_NEXT_INDEPENDENT_AUDIT',blocks_authorized_mainline=False),
        'AUD_R3_REAL_WINDOW_AND_EPISODE_CAPABILITY':dict(scope='Original 101-session coordinate gate, missing observations, frozen episode and LOO admission, V4-12 invalidation unavailable',
            evidence=[bind('reports/v4_11_r3a/INDEPENDENT_ORACLE.json'),bind('reports/v4_11_r3b/R3B_SEALED_PRODUCER_SET.json')],
            engineering_acceptance='EXPLICIT_UNKNOWN_DIAGNOSTIC_BOUNDARIES',external_acceptance='PENDING_CAPABILITY_SCOPED_REAUDIT',blocks_authorized_mainline=False),
        'AUD_A04_AMOUNT_A_FORWARD_CONSUMER':dict(scope='Independent Amount-A consumer H21 warmup; producer scoped acceptance does not authorize formal consumer',
            evidence=[bind(receipts['A02/A05/A04'])],engineering_acceptance='PRODUCER_SCOPED_ACCEPTED_CONSUMER_WARMUP',
            external_acceptance='FORWARD_CONSUMER_GATE_RETAINED',blocks_authorized_mainline=False),
        'AUD_R3C_ADJUSTMENT_COORDINATE_EXACTNESS':dict(scope='Signed zero and Decimal precision; final exact identity is unchanged on all actual source bars',
            evidence=[bind('reports/v4_11_r3/V4_11_R3C_COORDINATE_SOURCE_CHARACTERIZATION_R2.json'),bind('reports/v4_11_r3/R3C_RUNTIME_AUTHORITY_CLOSURE_R3.json')],
            engineering_acceptance='REPAIRED_WITH_COMPLETE_ACTUAL_SOURCE_IDENTITY_EQUIVALENCE',external_acceptance='PENDING_NEXT_INDEPENDENT_AUDIT',blocks_authorized_mainline=False),
        'AUD_R3_GIT_EXACT_BYTE_PORTABILITY':dict(scope='Protection metadata for two pre-existing exact CRLF/LF representations; strict business source admission remains unchanged',
            evidence=[bind('reports/v4_11_r3/SCOPED_METADATA_PORTABILITY_CLOSURE_R4.json')],engineering_acceptance='PINNED_REPRESENTATION_AND_REAL_CONTENT_DRIFT_REJECTION_VERIFIED',
            external_acceptance='PENDING_NEXT_INDEPENDENT_AUDIT',blocks_authorized_mainline=False),
    }
    registry.update(main_heads_changed=False,permissions=PERMISSIONS,next_stage='STOP_WAIT_INDEPENDENT_EXTERNAL_ACCEPTANCE')
    reg=write(REGISTRY,registry)
    contract=dict(contract_id='V4_NEXT_ROUND_EXECUTION_R3_SEVEN_TASK_CLOSURE_V1',status='SEVEN_TASKS_COMPLETED_ENGINEERING_EXTERNAL_PENDING',
        authority=entry['authority'],master=entry['master'],task_contracts=entry['task_bindings'],phase0=entry['phase0'],
        applicable_upgrade_document=bind('docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'),
        applicable_sections=['13A source DAG','34 exact legacy adapter','34A.5 STATE_EVENT_V1','34A.2A frozen predecessor','78 stage gates'],
        precedence='User authorization and R3 master/tasks govern this batch; no future promotion inferred from document text',
        task_statuses=stages,stage_evidence={k:bind(p) for k,p in receipts.items()},independent_audit_registry=reg,
        acceptance_result='ENGINEERING_CANDIDATE_AND_EXPLICIT_SCOPED_ACCEPTANCE_ONLY; tests are supplementary, external R3 acceptance pending',
        real_market_counts=summary['confirmation_counts'],diagnostic_only_scenarios=summary['diagnostic_only_reasons'],
        independent_oracle=bind('reports/v4_11_r3/V4_11_R3_INDEPENDENT_ORACLE.json'),
        clean_checkout_path='reports/v4_11_r3/V4_11_R3_CLEAN_CHECKOUT.json',
        DataHead='KEEP_2026-09-30',StageHead='KEEP_V4_00_TO_V4_10_ACCEPTED',formal_V4_11_head_created=False,
        V4_12_runtime=False,permissions=PERMISSIONS,next_stage='UNIFIED_COMMIT_PUSH_THEN_STOP_WAIT_INDEPENDENT_EXTERNAL_ACCEPTANCE')
    contract['supersedes']=bind(P+'BATCH_SEVEN_TASK_CLOSURE.json')
    write(P+'BATCH_SEVEN_TASK_CLOSURE_R2.json',contract)
    print('SEVEN_TASKS_COMPLETED_ENGINEERING_EXTERNAL_PENDING')

def paths():
    entry=verify_protected();baseline=set(entry['baseline_tracked_paths']);result=[]
    roots=['data/v4/confirmation_candidates_r3','data/v4/scoped_acceptance_r3','docs/evidence/next_round_r3','reports/v4_11_r3a','reports/v4_11_r3b','reports/v4_11_r3','reports/next_round_r3','reports/audits/next_round_r3']
    for folder in roots:
        result.extend(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    # Only the explicitly new R3 implementation/test families and scoped heads.
    result.extend(p.relative_to(ROOT).as_posix() for folder in ('scripts','src/v4','src/workbench_analysis','config','tests','data/v4','docs/audits','reports/audits')
        for p in (ROOT/folder).glob('**/*') if p.is_file() and p.relative_to(ROOT).as_posix() not in baseline
        and '__pycache__' not in p.parts and (
            (folder in ('scripts','src/v4','src/workbench_analysis','config') and 'r3' in p.name.lower()) or p.name.startswith('v4_11_target_fact')
            or any(x in p.parts for x in ('v4_11_r3a','v4_11_r3b','v4_11_r3c','v4_scoped_promotions_r3','v4_parallel_scoped_consolidation_r3'))
            or p.name in ('V4_11_R3A_INDEPENDENT_ORACLE_AND_FP_BOUNDARIES_20261002.md','A02_A05_A04_SCOPED_PROMOTION_CLOSURE_R3_20261002.md','V4_PARALLEL_SCOPED_FORMALIZATION_CONSOLIDATION_R3_20261002.md',
                'V4_05_ACCEPTED_HEAD_AMENDMENT_A02_R1.json','V4_07_ACCEPTED_HEAD_AMENDMENT_A02_R1.json','V4_09_ACCEPTED_HEAD_AMENDMENT_A02_R1.json',
                'V4_08_B2_CURRENT_SNAPSHOT_CAPABILITY_AMENDMENT_R1.json','A04_AMOUNT_A_GO_FORWARD_PRODUCER_ACCEPTED_HEAD_R1.json',
                'V4_SOURCE_AUTHORITY_SCOPED_DISPOSITION_REGISTRY_R5_INACTIVE.json','V4_PARALLEL_SCOPED_ACCEPTANCE_SUMMARY_HEAD_R3.json',
                'V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R13_CONSOLIDATION_R3.json','V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R14_BATCH_R3.json','V4_CROSS_STAGE_OPEN_AUDIT_REMEDIATION_REGISTRY_R15_BATCH_R3_FINAL.json')))
    return sorted(set(result+['.gitattributes'])-{P+'BATCH_ARTIFACT_MANIFEST.json'})

def manifest():
    refs=[bind(p) for p in paths()]
    write(P+'BATCH_ARTIFACT_MANIFEST.json',dict(contract_id='V4_R3_EXACT_ARTIFACT_MANIFEST_V1',artifacts=refs,
        protected_heads_action='KEEP',permissions=PERMISSIONS,external_acceptance=False),immutable=False)
    print(len(refs))

if __name__=='__main__':
    import sys
    manifest() if sys.argv[1:]==['manifest'] else close()
