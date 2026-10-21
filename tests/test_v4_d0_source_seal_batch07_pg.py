"""Contract regressions for D0 cutoff and exact publication identity."""
from datetime import datetime
import hashlib
import json

from workbench_analysis.d0_source_seal_r1 import (
    d0_publication_matches_contract, evaluate_d0_source_seal,
)
from workbench_analysis.d0_source_seal_r2 import (
    _exact_source_ingress, classify_source, same_cutoff_source_eligible,
)

TRADE_DATE='2026-10-15'
TOKEN='dev-token-2026-10-15'


def test_exact_d0_publication_identity_and_reader_version_are_required():
    row=dict(trade_date=TRADE_DATE,candidate_token=TOKEN,
        producer_contract_id='V4_D0_SOURCE_SEAL_SUCCESSOR_R2',producer_version='2.1.0')
    assert d0_publication_matches_contract(row,TRADE_DATE,TOKEN)
    assert not d0_publication_matches_contract(row,'2026-10-14',TOKEN)
    assert not d0_publication_matches_contract(row,TRADE_DATE,'0'*64)
    assert not d0_publication_matches_contract({**row,'producer_version':'99.0.0'},TRADE_DATE,TOKEN)


def test_post_cutoff_source_is_reconstructed_after_cutoff():
    source=dict(time_role='SAME_DAY_CAPTURE',available_at='2026-10-21T12:00:01+00:00',
        evidence_class='CAPTURED_AS_RECORDED')
    assert classify_source(source,datetime.fromisoformat('2026-10-21T12:00:00+00:00'))=='RECONSTRUCTED_AFTER_CUTOFF'


def test_later_reconstructed_source_before_replay_freeze_stays_non_pit():
    source=dict(time_role='RECONSTRUCTED_FROM_LATER_PACKAGE',available_at='2026-10-21T11:59:00+00:00',
        evidence_class='RECONSTRUCTED_NON_PIT')
    assert classify_source(source,datetime.fromisoformat('2026-10-21T12:00:00+00:00'))=='RECONSTRUCTED_NON_PIT'


def test_next_real_same_cutoff_capture_can_be_dev_pit_verified():
    candidate={'AS_RECORDED':False,'PIT_ELIGIBLE':False,'historical_PIT_permission':False}
    cutoff=datetime.fromisoformat('2026-10-22T17:00:00+08:00')
    args=dict(evidence_class='CAPTURED_AS_RECORDED',time_role='SAME_DAY_SOURCE_CAPTURE',
        available_at='2026-10-22T16:40:00+08:00',cutoff=cutoff,
        membership_observed_at='2026-10-22T16:42:00+08:00',membership_trade_date='2026-10-22',
        source_package_date='2026-10-22',trade_date='2026-10-22')
    proof=dict(candidate_validated=True,exact_source_binding=True)
    assert same_cutoff_source_eligible(candidate,**args,**proof)
    assert not same_cutoff_source_eligible(candidate,**{**args,'available_at':'2026-10-22T17:00:01+08:00'},**proof)
    assert not same_cutoff_source_eligible(candidate,**{**args,'time_role':'POST_CLOSE_LATE_CAPTURE'},**proof)
    assert not same_cutoff_source_eligible({**candidate,'PIT_ELIGIBLE':True},**args,**proof)
    assert not same_cutoff_source_eligible(candidate,**args,**{**proof,'exact_source_binding':False})


def test_fake_source_digest_fails_closed_before_binding_claim(tmp_path):
    raw=b'actual source bytes'
    path=tmp_path/'source.bin'
    path.write_bytes(raw)
    evidence=dict(trade_date=TRADE_DATE,candidate_token=TOKEN,
        cutoff_status='CUTOFF_CONTRACT_RESOLVED',knowledge_cutoff='2026-10-21T12:00:00+00:00',
        source_refs=[dict(role=role,path='source.bin',sha256='0'*64,bytes=len(raw)) for role in (
            'RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW','CORE_AND_RELATIVE_STRENGTH_FACTS',
            'FROZEN_D0_SCANNER_AND_THRESHOLDS','TARGET_FACT_PRODUCER','SCENARIO_DETECTOR',
            'D0_SOURCE_SEAL_CONTRACT','D0_PRODUCER_PARAMETERS')])
    result=evaluate_d0_source_seal(root=tmp_path,evidence=evidence,scenario='LAUNCH_CONFIRM',
        predicate_state='UNKNOWN',pg_readback={})
    assert result['seal_state']=='SOURCE_DIGEST_MISMATCH'
    assert result['mismatched_source_role']=='RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW'


