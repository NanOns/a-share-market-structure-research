from __future__ import annotations

from pathlib import Path
import struct

from tdx.gbbq_reader import GBBQ_RECORD_LENGTH, decode_record


LOCAL_GBBQ = Path(r"D:\new_tdx\T0002\hq_cache\gbbq")


def test_local_first_record_decodes_to_known_plain_fields() -> None:
    if not LOCAL_GBBQ.is_file():
        return
    with LOCAL_GBBQ.open("rb") as stream:
        declared = struct.unpack("<I", stream.read(4))[0]
        encrypted = stream.read(GBBQ_RECORD_LENGTH)
    record = decode_record(encrypted, source=str(LOCAL_GBBQ), record_index=0)
    assert declared > 0
    assert LOCAL_GBBQ.stat().st_size == 4 + declared * GBBQ_RECORD_LENGTH
    assert record.security_id == "SZ.000001"
    assert record.event_date == 19900301
    assert record.category == 1
    assert abs(record.c2 - 3.56) < 1e-5
    assert record.c4 == 1.0
