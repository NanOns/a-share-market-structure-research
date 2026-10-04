"""STATE_EVENT_V1: pure events after exact D2 and frozen prior-session state."""
from datetime import datetime
from .confirmation import digest,package,ConfirmationError
from .state_provenance import validate_output
EVENTS=('FIRST_OBSERVED','CONFIRMATION_INVALIDATED','RECONFIRMED','NEW_CONFIRMED','SCENARIO_UPGRADED','CONFIRMATION_WEAKENED','PERSISTENT_CONFIRMED','SCENARIO_CHANGED','NONE')
def freeze_prior_session(*,target_date,prior_date,calendar_publication_id,rows,source_binding,scope,calendar_manifest,episode_history=None):
    if prior_date>=target_date:raise ConfirmationError('SAME_DAY_REVISION_PARENT_FORBIDDEN')
    if scope!='SYNTHETIC_ENGINEERING_ONLY':raise ConfirmationError('REAL_PRIOR_HEAD_NOT_AUTHORIZED_FOR_CANDIDATE')
    sessions=calendar_manifest['sessions'];dates=[s['trade_date'] for s in sessions]
    if target_date not in dates or dates.index(target_date)==0 or dates[dates.index(target_date)-1]!=prior_date:raise ConfirmationError('EXACT_PREVIOUS_CALENDAR_SESSION_REQUIRED')
    if calendar_publication_id!='SYNTHETIC_CALENDAR:'+digest(calendar_manifest):raise ConfirmationError('PRIOR_CALENDAR_BINDING_INVALID')
    from .confirmation_d2_bridge import verify_d2_publication
    if rows!=verify_d2_publication(source_binding):raise ConfirmationError('CONTROLLED_PRIOR_D2_REQUIRED')
    history=episode_history or []
    for publication in history:
        for historical in verify_d2_publication(publication):
            if historical['trade_date']>prior_date or historical['calendar_publication_id']!=calendar_publication_id:raise ConfirmationError('FUTURE_EPISODE_HISTORY_REJECTED')
    for row in rows:
        validate_output(row)
        if row['trade_date']!=prior_date or row['calendar_publication_id']!=calendar_publication_id:raise ConfirmationError('PRIOR_SESSION_IDENTITY_MISMATCH')
    if len({r['entity_id'] for r in rows})!=len(rows):raise ConfirmationError('DUPLICATE_PRIOR_STATE')
    snapshot=dict(contract_id='V4_11_FROZEN_PRIOR_SESSION_STATE_HEAD_V1',target_trade_date=target_date,prior_trade_date=prior_date,
        calendar_publication_id=calendar_publication_id,rows=rows,source_binding=source_binding,scope=scope,calendar_manifest=calendar_manifest,episode_history=history)
    snapshot['head_digest']=digest(snapshot);return snapshot
