"""Register exact scoped external decisions, creating only new producer records."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from v4.rps_pit_history_a02_v1 import binding,read_bound,immutable_json
from v4.a02_a05_external_acceptance_r1 import AUDIT_PATH,BASELINE,validate_authority,RPS_HEAD,A05_RECORD

def main():
    authority=binding(ROOT,ROOT/AUDIT_PATH)
    validate_authority(ROOT,authority,'PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE')
    entry_path=ROOT/'reports/next_round_r2/BATCH_STAGE_ENTRY_R1.json'
    entry=json.loads(entry_path.read_bytes());timestamp=entry['observed_at_utc']
    rps_proof=json.loads((ROOT/'reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R3.json').read_bytes())
    for day,ref in rps_proof['publications'].items():
        publication=read_bound(ROOT,ref)
        if publication['trade_date']!=day or publication['AS_RECORDED'] is not False: raise ValueError('A02_PUBLICATION_SCOPE')
    rps_record=dict(contract_id='A02_EXTERNAL_ACCEPTANCE_RECORD_V1',status='PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE',audited_head=BASELINE,external_authority=authority,formalized_at=timestamp,accepted_dates=sorted(rps_proof['publications']),publications=rps_proof['publications'],inputs=rps_proof['inputs'],deltas=rps_proof['deltas'],accepted_contracts=[binding(ROOT,ROOT/'config/a02_rps_pit_history_v1.json'),binding(ROOT,ROOT/'config/a02_history_publication_reader_producer_r2.json')],producer_evidence=binding(ROOT,ROOT/'reports/audits/A02_RPS_HISTORY_BOOTSTRAP_EVIDENCE_R3.json'),knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,historical_first_availability_proven=False,downstream_amendments_accepted=False,production=False,shadow=False,focus=False,global_mandatory_adoption=False)
    record_path=ROOT/'reports/audits/next_round_r2/A02_EXTERNAL_ACCEPTANCE_RECORD_R1.json';immutable_json(record_path,rps_record)
    head=dict(contract_id='V4_RPS_PIT_HISTORY_ACCEPTED_HEAD_R1',version='1.0.0',status='EXTERNALLY_ACCEPTED_SCOPED_PRODUCER',audited_head=BASELINE,external_authority=authority,acceptance_record=binding(ROOT,record_path),accepted_dates=rps_record['accepted_dates'],publications=rps_record['publications'],knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,historical_first_availability_proven=False,does_not_promote_Data_Head=True,does_not_promote_Stage_Head=True,downstream_amendments_accepted=False,production=False,shadow=False,focus=False,global_mandatory_adoption=False)
    immutable_json(ROOT/RPS_HEAD,head)
    validate_authority(ROOT,authority,'PASS_EXACT_CURRENT_SNAPSHOT_PRODUCER_SCOPE')
    old=json.loads((ROOT/'reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R2.json').read_bytes())
    cfg=json.loads((ROOT/'config/a05_legacy_valid_member_exact_v1.json').read_bytes());data=read_bound(ROOT,old['input_binding'])
    a05=dict(contract_id='A05_EXTERNAL_ACCEPTANCE_RECORD_V1',status='PASS_EXACT_CURRENT_SNAPSHOT_PRODUCER_SCOPE',audited_head=BASELINE,external_authority=authority,formalized_at=timestamp,source=cfg['source'],symbol='sector.phase2.prepare',exact_AST_digest=cfg['exact_ast_digest'],contract=binding(ROOT,ROOT/'config/a05_legacy_valid_member_exact_v1.json'),producer=binding(ROOT,ROOT/'src/sector/legacy_valid_member_a05_v1.py'),real_observations=old['input_binding'],real_observation_count=6188,legacy_sector_count=541,real_mismatch_count=0,accepted_snapshot_trade_date=data['trade_date'],accepted_time_role='CURRENT_SNAPSHOT_ONLY',historical_PIT_equivalent=False,AS_RECORDED=False,historical_membership_acceptance=False,producer_evidence=binding(ROOT,ROOT/'reports/audits/A05_EXACT_RECOVERY_EVIDENCE_R2.json'),V4_08_business_head_amendment_accepted=False,production=False,shadow=False,focus=False,global_mandatory_adoption=False)
    immutable_json(ROOT/A05_RECORD,a05)
    print(json.dumps(dict(A02_EXTERNAL_ACCEPTANCE_FORMALIZED='PASS',A05_EXTERNAL_ACCEPTANCE_FORMALIZED='PASS',accepted_RPS_head=RPS_HEAD,A05_record=A05_RECORD)))
if __name__=='__main__': main()
