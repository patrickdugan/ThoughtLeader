from typing import Any, Dict, List, Set, Tuple


POLISH_THRESHOLDS = {
    "effects_per_reaction": 4.5,
    "reactions_per_option": 2.5,
    "options_per_encounter": 3.2,
    "desirability_vars_per_reaction": 1.6,
    "act2_gate_pct": 5.0,
    "act2_gate_vars": 1.2,
    "act3_gate_pct": 8.0,
    "act3_gate_vars": 1.5,
    "secret_reachability_pct": 5.0,
}


def collect_vars(script: Any, out: Set[Tuple[str, str]]) -> None:
    if script is None:
        return
    if isinstance(script, dict):
        if script.get("pointer_type") == "Bounded Number Pointer":
            char = script.get("character")
            keyring = script.get("keyring") or []
            if char and keyring:
                out.add((char, keyring[0]))
        for v in script.values():
            collect_vars(v, out)
    elif isinstance(script, list):
        for v in script:
            collect_vars(v, out)


def count_vars(script: Any) -> int:
    out: Set[Tuple[str, str]] = set()
    collect_vars(script, out)
    return len(out)


def script_has_operator(script: Any, operator_type: str) -> bool:
    if isinstance(script, dict):
        if script.get("operator_type") == operator_type:
            return True
        for v in script.values():
            if script_has_operator(v, operator_type):
                return True
    elif isinstance(script, list):
        for v in script:
            if script_has_operator(v, operator_type):
                return True
    return False


def _script_is_constant(script: Any) -> bool:
    if not isinstance(script, dict):
        return True
    if script.get("script_element_type") == "Pointer":
        return script.get("pointer_type") in (
            "Bounded Number Constant",
            "Boolean Constant",
            "String Constant",
        )
    if script.get("script_element_type") == "Operator":
        operands = script.get("operands", []) or []
        if not operands:
            return True
        return all(_script_is_constant(op) for op in operands)
    return True


def _is_super_secret_encounter(encounter: Dict[str, Any]) -> bool:
    if (encounter.get("id") or "").startswith("page_secret_"):
        return True
    for option in encounter.get("options", []) or []:
        if option.get("secret") is True:
            return True
        vis = option.get("visibility_script")
        if isinstance(vis, dict) and vis.get("pointer_type") != "Boolean Constant":
            return True
    return False


def is_visibility_gated(script: Any) -> bool:
    if script is True:
        return False
    if isinstance(script, dict) and script.get("pointer_type") == "Boolean Constant":
        return not bool(script.get("value", False)) if script.get("value") is not None else True
    return True


def compute_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    encounters = data.get("encounters", [])
    enc_by_id = {e.get("id"): e for e in encounters if e.get("id")}

    total_options = 0
    total_reactions = 0
    total_effects = 0
    desirability_vars: List[int] = []

    enc_with_options = 0
    for enc in encounters:
        options = enc.get("options", []) or []
        if options:
            enc_with_options += 1
        total_options += len(options)
        for opt in options:
            reactions = opt.get("reactions", []) or []
            total_reactions += len(reactions)
            for rxn in reactions:
                effects = rxn.get("after_effects", []) or []
                total_effects += len(effects)
                desirability_vars.append(count_vars(rxn.get("desirability_script")))

    effects_per_reaction = (total_effects / total_reactions) if total_reactions else 0.0
    reactions_per_option = (total_reactions / total_options) if total_options else 0.0
    options_per_encounter = (total_options / enc_with_options) if enc_with_options else 0.0
    desirability_vars_avg = (sum(desirability_vars) / len(desirability_vars)) if desirability_vars else 0.0

    spools = data.get("spools", [])
    act2_ids = set()
    act3_ids = set()
    for sp in spools:
        name = (sp.get("spool_name") or "").lower()
        sid = (sp.get("id") or "").lower()
        ids = sp.get("encounters", []) or []
        if "act ii" in name or "act2" in sid or "act_2" in sid:
            act2_ids.update(ids)
        if "act iii" in name or "act3" in sid or "act_3" in sid:
            act3_ids.update(ids)

    def gate_stats(enc_ids):
        opts = 0
        gated = 0
        gated_vars = []
        for eid in enc_ids:
            enc = enc_by_id.get(eid)
            if not enc:
                continue
            for opt in enc.get("options", []) or []:
                opts += 1
                vis = opt.get("visibility_script", True)
                if is_visibility_gated(vis):
                    gated += 1
                    gated_vars.append(count_vars(vis))
        pct = (gated / opts * 100.0) if opts else 0.0
        avg_vars = (sum(gated_vars) / len(gated_vars)) if gated_vars else 0.0
        return pct, avg_vars, opts, gated

    act2_pct, act2_vars, act2_opts, act2_gated = gate_stats(act2_ids)
    act3_pct, act3_vars, act3_opts, act3_gated = gate_stats(act3_ids)

    secret_candidates = [enc for enc in encounters if _is_super_secret_encounter(enc)]
    super_secret_accessible = 0
    super_secret_candidates = len(secret_candidates)
    for enc in secret_candidates:
        if not _script_is_constant(enc.get("acceptability_script", 0.0)):
            super_secret_accessible += 1
    super_secret_access_pct = (super_secret_accessible / super_secret_candidates) if super_secret_candidates else 0.0

    secret_checks = []
    for enc in encounters:
        eid = enc.get("id", "")
        if eid.startswith("page_secret_"):
            acc = enc.get("acceptability_script")
            vars_count = count_vars(acc)
            has_distance = script_has_operator(acc, "Absolute Value")
            secret_checks.append((eid, vars_count, has_distance))

    return {
        "effects_per_reaction": effects_per_reaction,
        "reactions_per_option": reactions_per_option,
        "options_per_encounter": options_per_encounter,
        "desirability_vars_avg": desirability_vars_avg,
        "act2": (act2_pct, act2_vars, act2_opts, act2_gated),
        "act3": (act3_pct, act3_vars, act3_opts, act3_gated),
        "super_secret_access_pct": super_secret_access_pct,
        "secret_checks": secret_checks,
    }
