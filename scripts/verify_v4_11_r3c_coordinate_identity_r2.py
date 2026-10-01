"""Preserve the old regression evidence and prove real-slot identity neutrality."""
from __future__ import annotations

from datetime import datetime,timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from scripts.characterize_v4_11_r3c_coordinate_identity import ROOT,binding,bound,atomic
from src.v4.state_identity import canonical,digest

OUT = ROOT / "reports/v4_11_r3"
ARCHIVE = OUT / "superseded/confirmation_d2_upstream_r3.py.attempt_R2"
RUNTIME = ROOT / "src/v4/confirmation_d2_upstream_r3.py"
TEST = ROOT / "tests/v4_11_r3c/test_upstream_source_admission.py"
PARENT = OUT / "V4_11_R3C_COORDINATE_SOURCE_CHARACTERIZATION_R1.json"


def atomic_bytes(path,data):
    import os
    fd,temporary = tempfile.mkstemp(prefix=".coordinate-evidence-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def test_receipt(*,archive=False):
    with tempfile.TemporaryDirectory(prefix=".coordinate-tests-",dir=OUT) as temporary:
        xml = Path(temporary)/"receipt.xml"
        arguments = ["tests/v4_11_r3c/test_upstream_source_admission.py","-q","--junitxml="+str(xml)]
        if archive:
            code = "\n".join([
                "import importlib.machinery, importlib.util, sys, pytest",
                "from pathlib import Path",
                "archive = Path("+repr(str(ARCHIVE))+")",
                "loader = importlib.machinery.SourceFileLoader('src.v4._coordinate_upstream_review_r2',str(archive))",
                "spec = importlib.util.spec_from_loader(loader.name,loader)",
                "module = importlib.util.module_from_spec(spec)",
                "sys.modules[loader.name] = module",
                "loader.exec_module(module)",
                "class ArchivedRuntimePlugin:",
                "    def pytest_collection_modifyitems(self,session,config,items):",
                "        for item in items:",
                "            if item.module.__name__.endswith('test_upstream_source_admission'):",
                "                item.module.derive = module.derive",
                "raise SystemExit(pytest.main("+repr(arguments)+",plugins=[ArchivedRuntimePlugin()]))",
            ])
            command = [sys.executable,"-c",code]
        else:
            command = [sys.executable,"-m","pytest",*arguments]
        result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding="utf8")
        if not xml.exists():
            raise RuntimeError(result.stdout+result.stderr)
        data = xml.read_bytes()
        suites = ET.fromstring(data).findall("testsuite")
        counts = {key:sum(int(s.attrib.get(key,"0")) for s in suites) for key in ("tests","failures","errors","skipped")}
        expected = dict(tests=11,failures=2 if archive else 0,errors=0,skipped=0)
        if counts != expected or result.returncode != (1 if archive else 0):
            raise RuntimeError("COORDINATE_TARGETED_TEST_RESULT_CHANGED:"+json.dumps(counts)+"\n"+result.stdout+result.stderr)
        name = "V4_11_R3C_UPSTREAM_SOURCE_ADMISSION_INITIAL_R2.xml" if archive else "V4_11_R3C_UPSTREAM_SOURCE_ADMISSION_FINAL_R2.xml"
        final_xml = OUT/name
        atomic_bytes(final_xml,data)
        return dict(runtime="ARCHIVED_R2_PRE_REPAIR" if archive else "FINAL_EXACT_CANONICAL_DECIMAL_RUNTIME",
            test_source=binding(TEST),runtime_source=binding(ARCHIVE if archive else RUNTIME),
            xml=binding(final_xml),exit_code=result.returncode,counts=counts,
            passed=counts["tests"]-counts["failures"]-counts["errors"]-counts["skipped"],
            stdout=result.stdout,stderr=result.stderr,
            scope="ENGINEERING_ONLY_NOT_MARKET_FACT_PUBLICATION_OR_EXTERNAL_ACCEPTANCE")


