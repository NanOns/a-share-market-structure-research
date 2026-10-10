"""Read-only current admission; historical engineering acceptance grants no production rights."""
import hashlib
import json
from pathlib import Path

VERSION = 'FEP_CURRENT_ADMISSION_R4_V2'
REASONS = {
    'TRUSTED_AUTHORITY_UNAVAILABLE': '已实现 canonical DB 只读解析；正式生产 Owner、模型版本及独立能力批准源尚未接纳。',
    'PREDICTION_OWNER_MISSING': '缺少已接纳的预测消费 Owner。',
    'MODEL_NOT_FOUND': '未找到匹配当前用途的模型注册。',
    'MODEL_NOT_ACCEPTED': '已有历史工程模型，但尚未接受为当前生产模型。',
    'GRANT_MISSING': '缺少当前模型、范围和能力的正式授权。',
    'INPUT_ASOF_NOT_VERIFIED': '训练或预测输入的当时首次可用时间尚未核验。',
    'SAMPLE_NOT_MATURE': '当前用途的真实前瞻样本尚未成熟。',
    'NO_SCORING_AUTHORITY': '尚无生产评分或排序权限。',
}
FIELDS = ('return_expectancy', 'downside_risk', 'return_quantiles', 'prediction_revision', 'model_display', 'priority_use')

def evaluate(model=None, *, accepted=False, grant=None, request=None, input_asof=False, mature=False, scoring=False):
    """No writes, inference, grant issuance or fixture promotion occur here."""
    reasons = []
    if model is None:
        reasons.append('MODEL_NOT_FOUND')
    elif not accepted or model.get('production_role') != 'ACCEPTED_PRODUCTION':
        reasons.append('MODEL_NOT_ACCEPTED')
    exact = bool(grant and request and all(grant.get(k) == request.get(k) and request.get(k) is not None
        for k in ('scope_id', 'target_id', 'horizon', 'feature_contract_id', 'model_set_id', 'model_revision', 'capability'))
        and grant.get('formal_approval') is True and grant.get('active') is True)
    exact = bool(exact and model and all(model.get(k) == request.get(k)
        for k in ('scope_id', 'target_id', 'horizon', 'feature_contract_id', 'model_set_id', 'model_revision')))
    if not exact:
        reasons.append('GRANT_MISSING')
    if not input_asof:
        reasons.append('INPUT_ASOF_NOT_VERIFIED')
    if not mature:
        reasons.append('SAMPLE_NOT_MATURE')
    if not scoring:
        reasons.append('NO_SCORING_AUTHORITY')
    candidate_eligible = not reasons
    # Legacy arguments are display claims only. No caller-supplied bool/dict
    # can cross the production trust boundary. Current registry is engineering
    # only; no formal authority adapter has been admitted.
    reasons.extend(['TRUSTED_AUTHORITY_UNAVAILABLE', 'PREDICTION_OWNER_MISSING'])
    return dict(gate_candidate_status='GATE_ELIGIBLE_CANDIDATE' if candidate_eligible else 'NOT_ELIGIBLE',
        authority=dict(status='TRUSTED_AUTHORITY_UNAVAILABLE', production_authorized=False,
            formal_owner=None, evidence_trust='DISPLAY_CLAIMS_ONLY'), contract_id=VERSION, engineering_status='FEP_ENGINEERING_GATE_READY',
        production_status='BLOCKED',
        status='FEP_CAPABILITY_NOT_READY', reasons=reasons,
        reason_text=[REASONS[k] for k in reasons],
        fields={k: dict(value=None, status='SOURCE_INCOMPLETE', reasons=list(reasons)) for k in FIELDS},
        production_authorized=False, prediction_generated=False)

def resolve_current_authority():
    """Actual source discovery; canonical DB reader exists but Owner admission is absent.

    The engineering Ledger remains HISTORICAL_ENGINEERING_FIXTURE_ONLY. The
    canonical readonly adapter validates DB snapshots without issuing rights.
    Caller dictionaries, context tokens and shadow receipts are never authority.
    """
    from .trusted_authority import resolve_current_sources
    return resolve_current_sources(Path(__file__).resolve().parents[3])


