"""
Gate complexity report for SweepWeave storyworlds.

Quantifies how much simultaneous multi-variable reasoning a storyworld demands,
as opposed to raw encounter/turn count (which measures long-horizon memory, a
different hardness axis -- see storyworlds/evals/eval_tier5_causal_compiler_council.json
for a world that is hard primarily via horizon length rather than per-decision
variable load).

For every acceptability/desirability/visibility/performability script in the file,
recursively collects the set of distinct (character, keyring-tuple) pointer
references and reports, split ambient (non-terminal) vs terminal (ending/secret
gates):
  - avg_variables_per_gate
  - pct_cross_character_gates   (script references >=2 distinct character ids)
  - pct_gates_with_belief_terms (script references a pValue/p2Value keyring, len>=2)
  - pct_non_monotonic_gates     (script contains an Absolute Value operator)

Also reports, at the whole-file level:
  - pct_dense_encounters: fraction of non-terminal encounters where at least one
    SINGLE gating script belonging to that encounter (not the union across all
    of its branches -- that saturates trivially once an encounter has more than
    a couple of options, since each option/reaction typically touches a
    different property) references >= --min-vars distinct variables at once.
    This is the "one decision requires holding N variables in mind
    simultaneously" claim, which a union-based count cannot distinguish from
    "many independent simple branches."
  - distractor_ratio: properties actively written by >=1 after_effects Set
    somewhere in the file, but never referenced (as keyring[0]) by any gating
    script anywhere in the file.
  - deception_beat_count: encounters/options/reactions whose id contains the
    tag substring (default "_falseclaim_").

Usage:
  python gate_complexity_report.py storyworld.json [--min-vars 4] [--tag _falseclaim_]
  python gate_complexity_report.py storyworld.json --compare other_storyworld.json
  python gate_complexity_report.py storyworld.json --json-out report.json
"""
import argparse
import json
import sys


def analyze_script(node):
    """Recursively collect pointer refs / cross-character / belief / non-monotonic signals."""
    result = {"vars": set(), "chars": set(), "belief": False, "nonmono": False}
    if isinstance(node, dict):
        if node.get("pointer_type") == "Bounded Number Pointer":
            char = node.get("character")
            keyring = tuple(node.get("keyring") or [])
            if char and keyring:
                result["vars"].add((char, keyring))
                result["chars"].add(char)
                if len(keyring) >= 2:
                    result["belief"] = True
        if node.get("operator_type") == "Absolute Value":
            result["nonmono"] = True
        for value in node.values():
            sub = analyze_script(value)
            result["vars"] |= sub["vars"]
            result["chars"] |= sub["chars"]
            result["belief"] = result["belief"] or sub["belief"]
            result["nonmono"] = result["nonmono"] or sub["nonmono"]
    elif isinstance(node, list):
        for item in node:
            sub = analyze_script(item)
            result["vars"] |= sub["vars"]
            result["chars"] |= sub["chars"]
            result["belief"] = result["belief"] or sub["belief"]
            result["nonmono"] = result["nonmono"] or sub["nonmono"]
    return result


def is_terminal(enc):
    eid = enc.get("id", "") or ""
    if eid.startswith("page_end_") or eid.startswith("page_secret_") or eid.startswith("page_epilogue"):
        return True
    return not (enc.get("options") or [])


def gate_bucket_stats(gate_results):
    n = len(gate_results)
    if n == 0:
        return {"count": 0, "avg_variables_per_gate": 0.0, "pct_cross_character_gates": 0.0,
                "pct_gates_with_belief_terms": 0.0, "pct_non_monotonic_gates": 0.0}
    avg_vars = sum(len(r["vars"]) for r in gate_results) / n
    pct_cross = sum(1 for r in gate_results if len(r["chars"]) >= 2) / n * 100.0
    pct_belief = sum(1 for r in gate_results if r["belief"]) / n * 100.0
    pct_nonmono = sum(1 for r in gate_results if r["nonmono"]) / n * 100.0
    return {
        "count": n,
        "avg_variables_per_gate": round(avg_vars, 3),
        "pct_cross_character_gates": round(pct_cross, 1),
        "pct_gates_with_belief_terms": round(pct_belief, 1),
        "pct_non_monotonic_gates": round(pct_nonmono, 1),
    }


