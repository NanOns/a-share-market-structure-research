"""Execution identity for V2 orchestration, separate from V1 computation."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from common.identity import _canonical,_file_hashes,_hash_bytes

V2_EXECUTION_IDENTITY_VERSION="v2-execution-identity-v1.1-separated"

def v2_execution_identity(root:str|Path)->dict[str,Any]:
    root=Path(root)
    paths=[
        "run_shadow_v2.py","run_steady_trend_v2.py","run_strong_pullback_v2.py",
        "run_breakout_prep_v2.py","run_sector_leader_v2.py","run_early_mover_v2.py",
        "run_priority_v2.py","run_live_forward.py","run_forward_evaluation.py",
        "src/common/v2_identity.py","src/common/paths.py","src/production/workbench.py",
        "src/shadow_v2/queue_ranking.py","src/sector/membership_snapshot.py",
        "src/forward/live.py","src/forward/observation.py","src/forward/evaluation.py",
        "docs/R4_FORWARD_OBSERVATION_CONTRACT_V1.md",
        "docs/R4_LIVE_DAILY_FORWARD_CAPTURE_CONTRACT_V1.md",
        "docs/V2_QUEUE_RANKING_CONTRACT_V1.md","docs/FORWARD_EVALUATION_CONTRACT_V1.md",
    ]
    missing=[relative for relative in paths if not (root/relative).is_file()]
    if missing:raise FileNotFoundError("V2_EXECUTION_IDENTITY_FILE_MISSING:"+",".join(missing))
    value={"version":V2_EXECUTION_IDENTITY_VERSION,"files":_file_hashes(root,paths)}
    value["sha256"]=_hash_bytes(_canonical(value));return value
