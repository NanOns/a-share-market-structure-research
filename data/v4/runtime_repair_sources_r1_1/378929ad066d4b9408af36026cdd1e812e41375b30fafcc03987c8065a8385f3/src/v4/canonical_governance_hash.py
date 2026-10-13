"""Platform-stable identities for governance JSON and ordinary text artifacts."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

CANONICAL_JSON_SHA256_V1 = "CANONICAL_JSON_SHA256_V1"
CANONICAL_TEXT_SHA256_V1 = "CANONICAL_TEXT_SHA256_V1"


def canonical_json_bytes(value: Any) -> bytes:
    """Encode parsed JSON without whitespace, key-order, or newline dependence."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def canonical_json_file_bytes(path: str | Path) -> bytes:
    """Parse a UTF-8 JSON file (optional BOM) and return its canonical bytes."""
    value = json.loads(Path(path).read_bytes().decode("utf-8-sig"))
    return canonical_json_bytes(value)


def canonical_json_sha256(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def canonical_json_file_sha256(path: str | Path) -> str:
    return sha256(canonical_json_file_bytes(path)).hexdigest()


def canonical_text_file_bytes(path: str | Path) -> bytes:
    """Normalize a UTF-8 text file to LF and omit a UTF-8 BOM."""
    text = Path(path).read_bytes().decode("utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_text_file_sha256(path: str | Path) -> str:
    return sha256(canonical_text_file_bytes(path)).hexdigest()
