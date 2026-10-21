"""Fail-closed R8 append evidence comparator.

Memory snapshots are useful engineering vectors, but they cannot prove source
bytes, historical identity, or a PostgreSQL append.  The corresponding gates
stay closed until their independently bound evidence is supplied.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


CONTRACT_ID = "V4_R8_CANDIDATE_APPEND_COMPARATOR_R2"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha(value):
    return (isinstance(value, str) and len(value) == 64 and
            all(char in "0123456789abcdef" for char in value.lower()))


def _read_binding(root, binding):
    """Read a G-workspace-relative binding and independently verify its bytes."""
    if not isinstance(binding, dict):
        raise ValueError("BINDING_NOT_AN_OBJECT")
    rel = binding.get("path")
    if not isinstance(rel, str) or not rel.strip():
        raise ValueError("BINDING_PATH_MISSING")
    base = Path(root).resolve()
    path = (base / rel).resolve()
    if path == base or base not in path.parents:
        raise ValueError("BINDING_PATH_ESCAPES_ROOT")
    raw = path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    if binding.get("bytes") != len(raw) or binding.get("sha256") != actual_sha:
        raise ValueError("BINDING_BYTES_OR_SHA_MISMATCH")
    return raw, dict(path=Path(rel).as_posix(), bytes=len(raw), sha256=actual_sha)


def _g2_identity_preserved(root, reference_snapshot, candidate_snapshot):
    reference = reference_snapshot.get("historical_identity_binding")
    candidate = candidate_snapshot.get("historical_identity_binding")
    if not reference or not candidate:
        return False, "G2_BOUND_HISTORICAL_IDENTITY_BYTES_REQUIRED"
    try:
        reference_bytes, reference_meta = _read_binding(root, reference)
        candidate_bytes, candidate_meta = _read_binding(root, candidate)
    except (OSError, ValueError) as exc:
        return False, "G2_" + str(exc)
    if reference_meta["sha256"] != candidate_meta["sha256"] or reference_bytes != candidate_bytes:
        return False, "G2_HISTORICAL_IDENTITY_BYTES_CHANGED"
    return True, None


def _g3_source_digest(root, source_bindings, *, parameters, window, previous_ref,
                      expected_g3_digest):
    if not isinstance(source_bindings, list) or not source_bindings:
        return False, "G3_SOURCE_BINDINGS_REQUIRED", None
    if parameters is None or window is None or previous_ref is None:
        return False, "G3_PARAMETERS_WINDOW_AND_PREVIOUS_REF_REQUIRED", None
    if not _sha(expected_g3_digest):
        return False, "G3_EXPECTED_OWNER_DIGEST_REQUIRED", None
    verified = []
    try:
        for binding in source_bindings:
            _, actual = _read_binding(root, binding)
            owner = binding.get("owner")
            if not isinstance(owner, str) or not owner.strip():
                return False, "G3_OWNER_NAME_REQUIRED", None
            verified.append({"owner": owner, **actual})
    except (OSError, ValueError) as exc:
        return False, "G3_" + str(exc), None
    actual_digest = _digest({"source_bindings": verified, "parameters": parameters,
                             "window": window, "previous_ref": previous_ref})
    if actual_digest != expected_g3_digest:
        return False, "G3_RECOMPUTED_DIGEST_MISMATCH", actual_digest
    return True, None, actual_digest


def compare_candidate_append(*, formal_predecessor, candidate_predecessor,
                             reference_snapshot, candidate_snapshot, target_session,
                             compute_sessions, source_bindings, revisions_detected=False,
                             root=None, parameters=None, window=None, previous_ref=None,
                              expected_g3_digest=None, pg_receipt_binding=None,
                              pg_schema=None, pg_database_identity=None):
    """Compare candidate evidence without treating caller assertions as proof.

    G1 remains a scoped value comparison. G2/G3 require actual bound bytes.
    G4 requires a PG-produced append receipt; a boolean or date list is not
    sufficient evidence of a write, CAS, idempotency, recovery, or readback.
    """
    errors = []
    formal_ok = (isinstance(formal_predecessor, dict) and
                 formal_predecessor.get("accepted") is True and
                 _sha(formal_predecessor.get("head_sha256")))
    if not formal_ok:
        errors.append("FORMAL_ACCEPTED_PREDECESSOR_NOT_PROVEN")

    candidate_identity_ok = (isinstance(candidate_predecessor, dict) and
        candidate_predecessor.get("accepted") is False and
        candidate_predecessor.get("evidence_class") == "NON_PIT")
    if candidate_predecessor and not candidate_identity_ok:
        errors.append("CANDIDATE_PREDECESSOR_IDENTITY_INVALID")

    g1_pass = (isinstance(reference_snapshot, dict) and
               isinstance(candidate_snapshot, dict) and
               reference_snapshot.get("business_values") == candidate_snapshot.get("business_values") and
               reference_snapshot.get("business_values") is not None)
    if not g1_pass:
        errors.append("G1_BUSINESS_SNAPSHOT_MISMATCH")

    g2_pass, g2_error = (False, "G2_ROOT_REQUIRED")
    if root is not None and isinstance(reference_snapshot, dict) and isinstance(candidate_snapshot, dict):
        g2_pass, g2_error = _g2_identity_preserved(root, reference_snapshot, candidate_snapshot)
    if not g2_pass:
        errors.append(g2_error)

    g3_pass, g3_error, source_digest = (False, "G3_ROOT_REQUIRED", None)
    if root is not None:
        g3_pass, g3_error, source_digest = _g3_source_digest(
            root, source_bindings, parameters=parameters, window=window,
            previous_ref=previous_ref, expected_g3_digest=expected_g3_digest)
    if not g3_pass:
        errors.append(g3_error)

    g4_pass = False
    if root is not None and isinstance(pg_receipt_binding, dict) and isinstance(pg_schema,str):
        try:
            raw, _ = _read_binding(root, pg_receipt_binding)
            receipt = json.loads(raw)
            # G4 is an independent, read-only database check. Values in the
            # receipt are bindings for comparison, never proof of the write.
            from workbench_db.v4_native import connection
            with connection(pg_schema, read_only=True) as pg:
                identity = pg.execute("SELECT current_database(), (SELECT oid FROM pg_database WHERE datname=current_database()), inet_server_addr()::text, inet_server_port()",()).fetchone()
                db_identity = {"database":identity[0],"database_oid":identity[1],"host":identity[2],"port":identity[3]}
                row = pg.execute("SELECT candidate_token,trade_date::text,predecessor_head_sha256,candidate_head_sha256,owner_authority_sha256,source_freeze_sha256,readback FROM r8_publications WHERE candidate_token=%s",(receipt.get("candidate_token"),)).fetchone()
                event = pg.execute("SELECT event_type,row_sha256,evidence FROM r8_publication_events WHERE candidate_token=%s ORDER BY event_id DESC LIMIT 1",(receipt.get("candidate_token"),)).fetchone()
                expected_row_sha = _digest([*row[:6],row[6]]) if row else None
                tx_raw, _ = _read_binding(root, receipt.get("publication_transaction")) if receipt.get("publication_transaction") else (b"",None)
                tx = json.loads(tx_raw) if tx_raw else {}
                head_path = Path(root) / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json"
                actual_head_sha = hashlib.sha256(head_path.read_bytes()).hexdigest()
            pg_matches = bool(row and event and event[0] == "FINALIZED" and event[1] == expected_row_sha
                and event[2].get("readback") == receipt.get("readback")
                and event[2].get("transaction_sha256") == hashlib.sha256(tx_raw).hexdigest()
                and row[:6] == (receipt.get("candidate_token"),target_session,receipt.get("predecessor_head_sha256"),
                    receipt.get("candidate_head_sha256"),receipt.get("owner_authority",{}).get("sha256"),
                    receipt.get("source_freeze",{}).get("sha256"))
                and row[6].get("status") == "PENDING"
                and receipt.get("pg_row_sha256") == expected_row_sha
                and db_identity == pg_database_identity
                and receipt.get("pg_database_identity") == db_identity
                and tx.get("state") == "COMMITTED" and tx.get("candidate_token") == receipt.get("candidate_token")
                and tx.get("head_sha256") == actual_head_sha == receipt.get("candidate_head_sha256"))
            required = (receipt.get("contract_id") == "V4_R8_REAL_APPEND_PG_RECEIPT_R2" and
                receipt.get("trade_date") == target_session and
                receipt.get("compute_sessions") == [target_session] and
                receipt.get("candidate_only") is True and
                receipt.get("formal_head_modified") is False and
                receipt.get("production_accepted") is False and
                receipt.get("cas_result") in ("APPLIED", "IDEMPOTENT") and
                receipt.get("write_count") == 1 and
                receipt.get("duplicate_write_count") == 0 and
                receipt.get("last_good_preserved_on_failure") is True)
            g4_pass = bool(required and pg_matches and list(compute_sessions or []) == [target_session]
                            and not revisions_detected)
            if not required:
                errors.append("G4_PG_RECEIPT_FIELDS_INVALID")
            elif not pg_matches:
                errors.append("G4_INDEPENDENT_PG_HEAD_TRANSACTION_READBACK_MISMATCH")
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append("G4_PG_RECEIPT_BYTES_INVALID")
    elif revisions_detected:
        errors.append("REVISION_REQUIRES_RANGE_REPAIR")
    else:
        errors.append("G4_REAL_PG_OPERATION_REQUIRED")
    if not g4_pass and revisions_detected and "REVISION_REQUIRES_RANGE_REPAIR" not in errors:
        errors.append("REVISION_REQUIRES_RANGE_REPAIR")
    if not g4_pass and list(compute_sessions or []) != [target_session]:
        errors.append("G4_APPEND_SCOPE_INVALID")

    gates = (formal_ok, g1_pass, g2_pass, g3_pass, g4_pass)
    status = "PASS" if all(gates) else "FAIL_CLOSED"
    return dict(contract_id=CONTRACT_ID, version="2.0.0", status=status,
        T0=target_session, formal_predecessor_accepted=formal_ok,
        candidate_predecessor_used_as_formal=False,
        candidate_predecessor_non_pit=candidate_identity_ok,
        G1="PASS" if g1_pass else "FAIL", G2="PASS" if g2_pass else "FAIL",
        G3="PASS" if g3_pass else "FAIL", G4="PASS" if g4_pass else "FAIL",
        reference_snapshot_sha256=_digest(reference_snapshot) if isinstance(reference_snapshot, dict) else None,
        candidate_snapshot_sha256=_digest(candidate_snapshot) if isinstance(candidate_snapshot, dict) else None,
        source_binding_count=len(source_bindings or []),
        recomputed_source_digest=source_digest, errors=errors,
        writes_performed=False, head_modified=False, production_admission=False,
        evidence_class="REAL_EVIDENCE_REQUIRED" if status != "PASS" else "BOUND_APPEND_EVIDENCE")
