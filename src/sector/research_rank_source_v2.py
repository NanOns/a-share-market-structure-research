"""Extract the existing strength RS/cycle rank from bound Core research inputs.

RET minus the same-date normal-universe median is the original strength RS,
not RPS, absolute RET or the Native percentile. All history stays reconstructed.
"""
import json
from pathlib import Path
import pandas as pd
from workbench_analysis.r43_owner_replay import checked,gzrows,ref
from workbench_analysis.v4_14_replay_io import publish,digest
from .operational_candidate_v1 import produce_rank_window_sources


def extract_strength(core,states,day):
    from workbench_analysis.strict_source_candidate_v2 import validate_cutoff
    for group in (core,states):
        if any(r['trade_date']!=day for r in group) or len({r['security_id'] for r in group})!=len(group):
            raise ValueError('RANK_DATED_UNIQUE_INPUT_REQUIRED')
        for row in group:validate_cutoff(row,day)
    normal={r['security_id']:r['target_values'].get('normal_universe') for r in states}
    returns={n:{r['security_id']:r['fields'][f'ret{n}']['value'] for r in core
        if normal.get(r['security_id']) is True and r['fields'][f'ret{n}'].get('quality_state')=='OBSERVED'
        and r['fields'][f'ret{n}'].get('value') is not None} for n in (5,20)}
    medians={n:float(pd.Series(rs,dtype=float).median()) if len(rs)>=100 else None for n,rs in returns.items()}
    result=[]
    for row in core:
        sid=row['security_id'];values={}
        for n in (5,20):
            v=returns[n].get(sid);m=medians[n];values[f'rs{n}']=v-m if v is not None and m is not None else None
        result.append(dict(security_id=sid,trade_date=day,**values))
    return result


def build(root, *, head, trade_date):
    root=Path(root)
    calendar=ref(root,root/'docs/evidence/r4_3_four_session_closeout_20261009/owner_v3/FOCUS_CALENDAR.json')
    sessions=json.loads(checked(root,calendar).read_bytes())['session_dates'];i=sessions.index(trade_date)
    if i<3:raise ValueError('THREE_SESSION_SOURCE_WINDOW_REQUIRED')
    dates=sessions[i-3:i+1]
    if any(d not in head['owners'] for d in dates):raise ValueError('DATED_CORE_RANK_WINDOW_NOT_AVAILABLE')
    snapshot=json.loads(checked(root,head['membership_snapshot']).read_bytes())
    raw_members=[r for r in gzrows(checked(root,snapshot['memberships'])) if r['security_id']]
    technical=[];members=[];sources=[]
    for day in dates:
        owner=head['owners'][day];sources.extend([owner['core'],owner['prewatch']])
        core=gzrows(checked(root,owner['core']));states=gzrows(checked(root,owner['prewatch']))
        technical.extend(extract_strength(core,states,day))
        # This explicit latest-member historical replay never becomes PIT.
        members.extend(dict(security_id=r['security_id'],sector_id=r['sector_id'],sector_type=r['sector_type'],
                            sector_name=r['sector_name'],trade_date=day) for r in raw_members)
    algorithms=[ref(root,root/p) for p in ('src/workbench_analysis/strength.py','src/workbench_analysis/sector_cycle.py',
        'src/workbench_service/research_builder.py','src/sector/research_rank_source_v2.py')]
    slot=digest([sources,head['membership_snapshot'],calendar,algorithms])
    tb=publish(root,f'data/v4/research_rank_sources_v2/{slot}/technical.json',dict(rows=technical,sources=sources,
        extraction='Existing strength RS=normal RET minus same-date normal RET median; min_universe=100',
        algorithms=algorithms,production=False,evidence_class='RECONSTRUCTED_RESEARCH_ONLY'))
    mb=publish(root,f'data/v4/research_rank_sources_v2/{slot}/members.json',dict(rows=members,
        source=head['membership_snapshot'],production=False,evidence_class='RECONSTRUCTED_RESEARCH_ONLY'))
    ast=ref(root,root/'config/v4_08_b2_machine_ast_r5.json')
    return produce_rank_window_sources(root,technical_binding=tb,memberships_binding=mb,
        calendar_binding=calendar,trade_date=trade_date,ast_binding=ast)
