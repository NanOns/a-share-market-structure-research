"""Trace file reads made by one approved read-only V4 validation entrypoint."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ALLOWED_ENTRYPOINTS = {"scripts/validate_v4_12_promotion_r14.py"}


def trace(root: Path, entrypoint: str, output: Path) -> dict[str, Any]:
    root = root.resolve()
    rel = Path(entrypoint).as_posix()
    if rel not in ALLOWED_ENTRYPOINTS:
        raise ValueError("READ_ONLY_TRACE_ENTRYPOINT_NOT_ALLOWLISTED")
    target = (root / rel).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("READ_ONLY_TRACE_ENTRYPOINT_INVALID")
    git_head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    events: list[dict[str, Any]] = []
    hashing = False

    def hook(event: str, args: tuple[Any, ...]) -> None:
        if hashing:
            return
        if event == "open" and args:
            try:
                raw_path = os.fspath(args[0])
                if isinstance(raw_path, bytes):
                    raw_path = os.fsdecode(raw_path)
                path = Path(raw_path).resolve(strict=False)
                if path.is_relative_to(root):
                    mode = args[1] if len(args) > 1 else "r"
                    flags = args[2] if len(args) > 2 else None
                    events.append({"event": "open", "path": path.relative_to(root).as_posix(),
                                   "mode": str(mode), "flags": flags,
                                   "read_only_open": not any(c in str(mode) for c in "wax+")})
            except (OSError,TypeError,ValueError):
                return
        elif event == "subprocess.Popen":
            executable = args[0] if args else None
            argv = args[1] if len(args) > 1 else None
            cwd = args[2] if len(args) > 2 else None
            events.append({"event": "subprocess.Popen", "executable": str(executable)[:512] if executable is not None else None,
                           "argv": [str(x)[:512] for x in argv[:32]] if isinstance(argv,(list,tuple)) else str(argv)[:2048] if argv is not None else None,
                           "cwd": str(cwd)[:1024] if cwd is not None else None})

    before = time.time_ns()
    sys.addaudithook(hook)
    old_argv, old_cwd, old_path = sys.argv, Path.cwd(), list(sys.path)
    try:
        os.chdir(root)
        sys.path[:0] = [str(root), str(target.parent)]
        sys.argv = [str(target)]
        runpy.run_path(str(target), run_name="__main__")
        outcome = "COMPLETED"
    except BaseException as exc:
        outcome = "FAILED"
        events.append({"event": "entrypoint_exception", "type": type(exc).__name__, "message": str(exc)[:2000]})
    finally:
        sys.argv = old_argv
        sys.path[:] = old_path
        os.chdir(old_cwd)
    unique_paths = sorted({x["path"] for x in events if x.get("event") == "open"})
    identities = []
    hashing = True
    try:
        for relpath in unique_paths:
            path = root / Path(relpath)
            try:
                digest = hashlib.sha256()
                size = 0
                with path.open("rb") as stream:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk); size += len(chunk)
                identities.append({"path": relpath, "sha256": digest.hexdigest(), "bytes": size,
                                   "exists_after_run": True})
            except OSError as exc:
                identities.append({"path": relpath, "sha256": None, "bytes": None,
                                   "exists_after_run": False, "error": type(exc).__name__})
    finally:
        hashing = False
    result = {"contract_id": "V4_READ_ONLY_FILE_ACCESS_TRACE_R1", "version": "1.0.0",
              "repository_root": str(root), "git_head": git_head,
              "entrypoint": rel, "outcome": outcome, "started_utc_ns": before,
              "ended_utc_ns": time.time_ns(), "event_count": len(events),
              "read_open_count": sum(1 for e in events if e.get("event") == "open" and e.get("read_only_open")),
              "write_capable_open_count": sum(1 for e in events if e.get("event") == "open" and not e.get("read_only_open")),
              "file_identities": identities, "events": events,
              "evidence_boundary": "local validation entrypoint only; not scanner evidence, production runtime, PG, market-source or deployment acceptance"}
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name("." + output.name + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, output)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--entrypoint", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = trace(Path(args.root), args.entrypoint, Path(args.output))
    print(json.dumps({k: result[k] for k in ("git_head", "entrypoint", "outcome", "read_open_count", "write_capable_open_count")}))
    return 0 if result["outcome"] == "COMPLETED" and result["write_capable_open_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
