"""Parity gate then immutable target owner publications; no D2 finalization."""
from scripts.next_round_execution_r5 import *
from scripts.build_v4_11_target_facts_r4a import compressed
from src.v4.owner_inputs_r5 import project_owners,target_records,project_seed,packages,CONTRACT,UNAVAILABLE
from src.v4.confirmation import digest
from src.v4.a02_a05_external_acceptance_r1 import read_accepted_rps
from collections import Counter
from copy import deepcopy
import gzip,json

OUT='reports/v4_11_r5a/'
D='data/v4/confirmation_candidates_r5/'

def gz(ref):return json.loads(gzip.decompress(exact(ref).read_bytes()))
def jsonl(ref):return [json.loads(line) for line in gzip.open(exact(ref),'rt',encoding='utf8')]
def scoped(stage):
    pointer=read('data/v4/'+stage+'_ACCEPTED_HEAD_AMENDMENT_A02_R1.json')
    return read(exact(pointer['payload']).relative_to(ROOT).as_posix())

def parity():
    verify_protected();replay=read('reports/audits/next_round_r2/A02_DOWNSTREAM_AMENDMENT_REPLAY_R1.json')
    rec=read(exact(replay['amendments']['V4_05']).relative_to(ROOT).as_posix())
    cores=jsonl(rec['artifact']);factors={r['security_id']:r for r in jsonl(rec['factor_artifact'])}
    s7=scoped('V4_07');s9=scoped('V4_09');seeds={r['security_id']:r for r in jsonl(s7['artifact'])};stocks={r['security_id']:r for r in jsonl(s9['artifact'])}
    sc=deepcopy(replay['new_seed_context']);sc['identity_ids']=sorted(seeds);st=replay['new_stock_context']
    rows=[];diff=[]
    for core in cores:
        sid=core['security_id'];out=project_owners(core,factors[sid],sc,st,ROOT)
        for owner,expected,actual in [('Seed',seeds[sid],out['seed']),('PREWATCH',stocks[sid],out['prewatch'])]:
            for f,v in actual.items():
                if expected.get(f)!=v:diff.append(dict(security_id=sid,owner=owner,field=f,expected=expected.get(f),actual=v))
        rows.append(dict(security_id=sid,trade_date='2026-09-28',**out))
    if not (set(seeds)==set(stocks)==set(factors)=={r['security_id'] for r in cores}):raise ValueError('PARITY_SCOPE_MISMATCH')
    ref=compressed(D+'OWNER_PARITY_2026-09-28_R5.json.gz',rows)
    report=dict(contract_id='V4_11_R5A_EXACT_OWNER_PARITY_V1',status='PASS' if not diff and len(rows)==s7['row_count']==s9['row_count'] else 'FAIL',row_scope=len(rows),business_mismatches=len(diff),quality_mismatches=sum(r['field']=='quality' for r in diff),unknown_reason_mismatches=sum(r['field'] in ('waiting_for','quality_codes') for r in diff),differences=diff,core=rec['artifact'],factors=rec['factor_artifact'],accepted_seed=s7['artifact'],accepted_prewatch=s9['artifact'],scoped_seed=bind('data/v4/V4_07_ACCEPTED_HEAD_AMENDMENT_A02_R1.json'),scoped_prewatch=bind('data/v4/V4_09_ACCEPTED_HEAD_AMENDMENT_A02_R1.json'),replay=ref,adapter=bind('src/v4/owner_inputs_r5.py'),accepted=False,permissions=PERMISSIONS,formal_t_minus_1_known_count=sum(r['seed_facts'][f]['value'] is not None for r in rows for f in ('close_t_minus_1','ma20_t_minus_1')))
    write(OUT+'V4_07_V4_09_EXACT_OWNER_PARITY.json',report)
    if report['status']!='PASS':raise ValueError('R5A_PARITY_GATE_FAIL:'+str(diff[:5]))
    return report

