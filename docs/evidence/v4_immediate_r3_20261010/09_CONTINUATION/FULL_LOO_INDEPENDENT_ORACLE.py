"""Whole published current LOO: stdlib, no business imports."""
from pathlib import Path
import json,gzip,bisect,math,sys
def main():
    here=Path(__file__).parent
    with gzip.open(sys.argv[1] if len(sys.argv)>1 else here/'FULL_LOO_ORACLE_INPUT.json.gz','rt',encoding='utf8') as f:p=json.load(f)
    sorted_vectors={(sector,k):sorted((p['stocks'][m][k],m) for m in members if p['stocks'].get(m,{}).get(k) is not None) for sector,members in p['sectors'].items() for k in ('ret1','ret5')};checks=0;errors=[];unknown=0
    def check(sid,sector,field,e,a):
        nonlocal checks
        checks+=1;ok=e==a if e is None or a is None or isinstance(e,str) else math.isclose(e,a,rel_tol=1e-12,abs_tol=1e-12)
        if not ok:errors.append(dict(security_id=sid,sector_id=sector,field=field,expected=e,actual=a))
    for row in p['actual']:
        sid=row['security_id'];s=p['stocks'][sid]
        for m in row['memberships']:
            sector=m['sector_id'];members=p['sectors'][sector];count=len(members)-(sid in members);known={};med={}
            for k in ('ret1','ret5'):
                v=sorted_vectors[sector,k];pair=(s[k],sid) if s[k] is not None and sid in members else None
                index=bisect.bisect_left(v,pair) if pair else None;n=len(v)-(pair is not None);known[k]=n
                def at(i):return v[i+(index is not None and i>=index)][0]
                med[k]=None if not n else at(n//2) if n%2 else (at(n//2-1)+at(n//2))/2
            eligible=count>=p['min_members'] and count>0 and known['ret1']/count>=p['min_coverage']
            values=dict(rps5=s['rps5'],rps20=s['rps20'],rps20_delta3=s['rps20_delta3'],rel_market_1=s['ret1']-med['ret1'] if s['ret1'] is not None and med['ret1'] is not None else None,rel_market_5=s['ret5']-med['ret5'] if s['ret5'] is not None and med['ret5'] is not None else None)
            check(sid,sector,'non_target_member_count',count,m['non_target_member_count'])
            a=m.get('relative_substitutions')
            if eligible:
                for k,v in values.items():check(sid,sector,k,v,a[k])
            else:check(sid,sector,'no_substitution_for_ineligible',None,a)
            if not eligible or None in values.values() or 'UNKNOWN' in (s['compression_state'],s['ma_structure_state']):state=None;quality='UNKNOWN';unknown+=1
            else:
                rps,delta,rel=values['rps20'],values['rps20_delta3'],values['rel_market_1'];q=p['parameters'];active=delta>=q['RELATIVE_ACTIVE_DELTA'] and (s['compression_state'] in ('COMPRESSING','COMPRESSING_STRONG') or s['ma_structure_state'] in ('BULL_TRANSITION','BULL_ALIGNED'))
                state='ACTIVE_EMERGENCE' if active else 'PASSIVE_RESILIENCE' if rel>0 and delta<=0 else 'LEADING_ACCELERATING' if rps>=q['RELATIVE_LEADING_RPS'] and delta>0 else 'LEADING_STABLE' if rps>=q['RELATIVE_LEADING_RPS'] and delta>=-q['RELATIVE_IMPROVING_DELTA'] else 'IMPROVING' if delta>q['RELATIVE_IMPROVING_DELTA'] else 'WEAKENING' if delta< -q['RELATIVE_IMPROVING_DELTA'] else 'LAGGING' if rps<q['RELATIVE_LAGGING_RPS'] else 'NEUTRAL';quality='KNOWN'
            check(sid,sector,'state',state,m['value']);check(sid,sector,'quality',quality,m['quality'])
    out=dict(contract=p['contract'],trade_date=p['trade_date'],pairs=sum(len(r['memberships']) for r in p['actual']),checks=checks,errors=len(errors),differences=errors,unknown_contexts=unknown,scope=p['scope'],acceptance='PASS_FULL_CURRENT_OPERATIONAL_LOO_SCOPE' if not errors else 'FAIL')
    dest=Path(sys.argv[2] if len(sys.argv)>2 else here/'FULL_LOO_ORACLE_RESULT.json');tmp=dest.with_suffix('.tmp');tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(dest);print(json.dumps({k:out[k] for k in ('pairs','checks','errors','unknown_contexts')}));return bool(errors)
if __name__=='__main__':sys.exit(main())
