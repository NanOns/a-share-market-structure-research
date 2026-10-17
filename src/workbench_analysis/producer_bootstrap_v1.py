"""Optional DD sidecar; failures cannot block the accepted daily main flow."""
from datetime import datetime, timezone
from pathlib import Path
import json
from .r43_owner_replay import source_ingress, ref
from .source_capture_candidate_v1 import capture
from .full_state_signal_candidate_v1 import produce


def _pg_owner_rows(root, head, day, domain):
    from workbench_db.v4_operational_owner_authority_v2 import read_domain
    return read_domain(root,head,day,domain,workspace_root=str(root))


def _candidate_document(value, day):
    """Accept an in-memory candidate envelope only; never reopen its workspace copy."""
    if not isinstance(value, dict):
        raise ValueError('PG_OPERATIONAL_CANDIDATE_REQUIRED_NO_FILE_FALLBACK')
    if value.get('contract_id') != 'V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1':
        raise ValueError('PG_OPERATIONAL_CANDIDATE_CONTRACT_REQUIRED')
    if value.get('accepted_trade_date') != day:
        raise ValueError('PG_OPERATIONAL_CANDIDATE_T0_MISMATCH')
    return value


def capture_daily_sources(root, day, freeze_binding, *, pg_head_candidate=None, research_replay=False):
    root = Path(root)
    artifact = json.loads(source_ingress(root, freeze_binding).read_bytes())
    # Candidate transport can provide the binding envelope, while all Owner,
    # membership and predecessor payloads are re-read from PG below. It does
    # not confer accepted Head authority.
    if not isinstance(pg_head_candidate, dict):
        raise ValueError('PG_OPERATIONAL_HEAD_CANDIDATE_REQUIRED')
    head = pg_head_candidate
    if head.get('contract_id') != 'V4_OPERATIONAL_INCREMENTAL_SUCCESSOR_V1':
        raise ValueError('PG_ACCEPTED_OPERATIONAL_HEAD_CONTRACT_REQUIRED')
    from workbench_db.v4_membership_reference_pg_v1 import context_snapshot, read as read_membership
    snapshot = context_snapshot(root, head)
    membership_rows = read_membership(root, head, workspace_root=str(root))
    from workbench_db.v4_market_calendar_reader_r1 import from_environment as market_calendar_reader
    accepted_calendar=market_calendar_reader().calendar()
    from workbench_db.v4_operational_owner_authority_v2 import load as load_owner, read as read_owner
    owner_authority = load_owner(root, head)
    lifecycle_binding = head['owners'][head['accepted_trade_date']]['lifecycle']
    lifecycle_rows = read_owner(root, owner_authority, head['accepted_trade_date'], 'lifecycle',
                                lifecycle_binding, workspace_root=str(root))
    if not isinstance(lifecycle_rows,list) or any(not isinstance(row,dict) for row in lifecycle_rows):
        raise ValueError('PG_LIFECYCLE_OWNER_PAYLOAD_SHAPE_INVALID')
    active_security_ids=sorted({row['security_id'] for row in lifecycle_rows if row.get('security_id')})
    if not active_security_ids:raise ValueError('PG_LIFECYCLE_ACTIVE_UNIVERSE_EMPTY')
    native = artifact['native_baostock']
    native_doc = json.loads(source_ingress(root, native).read_bytes())
    native_time = native_doc['observed_at']
    transport=native_doc.get('source_transport_v2',{})
    native_requested = native_doc.get('requested_at') or transport.get('requested_at') or transport.get('daily',{}).get('requested_at')
    target_doc=json.loads(source_ingress(root,artifact['tdx']).read_bytes())
    sources = [dict(name='daily_freeze', path=freeze_binding['path'], sha256=freeze_binding['sha256'],
                    trade_date=day, requested_at=native_requested, received_at=artifact['observed_at']),
               dict(name='native_baostock', path=native['path'], sha256=native['sha256'], trade_date=day,
                    requested_at=native_requested, received_at=native_time),
               dict(name='tdx_target',path=artifact['tdx']['path'],sha256=artifact['tdx']['sha256'],trade_date=day,
                    requested_at=target_doc.get('source_transport_v2',{}).get('requested_at'),received_at=target_doc['source_available_at'])]
    # Membership and market calendar are already typed PG facts. Preserve their
    # exact identities in the candidate without reopening archived source paths.
    members = membership_rows
    return capture(root, trade_date=day, sessions=accepted_calendar['session_dates'],
        calendar_binding=accepted_calendar['binding'], sources=sources,
        security_ids=active_security_ids, sector_ids=sorted({r['sector_id'] for r in members}),
        model_binding=ref(root, root/'src/workbench_analysis/r43_focus_replay.py'),
        config_binding=ref(root, root/'config/research_attention_v3.yaml'), research_replay=research_replay,
        preliminary_scope=dict(head=head.get('publication_binding'),calendar=accepted_calendar['binding'],
            accepted_trade_date=head['accepted_trade_date'], lifecycle=head['owners'][head['accepted_trade_date']]['lifecycle'],
            membership_snapshot=head['membership_snapshot'],membership_pg_binding=snapshot['memberships']))


