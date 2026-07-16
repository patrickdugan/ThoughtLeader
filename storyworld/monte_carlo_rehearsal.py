"""
Monte Carlo rehearsal simulator for SweepWeave storyworlds.
Ports the Rehearsal.gd / AutoRehearsal.gd engine logic to Python.

Usage:
  python monte_carlo_rehearsal.py storyworld.json [--runs 10000] [--seed 42]

Output: ending distribution, dead-end rate, property distributions,
        late-game blocking rate, secret reachability.
"""
import json
import random
import sys
from collections import Counter, defaultdict


def eval_script(script, state):
    """Recursively evaluate a SweepWeave script expression."""
    if script is True:
        return True
    if script is False:
        return False
    if isinstance(script, (int, float)):
        return script
    if not isinstance(script, dict):
        return script

    pt = script.get("pointer_type")
    ot = script.get("operator_type")

    if pt == "Bounded Number Constant":
        return script["value"]
    if pt == "Bounded Number Pointer":
        char = script["character"]
        keyring = tuple(script["keyring"])
        coeff = script.get("coefficient", 1.0)
        return state.get((char, keyring), 0.0) * coeff
    if pt == "String Constant":
        return script.get("value", "")

    if ot == "Arithmetic Comparator":
        sub = script["operator_subtype"]
        left = eval_script(script["operands"][0], state)
        right = eval_script(script["operands"][1], state)
        ops = {
            "Greater Than or Equal To": lambda a, b: a >= b, "GTE": lambda a, b: a >= b,
            "Less Than or Equal To": lambda a, b: a <= b, "LTE": lambda a, b: a <= b,
            "Greater Than": lambda a, b: a > b, "GT": lambda a, b: a > b,
            "Less Than": lambda a, b: a < b, "LT": lambda a, b: a < b,
            "Equal To": lambda a, b: a == b, "EQ": lambda a, b: a == b,
            "Not Equal To": lambda a, b: a != b, "NEQ": lambda a, b: a != b,
        }
        return ops.get(sub, lambda a, b: False)(left, right)

    # Backward-compatible support for shorthand operator_types used by some generators
    if ot == "GreaterThan":
        left = eval_script(script["operands"][0], state)
        right = eval_script(script["operands"][1], state)
        return left > right
    if ot == "GreaterThanOrEqualTo":
        left = eval_script(script["operands"][0], state)
        right = eval_script(script["operands"][1], state)
        return left >= right

    if ot == "And":
        return all(eval_script(op, state) for op in script["operands"])
    if ot == "Or":
        return any(eval_script(op, state) for op in script["operands"])
    if ot == "Addition":
        return sum(eval_script(op, state) for op in script["operands"])
    if ot == "Multiplication":
        r = 1.0
        for op in script["operands"]:
            r *= eval_script(op, state)
        return r
    if ot == "Absolute Value":
        return abs(eval_script(script["operands"][0], state))
    if ot == "Nudge":
        cur = eval_script(script["operands"][0], state)
        delta = eval_script(script["operands"][1], state)
        return max(-1.0, min(1.0, cur + delta))

    return script.get("value", 0.0)


def apply_effects(reaction, state):
    for ae in reaction.get("after_effects", []):
        if ae.get("effect_type") == "Bounded Number Effect":
            char = ae["Set"]["character"]
            keyring = tuple(ae["Set"]["keyring"])
            new_val = eval_script(ae["to"], state)
            state[(char, keyring)] = max(-1.0, min(1.0, new_val))


def select_reaction(option, state):
    best, best_d = None, -999
    for rxn in option.get("reactions", []):
        d = eval_script(rxn.get("desirability_script", 0), state)
        if d is None: d = 0
        if isinstance(d, bool): d = 1.0 if d else 0.0
        if d > best_d:
            best_d, best = d, rxn
    return best


def starting_encounter(data):
    enc_by_id = {e["id"]: e for e in data.get("encounters", [])}
    if "page_0000" in enc_by_id:
        return "page_0000"
    spools = [s for s in data.get("spools", []) if s.get("starts_active")]
    spools.sort(key=lambda s: s.get("creation_index", 0))
    for sp in spools:
        encs = sp.get("encounters") or []
        if encs:
            return encs[0]
    encounters = data.get("encounters", [])
    return encounters[0]["id"] if encounters else None


