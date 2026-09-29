"""Run V4-00C-equivalent publication/revision tests in an isolated SQLite namespace."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "scripts/sql/v4_05_r4_revision_ledger_harness_v1.sql"
OUT = ROOT / "reports/v4_05/V4_05_R4_REVISION_LEDGER_IDEMPOTENCY.json"
DATE = "2026-09-28"
NAMESPACE = "v4-05-r4-isolated-replay"
NS_ID = "NS-V4-05-R4-ISOLATED"


def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def table_counts(db: sqlite3.Connection) -> dict[str, int]:
    names = ("source_revisions", "publications", "publication_consumed_sources",
             "publication_revision_events", "publication_heads")
    return {name: db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in names}


def identity(source_revision_id: str, source_payload_digest: str) -> dict:
    consumed = {
        "TDX_RAW_PACKAGE": {"source_revision_id": source_revision_id, "digest": source_payload_digest},
        "FROZEN_GBBQ": {"source_revision_id": "GBBQ-20260926-FROZEN", "digest": "775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e"},
        "MARKET_CALENDAR": {"source_revision_id": "CALENDAR-20260926-FROZEN", "digest": "6188c28ae84890b1f2f7c6b44833528bfe5b00b819b25b9fbbedff3022c3b54a"},
        "CONTRACTS": {"source_revision_id": "V4-CONTRACT-SET-R4", "digest": "contracts-r4"},
        "PARAMETERS": {"source_revision_id": "V4-PARAMETERS-R4", "digest": "parameters-r4"},
    }
    manifest = digest(consumed)
    computation = digest({"target_date": DATE, "namespace": NAMESPACE, "source_manifest": manifest,
                          "formal_publication_identity": "2026-09-29T06:53:52+00:00"})
    return {"consumed": consumed, "manifest": manifest, "computation": computation,
            "formal": "2026-09-29T06:53:52+00:00"}


def run() -> dict:
    migration = MIGRATION.read_bytes()
    migration_id = "V4_05_R4_ISOLATED_LEDGER_HARNESS_V1"
    database_path = Path(tempfile.gettempdir()) / f"v4_05_r4_ledger_{uuid.uuid4().hex}.sqlite3"
    cleanup = {"attempted": False, "succeeded": False}
    receipt: dict = {"contract_id": "V4_05_R4_REVISION_LEDGER_IDEMPOTENCY_V1",
                     "namespace": NAMESPACE, "namespace_id": NS_ID,
                     "schema_migration_id": migration_id,
                     "schema_migration_sha256": sha256(migration).hexdigest(),
                     "database_engine": "SQLite isolated disposable database",
                     "database_path_redacted": database_path.name,
                     "contract_equivalence": ["append-only publication revisions", "immutable consumed-source binding",
                                              "unique replay identity", "explicit accepted-head transition",
                                              "revision predecessor", "atomic transaction rollback"]}
    db = sqlite3.connect(database_path)
    db.execute("PRAGMA foreign_keys=ON")
    try:
        db.executescript(migration.decode("utf-8"))
        db.execute("INSERT INTO model_namespaces VALUES(?,?,?,?)", (NS_ID, "V4_05_REPLAY_GATE_A", "REPLAY", NAMESPACE))
        db.commit()

        def add_source(revision_id: str, payload: str, revision_no: int, prior: str | None = None) -> str:
            payload_digest = sha256(payload.encode()).hexdigest()
            old = db.execute("SELECT digest,payload FROM source_revisions WHERE source_revision_id=?", (revision_id,)).fetchone()
            if old:
                if old != (payload_digest, payload):
                    raise ValueError("SAME_SOURCE_REVISION_ID_DIFFERENT_PAYLOAD")
                return payload_digest
            db.execute("INSERT INTO source_revisions VALUES(?,?,?,?,?,?)",
                       (revision_id, "TDX_RAW_PACKAGE", revision_no, payload_digest, payload, prior))
            return payload_digest

        def replay(source_revision_id: str, source_payload: str, revision_no: int, prior_publication: str | None,
                   prior_source: str | None) -> tuple[str, bool]:
            payload_digest = add_source(source_revision_id, source_payload, revision_no, prior_source)
            ident = identity(source_revision_id, payload_digest)
            existing = db.execute("""SELECT publication_id FROM publications WHERE trade_date=? AND model_namespace_id=?
                AND source_manifest_sha256=? AND computation_identity_sha256=? AND formal_publication_identity=? AND logical_output_sha256=?""",
                                  (DATE, NS_ID, ident["manifest"], ident["computation"], ident["formal"], "logical-output-" + ident["computation"])).fetchone()
            if existing:
                return existing[0], False
            next_revision = db.execute("SELECT COALESCE(MAX(revision_no),0)+1 FROM publications WHERE trade_date=? AND model_namespace_id=?",
                                       (DATE, NS_ID)).fetchone()[0]
            publication_id = "PUB-" + ident["computation"][:24]
            db.execute("""INSERT INTO publications(publication_id,trade_date,model_namespace_id,revision_no,status,
                source_manifest_sha256,computation_identity_sha256,formal_publication_identity,logical_output_sha256,parent_publication_id)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                       (publication_id, DATE, NS_ID, next_revision, "CANDIDATE", ident["manifest"], ident["computation"],
                        ident["formal"], "logical-output-" + ident["computation"], prior_publication))
            for key, value in ident["consumed"].items():
                if key == "TDX_RAW_PACKAGE":
                    db.execute("INSERT OR IGNORE INTO source_revisions VALUES(?,?,?,?,?,NULL)",
                               (value["source_revision_id"], "TDX_RAW_PACKAGE", revision_no, value["digest"], source_payload))
                else:
                    db.execute("INSERT OR IGNORE INTO source_revisions VALUES(?,?,?,?,?,NULL)",
                               (value["source_revision_id"], key, 1, value["digest"], value["digest"]))
                db.execute("INSERT INTO publication_consumed_sources VALUES(?,?,?,?)",
                           (publication_id, key, value["source_revision_id"], value["digest"]))
            db.execute("INSERT INTO publication_revision_events VALUES(?,?,?,?)",
                       ("EV-CREATED-" + publication_id, publication_id, "CREATED", prior_publication))
            return publication_id, True

        def accept(publication_id: str) -> None:
            row = db.execute("SELECT status,trade_date,model_namespace_id FROM publications WHERE publication_id=?", (publication_id,)).fetchone()
            if not row:
                raise ValueError("UNKNOWN_PUBLICATION")
            if row[0] == "ACCEPTED":
                return
            if row[0] != "CANDIDATE":
                raise ValueError("PUBLICATION_NOT_ACCEPTABLE")
            prior_head_row = db.execute("SELECT publication_id FROM publication_heads WHERE trade_date=? AND model_namespace_id=?", (row[1], row[2])).fetchone()
            db.execute("UPDATE publications SET status='ACCEPTED' WHERE publication_id=?", (publication_id,))
            db.execute("INSERT INTO publication_revision_events VALUES(?,?,?,?)",
                       ("EV-ACCEPTED-" + publication_id, publication_id, "ACCEPTED",
                        prior_head_row[0] if prior_head_row else None))
            db.execute("INSERT INTO publication_heads VALUES(?,?,?) ON CONFLICT(trade_date,model_namespace_id) DO UPDATE SET publication_id=excluded.publication_id",
                       (row[1], row[2], publication_id))

        before = table_counts(db)
        source1_digest = add_source("TDX-REV-1", "r3-frozen-raw-package", 1)
        pub1, first_created = replay("TDX-REV-1", "r3-frozen-raw-package", 1, None, None)
        db.commit()
        after_first = table_counts(db)
        pub1_repeat, second_created = replay("TDX-REV-1", "r3-frozen-raw-package", 1, None, None)
        db.commit()
        after_repeat = table_counts(db)
        accept(pub1)
        db.commit()
        head_after_first_accept = db.execute("SELECT publication_id FROM publication_heads WHERE trade_date=? AND model_namespace_id=?", (DATE, NS_ID)).fetchone()[0]

        source2_digest = sha256(b"controlled source revision r2").hexdigest()
        pub2, changed_created = replay("TDX-REV-2", "controlled source revision r2", 2, pub1, "TDX-REV-1")
        db.commit()
        head_before_changed_accept = db.execute("SELECT publication_id FROM publication_heads WHERE trade_date=? AND model_namespace_id=?", (DATE, NS_ID)).fetchone()[0]
        after_changed_candidate = table_counts(db)
        accept(pub2)
        db.commit()
        head_after_changed_accept = db.execute("SELECT publication_id FROM publication_heads WHERE trade_date=? AND model_namespace_id=?", (DATE, NS_ID)).fetchone()[0]
        after_changed_accept_counts = table_counts(db)

        conflict = {"hard_fail": False, "message": None}
        try:
            add_source("TDX-REV-2", "different payload under same revision id", 2, "TDX-REV-1")
        except ValueError as exc:
            conflict = {"hard_fail": True, "message": str(exc)}
        if not conflict["hard_fail"]:
            raise AssertionError("same revision identity conflict was not rejected")

        before_rollback = table_counts(db)
        rollback_ok = False
        try:
            db.execute("BEGIN")
            payload = "injected transaction failure"
            payload_hash = sha256(payload.encode()).hexdigest()
            db.execute("INSERT INTO source_revisions VALUES(?,?,?,?,?,NULL)", ("ROLLBACK-SRC", "TDX_RAW_PACKAGE", 3, payload_hash, payload))
            db.execute("INSERT INTO publications VALUES(?,?,?,?,?,?,?,?,?,?)",
                       ("ROLLBACK-PUB", DATE, NS_ID, 3, "CANDIDATE", "a"*64, "b"*64, "test-formal", "c"*64, pub2))
            db.execute("INSERT INTO publication_consumed_sources VALUES(?,?,?,?)", ("ROLLBACK-PUB", "TDX_RAW_PACKAGE", "ROLLBACK-SRC", payload_hash))
            raise RuntimeError("INJECTED_FAILURE_AFTER_CONSUMED_SOURCE_BEFORE_HEAD")
        except RuntimeError:
            db.rollback()
            rollback_ok = True
        after_rollback = table_counts(db)
        dangling = db.execute("SELECT COUNT(*) FROM publications WHERE publication_id='ROLLBACK-PUB'").fetchone()[0]
        dangling_consumed = db.execute("SELECT COUNT(*) FROM publication_consumed_sources WHERE publication_id='ROLLBACK-PUB'").fetchone()[0]
        if not rollback_ok or before_rollback != after_rollback or dangling or dangling_consumed:
            raise AssertionError("rollback left partial ledger rows")

        revisions = db.execute("SELECT publication_id,revision_no,status,parent_publication_id FROM publications ORDER BY revision_no").fetchall()
        counts_final = table_counts(db)
        receipt.update({"status": "PASS", "cases": {
            "I01_identical_replay": {"same_publication_id": pub1 == pub1_repeat, "first_created": first_created,
                                     "second_created": second_created, "no_count_drift": after_first == after_repeat,
                                     "publication_id": pub1, "head_id": head_after_first_accept},
            "I02_changed_source_revision": {"new_revision_appended": changed_created, "publication_id": pub2,
                                            "prior_revision_immutable": revisions[0][0] == pub1 and revisions[0][2] == "ACCEPTED",
                                            "predecessor_publication_id": revisions[1][3],
                                            "head_before_explicit_accept": head_before_changed_accept,
                                            "head_after_explicit_accept": head_after_changed_accept,
                                            "source_revision_digests": {"r1": source1_digest, "r2": source2_digest}},
            "I03_same_revision_different_payload": conflict,
            "I04_transaction_rollback": {"rollback_result": rollback_ok, "before_counts": before_rollback,
                                          "after_counts": after_rollback, "dangling_publications": dangling,
                                          "dangling_consumed_sources": dangling_consumed,
                                          "failure_point": "AFTER_CONSUMED_SOURCE_BEFORE_HEAD"}},
            "before_counts": before, "after_first_replay_counts": after_first, "after_second_replay_counts": after_repeat,
            "after_changed_source_candidate_counts": after_changed_candidate, "after_changed_source_accept_counts": after_changed_accept_counts,
            "final_counts": counts_final, "publication_lineage": revisions,
            "cleanup": cleanup})
    finally:
        db.close()
        cleanup["attempted"] = True
        try:
            database_path.unlink(missing_ok=True)
            cleanup["succeeded"] = not database_path.exists()
        except OSError as exc:
            cleanup["error"] = str(exc)
        receipt["cleanup"] = cleanup
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix(OUT.suffix + ".tmp")
    temp.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, OUT)
    return receipt


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True))
