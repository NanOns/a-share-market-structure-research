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
