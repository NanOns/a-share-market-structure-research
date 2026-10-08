"""Bounded domain projections over a single immutable publication."""
import json
import sqlite3
from collections import Counter,defaultdict

CHANGE_EVENTS={'NEW_PREWATCH','UPGRADED','NEW_CONFIRMED','SCENARIO_UPGRADE','RECONFIRMED','WEAKENED','IMPORTANT_WEAKENED','INVALIDATED'}
RISK_EVENTS={'WEAKENED','IMPORTANT_WEAKENED','INVALIDATED','EXITED'}
ROTATIONS={'ROTATION_PULSE','ROTATION_IN','ROTATION_ACCEPTED','ROTATION_EXPANDING','ROTATION_REACCELERATING','ROTATION_OUT','ROTATION_FAILED'}

def objects(reader,domain):
    with sqlite3.connect(reader.path.as_uri()+'?mode=ro',uri=True) as db:
        return [json.loads(r[0]) for r in db.execute('SELECT payload FROM objects WHERE domain=? ORDER BY id',(domain,))]

def value(row,key):return row.get('fields',{}).get(key,{}).get('value')

def sector_view(reader,item,kind,query):
    sid=item['entity_id'];authority=reader.manifest.get('domain_features',{}).get('sector')
    if kind in ('timeline','rotation-timeline'):
        return reader.envelope(status='SOURCE_INCOMPLETE',items=[item],total=1,has_next=False,earliest_valid_date=reader.context['trade_date'],requested_windows=[5,10,20],historical_membership='NOT_BACKFILLED',reason='FIRST_ACCEPTED_PIT_MEMBERSHIP_NO_PRIOR_DATED_NATIVE_HISTORY',source=authority)
    with sqlite3.connect(reader.path.as_uri()+'?mode=ro',uri=True) as db:
        groups=defaultdict(set)
        for s,e in db.execute('SELECT sector,security FROM members'):groups[s].add(e)
    members=groups[sid];allsectors={r['entity_id']:r for r in objects(reader,'sectors')};overlaps=[];shared=set()
    for other,ids in groups.items():
        if other==sid or not other.startswith('THEME:'):continue
        intersection=members&ids
        if not intersection:continue
        shared.update(intersection);union=members|ids
        overlaps.append(dict(sector_id=other,display_name=allsectors.get(other,{}).get('display_name',other),intersection_count=len(intersection),union_count=len(union),jaccard=len(intersection)/len(union),overlap_share=len(intersection)/len(members),href='/v4/research/sectors/'+other))
    overlaps.sort(key=lambda x:(-x['jaccard'],x['sector_id']));offset=int(query.get('offset',0));limit=int(query.get('limit',30))
    return reader.envelope(status='READY',items=overlaps[offset:offset+limit],total=len(overlaps),offset=offset,limit=limit,has_next=offset+limit<len(overlaps),member_count=len(members),unique_member_count=len(members-shared),unique_share=len(members-shared)/len(members) if members else None,contract_id='FP06_PIT_MEMBERSHIP_JACCARD_V1',as_of=reader.context['trade_date'],source=reader.manifest['sources']['membership'],cluster=None,cluster_reason='NO_VERSIONED_CLUSTER_ENGINE_OUTPUT')

def home(reader):
    events=objects(reader,'events');changes=[r for r in events if value(r,'effective_event') in CHANGE_EVENTS]
    sectors=objects(reader,'sectors');rotations=[r for r in sectors if value(r,'output_state') in ROTATIONS and not r['entity_id'].startswith('STYLE:')]
    # A sector is a change only when an owner supplies a real stage or rotation delta.
    sector_changes=[r for r in sectors if not r['entity_id'].startswith('STYLE:') and (value(r,'output_state') in ROTATIONS or value(r,'effective_event') in CHANGE_EVENTS)]
    members=defaultdict(set)
    with sqlite3.connect(reader.path.as_uri()+'?mode=ro',uri=True) as db:
        for s,e in db.execute('SELECT sector,security FROM members'):members[s].add(e)
    covered=set();cards=[]
    for row in sector_changes:
        related=[r for r in changes if r['entity_id'] in members[row['entity_id']]]
        fresh=[r for r in related if r['entity_id'] not in covered];covered.update(r['entity_id'] for r in related)
        cards.append(dict(item=row,member_previews=related[:5],change_counts=dict(Counter(value(r,'effective_event') for r in related)),net_information_count=len(fresh),member_total=len(members[row['entity_id']])))
    independent=[r for r in changes if r['entity_id'] not in covered]
    return reader.envelope(status='READY',counts=reader.manifest['counts'],gaps=reader.manifest['gaps'],market=reader.manifest.get('domain_features',{}).get('market'),
        changes=independent[:30],change_total=len(independent),persistent_count=sum(value(r,'effective_event')=='PERSISTENT' for r in events),
        sector_changes=cards[:15],sector_change_total=len(cards),rotations=rotations[:15],rotation_total=len(rotations),risks=[r for r in changes if value(r,'effective_event') in RISK_EVENTS][:30],
        net_information_count=len({r['entity_id'] for r in changes}),comparison=dict(trade_date=reader.context['trade_date'],mode='OWNER_EMITTED_STATE_EVENT_DELTA',source=reader.manifest['sources']['events'],sector_reason='CURRENT_OWNER_ROTATION_UNKNOWN_NO_PRIOR_ACCEPTED_MEMBERSHIP' if not rotations else None),
        radar=objects(reader,'radar')[:15])
