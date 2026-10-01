"""Record real-date prospective vectors and verify frozen historical replay bytes."""
import hashlib,importlib.util,json,tempfile,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from workbench_analysis.source_authority_governance_r1 import evaluate_consumer_gate
P='reports/audits/A10_A12_R3_'
def main():
    spec=importlib.util.spec_from_file_location('vectors',ROOT/'tests/v4_a10_a12_r3/test_producer_instances.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    vectors=[]
    with tempfile.TemporaryDirectory(prefix='producer_instance_r3_') as directory:
        root=Path(directory);config,manifest=module.install(root)
        for target in ('2026-09-28','2026-09-29','2026-09-30'):
            for rule in config['field_rules']:
                if rule['field_id'] not in ('TRADING_STATUS','ISST'):continue
                result=evaluate_consumer_gate(rule,project_root=root,consumer_contract_id=module.CONSUMER,
                    target_trade_date=target,availability='AVAILABLE',required=True,
                    source_instance_binding=manifest['instances'].get(target,{}).get(rule['field_id']))
                assert result['formal_authority_authorized']==(target!='2026-09-29')
                vectors.append(dict(target=target,field=rule['field_id'],status=result['status'],
                    reason=result['owner_acceptance_reason'],authorized=result['formal_authority_authorized']))
    checked={};representations=[]
    def visit(value):
        if isinstance(value,dict):
            if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):
                p=value['path']
                if p not in checked:
                    actual=bind(p)['sha256']
                    if actual!=value['sha256']:
                        data=(ROOT/p).read_bytes()
                        if Path(p).suffix in ('.json','.md','.txt','.py') and hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()==value['sha256']:
                            representations.append(dict(path=p,working_sha256=actual,receipt_sha256=value['sha256'],difference='PRE_EXISTING_CRLF_LF_ONLY'))
                        else:
                            if p in ('scripts/seal_source_authority_metadata_r1.py','scripts/verify_source_authority_clean_r1.py','src/workbench_analysis/dm01_source_boundary_r2.py','src/workbench_analysis/source_authority_governance_r1.py'):
                                historical=subprocess.check_output(['git','show','a43d663:'+p],cwd=ROOT)
                                assert hashlib.sha256(historical).hexdigest()==value['sha256']
                                representations.append(dict(path=p,working_sha256=actual,receipt_sha256=value['sha256'],difference='R3_ADDITIVE_VERSION_DISPATCH_OLD_EXECUTED_SOURCE_RETAINED_IN_a43d663'))
                                checked[p]=value['sha256']
                                return
                            assert p in ('scripts/capture_a12_r2_empty_return_semantics.py','scripts/capture_a12_r2_semantics_revision.py','scripts/freeze_a12_r2_real_source_authority.py','scripts/verify_a12_r2_real_source_oracle.py'),(p,actual,value['sha256'])
                            historical=subprocess.check_output(['git','show','2b76767:'+p],cwd=ROOT)
                            current=subprocess.check_output(['git','show','a43d663:'+p],cwd=ROOT)
                            assert hashlib.sha256(historical).hexdigest()==value['sha256'] and current.replace(b'\r\n',b'\n')==data.replace(b'\r\n',b'\n')
                            representations.append(dict(path=p,working_sha256=actual,receipt_sha256=value['sha256'],difference='EXECUTED_PRE_NOSYMBOL_REPAIR_SOURCE_RETAINED_IN_2b76767',disposition=bind('reports/audits/A12_R2_NOSYMBOL_REPAIR_DISPOSITION_R1.json')))
                    checked[p]=value['sha256']
                    if p.endswith('.json') and p.startswith(('reports/audits/A12_R2_','reports/audits/a12_')):
                        visit(json.loads((ROOT/p).read_text(encoding='utf8')))
            for v in value.values():visit(v)
        elif isinstance(value,list):
            for v in value:visit(v)
    visit(json.loads((ROOT/'reports/audits/A12_R2_CANDIDATE_EVIDENCE_MANIFEST_R1.json').read_text(encoding='utf8')))
    atomic_json(ROOT/(P+'REAL_DATE_GLOBAL_GATE_AND_HISTORICAL_PROTECTION_R1.json'),dict(
        status='PASS',producer_acceptance='PROSPECTIVE_TEMPORARY_FIXTURE_ONLY_NOT_ACTUAL_DAILY_REGISTRATION',
        source_instances=bind(P+'SOURCE_INSTANCE_MANIFEST_R1.json'),vectors=vectors,
        candidate_fact_called=False,global_gate_independently_blocks_missing_day=True,
        network_calls=0,historical_replay_bindings_verified=checked,
        historical_business_replay_bytes_unchanged=True,preexisting_metadata_representation_differences=representations,dm01_all_nine_accepted=False))
    print(json.dumps(dict(status='PASS',vectors=len(vectors),historical_bindings=len(checked))))
if __name__=='__main__':main()

