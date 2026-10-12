"""Bounded Focus history payloads; complete source timeline remains authoritative."""
import gzip
import json

CONTRACT='V4_FOCUS_REPLAY_BOUNDED_HISTORY_FULL_TIMELINE_R1'

def read_history(path, window):
    """Decode every source bar, retain only payloads consumed by this window.

    The caller verifies the entire immutable source SHA. All observed dates,
    first/last dates and counts remain exact; no synthetic bar is introduced.
    """
    dates=frozenset(window)
    histories={};timelines={}
    with gzip.open(path,'rt',encoding='utf8') as stream:
        for line in stream:
            if not line.strip():continue
            row=json.loads(line);sid=row['security_id']
            if sid in histories:raise ValueError('FOCUS_HISTORY_DUPLICATE_SECURITY')
            bars=row['bars']
            observed=frozenset(int(bar['trade_date'].replace('-','')) for bar in bars)
            histories[sid]=[bar for bar in bars if bar['trade_date'] in dates]
            timelines[sid]=observed
    return histories,timelines
