"""Independent R5A oracle: no R5 adapter helper generates expectations."""
from scripts.next_round_execution_r5 import *
from scripts.build_v4_11_target_facts_r4a import compressed
from src.v4 import base_seed,stock_prewatch
from src.v4.a02_a05_external_acceptance_r1 import read_accepted_rps
from src.v4.adjustment_basis_r4 import observations
from src.v4.factors.core import compute_core
from src.v4.confirmation import digest
from dataclasses import asdict
from collections import Counter
import gzip,json,re

OUT='reports/v4_11_r5a/'
def gz(ref):return json.loads(gzip.decompress(exact(ref).read_bytes()))

def verify():
    verify_protected();set_=read(OUT+'R5A_TARGET_PUBLICATIONS.json');parity=read(exact(set_['parity']).relative_to(ROOT).as_posix())
    if parity['status']!='PASS' or parity['formal_t_minus_1_known_count'] or parity['business_mismatches']:raise ValueError('R5A_PARITY_NOT_PASS')
    params=base_seed._parameter_values(read('config/v4_07_parameter_set_v1.json'));package=stock_prewatch.load_package(ROOT);reports=[]
    a=read('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json')
    for day,ref in set_['publications'].items():
        pub=gz(ref);material=dict(pub);pid=material.pop('publication_id');assert pid=='V4_11_R5A_OWNERS:'+digest(material)
        source=gz(pub['profile']);context=source['context'];pairs={r['core']['security_id']:r for r in source['rows']}
        identities=read(exact(pub['identity']).relative_to(ROOT).as_posix());ix={r['security_id']:r for r in identities['rows']}
        status_ref=next(r for r in pub['source_bindings'] if r['path'].endswith('.json') and 'TRADING_STATUS' in r['path'].upper());sx={r['security_id']:r for r in read(exact(status_ref).relative_to(ROOT).as_posix())['rows']}
        rps=read_accepted_rps(ROOT,day);delta={r['security_id']:r['fields']['rps5_delta3'] for r in rps['deltas'][3]}
        calculations={r['security_id']:r for r in gz(a['calculations'][day])}
        assert set(pairs)==set(ix)=={r['security_id'] for r in pub['rows']}
        checked=Counter();rows=[]
        for row in pub['rows']:
            sid=row['security_id'];c=pairs[sid]['core'];f=pairs[sid]['factor'];calc=calculations[sid]
            # Independently reexecute accepted Core arithmetic from frozen R4 sources.
            slots=[dict(r,accepted_source_digest=digest(r)) for r in calc['window']]
            statuses={(sid,r['date']):r['accepted_trading_status'] for r in slots if r.get('accepted_trading_status')}
            expected_core={k:asdict(v) for k,v in compute_core(observations(slots,sid,statuses),sid,asof=day).items()}
            for field,expected in expected_core.items():
                for key,value in expected.items():assert f['fields'][field][key]==value,(sid,field,key)
            expected=base_seed._normalize_facts(c,f,context)
            sr=sx.get(sid,{});status=sr.get('status',sr.get('trading_status'))
            if sr.get('status_conflict') or sr.get('provider_conflicts'):status='UNKNOWN'
            assert expected['actual_bar']['value']==(True if status=='ACTUAL_TRADED' else False if status=='SUSPENDED' else None)
            source_valid=(ix[sid].get('identity_status')=='IDENTITY_BOUND' and ix[sid].get('security_id')==sid and ix[sid].get('trade_date')==day and ix[sid].get('security_type')=='A_STOCK' and ix[sid].get('source_security_key')==calc['window'][-1].get('source_security_key'))
            assert c['symbol']==(ix[sid]['source_security_key'] if source_valid else None)
            assert c['board']==ix[sid]['board_scope'] and c['trade_date']==day and c['publication_id']==context['profile_row_publication_id'] and c['historical_as_recorded_claim'] is False
            identity_valid=bool(source_valid and re.fullmatch(r'SEC-[0-9A-F]{32}',sid) and isinstance(c['symbol'],str) and re.fullmatch(r'(?:SH|SZ)\.[0-9]{6}',c['symbol']) and c['board'] in context['expected_board_counts'])
            assert expected['research_universe']['value'] is True and expected['price_identity_READY']['value']==(True if identity_valid else None)
            for field in ('close_t_minus_1','ma20_t_minus_1'):
                assert row['seed_facts'][field]==dict(value=None,reason='ACCEPTED_T_MINUS_1_CORE_FIELD_UNAVAILABLE');checked['formal_t_minus_1_unknown']+=1
            assert row['seed_facts']==expected
            d=delta.get(sid,dict(value=None,quality_state='UNKNOWN',unknown_reason='PRIOR_UNIVERSE_MEMBER_MISSING'))
            for key in ('value','quality_state','unknown_reason'):assert f['fields']['rps5_delta3'][key]==d[key]
            seed=base_seed._eval(expected,params);assert seed==row['seed']
            seed_record=dict(security_id=sid,trade_date=day,publication_id=context['source_publication_id'],source_publication_id=c['publication_id'],source_core_logical_digest=context['core_logical_digest'],model_contract_id='BASE_SEED_V1',**seed)
            facts,reasons,provenance=stock_prewatch.project(c,f,seed_record,context,package)
            evaluated=stock_prewatch.evaluate(facts,package)
            assert facts==row['prewatch_facts'] and reasons==row['prewatch_required_reasons']
            for key,value in evaluated.items():assert row['prewatch'][key]==value
            out={k:v for k,v in row.items() if k not in ('security_id','trade_date','producer_contract_id','source_output_digest')}
            assert row['source_output_digest']==digest(out)
            checked['owner_rows']+=1;rows.append(dict(security_id=sid,seed_output_digest=digest(seed),prewatch_output_digest=digest(row['prewatch']),actual_status=status))
        proof=compressed('data/v4/confirmation_candidates_r5/INDEPENDENT_OWNER_ORACLE_'+day+'_R5.json.gz',rows)
        reports.append(dict(trade_date=day,status='PASS',counts=dict(checked),publication=ref,source_profile=pub['profile'],independent_proof=proof,adapter_helpers_called_for_expected=False))
    return write(OUT+'INDEPENDENT_OWNER_INPUT_ORACLE.json',dict(contract_id='V4_11_R5A_INDEPENDENT_OWNER_ORACLE_V1',status='PASS',dates=reports,formal_t_minus_1_known_count=0,adapter_helpers_called_for_expected=False,accepted_owner_algorithms=True,parameter_bindings=[bind(p) for p in ('config/v4_07_parameter_set_v1.json','config/v4_09_parameter_set_v1.json')],verifier=bind('scripts/verify_v4_11_owner_inputs_r5a.py'),permissions=PERMISSIONS))

