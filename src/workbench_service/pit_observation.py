"""Go-forward first-observed freeze; never backdate corrected history to PIT."""
import json
from datetime import datetime,timezone
from pathlib import Path
from .current_v4_context import canonical,digest,SourceInvalid
from .v4_daily_refresh import atomic_bytes

def freeze(reader,now=None):
    captured=datetime.now(timezone.utc)
    stamp=datetime.fromisoformat(now) if now else captured
    if stamp.tzinfo is None:raise SourceInvalid('PIT_OBSERVATION_TIMEZONE_REQUIRED')
    if stamp.astimezone(timezone.utc)>captured:raise SourceInvalid('FUTURE_OBSERVATION_TIME')
    if (captured-stamp.astimezone(timezone.utc)).total_seconds()>5:
        raise SourceInvalid('BACKDATED_OBSERVATION_TIME')
    # An optional caller timestamp is only a freshness assertion, never the
    # authority for a persisted first-observed timestamp.
    observed=captured.isoformat()
    day=reader.context['trade_date'];sources={k:v for k,v in reader.manifest['sources'].items() if k in ('membership','states','advanced','stock_factors','sector_operational')}
    identity=digest(canonical(sources));path=reader.root/'data/v4/pit_first_observed'/day/identity/'observation.json'
    if path.exists():
        receipt=json.loads(path.read_bytes())
        if (receipt.get('contract_id')!='R2_FIRST_OBSERVED_FREEZE_V1' or
            receipt.get('source_identity')!=identity or receipt.get('trade_date')!=day or
            receipt.get('strict_t0_pit_ready') is not False or receipt.get('AS_RECORDED') is not False):
            raise SourceInvalid('PIT_EXISTING_RECEIPT_CONFLICT')
        original=datetime.fromisoformat(receipt['first_observed_at'])
        if original.tzinfo is None or original.astimezone(timezone.utc)>captured:
            raise SourceInvalid('PIT_EXISTING_RECEIPT_TIME_INVALID')
        if set(receipt.get('sources',{}))!=set(sources):raise SourceInvalid('PIT_EXISTING_SOURCE_SET_CONFLICT')
        for name,b in receipt['sources'].items():
            from .joint_release import checked_path
            checked_path(reader.root,b)
            if b['sha256']!=sources[name]['sha256']:raise SourceInvalid('PIT_EXISTING_SOURCE_IDENTITY_CONFLICT')
        return receipt
    bindings={}
    for name,b in sources.items():
        raw=(reader.root/b['path']).read_bytes()
        if digest(raw)!=b['sha256']:raise SourceInvalid('PIT_FREEZE_SOURCE_MISMATCH')
        target=path.parent/(name+Path(b['path']).suffix);atomic_bytes(target,raw)
        bindings[name]=dict(path=target.relative_to(reader.root).as_posix(),sha256=b['sha256'],bytes=len(raw))
    receipt=dict(contract_id='R2_FIRST_OBSERVED_FREEZE_V1',trade_date=day,first_observed_at=observed,sources=bindings,source_identity=identity,strict_t0_pit_ready=False,reason='FIRST_OBSERVED_TIME_IS_NOT_PROOF_OF_HISTORICAL_FIRST_AVAILABLE',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
    atomic_bytes(path,canonical(receipt));return receipt
