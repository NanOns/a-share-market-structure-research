"""Prepare immutable thin corrections; never mutate sealed numerical Owners."""
import copy,json,hashlib
from pathlib import Path
from dataclasses import asdict
from scripts.v4_closeout_profile_rule_oracle import ROOT,OUT
from v4.profile_core import extension_risk,severe_extension
from v4.profile_status import component_status
from v4.state_identity import digest
from workbench_analysis.r43_owner_replay import checked,ref
from workbench_analysis.r43_operational_publication import rows
from workbench_analysis.operational_daily_storage_v1 import atomic_json

CONTRACT='V4_PROFILE_BRANCH_SEMANTIC_THIN_CORRECTION_R1'

def main():
    report=OUT/'PROFILE_SEMANTIC_PATCH_PREPARATION_R6_R1.json'
    if report.exists():raise ValueError('PRESERVE_PROFILE_PATCH_PREPARATION')
    scope_path=OUT/'EXTENSION_CHANGED_SCOPE_SIX_DATES_R6_R1.json';scope=json.loads(scope_path.read_bytes())
    if scope['acceptance']!='PASS_CHANGED_FUNCTION_ONLY' or scope['errors']:raise ValueError('CHANGED_FUNCTION_ORACLE_REQUIRED')
    candidate=json.loads(checked(ROOT,scope['candidate']).read_bytes());repo=Path(__file__).resolve().parents[1]
    code=(repo/'src/v4/profile_core.py').read_bytes();sha=hashlib.sha256(code).hexdigest()
    folder=ROOT/'data/v4/profile_semantic_corrections_v1'/digest([scope['candidate'],sha,CONTRACT])
    source=folder/'profile_core.py'
    if source.exists() and source.read_bytes()!=code:raise ValueError('IMMUTABLE_CORRECTION_SOURCE_CONFLICT')
    if not source.exists():
        from workbench_analysis.tdx_official_daily_source import _atomic_write
        _atomic_write(source,code,tdx_root=Path('D:/new_tdx'))
    dated=[]
    for day_scope in scope['dates']:
        day=day_scope['T0'];owner=candidate['owners'][day];wanted={c['security_id']:c for c in day_scope['corrections']};patches=[]
        for row in rows(ROOT,owner['profile']):
            sid=row['security_id']
            if sid not in wanted:continue
            old=row['states']['core_extension_risk'];risk=extension_risk(old['evidence']);severe=severe_extension(risk)
            if risk.value!=wanted[sid]['new_risk'] or severe.value!=wanted[sid]['new_severe']:raise ValueError('PATCH_ORACLE_MISMATCH')
            replacement=copy.deepcopy(row)
            for field,state in (('core_extension_risk',risk),('severe_extension',severe)):
                cell=copy.deepcopy(row['states'][field]);cell.update(asdict(state));cell['input_digest']=digest(state.evidence)
                cell.pop('output_digest');cell['output_digest']=digest(cell);replacement['states'][field]=cell
            core_states=[c for k,c in replacement['states'].items() if k!='relative_sector_state']
            unknown=sum(c.get('unknown_reason') is not None for c in core_states)
            replacement['profile_component_status']=component_status(len(core_states)-unknown,len(core_states))
            replacement['profile_quality']='COMPLETE' if unknown==0 else 'PARTIAL_UNKNOWN'
            replacement.pop('output_digest');replacement['output_digest']=digest(replacement)
            unchanged={k:v for k,v in row.items() if k not in ('states','output_digest','profile_component_status','profile_quality')}
            if any(replacement[k]!=v for k,v in unchanged.items()):raise ValueError('PATCH_NONSEMANTIC_FIELD_CHANGED')
            if any(replacement['states'][k]!=v for k,v in row['states'].items() if k not in ('core_extension_risk','severe_extension')):raise ValueError('PATCH_OTHER_STATE_CHANGED')
            patches.append(dict(security_id=sid,original_row_digest=digest(row),replacement=replacement))
        if set(wanted)!={p['security_id'] for p in patches}:raise ValueError('PATCH_SCOPE_INCOMPLETE')
        document=dict(contract_id=CONTRACT,T0=day,original_profile=owner['profile'],original_base_profile=owner.get('base_profile'),original_candidate=scope['candidate'],source=ref(ROOT,source),rows=patches,publication_ready=False,PIT_ELIGIBLE=False,AS_RECORDED=False,scope='Risk/severe/availability/digest correction only; row source_digest retains original upstream input, producing correction Source separately bound')
        target=folder/(day+'.json')
        if target.exists():raise ValueError('PRESERVE_EXISTING_PATCH_DOCUMENT')
        atomic_json(ROOT,target,document);dated.append(dict(T0=day,patch=ref(ROOT,target),rows=len(patches)))
    result=dict(contract_id=CONTRACT,acceptance='PASS_THIN_PATCH_PREPARATION_ONLY',original_candidate=scope['candidate'],scope=ref(OUT,scope_path),source=ref(ROOT,source),dates=dated,correction_count=sum(x['rows'] for x in dated),numerical_producers_reexecuted=False,sealed_owners_changed=False,native_pg_changed=False,publication_ready=False,next='Native semantic correction authority and exactly affected D0/D2/Forward lineage; no release until consumers and independent checks close')
    atomic_json(OUT,report,result);print(json.dumps(dict(acceptance=result['acceptance'],corrections=result['correction_count'])))

if __name__=='__main__':main()
