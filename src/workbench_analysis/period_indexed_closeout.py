"""Exact calendar lookup optimization; original period branches stay intact."""
import ast
import hashlib
import inspect
from functools import lru_cache
from . import dm01_incremental_component_builders_r3_3 as kernels
from .v4_12_structure_io import canonical

CONTRACT='V4_PERIOD_INDEXED_CALENDAR_EXACT_PARENT_CLOSEOUT_R1'

@lru_cache(maxsize=16)
def calendar_index(sessions):
    index={kind:{} for kind in ('WEEKLY','MONTHLY')}
    for day in sessions:
        number=int(day.replace('-',''))
        for kind in index:index[kind].setdefault(kernels.period_key(number,kind),[]).append(day)
    return index

def install(scope,sessions):
    tree=ast.parse(inspect.getsource(kernels._build_period))
    changed=[]
    class ExactLookup(ast.NodeTransformer):
        def visit_Assign(self,node):
            if len(node.targets)!=1 or not isinstance(node.targets[0],ast.Name):return node
            name=node.targets[0].id
            if name not in ('eligible','dates'):return node
            expected="[d for d in sessions if period_key(int(d.replace('-','')),kind)=="+('oldkey[2]' if name=='eligible' else 'pk')+"]"
            if ast.dump(node.value)!=ast.dump(ast.parse(expected,mode='eval').body):
                raise ValueError('PERIOD_FROZEN_CALENDAR_LOOKUP_AST_CHANGED')
            node.value=ast.parse('_closeout_calendar_dates(kind,'+('oldkey[2]' if name=='eligible' else 'pk')+')',mode='eval').body
            changed.append(name);return node
    tree=ExactLookup().visit(tree)
    if sorted(changed)!=['dates','eligible']:raise ValueError('PERIOD_EXACTLY_TWO_CALENDAR_LOOKUPS_REQUIRED')
    index=calendar_index(tuple(sessions))
    scope['_closeout_calendar_dates']=lambda kind,key:list(index[kind].get(key,()))
    exec(compile(ast.fix_missing_locations(tree),__file__,'exec'),scope)

def parent_digest_factory():
    """Hash the identical canonical parent, reusing serialized immutable cells."""
    cache={}
    def digest_parent(parent):
        if set(parent)!={'rows'}:raise ValueError('PERIOD_EXACT_PARENT_SHAPE_REQUIRED')
        result=hashlib.sha256();result.update(b'{"rows":[')
        for number,row in enumerate(parent['rows']):
            if number:result.update(b',')
            key=tuple((name,type(value),value) for name,value in sorted(row.items()))
            try:raw=cache.get(key)
            except TypeError:raw=canonical(row)[:-1];key=None
            if raw is None:
                raw=canonical(row)[:-1]
                if key is not None:cache[key]=raw
            result.update(raw)
        result.update(b']}\n');return result.hexdigest()
    return digest_parent
