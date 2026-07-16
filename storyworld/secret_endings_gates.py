import argparse
import json
import sys


def is_constant_script(script):
    if not isinstance(script, dict):
        return True
    if script.get("script_element_type") == "Pointer":
        return script.get("pointer_type") in (
            "Bounded Number Constant",
            "Boolean Constant",
            "String Constant",
        )
    if script.get("script_element_type") == "Operator":
        ops = script.get("operands", [])
        if not ops:
            return True
        return all(is_constant_script(op) for op in ops)
    return False


def has_variable_pointer(script):
    if not isinstance(script, dict):
        return False
    if script.get("pointer_type") == "Bounded Number Pointer":
        return True
    if script.get("script_element_type") == "Operator":
        return any(has_variable_pointer(op) for op in script.get("operands", []))
    return False


def extract_thresholds(script):
    """Return list of numeric thresholds found in Arithmetic Comparator nodes."""
    found = []
    if not isinstance(script, dict):
        return found
    if script.get("operator_type") == "Arithmetic Comparator":
        for op in script.get("operands", []):
            if isinstance(op, dict) and op.get("pointer_type") == "Bounded Number Constant":
                found.append(float(op.get("value", 0.0)))
    for op in script.get("operands", []):
        found.extend(extract_thresholds(op))
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("storyworld")
    parser.add_argument("--min-effects", type=int, default=3)
    parser.add_argument("--min-reactions", type=int, default=2)
    parser.add_argument("--min-options", type=int, default=2)
    parser.add_argument("--min-threshold", type=float, default=0.02)
    args = parser.parse_args()

    with open(args.storyworld, "r", encoding="utf-8") as f:
        data = json.load(f)

    issues = []
    gated_options = 0
    gated_ok = 0

    for enc in data.get("encounters", []):
        eid = enc.get("id", "?")
        options = enc.get("options", [])
        if isinstance(options, list) and len(options) and len(options) < args.min_options:
            issues.append(f"{eid}: fewer than {args.min_options} options")

        for opt in options:
            vis = opt.get("visibility_script")
            if isinstance(vis, dict) and vis.get("pointer_type") != "Boolean Constant":
                gated_options += 1
                thresholds = extract_thresholds(vis)
                threshold_ok = any(t >= args.min_threshold for t in thresholds) if thresholds else False
                reactions = opt.get("reactions", [])
                if len(reactions) < args.min_reactions:
                    issues.append(f"{eid}:{opt.get('id','?')} fewer than {args.min_reactions} reactions")
                all_ok = True
                for rxn in reactions:
                    ds = rxn.get("desirability_script")
                    if not ds or is_constant_script(ds) or not has_variable_pointer(ds):
                        all_ok = False
                        issues.append(f"{eid}:{opt.get('id','?')}:{rxn.get('id','?')} desirability not variable")
                    effects = rxn.get("after_effects", [])
                    if len(effects) < args.min_effects:
                        all_ok = False
                        issues.append(f"{eid}:{opt.get('id','?')}:{rxn.get('id','?')} fewer than {args.min_effects} effects")
                if all_ok and threshold_ok:
                    gated_ok += 1
                elif not threshold_ok:
                    issues.append(f"{eid}:{opt.get('id','?')} visibility threshold too low or missing")

    score = gated_ok / gated_options if gated_options else 0.0
    print(f"gated_options={gated_options} gated_ok={gated_ok} score={score:.3f}")
    if issues:
        print("issues:")
        for item in issues:
            print("-", item)
        sys.exit(2)


if __name__ == "__main__":
    main()
