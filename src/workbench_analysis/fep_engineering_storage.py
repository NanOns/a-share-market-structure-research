"""Versioned, resolved engineering-only storage admission for E2/E3 artifacts."""
import json
from pathlib import Path

CONTRACT_ID='FEP_ENGINEERING_STORAGE_V2'
CONTRACT=Path(__file__).resolve().parents[2]/'config/fep_engineering_storage_contract_v2.json'

def engineering_directory(directory, *, error):
    candidate=Path(directory)
    if '..' in candidate.parts:
        raise ValueError(error)
    resolved=candidate.resolve()
    contract=json.loads(CONTRACT.read_bytes())
    if contract['contract_id']!=CONTRACT_ID:
        raise ValueError(error)
    roots=[Path(value).resolve() for value in contract['allowed_roots']]
    if not any(resolved.is_relative_to(root) for root in roots):
        raise ValueError(error)
    return resolved
