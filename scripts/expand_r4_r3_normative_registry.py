"""Preserve every §87A row, including its four-column supplement and open families."""
from pathlib import Path
import csv,hashlib,io,json,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/audits/r4_r3_semantics_focus_20261011'
source=ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md'
lines=source.read_text(encoding='utf8').splitlines();rows=[];in_section=False;families=[]
for number,line in enumerate(lines,1):
    if line.startswith('# 87A.'):in_section=True;continue
    if in_section and line.startswith('# '):break
    if not in_section or not line.startswith('|') or '---' in line:continue
    cells=[cell.strip() for cell in line.strip('|').split('|')]
    if cells[0] in ('字段/字段族','字段族'):continue
    if len(cells) not in (4,5):raise ValueError('UNREVIEWED_REGISTRY_TABLE_SHAPE')
    if len(cells)==5:expression,input_authority,contract,stage,boundary=cells
    else:expression,contract,stage,boundary=cells;input_authority='REFERENCED_CONTRACT_REQUIRED'
    families.append(dict(line=number,expression=expression,column_count=len(cells)))
    for term in expression.split(';'):
        term=term.strip();expanded=[]
        # Only literal shorthand with explicit shared prefix is expanded.
        numeric=re.fullmatch(r'([A-Za-z_]+)([0-9]+(?:/[0-9]+)+)',term)
        if numeric:expanded=[numeric[1]+suffix for suffix in numeric[2].split('/')]
        elif term=='entered/exited':expanded=['entered','exited']
        elif term=='effective_from/to':expanded=['effective_from','effective_to']
        else:expanded=[term]
        for field in expanded:
            concrete=bool(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',field))
            rows.append(dict(normative_field=field,source_expression=term,source_line=number,contract_chain=contract,stage=stage,input_authority=input_authority,missing_boundary=boundary,expansion_rule='EXPLICIT_SHARED_PREFIX' if len(expanded)>1 else 'LITERAL',qualification='CONCRETE_DECLARATION' if concrete else 'OPEN_FAMILY_REQUIRES_SCHEMA_EXPANSION',semantic_acceptance='OPEN_PER_FIELD_PRODUCER_CONSUMER_ORACLE'))
buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
summary=dict(contract_id='R4_R3_COMPLETE_87A_TABLE_PRESERVATION_R1',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),table_rows=len(families),four_column_supplement_rows=sum(f['column_count']==4 for f in families),declared_expanded_entries=len(rows),concrete_declared_entries=sum(r['qualification']=='CONCRETE_DECLARATION' for r in rows),open_family_entries=[r for r in rows if r['qualification']!='CONCRETE_DECLARATION'],families=families,full_semantic_denominator=None,remaining=['Explicit Focus/profile family schemas','FEP referenced §90 and R2 DDL per-field expansion','Concrete producer/source/API mappings and numerical positive/negative tests'],status='ALL_87A_TABLE_ROWS_PRESERVED_FULL_SEMANTIC_ACCEPTANCE_OPEN')
for name,value in [('V4_87A_ALL_DECLARED_FIELDS_R1.csv',buffer.getvalue()),('V4_87A_ALL_TABLE_ROWS_R1.json',json.dumps(summary,ensure_ascii=False,indent=2)+'\n')]:
    with (OUT/name).open('x',encoding='utf8',newline='') as stream:stream.write(value)
print(json.dumps({k:summary[k] for k in ('table_rows','four_column_supplement_rows','declared_expanded_entries','concrete_declared_entries')}))
