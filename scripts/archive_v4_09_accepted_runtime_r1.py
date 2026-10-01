"""Preserve accepted implementation bytes independently from current candidate code."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json,atomic_bytes
from scripts.enter_source_authority_remediation_r2 import bind
AUDITED='981332582c1982d9da3af922688e682946822119'

def main():
    head=json.loads((ROOT/'data/v4/V4_09_ACCEPTED_HEAD.json').read_text(encoding='utf8'));bindings={}
    for source in ['src/v4/stock_prewatch.py','src/v4/stock_prewatch_persistence.py']:
        expected=head['evidence_bindings'][source]
        payload=subprocess.check_output(['git','show',AUDITED+':'+source],cwd=ROOT)
        assert hashlib.sha256(payload).hexdigest()==expected['sha256'] and len(payload)==expected['byte_count']
        archive='docs/evidence/cross_stage/runtime_archives/V4_09_R1_1/'+Path(source).name+'.txt'
        if (ROOT/archive).exists():assert (ROOT/archive).read_bytes()==payload
        atomic_bytes(ROOT/archive,payload);bindings[source]=dict(accepted_source=expected,archive=bind(archive))
    atomic_json(ROOT/'config/v4_09_historical_runtime_archive_r1.json',dict(contract_id='V4_09_ACCEPTED_RUNTIME_HISTORICAL_ARCHIVE_R1',audited_commit=AUDITED,scope='ACCEPTED_PUBLICATION_HISTORY_ONLY',bindings=bindings,current_candidate_runtime_accepted=False,does_not_grant_new_promotion_or_runtime_acceptance=True))

if __name__=='__main__':main()
