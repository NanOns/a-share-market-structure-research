"""Preserve all 87A tables, concrete registry versions and 56 dynamic evidence.

Missing observations remain explicit; source snapshots never become execution SHA.
"""
from pathlib import Path
import csv, io, json, hashlib, re

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('G:/codex_tmp/v4_full_closeout_20261012/pg_semantics/full_ledger_R2')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def csv_write(name,rows):
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (OUT/name).write_text(stream.getvalue(),encoding='utf8')

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    contract=ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
    lines=contract.read_text('utf8').splitlines();inside=False;norms=[]
    for number,line in enumerate(lines,1):
        if line.startswith('# 87A.'):inside=True;continue
        if inside and line.startswith('# '):break
        if not inside or not line.startswith('|') or '---' in line:continue
        cells=[c.strip() for c in line.strip('|').split('|')]
        if cells[0] in ('字段/字段族','字段族'):continue
        if len(cells)==5:expression,authority,algorithm,stage,boundary=cells
        elif len(cells)==4:expression,algorithm,stage,boundary=cells;authority='REFERENCED_CONTRACT_REQUIRED'
        else:raise ValueError('UNREVIEWED_87A_TABLE_SHAPE')
        for term in expression.split(';'):
            term=term.strip();numeric=re.fullmatch(r'([A-Za-z_]+)([0-9]+(?:/[0-9]+)+)',term)
            expanded=[numeric[1]+n for n in numeric[2].split('/')] if numeric else ['entered','exited'] if term=='entered/exited' else ['effective_from','effective_to'] if term=='effective_from/to' else [term]
            for field in expanded:
                norms.append(dict(field=field,source_expression=term,table_columns=len(cells),source_line=number,source_sha256=sha(contract),authoritative_input=authority,algorithm_contract=algorithm,stage=stage,missing_boundary=boundary,concrete=bool(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',field)),source_cutoff_quality_transform_stored_consumer='PER_REGISTRY_AND_REAL_OWNER_REQUIRED',acceptance='NOT_ESTABLISHED_BY_DECLARATION'))
    csv_write('V4_NORMATIVE_FIELD_LEDGER.csv',norms)
    registries=[]
    for path in sorted((ROOT/'config').glob('*field*registry*.json')):
        doc=json.loads(path.read_bytes());fields=doc.get('fields') or doc.get('registry') or []
        contract_id=doc.get('contract_id') or doc.get('field_registry_id') or doc.get('registry_contract_id') or 'EXPLICIT_REGISTRY_FILE_VERSION'
        if isinstance(fields,dict):fields=[dict(item,field_id=field) for field,item in fields.items()]
        for field in fields:
            name=field.get('field_id') or field.get('field') or field.get('logical_field') or field.get('name')
            if not name:raise ValueError('UNIDENTIFIED_FIELD:'+path.name)
            producer=field.get('producer_contract_id') or field.get('producer') or field.get('producer_authority') or ''
            registries.append(dict(registry_file=path.relative_to(ROOT).as_posix(),registry_sha256=sha(path),registry_contract_id=contract_id,field=name,producer=json.dumps(producer,ensure_ascii=False),unit=field.get('unit'),formula=field.get('formula_family') or field.get('semantic_definition') or field.get('semantic'),window=field.get('window_semantics') or field.get('window_contract'),source_cutoff=field.get('time_semantics') or field.get('time_role') or field.get('as_of'),quality=field.get('quality_propagation') or field.get('unknown_policy') or field.get('unknown_behavior') or field.get('missing'),consumer=json.dumps(field.get('consumer') or field.get('consumer_stage') or field.get('consumer_definitions') or '',ensure_ascii=False),metadata=json.dumps(field,ensure_ascii=False,separators=(',',':')),active_version='RETAINED_VERSION_NO_STATIC_EXCLUSION',acceptance='REAL_SOURCE_PG_READBACK_AND_INDEPENDENT_ORACLE_REQUIRED'))
    csv_write('V4_ALL_VERSIONED_FIELD_PIPELINES.csv',registries)
    original=ROOT/'docs/audits/full_system_repair_r3_20261011_239fb9b5/A4_CONSUMER_IMPACT.json'
    consumers=json.loads(original.read_bytes())['consumers'];assert len(consumers)==56
    traces=[]
    for path in sorted((ROOT/'docs/audits/v4_full_closeout_20261012').rglob('*TRACE*.json')):
        try:doc=json.loads(path.read_bytes())
        except json.JSONDecodeError:continue
        if doc.get('denominator')==56 and isinstance(doc.get('rows'),list):traces.append((path,doc))
    matrix=[]
    for number,consumer in enumerate(consumers,1):
        name=consumer['path'].replace('\\','/');observations=[]
        for path,doc in traces:
            row=next((r for r in doc['rows'] if r['path']==name),None)
            if row and row.get('actual_call_count',0):observations.append(dict(evidence=path.relative_to(ROOT).as_posix(),evidence_sha256=sha(path),entry=doc['entry'],actual_calls=row['actual_call_count'],source_sha256_observed_at_trace_close=row['source_sha256'],loaded_source_sha256='SEPARATE_ENTRY_BEFORE_BINDING_REQUIRED',functions=row.get('calls',[])))
        matrix.append(dict(index=number,path=name,original_sha256=consumer['sha256'],current_sha256=sha(ROOT/name),original_transport=consumer['transport'],observed_entries=len(observations),actual_calls=sum(r['actual_calls'] for r in observations),dynamic_evidence=json.dumps(observations,ensure_ascii=False,separators=(',',':')),reachability='DYNAMICALLY_OBSERVED' if observations else 'UNRESOLVED_NOT_PROVEN_UNREACHABLE',arithmetic_oracle='CALLER_SOURCE_COORDINATE_NUMERIC_EVIDENCE_REQUIRED',acceptance='NO_GLOBAL_PASS_FROM_CALL_ENUMERATION'))
    csv_write('V4_EXACT_56_MATRIX.csv',matrix)
    result=dict(contract_id='V4_FULL_NORMATIVE_AND_56_PRESERVATION_R2',normative_source_sha256=sha(contract),all_87a_table_rows=len({r['source_line'] for r in norms}),four_column_table_rows=len({r['source_line'] for r in norms if r['table_columns']==4}),declared_expressions=len(norms),registry_versions=len({r['registry_sha256'] for r in registries}),versioned_concrete_field_entries=len(registries),consumer_denominator=56,observed_consumers=sum(bool(r['observed_entries']) for r in matrix),trace_bindings=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p,d in traces],normative_approved_atom_denominator=None,full_semantics_acceptance='OPEN_NOT_COLUMN_ENUMERATION_PASS',limitations=['R1 five-column-only ledger omitted the four-column supplement; R2 preserves all tables','All registry file versions are retained; no version is excluded by filename','Trace close-time source SHA is not substituted for the actually loaded before-run source','An unobserved caller is unresolved, never automatically a legacy exclusion'])
    (OUT/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('trace_bindings','limitations')}))

if __name__=='__main__':main()
