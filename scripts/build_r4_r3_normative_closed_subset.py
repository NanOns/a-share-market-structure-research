"""Current-body-anchored algorithm requirements with real scoped oracle evidence."""
from pathlib import Path
import json,hashlib,csv,io,os
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/audits/r4_r3_semantics_focus_20261011'

def main():
    body_path=ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
    body=body_path.read_text(encoding='utf8').splitlines();source_sha=hashlib.sha256(body_path.read_bytes()).hexdigest()
    machine=ROOT/'config/v4_04_algorithm_contracts_v2.json';rules=json.loads(machine.read_bytes())['rules']
    oracle=json.loads((OUT/'V4_04_MACHINE_NUMERIC_ORACLE.json').read_bytes())
    assert oracle['status']=='PASS' and oracle['rules_missing_vector_coverage']==[]
    atoms=[]
    def branch_sets(node,path=''):
        if isinstance(node,dict):
            if isinstance(node.get('branches'),list):yield path,node['branches']
            for key,value in node.items():
                if key!='branches' or isinstance(value,dict):yield from branch_sets(value,path+'/'+key)
        elif isinstance(node,list):
            for index,value in enumerate(node):yield from branch_sets(value,path+'/'+str(index))
    for parent_id,rule in rules.items():
      for branch_path,branches in branch_sets(rule):
        rule_id=parent_id+branch_path
        for position,branch in enumerate(branches):
            label=branch['value'];predicate=branch.get('when');digest=hashlib.sha256(json.dumps(predicate,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            anchor=[i for i,line in enumerate(body,1) if isinstance(label,str) and label and label in line and i<6848]
            atoms.append(dict(requirement_id=rule_id+'::FIRST_TRUE_BRANCH_'+str(position),contract_version='V4_04_ALGORITHM_CONTRACTS_V2',
                requirement='In ordered first-true evaluation return '+str(label)+' when predicate holds and all earlier branches do not hold',
                predicate_json=json.dumps(predicate,separators=(',',':')),predicate_sha256=digest,
                current_body_source_sha256=source_sha,current_body_anchor_lines=json.dumps(anchor),
                machine_source_sha256=hashlib.sha256(machine.read_bytes()).hexdigest(),
                algorithm_numeric_and_missing_quality='SCOPED_ORACLE_PASS',evidence='V4_04_MACHINE_NUMERIC_ORACLE.json',
                current_body_semantic_anchor='MATCHED_LABEL_REQUIRES_FULL_PREDICATE_REVIEW' if anchor else 'OPEN_NO_EXACT_LABEL_ANCHOR',
                field_pipeline_source_pg_api_ui='OPEN_PER_REGISTERED_FIELD',external_acceptance='PENDING_INDEPENDENT_REVIEW'))
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=list(atoms[0]));writer.writeheader();writer.writerows(atoms)
    dest=OUT/'V4_NORMATIVE_ALGORITHM_ATOMS_SCOPED.csv';tmp=dest.with_suffix('.csv.tmp');tmp.write_text(buf.getvalue(),encoding='utf8');os.replace(tmp,dest)
    summary=dict(contract_id='R4_R3_SCOPED_NORMATIVE_ALGORITHM_ATOMS_R1',scoped_first_true_requirement_atoms=len(atoms),
        all_current_body_normative_atom_denominator=None,public_rule='Every ordered first-true branch is one conditional-selection requirement; order embedded in requirement identity',
        dedup='contract version + rule ID + branch position; distinct field authorities retained',
        scoped_oracle_rule_count=oracle['machine_rule_count'],scoped_oracle_branch_count=oracle['branch_count'],
        limitations=['Current-body label positions are evidence anchors, not complete predicate proof','Core formulas, field lifecycle, authority/PIT/quality, consumers, schema and all other body requirements remain independently qualified',
            '70 machine branch coverage is not all-V4 normative acceptance'],status='SCOPED_NUMERIC_RULE_REQUIREMENTS_VALIDATED_FULL_NORMATIVE_DENOMINATOR_OPEN')
    dest=OUT/'V4_NORMATIVE_ALGORITHM_ATOMS_SCOPED.json';tmp=dest.with_suffix('.json.tmp');tmp.write_text(json.dumps(summary,indent=2),encoding='utf8');os.replace(tmp,dest)
    print(json.dumps(dict(first_true_atoms=len(atoms),status='SCOPED')))

if __name__=='__main__':main()
