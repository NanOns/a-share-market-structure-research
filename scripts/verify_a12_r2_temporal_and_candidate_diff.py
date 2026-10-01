"""R1-to-R2 full business restoration and candidate availability classification."""
import json,sys,gzip
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.complete_a12_cascade_r1 import diff,rows
P='reports/audits/A12_R2_'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def main():
    old=read('reports/audits/A12_DOWNSTREAM_CASCADE_AND_FULL_BUSINESS_DIFF_R1.json')['stages'];new=read(P+'DOWNSTREAM_CASCADE_AND_FULL_BUSINESS_DIFF_R1.json')['stages'];pairs={}
    pairs['V4_03']=('reports/audits/a12_v4_03_r1/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz','reports/audits/a12_v4_03_r2/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz')
    pairs['V4_04']=(read('reports/audits/A12_V4_04_TRUE_REPLAY_R1.json')['artifact']['path'],read(P+'V4_04_TRUE_REPLAY_R1.json')['artifact']['path'])
    for k in ['V4_07','V4_09']:pairs[k]=(old[k]['artifact']['path'],new[k]['artifact']['path'])
    for k in ['core','factors']:pairs['V4_05_'+k]=(old['V4_05']['artifacts'][k]['path'],new['V4_05']['artifacts'][k]['path'])
    changes={k:dict(old=bind(a),candidate=bind(b),diff=diff(rows(a),rows(b))) for k,(a,b) in pairs.items()}
    for k in ['B0','B2','ROTATION','SECTOR_NATIVE']:
        a=old['V4_08']['outputs'][k]['artifact']['path'];b=new['V4_08']['outputs'][k]['artifact']['path'];changes['V4_08_'+k]=dict(old=bind(a),candidate=bind(b),diff=diff(rows(a),rows(b),key='sector_id'))
    temporal=[]
    for k in ['V4_07','V4_09']:
        path=new[k]['artifact']['path'];rs=rows(path)
        assert all(r.get('formal_publication') is not True for r in rs)
        temporal.append(dict(stage=k,artifact=bind(path),formal_publication=False,scope='Recomputed candidate available now, old input publication metadata retained only as input provenance'))
    corepath=new['V4_05']['artifacts']['core']['path'];core=rows(corepath)
    assert all(r['formal_publication'] is False and r['first_availability_at_target_proven'] is False and r['lineage']=='RECONSTRUCTED_CORRECTED' for r in core)
    assert all(datetime.fromisoformat(r['formal_publication_at']).date().isoformat()=='2026-10-01' for r in core)
    # Raw unchanged kernel intermediates can carry the original accepted-input publication timestamps.
    # They are quarantined by this binding and never authorize formal publication or at-target knowledge.
    raw=[bind(p.relative_to(ROOT).as_posix()) for d in ['reports/audits/a12_v4_03_r2','reports/audits/a12_v4_05_r2'] for p in (ROOT/d).rglob('*') if p.is_file()]
    atomic_json(ROOT/(P+'TEMPORAL_AND_R1_RESTORATION_PROOF_R1.json'),dict(status='PASS_CANDIDATE_TEMPORAL_BOUNDARY_AND_FULL_BUSINESS_DIFF',r1_to_r2=changes,normalized_core=bind(corepath),normalized_core_first_availability_at_target_proven=False,final_candidate_temporal_bindings=temporal,unchanged_kernel_intermediates=raw,intermediate_metadata_role='Original formal_publication_at/available_at are inherited accepted INPUT timestamps, not corrected candidate publication or first availability. Raw candidate intermediates are unpublished; only explicitly normalized cascade rows represent candidate availability.',candidate_knowledge_lineage='RECONSTRUCTED_CORRECTED',allowed_historical_mode='TARGET_DATE_QUERYABLE_FACT',formal_publication=False,owner_registration=False,external_acceptance=None))
    print('PASS_R1_TO_R2_BUSINESS_RESTORATION',{k:v['diff']['security_rows_changed'] for k,v in changes.items()})
if __name__=='__main__':main()
