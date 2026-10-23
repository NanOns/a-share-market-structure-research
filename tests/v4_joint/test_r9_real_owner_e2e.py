"""显式真实候选输入→独立全量数值对账→开发 PG Owner；不修改 Head。"""
import hashlib
import json
import math
import os
from pathlib import Path
from collections import Counter
import time

import pytest

pytestmark=pytest.mark.skipif(os.environ.get('R9_REAL_OWNER_E2E')!='1',reason='需显式候选输入目录和开发 PG 授权环境')


def _sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def _digest(value):
    from workbench_analysis.operational_successor_v1 import digest
    return digest(value)


def _stock_oracle(rows,day):
    ranked=[]
    for row in rows:
        fields=row['fields'];values={}
        if row.get('trade_date')!=day:continue
        invalid=False
        for key in ('close','prior_low20','rps20','rps20_delta3','ret5','pos60'):
            cell=fields.get(key,{})
            value=cell.get('value')
            if (type(value) not in (int,float) or not math.isfinite(value)
                    or cell.get('quality') not in {'KNOWN','OBSERVED','RECONSTRUCTED','PROXY_RECONSTRUCTED'}
                    or cell.get('as_of',day)!=day):
                invalid=True;break
            values[key]=value
        if invalid:continue
        c,l,r,d,ret,pos=(values[k] for k in ('close','prior_low20','rps20','rps20_delta3','ret5','pos60'))
        if not (c>0 and l>0 and 0<=r<=100 and -100<=d<=100 and ret> -1 and 0<=pos<=1):continue
        damage=fields.get('core_price_damage',{})
        if (damage.get('value') is not False or damage.get('quality') not in {'KNOWN','OBSERVED','RECONSTRUCTED'}
                or damage.get('as_of',day)!=day):continue
        if not fields['close'].get('adjustment_basis') or fields['close']['adjustment_basis']!=fields['prior_low20'].get('adjustment_basis'):continue
        if not (d>0 and ret>0 and pos<.95):continue
        distance=min(1,max(0,(c-l)/l))
        score=round(4+min(4,d*100)+min(2,ret*100)+max(0,2-distance*10),6)
        ranked.append((row['entity_id'],score,d,ret))
    return sorted(ranked,key=lambda row:(-row[1],-row[2],-row[3],row[0]))


def _sector_oracle(rows,day):
    ranked=[]
    active={'ROTATION_IN','ROTATION_ACCEPTED','ROTATION_EXPANDING','ROTATION_REACCELERATING'}
    for row in rows:
        f=row['fields'];m=f.get('maturity',{});h=f.get('health',{});rot=f.get('output_state',{})
        maturity=m.get('value');health=h.get('value');rotation=rot.get('value')
        if maturity not in {'MATURE','DEVELOPING','EARLY','NONE'} or health not in {'NONE','WATCH','WEAKENING','DAMAGED'}:continue
        if any(cell.get('as_of')!=day or cell.get('quality') not in {'KNOWN','OBSERVED','RECONSTRUCTED'}
               or not all(cell.get('source',{}).get(k) for k in ('input_digest','producer_sha256','parameter_sha256','source_bindings')) for cell in (m,h)):continue
        if (rotation not in active|{'ROTATION_PULSE','ROTATION_OUT','ROTATION_FAILED','NONE'}
                or rot.get('quality') not in {'KNOWN','OBSERVED','RECONSTRUCTED','PROXY_RECONSTRUCTED'}
                or rot.get('as_of',day)!=day):continue
        numbers=[]
        for key in ('sector_rs5','sector_rs20'):
            cell=f.get(key,{});value=cell.get('value')
            if (type(value) not in (int,float) or not math.isfinite(value)
                    or cell.get('quality') not in {'KNOWN','OBSERVED','RECONSTRUCTED','PROXY_RECONSTRUCTED'}
                    or cell.get('as_of',day)!=day):break
            numbers.append(value)
        if len(numbers)!=2:continue
        rs5,rs20=numbers
        score=(4 if rotation in active else 2 if rotation=='ROTATION_PULSE' else 0)
        score+={'MATURE':4,'DEVELOPING':3,'EARLY':1,'NONE':0}[maturity]
        score+={'NONE':2,'WATCH':1,'WEAKENING':0,'DAMAGED':-3}[health]+int(rs5>0)+int(rs20>0)
        ranked.append((row['entity_id'],score,rs5,rs20))
    return sorted(ranked,key=lambda row:(-row[1],-row[2],-row[3],row[0]))