def inspect_isolated_candidate(bundle, request, *, at):
    """Pure contract rehearsal; never used by current_gate or permission checks.

    Even a complete fixture is only a candidate, never a production grant.
    Caller-supplied evidence is explicitly untrusted and isolated.
    """
    from datetime import datetime
    keys = ('scope_id', 'target_id', 'horizon', 'feature_contract_id',
            'model_set_id', 'model_revision', 'capability')
    errors = []
    try:
        now = datetime.fromisoformat(at)
        grant = bundle['grant']
        model = bundle['model']
        for key in keys:
            if request.get(key) is None or grant.get(key) != request[key]:
                errors.append('GRANT_BINDING_MISMATCH:' + key)
        for key in keys[:-1]:
            if model.get(key) != request.get(key):
                errors.append('REGISTRY_BINDING_MISMATCH:' + key)
        if request.get('capability') not in ('MODEL_DISPLAY', 'PRIORITY_USE'):
            errors.append('CAPABILITY_NOT_PRODUCTION')
        if model.get('production_role') != 'ACCEPTED_PRODUCTION' or model.get('champion') is not True:
            errors.append('MODEL_NOT_ACCEPTED_CHAMPION')
        if not grant.get('active') or grant.get('revoked') or not grant.get('formal_approval'):
            errors.append('GRANT_INACTIVE')
        if not (datetime.fromisoformat(grant['valid_from']) <= now < datetime.fromisoformat(grant['expires_at'])):
            errors.append('GRANT_TIME_INVALID')
        head, receipt = bundle['head'], bundle['cas_receipt']
        if head.get('action') != 'ALLOW' or head.get('grant_id') != grant.get('grant_id'):
            errors.append('HEAD_NOT_ALLOWED')
        if not head.get('activation_id') or any(head.get(k) != receipt.get(k) for k in ('grant_id', 'activation_id', 'version')):
            errors.append('CAS_RECEIPT_MISMATCH')
        if not bundle.get('external_approval_id'):
            errors.append('EXTERNAL_APPROVAL_MISSING')
        source = bundle['source']
        if source.get('input_mode') != 'AS_RECORDED' or not source.get('digest') or datetime.fromisoformat(source['first_available_at']) > now:
            errors.append('INPUT_ASOF_NOT_VERIFIED')
        if not isinstance(bundle.get('mature_count'), int) or isinstance(bundle.get('mature_count'), bool) or bundle['mature_count'] <= 0:
            errors.append('SAMPLE_NOT_MATURE')
        if not bundle.get('prediction_owner'):
            errors.append('PREDICTION_OWNER_MISSING')
        if bundle.get('frozen_digest') != bundle.get('original_frozen_digest') or not bundle.get('frozen_digest'):
            errors.append('FEP_FROZEN_PREDICTION_MUTATION')
    except (KeyError, TypeError, ValueError):
        errors.append('MALFORMED_ISOLATED_EVIDENCE')
    return dict(status='GATE_ELIGIBLE_CANDIDATE' if not errors else 'NOT_ELIGIBLE',
        evidence_trust='UNTRUSTED_ISOLATED_FIXTURE', errors=errors,
        production_authorized=False, prediction_generated=False)

def current_gate(root):
    path = Path(root) / 'reports/fep_e5_r1/MODEL_CATALOG.json'
    try:
        models = json.loads(path.read_text(encoding='utf-8')).get('models', []) if path.exists() else []
        if not isinstance(models,list) or any(not isinstance(m,dict) for m in models):
            models=[]
    except (OSError, ValueError, AttributeError):
        models=[]
    result = evaluate(models[0] if models else None)
    from .trusted_authority import resolve_current_sources
    result['authority'] = resolve_current_sources(root)
    result['historical_engineering_model_count'] = len(models)
    result['source_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    return result

def frozen_equal(existing, candidate):
    """Frozen metadata, including clocks and revisions, must remain byte-logically exact."""
    if existing != candidate:
        raise ValueError('FEP_FROZEN_PREDICTION_MUTATION')
    return existing