def build_targets():
    entry=verify_protected();gate=read(OUT+'V4_07_V4_09_EXACT_OWNER_PARITY.json')
    if gate['status']!='PASS':raise ValueError('R5A_PARITY_REQUIRED_BEFORE_TARGET_PUBLICATIONS')
    a=read('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json');head=read('data/v4/V4_DATA_ACCEPTED_HEAD.json');chain=read(head['accepted_chain']['path']);cutoff=entry['observed_at_utc']
    contract=write('config/v4_11_r5a_owner_input_contract_v1.json',dict(contract_id=CONTRACT,authority=bind(AUDIT),task=bind(DOCROOT+TASKS[0]),adapter=bind('src/v4/owner_inputs_r5.py'),owners=entry['owner_authority'],parity=bind(OUT+'V4_07_V4_09_EXACT_OWNER_PARITY.json'),r4a_seal=bind('reports/v4_11_r4a/R4A_SEALED_PRODUCER_SET.json'),t_minus_1='UNKNOWN:'+UNAVAILABLE,reconstruction_allowed=False,actual_bar='EXACT_ACCEPTED_DATED_STATUS_TRISTATE',identity='CANONICAL_SECURITY_SYMBOL_BOARD_DATE_CANDIDATE_PUBLICATION_MEMBERSHIP',accepted=False,formal_consumer_enabled=False,permissions=PERMISSIONS))
    publications={};profiles={};sources={};coverage={}
    for day in ('2026-09-29','2026-09-30'):
        node=next(n for n in chain['nodes'] if n['trade_date']==day)
        refs={k:dict(path=node['components'][k]['artifact_path'],sha256=node['components'][k]['artifact_sha256'],bytes=node['components'][k]['artifact_bytes']) for k in ('IDENTITY_UNIVERSE','TRADING_STATUS')}
        identities=read(exact(refs['IDENTITY_UNIVERSE']).relative_to(ROOT).as_posix())['rows'];statuses=read(exact(refs['TRADING_STATUS']).relative_to(ROOT).as_posix())['rows']
        ix={r['security_id']:r for r in identities};sx={r['security_id']:r for r in statuses}
        rps=read_accepted_rps(ROOT,day);deltas={r['security_id']:r['fields']['rps5_delta3'] for r in rps['deltas'][3]}
        calculations=gz(a['calculations'][day]);assert set(ix)=={r['security_id'] for r in calculations}
        identity_material=dict(contract_id='V4_11_R5A_TARGET_IDENTITY_V1',trade_date=day,rows=identities,source=refs['IDENTITY_UNIVERSE'],accepted=False,AS_RECORDED=False,historical_as_recorded_claim=False)
        identity_material['publication_id']='V4_11_R5A_IDENTITY:'+digest(identity_material)
        identity_ref=write(D+'TARGET_IDENTITY_'+day+'_R5.json',identity_material)
        profile_id='V4_11_R5A_CORE_CANDIDATE:'+digest(dict(identity=identity_ref,calculation=a['calculations'][day],contract=contract))
        context=dict(trade_date=day,identity_ids=sorted(ix),expected_board_counts=dict(Counter(r['board_scope'] for r in identities)),profile_row_publication_id=profile_id,knowledge_cutoff=cutoff)
        corefactor=[]
        for calc in calculations:
            sid=calc['security_id'];delta=deltas.get(sid,dict(value=None,quality_state='UNKNOWN',unknown_reason='PRIOR_UNIVERSE_MEMBER_MISSING'))
            c,f=target_records(calc,ix[sid],sx.get(sid,{}),delta,context);corefactor.append(dict(core=c,factor=f))
        context.update(source_publication_id='V4_11_R5A_BASE_SEED:'+digest(corefactor),core_logical_digest=digest([r['core'] for r in corefactor]))
        rows=[]
        for pair in corefactor:
            sid=pair['core']['security_id'];out=project_owners(pair['core'],pair['factor'],context,context,ROOT)
            out['source_output_digest']=digest(out)
            rows.append(dict(security_id=sid,trade_date=day,producer_contract_id=CONTRACT,**out))
        profile_ref=compressed(D+'TARGET_CORE_OWNER_RECORDS_'+day+'_R5.json.gz',dict(contract_id='V4_11_R5A_CORE_RECORDS_V1',rows=corefactor,context=context,accepted=False,AS_RECORDED=False))
        source_refs=[identity_ref,refs['TRADING_STATUS'],a['calculations'][day],a['publications'][day],bind('data/v4/V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1.json'),contract,profile_ref]
        material=dict(contract_id='V4_11_R5A_SEALED_OWNER_PUBLICATION_V1',producer_contract_id=CONTRACT,trade_date=day,rows=rows,identity=identity_ref,profile=profile_ref,source_bindings=source_refs,accepted=False,knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,formal_consumer_enabled=False,permissions=PERMISSIONS)
        material['publication_id']='V4_11_R5A_OWNERS:'+digest(material);publications[day]=compressed(D+'SEALED_OWNER_PUBLICATION_'+day+'_R5.json.gz',material)
        profiles[day]=profile_ref;sources[day]=source_refs
        coverage[day]=dict(rows=len(rows),formal_t_minus_1_known_count=sum(r['seed_facts'][f]['value'] is not None for r in rows for f in ('close_t_minus_1','ma20_t_minus_1')),SEED=dict(Counter(r['seed']['base_seed_state'] for r in rows)),PREWATCH=dict(Counter(r['prewatch']['raw_qualification'] for r in rows)))
    write(OUT+'R5A_TARGET_PUBLICATIONS.json',dict(contract=contract,publications=publications,profiles=profiles,source_bindings=sources,coverage=coverage,parity=bind(OUT+'V4_07_V4_09_EXACT_OWNER_PARITY.json'),sealed=False))
    fields=list(gz(publications['2026-09-30'])['rows'][0]['seed_facts'])
    mappings=dict(research_universe='sealed target identity membership',actual_bar='accepted dated status',price_identity_READY='target identity publication security/symbol/board/date/profile identity',delta3='accepted RPS history rps5_delta3',close_t_minus_1=UNAVAILABLE,ma20_t_minus_1=UNAVAILABLE)
    write(OUT+'OWNER_INPUT_AUTHORITY_MATRIX.json',dict(contract_id='V4_11_R5A_OWNER_INPUT_AUTHORITY_MATRIX_V1',fields=[dict(field=f,accepted_owner='BASE_SEED_V1 projection' if f in mappings else 'accepted Core Profile owner',accepted_source_field_rule=mappings.get(f,'accepted Core projection: '+f),target_date_source_binding=publications,quality_semantics='KNOWN iff exact owner projection accepts source; otherwise UNKNOWN',tri_state_semantics='EXACT_ACCEPTED_KLEENE',time_role='T_MINUS_1_UNAVAILABLE' if f.endswith('minus_1') else 'T',reconstruction_allowed=False if f.endswith('minus_1') else f not in mappings,formal_in_R5=not f.endswith('minus_1'),unknown_reason=UNAVAILABLE if f.endswith('minus_1') else 'EXACT_SOURCE_OWNER_REASON') for f in fields]))
    print(json.dumps(dict(status='R5A_TARGETS_READY_FOR_INDEPENDENT_ORACLE',coverage=coverage)))

if __name__=='__main__':
    packages.cache_clear();parity();build_targets()
