from __future__ import annotations

from pathlib import Path
import struct

import pytest

from tdx.gbbq_reader import decode_gbbq_bytes


def test_gbbq_declared_size_must_close() -> None:
    content = struct.pack("<I", 2) + b"A" * 29
    with pytest.raises(ValueError, match="size mismatch"):
        decode_gbbq_bytes(content)
