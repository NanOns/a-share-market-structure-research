"""Read-only current admission; historical engineering acceptance grants no production rights."""
import hashlib
import json
from pathlib import Path

VERSION = 'FEP_CURRENT_ADMISSION_R4_V1'
REASONS = {
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
    return dict(contract_id=VERSION, engineering_status='FEP_ENGINEERING_GATE_READY',
        production_status='BLOCKED' if reasons else 'FEP_PRODUCTION_AUTHORIZED',
        status='FEP_CAPABILITY_NOT_READY' if reasons else 'READY', reasons=reasons,
        reason_text=[REASONS[k] for k in reasons],
        fields={k: dict(value=None, status='FEP_CAPABILITY_NOT_READY', reasons=list(reasons)) for k in FIELDS},
        production_authorized=not reasons, prediction_generated=False)

def current_gate(root):
    path = Path(root) / 'reports/fep_e5_r1/MODEL_CATALOG.json'
    try:
        models = json.loads(path.read_text(encoding='utf-8')).get('models', []) if path.exists() else []
        if not isinstance(models,list) or any(not isinstance(m,dict) for m in models):
            models=[]
    except (OSError, ValueError, AttributeError):
        models=[]
    result = evaluate(models[0] if models else None)
    result['historical_engineering_model_count'] = len(models)
    result['source_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    return result

def frozen_equal(existing, candidate):
    """Frozen metadata, including clocks and revisions, must remain byte-logically exact."""
    if existing != candidate:
        raise ValueError('FEP_FROZEN_PREDICTION_MUTATION')
    return existing
