"""Go-forward first-observed freeze; never backdate corrected history to PIT."""
import json
from datetime import datetime,timezone
from pathlib import Path
from .current_v4_context import canonical,digest,SourceInvalid
from .v4_daily_refresh import atomic_bytes

def freeze(reader,now=None):
    observed=now or datetime.now(timezone.utc).isoformat();stamp=datetime.fromisoformat(observed)
    if stamp.tzinfo is None:raise SourceInvalid('PIT_OBSERVATION_TIMEZONE_REQUIRED')
    if stamp.astimezone(timezone.utc)>datetime.now(timezone.utc):raise SourceInvalid('FUTURE_OBSERVATION_TIME')
    day=reader.context['trade_date'];sources={k:v for k,v in reader.manifest['sources'].items() if k in ('membership','states','advanced','stock_factors','sector_operational')}
    identity=digest(canonical(sources));path=reader.root/'data/v4/pit_first_observed'/day/identity/'observation.json'
    if path.exists():return json.loads(path.read_bytes())
    bindings={}
    for name,b in sources.items():
        raw=(reader.root/b['path']).read_bytes()
        if digest(raw)!=b['sha256']:raise SourceInvalid('PIT_FREEZE_SOURCE_MISMATCH')
        target=path.parent/(name+Path(b['path']).suffix);atomic_bytes(target,raw)
        bindings[name]=dict(path=target.relative_to(reader.root).as_posix(),sha256=b['sha256'],bytes=len(raw))
    receipt=dict(contract_id='R2_FIRST_OBSERVED_FREEZE_V1',trade_date=day,first_observed_at=observed,sources=bindings,source_identity=identity,strict_t0_pit_ready=False,reason='FIRST_OBSERVED_TIME_IS_NOT_PROOF_OF_HISTORICAL_FIRST_AVAILABLE',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
    atomic_bytes(path,canonical(receipt));return receipt
