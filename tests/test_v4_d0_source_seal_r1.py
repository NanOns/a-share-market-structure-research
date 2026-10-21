import hashlib

from workbench_analysis.d0_source_seal_r1 import (
    _observed_timezone, candidate_publication_token_matches, evaluate_d0_source_seal,
)


ROLES = [
    'RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW', 'CORE_AND_RELATIVE_STRENGTH_FACTS',
    'OFFICIAL_MASTER_SESSION_CALENDAR', 'FROZEN_D0_SCANNER_AND_THRESHOLDS',
    'TARGET_FACT_PRODUCER', 'SCENARIO_DETECTOR', 'D0_SOURCE_SEAL_CONTRACT',
    'D0_PRODUCER_PARAMETERS',
]


def evidence_tree(tmp_path, *, cutoff='2026-10-22T08:00:00+00:00'):
    refs=[]
    for i,role in enumerate(ROLES):
        raw=f'source-{i}'.encode()
        name=f'{i}.bin'
        (tmp_path/name).write_bytes(raw)
        refs.append(dict(role=role,path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
    return dict(source_refs=refs,cutoff_status='CUTOFF_CONTRACT_RESOLVED',
        knowledge_cutoff=cutoff,trade_date='2026-10-22')


def pg_receipt(*, available='2026-10-22T07:55:00+00:00', evidence_class='CAPTURED_AS_RECORDED'):
    return dict(source_ingress=dict(receipts=[dict(available_at=available,time_role='AS_OF_T0',
        evidence_class=evidence_class,byte_readback=dict(status='PASS'))]),
        d0_owner_publication=dict(status='PG_BINDING_MISSING',permission_chain_proven=False,
            consumed_source_rows=[]))


def seal(tmp_path, evidence, pg):
    return evaluate_d0_source_seal(root=tmp_path,evidence=evidence,scenario='LAUNCH_CONFIRM',
        predicate_state='FALSE',pg_readback=pg)


def test_formal_d0_seal_positive_requires_exact_inputs_clock_and_pg_permission(tmp_path):
    evidence=evidence_tree(tmp_path)
    pg=pg_receipt()
    required={r['sha256'] for r in evidence['source_refs'] if r['role'] in (
        'RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW','CORE_AND_RELATIVE_STRENGTH_FACTS')}
    pg['d0_owner_publication'].update(status='PG_BINDING_PRESENT',permission_chain_proven=True,
        consumed_source_rows=[dict(digest=d) for d in required])
    result=seal(tmp_path,evidence,pg)
    assert result['seal_state']=='VERIFIED_BY_CUTOFF'
    assert result['admission']=='DEV_SOURCE_VERIFIED'
    assert result['predicate_state']=='FALSE'
    assert result['production_admission'] is False


def test_reconstructed_or_late_source_is_rejected_even_with_pg_owner(tmp_path):
    evidence=evidence_tree(tmp_path,cutoff='2026-10-22T08:00:00+00:00')
    pg=pg_receipt(available='2026-10-22T08:00:01+00:00',evidence_class='RECONSTRUCTED_NON_PIT')
    pg['d0_owner_publication'].update(status='PG_BINDING_PRESENT',permission_chain_proven=True)
    result=seal(tmp_path,evidence,pg)
    assert result['seal_state']=='POST_HOC_AFTER_CUTOFF'
    assert result['admission']=='NOT_ADMITTED'


def test_actual_source_bytes_are_rehashed_before_permission_evaluation(tmp_path):
    evidence=evidence_tree(tmp_path)
    (tmp_path/evidence['source_refs'][0]['path']).write_bytes(b'tampered')
    result=seal(tmp_path,evidence,pg_receipt())
    assert result['seal_state']=='SOURCE_DIGEST_MISMATCH'
    assert result['mismatched_source_role']=='RAW_AND_TDX_NATIVE_QFQ_PRICE_WINDOW'


def test_missing_pg_owner_publication_and_permission_chain_fail_closed(tmp_path):
    evidence=evidence_tree(tmp_path)
    result=seal(tmp_path,evidence,pg_receipt())
    assert result['seal_state']=='PG_BINDING_MISSING'
    assert result['admission']=='NOT_ADMITTED'


def test_unresolved_cutoff_does_not_infer_t0_end_of_day(tmp_path):
    evidence=evidence_tree(tmp_path)
    evidence.update(cutoff_status='CUTOFF_CONTRACT_UNRESOLVED',knowledge_cutoff=None)
    result=seal(tmp_path,evidence,pg_receipt())
    assert result['seal_state']=='CUTOFF_CONTRACT_UNRESOLVED'
    assert result['admission']=='NOT_ADMITTED'


def test_diagnostic_scenarios_never_enter_formal_d0_seal(tmp_path):
    result=evaluate_d0_source_seal(root=tmp_path,evidence={},scenario='TREND_CONTINUE',
        predicate_state='UNKNOWN',pg_readback={})
    assert result['seal_state']=='DIAGNOSTIC_ONLY'
    assert result['admission']=='DEV_DIAGNOSTIC'


def test_caller_hash_boolean_and_fake_permission_chain_cannot_supply_source_binding(tmp_path):
    result=evaluate_d0_source_seal(root=tmp_path,evidence={'source_sha256':'a'*64,
        'permission_chain_proven':True,'chain_sha256':'b'*64},scenario='RECOVERY_TURN',
        predicate_state='FALSE',pg_readback={})
    assert result['seal_state']=='SOURCE_MISSING'
    assert result['admission']=='NOT_ADMITTED'


def test_wrong_pg_candidate_publication_token_does_not_bind_same_date():
    observed=dict(candidate_token='wrong-token',trade_date='2026-10-22')
    assert not candidate_publication_token_matches('expected-token',observed,'2026-10-22')
    assert not candidate_publication_token_matches('expected-token',
        dict(candidate_token='expected-token',trade_date='2026-10-21'),'2026-10-22')


def test_source_receipt_from_another_t0_is_rejected(tmp_path):
    evidence=evidence_tree(tmp_path)
    pg=pg_receipt()
    pg['source_ingress']['receipts'][0]['trade_date']='2026-10-21'
    result=seal(tmp_path,evidence,pg)
    assert result['seal_state']=='PG_BINDING_MISSING'
    assert result['reason']=='PG_SOURCE_RECEIPT_T0_MISMATCH'


def test_future_window_trade_date_and_wrong_price_coordinate_are_rejected(tmp_path):
    evidence=evidence_tree(tmp_path)
    evidence['source_max_trade_date']='2026-10-23'
    pg=pg_receipt()
    pg['source_ingress']['receipts'][0]['max_source_trade_date']='2026-10-23'
    result=seal(tmp_path,evidence,pg)
    assert result['seal_state']=='PG_BINDING_MISSING'
    assert result['reason']=='PG_SOURCE_WINDOW_CONTAINS_FUTURE_TRADE_DATE'
    del pg['source_ingress']['receipts'][0]['max_source_trade_date']
    evidence['source_max_trade_date']='2026-10-22'
    evidence['price_coordinate']='RAW_WHEN_TDX_NATIVE_QFQ_REQUIRED'
    result=seal(tmp_path,evidence,pg)
    assert result['seal_state']=='SOURCE_DIGEST_MISMATCH'
    assert result['reason']=='D0_PRICE_COORDINATE_MISMATCH'


def test_timezone_missing_and_reconstructed_as_recorded_claim_fail_closed(tmp_path):
    evidence=evidence_tree(tmp_path)
    pg=pg_receipt(available='2026-10-22T07:55:00',evidence_class='CAPTURED_AS_RECORDED')
    result=seal(tmp_path,evidence,pg)
    assert result['seal_state']=='PG_BINDING_MISSING'
    assert result['reason']=='PG_SOURCE_INGRESS_CLOCK_OR_TIMEZONE_MISSING'
    pg=pg_receipt(available='2026-10-22T07:55:00+00:00',evidence_class='RECONSTRUCTED_NON_PIT')
    result=seal(tmp_path,evidence,pg)
    assert result['seal_state']=='POST_HOC_AFTER_CUTOFF'
    assert result['admission']=='NOT_ADMITTED'


def test_observation_timezone_comes_from_timestamp_not_a_hardcoded_zone():
    assert _observed_timezone('2026-10-21T22:25:53.506409+08:00')=='+0800'
    assert _observed_timezone('2026-10-21T14:25:53.506409Z')=='UTC'
    assert _observed_timezone('2026-10-21T14:25:53.506409') is None
