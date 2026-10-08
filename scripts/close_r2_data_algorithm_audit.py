"""Independent numeric checks and truthful field-local successor disposition."""
import collections
import copy
import gzip
import json
import math
import os
import sqlite3
import statistics
import subprocess
import sys
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from scripts.audit_r2_data_algorithm import OUT
from workbench_service.joint_release import AUTHORITY,checked_path,validate,activate
from workbench_service.current_v4_context import digest,SourceInvalid
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.domain_views import objects
from workbench_service.forward_daily import verify_due_settlement


def records(binding):
    with gzip.open(checked_path(ROOT,binding),'rt',encoding='utf8') as stream:
        return [json.loads(line) for line in stream]


def main():
    if (OUT/'R2_DATA_ALGORITHM_CLOSURE_FINAL.md').exists():
        raise RuntimeError('CLOSURE_ALREADY_SEALED_USE_NEW_EVIDENCE_NAMESPACE')
    before=(ROOT/AUTHORITY).read_bytes();joint=json.loads(before)
    manifest=validate(ROOT,joint);r=ProductionV4ResearchReader(ROOT);day=r.context['trade_date']
    stocks=objects(r,'stocks');sectors=objects(r,'sectors');owner=manifest['domain_features']['stocks']
    factor={x['security_id']:x for x in records(owner['factors'])}
    profile={x['security_id']:x for x in records(owner['profiles'])}
    lineage=[]
    for key in sorted({k for x in stocks for k in x['fields']}):
        cells=[(x['entity_id'],x['fields'][key]) for x in stocks if key in x['fields']]
        example=cells[0][1];f=[factor[s]['fields'][key] for s,c in cells if s in factor and key in factor[s]['fields']]
        p=[profile[s]['states'][key] for s,c in cells if s in profile and key in profile[s]['states']]
        src=f or p
        lineage.append(dict(field=key,owner_contract=example.get('source_contract_id'),
            owner_source_digest=example.get('source_digest'),business_date=day,
            source_as_of=example.get('source_as_of'),publication_at=manifest['metadata']['published_at'],
            first_available_at_target_proven=False,first_available_at=None,
            parameter_set=example.get('parameter_set_id'),price_basis=owner['price_basis'],unit=example.get('unit'),
            formula_contract=src[0].get('contract_id') if src else example.get('source_contract_id'),
            formula_evidence=src[0] if src else dict(status='NO_NUMERICAL_OWNER_CONTRACT_IN_CORE_FACTORS_OR_PROFILES',cell=example),
            known_rows=sum(c.get('value') not in (None,'UNKNOWN') and c.get('quality')!='UNKNOWN' for s,c in cells),
            unknown_reasons=dict(collections.Counter(str(c.get('reason') or 'OWNER_UNKNOWN') for s,c in cells
                if c.get('value') in (None,'UNKNOWN') or c.get('quality')=='UNKNOWN'))))
    write(OUT/'R2_OWNER_FIELD_DATA_LINEAGE.json',dict(contract_id='R2_OWNER_FIELD_DATA_LINEAGE_V1',
        business_date=day,fields=lineage,sources=manifest['sources'],owners=joint['daily_owner_authorities'],
        identity_pool=manifest['counts'],volume_unit=owner['volume_unit'],amount_unit=owner['amount_unit'],
        strict_pit=False,formula_limit='OWNER_CONTRACT_AND_EVIDENCE_NOT_FULL_INDEPENDENT_REIMPLEMENTATION'))
    groups=collections.defaultdict(set)
    for x in records(manifest['sources']['membership']):
        assert x['target_trade_date']==x['membership_asof_date']==day
        groups[x['sector_id']].add(x['security_id'])
    native={x['sector_id']:x for x in records(manifest['domain_features']['sector']['native'])}
    sector_comparisons=[]
    for item in sectors:
        sid=item['entity_id'];ids=groups[sid];values={}
        for key,input_key in [('sector_rs5','ret5'),('sector_rs20','ret20'),('participation_proxy','amount_ratio20')]:
            nums=[factor[s]['fields'][input_key]['value'] for s in ids if s in factor and factor[s]['fields'][input_key]['value'] is not None]
            expected=statistics.median(nums) if nums else None;actual=item['fields'][key]['value']
            assert expected is None and actual is None or math.isclose(expected,actual,rel_tol=1e-12,abs_tol=1e-12)
            values[key]=dict(expected=expected,actual=actual,known_member_count=len(nums),member_count=len(ids))
        sector_comparisons.append(dict(sector_id=sid,name=item['display_name'],sector_type=item['fields']['sector_type']['value'],
            current=values,prior=None,prior_reason='NO_ACCEPTED_DATE_OWNED_20260929_MEMBERSHIP',
            membership_entered=None,membership_exited=None,state=item['fields']['output_state'],
            seed=native[sid]['fields']['seed_width'],breadth_delta3=native[sid]['fields']['breadth_delta3']))
    center=manifest['domain_features']['market_center']
    raw=json.loads(checked_path(ROOT,center['sources']['RAW_DAILY']).read_bytes())['rows']
    prices={x['security_id']:x for x in raw}
    limits=json.loads(checked_path(ROOT,center['sources']['PRICE_LIMIT']).read_bytes())['rows']
    breadth=collections.Counter();limit_counts=collections.Counter();classified=0
    for x in limits:
        limit_counts[x['limit_status']]+=1;p=prices.get(x['security_id'])
        if p and x['trading_status']=='ACTUAL_TRADED' and x['reference_price'] is not None:
            delta=Decimal(str(p['close']))-Decimal(x['reference_price'])
            breadth['up' if delta>0 else 'down' if delta<0 else 'flat']+=1
        else:breadth['unknown']+=1
        if p and x['limit_up_price'] and x['limit_down_price'] and x['trading_status']=='ACTUAL_TRADED':
            close=Decimal(str(p['close']))
            expected='LIMIT_UP' if close==Decimal(x['limit_up_price']) else 'LIMIT_DOWN' if close==Decimal(x['limit_down_price']) else 'NOT_LIMIT'
            assert expected==x['limit_status'];classified+=1
    assert dict(limit_counts)==center['limits']['counts']
    for k,v in breadth.items():assert center['breadth'][k]==v
    assert sum(breadth.values())==center['breadth']['denominator']==len(limits)
    raw_amount=float(sum(Decimal(str(x['amount'])) for x in raw))
    assert raw_amount==center['breadth']['amount_cny']
    market_oracle=dict(business_date=day,breadth=dict(breadth),denominator=len(limits),
        limit_counts=dict(limit_counts),close_limit_comparisons=classified,amount_cny=raw_amount,
        amount_rows=len(raw),sources=center['sources'],
        scope='RAW_CLOSE_VS_ACCEPTED_REFERENCE_AND_LIMIT_BOUNDS_NOT_INDEPENDENT_EXCHANGE_RULE_REAUDIT',
        four_axis_algorithm_acceptance='NOT_REIMPLEMENTED_THIS_ROUND')
    numeric=[];missing=collections.Counter()
    with sqlite3.connect(checked_path(ROOT,owner['series']).as_uri()+'?mode=ro',uri=True) as db:
        for item in stocks:
            sid=item['entity_id'];cells=factor[sid]['fields']
            for key in ('ma20','ret5'):
                c=cells[key]
                if c.get('value') is None or c.get('unknown_reason'):
                    missing[key]+=1;continue
                if key=='ma20':
                    bars=[json.loads(x[0]) for x in db.execute('SELECT payload FROM bars WHERE security=? AND day<=? ORDER BY day DESC LIMIT 20',(sid,day))]
                    assert len(bars)==20 and all(b['qfq_ohlc'] for b in bars)
                    expected=sum(float(b['qfq_ohlc'][3]) for b in bars)/20
                else:
                    bars={d:json.loads(p) for d,p in db.execute('SELECT day,payload FROM bars WHERE security=? AND day IN (?,?)',(sid,c['window_start_trade_date'],day))}
                    expected=float(bars[day]['qfq_ohlc'][3])/float(bars[c['window_start_trade_date']]['qfq_ohlc'][3])-1
                assert math.isclose(expected,c['value'],rel_tol=1e-11,abs_tol=1e-10),(sid,key)
                numeric.append(dict(entity_id=sid,field=key,expected=expected,actual=c['value']))
        # Independently inspect all prior-day Focus observations against actual
        # dated bars; compare only when both RAW and QFQ coordinates coincide.
        paths=[];unverified=[];adjusted_checks=[]
        focus=manifest['domain_features']['focus']
        for ep in focus['episodes']:
            if ep['T0']!='2026-09-29':continue
            obs=next((o for o in ep['observations'] if o['trade_date']==day),None)
            if not obs:continue
            bars={d:json.loads(p) for d,p in db.execute('SELECT day,payload FROM bars WHERE security=? AND day IN (?,?)',(ep['entity_id'],ep['T0'],day))}
            ready=len(bars)==2 and all(b.get('qfq_ohlc') and b.get('raw_ohlc') and math.isclose(float(b['qfq_ohlc'][3]),float(b['raw_ohlc'][3]),abs_tol=1e-9) for b in bars.values())
            if not ready:
                if len(bars)==2 and all(b.get('qfq_ohlc') for b in bars.values()):
                    operands={d:[Decimal(str(v)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP) for v in b['qfq_ohlc']] for d,b in bars.items()}
                    anchor=operands[ep['T0']][3];end=operands[day][3];expected=end/anchor-1
                    assert math.isclose(float(expected),float(obs['price_path']['metrics']['return_close']),abs_tol=1e-12)
                    outcome=next(o for o in ep['outcomes'] if o['horizon']==1)
                    assert outcome['target_trade_date']==day and outcome['outcome_status']=='OBSERVED'
                    assert math.isclose(float(expected),float(outcome['metrics']['return_close']),abs_tol=1e-12)
                    adjusted_checks.append(dict(entity_id=ep['entity_id'],episode_id=ep['episode_id'],T0=ep['T0'],target=day,
                        qfq_rounded_operands={d:list(map(str,v)) for d,v in operands.items()},expected_return=str(expected),
                        comparison='ACCEPTED_QFQ_SERIES_VS_INDEPENDENT_FOCUS_REANCHOR_OUTPUT',
                        independent_raw_affine_coefficients_proven=False))
                unverified.append(dict(episode_id=ep['episode_id'],entity_id=ep['entity_id'],
                    actual_dates=sorted(bars),adjustment_reasons={d:b.get('adjustment_reason') for d,b in bars.items()},
                    qfq_known={d:bool(b.get('qfq_ohlc')) for d,b in bars.items()},
                    price_path=obs['price_path'],reason='REQUIRES_INDEPENDENT_AFFINE_REANCHOR_OR_MISSING_BAR'));continue
            start=float(bars[ep['T0']]['raw_ohlc'][3]);end=float(bars[day]['raw_ohlc'][3])
            expected_return=end/start-1
            assert obs['price_path']['quality']=='READY'
            assert math.isclose(expected_return,float(obs['price_path']['metrics']['return_close']),abs_tol=1e-12)
            outcome=next(o for o in ep['outcomes'] if o['horizon']==1)
            assert outcome['target_trade_date']==day and outcome['outcome_status']=='OBSERVED'
            assert math.isclose(expected_return,float(outcome['metrics']['return_close']),abs_tol=1e-12)
            paths.append(dict(episode_id=ep['episode_id'],entity_id=ep['entity_id'],T0=ep['T0'],
                target_trade_date=day,raw_return=expected_return,comparison='INDEPENDENT_RAW_RETURN_EQUALS_PATH_AND_H1_OUTCOME',price_path=obs['price_path'],outcomes=ep['outcomes']))
    forward=manifest['domain_features']['forward'];due=verify_due_settlement(forward,day)
    assert due==0 and len(forward['enrollments'])==117 and len(forward['plans'])==585
    write(OUT/'R2_NUMERICAL_ORACLE_V2.json',dict(contract_id='R2_NUMERICAL_ORACLE_V2',strict_pit=False,
        market=market_oracle,
        stocks=dict(comparisons=len(numeric),unknown_preserved=dict(missing),samples=numeric),
        sectors=dict(comparisons=len(sector_comparisons)*3,rows=sector_comparisons,
            full_two_date_rotation_acceptance='NOT_VERIFIABLE',verified_output_states=sum(x['state']['value']!='UNKNOWN' for x in sector_comparisons)),
        focus=dict(raw_coordinate_samples=paths,adjusted_coordinate_checks=adjusted_checks,unverified=unverified,
            scope='INDEPENDENT_RAW_RETURN_PATH_AND_H1_OUTCOME_NOT_YET_FULL_AFFINE_PATH_ACCEPTANCE',forward_settlement=False),
        forward=dict(enrollments=117,plans=585,frozen_t0=len(forward['t0_freezes']),due=due,
            real_due_acceptance='NOT_VERIFIABLE_NO_REAL_DUE_SESSION')))
    inventory=json.loads((ROOT/'docs/evidence/r2_read_domains_continuation_20261008/R2_PRODUCT_FIELD_COVERAGE.json').read_bytes())
    debts=[]
    for row in inventory['rows']:
        if row['product_pass']:continue
        feature=row['feature'];section=row['section']
        if feature in ('strict_pit','frozen_sector'):
            category='HISTORICAL_PROOF_TO_ACCUMULATE';acceptance='HISTORICAL_PIT_UNPROVEN'
        elif feature in ('broken_limit','facts_events','hypothesis','supporting_evidence','counterevidence','next_discriminator'):
            category='OPTIONAL_EXTERNAL_OR_HYPOTHESIS_SOURCE';acceptance='OPTIONAL_SOURCE_DEBT'
        elif feature=='parent_episode_id':
            category='REAL_INPUT_SEMANTICS_REVIEW';acceptance='ONGOING_VALIDATION_DEBT'
        else:
            category='CURRENT_ALGORITHM_MEANING';acceptance='CURRENT_PRODUCTION_BLOCKED'
        debts.append(dict(id='AUD-R2-DATA-'+str(len(debts)+1).zfill(3),section=section,field=feature,
            category=category,capability_acceptance=acceptance,owner=row.get('owner'),
            evidence_reason=row.get('debt_reason'),reason_counts=row.get('reason_counts'),
            global_production_block=False,acceptance='OPEN_FIELD_LOCAL',adapter_omission_proven=False))
    assert len(debts)==50
    write(OUT/'R2_VERSIONED_FIELD_DEBT_LEDGER.json',dict(contract_id='R2_FIELD_DEBT_LEDGER_V1',baseline_inventory=ref('docs/evidence/r2_read_domains_continuation_20261008/R2_PRODUCT_FIELD_COVERAGE.json'),rows=debts,
        counts=dict(collections.Counter(x['category'] for x in debts)),old_product_pass_unchanged=True))
    # Actual current release becomes the rollback predecessor in this isolated
    # successor. Hardlinks are read-only inputs here; no linked file is mutated.
    sandbox=Path('E:/codex_tmp/r2_algorithm_rollback')
    sandbox.mkdir(parents=True,exist_ok=True)
    refs=[joint['snapshot']['manifest'],manifest['database'],*manifest['sources'].values(),*joint['ui_assets'].values()]
    for o in joint['daily_owner_authorities'].values():
        for v in o.values():
            if isinstance(v,dict) and {'path','sha256'}<=v.keys():refs.append(v)
    for b in refs:
        source=checked_path(ROOT,b);target=sandbox/b['path'];target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            try:os.link(source,target)
            except OSError:write(target,source.read_bytes())
        assert digest(target.read_bytes())==b['sha256']
    write(sandbox/AUTHORITY,before);validate(sandbox,joint)
    successor=copy.deepcopy(joint);successor['audit_rehearsal_only']='R2_DATA_ALGORITHM_REPAIR_V1'
    def health(candidate):
        actual=ProductionV4ResearchReader(sandbox)
        assert actual.query('stocks',{'limit':'1'})['total']==5213
        return {'pass':True,'context_token':actual.token}
    receipt=activate(sandbox,successor,digest(before),health)
    active=(sandbox/AUTHORITY).read_bytes()
    restored=activate(sandbox,joint,digest(active),health)
    assert (sandbox/AUTHORITY).read_bytes()==before
    try:activate(sandbox,successor,digest(before),lambda c:{'pass':False})
    except SourceInvalid as e:assert str(e)=='JOINT_HEALTH_FAILED'
    else:raise AssertionError('HEALTH_FAILURE_NOT_REJECTED')
    assert (sandbox/AUTHORITY).read_bytes()==before
    write(OUT/'R2_DAILY_RELEASE_ROLLBACK.json',dict(contract_id='R2_DAILY_RELEASE_ROLLBACK_V1',
        real_current_authority=ref(AUTHORITY),actual_predecessor_readable=True,isolated_successor=receipt,
        isolated_restore=restored,health_failure_exact_restore=True,live_authority_unchanged=True,
        historical_adjacent_predecessor='STILL_OPEN_AUD-R2-SNAPSHOT-PREDECESSOR-MUTABLE-REF',
        no_new_session='SEE_SEPARATE_CLI_NOOP_RECEIPT',full_product_release=False))
    assert (ROOT/AUTHORITY).read_bytes()==before
    print(json.dumps(dict(result='SCOPED_ORACLES_AND_ROLLBACK_PASS',stock_comparisons=len(numeric),sector_comparisons=len(sector_comparisons)*3,field_debts=len(debts),focus_raw_windows=len(paths),forward_due=due)))


if __name__=='__main__':main()
