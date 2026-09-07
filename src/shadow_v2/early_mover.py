from __future__ import annotations
import math

RULESET_ID="early-mover-v2-shadow-v1.1-explicit-support"
DISPLAY_NAME="EARLY_RELATIVE_MOVER_V2"
NO_TEMPORAL_LEADERSHIP_CLAIM_WITHOUT_FORWARD_SEQUENCE=True

def trend_support(v):
 if not _finite(v):return "TREND_DATA_INSUFFICIENT"
 return "TREND_STRONG" if v>=.55 else "TREND_MODERATE" if v>=.40 else "TREND_WEAK"
def position_support(v):
 if not _finite(v):return "POSITION_DATA_INSUFFICIENT"
 return "POSITION_HEALTHY" if v>=.60 else "POSITION_NOT_CONFIRMED"
def sector_context(has_economic, economic_stabilizing, price_style_only=False, unknown_only=False):
 if economic_stabilizing:return "SECTOR_STABILIZING"
 if has_economic:return "NO_SECTOR_SIGNAL"
 if price_style_only:return "PRICE_BEHAVIOR_STYLE_ONLY"
 return "UNKNOWN_SECTOR_CONTEXT"
def classify(v1,context,trend,continuity,pulse,position):
 if not bool(v1):return "OUTSIDE_V1_EARLY_MOVER",False
 evidence=(trend,continuity,pulse,position)
 if any("DATA_INSUFFICIENT" in x for x in evidence) or context is None:return "DATA_INSUFFICIENT",False
 if context=="SECTOR_STABILIZING":return "SECTOR_ALREADY_STABILIZING",False
 if context in ("PRICE_BEHAVIOR_STYLE_ONLY","UNKNOWN_SECTOR_CONTEXT"):return "CONTEXT_UNCERTAIN",False
 if pulse=="PULSE_HIGH" or continuity=="CONTINUITY_WEAK":return "SHORT_TERM_PULSE",False
 core=trend in ("TREND_STRONG","TREND_MODERATE") and continuity in ("CONTINUITY_STRONG","CONTINUITY_MODERATE") and pulse!="PULSE_HIGH" and position=="POSITION_HEALTHY"
 supported=trend in ("TREND_STRONG","TREND_MODERATE") or position=="POSITION_HEALTHY"
 return ("EARLY_CORE",True) if core else (("EARLY_SUPPORTED",True) if supported else ("SHORT_TERM_PULSE",False))
def _finite(v):
 try:return math.isfinite(float(v))
 except (TypeError,ValueError):return False
