"""Produce mechanism policy and real matched matrix without fitting tolerance."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
from collections import Counter
import hashlib,json,requests
from datetime import datetime,timezone
from scripts.next_round_bundle_r1 import ROOT,write,bind,read,atomic_bytes
from workbench_analysis.baostock_tolerance_candidate_r2 import decompose,validate_policy


def build():
    prefix='data/v4/source_evidence/a06_r2/'
    capture='reports/audits/A06_R2_DOCUMENT_FREEZE_R1.json'
    if not (ROOT/capture).exists():
        old=read('data/v4/source_evidence/a12_r2/PROVIDER_DOCUMENTATION_CAPTURE_R1.json')
        records=[]
        for item in old['records']:
            data=(ROOT/item['path']).read_bytes()
            if hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('PRIOR_OFFICIAL_DOC_HASH_INVALID')
            output=prefix+Path(item['path']).name
            atomic_bytes(output,data)
            records.append(dict(frozen=bind(output),original_capture=item,original_capture_receipt=bind('data/v4/source_evidence/a12_r2/PROVIDER_DOCUMENTATION_CAPTURE_R1.json')))
        url='https://www.baostock.com/helpdocs/api/markdown/stockKData.md'
        observed=datetime.now(timezone.utc).isoformat()
        with requests.get(url,timeout=20,headers={'User-Agent':'Mozilla/5.0'},stream=True,allow_redirects=False) as response:
            body=next(response.iter_content(1048577),b'')
            if len(body)>1048576:raise ValueError('OFFICIAL_DOCUMENT_TOO_LARGE')
            attempt_path=prefix+'CURRENT_OFFICIAL_DOCUMENT_REQUEST_BODY_R1.bin'
            atomic_bytes(attempt_path,body)
            attempt=dict(url=url,observed_at=observed,status=response.status_code,body=bind(attempt_path),max_requests=1,max_bytes=1048576,timeout_seconds=20,redirects_allowed=False)
        write(capture,dict(status='PASS_PRIOR_EXACT_OFFICIAL_DOC_FROZEN',records=records,current_request=attempt,
            current_request_is_new_semantic_authority=False,documentation_generation_rounding='NOT_DOCUMENTED',lineage='OBSERVED_NOW_REFERENCE_ONLY'))
    docs=read(capture)
    policy=dict(contract_id='BAOSTOCK_BINDING_TOLERANCE_POLICY_R2_CANDIDATE',version='2.0.0',acceptance='PENDING_INDEPENDENT_EXTERNAL_REAUDIT',
        strict_binding_allowed=False,may_block_tdx_core=False,canonical_authority=dict(OHLC=False,QFQ=False),
        documentation=bind(capture),source_contract=bind('config/baostock_supplemental_contract_v1.json'),
        prior_unaccepted_tolerance=bind('config/baostock_turnover_binding_tolerance_v1.json'),
        fields={k:dict(unit=unit,documented_precision=precision,generation_rounding_proven=False,tolerance=None,
            derivation='Precision is not a bound without generation/rounding semantics; IEEE754 storage bound is conditional and diagnostic only') for k,unit,precision in [
                ('close','CNY/share',4),('volume','shares',None),('amount','CNY',4),('turn','PERCENT_POINTS',6)]},
        difference_categories=['ROUNDING','UNIT_CONVERSION','ADJUSTMENT_BASIS','PROVIDER_REVISION','CALENDAR_IDENTITY_MISMATCH','TRUE_DATA_CONFLICT'],
        turn_normalization='exact decimal percent points / 100; denominator remains provider-defined circulating shares, not free float',
        forbidden_empirical_percentage_tolerance=True)
    validate_policy(policy)
    write('config/baostock_binding_tolerance_policy_r2_candidate.json',policy)
    head=read('data/v4/V4_DATA_ACCEPTED_HEAD.json');chain=read(head['accepted_chain']['path']);context=read(chain['source_context']['path'])
    rows=[];inputs=[];coverage={};prior_suspended=set();resumptions=[];corporate=[];suspension_observations=[]
    for node in chain['nodes']:
        date=node['trade_date'];raw_ref=node['components']['RAW_DAILY'];raw=read(raw_ref['artifact_path'])['rows']
        source_ref=context['inputs'][date]['inputs']['BAOSTOCK_DAILY_UPDATE'];source=read(source_ref['path'])['daily_rows']
        inputs.extend([dict(path=raw_ref['artifact_path'],sha256=raw_ref['artifact_sha256'],bytes=raw_ref['artifact_bytes']),source_ref])
        local={x['source_security_key'].lower():x for x in raw};suspended={x['code'] for x in source if x['tradestatus']=='0'}
        suspension_observations.extend(dict(date=date,key=x['code'],provider=x,tdx_daily_bar_present=x['code'] in local,
            comparison='NONCOMPARABLE_IF_NATIVE_BAR_ABSENT; NEVER_ZERO_FILL_OR_SYNTHETIC_TDX') for x in source if x['tradestatus']=='0')
        for item in source:
            current=local.get(item['code'])
            if current is None:continue
            diagnosis=decompose(current,item)
            independent={k:str(Fraction(Decimal(str(current[k])))-Fraction(Decimal(item[k]))) for k in ['close','volume','amount']} if item['tradestatus']=='1' else None
            if independent is not None:
                for k,value in diagnosis['differences'].items():
                    if Fraction(Decimal(value))!=Fraction(independent[k]):raise ValueError('INDEPENDENT_ARITHMETIC_DISAGREEMENT')
            rows.append(dict(trade_date=date,security_key=item['code'],board=current['board_scope'],local={k:current[k] for k in ('close','volume','amount')},
                provider={k:item[k] for k in ('close','volume','amount','turn','tradestatus','adjustflag')},diagnosis=diagnosis,independent_fraction_differences=independent))
            if item['code'] in prior_suspended and item['tradestatus']=='1':resumptions.append(dict(date=date,key=item['code']))
        prior_suspended=suspended
        from tdx.gbbq_reader import read_gbbq
        from dataclasses import asdict
        gbbq_ref=context['inputs'][date]['inputs']['GBBQ']
        actions=[e for e in read_gbbq(ROOT/gbbq_ref['path']) if e.category==1 and e.event_date<=int(date.replace('-',''))]
        near=sorted(actions,key=lambda e:e.event_date,reverse=True)[:4]
        corporate.append(dict(date=date,source=gbbq_ref,exact_native_action_examples=[asdict(e) for e in near],
            corporate_action_today=[asdict(e) for e in actions if e.event_date==int(date.replace('-',''))],
            comparison_scope='RAW adjustflag=3 only; provider adjusted-basis comparisons prohibited'))
    def examples(test):return [dict(date=x['trade_date'],key=x['security_key']) for x in rows if test(x)][:4]
    identity={}
    for node in chain['nodes']:
        identity[node['trade_date']]=read(node['components']['IDENTITY_UNIVERSE']['artifact_path'])
    new_events=[dict(date=d,event=e) for d,a in identity.items() for e in a['boundary_events'] if e['event_type']=='LISTING_START']
    coverage={**{board:examples(lambda x,b=board:x['board']==b) for board in ['SH_MAIN','SZ_MAIN','STAR','CHINEXT']},
        'HIGH_PRICE':examples(lambda x:Decimal(x['provider']['close'])>=200),
        'LOW_PRICE':examples(lambda x:Decimal(x['provider']['close'])<=2),
        'SUSPENSION':suspension_observations, 'RESUMPTION':resumptions,
        'NEW_LISTING':new_events,'NORMAL_DATE':['2026-09-28','2026-09-29'],'BOUNDARY_DATE':['2026-09-30'],
        'CORPORATE_ACTION':corporate}
    matrix='reports/audits/A06_R2_REAL_REPRESENTATIVE_MATRIX_R2.json'
    write(matrix,dict(status='PARTIAL_REAL_MATRIX_GENERATION_ROUNDING_NOT_DOCUMENTED',rows=rows,matched_rows=len(rows),
        inputs=inputs,coverage=coverage,classification_counts=dict(Counter(x['diagnosis']['classification'] for x in rows)),
        independent_arithmetic='Decimal differences independently cross-checked against exact Fraction differences on every active matched row',
        future_data_used=False,source_window=['2026-09-28','2026-09-29','2026-09-30'],
        supersedes_draft_matrix=bind('reports/audits/A06_R2_REAL_REPRESENTATIVE_MATRIX_R1.json')))
    write('reports/audits/A06_R2_TOLERANCE_CANDIDATE_HANDOFF_R2.json',dict(
        status='A06_BAOSTOCK_TOLERANCE_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',execution_result='PARTIAL',
        policy=bind('config/baostock_binding_tolerance_policy_r2_candidate.json'),matrix=bind(matrix),documentation=bind(capture),
        blockers=['Provider generation/rounding algorithm is undocumented: no numeric tolerance authorized','Provider-defined turnover denominator still lacks scoped independent acceptance'],
        strict_binding_allowed=False,tdx_core_blocked=False,authority_upgraded=False,stage_head_action='KEEP',data_head_action='KEEP',
        production=False,shadow=False,focus_cutover=False,next_stage='INDEPENDENT_EXTERNAL_REAUDIT'))
    return dict(status='CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',execution_result='PARTIAL',matched_rows=len(rows))


if __name__=='__main__':print(json.dumps(build()))
