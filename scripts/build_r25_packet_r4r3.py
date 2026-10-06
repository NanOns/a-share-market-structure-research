"""Explicit V5 packet successor; historical R4R2 producer stays read-only."""
from types import FunctionType,CodeType
from scripts import build_r25_bridge_r4r2 as predecessor

def _successor_code(code):
    changes={'config/v4_16_runtime_dependencies_v4.json':'config/v4_16_runtime_dependencies_v5.json',
             'V4_16_R25_PACKET_R4R2_V1':'V4_16_R25_PACKET_R4R3_V1'}
    consts=tuple(_successor_code(c) if isinstance(c,CodeType) else changes.get(c,c) if isinstance(c,str) else c for c in code.co_consts)
    return code.replace(co_consts=consts)

old=predecessor.produce_packet
produce_packet=FunctionType(_successor_code(old.__code__),old.__globals__,old.__name__,old.__defaults__,old.__closure__)
produce_packet.__kwdefaults__=old.__kwdefaults__
