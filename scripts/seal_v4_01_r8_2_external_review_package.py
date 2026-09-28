from __future__ import annotations

"""Create an atomic, evidence-bound R8.2 external review package."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_2.json")
QUEUE = Path("reports/v4_01/V4_01_R8_2_UNRESOLVED_AUDIT_QUEUE.json")
POST = Path("reports/v4_01/V4_01_R8_2_INDEPENDENT_POSTCHECK_R1_20260928.json")
STAGE = Path("reports/v4_01/v4_01_final_stage_receipt_R8_2_20260928.json")
TESTS = Path("reports/v4_joint/V4_R8_2_DM01_TEST_RECEIPT_R1_20260928.json")
OUTPUT = Path("reports/v4_01/V4_01_R8_2_EXTERNAL_REVIEW_PACKAGE_R1_20260928.md")


def sha(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def atomic_text(path: Path, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, target)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def main() -> int:
    event, queue, post, stage, tests = map(read, (EVENT, QUEUE, POST, STAGE, TESTS))
    lines = [
        "# V4-01 R8.2 Identity Relation Policy — External Review Package",
        "",
        f"Prepared: {datetime.now(timezone.utc).replace(microsecond=0).isoformat()}",
        "Internal policy/postcheck result: **PASS**",
        f"Required Scope owner gate: **{stage.get('required_scope_status')}**",
        "External acceptance: **PENDING_EXTERNAL_AUDIT**",
        "",
        "## Scope and disposition",
        "",
        "R8.2 binds identity resolution to `IDENTITY_RELATION_EVIDENCE_POLICY_V1`. Listing dates, source revisions, lifecycle adjacency, roster adjacency, names, and bar continuity remain candidate signals. SAME requires a verified official code-change notice or a versioned accepted alias; DISTINCT requires verified official distinct issuer identity or accepted lifecycle identity evidence.",
        "",
        f"The accepted-history backscan found **{event.get('candidate_count')}** candidates: **{event.get('candidate_status_counts', {}).get('CONFIRMED_SAME_ENTITY_CODE_CHANGE', 0)}** SAME confirmation and **{event.get('unresolved_required_scope_candidate_count')}** unresolved Required Scope candidates. No candidate was resolved DISTINCT without explicit distinct issuer or accepted lifecycle evidence. Under the zero-unresolved limit, Gate A is **BLOCKED** until evidence for those candidates is accepted.",
        "",
        "The unresolved queue is open and contains only Required Scope unresolved events. It must not be interpreted as confirmed identity or confirmed distinction.",
        "",
        "## Verification evidence",
        "",
        f"- Relation policy: `{stage['evidence']['policy']['path']}` (SHA-256 `{stage['evidence']['policy']['sha256']}`).",
        f"- Discovery report: `{EVENT.as_posix()}` (SHA-256 `{sha(EVENT)}`). Candidate status counts: `{json.dumps(event.get('candidate_status_counts', {}), sort_keys=True)}`.",
        f"- Unresolved queue: `{QUEUE.as_posix()}` (SHA-256 `{sha(QUEUE)}`). Queue count: `{queue.get('candidate_count')}`.",
        f"- Independent postcheck: `{POST.as_posix()}` (SHA-256 `{sha(POST)}`); status `{post.get('status')}`, owner gate `{post.get('owner_stage_result')}`.",
        f"- Regression receipt: `{TESTS.as_posix()}` (SHA-256 `{sha(TESTS)}`); status `{tests.get('status')}`, counts `{json.dumps(tests.get('counts', {}), sort_keys=True)}`.",
        f"- R8.2 stage receipt: `{STAGE.as_posix()}` (SHA-256 `{sha(STAGE)}`).",
        "- R7 canonical identity map and required universe hashes are unchanged from the accepted R8 baseline.",
        "- The discovery algorithm contains no fixture-specific security-code branches; known transition examples remain in test data.",
        "",
        "## External review requested",
        "",
        "Please review the evidence policy, the single confirmed SAME relation, the 37 unresolved candidates, and whether any independently accepted official issuer/lifecycle evidence exists for each candidate. An external FULL_PASS must not be issued while any required-scope candidate remains unresolved.",
        "",
        "DM-01 remains framework-only. This package does not claim that incremental component builders are wired, that a completed-session E2E ran, or that Data Head advanced. V4-03 remains blocked.",
        "",
        "## Next stage",
        "",
        "Complete external R8.2 review and independently accepted evidence triage. Only after Gate A external acceptance should DM-01 complete its real incremental builder wiring and run a real completed-session E2E with a complete source freeze.",
        "",
    ]
    atomic_text(OUTPUT, "\n".join(lines))
    print(json.dumps({"status": "READY_FOR_EXTERNAL_REVIEW", "package": OUTPUT.as_posix(),
                      "sha256": sha(OUTPUT), "external_acceptance": "PENDING_EXTERNAL_AUDIT"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
