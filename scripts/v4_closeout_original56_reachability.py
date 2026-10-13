"""Preserve original 56 and collect conservative current entry reachability.

Static absence is diagnostic until dynamic execution sites are reviewed.
"""
import ast,json,hashlib,subprocess
from pathlib import Path
from collections import deque
from workbench_analysis.operational_daily_storage_v1 import atomic_json

ROOT=Path(__file__).resolve().parents[1];OUT=Path('G:/codex_tmp/v4_full_closeout_20261012')
ENTRY=('workbench_desktop.engine','workbench_service.core_product_server_r1','workbench_analysis.operational_daily_executor_v1','workbench_desktop.source_adapter')

def main():
    report=OUT/'ORIGINAL56_REACHABILITY_R3.json'
    if report.exists():raise ValueError('PRESERVE_PRIOR_REACHABILITY')
    names=subprocess.check_output(['rg','--files','--hidden','--no-ignore','src','scripts','-g','*.py'],cwd=ROOT,text=True).splitlines()
    modules={};files={};trees={}
    for name in names:
        name=name.replace('\\','/');raw=(ROOT/name).read_bytes();tree=ast.parse(raw.decode('utf-8-sig'));trees[name]=tree
        module=name[:-3].replace('/','.');aliases={module}
        if module.startswith('src.'):aliases.add(module[4:])
        if module.endswith('.__init__'):aliases={x[:-9] for x in aliases}
        for alias in aliases:modules[alias]=name
        files[name]=dict(path=name,sha256=hashlib.sha256(raw).hexdigest())
    edges={};sites={}
    for module,name in modules.items():
        package=module if name.endswith('/__init__.py') else module.rsplit('.',1)[0];imports=set();dynamic=[]
        parts=module.split('.')
        imports.update('.'.join(parts[:i]) for i in range(1,len(parts)))
        for node in ast.walk(trees[name]):
            if isinstance(node,ast.Import):imports.update(x.name for x in node.names)
            elif isinstance(node,ast.ImportFrom):
                parent=package.split('.');prefix='.'.join(parent[:len(parent)-node.level+1]) if node.level else ''
                base='.'.join(x for x in (prefix,node.module) if x);imports.add(base);imports.update(base+'.'+x.name for x in node.names)
            elif isinstance(node,ast.Call):
                function=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
                if function in ('__import__','import_module') and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):imports.add(node.args[0].value)
                if function in ('__import__','import_module','exec_module','exec','eval','spec_from_file_location'):
                    dynamic.append(dict(line=node.lineno,function=function,expression=ast.unparse(node)[:600]))
        edges[module]=sorted(x for x in imports if x in modules);sites[module]=dynamic
    witness={};queue=deque((m,[m]) for m in ENTRY)
    while queue:
        module,path=queue.popleft()
        if module in witness:continue
        witness[module]=path;queue.extend((m,path+[m]) for m in edges.get(module,()))
    byfile={}
    for module,path in witness.items():byfile.setdefault(modules[module],path)
    traces=[]
    for name in ('exact_daily_candidate_20261013_R3_EXACT56_TRACE.json','exact_daily_candidate_20261013_R4_EXACT56_TRACE.json','exact_daily_candidate_20261013_R6_EXACT56_TRACE.json','FIELD_PROJECTION_ORACLE_R6_R1/EXACT56_TRACE.json','SEALED_BFF_R6_FIELD_CONTINUATION/EXACT56_TRACE.json','RESEARCH_SIDECAR_EXACT56_TRACE_R6_R1.json'):
        path=OUT/name
        if path.is_file():traces.append((name,json.loads(path.read_bytes())))
    original=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5/A4_CONSUMER_IMPACT.json';rows=[]
    for item in json.loads(original.read_bytes())['consumers']:
        name=item['path'].replace('\\','/');observations=[]
        for source,trace in traces:
            observed=next(r for r in trace['rows'] if r['path']==name)
            substantive=[c for c in observed['calls'] if c['function']!='<module>']
            if substantive:observations.append(dict(trace=source,executed_source_sha256=observed['source_sha256'],calls=substantive,current_file_same=observed['source_sha256']==files[name]['sha256']))
        rows.append(dict(path=name,current_source=files[name],original_audit_source_sha256=item['sha256'],static_reachable=name in byfile,
            witness=byfile.get(name),observations=observations,disposition='ACTIVE_OBSERVED_REQUIRES_SEMANTIC_BINDING' if observations else 'REACHABLE_IMPORT_REQUIRES_FUNCTION_REVIEW' if name in byfile else 'STATIC_ABSENCE_REQUIRES_DYNAMIC_PROOF'))
    dynamics={name:sites[module] for name,path in byfile.items() if sites[module:=path[-1]]}
    result=dict(contract_id='V4_ORIGINAL56_CURRENT_REACHABILITY_AUDIT_R1',acceptance='DIAGNOSTIC_NO_EXCLUSIONS',denominator=len(rows),original_audit=dict(path=original.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(original.read_bytes()).hexdigest()),
        entries=list(ENTRY),rows=rows,dynamic_sites=dynamics,reachable_files=[files[name] for name in sorted(byfile)],
        scope='Conservative imports including packages, scripts, src aliases and literal dynamic imports; unobserved and dynamic sites require review, no UNKNOWN exclusion or price correctness claim')
    atomic_json(OUT,report,result);print(json.dumps(dict(denominator=len(rows),observed=sum(bool(x['observations']) for x in rows),static_reachable=sum(x['static_reachable'] for x in rows),dynamic_files=len(dynamics))),flush=True)

if __name__=='__main__':main()
