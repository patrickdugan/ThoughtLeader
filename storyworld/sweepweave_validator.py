
# Sweepweave Validator + Normalizer
# Usage:
#   python sweepweave_validator.py validate file.json
#   python sweepweave_validator.py normalize in.json out.json [ref.json]

import json, sys, time, uuid
from collections import Counter, defaultdict, deque, OrderedDict

def now_ts():
    return float(time.time())

def validate_storyworld(path: str):
    import os
    errors = []
    if not os.path.exists(path):
        return [f"File not found: {path}"]
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"JSON parse error: {e}"]
    required_top = ["IFID","about_text","css_theme","debug_mode","display_mode","creation_time","modified_time","characters","authored_properties","spools","encounters"]
    for k in required_top:
        if k not in data:
            errors.append(f"{k}: missing")
    multiplayer = data.get("multiplayer", 1)
    turns = data.get("turns")
    requires_turns = ("multiplayer" in data) or (isinstance(multiplayer, int) and multiplayer > 1)
    if requires_turns:
        if not isinstance(multiplayer, int) or multiplayer < 1:
            errors.append("multiplayer: must be an integer >= 1")
        if not isinstance(turns, list) or len(turns) == 0:
            errors.append("turns: required as a non-empty array when multiplayer is set")
        else:
            character_ids = {entry.get("id") for entry in data.get("characters", []) if isinstance(entry, dict) and entry.get("id")}
            unknown_turns = [entry for entry in turns if character_ids and entry not in character_ids]
            if unknown_turns:
                errors.append(f"turns: unknown character ids {unknown_turns}")
            if character_ids and isinstance(multiplayer, int):
                covered = {entry for entry in turns if entry in character_ids}
                if len(covered) < min(multiplayer, len(character_ids)):
                    errors.append("turns: does not cover the declared multiplayer cast count")
    if errors:
        return errors

    characters = data.get("characters", [])
    authored_properties = data.get("authored_properties", [])
    spools = data.get("spools", [])
    encounters = data.get("encounters", [])

    def duplicate_values(values):
        return sorted(value for value, count in Counter(values).items() if value and count > 1)

    character_ids = [c.get("id") for c in characters if isinstance(c, dict)]
    duplicate_character_ids = duplicate_values(character_ids)
    if duplicate_character_ids:
        errors.append(f"characters: duplicate ids {duplicate_character_ids}")

    property_ids = [
        p.get("id") or p.get("property_name")
        for p in authored_properties
        if isinstance(p, dict)
    ]
    duplicate_property_ids = duplicate_values(property_ids)
    if duplicate_property_ids:
        errors.append(f"authored_properties: duplicate ids {duplicate_property_ids}")

    spool_ids = [s.get("id") for s in spools if isinstance(s, dict)]
    duplicate_spool_ids = duplicate_values(spool_ids)
    if duplicate_spool_ids:
        errors.append(f"spools: duplicate ids {duplicate_spool_ids}")

    encounter_id_list = [e.get("id") for e in encounters if isinstance(e, dict)]
    duplicate_encounter_ids = duplicate_values(encounter_id_list)
    if duplicate_encounter_ids:
        errors.append(f"encounters: duplicate ids {duplicate_encounter_ids}")

    # Build encounter id set for reference checks
    encounter_ids = set()
    for e in encounters:
        if isinstance(e, dict) and "id" in e:
            encounter_ids.add(e["id"])
    if not encounter_ids:
        errors.append("encounters: empty")
        return errors

    # Validate spools
    if not spools:
        errors.append("spools: empty")
    start_spools = [s for s in spools if s.get("starts_active")]
    if not start_spools:
        errors.append("spools: no starts_active spool")
    for s in spools:
        encs = s.get("encounters", None)
        if not isinstance(encs, list) or len(encs) == 0:
            errors.append(f"spools[{s.get('id','?')}]: encounters empty")
            continue
        for eid in encs:
            if eid not in encounter_ids:
                errors.append(f"spools[{s.get('id','?')}]: unknown encounter id {eid}")

    authored_property_ids = {
        p.get("id")
        for p in authored_properties
        if isinstance(p, dict) and p.get("id")
    } | {
        p.get("property_name")
        for p in authored_properties
        if isinstance(p, dict) and p.get("property_name")
    }
    character_id_set = {cid for cid in character_ids if cid}
    spool_id_set = {sid for sid in spool_ids if sid}

    def walk_script_refs(node, context):
        if isinstance(node, dict):
            if node.get("pointer_type") == "Bounded Number Pointer":
                char_id = node.get("character")
                keyring = node.get("keyring") or []
                prop_id = keyring[0] if keyring else None
                if char_id not in character_id_set:
                    errors.append(f"{context}: unknown bounded-number character {char_id}")
                if prop_id not in authored_property_ids:
                    errors.append(f"{context}: unknown bounded-number property {prop_id}")
                # keyring[1:] are pValue/p2Value perceived-character ids (belief pointers),
                # not property ids -- validate them against characters, not properties.
                for perceived_char_id in keyring[1:]:
                    if perceived_char_id not in character_id_set:
                        errors.append(
                            f"{context}: unknown perceived-character id {perceived_char_id} "
                            f"in belief-pointer keyring {keyring}"
                        )
            for value in node.values():
                walk_script_refs(value, context)
        elif isinstance(node, list):
            for value in node:
                walk_script_refs(value, context)

    option_ids = []
    reaction_ids = []
    edges = defaultdict(list)
    wild_sources = set()
    encounter_by_id = {e.get("id"): e for e in encounters if isinstance(e, dict)}

    def is_wild_consequence(consequence_id):
        return (
            consequence_id is None
            or (isinstance(consequence_id, str) and consequence_id.strip() == "")
            or consequence_id == "wild"
        )

    # Validate reactions have consequence_id and that it targets a real encounter.
    for e in encounters:
        eid = e.get("id", "?")
        for spool_id in e.get("connected_spools", []) or []:
            if spool_id not in spool_id_set:
                errors.append(f"encounter connected_spools unknown: encounter={eid} spool={spool_id}")
        walk_script_refs(e.get("acceptability_script", True), f"encounter={eid} acceptability_script")
        walk_script_refs(e.get("desirability_script", 0), f"encounter={eid} desirability_script")
        for opt in e.get("options", []):
            oid = opt.get("id", "?")
            option_ids.append(oid)
            walk_script_refs(opt.get("visibility_script", True), f"encounter={eid} option={oid} visibility_script")
            walk_script_refs(opt.get("performability_script", True), f"encounter={eid} option={oid} performability_script")
            for r in opt.get("reactions", []):
                rid = r.get("id", "?")
                reaction_ids.append(rid)
                walk_script_refs(r.get("desirability_script", 0), f"encounter={eid} option={oid} reaction={rid} desirability_script")
                walk_script_refs(r.get("after_effects", []), f"encounter={eid} option={oid} reaction={rid} after_effects")
                for spool_field in ["activate_spools", "deactivate_spools"]:
                    for spool_id in r.get(spool_field, []) or []:
                        if spool_id not in spool_id_set:
                            errors.append(f"reaction {spool_field} unknown: encounter={eid} option={oid} reaction={rid} -> {spool_id}")
                cid = r.get("consequence_id", "")
                if not isinstance(cid, str):
                    errors.append(f"reaction missing consequence_id: encounter={eid} option={oid} reaction={rid}")
                elif is_wild_consequence(cid):
                    wild_sources.add(eid)
                elif cid not in encounter_ids:
                    errors.append(f"reaction consequence_id not found: encounter={eid} option={oid} reaction={rid} -> {cid}")
                else:
                    edges[eid].append(cid)

    duplicate_option_ids = duplicate_values(option_ids)
    if duplicate_option_ids:
        errors.append(f"options: duplicate ids {duplicate_option_ids}")

    duplicate_reaction_ids = duplicate_values(reaction_ids)
    if duplicate_reaction_ids:
        errors.append(f"reactions: duplicate ids {duplicate_reaction_ids}")

    def starting_encounter_id():
        if "page_0000" in encounter_ids:
            return "page_0000"
        active_spools = [s for s in spools if s.get("starts_active")]
        active_spools.sort(key=lambda s: s.get("creation_index", 0))
        for spool in active_spools:
            for eid in spool.get("encounters") or []:
                if eid in encounter_ids:
                    return eid
        return encounters[0].get("id") if encounters else None

    start_id = starting_encounter_id()
    if not start_id:
        errors.append("encounters: could not determine starting encounter")
        return errors

    start_active_spools = [s for s in spools if s.get("starts_active")]
    if not start_active_spools:
        start_active_spools = list(spools)
    wild_target_ids = []
    seen_wild_targets = set()
    for spool in sorted(start_active_spools, key=lambda s: s.get("creation_index", 0)):
        for target in spool.get("encounters") or []:
            if target in encounter_ids and target not in seen_wild_targets:
                seen_wild_targets.add(target)
                wild_target_ids.append(target)

    def within_turn_window(eid, turn):
        e = encounter_by_id.get(eid) or {}
        earliest = e.get("earliest_turn", 0)
        latest = e.get("latest_turn", 999999)
        return turn >= earliest and turn <= latest

    def possible_targets(eid, next_turn):
        targets = list(edges[eid])
        if eid in wild_sources:
            targets.extend(
                target
                for target in wild_target_ids
                if target != eid and within_turn_window(target, next_turn)
            )
        return targets

    reachable_turns = defaultdict(set)
    reachable_turns[start_id].add(0)
    turn_queue = deque([(start_id, 0)])
    max_turns = max(
        [int(e.get("latest_turn", 0)) for e in encounters if isinstance(e.get("latest_turn", 0), int)]
        + [80]
    )
    while turn_queue:
        eid, turn = turn_queue.popleft()
        if turn >= max_turns:
            continue
        next_turn = turn + 1
        for target in possible_targets(eid, next_turn):
            if next_turn not in reachable_turns[target]:
                reachable_turns[target].add(next_turn)
                turn_queue.append((target, next_turn))

    reachable = set(reachable_turns.keys())

    unreachable = sorted(eid for eid in encounter_ids if eid not in reachable)
    if unreachable:
        errors.append(f"encounters: unreachable from start {start_id}: {unreachable}")

    inbound = Counter(target for targets in edges.values() for target in targets)
    for source in wild_sources:
        for target in wild_target_ids:
            if target != source:
                inbound[target] += 1
    zero_inbound = sorted(eid for eid in encounter_ids if eid != start_id and inbound[eid] == 0)
    if zero_inbound:
        errors.append(f"encounters: zero inbound references: {zero_inbound}")

    terminal_window_failures = []
    for eid, e in encounter_by_id.items():
        if e.get("options"):
            continue
        if not (str(eid).startswith("page_end") or str(eid).startswith("page_epilogue") or str(eid).startswith("page_secret")):
            errors.append(f"terminal encounter is not an ending/epilogue/secret: {eid}")
        earliest = e.get("earliest_turn", 0)
        latest = e.get("latest_turn", 999999)
        turns_seen = sorted(reachable_turns.get(eid, set()))
        invalid_turns = [turn for turn in turns_seen if turn < earliest or turn > latest]
        if invalid_turns:
            terminal_window_failures.append(
                f"{eid} reachable at invalid turns {invalid_turns[:20]} but valid only {earliest}..{latest}"
            )
    if terminal_window_failures:
        errors.append(f"terminal turn windows impossible: {terminal_window_failures}")
    return errors

