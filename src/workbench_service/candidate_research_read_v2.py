"""Optional, head-bound candidate display. No formal fields or counts change."""
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo
from workbench_analysis.r43_owner_replay import checked
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
    """Return the accepted close-time contract identity without guessing a cutoff."""
    path=Path(root)/'config/v4_dm01_bridge_calendar_v1.json'
    raw=path.read_bytes();document=json.loads(raw)
    runtime=document.get('runtime',{})
    if document.get('contract_id')!='V4_DM01_OFFICIAL_CALENDAR_BRIDGE_V1' or runtime.get('timezone')!='Asia/Shanghai' or not runtime.get('market_close_local'):
        raise ValueError('SESSION_CUTOFF_CONTRACT_INVALID')
    return runtime['market_close_local'],dict(path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),
        contract_id=document['contract_id'],timezone=runtime['timezone'])


def checked_dependency(root,binding):
    """Verify original computation bytes after a source-code revision.

    Only model/config dependencies can use this content-addressed archive.
    Owner/source data and the accepted release chain never fall back here.
    """
    relative=Path(binding['path'])
    if relative.is_absolute() or '..' in relative.parts or not relative.parts or relative.parts[0] not in ('src','config'):
        return checked(root,binding)
    try:
        return checked(root,binding)
    except (ValueError,OSError):
        sha=binding['sha256']
        if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):
            raise ValueError('FROZEN_DEPENDENCY_SHA_REQUIRED')
        archive='docs/evidence/producer_dependency_archive_v1/'+sha+'.bin'
        try:
            return checked(root,dict(binding,path=archive))
        except (ValueError,OSError) as exc:
            raise ValueError('HISTORICAL_COMPUTATION_BYTES_NOT_CAPTURED') from exc


def accepted_candidate_head(root, current, token, binding, day):
    """Resolve only a hash-linked predecessor of the authenticated active reader.

    An archive's existence is not acceptance. Its bytes must also be linked by
    the current accepted release, whose token and fixed pointer still agree.
    """
    pointer=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    if digest(current)!=token or not pointer.is_file() or json.loads(pointer.read_bytes())!=current:
        raise ValueError('OLD_TOKEN')
    cutoff=current.get('accepted_trade_date')
    if not cutoff or day>cutoff:raise ValueError('FUTURE_DATE')
    if current.get('exact_daily_adjustment_contract'):
        from workbench_db.v4_membership_reference_pg_v1 import research_authority
        research=research_authority(root,current,day)
        if research['input_candidate']!=binding:raise ValueError('NATIVE_RESEARCH_INPUT_HEAD_MISMATCH')
        # Input-owner conservation never accepts the pending producer Head.
        return json.loads(checked(root,binding).read_bytes())
    candidate=current;seen=set()
    for _ in range(4096):
        identity=digest(candidate)
        if identity in seen:raise ValueError('UNACCEPTED_HEAD')
        seen.add(identity)
        if identity==binding['sha256']:
            if json.loads(checked(root,binding).read_bytes())!=candidate:
                raise ValueError('MUTATED_ARCHIVE')
            if day not in candidate.get('published_sessions',candidate.get('dates',[])) or day not in candidate.get('owners',{}):
                raise ValueError('WRONG_SESSION')
            return candidate
        predecessor=candidate.get('predecessor')
        if not predecessor:break
        # CAS preserves each predecessor at this fixed content-addressed path.
        archive=root/'data/v4/predecessors'/(predecessor['sha256']+'.json')
        try:
            raw=checked(root,predecessor).read_bytes()
            archived=checked(root,dict(path=archive.relative_to(root).as_posix(),sha256=predecessor['sha256'])).read_bytes()
            if raw!=archived:raise ValueError('MUTATED_ARCHIVE')
            candidate=json.loads(archived)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            raise ValueError('MUTATED_ARCHIVE') from exc
    raise ValueError('UNACCEPTED_HEAD')


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
        pointer=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
        if digest(head)!=token or not pointer.is_file() or json.loads(pointer.read_bytes())!=head:
            raise ValueError('OLD_TOKEN')
        if not head.get('accepted_trade_date') or day>head['accepted_trade_date']:
            raise ValueError('FUTURE_DATE')
        index_path=root/'data/v4/producer_candidate_index_v2.json'
        if not index_path.exists():return dict(result,reason='CANDIDATE_INDEX_NOT_CREATED')
        index=json.loads(index_path.read_bytes());entry=index.get('sessions',{}).get(day)
        if not entry:return dict(result,reason='HISTORICAL_CANDIDATE_SOURCE_NOT_CAPTURED')
        if index.get('contract_id')!='PRODUCER_CANDIDATE_INDEX_V2' or entry.get('production') is not False:
            raise ValueError('CANDIDATE_INDEX_SCOPE_REQUIRED')
        current=head;head=accepted_candidate_head(root,head,token,entry['head'],day)
        def read_document(binding):
            if current.get('exact_daily_adjustment_contract'):
                from workbench_db.v4_membership_reference_pg_v1 import read_research
                return read_research(root,current,day,binding)
            return json.loads(checked(root,binding).read_bytes())
        if sector_id is not None:
            binding=entry['sector'];document=read_document(binding)
            if document['T0']!=day or document['production'] is not False:raise ValueError('RESEARCH_SCOPE_REQUIRED')
            if set(document['sources'])!={'lifecycle','core','sector','prewatch'}:
                raise ValueError('COMPLETE_CANDIDATE_SOURCE_BINDINGS_REQUIRED')
            for name,source in document['sources'].items():
                if source!=head['owners'][day][name]:raise ValueError('CANDIDATE_OWNER_MISMATCH')
                checked(root,source)
            if document['membership']!=head['membership_snapshot']:raise ValueError('CANDIDATE_MEMBERSHIP_MISMATCH')
            checked(root,document['membership'])
            for dep in document['dependencies']+[document['model']]:checked_dependency(root,dep)
            rows=[r for r in document['rows'] if r['sector_id']==sector_id]
            if len(rows)>1:raise ValueError('DUPLICATE_SECTOR_CANDIDATE')
            for row in rows:
                if row['T0']!=day or row['production'] is not False or row['formal_consumer_enabled'] is not False:
                    raise ValueError('RESEARCH_ROW_SCOPE_REQUIRED')
                for cell in row['inputs'].values():
                    if cell.get('source'):
                        receipt=json.loads(checked(root,cell['source']).read_bytes())
                        if receipt['T0']!=day or receipt['sector_id']!=sector_id:raise ValueError('RANK_SOURCE_SCOPE_REQUIRED')
                        for source in receipt['sources']:checked(root,source)
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
            for key in ('source','membership'):checked(root,state[key])
            for key in ('model','config','implementation'):checked_dependency(root,state[key])
        if strict:
            if (strict['T0']!=day or strict['production'] is not False or strict['candidate_head']!=entry['head']
                    or strict['source_capture']!=bindings['source_capture']):raise ValueError('STRICT_CANDIDATE_SCOPE_REQUIRED')
            for key in ('frozen_scanner_inputs','calendar'):checked(root,strict[key])
            for key in ('model','config','implementation','state_implementation'):checked_dependency(root,strict[key])
            for name,source in strict['input_bindings'].items():
                if source!=head['owners'][day][name]:raise ValueError('STRICT_INPUT_BINDING_MISMATCH')
                checked(root,source)
        capture=docs.get('source_capture')
        if capture:
            if capture['T0']!=day or capture['production'] is not False:raise ValueError('CAPTURE_SCOPE_REQUIRED')
            for source in capture['sources']:checked(root,source['original_bytes'])
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
