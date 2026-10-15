"""Read and integrity-check the existing E2/E3/E4 research evidence for R7."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

SCOPE = "FEP_STOCK_ENTRY_CORE / FIRST_PREWATCH / ABS_RETURN_N:T1 / CORE"


def _verified_json(root: Path, reference: dict):
    path = Path(reference["path"])
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("FEP_ARTIFACT_PATH_INVALID")
    target = (root / path).resolve()
    target.relative_to(root.resolve())
    raw = target.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) != reference.get("bytes") or digest != reference.get("sha256"):
        raise ValueError("FEP_ARTIFACT_DIGEST_MISMATCH")
    return json.loads(raw), dict(path=path.as_posix(),bytes=len(raw),sha256=digest)


def read_r7_fep(root: str | Path, *, current_counts: dict | None = None,
                now: datetime | None = None):
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    catalog_path = root / "reports/fep_e5_r1/MODEL_CATALOG.json"
    if not catalog_path.is_file():
        return dict(status="DATA_MISSING",scope=SCOPE,models=[],historical_baselines=[],
                    diagnostics=[],current_observation_coverage=current_counts,
                    prediction_slots=[dict(status="PENDING",reason="DAILY_MODEL_NOT_TRAINED")],
                    missing_inputs=["reports/fep_e5_r1/MODEL_CATALOG.json"],asof=now.isoformat())
    raw_catalog = catalog_path.read_bytes()
    catalog_sha = hashlib.sha256(raw_catalog).hexdigest()
    catalog = json.loads(raw_catalog)
    models=[]; baselines=[]; diagnostics=[]; unavailable=[]
    for entry in catalog.get("models",[]):
        stage = entry.get("stage")
        base = dict(stage=stage,model_family=entry.get("model_family"),
                    evidence_class=entry.get("evidence_class"),production_role=entry.get("production_role"),
                    model_id=entry.get("model_id"),model_set_id=entry.get("model_set_id"),
                    scope_id=entry.get("scope_id"),observation_scope=entry.get("observation_scope"),
                    target_id=entry.get("target_id"),horizon=entry.get("horizon"),
                    feature_contract_id=entry.get("feature_contract_id"),
                    artifact_digest=entry.get("artifact_digest"),champion=entry.get("champion",False),
                    source=dict(path="reports/fep_e5_r1/MODEL_CATALOG.json",sha256=catalog_sha))
        models.append(base)
        reference = entry.get("artifact_references",{}).get("primary")
        if stage != "E2":
            refs=entry.get("artifact_references",{})
            checks=[]
            for role,ref in sorted(refs.items()):
                try:
                    _, receipt = _verified_json(root,ref)
                    checks.append(dict(role=role,**receipt))
                except (OSError,ValueError,KeyError,TypeError) as exc:
                    unavailable.append(dict(stage=stage,role=role,reason=str(exc),path=ref.get("path")))
            diagnostics.append(dict(**base,diagnostic_only=True,
                                    verdict="工程诊断，未证明增益",
                                    available_artifacts=checks,
                                    missing_inputs=[x for x in unavailable if x.get("stage")==stage]))
            continue
        if not reference:
            unavailable.append(dict(stage="E2",reason="PRIMARY_ARTIFACT_REFERENCE_MISSING")); continue
        try:
            artifact, receipt = _verified_json(root,reference)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            unavailable.append(dict(stage="E2",reason=str(exc),path=reference.get("path"))); continue
        rows=artifact.get("counts",{}).get("rows")
        eligible=artifact.get("denominator_summary",{}).get("eligible")
        supported=next((x for x in artifact.get("backoff_trace",[]) if x.get("state")=="SUPPORTED"),None)
        stats=artifact.get("statistics",{})
        baselines.append(dict(base,artifact_id=artifact.get("artifact_id"),
            artifact_contract=artifact.get("contract_id"),dataset_id=artifact.get("dataset_id"),
            dataset_digest=artifact.get("dataset_digest"),sample_count=rows,eligible_count=eligible,
            expected_count=artifact.get("denominator_summary",{}).get("expected"),
            missing_fraction=artifact.get("denominator_summary",{}).get("missing_fraction"),
            statistics=stats,condition_tuple=artifact.get("condition_tuple"),
            base_partition=artifact.get("base_partition"),backoff_trace=artifact.get("backoff_trace"),
            supported_level=supported.get("level") if supported else None,
            support_status=supported.get("state") if supported else "INSUFFICIENT_SUPPORT",
            created_at=artifact.get("created_at"),source=receipt,
            quality="HISTORICAL_ENGINEERING_DESCRIPTIVE_ONLY"))
    missing_inputs=unavailable
    return dict(status="READY" if models or baselines else "DATA_MISSING",scope=SCOPE,
        models=models,historical_baselines=baselines,diagnostics=diagnostics,
        current_observation_coverage=current_counts,
        prediction_slots=[dict(status="PENDING",reason="DAILY_MODEL_NOT_TRAINED",
            eligible_prediction_generated=False,priority_v1_unchanged=True)],
        asof=now.isoformat(),evidence_class="HISTORICAL_ENGINEERING_AND_RESEARCH_ONLY",
        quality="E2_BASELINE_AVAILABLE" if baselines else "E2_BASELINE_UNAVAILABLE",
        source=dict(path="reports/fep_e5_r1/MODEL_CATALOG.json",sha256=catalog_sha,bytes=len(raw_catalog)),
        missing_inputs=missing_inputs)