def produce_daily_state(root, day, candidate_binding):
    root = Path(root)
    head = _candidate_document(candidate_binding, day)
    owner = head['owners'][day]
    from workbench_db.v4_membership_reference_pg_v1 import context_snapshot
    snapshot=context_snapshot(root,head)
    life_rows=_pg_owner_rows(root,head,day,'lifecycle')
    universe=sorted({r['security_id'] for r in life_rows if isinstance(r,dict) and r.get('security_id')})
    rows = _pg_owner_rows(root,head,day,'prewatch')
    # Original operational State currently remains reconstructed. A contemporary
    # raw capture does not silently elevate its windows or historical members.
    from .v4_14_replay_io import digest,publish
    model=ref(root,root/'src/workbench_analysis/r43_focus_replay.py')
    config=ref(root,root/'config/research_attention_v3.yaml')
    implementation=ref(root,root/'src/workbench_analysis/full_state_signal_candidate_v1.py')
    slot=digest([owner['prewatch'],owner['lifecycle'],snapshot['memberships'],model,config,implementation,'freeze-clock-v2'])
    path=f'data/v4/state_signal_candidates_v2/{slot}/signals.json'
    if (root/path).exists():return ref(root,root/path)
    document = produce(rows, universe=universe, trade_date=day,
        source_binding=owner['prewatch'], membership_binding=snapshot['memberships'],
        model_binding=model,config_binding=config,captured_at=datetime.now(timezone.utc).isoformat())
    from .producer_dependency_archive_v1 import freeze_dependencies
    freeze_dependencies(root,[model,config,implementation])
    return publish(root,path,dict(document,implementation=implementation,publication_id=owner['prewatch']['sha256'],revision='r2',
        frozen_clock_basis='ACTUAL_CANDIDATE_FREEZE_TIME'))


def build_review_and_display_candidates(root,day,candidate,capture_result,*,candidate_binding,research_replay=False):
    """Build the exact-daily candidate handoff in memory for the PG Owner writer."""
    from .producer_candidate_index_pg_v1 import build_review_and_display_candidates as build_pg_index
    return build_pg_index(root, day, candidate, capture_result, candidate_binding=candidate_binding,
                          research_replay=research_replay)


def produce_first_observed_state(root, day, candidate_binding):
    """Capture an explicitly supplied full-market source without admitting it.

    No fallback from reconstructed prewatch, no grants, no accepted Head edits.
    The optional input must bind all three source versions for this exact day.
    """
    root=Path(root)
    head=_candidate_document(candidate_binding, day)
    inputs=head.get('first_observed_state_sources',{}).get(day)
    if not inputs:
        return dict(status='SOURCE_INCOMPLETE',formal_status='BLOCKED',
                    reason='AUTHORITATIVE_FULL_MARKET_STATE_SOURCE_NOT_SUPPLIED',
                    production_write_authorized=False,observed_count=None)
    if set(inputs)!=set(('state','membership','model')):
        raise ValueError('FIRST_OBSERVED_STATE_VERSIONED_INPUTS_REQUIRED')
    from .full_state_first_observed_v1 import freeze_first_observed
    return freeze_first_observed(root,state_binding=inputs['state'],membership_binding=inputs['membership'],
            model_binding=inputs['model'],candidate_directory='data/v4/candidate_stores/full_state_first_observed_candidates_v1')


def produce_daily_sector(root, day, candidate_binding):
    from sector.operational_candidate_v1 import compute
    from .v4_14_replay_io import publish
    root = Path(root)
    head = _candidate_document(candidate_binding, day)
    owner = head['owners'][day]
    from workbench_db.v4_membership_reference_pg_v1 import context_snapshot,read as read_memberships
    membership_context=context_snapshot(root,head)
    memberships=read_memberships(root,head,workspace_root=str(root))
    sector_rows=_pg_owner_rows(root,head,day,'sector')
    core_rows=_pg_owner_rows(root,head,day,'core')
    state_rows=_pg_owner_rows(root,head,day,'prewatch')
    rows = compute(sector_rows,core_rows,
        [r for r in memberships if r.get('security_id')], trade_date=day,root=root,
        state_rows=state_rows)
    model=ref(root,root/'src/sector/operational_candidate_v1.py')
    return publish(root,f"data/v4/sector_operational_candidates/{day}/{owner['sector']['sha256']}/{model['sha256']}/candidate.json",
        dict(contract_id='SECTOR_D2_OPERATIONAL_CANDIDATE_V1', rows=rows, sources={k:owner[k] for k in ('core','sector')},
             production=False, formal_consumer_enabled=False, membership=membership_context['memberships'],
             model=model,state_source=owner['prewatch']))


def optional_step(function, *args, **kwargs):
    try:
        value=function(*args, **kwargs)
        if isinstance(value,dict) and 'status' in value and not (value.get('path') and value.get('sha256')):
            return dict(value,production=False,main_flow_blocked=False)
        return dict(status='CANDIDATE_PRODUCED', candidate=value, production=False)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return dict(status='CANDIDATE_FAILED', reason=f'{type(error).__name__}:{error}',
                    production=False, main_flow_blocked=False)
