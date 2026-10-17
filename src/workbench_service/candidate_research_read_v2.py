"""Optional, head-bound candidate display. No formal fields or counts change."""
import json
import hashlib
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo
from workbench_analysis.r43_operational_publication import digest

CONTRACT='OPERATIONAL_CANDIDATE_DISPLAY_READ_V2'


def first_capture_readiness(head, day, sessions, *, evaluated_at=None, session_close='15:00:00'):
    """Pure, clock-aware first-capture status; performs no extraction or writes.

    The session calendar supplies the candidate date, while the accepted
    exchange close in the versioned V4 calendar contract supplies the T0
    cutoff. A missing producer/receipt after that cutoff is reported as a
    missed first capture and is never repaired by a later observation.
    """
    zone=ZoneInfo('Asia/Shanghai')
    if evaluated_at is None:evaluated_at=datetime.now(zone)
    elif isinstance(evaluated_at,str):evaluated_at=datetime.fromisoformat(evaluated_at)
    if evaluated_at.tzinfo is None:evaluated_at=evaluated_at.replace(tzinfo=zone)
    evaluated_at=evaluated_at.astimezone(zone)
    accepted=head.get('accepted_trade_date')
    next_session=None
    if accepted in sessions:
        index=sessions.index(accepted)
        if index+1<len(sessions):next_session=sessions[index+1]
    candidate_session=day if day in sessions and (not accepted or day>accepted) else next_session
    gate_day=candidate_session or accepted or day
    owners=head.get('owners',{}).get(gate_day,{})
    producer=head.get('cohort_signal_producers',{}).get(gate_day)
    capture=head.get('cohort_capture_receipts',{}).get(gate_day)
    required={
        'FULL_AS_RECORDED_SIGNAL_PRODUCER':producer,
        'INDEPENDENT_VALIDATION_COHORT_OWNER':owners.get('validation_cohort'),
        'COMPLETE_FIRST_CAPTURE_RECEIPT':capture,
        'SEPARATE_FIRST_CAPTURE_WRITE_GRANT':head.get('cohort_write_grants',{}).get(gate_day),
    }
    missing=[name for name,binding in required.items() if not binding]
    cutoff=(datetime.combine(datetime.fromisoformat(candidate_session).date(),time.fromisoformat(session_close),zone)
            if candidate_session else None)
    future_session=bool(candidate_session and evaluated_at.date()<cutoff.date())
    before_cutoff=bool(cutoff and evaluated_at<cutoff)
    if not candidate_session:
        status='NOT_VERIFIABLE';missing_reason='OFFICIAL_SESSION_CALENDAR_COVERAGE_UNAVAILABLE'
    elif future_session or before_cutoff:
        status='PENDING_NEXT_SESSION'
        missing_reason='PENDING_FUTURE_SESSION'
    elif not producer or not capture:
        status='SOURCE_NOT_CAPTURED'
        missing_reason='NOT_CAPTURED_AT_T0' if cutoff and evaluated_at>=cutoff else 'MISSING_SOURCE'
    elif required['INDEPENDENT_VALIDATION_COHORT_OWNER'] is None or required['SEPARATE_FIRST_CAPTURE_WRITE_GRANT'] is None:
        status='NOT_ADMITTED';missing_reason='NOT_ADMITTED'
    else:
        status='CAPTURE_READY';missing_reason=None
    receipt=capture or {}
    admitted=receipt.get('admitted_count')
    if receipt.get('admission_status')=='ADMITTED' and admitted==0:status='ADMITTED_ZERO'
    elif receipt.get('admission_status')=='ADMITTED' and isinstance(admitted,int) and admitted>0:status='ADMITTED_NONZERO'
    settlement=receipt.get('settlement_status')
    if settlement in ('DUE_UNSETTLED','SETTLED'):
        settlement_status=settlement
    elif receipt.get('due_at'):
        due_at=datetime.fromisoformat(receipt['due_at'])
        if due_at.tzinfo is None:due_at=due_at.replace(tzinfo=zone)
        settlement_status='NOT_DUE' if evaluated_at<due_at.astimezone(zone) else 'DUE_UNSETTLED'
    else:settlement_status='NOT_DUE'
    missing_reasons={name:('MISSING_SOURCE' if name=='FULL_AS_RECORDED_SIGNAL_PRODUCER' else
                          'NOT_CAPTURED_AT_T0' if name=='COMPLETE_FIRST_CAPTURE_RECEIPT' and cutoff and evaluated_at>=cutoff else
                          'PENDING_FUTURE_SESSION' if candidate_session and cutoff and evaluated_at<cutoff else
                          'NOT_ADMITTED') for name in missing}
    return dict(contract_id='COHORT_FIRST_CAPTURE_READINESS_VIEW_R2',status=status,
        trade_date=day,as_of_trade_date=accepted,evaluated_at=evaluated_at.isoformat(),accepted_trade_date=accepted,
        next_session=next_session,next_capture_session=candidate_session,
        capture_deadline=cutoff.isoformat() if cutoff else None,
        first_available_at=receipt.get('first_available_at'),
        capture_condition='NEXT_SESSION_ACCEPTED_WITH_FULL_AS_RECORDED_SIGNAL_LEDGER_AND_INDEPENDENT_OWNER_AND_GRANT',
        missing_inputs=missing,missing_input_reasons=missing_reasons,missing_reason=missing_reason,
        capture_state='NOT_CAPTURED_AT_T0' if not capture and cutoff and evaluated_at>=cutoff else 'CAPTURE_PRESENT' if capture else 'PENDING',
        admission_status=receipt.get('admission_status','NOT_ADMITTED'),settlement_status=settlement_status,
        production_write_authorized=False,formal_cohort_enrollment_enabled=False,
        observed_count=receipt.get('observed_count'),admitted_count=admitted,
        matured_count=receipt.get('matured_count'),settled_count=receipt.get('settled_count'),
        historical_backfill_permitted=False)


