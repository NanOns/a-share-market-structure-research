"""Contract regressions for D0 cutoff and exact publication identity."""
from datetime import datetime
import hashlib

from workbench_analysis.d0_source_seal_r1 import (
    d0_publication_matches_contract, evaluate_d0_source_seal,
)
from workbench_analysis.d0_source_seal_r2 import classify_source, same_cutoff_source_eligible

TRADE_DATE='2026-10-15'
TOKEN='dev-token-2026-10-15'


def test_exact_d0_publication_identity_and_reader_version_are_required():
    row=dict(trade_date=TRADE_DATE,candidate_token=TOKEN,
        producer_contract_id='V4_D0_SOURCE_SEAL_SUCCESSOR_R2',producer_version='2.0.0')
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
    candidate={'AS_RECORDED':True,'PIT_ELIGIBLE':True}
    cutoff=datetime.fromisoformat('2026-10-22T17:00:00+08:00')
    args=dict(evidence_class='CAPTURED_AS_RECORDED',time_role='SAME_DAY_SOURCE_CAPTURE',
        available_at='2026-10-22T16:40:00+08:00',cutoff=cutoff,
        membership_observed_at='2026-10-22T16:42:00+08:00')
    assert same_cutoff_source_eligible(candidate,**args)
    assert not same_cutoff_source_eligible(candidate,**{**args,'available_at':'2026-10-22T17:00:01+08:00'})
    assert not same_cutoff_source_eligible(candidate,**{**args,'time_role':'POST_CLOSE_LATE_CAPTURE'})


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
    pg=dict(source_ingress=dict(receipts=[dict(trade_date=TRADE_DATE,time_role='SAME_DAY_CAPTURE',
        evidence_class='CAPTURED_AS_RECORDED',available_at='2026-10-21T12:00:01+00:00',
        byte_readback=dict(status='PASS'))]),d0_owner_publication={})
    result=evaluate_d0_source_seal(root=tmp_path,evidence=evidence,scenario='LAUNCH_CONFIRM',
        predicate_state='UNKNOWN',pg_readback=pg)
    assert result['seal_state']=='POST_HOC_AFTER_CUTOFF'
    assert result['predicate_state']=='UNKNOWN'
