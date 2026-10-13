"""Real R3 candidate admission into the byte-frozen V4-10 reducer rules.

The adapter extracts the accepted function AST and changes only admission,
candidate mode/identity and output validation. Its publications never enter the
accepted engineering ledger. Every implemented field resolves from an external
sealed file manifest; serialized inputs cannot supply a resolver.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import date, datetime, timezone
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path

from . import research_state, state_provenance
from .state_identity import CANONICALIZATION, digest

ROOT = Path(__file__).resolve().parents[2]
MODE = "REAL_CANDIDATE_INTERFACE"
INTERFACE = "V4_11_R3C_CANDIDATE_D2_INTERFACE_V1"
CONTRACT = "V4_11_R3C_CANDIDATE_D2_BRIDGE_V1"
ROW_PREFIX = "V4_11_R3C_D2_ROW:"
CONFIG = "config/v4_11_r3c_candidate_d2_contract_v3.json"
PERMISSIONS = dict(production=False, shadow=False, focus=False, global_mandatory_adoption=False)


@lru_cache(maxsize=8)
def _read(name):
    return json.loads((ROOT / f"config/v4_10_{name}_r1_2.json").read_bytes())


def exact(ref):
    path = (ROOT / ref["path"]).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError("CANDIDATE_BINDING_OUTSIDE_WORKSPACE_OR_MISSING")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != ref["sha256"] or len(data) != ref.get("bytes", ref.get("byte_count")):
        raise ValueError("CANDIDATE_SOURCE_BYTE_BINDING_MISMATCH")
    return path


def bound(ref):
    path = exact(ref)
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes())


def aware(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("CANDIDATE_AWARE_KNOWLEDGE_CUTOFF_REQUIRED")
    return result


@lru_cache(maxsize=1)
def candidate_policy():
    policy = deepcopy(_read("input_provenance"))
    policy["fields"]["CONFIRMED"].update(implemented=True,
        producer_contract_id="CONFIRMATION_DETECTOR_V1", producer_parameter_set_id="V4_11_CONFIRMATION_PARAMETER_SET_V1")
    policy["fields"]["scenario"].update(implemented=True,
        producer_contract_id="CONFIRMATION_DETECTOR_V1", producer_parameter_set_id="V4_11_CONFIRMATION_PARAMETER_SET_V1")
    return policy


def candidate_envelope(field, value, status, *, session_index, trade_date,
                       system_available_at, publication_id=None, payload_extra=None):
    definition = candidate_policy()["fields"][field]
    unavailable = status in ("NOT_IMPLEMENTED", "NOT_APPLICABLE")
    payload = dict(field=field, value=value, session_index=session_index, trade_date=trade_date)
    payload.update(payload_extra or {})
    return dict(field=field, value=value, quality="UNKNOWN" if value == "UNKNOWN" else "KNOWN", status=status,
        producer_contract_id=definition["producer_contract_id"], producer_parameter_set_id=definition["producer_parameter_set_id"],
        publication_id=None if unavailable else publication_id,
        source_output_digest=None if unavailable else digest(payload), source_field_payload={} if unavailable else payload,
        time_role=definition["time_role"], required=definition["required"],
        system_available_at=None if unavailable else system_available_at)


def seal_fact_manifest(material):
    material = {k: v for k, v in material.items() if k != "publication_id"}
    return dict(material, publication_id="V4_11_R3C_FACT:" + digest(material))


def input_skeleton(*, entity_id, trade_date, session_index, cutoff, calendar_manifest,
                   fields, prior_state=None, prior_publication_id=None):
    ids = sorted({f["publication_id"] for f in fields.values() if f["publication_id"]})
    binding = None if prior_state is None else dict(publication_id=prior_state["publication_id"],
        payload_digest=digest(prior_state), engineering_publication_id=prior_publication_id,
        ledger_id="V4_11_R3C_SEALED_FILE_CANDIDATE_LEDGER_V1")
    return dict(interface_contract_id=INTERFACE, entity_id=entity_id, entity_type="STOCK", trade_date=trade_date,
        session_index=session_index, calendar_publication_id=calendar_manifest["publication_id"],
        calendar_binding=dict(publication_id=calendar_manifest["publication_id"],
            manifest_digest=digest({k:v for k,v in calendar_manifest.items() if k != "publication_id"}),
            lineage_id=calendar_manifest["lineage_id"]), mode=MODE, cutoff=cutoff,
        input_publication_ids=ids, input_provenance=fields,
        input_publication_manifest_digest=digest(dict(input_publication_ids=ids, fields=fields)),
        prior_state=prior_state, prior_state_binding=binding, model_boundary={"status": "NONE"},
        bootstrap_status="NOT_BOOTSTRAP" if prior_state else "LEFT_CENSORED_NO_PRIOR_PUBLICATION")


def admission_context(producer_set, *, prior_binding=None, lineage_seen=None):
    # Recheck trust at each batch boundary; memoization is only inside a batch.
    research_state.load_package()
    _read.cache_clear()
    candidate_policy.cache_clear()
    _candidate_package.cache_clear()
    config = json.loads((ROOT / CONFIG).read_bytes())
    if config.get("contract_id") != CONTRACT or config.get("permissions") != PERMISSIONS:
        raise ValueError("CANDIDATE_D2_AUTHORITY_CONTRACT_INVALID")
    if producer_set not in config.get("authorized_source_sets", []):
        raise ValueError("CANDIDATE_D2_SOURCE_SET_NOT_AUTHORIZED_OUT_OF_BAND")
    for key, source_path in (("accepted_reducer_source", Path(research_state.__file__)),
                             ("accepted_provenance_source", Path(state_provenance.__file__))):
        ref = config.get(key)
        if not ref or (ROOT / ref["path"]).resolve() != source_path.resolve():
            raise ValueError("CANDIDATE_ACCEPTED_RUNTIME_BINDING_REQUIRED")
        exact(ref)
    for key in ("exact_owner_runtime", "exact_owner_parameters"):
        for ref in config.get(key, []):
            exact(ref)
    source_set = bound(producer_set)
    if source_set.get("contract_id") != "V4_11_R3C_D2_SOURCE_SET_V1" or source_set.get("mode") != MODE or source_set.get("accepted") is not False:
        raise ValueError("CANDIDATE_D2_SEALED_SOURCE_SET_REQUIRED")
    if source_set.get("permissions") != PERMISSIONS:
        raise ValueError("CANDIDATE_D2_SOURCE_PERMISSIONS_INVALID")
    for key in ("r3a_seal", "r3b_seal"):
        if source_set.get(key) != config.get(key):
            raise ValueError("CANDIDATE_D2_PARENT_PRODUCER_SEAL_MISMATCH")
        seal = bound(source_set[key])
        expected = "V4_11_R3A_TARGET_FACT_PRODUCERS_CANDIDATE_READY" if key == "r3a_seal" else "V4_11_R3B_EPISODE_SAFETY_LOO_CANDIDATE_READY"
        if seal.get("status") != expected:
            raise ValueError("CANDIDATE_D2_PRODUCER_SET_NOT_SEALED")
        def verify_refs(value):
            if isinstance(value, dict):
                if {"path", "sha256"} <= set(value) and ("bytes" in value or "byte_count" in value):
                    exact(value)
                else:
                    for child in value.values():
                        verify_refs(child)
            elif isinstance(value, list):
                for child in value:
                    verify_refs(child)
        verify_refs(seal)
    calendar = bound(source_set["calendar"])
    source_calendar = bound(config["accepted_calendar_source"])
    dates = source_calendar.get("session_dates")
    if dates is None:
        dates = [r["trade_date"] for r in source_calendar["sessions"]]
    expected_sessions = [dict(trade_date=d, session_index=i) for i,d in enumerate(dates)]
    if calendar.get("sessions") != expected_sessions or calendar.get("producer_contract_id") != "MARKET_CALENDAR_V1":
        raise ValueError("CANDIDATE_CALENDAR_DIFFERS_FROM_ACCEPTED_SOURCE")
    material = {k:v for k,v in calendar.items() if k != "publication_id"}
    if calendar.get("publication_id") != "V4_11_R3C_CALENDAR:" + digest(material):
        raise ValueError("CANDIDATE_CALENDAR_PUBLICATION_ID_MISMATCH")
    allowed = {digest(ref) for ref in config["allowed_source_bindings"]}
    manifests = {}
    for ref in source_set["publications"]:
        manifest = bound(ref)
        if manifest.get("contract_id") != "V4_11_R3C_STATE_INPUT_FACT_PUBLICATION_V1" or manifest.get("mode") != MODE or manifest.get("accepted") is not False:
            raise ValueError("CANDIDATE_FACT_MANIFEST_SCOPE_INVALID")
        if seal_fact_manifest(manifest) != manifest:
            raise ValueError("CANDIDATE_FACT_PUBLICATION_DIGEST_MISMATCH")
        refs = manifest.get("source_bindings", [])
        if not refs or any(digest(r) not in allowed for r in refs):
            raise ValueError("CANDIDATE_FACT_SOURCE_OUTSIDE_AUTHORIZED_BINDINGS")
        for source in refs:
            exact(source)
        if manifest.get("AS_RECORDED") is not False or manifest.get("knowledge_lineage") != "RECONSTRUCTED_CORRECTED":
            raise ValueError("CANDIDATE_FACT_HISTORICAL_AVAILABILITY_OVERCLAIM")
        pid = manifest["publication_id"]
        if pid in manifests:
            raise ValueError("DUPLICATE_CANDIDATE_SOURCE_PUBLICATION")
        entities = {(r["entity_id"], r["entity_type"]):r for r in manifest["rows"]}
        if len(entities) != len(manifest["rows"]):
            raise ValueError("DUPLICATE_CANDIDATE_SOURCE_ENTITY")
        manifests[pid] = (manifest, entities)
    prior = None
    if prior_binding:
        prior = bound(prior_binding)
        verify_candidate_d2_publication(prior, _lineage_seen=lineage_seen)
    return dict(config=config, source_set=source_set, producer_set=producer_set, calendar=calendar,
        manifests=manifests, prior_publication=prior,
        prior_rows={} if prior is None else {r["entity_id"]:r for r in prior["rows"]})


def _validate_inputs(inputs, context):
    x = deepcopy(inputs)
    policy = candidate_policy()
    if set(_read("input_schema")["required"]) - set(x) or x.get("mode") != MODE or x.get("interface_contract_id") != INTERFACE:
        raise ValueError("REAL_CANDIDATE_D2_INPUT_REQUIRED")
    if x["entity_type"] != "STOCK" or type(x["session_index"]) is not int or x["session_index"] < 0:
        raise ValueError("CANDIDATE_D2_ENTITY_SCOPE_INVALID")
    if x["model_boundary"] != {"status": "NONE"}:
        raise ValueError("BARE_OR_UNAUTHORIZED_MODEL_BOUNDARY_FORBIDDEN")
    if any(key.startswith("synthetic_") for key in x):
        raise ValueError("SYNTHETIC_CANDIDATE_INPUT_REJECTED")
    ids = state_provenance.publication_ids(x["input_publication_ids"])
    if ids != x["input_publication_ids"] or any(pid not in context["manifests"] for pid in ids):
        raise ValueError("CANDIDATE_PUBLICATION_NOT_IN_SEALED_SOURCE_SET")
    calendar = context["calendar"]
    mapping = {s["session_index"]:s["trade_date"] for s in calendar["sessions"]}
    expected_cal = dict(publication_id=calendar["publication_id"], manifest_digest=digest({k:v for k,v in calendar.items() if k != "publication_id"}), lineage_id=calendar["lineage_id"])
    if x["calendar_binding"] != expected_cal or x["calendar_publication_id"] != calendar["publication_id"] or mapping.get(x["session_index"]) != x["trade_date"]:
        raise ValueError("CANDIDATE_CALENDAR_IDENTITY_MISMATCH")
    cutoff = aware(x["cutoff"])
    if cutoff > datetime.now(timezone.utc):
        raise ValueError("CANDIDATE_FUTURE_KNOWLEDGE_CUTOFF")
    fields = x["input_provenance"]
    if set(fields) != set(policy["fields"]):
        raise ValueError("CANDIDATE_STATE_FIELD_MANIFEST_INCOMPLETE")
    if x["input_publication_manifest_digest"] != digest(dict(input_publication_ids=ids, fields=fields)):
        raise ValueError("CANDIDATE_INPUT_MANIFEST_DIGEST_MISMATCH")
    prior = x["prior_state"]
    if prior:
        if context["prior_publication"] is None or prior != context["prior_rows"].get(x["entity_id"]):
            raise ValueError("PRIOR_NOT_IN_SEALED_REAL_D2_PUBLICATION")
        if prior["trade_date"] != mapping.get(x["session_index"]-1) or prior["calendar_binding"] != expected_cal:
            raise ValueError("SAME_DAY_OR_NON_PRIOR_SESSION_D2_REJECTED")
        binding = dict(publication_id=prior["publication_id"], payload_digest=digest(prior),
            engineering_publication_id=context["prior_publication"]["publication_id"], ledger_id="V4_11_R3C_SEALED_FILE_CANDIDATE_LEDGER_V1")
        if x["prior_state_binding"] != binding:
            raise ValueError("CANDIDATE_PRIOR_STATE_BINDING_MISMATCH")
        validate_candidate_output(prior)
    elif x["prior_state_binding"] is not None or context["prior_rows"].get(x["entity_id"]) is not None:
        raise ValueError("CANDIDATE_PRIOR_STATE_OMITTED")
    elif x.get("bootstrap_status") != "LEFT_CENSORED_NO_PRIOR_PUBLICATION":
        raise ValueError("REAL_PRIOR_BOOTSTRAP_MUST_DECLARE_LEFT_CENSORING")
    values = {}
    for field, definition in policy["fields"].items():
        f = fields[field]
        if set(policy["envelope_required"]) - set(f) or f["field"] != field or f["required"] is not definition["required"] or f["time_role"] != definition["time_role"]:
            raise ValueError("CANDIDATE_FIELD_POLICY_MISMATCH:" + field)
        if (f["producer_contract_id"], f["producer_parameter_set_id"]) != (definition["producer_contract_id"], definition["producer_parameter_set_id"]):
            raise ValueError("CANDIDATE_WRONG_FIELD_PRODUCER_OR_PARAMETERS:" + field)
        value, status = f["value"], f["status"]
        if status == "IMPLEMENTED":
            if not definition["implemented"] or f["publication_id"] not in ids:
                raise ValueError("CANDIDATE_UNAUTHORIZED_FIELD_IMPLEMENTATION:" + field)
            manifest, entities = context["manifests"][f["publication_id"]]
            row = entities.get((x["entity_id"], x["entity_type"]))
            expected = {k:v for k,v in f.items() if k != "publication_id"}
            if row is None or row["fields"].get(field) != expected or manifest["calendar_publication_id"] != x["calendar_publication_id"]:
                raise ValueError("CANDIDATE_FIELD_NOT_IN_SEALED_SOURCE:" + field)
            payload = f["source_field_payload"]
            source_index = x["session_index"] if f["time_role"] == "T" else x["session_index"]-1
            if payload.get("field") != field or payload.get("value") != value or f["source_output_digest"] != digest(payload):
                raise ValueError("CANDIDATE_FIELD_PAYLOAD_DIGEST_MISMATCH:" + field)
            if payload.get("session_index") != source_index or payload.get("trade_date") != mapping.get(source_index) or manifest["trade_date"] != x["trade_date"]:
                raise ValueError("CANDIDATE_FIELD_TARGET_DATE_MISMATCH:" + field)
            if aware(f["system_available_at"]) > cutoff:
                raise ValueError("CANDIDATE_FUTURE_FIELD_REJECTED:" + field)
        elif status in ("NOT_IMPLEMENTED", "NOT_APPLICABLE"):
            if value != "UNKNOWN" or f["quality"] != "UNKNOWN" or f["publication_id"] is not None or f["source_output_digest"] is not None:
                raise ValueError("CANDIDATE_UNAVAILABLE_FACT_MUST_STAY_UNKNOWN:" + field)
            if status == "NOT_IMPLEMENTED" and definition["implemented"]:
                raise ValueError("CANDIDATE_IMPLEMENTED_OWNER_CANNOT_BE_OMITTED:" + field)
            if status == "NOT_APPLICABLE" and not (x["entity_type"] in definition["not_applicable_entity_types"] or
                    (field in ("frozen_invalidation", "episode_invalidation_contract_id") and prior is None)):
                raise ValueError("CANDIDATE_NOT_APPLICABLE_UNAUTHORIZED:" + field)
        else:
            raise ValueError("SYNTHETIC_OR_INVALID_FIELD_STATUS:" + field)
        if f["quality"] != ("UNKNOWN" if value == "UNKNOWN" else "KNOWN"):
            raise ValueError("CANDIDATE_FIELD_QUALITY_CONFLICT:" + field)
        domain = definition["domain"]
        if domain == "TRI" and value not in ("TRUE", "FALSE", "UNKNOWN"):
            raise ValueError("CANDIDATE_INVALID_TRI_STATE:" + field)
        if domain == "NUMBER" and value != "UNKNOWN" and (type(value) not in (int,float) or not math.isfinite(value)):
            raise ValueError("CANDIDATE_NONFINITE_METRIC:" + field)
        if domain == "RISK" and value not in ("LOW", "MEDIUM", "HIGH", "EXTREME", "UNKNOWN"):
            raise ValueError("CANDIDATE_INVALID_RISK")
        if domain == "SCENARIO" and value not in (*_read("output_schema")["axes"]["scenario"]["STOCK"], "UNKNOWN"):
            raise ValueError("CANDIDATE_INVALID_SCENARIO")
        values[field] = value
    if fields["WARM"]["status"] != "NOT_APPLICABLE":
        raise ValueError("CANDIDATE_STOCK_WARM_NOT_APPLICABLE_REQUIRED")
    x["detectors"] = {s:dict(value=values[s], status=fields[s]["status"], contract_id=fields[s]["producer_contract_id"],
        parameter_set_id=fields[s]["producer_parameter_set_id"], publication_id=fields[s]["publication_id"]) for s in ("CONFIRMED","WARM","PREWATCH","SEED")}
    x.update(core_price_damage=values["core_price_damage"], frozen_invalidation=dict(value=values["frozen_invalidation"],
        episode_id=fields["frozen_invalidation"]["source_field_payload"].get("episode_id"),
        contract_id=fields["frozen_invalidation"]["source_field_payload"].get("invalidation_contract_id")),
        episode_invalidation_contract_id=None if values["episode_invalidation_contract_id"] == "UNKNOWN" else values["episode_invalidation_contract_id"],
        risk=values["risk"], delta3=None if values["delta3"] == "UNKNOWN" else values["delta3"],
        dq5=None if values["dq5"] == "UNKNOWN" else values["dq5"],
        scenario=dict(value=values["scenario"], status="UNKNOWN" if values["scenario"] == "UNKNOWN" else "KNOWN"),
        suspended=values["suspended"], followup_complete=values["followup_complete"], model_boundary=False,
        provenance_unknown=[], authorized_boundary=None)
    return x


class AdmissionAdapter(ast.NodeTransformer):
    """Explicit changes are mechanically bounded; all reducer rules stay exact."""
    def __init__(self, output=False):
        self.output = output
        self.removed_admission_gate = 0
        self.mode_tuple_changes = 0
        self.cutoff_admission_changes = 0
        self.row_identity_changes = 0
        self.episode_identity_changes = 0

    def visit_If(self, node):
        if not self.output and any(isinstance(n, ast.Constant) and n.value == "UNACCEPTED_D0_D1_DETECTOR" for n in ast.walk(node)):
            self.removed_admission_gate += 1
            return None
        return self.generic_visit(node)

    def visit_Tuple(self, node):
        node = self.generic_visit(node)
        if [n.value for n in node.elts if isinstance(n, ast.Constant)] == ["SYNTHETIC_CONTRACT_VECTOR", "ACCEPTED_FACT_INTERFACE"]:
            node.elts = [ast.Constant(MODE)]
            self.mode_tuple_changes += 1
        return node

    def visit_Compare(self, node):
        # Reconstructed candidate availability is actual knowledge time. It is
        # deliberately not a historical target-date cutoff or PIT assertion.
        if self.output and ast.unparse(node) == "cutoff.date() != date.fromisoformat(row['trade_date'])":
            self.cutoff_admission_changes += 1
            return ast.Constant(False)
        return self.generic_visit(node)

    def visit_Constant(self, node):
        if not self.output and node.value == "V4_10:":
            self.row_identity_changes += 1
            return ast.Constant(ROW_PREFIX)
        if not self.output and node.value == "EP:":
            self.episode_identity_changes += 1
            return ast.Constant("V4_11_R3C_EP:")
        return node


@lru_cache(maxsize=1)
def _candidate_package():
    c, a, p = research_state.load_package()
    c = deepcopy(c)
    c["producer_contracts"]["CONFIRMED"] = "CONFIRMATION_DETECTOR_V1"
    c["producer_parameters"]["CONFIRMED"] = "V4_11_CONFIRMATION_PARAMETER_SET_V1"
    return c, a, p


@lru_cache(maxsize=1)
def extracted_runtime():
    research_state.load_package()  # validates byte-frozen accepted authority
    reducer_path = Path(research_state.__file__)
    validator_path = Path(state_provenance.__file__)
    reducer = next(n for n in ast.parse(reducer_path.read_text(encoding="utf8")).body if isinstance(n, ast.FunctionDef) and n.name == "reduce_state")
    output = next(n for n in ast.parse(validator_path.read_text(encoding="utf8")).body if isinstance(n, ast.FunctionDef) and n.name == "validate_output")
    adapter = AdmissionAdapter()
    reducer = adapter.visit(deepcopy(reducer))
    if adapter.removed_admission_gate != 1:
        raise ValueError("ACCEPTED_REDUCER_ADMISSION_AST_CHANGED")
    output = AdmissionAdapter(output=True).visit(deepcopy(output))
    validator_globals = dict(state_provenance.__dict__, _read=_read, INTERFACE=INTERFACE,
        state_id=lambda row: ROW_PREFIX + digest({k:v for k,v in row.items() if k != "publication_id"}))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[output], type_ignores=[])), "<R3C_candidate_output_admission>", "exec"), validator_globals)
    output_validator = validator_globals["validate_output"]
    reducer_globals = dict(research_state.__dict__, INTERFACE=INTERFACE, load_package=_candidate_package,
        validate_output=output_validator, validate_inputs=lambda inputs,context:_validate_inputs(inputs,context))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[reducer], type_ignores=[])), "<R3C_exact_reducer_rules_candidate_admission>", "exec"), reducer_globals)
    return reducer_globals["reduce_state"], output_validator


def validate_candidate_output(row):
    extracted_runtime()[1](row)
    if row["mode"] != MODE or row["interface_contract_id"] != INTERFACE:
        raise ValueError("CANDIDATE_D2_OUTPUT_NAMESPACE_REQUIRED")
    if row["state_freshness"] == "STALE" and (row["validity"] != "UNKNOWN" or row["health"] != "UNKNOWN"):
        raise ValueError("CANDIDATE_STALE_STATE_AXES_MUST_REMAIN_UNKNOWN")
    return row


def adapter_ast_evidence():
    """Mechanical, source-bound whitelist diff for the candidate admission AST.

    Normalize only the listed admission/mode/identity changes and compare the
    complete remaining AST. No numerical predicate, precedence, hysteresis,
    health, expiry, tracking or reentry statement is permitted to differ.
    """
    c, machine, parameters = research_state.load_package()
    sources = {"reducer": Path(research_state.__file__), "output_admission": Path(state_provenance.__file__)}
    functions = {}
    for key, path in sources.items():
        name = "reduce_state" if key == "reducer" else "validate_output"
        functions[key] = next(node for node in ast.parse(path.read_text(encoding="utf8")).body
            if isinstance(node, ast.FunctionDef) and node.name == name)
    transformed, adapters = {}, {}
    for key, function in functions.items():
        adapters[key] = AdmissionAdapter(output=key == "output_admission")
        transformed[key] = adapters[key].visit(deepcopy(function))

    class BusinessNormalization(ast.NodeTransformer):
        def visit_If(self, node):
            if any(isinstance(n,ast.Constant) and n.value == "UNACCEPTED_D0_D1_DETECTOR" for n in ast.walk(node)):
                return None
            return self.generic_visit(node)

        def visit_Constant(self, node):
            if node.value in ("V4_10:", ROW_PREFIX):
                return ast.Constant("AUDIT_ROW_NAMESPACE")
            if node.value in ("EP:", "V4_11_R3C_EP:"):
                return ast.Constant("AUDIT_EPISODE_NAMESPACE")
            return node

        def visit_Tuple(self, node):
            node = self.generic_visit(node)
            values = [n.value for n in node.elts if isinstance(n,ast.Constant)]
            if values in (["SYNTHETIC_CONTRACT_VECTOR", "ACCEPTED_FACT_INTERFACE"], [MODE]):
                node.elts = [ast.Constant("AUDIT_ADMISSION_MODE")]
            return node

        def visit_Compare(self, node):
            if ast.unparse(node) == "cutoff.date() != date.fromisoformat(row['trade_date'])":
                return ast.Constant(False)
            return self.generic_visit(node)

    bindings, comparisons = {}, {}
    for key,path in sources.items():
        data = path.read_bytes()
        bindings[key] = dict(path=path.relative_to(ROOT).as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        before = ast.dump(BusinessNormalization().visit(deepcopy(functions[key])), include_attributes=False)
        after = ast.dump(BusinessNormalization().visit(deepcopy(transformed[key])), include_attributes=False)
        if before != after:
            raise ValueError("CANDIDATE_ADAPTER_UNAUTHORIZED_BUSINESS_AST_DIFFERENCE")
        comparisons[key] = dict(source_AST_sha256=hashlib.sha256(ast.dump(functions[key],include_attributes=False).encode()).hexdigest(),
            candidate_AST_sha256=hashlib.sha256(ast.dump(transformed[key],include_attributes=False).encode()).hexdigest(),
            normalized_business_AST_sha256=hashlib.sha256(before.encode()).hexdigest(), normalized_business_AST_exact=True)
    reducer = adapters["reducer"]
    output = adapters["output_admission"]
    changes = dict(removed_unaccepted_D0_D1_admission_gate=reducer.removed_admission_gate,
        reducer_allowed_mode_tuple_changes=reducer.mode_tuple_changes,
        row_namespace_changes=reducer.row_identity_changes, episode_namespace_changes=reducer.episode_identity_changes,
        output_allowed_mode_tuple_changes=output.mode_tuple_changes,
        output_reconstructed_cutoff_admission_changes=output.cutoff_admission_changes)
    if any(value != 1 for value in changes.values()):
        raise ValueError("CANDIDATE_ADAPTER_CHANGE_WHITELIST_COUNT_MISMATCH")
    return dict(contract_id="V4_11_R3C_CANDIDATE_ADMISSION_AST_EVIDENCE_V1", accepted_source_bindings=bindings,
        mechanical_whitelist_changes=changes, business_AST_comparisons=comparisons,
        rule_order=machine["rule_order"], unchanged_parameter_set=parameters,
        exact_rule_order=True, exact_business_thresholds=True,
        admission_functions="New sealed-file candidate validate_inputs + candidate validate_output; old accepted ledger unchanged",
        capability_addition="CONFIRMATION_DETECTOR_V1 candidate producer identity, not acceptance",
        reconstructed_cutoff_scope="Actual knowledge timestamp; never historical first availability or AS_RECORDED",
        candidate_business_consumer_external_acceptance=False, accepted=False,
        candidate_namespace=INTERFACE, permissions=PERMISSIONS)


def candidate_d2_publication(inputs, *, producer_set, prior_publication=None, prior_binding=None, _lineage_seen=None):
    context = admission_context(producer_set, prior_binding=prior_binding, lineage_seen=_lineage_seen)
    if prior_publication is not None and context["prior_publication"] != prior_publication:
        raise ValueError("CANDIDATE_PRIOR_FILE_READBACK_MISMATCH")
    if not inputs or len({x["entity_id"] for x in inputs}) != len(inputs) or len({x["trade_date"] for x in inputs}) != 1:
        raise ValueError("CANDIDATE_D2_PUBLICATION_ENTITY_OR_DATE_INVALID")
    reduce, validate = extracted_runtime()
    rows = [reduce(x, ledger=context) for x in inputs]
    for row in rows:
        validate_candidate_output(row)
    material = dict(contract_id=CONTRACT, inputs=inputs, rows=rows, producer_set=producer_set, prior_binding=prior_binding,
        scope="REAL_SEALED_CANDIDATE_REPLAY_ONLY", accepted=False, AS_RECORDED=False,
        knowledge_lineage="RECONSTRUCTED_CORRECTED", permissions=PERMISSIONS,
        bootstrap_status="LEFT_CENSORED_NO_PRIOR_PUBLICATION" if prior_binding is None else "REAL_IMMEDIATE_PRIOR_CANDIDATE_D2")
    return dict(material, publication_id="V4_11_R3C_D2:" + digest(material))


def verify_candidate_d2_publication(publication, *, producer_set=None, _lineage_seen=None):
    if publication.get("scope") != "REAL_SEALED_CANDIDATE_REPLAY_ONLY" or publication.get("accepted") is not False:
        raise ValueError("REAL_CANDIDATE_D2_READBACK_REQUIRED")
    if producer_set is not None and publication.get("producer_set") != producer_set:
        raise ValueError("CANDIDATE_D2_SOURCE_SET_IDENTITY_MISMATCH")
    seen = set(_lineage_seen or ())
    if publication.get("publication_id") in seen:
        raise ValueError("CANDIDATE_D2_CIRCULAR_PRIOR_LINEAGE_REJECTED")
    seen.add(publication.get("publication_id"))
    rebuilt = candidate_d2_publication(publication["inputs"], producer_set=publication["producer_set"], prior_binding=publication["prior_binding"], _lineage_seen=seen)
    if rebuilt != publication:
        raise ValueError("CANDIDATE_D2_RULE_REEXECUTION_MISMATCH")
    return publication["rows"]