def state_events(d2_publication,prior_session_head,*,revision_of=None):
    from .confirmation_d2_bridge import verify_d2_publication
    final_states=verify_d2_publication(d2_publication);d2_publication_id=d2_publication['publication_id']
    c,m,p,a,scanner=package();frozen=dict(prior_session_head);expected=frozen.pop('head_digest',None)
    if digest(frozen)!=expected:raise ConfirmationError('FROZEN_PRIOR_HEAD_CHANGED')
    rebuilt=freeze_prior_session(target_date=frozen['target_trade_date'],prior_date=frozen['prior_trade_date'],calendar_publication_id=frozen['calendar_publication_id'],
        rows=frozen['rows'],source_binding=frozen['source_binding'],scope=frozen['scope'],calendar_manifest=frozen['calendar_manifest'],episode_history=frozen['episode_history'])
    if rebuilt!=prior_session_head:raise ConfirmationError('FROZEN_PRIOR_HEAD_CONTRACT_MISMATCH')
    if frozen['rows']!=verify_d2_publication(frozen['source_binding']):raise ConfirmationError('FROZEN_PRIOR_D2_READBACK_MISMATCH')
    confirmed_history=[]
    for publication in frozen['episode_history']:
        for historical in verify_d2_publication(publication):
            if historical['trade_date']>frozen['prior_trade_date'] or historical['calendar_publication_id']!=frozen['calendar_publication_id']:raise ConfirmationError('FUTURE_EPISODE_HISTORY_REJECTED')
            if historical['maturity']=='CONFIRMED' and historical['final_eligibility']=='TRUE':confirmed_history.append(historical)
    dates=[s['trade_date'] for s in frozen['calendar_manifest']['sessions']]
    if frozen['target_trade_date'] not in dates or dates.index(frozen['target_trade_date'])==0 or dates[dates.index(frozen['target_trade_date'])-1]!=frozen['prior_trade_date']:raise ConfirmationError('EXACT_PREVIOUS_CALENDAR_SESSION_REQUIRED')
    prior_date=frozen['prior_trade_date'];target=frozen['target_trade_date']
    if prior_date>=target or revision_of==frozen['source_binding'].get('publication_id'):raise ConfirmationError('SAME_DAY_REVISION_PARENT_FORBIDDEN')
    old={r['entity_id']:r for r in frozen['rows']};priority={s:i for i,s in enumerate(a['scenario_priority'])};output=[]
    for inputs in d2_publication['inputs']:
        if inputs.get('prior_state')!=old.get(inputs['entity_id']):raise ConfirmationError('D2_PARENT_DIFFERS_FROM_FROZEN_PRIOR_SESSION')
    for current in final_states:
        validate_output(current)
        if current['trade_date']!=target or current['calendar_publication_id']!=frozen['calendar_publication_id']:raise ConfirmationError('D2_PUBLICATION_SESSION_MISMATCH')
        prior=old.get(current['entity_id']);active=current['maturity']=='CONFIRMED' and current['final_eligibility']=='TRUE' and current['validity']=='VALID'
        was=bool(prior and prior['maturity']=='CONFIRMED' and prior['final_eligibility']=='TRUE' and prior['validity']=='VALID')
        related=bool(prior and (current['episode_id']==prior['episode_id'] or current.get('parent_episode_id')==prior['episode_id']))
        invalid=bool(prior and related and current['validity']=='INVALIDATED' and 'HARD_INVALIDATION' in current['transition_reasons'])
        ever_confirmed=bool(prior and (prior['maturity']=='CONFIRMED' or any(h['entity_id']==current['entity_id'] and h['episode_id'] in (current['episode_id'],current.get('parent_episode_id')) for h in confirmed_history)))
        reconfirmed=bool(prior and related and active and not was and ever_confirmed)
        upgraded=bool(active and was and current['scenario'] in priority and prior['scenario'] in priority and priority[current['scenario']]<priority[prior['scenario']])
        weakened=bool(prior and was and (not active or current['health'] in ('WEAKENING','DAMAGED','EXHAUSTED')))
        changed=bool(prior and active and was and current['scenario']!=prior['scenario'] and not upgraded)
        flags=dict(FIRST_OBSERVED=prior is None,CONFIRMATION_INVALIDATED=invalid,RECONFIRMED=reconfirmed,
            NEW_CONFIRMED=bool(prior and active and not was and not reconfirmed),SCENARIO_UPGRADED=upgraded,
            CONFIRMATION_WEAKENED=weakened,PERSISTENT_CONFIRMED=bool(prior and active and was and not upgraded and not changed and not weakened),
            SCENARIO_CHANGED=changed)
        matched=[e for e in EVENTS[:-1] if flags[e]] or ['NONE']
        output.append(dict(contract_id='STATE_EVENT_V1',entity_id=current['entity_id'],entity_type=current['entity_type'],trade_date=target,
            state_publication_id=current['publication_id'],d2_publication_id=d2_publication_id,prior_session_state_head_digest=expected,
            prior_session_state_publication_id=prior['publication_id'] if prior else None,event_types=matched,primary_event=matched[0],
            primary_scenario=current['scenario'],event_predicates=flags,revision_of=revision_of,
            episode_id=current['episode_id'],parent_episode_id=current['parent_episode_id'],counterevidence=current['unknown_predicates'],
            episode_history_publication_ids=[p['publication_id'] for p in frozen['episode_history']],
            D0_writes_final_state=False,permissions=dict(production=False,shadow=False,focus=False)))
    if len({r['entity_id'] for r in output})!=len(output):raise ConfirmationError('DUPLICATE_STATE_EVENT_ENTITY')
    return output
