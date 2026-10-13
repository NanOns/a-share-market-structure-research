"""V4-04 profile component status mapping for the frozen output schema."""


def component_status(observed: int, required: int, degraded: bool = False) -> str:
    if not 0 <= observed <= required or required == 0:
        raise ValueError("invalid required state availability")
    if degraded:
        return "DEGRADED"
    if observed == required:
        return "READY"
    if observed == 0:
        return "UNKNOWN_DATA"
    return "PARTIAL"
