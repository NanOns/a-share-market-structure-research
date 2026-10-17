"""Resolve configured local paths without writing to source directories."""
from __future__ import annotations
import os
import re
from pathlib import Path

def resolve_tdx_root(project_root: str|Path) -> Path:
    root=Path(project_root);config=root/"config/paths.yaml"
    configured=None
    if config.is_file():
        text=config.read_text("utf8");section=re.search(r"(?ms)^tdx:\s*\n(?P<body>(?:^[ \t]+.*\n?)*)",text)
        match=re.search(r"(?m)^\s+root:\s*['\"]?([^'\"#\r\n]+)",section.group("body") if section else "")
        configured=match.group(1).strip() if match else None
    candidate=configured or os.environ.get("TDX_ROOT")
    if candidate:return Path(candidate).expanduser().resolve()
    raise FileNotFoundError("TDX_ROOT_NOT_CONFIGURED")
