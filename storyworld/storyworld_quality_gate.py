#!/usr/bin/env python3
"""Quality gate for one-shot storyworld generation."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from polish_metrics import POLISH_THRESHOLDS, compute_metrics, count_vars
from sweepweave_validator import validate_storyworld


def _word_count(script: Any) -> int:
    if isinstance(script, dict):
        if script.get("pointer_type") == "String Constant":
            return len(str(script.get("value", "")).split())
        total = 0
        for value in script.values():
            total += _word_count(value)
        return total
    if isinstance(script, list):
        return sum(_word_count(item) for item in script)
    return len(str(script).split()) if isinstance(script, str) else 0


def _collect_pointer_refs(node: Any, out: List[Tuple[str, int]]) -> None:
    if isinstance(node, dict):
        if node.get("pointer_type") == "Bounded Number Pointer":
            keyring = node.get("keyring") or []
            if keyring and isinstance(keyring, list):
                prop = str(keyring[0])
                out.append((prop, len(keyring)))
        for value in node.values():
            _collect_pointer_refs(value, out)
        return
    if isinstance(node, list):
        for item in node:
            _collect_pointer_refs(item, out)


def _belief_ref_kind(prop: str, depth: int) -> Optional[str]:
    prop = str(prop)
    if prop.startswith("p2") or depth >= 3:
        return "p2"
    if prop.startswith("p") or depth == 2:
        return "p1"
    return None


def _is_ending(encounter: Dict[str, Any]) -> bool:
    eid = str(encounter.get("id", ""))
    if eid.startswith("page_end") or eid.startswith("page_secret"):
        return True
    options = encounter.get("options", []) or []
    return len(options) == 0


def _safe_mean(values: Iterable[float]) -> float:
    vals = list(values)
    return float(mean(vals)) if vals else 0.0


def _check(name: str, actual: float, target: float) -> Dict[str, Any]:
    return {
        "name": name,
        "actual": round(actual, 4),
        "target": target,
        "pass": actual >= target,
    }


def _check_max(name: str, actual: float, target_max: float) -> Dict[str, Any]:
    return {
        "name": name,
        "actual": round(actual, 4),
        "target": target_max,
        "pass": actual <= target_max,
    }


def _collect_operators(node: Any, out: collections.Counter) -> None:
    if isinstance(node, dict):
        op = node.get("operator_type")
        if op:
            out[str(op)] += 1
        for value in node.values():
            _collect_operators(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_operators(item, out)


def _script_is_constant(script: Any) -> bool:
    if not isinstance(script, dict):
        return True
    if script.get("script_element_type") == "Pointer":
        return script.get("pointer_type") in ("Bounded Number Constant", "Boolean Constant", "String Constant")
    if script.get("script_element_type") == "Operator":
        ops = script.get("operands", [])
        if not ops:
            return True
        return all(_script_is_constant(op) for op in ops)
    return False


def _script_operator_count(script: Any) -> int:
    if isinstance(script, dict):
        c = 1 if script.get("operator_type") else 0
        for value in script.values():
            c += _script_operator_count(value)
        return c
    if isinstance(script, list):
        return sum(_script_operator_count(item) for item in script)
    return 0


def _script_suite(scripts: List[Any]) -> Dict[str, float]:
    if not scripts:
        return {"nonconstant_ratio": 0.0, "avg_op_count": 0.0, "operator_variety": 0.0, "dominance": 1.0}
    nonconst = 0
    op_counts: List[int] = []
    op_hist: collections.Counter = collections.Counter()
    for s in scripts:
        if not _script_is_constant(s):
            nonconst += 1
        op_counts.append(_script_operator_count(s))
        local: collections.Counter = collections.Counter()
        _collect_operators(s, local)
        for k, v in local.items():
            op_hist[k] += v
    total_ops = sum(op_hist.values())
    dominance = (max(op_hist.values()) / total_ops) if total_ops else 1.0
    return {
        "nonconstant_ratio": nonconst / len(scripts),
        "avg_op_count": (sum(op_counts) / len(op_counts)) if op_counts else 0.0,
        "operator_variety": float(len(op_hist)),
        "dominance": dominance,
    }


def evaluate_storyworld(data: Dict[str, Any], validation_errors: List[str]) -> Dict[str, Any]:
    metrics = compute_metrics(data)
    encounters = data.get("encounters", []) or []

    encounter_words: List[int] = []
    reaction_words: List[int] = []
    variable_counts: List[int] = []
    pvalue_refs = 0
    p2value_refs = 0
    gated_options = 0
    total_options = 0
    desirability_ops: collections.Counter = collections.Counter()
    effect_ops: collections.Counter = collections.Counter()
    effect_scripts: List[Any] = []
    des_scripts: List[Any] = []
    vis_scripts: List[Any] = []
    perf_scripts: List[Any] = []
    enc_acc_scripts: List[Any] = []
    enc_des_scripts: List[Any] = []

    for encounter in encounters:
        enc_acc_scripts.append(encounter.get("acceptability_script", True))
        enc_des_scripts.append(encounter.get("desirability_script", 0.0))
        if not _is_ending(encounter):
            text_words = _word_count(encounter.get("text_script")) + _word_count(encounter.get("prompt_script"))
            encounter_words.append(text_words)
        for option in encounter.get("options", []) or []:
            total_options += 1
            vis = option.get("visibility_script", True)
            vis_scripts.append(vis)
            perf_scripts.append(option.get("performability_script", True))
            if vis is not True:
                gated_options += 1
                _collect_operators(vis, desirability_ops)
            for reaction in option.get("reactions", []) or []:
                reaction_words.append(_word_count(reaction.get("text_script")))
                variable_counts.append(count_vars(reaction.get("desirability_script")))
                des_scripts.append(reaction.get("desirability_script"))
                _collect_operators(reaction.get("desirability_script"), desirability_ops)

                refs: List[Tuple[str, int]] = []
                _collect_pointer_refs(reaction.get("desirability_script"), refs)
                _collect_pointer_refs(reaction.get("after_effects"), refs)
                _collect_operators(reaction.get("after_effects"), effect_ops)
                for eff in reaction.get("after_effects", []) or []:
                    if isinstance(eff, dict):
                        effect_scripts.append(eff.get("to"))
                for prop, depth in refs:
                    kind = _belief_ref_kind(prop, depth)
                    if kind == "p2":
                        p2value_refs += 1
                    elif kind == "p1":
                        pvalue_refs += 1

    gated_pct = (100.0 * gated_options / total_options) if total_options else 0.0
    des_ops_total = sum(desirability_ops.values())
    eff_ops_total = sum(effect_ops.values())
    des_ops_unique = len(desirability_ops)
    eff_ops_unique = len(effect_ops)
    des_top_share = (max(desirability_ops.values()) / des_ops_total) if des_ops_total else 1.0
    eff_top_share = (max(effect_ops.values()) / eff_ops_total) if eff_ops_total else 1.0
    eff_suite = _script_suite(effect_scripts)
    des_suite = _script_suite(des_scripts)
    vis_suite = _script_suite(vis_scripts)
    perf_suite = _script_suite(perf_scripts)
    enc_acc_suite = _script_suite(enc_acc_scripts)
    enc_des_suite = _script_suite(enc_des_scripts)

    checks = [
        _check(
            "options_per_encounter",
            float(metrics["options_per_encounter"]),
            float(POLISH_THRESHOLDS["options_per_encounter"]),
        ),
        _check(
            "reactions_per_option",
            float(metrics["reactions_per_option"]),
            float(POLISH_THRESHOLDS["reactions_per_option"]),
        ),
        _check(
            "effects_per_reaction",
            float(metrics["effects_per_reaction"]),
            float(POLISH_THRESHOLDS["effects_per_reaction"]),
        ),
        _check(
            "desirability_vars_per_reaction",
            float(metrics["desirability_vars_avg"]),
            float(POLISH_THRESHOLDS["desirability_vars_per_reaction"]),
        ),
        _check("avg_encounter_words", _safe_mean(encounter_words), 50.0),
        _check("avg_reaction_words", _safe_mean(reaction_words), 20.0),
        _check("pvalue_refs", float(pvalue_refs), 1.0),
        _check("p2value_refs", float(p2value_refs), 1.0),
        _check("visibility_gated_options_pct", gated_pct, 3.0),
        _check("desirability_operator_variety", float(des_ops_unique), 3.0),
        _check("effect_operator_variety", float(eff_ops_unique), 2.0),
        _check_max("desirability_operator_dominance", des_top_share, 0.9),
        _check_max("effect_operator_dominance", eff_top_share, 0.92),
        _check("effect_nonconstant_ratio", eff_suite["nonconstant_ratio"], 0.999),
        _check("desirability_nonconstant_ratio", des_suite["nonconstant_ratio"], 0.999),
        _check("effect_script_complexity", eff_suite["avg_op_count"], 1.2),
        _check("desirability_script_complexity", des_suite["avg_op_count"], 1.2),
        _check("option_visibility_nonconstant_ratio", vis_suite["nonconstant_ratio"], 0.03),
        _check("option_visibility_complexity", vis_suite["avg_op_count"], 0.6),
        _check("option_performability_nonconstant_ratio", perf_suite["nonconstant_ratio"], 0.03),
        _check("option_performability_complexity", perf_suite["avg_op_count"], 0.6),
        _check("encounter_acceptability_nonconstant_ratio", enc_acc_suite["nonconstant_ratio"], 0.2),
        _check("ending_reachability_balance", float(metrics.get('ending_gini', 1.0)), 0.19),
        _check("secret_reachability_balance", float(metrics.get('secret_gini', 1.0)), 0.12),
        _check("super_secret_reachability", float(metrics.get('super_secret_access_pct', 0.0)), 0.25),
        _check("encounter_desirability_nonconstant_ratio", enc_des_suite["nonconstant_ratio"], 0.2),
        _check("encounter_desirability_complexity", enc_des_suite["avg_op_count"], 0.5),
    ]

    checks.append(
        {
            "name": "validator_errors",
            "actual": len(validation_errors),
            "target": 0,
            "pass": len(validation_errors) == 0,
        }
    )

    failures = [c["name"] for c in checks if not c["pass"]]

    return {
        "checks": checks,
        "pass": len(failures) == 0,
        "failures": failures,
        "summary": {
            "encounters": len(encounters),
            "avg_encounter_words": round(_safe_mean(encounter_words), 2),
            "avg_reaction_words": round(_safe_mean(reaction_words), 2),
            "avg_desirability_vars": round(_safe_mean(variable_counts), 2),
            "pvalue_refs": pvalue_refs,
            "p2value_refs": p2value_refs,
            "gated_options_pct": round(gated_pct, 2),
            "desirability_operator_variety": des_ops_unique,
            "effect_operator_variety": eff_ops_unique,
            "desirability_operator_dominance": round(des_top_share, 4),
            "effect_operator_dominance": round(eff_top_share, 4),
            "effect_nonconstant_ratio": round(eff_suite["nonconstant_ratio"], 4),
            "desirability_nonconstant_ratio": round(des_suite["nonconstant_ratio"], 4),
            "option_visibility_nonconstant_ratio": round(vis_suite["nonconstant_ratio"], 4),
            "option_performability_nonconstant_ratio": round(perf_suite["nonconstant_ratio"], 4),
            "encounter_acceptability_nonconstant_ratio": round(enc_acc_suite["nonconstant_ratio"], 4),
            "encounter_desirability_nonconstant_ratio": round(enc_des_suite["nonconstant_ratio"], 4),
        },
        "operator_counts": {
            "desirability": dict(desirability_ops),
            "effects": dict(effect_ops),
        },
        "polish_metrics": metrics,
        "validator_errors": validation_errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Storyworld one-shot quality gate")
    parser.add_argument("--storyworld", required=True, help="Path to storyworld JSON")
    parser.add_argument("--report-out", default="", help="Optional report JSON output path")
    parser.add_argument("--strict", action="store_true", help="Return non-zero exit code when checks fail")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    storyworld_path = Path(args.storyworld).resolve()
    with storyworld_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    validation_errors = validate_storyworld(str(storyworld_path))
    report = evaluate_storyworld(data, validation_errors)
    report["storyworld"] = str(storyworld_path)

    output = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True)
    if args.report_out:
        out_path = Path(args.report_out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8", newline="\n")
        print(str(out_path))
    else:
        print(output)

    if args.strict and not report["pass"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
