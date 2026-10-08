"""Versioned V4 membership adapter; legacy V3 families and ledgers stay intact."""
from workbench_service.current_v4_context import canonical,digest

CONTRACT='FP08_V4_FOCUS_LIFECYCLE_V1'
def membership(row):
    q=row['raw_qualification']
    if q.get('CONFIRMED')=='TRUE':return 'CURRENT'
    if q.get('PREWATCH')=='TRUE':return 'EARLY'
    return 'NONE' if q.get('CONFIRMED')==q.get('PREWATCH')=='FALSE' else 'UNKNOWN'

def project(days):
    episodes={};latest={};events=[]
    for day,rows in sorted(days.items()):
        if any(r['trade_date']!=day for r in rows):raise ValueError('FOCUS_DATE_MIX')
        if len({r['entity_id'] for r in rows})!=len(rows):raise ValueError('FOCUS_DUPLICATE_ENTITY')
        for row in rows:
            sid=row['entity_id'];member=membership(row);prior=latest.get(sid);active=prior and prior['end_date'] is None
            if not active and member not in ('EARLY','CURRENT'):continue
            if not active:
                eid=digest(canonical([CONTRACT,sid,day]));ep=dict(episode_id=eid,entity_id=sid,T0=day,start_date=day,end_date=None,parent_episode_id=prior['episode_id'] if prior else None,anchors=[dict(kind='FIRST_FOCUS',trade_date=day,anchor_id=digest(canonical([eid,'FIRST_FOCUS',day])))],observations=[],membership=member)
                episodes[eid]=ep;latest[sid]=ep;event='REENTERED' if prior else 'NEW'
            else:
                ep=prior
                event='DATA_UNAVAILABLE' if member=='UNKNOWN' else 'EXITED' if member=='NONE' else 'UPGRADED' if ep['membership']=='EARLY' and member=='CURRENT' else 'WEAKENED' if ep['membership']=='CURRENT' and member=='EARLY' else 'PERSISTENT'
                if row.get('validity')=='INVALID':event='INVALIDATED'
                if member=='NONE' or event=='INVALIDATED':ep['end_date']=day
                if member!='UNKNOWN':ep['membership']=member
            obs=dict(trade_date=day,event=event,membership=member,health=row.get('health'),validity=row.get('validity'),scenario=row.get('scenario'),waiting_for=row.get('unknown_predicates',[]),source_publication=row['publication_id'],path_state=None,path_reason='V4_PATH_PREDICATE_ADAPTER_NOT_ADMITTED',outcome_status='PENDING',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
            ep['observations'].append(obs)
            if event in ('UPGRADED','EXITED','INVALIDATED'):ep['anchors'].append(dict(kind={'UPGRADED':'CURRENT_UPGRADE','EXITED':'EXIT_EFFECTIVE','INVALIDATED':'INVALIDATION'}[event],trade_date=day,anchor_id=digest(canonical([ep['episode_id'],event,day]))))
            events.append(dict(**obs,entity_id=sid,episode_id=ep['episode_id'],idempotency_key=digest(canonical([CONTRACT,sid,day,event])),contract_id=CONTRACT,source_permission='FP08_ENGINEERING_SUCCESSOR_ONLY'))
    return dict(episodes=list(episodes.values()),events=events)
