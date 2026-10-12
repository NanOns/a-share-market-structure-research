"""Explicit current registered field expansion without substituting for norms."""
from pathlib import Path
import json,csv,io,hashlib,os,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/audits/r4_r3_semantics_http_20261011'
SELECTED=['v4_03_field_registry_v1.json','v4_04_field_registry_v2.json','v4_07_field_registry_v1.json',
    'v4_08_sector_field_registry_r5.json','v4_09_field_registry_v1.json','v4_12_field_registry_v1.json',
    'v4_13_field_registry_v1_2.json','v4_15_field_registry_v1.json']

def atomic(name,text):
    dest=OUT/name;tmp=dest.with_suffix(dest.suffix+'.tmp');tmp.write_text(text,encoding='utf8');os.replace(tmp,dest)
def main():
    body=(ROOT/'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md').read_text(encoding='utf8').splitlines()
    section=False;families=[]
    for line_no,line in enumerate(body,1):
        if line.startswith('# 87A.'):section=True;continue
        if section and line.startswith('# '):break
        if section and line.startswith('|') and '---' not in line and '字段/字段族' not in line:
            cells=[c.strip() for c in line.strip('|').split('|')]
            if len(cells)==5:families.append((line_no,cells))
    rows=[];keys=set();bindings=[]
    for filename in SELECTED:
        path=ROOT/'config'/filename;blob=path.read_bytes();source_sha=hashlib.sha256(blob).hexdigest();registry=json.loads(blob)
        contract=registry.get('contract_id') or registry.get('field_registry_id')
        fields=registry.get('fields') or registry.get('registry')
        if isinstance(fields,dict):fields=[dict(value,field_id=key) for key,value in fields.items()]
        bindings.append(dict(path='config/'+filename,sha256=source_sha,contract_id=contract,field_entries=len(fields)))
        source_lines=blob.decode().splitlines()
        for entry in fields:
            field=entry.get('field_id') or entry.get('field') or entry.get('logical_field')
            if not field:raise ValueError('UNIDENTIFIED_REGISTRY_FIELD:'+filename)
            # Versioned identities intentionally retain distinct producer authorities.
            key=(contract,field,entry.get('producer_contract_id') or entry.get('producer') or '')
            if key in keys:raise ValueError('DUPLICATE_CURRENT_FIELD_IDENTITY:'+repr(key))
            keys.add(key)
            matched=[number for number,cells in families if re.search(r'(?<![A-Za-z0-9_])'+re.escape(field)+r'(?![A-Za-z0-9_])',cells[0])]
            loc=next((index for index,line in enumerate(source_lines,1) if '"'+field+'"' in line),None)
            numeric=field in ('ma5','ma20','ma60','ret1','ret3','ret5','ret20','amount_state','volume_state','near_high20_state','near_high60_state')
            rows.append(dict(field_id=field,registry_contract_id=contract,registry_source='config/'+filename,
                source_sha256=source_sha,source_line=loc,section_87a_lines=json.dumps(matched),
                formula=entry.get('formula_family') or entry.get('semantic_definition') or entry.get('semantic') or '',
                unit=entry.get('unit',''),window=entry.get('window_contract') or entry.get('window_semantics') or '',
                producer=entry.get('producer_contract_id') or entry.get('producer') or '',
                consumer=json.dumps(entry.get('consumer') or entry.get('consumer_definitions') or entry.get('consumer_stage') or '',ensure_ascii=False),
                source_time=entry.get('time_semantics') or entry.get('time_role') or entry.get('as_of') or '',
                quality=entry.get('quality_propagation') or entry.get('unknown_policy') or entry.get('unknown_behavior') or entry.get('missing') or '',
                declared_semantic_status=entry.get('semantic_status') or entry.get('authority_status') or '',
                scoped_numeric_evidence='HTTP_CORE_INDEPENDENT_ORACLE.json' if numeric else '',
                status='SCOPED_NUMERIC_VALIDATION_FORMAL_FIELD_OPEN' if numeric else 'OPEN_INDIVIDUAL_SEMANTIC_ORACLE',
                required_closure='Current approved producer+schema+indexes+source first-available+unit/formula/window+actual consumer/API/UI+independent positive/negative oracle',
                original_field_metadata=json.dumps(entry,ensure_ascii=False,separators=(',',':'))))
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    atomic('V4_FIELD_VERSIONED_EXPANSION.csv',buf.getvalue())
    summary=dict(contract_id='R4_R3_CURRENT_REGISTERED_FIELD_EXPANSION_R1',selected_versions=bindings,
        unique_versioned_registry_field_identities=len(rows),dedup_rule='registry contract_id + concrete field + producer authority; duplicate exact identities fail',
        normative_section87a_versioned_field_denominator=None,
        exact_field_name_matches_to_87a=sum(bool(json.loads(r['section_87a_lines'])) for r in rows),
        unmatched_registry_metadata_or_family_expansion=sum(not bool(json.loads(r['section_87a_lines'])) for r in rows),
        scope_rule='Explicit current stage registry list, retaining every concrete entry and original quality/permission metadata',
        missing_stages=['V4-10 output schema exists without a dedicated field registry; requires normative-field qualification','V4-11 typed legacy-adapter schema requires normative-field qualification'],
        limitations=['Selected concrete registry identities are not the approved §87A denominator','Slash/family expressions require explicit approved expansions','Source/authority flags are not execution acceptance'],
        status='REGISTERED_FIELD_EXPANSION_COMPLETE_NORMATIVE_COMPLETENESS_OPEN')
    atomic('V4_FIELD_VERSIONED_EXPANSION.json',json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(dict(versioned_registered_fields=len(rows),exact_87a_matches=summary['exact_field_name_matches_to_87a'])))

if __name__=='__main__':main()
