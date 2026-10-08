"""Existing-source presentation oracle and immutable UI successor."""
import collections,copy,json,shutil,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.fp01_evidence import write,ref
from workbench_service.joint_release import AUTHORITY,validate
from workbench_service.current_v4_context import canonical,digest
from workbench_service.production_v4 import ProductionV4ResearchReader
from workbench_service.stock_views import explanation
OUT=ROOT/'docs/evidence/r2_presentation_continuation_20261008'

def prepare():
    name='ACCEPTED_CANDIDATE.json' if '--accepted' in sys.argv else 'FINAL_CANDIDATE.json' if '--final' in sys.argv else 'QA_CANDIDATE.json' if '--qa' in sys.argv else 'READY_CANDIDATE.json' if '--ready' in sys.argv else 'CANDIDATE.json'
    if (OUT/name).exists():raise RuntimeError('PRESENTATION_CANDIDATE_ALREADY_FROZEN')
    before=(ROOT/AUTHORITY).read_bytes();candidate=json.loads(before);reader=ProductionV4ResearchReader(ROOT)
    count=0;reasons=collections.Counter();missing=collections.Counter()
    with sqlite3.connect(reader.path.as_uri()+'?mode=ro',uri=True) as db:
        for payload, in db.execute('SELECT payload FROM objects WHERE domain=?',('stocks',)):
            row=json.loads(payload);result=explanation(reader,row)
            for field,fallback in [('why_now','transition_reasons'),('waiting_for','unknown_predicates'),('invalid_if',None),('hypothesis',None)]:
                source=field if field in row['fields'] else fallback
                cell=row['fields'].get(source) if source else None
                projection=result['owner_explanations'][field]
                assert projection['source']==cell
                assert projection['value']==(cell.get('value') if cell else None)
                if not cell:missing[field]+=1
                if field=='why_now':reasons.update(projection['value'] or [])
                count+=1
    focus=reader.manifest['domain_features']['focus'];anchors=[a for ep in focus['episodes'] for a in ep['anchors']]
    assert len({a['anchor_id'] for a in anchors})==len(anchors)
    assert all(a['trade_date']<=reader.context['trade_date'] for a in anchors)
    oracle=dict(result='PASS',stock_count=count//4,explanation_cell_comparisons=count,
        missing=dict(missing),transition_reason_counts=dict(reasons),real_anchors=len(anchors),anchor_kind_counts=dict(collections.Counter(a['kind'] for a in anchors)),
        source=reader.manifest['sources']['focus_operational'],snapshot=candidate['snapshot'],strict_pit=False)
    if not (OUT/'REAL_SOURCE_ORACLE.json').exists():write(OUT/'REAL_SOURCE_ORACLE.json',oracle)
    else:assert json.loads((OUT/'REAL_SOURCE_ORACLE.json').read_bytes())==oracle
    source=ROOT/'src/workbench_service/static/research'
    build=digest(canonical({p.name:digest(p.read_bytes()) for p in sorted(source.iterdir()) if p.is_file()}));assets={}
    for p in sorted(source.iterdir()):
        if p.is_file():
            target=ROOT/'data/v4/ui_releases'/build/p.name
            if not target.exists():write(target,p.read_bytes())
            assert target.read_bytes()==p.read_bytes();assets[p.name]=ref(target)
    candidate.update(ui_build_id=build,ui_assets=assets)
    validate(ROOT,candidate);assert (ROOT/AUTHORITY).read_bytes()==before
    if not (OUT/'PREDECESSOR.json').exists():write(OUT/'PREDECESSOR.json',dict(sha256=digest(before),authority=json.loads(before)))
    write(OUT/name,candidate)
    print(json.dumps(dict(result='STAGED',ui_build_id=build,stock_comparisons=count,anchors=len(anchors))))

def serve():
    from workbench_service.v4_server import serve_v4
    sandbox=Path('E:/codex_tmp/r2_presentation_preview');candidate=json.loads((OUT/'ACCEPTED_CANDIDATE.json').read_bytes());manifest=validate(ROOT,candidate)
    # The previous isolated root contains the accepted context dependencies.
    # Reuse immutable files by hardlink; mutable config is copied, never linked.
    previous=Path('E:/codex_tmp/r2_focus_preview')
    for p in previous.rglob('*'):
        if p.is_file() and p.relative_to(previous).parts[0] in ('data','config'):
            target=sandbox/p.relative_to(previous)
            if not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(p,target) if p.relative_to(previous).parts[0]=='config' else __import__('os').link(p,target)
    for binding in [candidate['snapshot']['manifest'],manifest['database'],*manifest['sources'].values(),*candidate['ui_assets'].values()]:
        target=sandbox/binding['path'];target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copyfile(ROOT/binding['path'],target)
    write(sandbox/AUTHORITY,candidate);validate(sandbox,candidate);serve_v4(sandbox,'127.0.0.1',28768)

if __name__=='__main__':serve() if '--serve' in sys.argv else prepare()
