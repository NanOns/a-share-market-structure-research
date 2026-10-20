"""Prepare the complete PG authority set before publishing a successor Head."""
import json

from workbench_analysis.r43_owner_replay import checked

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
    from .v4_operational_period_artifact_pg_v1 import KEY as PERIOD_ARTIFACT_KEY, prepare as prepare_period_artifacts, attest as attest_period_artifact, ARTIFACTS
    from workbench_service.native_product_catalog_v3 import KEY as PRODUCT_KEY, PG_KEY as PRODUCT_PG_KEY, prepare_pg as prepare_product_pg, load as load_product_catalog

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
    if PERIOD_ARTIFACT_KEY in candidate:
        period = read_daily_evidence(root, candidate, 'period_numeric_oracle')
        for name in ARTIFACTS:
            attest_period_artifact(root, candidate, name, period[name])
        period_artifacts = dict(reused=True, publication=False)
    else:
        period_artifacts = prepare_period_artifacts(root, candidate)
    if PRODUCT_KEY in candidate:
        if PRODUCT_PG_KEY in candidate:
            product_catalog = load_product_catalog(root, candidate)
            product_receipt = dict(reused=True, publication=False)
        else:
            product_authority = json.loads(checked(root, candidate[PRODUCT_KEY]).read_bytes())
            product_receipt = prepare_product_pg(root, candidate, product_authority)
            product_catalog = load_product_catalog(root, candidate)
        if set(product_catalog['dates']) != set(candidate['published_sessions']):
            raise ValueError('PRODUCT_PG_CATALOG_DATE_DENOMINATOR')
    else:
        raise ValueError('PRODUCT_PG_CATALOG_REQUIRED_FOR_EXACT_DAILY_PUBLICATION')
    return dict(contract_id=CONTRACT, T0=candidate['accepted_trade_date'],
        predecessor=predecessor, registry=registry, daily_evidence=daily_evidence,
        period_artifacts=period_artifacts,
        product_catalog=product_receipt,
        publication=False)