def main():
    parent_ref = binding(PARENT)
    parent = bound(parent_ref)
    if parent["actual_ready_domain_result"] != "PASS_EXACT_NUMERIC_EQUIVALENCE":
        raise ValueError("ACTUAL_DOMAIN_CHARACTERIZATION_MUST_PASS_FIRST")
    before = {"archive":binding(ARCHIVE),"final_runtime":binding(RUNTIME),"tests":binding(TEST)}
    by_date = {}
    for day,item in sorted(parent["by_date"].items()):
        rows = bound(item["source"])
        counts = dict(entities=len(rows),price_ready_slots=0,exact_coordinate_string_mismatches=0,adjustment_basis_digest_mismatches=0)
        examples = []
        identity_proofs = []
        for row in rows:
            for slot in row["window"]:
                if slot.get("has_actual_bar") is not True:
                    continue
                counts["price_ready_slots"] += 1
                old = [str(Decimal(str(slot[key])).normalize()) for key in ("mul","add")]
                new = [canonical(Decimal(str(slot[key]))) for key in ("mul","add")]
                string_equal,identity_equal = old == new,digest(old) == digest(new)
                counts["exact_coordinate_string_mismatches"] += not string_equal
                counts["adjustment_basis_digest_mismatches"] += not identity_equal
                identity_proofs.append(dict(security_id=row["security_id"],trade_date=slot["date"],
                    old_coordinate=old,new_coordinate=new,old_adjustment_basis_id=digest(old),new_adjustment_basis_id=digest(new)))
                if not string_equal or not identity_equal:
                    examples.append(identity_proofs[-1])
        if counts["exact_coordinate_string_mismatches"] or counts["adjustment_basis_digest_mismatches"]:
            raise ValueError("ACTUAL_SOURCE_IDENTITY_NOT_NEUTRAL:"+day)
        if counts["price_ready_slots"] != item["counts"]["price_ready_slots"]:
            raise ValueError("ACTUAL_SOURCE_CHARACTERIZATION_SLOT_COUNT_CHANGED")
        by_date[day] = dict(source=item["source"],counts=counts,
            coordinate_and_basis_identity_all_slots_exact=True,
            per_slot_coordinate_identity_proof_digest=digest(identity_proofs),mismatch_examples=examples[:5])
    initial = test_receipt(archive=True)
    final = test_receipt()
    after = {"archive":binding(ARCHIVE),"final_runtime":binding(RUNTIME),"tests":binding(TEST)}
    if before != after:
        raise ValueError("RUNTIME_CHANGED_DURING_CHARACTERIZATION")
    report = dict(contract_id="V4_11_R3C_COORDINATE_ACTUAL_SOURCE_EQUIVALENCE_R2",
        scope="ENGINEERING_FIX_AND_SOURCE_IDENTITY_PROOF_ONLY",captured_at_utc=datetime.now(timezone.utc).isoformat(),
        predecessor=parent_ref,script=binding(Path(__file__)),bindings=after,by_date=by_date,
        initial_regression_preserved=initial,final_targeted_tests=final,
        actual_price_ready_slots_checked=sum(item["counts"]["price_ready_slots"] for item in by_date.values()),
        all_actual_coordinate_strings_exact=True,all_actual_adjustment_basis_digests_exact=True,
        fix="Replace context-sensitive Decimal.normalize with exact state_identity.canonical(Decimal(str(value))) text; preserve current real source coordinate strings and digests",
        raw_and_adjusted_source_files_modified=False,accepted_R3A_seal_modified=False,
        arithmetic_and_thresholds_changed=False,real_R2_source_manifest_payloads_need_numeric_repair=False,
        sealed_source_set_reuse_requires_new_runtime_authority=True,
        audit_item=dict(audit_id="AUD-R3C-ADJUSTMENT-COORDINATE-EXACTNESS-R1",
            scope="Signed-zero and Decimal-context precision adjustment identity; independently tracked from current stage gate",
            disposition="ENGINEERING_REPAIRED_ACTUAL_SOURCE_IDENTITIES_EXACT_EXTERNAL_ACCEPTANCE_PENDING",
            acceptance="ENGINEERING_ONLY_NOT_EXTERNAL_ACCEPTED"),
        source_arithmetic_review=dict(suspension="Only explicit accepted SUSPENDED becomes CONFIRMED_SUSPENSION; absent/MISSING/UNKNOWN remain unexplained gap",
            price_unavailable="Raw actual bar with missing adjustment remains ADJUSTMENT_UNKNOWN and cannot be inferred suspended",
            prior_fields="compute_core(observations[:-1], asof=immediate prior session); immediate prior close never substituted with last observed close",
            rps_delta_units="R3A fractional rps5_delta3 multiplied by100 into accepted D2 percentage points",
            history_limit="Only source-window-supported factors become known; insufficient 60/250-bar diagnostics stay UNKNOWN"),
        accepted=False,AS_RECORDED=False,StageHead="KEEP",DataHead="KEEP",V4_12_runtime=False,
        next_stage="Final runtime-authorized candidate D2 readback in clean checkout; independent external acceptance remains pending",
        permissions=dict(production=False,shadow=False,focus=False,global_mandatory_adoption=False))
    destination = OUT/"V4_11_R3C_COORDINATE_SOURCE_CHARACTERIZATION_R2.json"
    atomic(destination,report)
    print(json.dumps(dict(report=destination.relative_to(ROOT).as_posix(),actual_price_ready_slots_checked=report["actual_price_ready_slots_checked"],
        initial_counts=initial["counts"],final_counts=final["counts"],all_actual_coordinate_strings_exact=True,
        all_actual_adjustment_basis_digests_exact=True)))


if __name__ == "__main__":
    main()
