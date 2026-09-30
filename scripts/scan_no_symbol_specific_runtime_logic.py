"""P0 static boundary gate for named-security constants in application logic."""
from __future__ import annotations
import ast
import fnmatch
import hashlib
import json
from pathlib import Path
import re

SYMBOL=re.compile(r'\b(?:SH|SZ|BJ)\.\d{6}\b',re.IGNORECASE)
CANONICAL=re.compile(r'\bSEC-[A-F0-9]{16,}\b')
PLAIN_CODE=re.compile(r'^\d{6}$')
IDENTIFIER_CONTEXT=re.compile(r'(security|symbol|ticker|instrument|stock|share|listing|universe|code|index)',re.I)

def _names(node):
    if isinstance(node,ast.Name):return [node.id]
    if isinstance(node,(ast.Tuple,ast.List,ast.Set)):
        return [name for child in node.elts for name in _names(child)]
    return []

def _identifier_context(node,parents):
    context=[];current=node
    while current in parents:
        current=parents[current]
        if isinstance(current,ast.Compare):
            context.extend(_names(current.left))
            for side in current.comparators:context.extend(_names(side))
            break
        if isinstance(current,ast.Dict):
            for key in current.keys:
                if isinstance(key,ast.Constant) and isinstance(key.value,str):context.append(key.value)
        if isinstance(current,ast.Assign):
            context.extend(name.id for target in current.targets for name in ast.walk(target) if isinstance(name,ast.Name))
            break
        if isinstance(current,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Module,ast.ClassDef)):
            break
    return context

