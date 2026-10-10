"""Optional DD sidecar; failures cannot block the accepted daily main flow."""
from datetime import datetime, timezone
from pathlib import Path
import json
from .r43_owner_replay import checked, gzrows, ref
from .market_source_acquisition import official_sessions
from .source_capture_candidate_v1 import capture
from .full_state_signal_candidate_v1 import produce, freeze


def capture_daily_sources(root, day, freeze_binding, *, research_replay=False):
    root = Path(root)
    artifact = json.loads(checked(root, freeze_binding).read_bytes())
    head = json.loads((root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    snapshot = json.loads(checked(root, head['membership_snapshot']).read_bytes())
    life = json.loads(checked(root, head['owners'][head['accepted_trade_date']]['lifecycle']).read_bytes())
    native = artifact['native_baostock']
    native_doc = json.loads(checked(root, native).read_bytes())
    native_time = native_doc['observed_at']
    target_doc=json.loads(Path(artifact['tdx']['path']).read_bytes())
    sources = [dict(name='daily_freeze', path=freeze_binding['path'], sha256=freeze_binding['sha256'],
                    trade_date=day, requested_at=native_doc.get('requested_at'), received_at=artifact['observed_at']),
               dict(name='native_baostock', path=native['path'], sha256=native['sha256'], trade_date=day,
                    requested_at=native_doc.get('requested_at'), received_at=native_time),
               dict(name='tdx_target',path=artifact['tdx']['path'],sha256=artifact['tdx']['sha256'],trade_date=day,
                    requested_at=target_doc.get('source_transport_v2',{}).get('requested_at'),received_at=target_doc['source_available_at'])]
    # Local member bytes are observed again now, even if their SHA is unchanged.
    # This proves observation today, never their historical effective date.
    for i, source in enumerate(snapshot['sources']):
        now = datetime.now(timezone.utc).isoformat()
        sources.append(dict(name=f'local_members_{i}', path=source['address'], trade_date=day,
                            requested_at=now, received_at=now,timestamp_basis='LOCAL_READ'))
    calendar = root/'docs/evidence/r4_3_four_session_closeout_20261009/owner_v3/FOCUS_CALENDAR.json'
    members = gzrows(checked(root, snapshot['memberships']))
    return capture(root, trade_date=day, sessions=official_sessions(root),
        calendar_binding=ref(root, calendar), sources=sources,
        security_ids=life['active_security_ids'], sector_ids=sorted({r['sector_id'] for r in members}),
        model_binding=ref(root, root/'src/workbench_analysis/r43_focus_replay.py'),
        config_binding=ref(root, root/'config/research_attention_v3.yaml'), research_replay=research_replay)


def produce_daily_state(root, day, candidate_binding):
    root = Path(root)
    head = json.loads(checked(root, candidate_binding).read_bytes())
    owner = head['owners'][day]
    life = json.loads(checked(root, owner['lifecycle']).read_bytes())
    rows = gzrows(checked(root, owner['prewatch']))
    # Original operational State currently remains reconstructed. A contemporary
    # raw capture does not silently elevate its windows or historical members.
    from .v4_14_replay_io import digest,publish
    model=ref(root,root/'src/workbench_analysis/r43_focus_replay.py')
    config=ref(root,root/'config/research_attention_v3.yaml')
    implementation=ref(root,root/'src/workbench_analysis/full_state_signal_candidate_v1.py')
    slot=digest([owner['prewatch'],owner['lifecycle'],head['membership_snapshot'],model,config,implementation,'freeze-clock-v2'])
    path=f'data/v4/state_signal_candidates_v2/{slot}/signals.json'
    if (root/path).exists():return ref(root,root/path)
    document = produce(rows, universe=life['active_security_ids'], trade_date=day,
        source_binding=owner['prewatch'], membership_binding=head['membership_snapshot'],
        model_binding=model,config_binding=config,captured_at=datetime.now(timezone.utc).isoformat())
    return publish(root,path,dict(document,implementation=implementation,publication_id=owner['prewatch']['sha256'],revision='r2',
        frozen_clock_basis='ACTUAL_CANDIDATE_FREEZE_TIME'))


def build_review_and_display_candidates(root,day,candidate_binding,capture_result,*,research_replay=False):
    """Finish the isolated chain, publish a display index without changing Head."""
    from sector.operational_candidate_v2 import build as build_sector
    from .strict_source_candidate_v2 import freeze_for_review
    from .operational_daily_storage_v1 import atomic_json
    root=Path(root)
    sector=optional_step(build_sector,root,candidate_binding=candidate_binding,trade_date=day)
    state=optional_step(produce_daily_state,root,day,candidate_binding)
    strict=(optional_step(freeze_for_review,root,capture_binding=capture_result['candidate'],candidate_binding=candidate_binding,
                trade_date=day,research_replay=research_replay) if capture_result.get('candidate') else
            dict(status='CANDIDATE_FAILED',reason='INITIAL_CAPTURE_FAILED',production=False))
    sessions=official_sessions(root)
    index_path=root/'data/v4/producer_candidate_index_v2.json'
    index=json.loads(index_path.read_bytes()) if index_path.exists() else dict(contract_id='PRODUCER_CANDIDATE_INDEX_V2',sessions={})
    entry=dict(head=candidate_binding,next_session=next((d for d in sessions if d>day),None),production=False)
    for key,result in (('sector',sector),('full_state',state),('strict_source',strict),('source_capture',capture_result)):
        if result.get('candidate'):entry[key]=result['candidate']
        else:entry[key+'_failure']=result.get('reason')
    index['sessions'][day]=entry
    atomic_json(root,index_path,index)
    return dict(sector=sector,full_state=state,strict_source=strict,index=ref(root,index_path))


def produce_daily_sector(root, day, candidate_binding):
    from sector.operational_candidate_v1 import compute
    from .v4_14_replay_io import publish
    root = Path(root)
    head = json.loads(checked(root,candidate_binding).read_bytes())
    owner = head['owners'][day]
    snapshot = json.loads(checked(root, head['membership_snapshot']).read_bytes())
    rows = compute(gzrows(checked(root,owner['sector'])),gzrows(checked(root,owner['core'])),
        [r for r in gzrows(checked(root,snapshot['memberships'])) if r['security_id']], trade_date=day,root=root,
        state_rows=gzrows(checked(root,owner['prewatch'])))
    model=ref(root,root/'src/sector/operational_candidate_v1.py')
    return publish(root,f"data/v4/sector_operational_candidates/{day}/{owner['sector']['sha256']}/{model['sha256']}/candidate.json",
        dict(contract_id='SECTOR_D2_OPERATIONAL_CANDIDATE_V1', rows=rows, sources={k:owner[k] for k in ('core','sector')},
             production=False, formal_consumer_enabled=False, membership=head['membership_snapshot'],model=model,state_source=owner['prewatch']))


def optional_step(function, *args, **kwargs):
    try:
        return dict(status='CANDIDATE_PRODUCED', candidate=function(*args, **kwargs), production=False)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return dict(status='CANDIDATE_FAILED', reason=f'{type(error).__name__}:{error}',
                    production=False, main_flow_blocked=False)
