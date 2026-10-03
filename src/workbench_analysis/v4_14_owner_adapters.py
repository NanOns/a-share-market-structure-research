"""Frozen owner invocations and interface projection, no new business rules."""
import ast,json
from pathlib import Path
from functools import lru_cache
from copy import deepcopy
from .v4_14_replay_io import ref
@lru_cache(maxsize=4)
def state_book(root):return {v['id']:v for v in json.loads((Path(root)/'config/v4_10_machine_vectors_r1_2.json').read_bytes())['vectors']}
def state_vector(root,name):
    from src.v4.research_state import reduce_state
    return reduce_state(deepcopy(state_book(str(root))[name]['input']))
def structure_trace(root,names):
    from .v4_12_structure_io import FrozenContracts
    from .v4_12_ast_runtime import ASTEngine
    c=FrozenContracts(root);book=c.config['machine_vectors'];rows={v['vector_id']:v for v in book['vectors']}
    return [ASTEngine(c.config,{**book['defaults'],**rows[n]['inputs']}).target(rows[n]['target']).value for n in names]
def rotation_acceptance(root,name='R1B'):
    from src.sector.v4_08_rotation_vectors import evaluate_rotation_vector
    book=json.loads((Path(root)/'config/v4_08_rotation_machine_vectors_v2.json').read_bytes())
    return evaluate_rotation_vector(next(v['scenario'] for v in book['vectors'] if v['id']==name))

def synthetic_confirmation(publication):
    """Exact owner detector AST with an explicitly synthetic date envelope.

    The historical detector's data-head date gate admits only 2026-09-30.
    Engineering facts on other dates have no accepted-data capability claim.
    All business statements and the frozen scanner remain byte/AST unchanged.
    """
    from src.v4 import confirmation as owner
    from datetime import datetime
    def validate(p):
        c,m,params,a,scanner=owner.package()
        if p['mode']!='SYNTHETIC_ENGINEERING_VECTOR':raise ValueError('SYNTHETIC_D0_ONLY')
        q={k:v for k,v in p.items() if k not in ('input_digest','publication_id')}
        if p['input_digest']!=owner.digest(q) or p['publication_id']!='V4_11_INPUT:'+owner.digest(q):raise ValueError('SYNTHETIC_D0_DIGEST_INVALID')
        for r in p['source_bindings']:owner.exact(r)
        for row in p['rows']:
            if row['trade_date']!=p['trade_date']:raise ValueError('SYNTHETIC_D0_DATE_INVALID')
            for name,f in row['facts'].items():
                if f['acceptance']!='ENGINEERING_VECTOR' or f['time_role']!=m['input_time_roles'][name] or f['trade_date']>p['trade_date'] or datetime.fromisoformat(f['system_available_at'])>datetime.fromisoformat(p['cutoff_timestamp']):raise ValueError('SYNTHETIC_D0_PROVENANCE_INVALID')
                if f['time_role']=='PRIOR_SESSION_WINDOW' and f['trade_date']>=p['trade_date']:raise ValueError('SYNTHETIC_D0_PRIOR_WINDOW_INVALID')
        return c,m,params,a,scanner
    from src.v4 import confirmation_candidate_r4 as scoped_owner
    fn=next(n for n in ast.parse(Path(scoped_owner.__file__).read_text(encoding='utf8')).body if isinstance(n,ast.FunctionDef) and n.name=='detect')
    scope=dict(scoped_owner.__dict__,validate=lambda p,root:validate(p))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[deepcopy(fn)],type_ignores=[])),'<unchanged_owner_D0_AST>','exec'),scope)
    p=deepcopy(publication);p['logical_digest']=p['input_digest'];p['knowledge_cutoff']=p['cutoff_timestamp'];p['permissions']=dict(production=False,shadow=False,focus=False)
    # Validate the canonical original projection before adding owner transport aliases.
    validate(publication)
    def transport_validate(supplied,root):
        base={k:v for k,v in supplied.items() if k not in ('logical_digest','knowledge_cutoff','permissions')}
        validate(base)
    scope['validate']=transport_validate
    out=scope['detect'](p,owner.ROOT)
    out.update(scope='ENGINEERING_SYNTHETIC',knowledge_lineage='SYNTHETIC',AS_RECORDED=False)
    for row in out['rows']:row.update(knowledge_lineage='SYNTHETIC',AS_RECORDED=False)
    out['publication_id']='SYNTHETIC_D0:'+owner.digest({k:v for k,v in out.items() if k!='publication_id'})
    return out
def event_rows(current,prior,*,target,calendar_id):
    """Execute the unchanged accepted owner's complete per-entity event loop.

    The envelope adapter supplies already validated reducer outputs. The exact
    business AST is extracted from its accepted source, never restated here.
    """
    from src.v4 import confirmation_events as owner
    from src.v4.state_provenance import validate_output
    source=Path(owner.__file__).read_text(encoding='utf8');fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='state_events')
    loop=next(n for n in fn.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='current')
    context=dict(owner.__dict__,final_states=current,old={r['entity_id']:r for r in prior},confirmed_history=prior,
        target=target,calendar_publication_id=calendar_id,frozen=dict(calendar_publication_id=calendar_id,episode_history=[]),
        priority={s:i for i,s in enumerate(owner.package()[3]['scenario_priority'])},expected='REPLAY_EXACT_PRIOR',output=[],
        d2_publication_id='REPLAY_ACCEPTED_OWNER_OUTPUT',revision_of=None,validate_output=validate_output)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[deepcopy(loop)],type_ignores=[])),'<accepted_STATE_EVENT_V1_loop>','exec'),context)
    return context['output']
