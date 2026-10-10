"""Explain the unchanged previous-Head gate; never issue Identity authority."""
CONTRACT = 'NEXT_T0_OLD_HEAD_IDENTITY_PREFLIGHT_V1'


def diagnose(*, trade_date, previous_date, expected_codes, actual_codes,
             source_binding, parent_head, identity_binding, membership_binding,
             native_reconciled, requested_at, received_at, first_available_at):
    expected, actual = set(expected_codes), set(actual_codes)
    missing, added = sorted(expected-actual), sorted(actual-expected)
    return dict(contract_id=CONTRACT, target_session=trade_date,
        prior_identity_date=previous_date, parent_head=parent_head,
        prior_identity=identity_binding, prior_membership=membership_binding,
        original_source=source_binding, requested_at=requested_at,
        received_at=received_at, first_available_at=first_available_at,
        native_tdx_baostock_reconciliation_passed=bool(native_reconciled),
        old_identity_scope_matches=not (missing or added),
        missing_previous_codes=missing, added_observed_codes=added,
        diagnosis=('PREVIOUS_HEAD_IDENTITY_SCOPE_MISMATCH' if missing or added
                   else 'PREVIOUS_HEAD_IDENTITY_SCOPE_MATCH'),
        provider_availability=('NATIVE_BYTES_CAPTURED_RECONCILED' if native_reconciled
                               else 'NATIVE_RECONCILIATION_UNPROVEN'),
        main_dd_gate_policy='UNCHANGED_PREVIOUS_ACCEPTED_IDENTITY_REQUIRED',
        identity_authority_candidate=dict(target_session=trade_date,
            observed_source_codes=sorted(actual), original_source=source_binding,
            status='REQUIRES_SAME_DAY_IDENTITY_OWNER_REVIEW',
            eligible_as_authority=False,
            source_gaps=['SAME_DAY_IDENTITY_OWNER_NOT_ISSUED',
                         'SAME_DAY_MEMBERSHIP_AUTHORITY_NOT_PROVEN']),
        source_bytes_preserved=True, production=False, PIT_ELIGIBLE=False,
        formal_consumer_enabled=False, external_acceptance='NOT_GRANTED')
