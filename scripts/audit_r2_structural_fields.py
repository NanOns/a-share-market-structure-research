"""Full accepted owner states and independent same-day membership relations."""
import collections,gzip,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.joint_release import checked_path
from workbench_service.stock_views import membership_relations
OUT=ROOT/'docs/evidence/r2_structural_fields_continuation_20261008'

def main():
    reader=ProductionV4ResearchReader(ROOT);day=reader.context['trade_date'];sources=reader.manifest['sources'];state=json.loads(gzip.decompress(checked_path(ROOT,sources['states']).read_bytes()));states={r['entity_id']:r for r in state['rows']}
    def lines(binding):
        with gzip.open(checked_path(ROOT,binding),'rt',encoding='utf8') as f:return [json.loads(x) for x in f]
    advanced={r['security_id']:r for r in lines(sources['advanced'])};groups=collections.defaultdict(list)
    for row in lines(sources['membership']):
        assert row['membership_asof_date']==row['target_trade_date']==day;groups[row['security_id']].append(row)
    counts=collections.Counter();known=collections.Counter();unknown=collections.Counter();samples=[]
    with sqlite3.connect(reader.path) as db:
        stocks=[json.loads(r[0]) for r in db.execute("SELECT payload FROM objects WHERE domain='stocks' ORDER BY id")]
    for item in stocks:
        sid=item['entity_id'];owner=states[sid];assert owner['trade_date']==day
        for key in ('health','maturity','validity','tracking','scenario'):
            cell=item['fields'][key];assert cell['value']==owner[key] and cell['source_digest']==sources['states']['sha256']
            if cell['value'] in ('UNKNOWN',None):unknown[key]+=1
            else:known[key]+=1
            counts['state_value_source']+=1
        related=groups[sid];industries=[r for r in related if r['sector_type']=='INDUSTRY'];concepts=sorted({r['sector_id'] for r in related if r['sector_type']=='THEME'})
        if len(industries)>1 and any('official_classification_priority' not in r or 'taxonomy_depth' not in r for r in industries):primary=None
        else:
            ordered=sorted(industries,key=lambda r:(r.get('official_classification_priority',0),-r.get('taxonomy_depth',0),r['sector_id']));primary=ordered[0]['sector_id'] if ordered else None
        for key,expected in [('primary_industry',primary),('supporting_concepts',concepts)]:
            cell=item['fields'][key];assert cell['value']==advanced[sid]['fields'][key]['value']==expected,(sid,key)
            assert cell['source_digest']==sources['advanced']['sha256'];counts['independent_membership_relation']+=1
        result=membership_relations(reader,item);expected_ids=([primary] if primary else [])+concepts;assert [x['sector_id'] for x in result['items']]==expected_ids
        for x in result['items']:
            assert x['status']=='READY' and x['membership_verified'] and x['display_name'] and x['trade_date']==day;counts['named_relation_identity']+=1
        if item['fields']['health']['value'] not in ('UNKNOWN',None) and len(samples)<5:samples.append(item)
    samples+= [x for x in stocks if x['fields']['health']['value'] in ('UNKNOWN',None)][:5]
    focus=reader.manifest['domain_features']['focus'];latest={ep['entity_id']:ep for ep in sorted(focus['episodes'],key=lambda x:x['T0'])}
    with sqlite3.connect(reader.path) as db:
        rows=[json.loads(r[0]) for r in db.execute("SELECT payload FROM objects WHERE domain='focus'")]
    for item in rows:
        ep=latest[item['entity_id']];obs=ep['observations'][-1]
        for key in ('event','episode_id','health','validity','membership'):
            expected=ep['episode_id'] if key=='episode_id' else obs.get(key)
            assert item['fields'][key]['value']==expected;counts['focus_current_state']+=1
    write(OUT/'SOURCE_ORACLE.json',dict(result='PASS',stock_count=len(stocks),focus_count=len(rows),comparisons=dict(counts),known=dict(known),unknown=dict(unknown),sources={k:sources[k] for k in ('states','advanced','membership','focus_operational')},scope='CORRECTED_ACCEPTED_OWNER_OUTPUT_NOT_INDEPENDENT_MODEL_REIMPLEMENTATION_OR_HISTORICAL_PIT'))
    write(OUT/'BROWSER_INPUTS.json',dict(context_token=reader.token,samples=[dict(id=x['entity_id'],name=x['display_name'],fields={k:x['fields'][k] for k in ('health','maturity','validity','tracking','scenario','primary_industry','supporting_concepts')},relations=membership_relations(reader,x)) for x in samples]))
    print(json.dumps(dict(result='PASS',counts=dict(counts),known=dict(known),unknown=dict(unknown))))
if __name__=='__main__':main()
