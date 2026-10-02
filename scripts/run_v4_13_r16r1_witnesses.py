"""Actual runtime observations only. Independent validator generates expected values."""
import sys,json,tempfile,gzip
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from workbench_analysis.v4_13_io import FrozenContracts,atomic,canonical,file_ref,envelope,exact,revision_ordinal
from workbench_analysis.v4_13_input_binder import AcceptedInputBinder
from workbench_analysis.v4_13_loo_runtime import LOOContextRuntime,select_sector
from workbench_analysis.v4_13_profile_runtime import copy_structure,dual_enrichment,fold_quality,sector_snapshot
from workbench_analysis.v4_13_publication import publish,publish_stream
from test_v4_13_r16a_runtime import fixture_binder
from test_v4_13_r16r1_repair import source_row

def run():
    c=FrozenContracts(ROOT);engine=LOOContextRuntime(c);out={}
    cases=[]
    for label,count,missing in [('complete',6,()),('minimum',2,()),('incomplete',6,('a','b','c'))]:
        b=fixture_binder(c,count,missing)
        cases.append(dict(label=label,input=dict(memberships=b.memberships,current=b.current,stock=b.stock,seed=b.seed),actual=engine.compute(b,'target','r1')))
    out['context_cases']=cases
    candidates=[dict(sector_id=s,quality='READY',confirmed_raw=confirmed,warm_raw=warm,emergence=emergence,adjusted_seed_width=width) for s,confirmed,warm,emergence,width in [('Z',True,True,'HIGH',.9),('A',True,True,'HIGH',.9),('B',True,True,'MEDIUM',1),('C',True,False,'HIGH',1),('D',False,True,'HIGH',1),('E',True,True,'HIGH',.8)]]
    out['selector_cases']=[]
    for i in range(len(candidates)):
        items=candidates[i:];out['selector_cases'].append(dict(input=items,actual=select_sector(items)))
        out['selector_cases'].append(dict(input=list(reversed(items)),actual=select_sector(list(reversed(items)))))
    out['quality_cases']=[]
    qualities=['KNOWN','UNKNOWN','NOT_IMPLEMENTED','NOT_APPLICABLE','DEGRADED']
    for a in qualities:
        for b in qualities:out['quality_cases'].append(dict(input=[a,b],actual=fold_quality([a,b],c.config['quality_map']['component_pair_table'])))
    out['dual_cases']=[]
    for rq,sq in [('KNOWN','UNKNOWN'),('UNKNOWN','KNOWN'),('KNOWN','KNOWN')]:
        rotation=envelope('STABLE',rq,'ROTATION_REASON',[{'owner':'V4_08'}]);structure=envelope({'support':'HELD'},sq,'STRUCTURE_REASON',[{'owner':'V4_12'}])
        out['dual_cases'].append(dict(rotation=rotation,structure=structure,actual=dual_enrichment(rotation,structure,c)))
    out['structure_cases']=[]
    ref=dict(path='SYNTHETIC_NOT_ACCEPTED',sha256='fixture',bytes=0,producer_contract_id=c.config['projection']['source_publication_contract'],trade_date='2026-09-30',available_at='2026-10-02T06:00:00+00:00',source_revision='r1')
    rows=[('base',source_row())]
    for machine in ['support','acceptance','pullback','recovery']:
        for key,value in [('quality','UNKNOWN'),('reason',['CHANGED_MACHINE_REASON'])]:
            row=source_row();row['anchor_states'][0]['state_observations'][machine][key]=value;rows.append((machine+'_'+key,row))
    row=source_row();row['active_selection']['reason']='CHANGED_SELECTOR';row['active_projection']['reason']='CHANGED_SELECTOR';rows.append(('selector_only',row))
    row=source_row();row['anchor_states'][0]['output_envelope']['anchor_view_asof_t']['quality']='KNOWN';rows.append(('view_known',row))
    row=source_row();row['anchor_states'][0]['output_envelope']['structure_health'].update(producer_identity={'owner':'PUBLISHED_HEALTH'},source_identity=[{'owner':'PUBLISHED_HEALTH_REF'}]);rows.append(('published_identity',row))
    for label,row in rows:out['structure_cases'].append(dict(label=label,input=row,source_ref=ref,actual=copy_structure(row,c,ref)))
    # Every authorized owner publication, including selected machine UNKNOWN cases.
    out['authorized_structure_cases']=[]
    head=c.owners['V4_12']
    from workbench_analysis.v4_13_io import rows as records
    for manifest_ref in head['publication_authority']['authorized_manifests']:
        if '/synthetic/' not in manifest_ref['path']:continue
        manifest=json.loads(exact(ROOT,manifest_ref));artifact=next(r for r in manifest['artifacts'] if 'runtime_security' in r['path'])
        r=next(records(ROOT,artifact));out['authorized_structure_cases'].append(dict(manifest_ref=manifest_ref,artifact_ref=artifact,input=r,actual=copy_structure(r,c,artifact)))
    b=AcceptedInputBinder(c,'2026-09-30','2026-10-03T00:00:00+08:00')
    out['provenance_cases']=b.component_sources('S',{'value':'I'},'WITNESS_LOO')
    out['revision_ordinals']={r:revision_ordinal(r) for r in ['r9','r10','r11']}
    out['negative_cases']=[]
    def probe(label,call):
        try:call()
        except ValueError as error:out['negative_cases'].append(dict(label=label,rejected=True,reason=str(error)))
        else:out['negative_cases'].append(dict(label=label,rejected=False))
    probe('producer_mismatch',lambda:copy_structure(source_row(),c,dict(ref,producer_contract_id='WRONG')))
    with tempfile.TemporaryDirectory(prefix='v4-13-r16r1-') as td:
        root=Path(td);r=atomic(root,'one',b'one');atomic(root,'two',b'two')
        probe('hash_mismatch',lambda:exact(root,dict(r,sha256='0'*64)))
        probe('path_mismatch',lambda:exact(root,dict(r,path='two')))
        probe('write_escape',lambda:atomic(root,'../escape',b'escape'))
        for revision in ['r0','r01','rX','r1/../r2']:probe('revision_'+revision,lambda:revision_ordinal(revision))
        meta=dict(source_refs=[],diagnostics={},prior_session_ref={'trade_date':'2026-09-29'})
        for method in [publish,publish_stream]:
            for ns,date,rev in [('bad/../escape','2026-09-30','r1'),('good','../../escape','r1'),('good','2026-02-30','r1'),('good','2026-9-30','r1'),('good','2026-09-30','r01')]:
                probe(method.__name__+'_boundary_'+ns+'_'+date+'_'+rev,lambda:method(root,ns,date,rev,[],[],meta) if method==publish else method(root,ns,date,rev,[],meta))
            row=dict(security_id='S',trade_date='2026-09-30',revision='r1',value=1)
            def emit(value):
                obj=dict(row,value=value)
                return method(root,method.__name__,'2026-09-30','r1',[obj],[],meta) if method==publish else method(root,method.__name__,'2026-09-30','r1',[(obj,[])],meta)
            published=emit(1);before={p.relative_to(root).as_posix():file_ref(root,p.relative_to(root).as_posix()) for p in (root/Path(published['path']).parent).iterdir()}
            same=emit(1);probe(method.__name__+'_append_only_conflict',lambda:emit(2))
            after={p.relative_to(root).as_posix():file_ref(root,p.relative_to(root).as_posix()) for p in (root/Path(published['path']).parent).iterdir()}
            out[method.__name__+'_append_only']=dict(before=before,after=after,initial=published,idempotent=same,manifest=json.loads(exact(root,published)))
    return atomic(ROOT,'reports/v4_13_runtime_r16r1/runtime_witnesses.json',canonical(out))

if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
