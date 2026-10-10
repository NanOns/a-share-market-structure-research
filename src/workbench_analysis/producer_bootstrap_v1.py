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
                    trade_date=day, requested_at=artifact.get('requested_at'), received_at=artifact['observed_at']),
               dict(name='native_baostock', path=native['path'], sha256=native['sha256'], trade_date=day,
                    requested_at=native_doc.get('requested_at'), received_at=native_time),
               dict(name='tdx_target',path=artifact['tdx']['path'],sha256=artifact['tdx']['sha256'],trade_date=day,
                    requested_at=None,received_at=target_doc['source_available_at'])]
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
    document = produce(rows, universe=life['active_security_ids'], trade_date=day,
        source_binding=owner['prewatch'], membership_binding=head['membership_snapshot'],
        model_binding=ref(root, root/'src/workbench_analysis/r43_focus_replay.py'),
        config_binding=ref(root, root/'config/research_attention_v3.yaml'), captured_at=head['observed_at'])
    return freeze(root, document, publication_id=owner['prewatch']['sha256'], revision='r1')


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
