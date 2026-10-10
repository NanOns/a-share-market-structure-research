"""Archive read-only R4 FEP inventory; never execute models or database writes."""
import json
import hashlib
import os
from pathlib import Path
from workbench_analysis.fep_e5.admission import current_gate, REASONS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/v4_current_snapshot_r4_20261010/04_D_FEP'
def ref(path):
    p=ROOT/path
    return dict(path=path,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def write(name, payload):
    target=OUT/name;temp=target.with_suffix(target.suffix+'.tmp')
    temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temp,target)
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    catalog=json.loads((ROOT/'reports/fep_e5_r1/MODEL_CATALOG.json').read_bytes())['models']
    export=json.loads((ROOT/'reports/fep_e5_r1r1c/FRESH_CANONICAL_LEDGER_EXPORT.json').read_bytes())['tables']
    refs=[ref(p) for p in ['reports/fep_e5_r1/MODEL_CATALOG.json','reports/fep_e5_r1/PERMISSION_MATRIX.json',
        'reports/fep_e5_r1r1c/FRESH_CANONICAL_LEDGER_EXPORT.json','reports/fep_e5_r1r1c/STAGE_ACCEPTANCE_AND_NEXT.json',
        'reports/fep_e3_r1/MODEL_REGISTRY_GATE.json','reports/fep_e4_r1/MODEL_REGISTRY_GATE.json',
        'docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV4_FEP_R2_20260930.md']]
    models=[]
    for model in catalog:
        artifacts=[]
        for artifact in model['artifact_references'].values():
            actual=ref(artifact['path']);actual['matches_registered_sha']=actual['sha256']==artifact['sha256'];artifacts.append(actual)
        models.append(dict(model_registration=model,artifacts=artifacts,model_revision=dict(value=model['artifact_digest'],kind='CONTENT_ADDRESSED_HISTORICAL_MODEL',numeric_revision=None),
            training_first_available=dict(status='INPUT_ASOF_NOT_VERIFIED',AS_RECORDED=False,FIRST_OBSERVED=False,reason='Existing accepted corrected/reconstructed historical artifacts do not establish contemporaneous availability.'),
            review_state='ACCEPTED_ENGINEERING_ONLY_NO_PRODUCTION',current_production_usable=False))
    predictions=export['predictions'];usable=sum(p['outputs'].get('projection_state')=='READY' and p['outputs'].get('axes',{}).get('return_expectancy') is not None for p in predictions)
    gate=current_gate(ROOT)
    write('D_FEP_ACCEPTED_MODEL_AND_GRANT_INVENTORY.json',dict(contract=gate['contract_id'],search_scope='Repository reports/config/source and latest sealed canonical fixture export; live production DB not queried',
        source_bindings=refs,models=models,accepted_model_sets=export['model_sets'],grant_keys=export['permission_keys'],
        grants_scope='HISTORICAL_ENGINEERING_SHADOW_ONLY_NOT_CURRENT_PRODUCTION',prediction_count=len(predictions),
        prediction_revisions=sorted({p['revision'] for p in predictions}),historical_ready_count=usable,
        historical_ready_rate=usable/len(predictions),current_production_ready_rate=0.0,real_oos_count=0,
        current_gate=gate,db_readback_provenance='Frozen 2026-10-06 fixture export, not live production inventory',
        next_stage='Independent acceptance and separately explicit current model/input/grant approval; no activation'))
    write('D_FEP_PERMISSION_NEGATIVES.json',dict(reasons=REASONS,tests='tests/fep_e5/test_r4_admission.py',result='14 PASSED',
        frozen_fields=['accepted_at','revision','model_id','input_digest','axes'],shadow_cannot_grant_model_display=True,
        broader_check=dict(passed=41,setup_errors=22,reason='DISPOSABLE_PG_CLUSTER_REQUIRED; default legacy port blocked before DB access'),
        no_prediction=True,no_grant_issued=True))
    write('D_FEP_FIELD_CAPABILITY_MATRIX.json',dict(source_bindings=refs,fields={field:dict(owner='FEP_CURRENT_ADMISSION_R4_V1',version='1',
        quality='UNAVAILABLE',coverage=None,permission='NOT_GRANTED',asof='INPUT_ASOF_NOT_VERIFIED',maturity='SAMPLE_NOT_MATURE',
        field_status=state,source_sha256=gate['source_sha256']) for field,state in gate['fields'].items()}))
    for name,text in {
        'D_FEP_ACTIVATION_DECISION.md':'# R4 D admission decision\n\nFEP_ENGINEERING_GATE_READY; FEP_PRODUCTION_AUTHORIZED remains BLOCKED.\n\nExisting E2/E3/E4 models, accepted sets and shadow grants are preserved and inventoried. Historical corrected reconstruction is not first-observed production evidence. No training, prediction, grant, activation, Accepted Head or TDX mutation occurred. Next gate requires independent external acceptance and explicit formal production model/input/grant authority.\n',
        'D_FEP_GATE_UI_QA.md':'# R4 D API/UI QA\n\n/api/v4/forward/fep retains null prediction and existing capability fields. It adds admission_gate, six field statuses and Chinese reason_text. Production remains locally degraded; historical model existence is shown accurately. New focused tests: 14 passed. Broader historical E5 tests: 41 passed, 22 setup errors caused by disposable-DB isolation guard; no DB was accessed.\n\nCurrent-code isolated API verification: 10 routes passed, FEP correctly returns missing-source and Chinese admission reasons. Evidence: ../05_E_RUNTIME/E_NEW_CODE_ISOLATED_READBACK.json.\n\nBrowser DOM: NOT_TESTED. IAB returned ERR_BLOCKED_BY_CLIENT; Chrome unavailable. API verification does not establish browser acceptance.\n'
    }.items():
        target=OUT/name;tmp=target.with_suffix('.tmp');tmp.write_text(text,encoding='utf-8');os.replace(tmp,target)

if __name__=='__main__':main()