def capture_calendar_contract(root):
    """Load the approved calendar cutoff contract only from its PG registry entry."""
    import os
    contract_id='V4_DM01_OFFICIAL_CALENDAR_BRIDGE_V1';version='1.0.0'
    source=os.environ.get('V4_DAILY_CONTRACT_SOURCE','PG')
    if source!='PG':raise ValueError('DAILY_RUNTIME_CONTRACT_PG_ONLY')
    namespace=os.environ.get('V4_PG_MODEL_NAMESPACE_ID','').strip()
    try:identity=json.loads(os.environ.get('V4_PG_EXPECTED_DATABASE_IDENTITY_JSON','{}'))
    except ValueError as exc:raise ValueError('PG_DATABASE_IDENTITY_CONFIGURATION_INVALID') from exc
    if not namespace:raise ValueError('PG_MODEL_NAMESPACE_REQUIRED_FOR_DAILY_CONTRACT')
    from workbench_analysis.contract_registry_pg_v1 import (
        ContractRegistryError,
        load_current_approved_contract,
    )
    from workbench_db.v4_publication_reader import readonly_connection
    try:
        with readonly_connection() as pg:
            registered=load_current_approved_contract(pg,contract_id,version,namespace,
                expected_database_identity=identity)
    except ContractRegistryError as exc:
        raise ValueError(str(exc)) from exc
    document=registered.parsed_json
    raw=registered.raw_content
    runtime=document.get('runtime',{})
    if (document.get('contract_id')!=contract_id
            or document.get('version')!=version
            or runtime.get('timezone')!='Asia/Shanghai'
            or not runtime.get('market_close_local')):
        raise ValueError('SESSION_CUTOFF_CONTRACT_INVALID')
    binding={'source':'PG_APPROVED_REGISTRY',
        'sha256':hashlib.sha256(raw).hexdigest(),'contract_id':document['contract_id'],
        'version':document['version'],'timezone':runtime['timezone']}
    return runtime['market_close_local'],binding