def test_real_two_day_priority_lifecycle_pg_and_independent_full_oracle():
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
    from workbench_analysis.r43_owner_replay import checked,ref
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1,_exact_price_coordinate
    from workbench_service.research_priority_r1 import build_priority
    from sector.candidate_lifecycle_v1 import build_candidate_lifecycle
    from workbench_db.forward_r7_store import _configured_forward_dsn
    from workbench_db.v4_operational_risk_pg_r1 import prepare_priority,load_priority
    from workbench_db.v4_sector_lifecycle_pg_r1 import prepare as prepare_lifecycle,load as load_lifecycle
    source=Path(__file__).resolve().parents[2]
    os.environ['V4_NATIVE_PG_DSN']=_configured_forward_dsn(source)
    root=Path(os.environ['R9_SOURCE_ROOT']).resolve()
    head_path=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    protected={str(p):_sha(p) for base in (root,source) for p in
        (base/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',base/'data/v4/V4_DATA_ACCEPTED_HEAD.json') if p.is_file()}
    records=[]
    for _ in range(2):
        candidate=json.loads(head_path.read_bytes());day=candidate['accepted_trade_date'];started=time.perf_counter()
        api=OperationalSuccessorReaderV1(root,candidate);bff=CoreProductBFFR1(api,None)
        stocks=bff.project('stocks',day);sectors=bff.project('sectors',day)
        lifecycle=build_candidate_lifecycle(root,candidate,source)
        sectors=bff._attach_candidate_lifecycle(sectors,lifecycle)
        parameter=_sha(source/'config/v4_daily_research_priority_r1.json')
        # A changed consumer is a new candidate derivation identity. Existing
        # token/day owners, including prior failed attempts, remain immutable.
        scope=dict(contract_id='V4_R9_CANDIDATE_OWNER_SCOPE_V1',T0=day,
            market_reprojection_contract='R9_MARKET_CORE_SOURCE_REPROJECTION_V1',
            source_workspace=str(root),source_head=ref(root,head_path),source_context_token=api.token,
            source_owners=candidate['owners'][day],parameter_sha256=parameter,
            producers={name:_sha(source/name) for name in ('src/workbench_service/core_product_bff_r1.py',
                'src/workbench_service/research_priority_r1.py','src/sector/candidate_lifecycle_v1.py',
                'src/sector/lifecycle_reconstructed_v1.py')},production_admission=False)
        derived_candidate=dict(candidate,r9_derivation_scope=scope)
        token=_digest(derived_candidate)
        from workbench_analysis.operational_daily_storage_v1 import atomic_json
        candidate_path=root/'data/v4/r9_candidate_scopes'/token/'CANDIDATE.json'
        atomic_json(root,candidate_path,derived_candidate)
        priority=build_priority(day,token,stocks,sectors,{'regime_publication_status':'NOT_PUBLISHED_V4_03'},
            candidate['owners'][day]['core'],candidate['owners'][day]['sector'],parameter)
        priority.update(source_context_token=api.token,derivation_scope=scope)
        for domain,rows,oracle in [('stocks',stocks,_stock_oracle),('sectors',sectors,_sector_oracle)]:
            expected=oracle(rows,day);got=priority[domain]
            assert [(row['entity_id'],row['score']) for row in got['all_items']]==[(row[0],row[1]) for row in expected]
            assert len(rows)==got['rankable']+got['not_rankable']==len(set(row['entity_id'] for row in rows))
            assert {row['entity_id'] for row in rows}=={row['entity_id'] for key in ('all_items','not_rankable_rows') for row in got[key]}
        binding,_=prepare_priority(root,token,day,priority)
        assert load_priority(root,token,day)[1]==priority
        prepared=prepare_lifecycle(root,token,day,list(lifecycle['items'].values()),producer_sha256=lifecycle['producer_sha256'],
            parameter_digest=lifecycle['parameter_sha256'],input_digest=lifecycle['candidate_digest'])
        assert load_lifecycle(root,token,day)[1]==lifecycle['items']
        # Repeating exact candidate input is idempotent, not a second Owner.
        assert prepare_priority(root,token,day,priority)[0]==binding
        cores={row['security_id']:row for row in bff.source('core',day)}
        adjusted={row['security_id']:row for row in bff.source('adjusted',day)}
        record=dict(T0=day,candidate_context_token=token,candidate_binding=ref(root,candidate_path),
            source_context_token=api.token,scope=scope,
            counts={domain:{k:priority[domain][k] for k in ('total','rankable','not_rankable')} for domain in ('stocks','sectors')},
            exclusion_reasons={domain:dict(Counter(row.get('exclusion_reason') for row in priority[domain]['not_rankable_rows'])) for domain in ('stocks','sectors')},
            full_oracle='PASS_ID_SCORE_SORT_AND_DENOMINATOR',priority_binding=binding,lifecycle_binding=prepared,
            coordinate_matches=sum(_exact_price_coordinate(row,adjusted.get(sid)) is not None for sid,row in cores.items()),
            core_count=len(cores),adjusted_count=len(adjusted),
            lifecycle_states={key:dict(Counter(row[key]['current'] for row in lifecycle['items'].values())) for key in ('maturity','health')},
            duration_seconds=round(time.perf_counter()-started,3),production_head_changed=False)
        records.append(record)
        output=Path(os.environ['R9_OWNER_EVIDENCE']);temp=output.with_suffix('.tmp')
        temp.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf8');os.replace(temp,output)
        print('真实候选 PG 全量对账',day,record['counts'],flush=True)
        head_path=checked(root,candidate['predecessor'])
    assert all(_sha(Path(path))==digest for path,digest in protected.items())
