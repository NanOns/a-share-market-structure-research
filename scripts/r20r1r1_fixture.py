"""Isolated exact-authority reachability fixtures, never current accepted evidence."""
import copy,json,os,tempfile
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path
from scripts.r20r1r1_io import ROOT,ref
def put(root,path,value=None,raw=None):
    root=Path(root).resolve()
    if root==ROOT.resolve() or not (root.is_relative_to(Path(tempfile.gettempdir()).resolve()) or root.is_relative_to((ROOT/'reports/r20r1r1/engineering_fixtures').resolve())):raise ValueError('ISOLATED_TEST_NAMESPACE_REQUIRED')
    p=(root/path).resolve()
    if not p.is_relative_to(root):raise ValueError('PATH_ESCAPE')
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');t.write_bytes(raw if raw is not None else (json.dumps(value,sort_keys=True,indent=2)+'\n').encode());os.replace(t,p);return ref(path,root)
def build(root,horizons=(1,)):
    root=Path(root);registry=json.loads((ROOT/'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json').read_bytes())
    head=json.loads((ROOT/registry['accepted_head']['path']).read_bytes());producer=json.loads((ROOT/registry['producer_receipt']['path']).read_bytes())
    copies=[registry[k] for k in ['accepted_head','owner_publication','enrollment','freeze','producer_receipt','T0_data_archive']]+[head['bindings']['runtime_seal'],head['bindings']['calendar']]
    for b in copies:put(root,b['path'],raw=(ROOT/b['path']).read_bytes())
    put(root,'data/v4/V4_STAGE_ACCEPTED_HEAD.json',raw=(ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json').read_bytes())
    put(root,'config/v4_15_maturity_t0_lineage_r20r1r1_v2.json',registry)
    put(root,'config/v4_15_maturity_debt_contract_r20r1r1_v2.json',raw=(ROOT/'config/v4_15_maturity_debt_contract_r20r1r1_v2.json').read_bytes())
    calendar=json.loads((ROOT/head['bindings']['calendar']['path']).read_bytes());past=[x['trade_date'] if isinstance(x,dict) else x for x in calendar['session_dates']]
    future=[];day=date(2026,10,8)
    while len(future)<20:
        if day.weekday()<5:future.append(day.isoformat())
        day+=timedelta(days=1)
    cal=put(root,'fixtures/future_accepted_calendar.json',dict(session_dates=past+future,fixture_scope='ENGINEERING_REACHABILITY_ONLY'))
    enrollment=json.loads((ROOT/registry['enrollment']['path']).read_bytes());freeze=json.loads((ROOT/registry['freeze']['path']).read_bytes());reference=Decimal(str(freeze['comparison_reference']))
    packets=[];parent=registry['T0_data_archive'];all_endpoints=[]
    for n in sorted(horizons):
        rows=[];endpoints=[];due=future[n-1]
        for j,day in enumerate(future[:n],1):
            close=reference*(Decimal(1)+Decimal(j)/100-Decimal(j%3)/200)
            row=dict(trade_date=day,security_id=freeze['signal_id'],source_authority='TDX_OFFICIAL_PACKAGE',close=float(close),high=float(close*Decimal('1.02')),low=float(close*Decimal('0.97')),evaluation_basis_date=due,verified_identity=True,verified_adjustment=True,T0_basis_verified=True,status='ACTUAL',transform_coefficients=dict(alpha=1,beta=0),T0_transform_coefficients=dict(alpha=1,beta=0))
            rows.append(row);endpoints.append(put(root,f'fixtures/endpoints/n{n}_{day}.json',dict(contract_id='DM01_ADJUSTED_DAILY_ARTIFACT_R3_3',rows=[row],fixture_scope='ENGINEERING_REACHABILITY_ONLY')))
        all_endpoints.extend(endpoints)
        data=dict(contract_id='V4_DATA_ACCEPTED_HEAD_V2',accepted_trade_date=due,parent_archive=parent,calendar=cal,component_artifacts=dict(FORWARD_EVALUATION_INPUTS=copy.deepcopy(all_endpoints)),fixture_scope='ENGINEERING_REACHABILITY_ONLY')
        data_ref=put(root,f'fixtures/accepted_data_{due}.json',data);put(root,'data/v4/V4_DATA_ACCEPTED_HEAD.json',data);parent=data_ref
        peak=reference;mdd=Decimal(0)
        for row in rows:c=Decimal(str(row['close']));peak=max(peak,c);mdd=min(mdd,c/peak-1)
        metrics=dict(R_N=float(Decimal(str(rows[-1]['close']))/reference-1),MFE_N=float(max([reference]+[Decimal(str(r['high'])) for r in rows])/reference-1),MAE_N=float(min([reference]+[Decimal(str(r['low'])) for r in rows])/reference-1),PATH_MDD_CLOSE_N=float(mdd))
        outcome=put(root,f'fixtures/outcome_n{n}_r1.json',dict(enrollment_id=enrollment['enrollment_id'],frozen_t0=registry['freeze'],outcome_status='OBSERVED',horizon=n,due_date=due,evidence_class='REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED',HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',price_path=rows,revision_sequence=1,supersedes=None,**metrics))
        opened=due+'T16:30:00+00:00'
        log=put(root,f'fixtures/read_receipt_n{n}.json',dict(freeze=registry['freeze'],accepted_endpoints=endpoints,first_future_endpoint_open_at=opened,raw_provider_fallback=False))
        packets.append(dict(accepted_head=registry['accepted_head'],data_head=data_ref,owner_publication=registry['owner_publication'],enrollment=registry['enrollment'],freeze=registry['freeze'],horizon=n,accepted_endpoints=endpoints,outcome=outcome,endpoint_read_receipt=log,freeze_completed_at=producer['end'],first_future_endpoint_open_at=opened,raw_provider_fallback=False,historical_prices_only=False,HISTORICAL_PIT_EFFECTIVENESS='NOT_GRANTED',REALTIME_ACCEPTED_COHORT_MATURITY='NOT_GRANTED'))
    put(root,'fixtures/packets.json',packets);return packets
