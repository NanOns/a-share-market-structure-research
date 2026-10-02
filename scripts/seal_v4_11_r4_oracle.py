"""Bind unchanged independent arithmetic to reason-only publication corrections."""
from scripts.next_round_execution_r4 import *
from scripts.verify_v4_11_r4_capability_closure import gz
from src.v4.confirmation import digest
from collections import Counter

def main():
    corrections=read('reports/v4_11_r4a/UNKNOWN_REASON_SOURCE_CORRECTION.json');reports=[]
    for day,amendment in corrections['amendments'].items():
        original=gz(amendment['old_publication_archive']);current=gz(amendment['current'])
        if original['source_bindings']!=current['source_bindings']:raise ValueError('SOURCE_CHANGE_NOT_METADATA_ONLY')
        checks=Counter();proof=[]
        for old,new in zip(original['rows'],current['rows']):
            if old['security_id']!=new['security_id']:raise ValueError('ROW_SCOPE_CHANGED')
            for field,fact in new['facts'].items():
                prior=old['facts'][field]
                if {k:v for k,v in fact.items() if k!='reason'}!={k:v for k,v in prior.items() if k!='reason'}:raise ValueError('BUSINESS_CHANGE_NOT_METADATA_ONLY')
                if fact['reason']==prior['reason']:continue
                reason=fact['reason'];checks[reason]+=1
                if reason.startswith('ACCEPTED_RPS_UNAVAILABLE:'):
                    dependency='rps20' if field=='trend_background_v3' else 'rps5_delta3'
                    dep=new['facts'][dependency]
                    if dep['quality']!='UNKNOWN' or dep['reason']!=reason.split(':',1)[1]:raise ValueError('RPS_REASON_NOT_ACCEPTED_SOURCE')
                elif reason=='ZERO_DENOMINATOR':
                    if field!='clv':raise ValueError('UNEXPECTED_DENOMINATOR_FIELD')
                elif reason not in ('CURRENT_BAR_SUSPENDED','ADJUSTMENT_UNKNOWN','UNEXPLAINED_DATA_GAP','CONFIRMED_SUSPENSION_IN_LEGACY_MASTER_WINDOW','MIXED_ADJUSTMENT_IDENTITY','INSUFFICIENT_HISTORY'):raise ValueError('UNKNOWN_REASON_UNCLASSIFIED')
                proof.append(dict(security_id=new['security_id'],field=field,source_reason=reason))
        path='reports/v4_11_r4a/INDEPENDENT_ORACLE_'+day+'.json';oldreport=read(path)
        archive='reports/v4_11_r4/superseded/INITIAL_'+day+'_INDEPENDENT_ORACLE.json';atomic_bytes(archive,(ROOT/path).read_bytes())
        oldreport.update(publication=amendment['current'],publication_digest=current['logical_digest'],reason_only_correction=dict(original_oracle=bind(archive),original_publication=amendment['old_publication_archive'],new_publication=amendment['current'],all_non_reason_fact_keys_exact=True,source_digest_exact=True,independent_source_dependency_checks=proof,reason_counts=dict(checks)),binding_verifier_source=bind('scripts/seal_v4_11_r4_oracle.py'))
        write(path,oldreport,immutable=False);reports.append(bind(path))
    from scripts.verify_v4_11_scenario_oracle_r3 import verify
    scenario=verify()
    write('reports/v4_11_r4/V4_11_R4_INDEPENDENT_ORACLE.json',dict(status='PASS',target_source_oracles=reports,accepted_core_parity=bind('reports/v4_11_r4a/V4_03_EXACT_PARITY_R1.json'),scenario_literal_oracle=scenario,scope='INDEPENDENT_ACCEPTED_SOURCE_ARITHMETIC_PLUS_ACCEPTED_ARTIFACT_PARITY',accepted=False,permissions=PERMISSIONS))
    print('R4_INDEPENDENT_ORACLE_SEALED')

if __name__=='__main__':main()
