"""Explicit current V6 startup. Historical V5 dispatcher remains byte-identical."""
from scripts.v4_16_go_forward_shadow_runtime_r4r4 import RealShadowController

def ShadowRuntimeController(root,mode='REAL_SHADOW',**kwargs):
    if mode!='REAL_SHADOW':raise ValueError('EXPLICIT_V6_REAL_SHADOW_ENTRY_ONLY')
    return RealShadowController(root,**kwargs)
