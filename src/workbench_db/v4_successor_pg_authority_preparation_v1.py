"""Prepare the complete PG authority set before publishing a successor Head."""

CONTRACT = 'V4_SUCCESSOR_PG_AUTHORITY_PREPARATION_R1'


def prepare_remaining(root, candidate):
    """Prepare predecessor, registry and daily evidence on a bound Head.

    Owner and membership authority are prepared by the exact-policy candidate
    builder. This completion step runs at publication immediately before the
    final candidate validation and pointer CAS.
    """
    from .v4_operational_predecessor_pg_v1 import KEY as PREDECESSOR_KEY, prepare as prepare_predecessor, read as read_predecessor
    from .v4_operational_registry_pg_v1 import KEY as REGISTRY_KEY, prepare as prepare_registry, read as read_registry
    from .v4_operational_daily_evidence_pg_v1 import KEY as EVIDENCE_KEY, prepare as prepare_daily_evidence, read as read_daily_evidence, DOCUMENTS

    predecessor = (read_predecessor(root, candidate) and dict(reused=True, publication=False)
        if PREDECESSOR_KEY in candidate else prepare_predecessor(root, candidate))
    registry = (read_registry(root, candidate) and dict(reused=True, publication=False)
        if REGISTRY_KEY in candidate else prepare_registry(root, candidate))
    if EVIDENCE_KEY in candidate:
        for name in DOCUMENTS:
            read_daily_evidence(root, candidate, name)
        daily_evidence = dict(reused=True, publication=False)
    else:
        daily_evidence = prepare_daily_evidence(root, candidate)
    return dict(contract_id=CONTRACT, T0=candidate['accepted_trade_date'],
        predecessor=predecessor, registry=registry, daily_evidence=daily_evidence,
        publication=False)
