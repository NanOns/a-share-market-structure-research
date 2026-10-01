"""Strict source admission layered over frozen R3 arithmetic and warmup ledger."""
import json
from .forward_pit_ledger_r2 import bound, canonical
from .amount_a_go_forward_r3 import (
    append_accepted_observation as frozen_append,
    read_verified_observations as frozen_read,
    compute_ledger_candidate as frozen_compute,
)

CONTRACT="A04_ACCEPTED_SOURCE_ADMISSION_R3_1"


def validate_roots(root,data_head_binding,membership_head_binding):
    from .dm01_accepted_chain_v1 import validate_head_v2
    data=json.loads(bound(root,data_head_binding))
    validate_head_v2(root,data)
    stage=json.loads(bound(root,data["stage_head"]))
    v408=json.loads(bound(root,stage["v4_08_binding"]))
    accepted=v408["membership_binding"]
    if (membership_head_binding["path"]!=accepted["path"] or membership_head_binding["sha256"]!=accepted["sha256"]
        or membership_head_binding.get("bytes",membership_head_binding.get("byte_count"))!=accepted.get("bytes",accepted.get("byte_count"))):
        raise ValueError("MEMBERSHIP_NOT_EXACT_ACCEPTED_V4_08_SOURCE")
    bound(root,accepted)
    return {"data_head_validation":"PASS_EXACT_V2_ACCEPTED_CHAIN_AND_SOURCE_COMPONENTS",
            "membership_admission":"EXACT_STAGE_BOUND_V4_08_ACCEPTED_MEMBERSHIP_SOURCE"}


def append_accepted_observation(root,*,data_head_binding,membership_head_binding,ledger="data/v4/a04_go_forward_r3"):
    validate_roots(root,data_head_binding,membership_head_binding)
    return frozen_append(root,data_head_binding=data_head_binding,membership_head_binding=membership_head_binding,ledger=ledger)


def read_verified_observations(root,bindings):
    for ref in bindings:
        item=json.loads(bound(root,ref))
        validate_roots(root,item["data_head_binding"],item["membership_head_binding"])
    return frozen_read(root,bindings)


def compute_ledger_candidate(root,bindings,*,target):
    read_verified_observations(root,bindings)
    return frozen_compute(root,bindings,target=target)
