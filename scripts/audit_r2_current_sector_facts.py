"""Independent actual member-set medians and overlap/set arithmetic."""
import collections,gzip,json,math,sqlite3,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.joint_release import checked_path
from workbench_service.domain_views import objects,sector_view
OUT=ROOT/'docs/evidence/r2_available_fields_continuation_20261008'

def records(binding):
    with gzip.open(checked_path(ROOT,binding),'rt',encoding='utf8') as stream:return [json.loads(line) for line in stream]

def main():
    candidate=json.loads((OUT/'CANDIDATE.json').read_bytes());reader=ProductionV4ResearchReader(ROOT,snapshot_authority=candidate['snapshot']);day=reader.context['trade_date']
    membership=records(reader.manifest['sources']['membership']);groups=collections.defaultdict(set)
    for row in membership:
        assert row['target_trade_date']==day and row['membership_asof_date']==day
        groups[row['sector_id']].add(row['security_id'])
    with sqlite3.connect(reader.path.as_uri()+'?mode=ro',uri=True) as db:
        projected=set(db.execute('SELECT sector,security FROM members'))
    expected={(sid,member) for sid,ids in groups.items() for member in ids};assert projected==expected
    authority=reader.manifest['domain_features']['sector'];factors={r['security_id']:r for r in records(authority['factors'])}
    native={r['sector_id']:r for r in records(authority['native'])};items=objects(reader,'sectors');numeric=0;overlap_count=0;comparisons=[]
    for item in items:
        sid=item['entity_id'];members=groups[sid];source=native[sid]
        assert set(source['member_ids'])==members and source['sector_type']==item['fields']['sector_type']['value']
        row=dict(sector_id=sid,member_count=len(members),values={})
        for field,input_field in [('sector_rs5','ret5'),('sector_rs20','ret20'),('participation_proxy','amount_ratio20')]:
            values=[factors[m]['fields'][input_field]['value'] for m in members if m in factors and factors[m]['fields'][input_field]['value'] is not None]
            value=statistics.median(values) if values else None;actual=item['fields'][field]['value']
            assert value is None and actual is None or math.isclose(value,actual,rel_tol=1e-12,abs_tol=1e-12),(sid,field,value,actual)
            row['values'][field]=dict(value=value,known_member_count=len(values),unknown_member_count=len(members)-len(values));numeric+=1
        expected_overlaps=[];shared=set()
        for other,ids in groups.items():
            if other==sid or not other.startswith('THEME:'):continue
            common=members.intersection(ids)
            if common:
                union=members.union(ids);shared.update(common)
                expected_overlaps.append(dict(sector_id=other,intersection_count=len(common),union_count=len(union),jaccard=len(common)/len(union),overlap_share=len(common)/len(members)))
        expected_overlaps.sort(key=lambda x:(-x['jaccard'],x['sector_id']))
        result=sector_view(reader,item,'overlap',dict(limit='200',offset='0'));actual=result['items']
        for offset in range(200,result['total'],200):actual+=sector_view(reader,item,'overlap',dict(limit='200',offset=str(offset)))['items']
        assert result['total']==len(expected_overlaps) and len(actual)==len(expected_overlaps)
        for a,b in zip(actual,expected_overlaps):
            for key,value in b.items():assert a[key]==value
            overlap_count+=1
        assert result['unique_member_count']==len(members-shared)
        assert result['unique_share']==len(members-shared)/len(members)
        row['unique_share']=result['unique_share'];row['overlap_count']=len(actual);comparisons.append(row)
    assert len(comparisons)==378
    write(OUT/'SECTOR_FACT_ORACLE.json',dict(result='PASS',actual_sectors=378,median_comparisons=numeric,overlap_pairs=overlap_count,
        membership_pairs=len(expected),source=reader.manifest['sources']['membership'],factors=authority['factors'],native=authority['native'],
        scope='CURRENT_ACCEPTED_MEMBERSHIP_ONLY_NO_HISTORICAL_PIT_CLAIM',comparisons=comparisons))
    print(json.dumps(dict(result='PASS',medians=numeric,overlap_pairs=overlap_count)))

if __name__=='__main__':main()
