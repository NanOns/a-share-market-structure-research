"""Stage a content-addressed, non-release Focus input manifest outside TDX."""
from __future__ import annotations

from pathlib import Path

from scripts.probe_focus_full_day_inputs import build_probe_manifest
from src.focus_tracker.input_manifest import write_manifest


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest, summary = build_probe_manifest()
    target = (ROOT / "runtime/focus_staging" /
              manifest.trade_date.strftime("%Y%m%d") /
              f"input-manifest-{manifest.sha256}.json")
    write_manifest(output_path=target, manifest=manifest)
    print({"mode": "STAGING_ONLY", "path": str(target),
           "sha256": manifest.sha256,
           "release_gate_reasons": manifest.release_gate_reasons,
           "source_rows": summary["source_rows"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
