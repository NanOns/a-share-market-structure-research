"""Seal the three completed scoped cards; root owns unified commit/push."""
import json
from pathlib import Path
import sys
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from workbench_analysis.forward_pit_ledger_r2 import atomic, canonical, reference
from v4.scoped_promotions_r3 import CONTRACT, HEADS, PERMISSIONS, read_payload
from scripts.next_round_execution_r3 import verify_protected

OUTPUT = "reports/audits/next_round_r3/scoped_promotions/"
CLOSURE = "docs/audits/A02_A05_A04_SCOPED_PROMOTION_CLOSURE_R3_20261002.md"


def main():
    entry = verify_protected()
    tests = ElementTree.parse(ROOT / OUTPUT / "TARGETED_TESTS_R1.xml").getroot()
    suites = list(tests.iter("testsuite"))
    counts = {k: sum(int(s.get(k, "0")) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    if counts != dict(tests=57, failures=0, errors=0, skipped=0):
        raise ValueError("SCOPED_TARGETED_TESTS_REQUIREMENT")
    receipt = json.loads((ROOT / OUTPUT / "PROMOTION_RECEIPT_R1.json").read_bytes())
    post = json.loads((ROOT / OUTPUT / "POST_PROMOTION_INDEPENDENT_READBACK_R1.json").read_bytes())
    if post["status"] != "PASS":
        raise ValueError("SCOPED_POST_READBACK_REQUIRED")
    text = """# A02 / A05 / A04 scoped promotion closure R3 — 2026-10-02

本轮依据为归档的 `V4_R2_BATCH_INDEPENDENT_EXTERNAL_AUDIT_R2_20261002.md` 与总调度卡 R3，实施基线为 d119c0526e44a819f85b4917159d3eeb5daadf2a 的当前 descendant。阶段入口 Phase 0 = DEGRADED_PASS。三卡均只登记外部已批准的精确 scope；独立 source replay 与 post-promotion readback 均为本轮重新运行。

| Task | Contract / Acceptance | Evidence / result | Next stage |
|---|---|---|---|
| A02 | A02_A05_A04_SCOPED_PROMOTIONS_R3_V1 / PASS_RECONSTRUCTED_CORRECTED_SCOPE | V4-05 / V4-07 / V4-09 各 5222 行；changed = 5222 / 5222 / 2811；15666 full old/new business diff rows，source oracle mismatches = 0 | 三个 append-only Amendment Heads，显式 historical research choice；等待统一提交后外审 |
| A05 | 同一 versioned contract / PASS_CURRENT_SNAPSHOT_ONLY | 2026-09-24，541 sectors，10 zero-member sectors，normal quote universe 5464；FALSE 535 / TRUE 2 / UNKNOWN 4；独立 exact AST mismatches = 0，9/30 rotation/context business diff = 0 | CURRENT_SNAPSHOT_20260924 显式读取，拒绝其他日期；等待统一提交后外审 |
| A04 | 同一 versioned contract / PASS_ENGINEERING_GO_FORWARD_SCOPE | 378 sectors，known Amount-A = 0，warmup UNKNOWN = 378，accepted sessions = 1，missing H21 = 20；实际 source admission / amount / membership replay 字节完全一致 | ACCUMULATION_CONTINUES，逐 accepted session append-only；consumer external acceptance 单独进行 |

最终状态为 `A02_DOWNSTREAM_AMENDMENTS_PROMOTED_SCOPED`、`V4_08_B2_CURRENT_SNAPSHOT_SCOPED_AMENDMENT_PROMOTED`、`A04_GO_FORWARD_PRODUCER_SCOPED_ACCEPTED` 与 `ACCUMULATION_CONTINUES`。

A02 每个 Amendment Head 精确绑定独立 RPS Head、old/new replay、business diff、原算法/参数 SHA、外部审计和本轮独立 readback。V4-09 绑定与 V4-07 相同的 exact seed artifact bytes。知识 lineage 为 RECONSTRUCTED_CORRECTED；AS_RECORDED = false；historical_first_availability_proven = false。Reader 必须显式选择 ORIGINAL_ACCEPTED 或 RECONSTRUCTED_CORRECTED_AMENDMENT，并返回所选 Head 与 mode；没有 silent fallback。

A05 独立 capability amendment 精确绑定 A05 acceptance record 与 R3 replay/diff，允许日期仅 2026-09-24，historical_PIT_equivalent = false。Amount-A warm branch 仍为 UNKNOWN / DIAGNOSTIC_AUDIT_OPEN，不注入 2026-09-30 V4-08。

A04 Head 仅接受工程 producer。formal_consumer_enabled = false；historical_reconstruction_accepted = false；H21_warmup_required = true；stock_amr20_dependency = false。未来 accumulation 继续复用严格 admitted daily command `python scripts/run_a04_go_forward_r3_1.py`，实际 accepted membership + amount source → observation → append-only。未到 H21 保持 UNKNOWN；达到 H21 后也不自动启用，必须另做 H21 completeness、source consistency、arithmetic oracle、consumer-specific external acceptance。没有回填不存在的 first availability。

五个新 Head 为 allowlisted scoped pointers，payload 以 SHA-256 命名并 immutable atomic publication。再执行 promotion 保持 pointer/payload 字节一致。实际 rollback 仅在临时副本验证：删除 exact bound pointer，保留全部 durable payload/evidence；真实 Heads 未 rollback。旧 Heads 与 Data/Stage Heads 已按本轮入口 SHA 验证完全不变。

本轮 targeted regression 57 passed / 0 failed / 0 errors / 0 skipped，覆盖 scope escalation、未来日期、unaudited rehashed candidate、consumer/permission escalation、idempotence、rollback 以及原 A04 arithmetic/source/stock independence 与 A02/A05 tests。测试结果与 source oracle、external authority、post-readback 共同构成 scoped readiness，不将测试代替外部验收。

证据目录：`reports/audits/next_round_r3/scoped_promotions/`。生产、Shadow、Focus、Global Mandatory Adoption 均为 false；Data Head KEEP 2026-09-30；Stage Head KEEP V4_00_TO_V4_10_ACCEPTED；本登记不产生 V4-11 Accepted Head，也不授权 V4-12 runtime。下一步仅 root 统一 commit + push 后 STOP，等待本轮独立外部验收。
"""
    atomic(ROOT / CLOSURE, text.encode("utf8"), immutable=True)
    paths = [
        "src/v4/scoped_promotions_r3.py", "scripts/promote_a02_a05_a04_scoped_r3.py",
        "scripts/verify_a02_a05_a04_scoped_r3.py", "scripts/seal_a02_a05_a04_scoped_r3.py",
        "tests/v4_scoped_promotions_r3/test_scoped_readers.py", CLOSURE,
        *HEADS.values(),
    ]
    paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / OUTPUT).glob("*")) if p.name != "HANDOFF_R1.json"]
    for key in HEADS:
        pointer, _ = read_payload(ROOT, key)
        paths.append(pointer["payload"]["path"])
    manifest = dict(contract_id=CONTRACT, status="THREE_SCOPED_TASKS_COMPLETED",
        task_statuses=receipt["statuses"], external_authority=entry["authority"],
        master=entry["master"], independent_source_readback=reference(ROOT, ROOT / OUTPUT / "INDEPENDENT_SOURCE_READBACK_R1.json"),
        independent_post_promotion_readback=reference(ROOT, ROOT / OUTPUT / "POST_PROMOTION_INDEPENDENT_READBACK_R1.json"),
        targeted_tests=counts, files=[reference(ROOT, ROOT / p) for p in sorted(set(paths))],
        permissions=PERMISSIONS, protected_heads_unchanged=True, Data_Head="KEEP_2026-09-30",
        Stage_Head="KEEP_V4_00_TO_V4_10_ACCEPTED", stage_promotion=False,
        next_stage="ROOT_UNIFIED_COMMIT_PUSH_THEN_STOP_WAIT_INDEPENDENT_EXTERNAL_ACCEPTANCE")
    atomic(ROOT / OUTPUT / "HANDOFF_R1.json", canonical(manifest), immutable=True)
    print(json.dumps(dict(status=manifest["status"], files=len(manifest["files"]), tests=counts)))


if __name__ == "__main__":
    main()
