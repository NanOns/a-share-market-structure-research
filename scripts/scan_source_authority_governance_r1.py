"""Structural source-governance inventory; findings remain separately owned audit items."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json

def literal(node):return node.value if isinstance(node,ast.Constant) else None
def strings(node):return {n.value for n in ast.walk(node) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
def flattened(value,prefix=''):
    if isinstance(value,dict):
        for k,v in value.items():yield from flattened(v,prefix+'.'+str(k))
    elif isinstance(value,list):
        for i,v in enumerate(value):yield from flattened(v,prefix+f'[{i}]')
    else:yield prefix,value

def inspect_file(relative,data,root=ROOT):
    findings=[]
    def add(category,line,evidence,owner,confidence='STRUCTURAL_REVIEW_REQUIRED'):
        f=dict(category=category,path=relative,line=line,evidence=evidence,remediation_owner=owner,
            confidence=confidence,status='OPEN',automatic_business_rewrite=False)
        if f not in findings:findings.append(f)
    text=data.decode('utf-8-sig')
    if relative.endswith('.py'):
        tree=ast.parse(text)
        all_strings=strings(tree)
        for n in ast.walk(tree):
            if isinstance(n,ast.If):
                test=ast.unparse(n.test)
                if 'date()' in test and ('target_date' in test or 'target_trade_date' in test) and any(x in text for x in ('query_daily_history_k_AStock','BAOSTOCK')):
                    add('C3_HISTORICAL_QUERY_SAME_DAY_ONLY_GATE',n.lineno,'Runtime gate compares current date with data target date','A01_R2','HIGH')
            if isinstance(n,(ast.Assign,ast.AnnAssign)):
                value=n.value
                if value is None:continue
                vs=strings(value)
                targets=n.targets if isinstance(n,ast.Assign) else [n.target]
                names={x.id for t in targets for x in ast.walk(t) if isinstance(x,ast.Name)}
                if any('REQUIRED_SOURCE_FAMILIES' in name for name in names) and any(x.startswith('BAOSTOCK') for x in vs):
                    add('C2_SUPPLEMENTAL_IN_GLOBAL_REQUIRED_SOURCE_SET',n.lineno,'BaoStock literal is in required source families','A01_R2','HIGH')
                if names & {'is_st','tradestatus','status'} and ('isST' in vs or 'tradestatus' in vs):
                    add('C2_PROVIDER_FIELD_ASSIGNED_TO_FORMAL_VARIABLE',n.lineno,'Formal field variable reads provider field; inspect field owner','A12')
            if isinstance(n,ast.Dict):
                for k,v in zip(n.keys,n.values):
                    if literal(k) in ('is_st','status'):
                        source_names={x.id for x in ast.walk(v) if isinstance(x,ast.Name)}
                        if any('provider' in x.lower() or 'baostock' in x.lower() for x in source_names):
                            add('C2_PROVIDER_VALUE_IN_FORMAL_FIELD',n.lineno,'Formal output field directly references provider variable','A12','HIGH')
                    if literal(k) in ('observed_at','received_at','first_available_at') and isinstance(v,ast.Name) and v.id in ('target_date','target_trade_date','trade_date'):
                        add('C4_TARGET_DATE_ASSIGNED_TO_KNOWLEDGE_TIME',n.lineno,'Target date used as observation/availability time','A10','HIGH')
        if 'source_freeze_complete_v2' in text and any(s.startswith('BAOSTOCK') for s in all_strings):
            add('C2_V2_ALL_FAMILY_GATE_WITH_BAOSTOCK',1,'Consumer couples V2 full freeze and BaoStock inputs','A01_R2')
        if 'UNAVAILABLE' in all_strings and any('NOT_QUERIED' in s or 'LOCAL_' in s for s in all_strings):
            add('C1_UNQUALIFIED_UNAVAILABLE_WITH_LOCAL_OR_NOT_QUERIED_STATE',1,'Mixed legacy terminology; receipt evidence required before provider claim','A10')
    elif relative.endswith('.json'):
        value=json.loads(text)
        for key,v in flattened(value):
            if isinstance(v,str) and v=='UNAVAILABLE' and any('capability' in p.lower() for p in key.split('.')):
                add('C1_UNQUALIFIED_CAPABILITY_UNAVAILABLE',None,key,'A10')
            if isinstance(v,str) and ('BaoStock tradestatus' in v or 'BAOSTOCK_DATED_ISST' in v or 'BAOSTOCK_LIFECYCLE_FACTS' in v):
                add('C2_DECLARED_PROVIDER_FORMAL_OWNER_REVIEW',None,key,'A11' if 'LIFECYCLE' in v else 'A12')
        def visit(v,p=''):
            if isinstance(v,dict):
                if v.get('role') in ('CORE_AUTHORITY','FIELD_AUTHORITY') and v.get('owner_contract_id') and v.get('field_id'):
                    from workbench_analysis.source_authority_accepted_owners_v1 import load_registered_owners,exact_json,OwnerAcceptanceError
                    registered=False
                    try:
                        owners=load_registered_owners(root)['owners']
                        for owner in owners:
                            if (owner['owner_contract_id']==v['owner_contract_id'] and owner['field_id']==v['field_id']
                                and owner['external_acceptance']=='EXTERNALLY_ACCEPTED' and owner['formal_consumer_authorization'] is True
                                and owner['role_binding_id']==v.get('role_binding_id')):
                                artifact=exact_json(root,owner['artifact'])
                                registered=artifact.get('role_binding')==v and artifact.get('external_acceptance')=='EXTERNALLY_ACCEPTED'
                    except (OwnerAcceptanceError,OSError,KeyError,ValueError):pass
                    if not registered:
                        category='FIELD_AUTHORITY_WITHOUT_ACCEPTED_OWNER_BINDING'
                        add(category,None,p+':'+v['field_id'],'A10_R2','PENDING_OWNER')
                        if v.get('enabled') is True and v.get('enabled_for_formal_consumer') is not False:
                            add('FORMAL_CONSUMER_USING_PENDING_OWNER',None,p+': declaration requires runtime rejection','A10_R2')
                        if v.get('source_family')=='BAOSTOCK' or v['owner_contract_id'].startswith('BAOSTOCK_SUPPLEMENTAL'):
                            add('SUPPLEMENTAL_ROLE_PROMOTED_WITHOUT_ACCEPTED_OWNER',None,p,'A10_R2','HIGH')
                if v.get('role')=='SUPPLEMENTAL_CROSSCHECK' and (v.get('required') or v.get('may_block_core') or v.get('may_change_core_value')):
                    add('C2_SUPPLEMENTAL_PERMISSION_ESCALATION',None,p,'A10','HIGH')
                if v.get('request_count')==0 and v.get('availability')=='PROVIDER_TARGET_DATE_EMPTY_CONFIRMED':
                    add('C1_NOT_QUERIED_AS_CONFIRMED_PROVIDER_EMPTY',None,p,'A10','HIGH')
                for k,x in v.items():visit(x,p+'.'+k)
            elif isinstance(v,list):
                for i,x in enumerate(v):visit(x,p+f'[{i}]')
        visit(value)
    return findings

def run(root=ROOT):
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode('utf8').split('\0')
    paths=sorted(p for p in tracked if p.endswith(('.py','.json')) and
        (p.startswith(('src/','scripts/','config/')) or ('ACCEPTED_HEAD' in p and p.startswith('data/v4/'))
         or ('CANDIDATE' in p.upper() and p.startswith('reports/'))))
    receipts=[];findings=[];errors=[]
    for p in paths:
        data=(root/p).read_bytes();receipts.append(dict(path=p,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
        try:findings.extend(inspect_file(p,data,root))
        except (UnicodeError,ValueError,SyntaxError) as exc:errors.append(dict(path=p,error=type(exc).__name__))
    groups={}
    for f in findings:groups[f['category']]=groups.get(f['category'],0)+1
    return dict(contract_id='V4_SOURCE_AUTHORITY_GOVERNANCE_SCAN_R2',status='PASS_SCAN_COMPLETE_FINDINGS_OPEN' if not errors else 'FAIL_SCAN_INCOMPLETE',
        scanned_file_count=len(receipts),file_receipts=receipts,findings=findings,finding_counts=groups,parse_errors=errors,
        scanner_limitations=['Structural findings require field-level semantic review; absence of a finding is not source acceptance.',
            'Legacy immutable files remain visible after corrected candidate runtimes are added.'],
        existing_algorithms_modified=False,accepted_heads_modified=False,external_acceptance=None)

if __name__=='__main__':
    result=run();atomic_json(ROOT/'reports/audits/V4_SOURCE_AUTHORITY_GOVERNANCE_SCAN_R1.json',result)
    print(json.dumps(dict(status=result['status'],files=result['scanned_file_count'],findings=len(result['findings']))))