def test_late_source_counterexample_keeps_predicate_state(tmp_path):
    refs=[]
    for i,role in enumerate(('RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW','CORE_AND_RELATIVE_STRENGTH_FACTS',
        'FROZEN_D0_SCANNER_AND_THRESHOLDS','TARGET_FACT_PRODUCER','SCENARIO_DETECTOR',
        'D0_SOURCE_SEAL_CONTRACT','D0_PRODUCER_PARAMETERS')):
        raw=('source-'+str(i)).encode();(tmp_path/f'{i}.bin').write_bytes(raw)
        refs.append(dict(role=role,path=f'{i}.bin',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
    evidence=dict(trade_date=TRADE_DATE,candidate_token=TOKEN,cutoff_status='CUTOFF_CONTRACT_RESOLVED',
        knowledge_cutoff='2026-10-21T12:00:00+00:00',source_refs=refs)
    package_sha='a'*64;artifact_sha='b'*64;source_freeze='f'*64;artifact_bytes=17
    available='2026-10-21T12:00:01+00:00'
    pg=dict(source_ingress=dict(receipts=[dict(trade_date=TRADE_DATE,source_sha256=package_sha,
        package_date=TRADE_DATE,artifact_sha256=artifact_sha,artifact_bytes=artifact_bytes,
        artifact_path='source.bin',time_role='SAME_DAY_CAPTURE',evidence_class='CAPTURED_AS_RECORDED',
        available_at=available,byte_readback=dict(status='PASS'))],candidate_source_binding=dict(
            status='EXACT_MATCH',match_count=1,candidate_token=TOKEN,trade_date=TRADE_DATE,
            source_freeze_sha256=source_freeze,package_sha256=package_sha,
            artifact_sha256=artifact_sha,artifact_bytes=artifact_bytes)),
        candidate_publication=dict(rows=[dict(candidate_token=TOKEN,trade_date=TRADE_DATE,
            source_freeze_sha256=source_freeze)]),
        d0_owner_publication=dict(batch07_publications=[dict(candidate_token=TOKEN,trade_date=TRADE_DATE,
            source_freeze_sha256=source_freeze)],batch07_consumed_sources=[dict(
                source_role='TDX_SOURCE_INGRESS_ARTIFACT',owner_version_token=package_sha,
                source_ingress_artifact_sha256=artifact_sha,source_bytes=artifact_bytes)],
            status='PG_BINDING_MISSING',permission_chain_proven=False))
    result=evaluate_d0_source_seal(root=tmp_path,evidence=evidence,scenario='LAUNCH_CONFIRM',
        predicate_state='UNKNOWN',pg_readback=pg)
    assert result['seal_state']=='POST_HOC_AFTER_CUTOFF'
    assert result['predicate_state']=='UNKNOWN'


class _ReceiptLookup:
    def __init__(self,rows):self.rows=rows;self.params=None
    def execute(self,query,params):
        self.params=params
        assert 'AND source_sha256=%s' in query
        return self
    def fetchall(self):
        return [row for row in self.rows if row[1]==self.params[1]]


def _freeze_candidate(tmp_path):
    artifact=tmp_path/'ingress.json';artifact.write_bytes(b'bound real source bytes')
    package_sha='a'*64
    freeze={'target_session':TRADE_DATE,'effective_package':{'contract_id':'TDX_CONTRACT','provider_package_date':TRADE_DATE,
        'download':{'sha256':package_sha,'target_date':TRADE_DATE}}}
    raw=json.dumps(freeze,separators=(',',':')).encode();freeze_path=tmp_path/'freeze.json';freeze_path.write_bytes(raw)
    binding={'path':'freeze.json','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    candidate={'source_registry':{TRADE_DATE:{'freeze':binding}}}
    receipt=('TDX_CONTRACT',package_sha,TRADE_DATE,'2026-10-21T17:35:26+08:00','CAPTURED_AS_RECORDED',
        'CAPTURED_AS_RECORDED',str(artifact),hashlib.sha256(artifact.read_bytes()).hexdigest(),
        artifact.stat().st_size,'2026-10-21T17:44:42+08:00')
    return candidate,binding,receipt


def test_source_ingress_joins_candidate_freeze_not_latest_receipt(tmp_path):
    candidate,binding,exact=_freeze_candidate(tmp_path)
    newer=('TDX_CONTRACT','b'*64,*exact[2:])
    pg=_ReceiptLookup([newer,exact])
    freeze,receipt=_exact_source_ingress(pg,tmp_path,candidate,TRADE_DATE,binding['sha256'])
    assert receipt==exact
    assert freeze['target_session']==TRADE_DATE
    assert pg.params==(datetime.fromisoformat(TRADE_DATE).date(), 'a'*64)


def test_duplicate_exact_ingress_receipts_fail_closed(tmp_path):
    candidate,binding,exact=_freeze_candidate(tmp_path)
    duplicate=(*exact[:2],exact[2],exact[3],exact[4],exact[5],exact[6],exact[7],exact[8])
    pg=_ReceiptLookup([exact,duplicate])
    try:
        _exact_source_ingress(pg,tmp_path,candidate,TRADE_DATE,binding['sha256'])
    except ValueError as exc:
        assert str(exc)=='D0_EXACT_SOURCE_INGRESS_MATCH_COUNT:2'
    else:
        raise AssertionError('duplicate exact receipt was accepted')