def _string_literals(tree):
    parents={}
    docstrings=set()
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):parents[child]=parent
        if isinstance(parent,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and parent.body:
            first=parent.body[0]
            if isinstance(first,ast.Expr) and isinstance(first.value,ast.Constant) and isinstance(first.value.value,str):
                docstrings.add(first.value)
    for node in ast.walk(tree):
        if not isinstance(node,ast.Constant) or not isinstance(node.value,str) or node in docstrings:continue
        value=node.value
        parent=parents.get(node)
        assigned_names=[]
        if isinstance(parent,ast.Assign):assigned_names=[name.id for target in parent.targets for name in ast.walk(target) if isinstance(name,ast.Name)]
        elif isinstance(parent,ast.keyword) and parent.arg:assigned_names=[parent.arg]
        assigned_names.extend(_identifier_context(node,parents))
        if any(re.search(r'(sha|hash|digest|fingerprint)',name,re.I) for name in assigned_names):
            continue
        explicit=SYMBOL.findall(value) or CANONICAL.findall(value)
        if explicit:
            for hit in SYMBOL.finditer(value):yield hit.group(0),node.lineno,'EXPLICIT_SECURITY_OR_SYMBOL_LITERAL'
            for hit in CANONICAL.finditer(value):yield hit.group(0),node.lineno,'CANONICAL_SECURITY_ID_LITERAL'
            continue
        if PLAIN_CODE.fullmatch(value):
            context=_identifier_context(node,parents)
            if isinstance(parent,ast.keyword) and parent.arg:context.append(parent.arg)
            if any(IDENTIFIER_CONTEXT.search(x or '') for x in context):
                yield value,node.lineno,'UNQUALIFIED_SECURITY_CODE_IN_IDENTIFIER_CONTEXT'

def _numeric_code_literals(tree):
    parents={child:parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    for node in ast.walk(tree):
        if not isinstance(node,ast.Constant) or not isinstance(node.value,int) or isinstance(node.value,bool):continue
        if not 100000<=node.value<=999999:continue
        if any(re.search(r'(sha|hash|digest|fingerprint)',name,re.I) for name in _identifier_context(node,parents)):continue
        if any(IDENTIFIER_CONTEXT.search(name or '') for name in _identifier_context(node,parents)):
            yield str(node.value),node.lineno,'NUMERIC_SECURITY_CODE_IN_IDENTIFIER_CONTEXT'

def scan_file(path: Path, *, root: Path, category: str):
    rel=path.relative_to(root).as_posix();hits=[];raw=path.read_bytes()
    if path.suffix.lower()=='.py':
        try:tree=ast.parse(raw.decode('utf-8'),filename=rel)
        except (SyntaxError,UnicodeDecodeError) as exc:
            return {'path':rel,'category':category,'parse_error':str(exc),'hits':[],'byte_count':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        for value,line,kind in _string_literals(tree):
            hits.append({'line':line,'value':value,'kind':kind})
        for value,line,kind in _numeric_code_literals(tree):
            hits.append({'line':line,'value':value,'kind':kind})
    elif path.suffix.lower()=='.sql':
        text=raw.decode('utf-8',errors='replace')
        for pattern,kind in [(SYMBOL,'EXPLICIT_SECURITY_OR_SYMBOL_LITERAL'),(CANONICAL,'CANONICAL_SECURITY_ID_LITERAL')]:
            hits.extend({'line':text.count('\n',0,m.start())+1,'value':m.group(0),'kind':kind} for m in pattern.finditer(text))
        for m in re.finditer(r'''(?:security|symbol|ticker|instrument|stock)[_ ]?(?:code|id)\s*(?:=|IN\s*\()\s*['"]?(\d{6})''',text,re.I):
            hits.append({'line':text.count('\n',0,m.start())+1,'value':m.group(1),'kind':'SQL_SECURITY_FILTER_LITERAL'})
    elif path.suffix.lower()=='.json':
        try:document=json.loads(raw)
        except (json.JSONDecodeError,UnicodeDecodeError) as exc:
            return {'path':rel,'category':category,'parse_error':str(exc),'hits':[],'byte_count':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        def walk(value,key=''):
            if isinstance(value,dict):
                for child_key,child in value.items():walk(child,child_key)
            elif isinstance(value,list):
                for child in value:walk(child,key)
            elif isinstance(value,str):
                for match in SYMBOL.finditer(value):
                    hits.append({'line':None,'value':match.group(0),'kind':'EXPLICIT_SECURITY_OR_SYMBOL_DATA','field':key})
                for match in CANONICAL.finditer(value):
                    hits.append({'line':None,'value':match.group(0),'kind':'CANONICAL_SECURITY_ID_DATA','field':key})
                if PLAIN_CODE.fullmatch(value) and IDENTIFIER_CONTEXT.search(key):
                    hits.append({'line':None,'value':value,'kind':'UNQUALIFIED_SECURITY_CODE_DATA','field':key})
        walk(document)
    elif path.suffix.lower()=='.md':
        text=raw.decode('utf-8',errors='replace')
        for pattern,kind in [(SYMBOL,'EXPLICIT_SECURITY_OR_SYMBOL_EVIDENCE'),(CANONICAL,'CANONICAL_SECURITY_ID_EVIDENCE')]:
            hits.extend({'line':text.count('\n',0,m.start())+1,'value':m.group(0),'kind':kind} for m in pattern.finditer(text))
    return {'path':rel,'category':category,'hits':hits,'byte_count':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def _matches(path,patterns):return any(fnmatch.fnmatchcase(path,p) for p in patterns)

def classify(path: str,policy: dict):
    if path.startswith('tests/') and path.endswith('.py'):return 'TEST_ONLY'
    if path.startswith('scripts/') and path.endswith(('.py','.sql')):return 'AUDIT_ONLY'
    if path.startswith('tests/') and path.endswith('.sql'):return 'TEST_ONLY'
    if _matches(path,policy['test_only_globs']):return 'TEST_ONLY'
    if _matches(path,policy.get('evidence_only_globs',[])):return 'EVIDENCE_ONLY'
    if _matches(path,policy['audit_only_globs']):return 'AUDIT_ONLY'
    if path in policy['reference_data_paths']:return 'REFERENCE_DATA'
    if _matches(path,policy['production_runtime_globs']):return 'PRODUCTION_RUNTIME'
    if path in policy['runtime_configuration_paths']:return 'RUNTIME_CONFIGURATION'
    if path.startswith('src/workbench_db/') and path.endswith('.sql'):return 'PRODUCTION_RUNTIME'
    if _matches(path,policy.get('contract_configuration_globs',[])):return 'CONTRACT_CONFIGURATION'
    if path.startswith('config/') and path.endswith('.json'):return 'CONTRACT_CONFIGURATION'
    if _matches(path,policy.get('audit_evidence_paths',[])):return 'EVIDENCE_ONLY'
    return 'UNCLASSIFIED'

def run(root: Path):
    policy_path=root/'config/runtime_path_policy_v1.json';policy=json.loads(policy_path.read_text(encoding='utf-8'))
    results=[]
    scan_roots=['src','scripts','tests','config','docs/evidence','reports/v4_08/audit_inputs']
    for dirname in scan_roots:
        base=root/dirname
        if not base.exists():continue
        for path in sorted(base.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in {'.py','.sql','.json','.md'}:continue
            rel=path.relative_to(root).as_posix()
            category=classify(rel,policy)
            if category=='UNCLASSIFIED':
                results.append({'path':rel,'category':category,'hits':[],'classification_error':True})
            else:results.append(scan_file(path,root=root,category=category))
    for path in [root/'run_daily.py',root/'run_workbench_service.py']:
        if path.exists():results.append(scan_file(path,root=root,category=classify(path.name,policy)))
    production=[x for x in results if x['category'] in {'PRODUCTION_RUNTIME','RUNTIME_CONFIGURATION'}]
    prod_hits=[{'path':x['path'],**hit} for x in production for hit in x['hits']]
    unclassified=[x['path'] for x in results if x['category']=='UNCLASSIFIED' or x.get('classification_error') or x.get('parse_error')]
    by_category={name:sum(len(x['hits']) for x in results if x['category']==name) for name in ['PRODUCTION_RUNTIME','RUNTIME_CONFIGURATION','REFERENCE_DATA','AUDIT_ONLY','TEST_ONLY','CONTRACT_CONFIGURATION','EVIDENCE_ONLY']}
    return {'status':'PASS' if not prod_hits and not unclassified else 'FAIL','gate':'NO_SYMBOL_SPECIFIC_RUNTIME_LOGIC','production_runtime_hits':len(prod_hits),'runtime_hits':prod_hits,'literal_symbol_hits':sum(len(x['hits']) for x in results),'audit_only_hits':by_category['AUDIT_ONLY'],'test_only_hits':by_category['TEST_ONLY'],'reference_data_hits':by_category['REFERENCE_DATA'],'runtime_configuration_hits':by_category['RUNTIME_CONFIGURATION'],'false_positive_hits':[],'unclassified_paths':unclassified,'scanned_paths':[x['path'] for x in results],'runtime_file_count':sum(x['category']=='PRODUCTION_RUNTIME' for x in results),'results':results,'policy_path':policy_path.relative_to(root).as_posix()}

def main():
    root=Path(__file__).resolve().parents[1]
    result=run(root)
    path=root/'reports/v4_08/V4_08_R4_P0_NO_SYMBOL_SPECIFIC_RUNTIME_SCAN.json'
    from build_v4_08_r2_membership_evidence import atomic_json
    atomic_json(path,result)
    print(json.dumps({k:result[k] for k in ['status','production_runtime_hits','literal_symbol_hits','audit_only_hits','test_only_hits','reference_data_hits','unclassified_paths']}))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
