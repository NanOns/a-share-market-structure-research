"""Owner-event-only episode close classification; never infer an exit."""

CONTRACT='FOCUS_EPISODE_OWNER_EVENT_STATE_R1'

def classify_episode(episode,events):
    identity=episode.get('entity_id')
    selected=sorted((event for event in events if event.get('entity_id')==identity and
        event.get('episode_id')==episode.get('episode_id') and
        event.get('event') in ('EXITED','INVALIDATED')),
        key=lambda event:(event.get('trade_date') or event.get('T0') or '',event.get('event') or ''))
    if not selected:
        if episode.get('end_date'):
            return dict(contract_id=CONTRACT,status='UNKNOWN',reason='EPISODE_END_DATE_WITHOUT_EXPLICIT_OWNER_CLOSE_EVENT',
                close_event=None,AS_RECORDED=False,PIT_ELIGIBLE=False)
        return dict(contract_id=CONTRACT,status='ACTIVE',reason='NO_ACCEPTED_EXIT_OR_INVALIDATION_EVENT',
            close_event=None,AS_RECORDED=False,PIT_ELIGIBLE=False)
    event=selected[-1]
    status='INVALIDATED' if event['event']=='INVALIDATED' else 'EXITED'
    return dict(contract_id=CONTRACT,status=status,reason='EXPLICIT_ACCEPTED_OWNER_EVENT',
        close_event=event,AS_RECORDED=False,PIT_ELIGIBLE=False)