def run_episode(data, rng, max_steps=200):
    enc_by_id = {e["id"]: e for e in data.get("encounters", [])}
    state = {}
    eid = starting_encounter(data)
    if not eid:
        return "DEAD_END", 0, state

    turns = 0
    while turns < max_steps and eid in enc_by_id:
        enc = enc_by_id[eid]
        options = enc.get("options", []) or []

        if not options:
            ok = True
            if turns < enc.get("earliest_turn", 0):
                ok = False
            if turns > enc.get("latest_turn", 999999):
                ok = False
            if not eval_script(enc.get("acceptability_script", True), state):
                ok = False
            return (eid if ok else "page_end_fallback"), turns, state

        visible = [o for o in options if eval_script(o.get("visibility_script", True), state)]
        if not visible:
            return "DEAD_END", turns, state

        chosen = rng.choice(visible)
        rxn = select_reaction(chosen, state)
        if rxn:
            apply_effects(rxn, state)
            next_id = rxn.get("consequence_id")
        else:
            next_id = None

        turns += 1
        if not next_id:
            return "DEAD_END", turns, state
        eid = next_id

    return "TIMEOUT", turns, state


def run_monte_carlo(data, num_runs=10000, seed=42):
    rng = random.Random(seed)
    endings = [e for e in data["encounters"] if e["id"].startswith("page_end_")]
    secrets = [e for e in data["encounters"] if e["id"].startswith("page_secret_")]

    ending_counts = Counter()
    dead_ends = 0
    prop_sums = defaultdict(float)
    prop_sq = defaultdict(float)
    late_blocks, late_total = 0, 0
    secret_hits = Counter()

    for _ in range(num_runs):
        end_id, turns, state = run_episode(data, rng)
        if end_id in ("DEAD_END", "TIMEOUT"):
            dead_ends += 1
            ending_counts[end_id] += 1
        else:
            ending_counts[end_id] += 1
            if end_id.startswith("page_secret_"):
                secret_hits[end_id] += 1

        for (char, keyring), val in state.items():
            key = f"{char}.{'.'.join(keyring)}"
            prop_sums[key] += val
            prop_sq[key] += val * val

    return {
        "chain_length": 0,
        "num_endings": len(endings),
        "num_secrets": len(secrets),
        "num_runs": num_runs,
        "ending_counts": ending_counts,
        "dead_ends": dead_ends,
        "late_blocks": late_blocks,
        "late_total": late_total,
        "secret_hits": secret_hits,
        "prop_sums": prop_sums,
        "prop_sq": prop_sq,
        "endings": endings,
    }


def print_report(r):
    N = r["num_runs"]
    print(f"\nChain: {r['chain_length']} encounters | {r['num_endings']} endings | {r['num_secrets']} secrets")
    print("=" * 70)
    print(f"MONTE CARLO RESULTS ({N} runs)")
    print("=" * 70)

    print("\n--- Ending Distribution ---")
    for eid, count in sorted(r["ending_counts"].items(), key=lambda x: -x[1]):
        pct = count / N * 100
        bar = "#" * int(pct / 2)
        print(f"  {eid:35s} {count:6d} ({pct:5.1f}%) {bar}")

    print(f"\n  Dead-end rate: {r['dead_ends']}/{N} ({r['dead_ends']/N*100:.1f}%)")

    print(f"\n--- Late-Game Gate Blocking ---")
    if r["late_total"] > 0:
        print(f"  {r['late_blocks']}/{r['late_total']} blocked ({r['late_blocks']/r['late_total']*100:.1f}%)")

    print(f"\n--- Secret Reachability ---")
    for sid in sorted(r["secret_hits"].keys()):
        c = r["secret_hits"][sid]
        print(f"  {sid:40s} {c:6d} ({c/N*100:.1f}%)")
    if not r["secret_hits"]:
        print("  None reachable")

    print(f"\n--- Property Distributions ---")
    for pk in sorted(r["prop_sums"].keys()):
        mean = r["prop_sums"][pk] / N
        var = r["prop_sq"][pk] / N - mean * mean
        std = var ** 0.5 if var > 0 else 0
        print(f"  {pk:45s}  mean={mean:+.4f}  std={std:.4f}")

    print(f"\n--- Unreachable Endings ---")
    for end in r["endings"]:
        if end["id"] not in r["ending_counts"]:
            print(f"  {end['id']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python monte_carlo_rehearsal.py storyworld.json [--runs N] [--seed S]")
        sys.exit(1)

    path = sys.argv[1]
    runs = 10000
    seed = 42
    for i, arg in enumerate(sys.argv):
        if arg == "--runs" and i + 1 < len(sys.argv):
            runs = int(sys.argv[i + 1])
        if arg == "--seed" and i + 1 < len(sys.argv):
            seed = int(sys.argv[i + 1])

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    result = run_monte_carlo(data, num_runs=runs, seed=seed)
    print_report(result)