def checked_dependency(root,binding):
    """Materialize exact frozen code/config bytes from PG source ingress."""
    from pathlib import Path
    root=Path(root).resolve()
    relative=Path(binding['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('DEPENDENCY_PATH_ESCAPE')
    if relative.parts and relative.parts[0] in ('src','config'):
        archive=root/'data/v4/artifact_store/producer_dependency_archive_v1'/(binding['sha256']+'.bin')
        try:
            from workbench_db.v4_historical_source_ingress_pg_r1 import materialize_bound
            return materialize_bound(root,dict(path=archive.relative_to(root).as_posix(),
                sha256=binding['sha256'],bytes=archive.stat().st_size))
        except OSError as exc:
            raise ValueError('HISTORICAL_COMPUTATION_BYTES_NOT_CAPTURED') from exc
        except ValueError as exc:
            raise ValueError('HISTORICAL_COMPUTATION_BYTES_NOT_CAPTURED') from exc
    from workbench_db.v4_historical_source_ingress_pg_r1 import materialize_bound
    return materialize_bound(root,binding)


def accepted_candidate_head(root, current, token, binding, day):
    """Resolve only a hash-linked predecessor of the authenticated active reader.

    An archive's existence is not acceptance. Its bytes must also be linked by
    the current accepted release, whose token and fixed pointer still agree.
    """
    token_matches_current = digest(current) == token
    if not token_matches_current:
        raise ValueError('OLD_TOKEN')
    cutoff=current.get('accepted_trade_date')
    if not cutoff or day>cutoff:raise ValueError('FUTURE_DATE')
    if current.get('exact_daily_adjustment_contract') and day==cutoff:
        from workbench_db.v4_membership_reference_pg_v1 import read_research_input_candidate
        # Input-owner conservation uses the exact Head-bound PG fact.
        return read_research_input_candidate(root,current,day,binding)
    raise ValueError('PG_HISTORICAL_RESEARCH_HEAD_REQUIRED_NO_FILE_FALLBACK')


def read_candidates(root, *, head, token, day, sector_id=None):
    root=Path(root)
    result=dict(contract_id=CONTRACT,candidate_status='NOT_CAPTURED',production=False,
        formal_consumer_enabled=False,observed_count=None,matured_count=None,
        cohort_enrollment_enabled=False,trade_date=day)
    try:
        from workbench_analysis.market_source_acquisition import official_sessions
        session_close,calendar_source=capture_calendar_contract(root)
        gate=first_capture_readiness(head,day,official_sessions(root),session_close=session_close)
        gate['calendar_source']=calendar_source
        result['first_capture_readiness']=gate
    except (ValueError,KeyError,TypeError,OSError) as exc:
        result['first_capture_readiness']=dict(contract_id='COHORT_FIRST_CAPTURE_READINESS_VIEW_R2',
            status='NOT_VERIFIABLE',trade_date=day,next_capture_session=None,
            missing_inputs=['OFFICIAL_SESSION_CALENDAR'],reason=str(exc),
            production_write_authorized=False,formal_cohort_enrollment_enabled=False,
            observed_count=None,matured_count=None,settled_count=None,historical_backfill_permitted=False)
    try:
        token_matches_head = digest(head) == token
        if not token_matches_head:
            raise ValueError('OLD_TOKEN')
        if not head.get('accepted_trade_date') or day>head['accepted_trade_date']:
            raise ValueError('FUTURE_DATE')
        if not head.get('exact_daily_adjustment_contract') or day!=head.get('accepted_trade_date'):
            raise ValueError('PG_HISTORICAL_RESEARCH_HEAD_REQUIRED_NO_FILE_FALLBACK')
        from workbench_db.v4_membership_reference_pg_v1 import research_authority
        research=research_authority(root,head,day)
        entry=research.get('index_entry')
        if research.get('index_contract')!='PRODUCER_CANDIDATE_INDEX_V2' or not isinstance(entry,dict):
            raise ValueError('NATIVE_RESEARCH_INDEX_PG_AUTHORITY_REQUIRED_NO_FALLBACK')
        if entry.get('production') is not False:raise ValueError('CANDIDATE_INDEX_SCOPE_REQUIRED')
        current=head;head=accepted_candidate_head(root,head,token,entry['head'],day)
        def read_document(binding):
            from workbench_db.v4_membership_reference_pg_v1 import read_research
            return read_research(root,current,day,binding)

        def read_owner(domain,binding):
            from workbench_db.v4_operational_owner_authority_v2 import load,read
            authority=load(root,current)
            return read(root,authority,day,domain,binding)
        if sector_id is not None:
            binding=entry['sector'];document=read_document(binding)
            if document['T0']!=day or document['production'] is not False:raise ValueError('RESEARCH_SCOPE_REQUIRED')
            if set(document['sources'])!={'lifecycle','core','sector','prewatch'}:
                raise ValueError('COMPLETE_CANDIDATE_SOURCE_BINDINGS_REQUIRED')
            for name,source in document['sources'].items():
                if source!=head['owners'][day][name]:raise ValueError('CANDIDATE_OWNER_MISMATCH')
                read_owner(name,source)
            if document['membership']!=head['membership_snapshot']:raise ValueError('CANDIDATE_MEMBERSHIP_MISMATCH')
            for dep in document['dependencies']+[document['model']]:checked_dependency(root,dep)
            rows=[r for r in document['rows'] if r['sector_id']==sector_id]
            if len(rows)>1:raise ValueError('DUPLICATE_SECTOR_CANDIDATE')
            for row in rows:
                if row['T0']!=day or row['production'] is not False or row['formal_consumer_enabled'] is not False:
                    raise ValueError('RESEARCH_ROW_SCOPE_REQUIRED')
                for cell in row['inputs'].values():
                    if cell.get('source'):
                        from workbench_db.v4_historical_source_ingress_pg_r1 import ingress_path
                        receipt=json.loads(ingress_path(root,cell['source']['path'],
                            expected_sha256=cell['source']['sha256'])['raw'])
                        if receipt['T0']!=day or receipt['sector_id']!=sector_id:raise ValueError('RANK_SOURCE_SCOPE_REQUIRED')
                        for source in receipt['sources']:
                            if source not in head['owners'][day].values():
                                raise ValueError('RANK_SOURCE_OWNER_NOT_BOUND')
            return dict(result,candidate_status='AVAILABLE' if rows else 'NOT_CAPTURED',item=rows[0] if rows else None,
                source=binding,evidence_class=document['evidence_class'],
                source_cutoff_date=day,historical_first_available=None,
                candidate_frozen_at=document.get('frozen_at'),
                clock_status='HISTORICAL_FIRST_AVAILABLE_NOT_VERIFIABLE',
                reason='VERSIONED_IDENTIFIER_CORRECTION_FOR_RESEARCH; A05_FORMAL_ADMISSION_PENDING')
        bindings={k:entry.get(k) for k in ('source_capture','full_state','strict_source')}
        docs={k:read_document(b) for k,b in bindings.items() if b}
        state=docs.get('full_state',{});strict=docs.get('strict_source',{})
        if state and (state.get('T0')!=day or state.get('production') is not False or state.get('source')!=head['owners'][day]['prewatch']):
            raise ValueError('STATE_CANDIDATE_SCOPE_REQUIRED')
        if state:
            if state['membership']!=head['membership_snapshot']:raise ValueError('STATE_MEMBERSHIP_MISMATCH')
            read_owner('prewatch',state['source'])
            for key in ('model','config','implementation'):checked_dependency(root,state[key])
        if strict:
            if (strict['T0']!=day or strict['production'] is not False or strict['candidate_head']!=entry['head']
                    or strict['source_capture']!=bindings['source_capture']):raise ValueError('STRICT_CANDIDATE_SCOPE_REQUIRED')
            from workbench_db.v4_historical_source_ingress_pg_r1 import ingress_path
            for key in ('frozen_scanner_inputs','calendar'):
                ingress_path(root,strict[key]['path'],expected_sha256=strict[key]['sha256'])
            for key in ('model','config','implementation','state_implementation'):checked_dependency(root,strict[key])
            for name,source in strict['input_bindings'].items():
                if source!=head['owners'][day][name]:raise ValueError('STRICT_INPUT_BINDING_MISMATCH')
                read_owner(name,source)
        capture=docs.get('source_capture')
        if capture:
            if capture['T0']!=day or capture['production'] is not False:raise ValueError('CAPTURE_SCOPE_REQUIRED')
            from workbench_db.v4_historical_source_ingress_pg_r1 import ingress_path
            for source in capture['sources']:
                ingress_path(root,source['original_bytes']['path'],
                    expected_sha256=source['original_bytes']['sha256'])
        next_session=entry.get('next_session')
        return dict(result,candidate_status='RESEARCH_CANDIDATE_FROZEN' if state else 'NOT_CAPTURED',
            universe_count=state.get('universe_count'),research_signal_count=state.get('signal_count'),
            research_eligible_count=state.get('research_eligible_count'),
            strict_source_status=strict.get('review_readiness','NOT_CAPTURED'),source_gaps=strict.get('source_gaps',[]),
            formal_admission='NOT_GRANTED',next_real_session=next_session,sources=bindings,
            source_cutoff_date=day,historical_first_available=None,
            source_observed_at=(capture or {}).get('captured_at'),
            candidate_frozen_at=next((r.get('frozen_at_candidate') for r in state.get('signals',[]) if r.get('frozen_at_candidate')),None),
            clock_status='HISTORICAL_FIRST_AVAILABLE_NOT_VERIFIABLE',
            evidence_class=state.get('evidence_class'),reason='Research candidate totals are not formal Cohort observations')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        # Optional capability failures stay local; existing product domains read.
        return dict(result,candidate_status='UNAVAILABLE',reason=str(exc))