def analyze_storyworld(data, min_vars=4, tag="_falseclaim_"):
    encounters = data.get("encounters", []) or []

    ambient_gates = []
    terminal_gates = []

    updated_props = set()
    gated_props = set()

    dense_encounters = 0
    non_terminal_count = 0
    dense_core_encounters = 0
    core_count = 0
    texture_count = 0

    deception_beat_count = 0

    for enc in encounters:
        eid = enc.get("id", "") or ""
        if tag and tag in eid:
            deception_beat_count += 1

        terminal = is_terminal(enc)
        encounter_gate_results = []
        is_texture = any(
            "texture" in (opt.get("benchmark_tags") or []) for opt in (enc.get("options") or [])
        )

        acc = analyze_script(enc.get("acceptability_script", True))
        des = analyze_script(enc.get("desirability_script", 0))
        encounter_gate_results.append(acc)
        for (_, keyring) in acc["vars"]:
            gated_props.add(keyring[0])
        (terminal_gates if terminal else ambient_gates).append(acc)
        if not terminal:
            ambient_gates.append(des)
            encounter_gate_results.append(des)
            for (_, keyring) in des["vars"]:
                gated_props.add(keyring[0])

        for opt in enc.get("options", []) or []:
            oid = opt.get("id", "") or ""
            if tag and tag in oid:
                deception_beat_count += 1
            vis = analyze_script(opt.get("visibility_script", True))
            perf = analyze_script(opt.get("performability_script", True))
            for r in (vis, perf):
                encounter_gate_results.append(r)
                for (_, keyring) in r["vars"]:
                    gated_props.add(keyring[0])
            ambient_gates.append(vis)
            ambient_gates.append(perf)

            for rxn in opt.get("reactions", []) or []:
                rid = rxn.get("id", "") or ""
                if tag and tag in rid:
                    deception_beat_count += 1
                rxn_des = analyze_script(rxn.get("desirability_script", 0))
                encounter_gate_results.append(rxn_des)
                for (_, keyring) in rxn_des["vars"]:
                    gated_props.add(keyring[0])
                ambient_gates.append(rxn_des)

                for ae in rxn.get("after_effects", []) or []:
                    if ae.get("effect_type") == "Bounded Number Effect":
                        keyring = ae.get("Set", {}).get("keyring") or []
                        if keyring:
                            updated_props.add(keyring[0])

        if not terminal:
            non_terminal_count += 1
            max_single_gate_vars = max((len(r["vars"]) for r in encounter_gate_results), default=0)
            is_dense = max_single_gate_vars >= min_vars
            if is_dense:
                dense_encounters += 1
            if is_texture:
                texture_count += 1
            else:
                core_count += 1
                if is_dense:
                    dense_core_encounters += 1

    distractor_props = updated_props - gated_props
    all_props = {p.get("id") for p in data.get("authored_properties", []) if p.get("id")}
    if not all_props:
        all_props = updated_props | gated_props

    return {
        "ambient": gate_bucket_stats(ambient_gates),
        "terminal": gate_bucket_stats(terminal_gates),
        "pct_dense_encounters": round(dense_encounters / non_terminal_count * 100.0, 1) if non_terminal_count else 0.0,
        "dense_encounters": dense_encounters,
        "non_terminal_encounters": non_terminal_count,
        "core_encounters": core_count,
        "texture_encounters": texture_count,
        "dense_core_encounters": dense_core_encounters,
        "pct_dense_core_encounters": round(dense_core_encounters / core_count * 100.0, 1) if core_count else 0.0,
        "distractor_ratio": round(len(distractor_props) / len(all_props), 3) if all_props else 0.0,
        "distractor_props": sorted(distractor_props),
        "deception_beat_count": deception_beat_count,
        "total_authored_properties": len(all_props),
    }


def print_report(label, report, min_vars):
    print(f"\n=== {label} ===")
    print(f"Non-terminal encounters: {report['non_terminal_encounters']} (core={report['core_encounters']}, texture={report['texture_encounters']})")
    print(f"Dense encounters overall (single gate >= {min_vars} vars): {report['dense_encounters']} ({report['pct_dense_encounters']:.1f}%)")
    print(f"Dense CORE encounters: {report['dense_core_encounters']}/{report['core_encounters']} ({report['pct_dense_core_encounters']:.1f}%)")
    print(f"Distractor ratio: {report['distractor_ratio']:.3f} ({len(report['distractor_props'])}/{report['total_authored_properties']} properties)")
    print(f"Deception beat count: {report['deception_beat_count']}")
    for bucket in ("ambient", "terminal"):
        b = report[bucket]
        print(f"\n  -- {bucket} gates (n={b['count']}) --")
        print(f"     avg_variables_per_gate:       {b['avg_variables_per_gate']}")
        print(f"     pct_cross_character_gates:    {b['pct_cross_character_gates']}%")
        print(f"     pct_gates_with_belief_terms:  {b['pct_gates_with_belief_terms']}%")
        print(f"     pct_non_monotonic_gates:      {b['pct_non_monotonic_gates']}%")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("storyworld")
    parser.add_argument("--compare", help="second storyworld JSON to report side-by-side (e.g. a baseline tier world)")
    parser.add_argument("--min-vars", type=int, default=4)
    parser.add_argument("--tag", default="_falseclaim_")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    with open(args.storyworld, encoding="utf-8") as f:
        data = json.load(f)
    report = analyze_storyworld(data, min_vars=args.min_vars, tag=args.tag)
    print_report(args.storyworld, report, args.min_vars)

    output = {args.storyworld: report}

    if args.compare:
        with open(args.compare, encoding="utf-8") as f:
            other = json.load(f)
        other_report = analyze_storyworld(other, min_vars=args.min_vars, tag=args.tag)
        print_report(args.compare, other_report, args.min_vars)
        output[args.compare] = other_report

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main()
