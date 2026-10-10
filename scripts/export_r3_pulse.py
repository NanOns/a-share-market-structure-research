"""Export actual pulse source endpoints in the producer's target coordinate."""
from immediate_r3_common import *
def main():
    p=load(OUT/'02_P0_ALG/P0_ALG_ORACLE_INPUT.json');head=load('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json');records=[]
    for date in head['published_sessions']:
        pulse=[r for r in p['rotations'] if r['trade_date']==date and (r['rotation'].get('episode') or {}).get('pulse_date')==date]
        if not pulse:continue
        o=head['owners'][date];previous=p['calendar'][p['calendar'].index(date)-1]
        snapshot=load(head['membership_snapshot']);source_members=load(snapshot['memberships']);prior={}
        for m in source_members:
            if m.get('security_id'):prior.setdefault(m['sector_id'],set()).add(m['security_id'])
        ids={m for r in pulse for m in r['rotation']['episode']['frozen_basket']};hr=load(o['diagnostic'])['owner']['history'];bars={}
        with gzip.open(checked(hr),'rt',encoding='utf8') as f:
            for line in f:
                r=json.loads(line)
                if r['security_id'] in ids:bars[r['security_id']]=[b for b in r['bars'] if b['trade_date'] in (previous,date)]
        for r in pulse:records.append(dict(sector_id=r['sector_id'],trade_date=date,previous=previous,actual_episode=r['rotation']['episode'],source_previous_member_ids=sorted(prior[r['sector_id']]),member_bars={m:bars.get(m,[]) for m in r['rotation']['episode']['frozen_basket']},sources=[snapshot['memberships'],hr,o['rotation']],membership_scope='TDX_LATEST_MEMBER_RETRO_V1, not historical AS_RECORDED',initial_prior='FINITE_OPERATIONAL_WINDOW_RESET when no prior; not historical episode absence'))
    write(OUT/'09_CONTINUATION/PULSE_SOURCE_ORACLE_INPUT.json',dict(contract='R3_FIRST_PULSE_BASELINE_SOURCE_V1',records=records))
    print(json.dumps(dict(actual_pulse_rows=len(records))))
if __name__=='__main__':main()
