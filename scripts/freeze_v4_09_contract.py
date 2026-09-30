"""Freeze V4-09 authority, minimal eligibility quality, AST and independent vectors."""
from pathlib import Path
import json
import sys
import hashlib
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_v4_08_r2_membership_evidence import atomic_json, atomic_bytes

MASTER = 'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
TASK = 'docs/evidence/V4_08_ACCEPTED_HEAD_PROMOTION_AND_V4_09_STOCK_PREWATCH_ENTRY_TASK_20260930.md'
def binding(p):
    b = (ROOT/p).read_bytes(); return dict(path=p, sha256=hashlib.sha256(b).hexdigest(), byte_count=len(b))

def main():
    from scripts.promote_v4_08_accepted_head import validate
    if validate()['status'] != 'PASS': raise ValueError('V4_08_PROMOTION_REQUIRED')
    authority = dict(master=binding(MASTER), task=binding(TASK), sections=['22', '23', '24', '78'])
    common = dict(version='1.0.0', status='FROZEN_CANDIDATE', authority=authority)
    quality = dict(common, contract_id='MANDATORY_CORE_QUALITY_V1',
        required_fields=[
            dict(field='base_seed_state', producer='accepted V4-07 BASE_SEED_V1', quality_allowlist=['READY','PARTIAL_UNKNOWN'],
                 value_allowlist=['TRUE','FALSE'], reason='Resolved accepted Seed state carries its existing safety predicates; UNKNOWN state propagates.'),
            dict(field='core_price_damage', producer='accepted V4-05 CORE_FACTOR_V1', quality_allowlist=['OBSERVED'],
                 value_type='boolean', reason='PASS C Core damage observability; value is not a new damage eligibility veto.'),
        ],
        contextual_requirements=['exact accepted identity/universe membership', 'same security and trade_date across Core/factors/Seed',
            'Seed source publication and Core logical digest exact', 'accepted source availability <= knowledge_cutoff',
            'max_source_trade_date <= target trade_date', 'Core and factors T0_CURRENT_COORDINATE'],
        unknown_rule='Any unavailable required value or provenance yields UNKNOWN, including FALSE Seed with UNKNOWN damage.',
        false_quality_rule=None, excluded=['all other Profile fields', 'Supplemental', 'turnover', 'Sector', 'priority axes'],
        price_basis='T0_CURRENT_COORDINATE engineering replay, no historical as-recorded claim',
        priority_quality_independent=True)
    params = dict(common, parameter_set_id='V4_09_STOCK_PREWATCH_PARAMETER_SET_V1',
        parameters=[dict(parameter_id='delta3_medium', value=3, unit='percentage_points', comparison='GTE'),
                    dict(parameter_id='delta3_high', value=10, unit='percentage_points', comparison='GTE')],
        accepted_core_unit_contract=binding('config/v4_03_field_registry_v1.json'))
    ast = dict(common, contract_id='V4_09_MACHINE_AST_V1',
        raw=dict(op='UNKNOWN_DOMINANT_AND', fields=['base_seed_state','mandatory_core_quality_ready']),
        emergence=[dict(result='HIGH', parameter='delta3_high'), dict(result='MEDIUM', parameter='delta3_medium')],
        structure=[dict(result='HIGH', field='compression_state', equals='COMPRESSING_STRONG'),
                   dict(result='MEDIUM', field='compression_state', equals='COMPRESSING'),
                   dict(result='MEDIUM', field='ma_structure_state', equals='BULL_TRANSITION')],
        bucket_rules=[dict(bucket='A', all=[['emergence_axis','EQ','HIGH'],['structure_quality_axis','EQ','HIGH'],['risk_axis','EQ','LOW']]),
                      dict(bucket='B', all=[['emergence_axis','EQ','HIGH'],['structure_quality_axis','GE','MEDIUM'],['risk_axis','LE','MEDIUM']]),
                      dict(bucket='C', all=[['emergence_axis','EQ','MEDIUM'],['structure_quality_axis','EQ','HIGH'],['risk_axis','EQ','LOW']])],
        enum_order=dict(bucket=['A','B','C','D'], emergence_axis=['LOW','MEDIUM','HIGH'], structure_quality_axis=['LOW','MEDIUM','HIGH'], risk_axis=['LOW','MEDIUM','HIGH','EXTREME']),
        unknown_priority='UNKNOWN_BUCKET for unresolved raw or eligible with unresolved axis; FALSE is NOT_ELIGIBLE; never alter raw.',
        fallback_bucket='D')
    fields = ['security_id','trade_date','publication_id','base_seed_state','mandatory_core_quality_ready','raw_qualification',
              'emergence_axis','structure_quality_axis','risk_axis','priority_bucket','matched_predicates','unknown_predicates',
              'waiting_for','quality','input_digest','parameter_set_id','model_contract_id','priority_sort_key']
    registry = dict(common, contract_id='V4_09_FIELD_REGISTRY_V1', fields={f:dict(producer='STOCK_PREWATCH_V1', persistence='v4.stock_prewatch_results') for f in fields},
        input_fields=dict(delta3=dict(producer='V4-05 CORE_FACTOR_V1:rps5_delta3', unit='percentage_points'),
          compression_state=dict(producer='V4-05 COMPRESSION_STATE_V1', quality='known value with null unknown_reason'),
          ma_structure_state=dict(producer='V4-05 MA_STRUCTURE_V1', quality='known value with null unknown_reason'),
          core_extension_risk=dict(producer='V4-05 EXTENSION_RISK_V1', quality='known value with null unknown_reason')))
    contract = dict(common, contract_id='STOCK_PREWATCH_V1', formula='base_seed_state AND mandatory_core_quality_READY',
        raw_logic=ast['raw'], mandatory_quality_contract='MANDATORY_CORE_QUALITY_V1', priority_contract='PRIORITY_V1',
        accepted_sources=['V4-05 Core Profile/factors','V4-07 Base Seed','accepted identity/universe','accepted target publication context'],
        forbidden_inputs=['same-day Sector','Rotation','B2','D2','State Reducer','Confirmation','Anchor','Support','Radar','Focus','UI','future outcome','forward return'],
        context_policy='Accepted V4-08 sequencing only; context never gates Stock raw.', unknown_priority=ast['unknown_priority'],
        production_permission=False, next_stage='Independent external reaudit; no V4-09 Accepted Head')
    vectors=[]
    def add(name, seed, quality, delta, compression, ma, risk, raw, axes, bucket):
        vectors.append(dict(id=name, facts=dict(base_seed_state=seed, mandatory_core_quality_ready=quality, delta3=delta,
            compression_state=compression, ma_structure_state=ma, core_extension_risk=risk),
            expected=dict(raw_qualification=raw, emergence_axis=axes[0], structure_quality_axis=axes[1], risk_axis=axes[2], priority_bucket=bucket)))
    for seed in ['TRUE','FALSE','UNKNOWN']:
        for q in ['TRUE','UNKNOWN']:
            raw='UNKNOWN' if 'UNKNOWN' in [seed,q] else seed
            add('RAW_'+seed+'_'+q,seed,q,10,'COMPRESSING_STRONG','BULL_ALIGNED','LOW',raw,['HIGH','HIGH','LOW'], 'A' if raw=='TRUE' else 'NOT_ELIGIBLE' if raw=='FALSE' else 'UNKNOWN_BUCKET')
    for d,e in [(2.999,'LOW'),(3,'MEDIUM'),(3.001,'MEDIUM'),(9.999,'MEDIUM'),(10,'HIGH'),(10.001,'HIGH'),(None,'UNKNOWN')]:
        for c,m,s in [('COMPRESSING_STRONG','BEAR_ALIGNED','HIGH'),('COMPRESSING','BEAR_ALIGNED','MEDIUM'),('NORMAL','BULL_TRANSITION','MEDIUM'),('NORMAL','BEAR_ALIGNED','LOW')]:
            for risk in ['LOW','MEDIUM','HIGH','EXTREME','UNKNOWN']:
                bucket='UNKNOWN_BUCKET' if 'UNKNOWN' in [e,s,risk] else 'A' if e=='HIGH' and s=='HIGH' and risk=='LOW' else 'B' if e=='HIGH' and s in ['HIGH','MEDIUM'] and risk in ['LOW','MEDIUM'] else 'C' if e=='MEDIUM' and s=='HIGH' and risk=='LOW' else 'D'
                add(f'AXES_{len(vectors)}','TRUE','TRUE',d,c,m,risk,'TRUE',[e,s,risk],bucket)
    for c,m,s in [('UNKNOWN','BULL_TRANSITION','UNKNOWN'),('NORMAL','UNKNOWN','UNKNOWN'),('COMPRESSING_STRONG','UNKNOWN','HIGH'),('COMPRESSING','UNKNOWN','MEDIUM')]:
        add(f'UNKNOWN_{len(vectors)}','TRUE','TRUE',10,c,m,'LOW','TRUE',['HIGH',s,'LOW'],'UNKNOWN_BUCKET' if s=='UNKNOWN' else 'A' if s=='HIGH' else 'B')
    configs = dict(stock_prewatch_contract=contract, mandatory_core_quality_contract=quality, field_registry=registry,
                   parameter_set=params, machine_ast=ast, machine_vectors=dict(common, contract_id='V4_09_MACHINE_VECTORS_V1', vectors=vectors))
    for name, value in configs.items(): atomic_json(ROOT/f'config/v4_09_{name}_v1.json',value)
    atomic_json(ROOT/'reports/v4_09/V4_09_CONTRACT_FREEZE.json',dict(contract_id='V4_09_CONTRACT_FREEZE_V1',
        status='PASS_CONTRACT_FREEZE_CANDIDATE', authority=authority, before_runtime_implementation=True,
        frozen_bindings=[binding(f'config/v4_09_{name}_v1.json') for name in configs], vector_count=len(vectors)))
    atomic_bytes(ROOT/'reports/v4_09/V4_09_STAGE_ENTRY.md',
        ('# V4-09 Stock PREWATCH stage entry\n\nContract: latest REV4 FEP R2 §§22–24,78 and supplied promotion/task card.\n'
         'V4-08 promotion validated PASS. Phase 0 FULL_PASS inherited. Minimal eligibility quality and separate priority uncertainty frozen before runtime.\n'
         'Accepted same-session Core/factors/Seed determine date, publication, identities and board counts. No TDX writes.\n'
         'Acceptance target: ENGINEERING_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT. Next stage: independent external audit.\n').encode())
    atomic_bytes(ROOT/'docs/evidence/V4_08_ACCEPTED_HEAD_PROMOTION_AND_V4_09_ENTRY_20260930.md',
        ('# V4-08 promotion and V4-09 entry\n\nExternal decision: V4_08_EXTERNAL_ACCEPTANCE_PASS_R5_2_ENGINEERING_SCOPE.\n'
         'Promotion validation and receipt: reports/v4_joint/V4_08_ACCEPTED_HEAD_PROMOTION_{VALIDATION,RECEIPT}_R1.json.\n'
         'Global Stage range V4_00_TO_V4_08_ACCEPTED; Data/Dev/PIT bytes preserved. All production/shadow/Focus permissions false.\n'
         'B2 legacy valid-member producer remains NOT_IMPLEMENTED; Amount A and four capability audits stay OPEN.\n'
         'V4-09 entry authorized only for raw Stock PREWATCH and independent priority axes. No final eligibility or UI.\n').encode())
    print(json.dumps(dict(status='PASS_CONTRACT_FREEZE_CANDIDATE', vectors=len(vectors))))

if __name__ == '__main__': main()