def normalize_storyworld(input_path: str, output_path: str, reference_path: str):
    with open(reference_path,"r",encoding="utf-8") as f:
        ref = json.load(f, object_pairs_hook=OrderedDict)
    with open(input_path,"r",encoding="utf-8") as f:
        test = json.load(f, object_pairs_hook=OrderedDict)

    normalized = OrderedDict()
    for key in ref.keys():
        normalized[key] = test.get(key, ref[key])

    # Preserve authored spools & encounters verbatim after key-order merge
    # (prevents wiping nested fields like connected_spools by ref defaults)
    if "spools" in test:
        normalized["spools"] = test["spools"]
    if "encounters" in test:
        normalized["encounters"] = test["encounters"]
    for passthrough_key in ["multiplayer", "turns"]:
        if passthrough_key in test:
            normalized[passthrough_key] = test[passthrough_key]

    import uuid, time
    if not isinstance(normalized.get("IFID",""), str) or len(normalized["IFID"]) < 10:
        normalized["IFID"] = str(uuid.uuid4())

    for k in ["creation_time", "modified_time"]:
        if k in normalized:
            normalized[k] = float(normalized[k])

    with open(output_path,"w",encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)

    return output_path

if __name__=="__main__":
    if len(sys.argv)<3:
        print("Usage: python sweepweave_validator.py (validate|normalize) file.json [out.json ref.json]")
        sys.exit(1)
    mode=sys.argv[1]
    if mode=="validate":
        errs=validate_storyworld(sys.argv[2])
        if errs:
            print("Invalid:",errs); sys.exit(2)
        print("VALID OK")
    elif mode=="normalize":
        out=sys.argv[3] if len(sys.argv)>3 else "normalized.json"
        ref=sys.argv[4] if len(sys.argv)>4 else "dogs_in_a_barrel_secret_endings_spools.json"
        path=normalize_storyworld(sys.argv[2],out,ref)
        print("Normalized written to",path)