def seal():
    verify_protected();ref=verify();receipt=read(ref['path']);set_=read(OUT+'R5A_TARGET_PUBLICATIONS.json')
    tamper=read(OUT+'OWNER_BOUNDARY_TEST_RECEIPT.json')
    if tamper['status']!='PASS':raise ValueError('R5A_BOUNDARY_TESTS_REQUIRED')
    write(OUT+'R5A_SEALED_OWNER_PRODUCER_SET.json',dict(contract_id='V4_11_R5A_SEALED_OWNER_PRODUCER_SET_V1',status='V4_11_R5A_OWNER_INPUT_AUTHORITY_PARITY_CANDIDATE_READY',sealed=True,accepted=False,AS_RECORDED=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',formal_consumer_enabled=False,contract=set_['contract'],parity=set_['parity'],publications=set_['publications'],profiles=set_['profiles'],coverage=set_['coverage'],independent_oracle=ref,boundary_tests=bind(OUT+'OWNER_BOUNDARY_TEST_RECEIPT.json'),authority_matrix=bind(OUT+'OWNER_INPUT_AUTHORITY_MATRIX.json'),permissions=PERMISSIONS,next_stage='R5B_SEALED_OWNER_INPUTS_ONLY'))
    print('R5A_PASS_SEALED')

if __name__=='__main__':seal()
