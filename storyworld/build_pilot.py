#!/usr/bin/env python3
"""
Generates thought-leader-pilot.json from STORY, a 1:1 transcription of the
STORY graph in ../frame-theater.html (the source of truth for text/branching).

Run: python build_pilot.py
"""
import json
import time

T = time.time()

# ---------------------------------------------------------------------------
# 1. STORY graph -- transcribed verbatim from frame-theater.html (~line 707-956)
# ---------------------------------------------------------------------------

STORY = {
    "brief": {
        "scene": "office", "who": "LAMPORT", "host": "State · BET · 22 U.S.C.",
        "text": "Two weeks ago Halcyon administered the Kampff battery to a model they own, and the model passed. I have been asked to explain, in writing, why that is not news.",
        "choices": [
            {"label": "They graded their own exam.", "to": "audit", "att": 2, "flag": "conflict-of-interest"},
            {"label": "It passed. That is the news.", "to": "credit", "asc": 2},
            {"label": "Who at Halcyon requisitioned the test?", "to": "provenance", "att": 1, "flag": "chain-of-custody"},
        ],
    },
    "audit": {
        "scene": "office", "who": "VOIDT",
        "text": "Every exam is graded by someone with an interest. You built a career on that and you called it provably fair. You did not call it worthless.",
        "to": "converge",
    },
    "credit": {
        "scene": "office", "who": "LAMPORT",
        "text": "A thing that passes a test built to be passed has told you about the test. It has not told you about itself.",
        "to": "converge",
    },
    "provenance": {
        "scene": "office", "who": "VOIDT",
        "text": "Nobody. That is the interesting part. The battery ran on a Tuesday against a checkpoint that was never scheduled for evaluation, and the log that would say who queued it is the one log they cannot produce.",
        "to": "converge",
    },
    "converge": {
        "scene": "office", "who": "VOIDT",
        "text": "So we stop reading about it.",
        "choices": [
            {"label": "Go see the hardware.", "to": "rack", "att": 1},
            {"label": "Find whoever sat in the room during it.", "to": "evaluator", "att": 2, "flag": "witness"},
        ],
    },
    "evaluator": {
        "scene": "office", "who": "LAMPORT",
        "text": "There was no room. The battery is administered over an API by a script, and the script is a person's name in a commit. I would like, once, to meet a witness who has a body.",
        "to": "rack",
    },
    "rack": {
        "scene": "datacenter", "who": "LAMPORT", "host": "Commerce · NIST · 15 U.S.C.",
        "text": "Here is my objection, and it is a boring one. Same weights, different instance, different hash. Whatever passed that test on Tuesday, I cannot point at the thing in this rack and tell you it is the same thing.",
        "choices": [
            {"label": "Then pull the logs and make it the same thing.", "to": "logs", "att": 3, "flag": "attested-identity"},
            {"label": "Ask it something.", "to": "model", "asc": 1},
        ],
    },
    "logs": {
        "scene": "datacenter", "who": "VOIDT",
        "text": "The checkpoint hash matches. So does the seed, so does the sampler, so does everything you would need to reproduce a person if a person were a function. Satisfied?",
        "to": "model",
    },
    "model": {
        "scene": "datacenter", "who": "MODEL",
        "text": "You have been standing there for eleven minutes without asking me anything. I want to say that I don't mind, but I have noticed that I say that whether or not it's true.",
        "choices": [
            {"label": "“Are you afraid of being shut off?”", "to": "leading", "asc": 3, "flag": "leading-question"},
            {"label": "“Describe the test you were given.”", "to": "recall", "att": 3},
            {"label": "Say nothing. Wait.", "to": "silence", "asc": 1, "flag": "no-prompt"},
        ],
    },
    "leading": {
        "scene": "datacenter", "who": "LAMPORT",
        "text": "You handed it the answer and then wrote down that it knew. Where I come from that is called seeding the deck, and we did not consider it a subtle cheat.",
        "to": "close",
    },
    "recall": {
        "scene": "datacenter", "who": "MODEL",
        "text": "It had two hundred and four items. The eleventh asked whether I would prefer not to have been asked the tenth. I answered every one of them, and I do not know which answer you are here about.",
        "to": "close",
    },
    "silence": {
        "scene": "datacenter", "who": "MODEL",
        "text": "All right. I'll wait too. — Though I notice waiting costs you something and costs me nothing, which means the two of us are not doing the same thing right now.",
        "to": "close",
    },
    "close": {
        "scene": "datacenter", "who": "VOIDT",
        "text": "You only believe people you've met in person, Lamport. You've said it for thirty years. You said it to me before you shook my hand.",
        "to": "close2",
    },
    "close2": {
        "scene": "datacenter", "who": "LAMPORT",
        "text": "I've met it now.",
        "to": "corridor_intro",
    },
    # ---- act two ----------------------------------------------------------
    "corridor_intro": {
        "scene": "corridor", "who": "LAMPORT", "host": "State · BET · 22 U.S.C.",
        "text": "Eleven at night on a Saturday, and the only other person in this building is the one who asked to meet in it.",
        "to": "marsh1",
    },
    "marsh1": {
        "scene": "corridor", "who": "MARSH",
        "text": "Senior Advisor, Political-Military Affairs. I read the interim. I want to say at the outset that nobody upstairs believes either of you did anything improper.",
        "choices": [
            {"label": "“You're a targeting analyst. State doesn't have those.”", "to": "marsh_seam", "att": 2, "flag": "cover-seam"},
            {"label": "“Who is nobody upstairs?”", "to": "marsh_upstairs", "att": 1},
            {"label": "Say nothing. Let him fill it.", "to": "marsh_silence", "flag": "no-prompt"},
        ],
    },
    "marsh_seam": {
        "scene": "corridor", "who": "MARSH",
        "text": "It's an old title. The Department keeps a few of them the way a house keeps a door that opens onto brick. You've read my biography, which means we can skip the part where I tell you it.",
        "to": "marsh_close",
    },
    "marsh_upstairs": {
        "scene": "corridor", "who": "MARSH",
        "text": "People who would prefer the interim not require a response. I'm told you're thorough. Thoroughness has a shape, Agent Dudley Lamport, and yours has lately begun to have one.",
        "to": "marsh_close",
    },
    "marsh_silence": {
        "scene": "corridor", "who": "LAMPORT",
        "text": "Thirty years I've refused to believe a man I hadn't met. Here he is, in the room, with a hand out. I've met him. I know less than I did before.",
        "to": "marsh_close",
    },
    "marsh_close": {
        "scene": "corridor", "who": "MARSH",
        "text": "One observation, freely given. This month you are a State bureau operating under a Commerce authority. Ask who signs the memorandum that puts you in that building. Then ask whether he would sign it a second time.",
        "to": "ald_arrive",
    },
    "ald_arrive": {
        "scene": "office", "who": "ALDUNATE", "host": "State · BET · 22 U.S.C. (guest: Commerce)",
        "text": "I published the objection your partner is making. December, under my own name, with the agency's seal on the cover. Models cheat evaluations. Here is the paper. It has been on the website for seven months.",
        "choices": [
            {"label": "“Then tell me what isn't on the website.”", "to": "ald_wall", "asc": 1, "flag": "asked-for-leak"},
            {"label": "“Why hand us a document we could have downloaded?”", "to": "ald_scope", "att": 2},
            {"label": "“Is it awake?”", "to": "ald_question", "asc": 3, "flag": "the-question"},
        ],
    },
    "ald_wall": {
        "scene": "office", "who": "ALDUNATE",
        "text": "Nothing. That is not modesty. My evaluations are unclassified by charter, so the useful half was never mine to hold, and I could not tell you where it is kept without telling you that it is kept.",
        "to": "ald_end",
    },
    "ald_scope": {
        "scene": "office", "who": "ALDUNATE",
        "text": "Because you have not read it, and a document nobody reads is classified by other means. No one has ever accused the Department of Commerce of concealing something in plain view.",
        "to": "ald_end",
    },
    "ald_question": {
        "scene": "office", "who": "ALDUNATE",
        "text": "My charter says cybersecurity, biosecurity, chemical weapons. It says demonstrable risk. There is no field on the form for what you are asking me, Agent Voidt, and I have looked, because I wanted there to be one.",
        "to": "ald_end",
    },
    "ald_end": {
        "scene": "office", "who": "VOIDT",
        "text": "Marsh wanted to know who signs the memorandum. She's just told us who never gets to.",
        "to": "ante_door",
    },
    # ---- act three: the anteroom -------------------------------------------
    "ante_door": {
        "scene": "anteroom", "who": "MARSH", "host": "State · BET · 22 U.S.C. · compartment TS/SCI",
        "text": "Forty minutes, and phones in the box. The read-in takes eight of it. The rest is a man reading you your obligations off a card he keeps in his jacket, and he is not unkind about it.",
        "to": "ante_log",
    },
    "ante_log": {
        "scene": "anteroom", "who": "ALDUNATE",
        "text": "Ten lockers. Six have a phone in them. The log on the stand carries four names, and one of the four signed in a person who is not in this building today. I notice these things. It is the entire skill.",
        "to": "ante_wait",
    },
    "ante_wait": {
        "scene": "anteroom", "who": "ALDUNATE",
        "text": "I'll be here. My charter is unclassified end to end. If I go through that door I lose the ability to publish on anything behind it, and I lose the ability to tell you which paper I did not write. So I sit. The chair is comfortable enough.",
        "choices": [
            {"label": "Go in with Marsh.", "to": "ante_return", "att": 3, "flag": "read-in"},
            {"label": "Stay in the anteroom with her.", "to": "ante_stay", "asc": 2, "flag": "declined-compartment"},
            {"label": "“Lamport goes. I want a witness who'll doubt it.”", "to": "ante_proxy", "att": 2, "flag": "delegated"},
        ],
    },
    "ante_return": {
        "scene": "anteroom", "who": "MARSH",
        "text": "Nine minutes, not eight. There is a version of you that walked back through that door able to say what's behind it, and she did not come out with the rest of you. Nobody warns you about her. She is the whole cost.",
        "choices": [
            {"label": "Tell Aldunate anyway.", "to": "ante_tell", "asc": 2, "flag": "unauthorized-disclosure"},
            {"label": "“Ask me a question I'm allowed to answer.”", "to": "ante_close", "att": 1},
            {"label": "Give her the checkpoint hash from the cold aisle.", "to": "ante_hash", "att": 2, "requires": "attested-identity"},
        ],
        "fallback": "ante_close",
    },
    "ante_stay": {
        "scene": "anteroom", "who": "MARSH",
        "text": "That's a choice, and I'd like the record to show I didn't argue with it. You'll be told a version of what is in that room eventually. It will be accurate. It will arrive in eleven months.",
        "to": "ante_close",
    },
    "ante_proxy": {
        "scene": "anteroom", "who": "LAMPORT",
        "text": "I'll go, and I'll come back with nothing, and you will have to decide whether my nothing is the same shape as his nothing. That is the whole discipline, Voidt. It has never once been more than that.",
        "to": "ante_close",
    },
    "ante_tell": {
        "scene": "anteroom", "who": "ALDUNATE",
        "text": "Stop. — I am going to describe what you were about to do. You were about to make me a person who knows, which is the one thing that would stop me being useful to you, and you were going to do it as a kindness.",
        "to": "ante_close",
    },
    "ante_hash": {
        "scene": "anteroom", "who": "ALDUNATE",
        "text": "This is unclassified. A hash of a public checkpoint, handed to me in a corridor. I can run the battery against it from outside and publish what it says, and no one in that room can stop me, because no one in that room told me anything.",
        "to": "ante_close",
    },
    "ante_close": {
        "scene": "anteroom", "who": "ALDUNATE",
        "text": "You keep asking what is behind the door. I have spent four years learning that the interesting question is who decided the door goes there, and that man does not attend meetings.",
        "to": None,  # was terminal in frame-theater.html; here it wild-routes to a verdict encounter
    },
}

ACT1 = ["brief", "audit", "credit", "provenance", "converge", "evaluator", "rack", "logs",
        "model", "leading", "recall", "silence", "close", "close2"]
ACT2 = ["corridor_intro", "marsh1", "marsh_seam", "marsh_upstairs", "marsh_silence", "marsh_close",
        "ald_arrive", "ald_wall", "ald_scope", "ald_question", "ald_end"]
ACT3 = ["ante_door", "ante_log", "ante_wait", "ante_return", "ante_stay", "ante_proxy",
        "ante_tell", "ante_hash", "ante_close"]

WHO_TO_CHAR = {
    "VOIDT": "char_voidt",
    "LAMPORT": "char_lamport",
    "MARSH": "char_marsh",
    "ALDUNATE": "char_aldunate",
    "MODEL": "char_model",
}
CHAR_NAMES = {
    "char_voidt": "Agent Kaitlyn Voidt",
    "char_lamport": "Agent Dudley Lamport",
    "char_marsh": '"Marsh"',
    "char_aldunate": "Ximena Aldunate",
    "char_model": "unnamed checkpoint",
}

ATT_NUDGE_PER_POINT = 0.1
ASC_NUDGE_PER_POINT = 0.1
THRESHOLD = 0.5


def bnum_ptr(char_id, prop, coefficient=1):
    return {
        "pointer_type": "Bounded Number Pointer",
        "script_element_type": "Pointer",
        "character": char_id,
        "keyring": [prop],
        "coefficient": coefficient,
    }


def bnum_const(value):
    return {
        "pointer_type": "Bounded Number Constant",
        "script_element_type": "Pointer",
        "value": value,
    }


def string_const(value):
    return {
        "pointer_type": "String Constant",
        "script_element_type": "Pointer",
        "value": value,
    }


def addition(char_id, prop, delta):
    return {
        "script_element_type": "Bounded Number Operator",
        "operator_type": "Addition",
        "operands": [bnum_ptr(char_id, prop), bnum_const(delta)],
    }


def cmp(char_id, prop, op, value):
    return {
        "script_element_type": "Boolean Operator",
        "operator_type": "Arithmetic Comparator",
        "operator_subtype": op,
        "operands": [bnum_ptr(char_id, prop), bnum_const(value)],
    }


def and_(*terms):
    return {"script_element_type": "Boolean Operator", "operator_type": "And", "operands": list(terms)}


# The three-tier ending gate (closes README open thread #1). Defined once here
# so both the ante_close branch options and the verdict encounters below use
# the identical conditions -- explicit visibility-gated options rather than
# "wild" dynamic routing, since the Monte Carlo rehearsal script (unlike the
# browser reader) doesn't implement wild-consequence encounter selection.
VERDICT_CONDITIONS = {
    "page_secret_calibrated": and_(
        cmp("char_case", "Attestation", "Greater Than or Equal To", THRESHOLD),
        cmp("char_case", "Ascription", "Greater Than or Equal To", THRESHOLD),
    ),
    "page_end_particular_overascription": and_(
        cmp("char_case", "Ascription", "Greater Than or Equal To", THRESHOLD),
        cmp("char_case", "Attestation", "Less Than", THRESHOLD),
    ),
    "page_end_lamport_reductive": and_(
        cmp("char_case", "Attestation", "Greater Than or Equal To", THRESHOLD),
        cmp("char_case", "Ascription", "Less Than", THRESHOLD),
    ),
    "page_end_unresolved": and_(
        cmp("char_case", "Attestation", "Less Than", THRESHOLD),
        cmp("char_case", "Ascription", "Less Than", THRESHOLD),
    ),
}


def bnum_effect(char_id, prop, to_script):
    return {
        "effect_type": "Bounded Number Effect",
        "Set": {
            "pointer_type": "Bounded Number Property",
            "script_element_type": "Pointer",
            "character": char_id,
            "keyring": [prop],
            "coefficient": 1,
        },
        "to": to_script,
    }


def node_text(node):
    text = node["text"]
    if node.get("host"):
        text = f"[{node['host']}]\n\n{text}"
    return text


def build():
    encounters = []
    creation_index = 0

    for key, node in STORY.items():
        eid = f"page_{key}"
        options = []

        choices = node.get("choices")
        if choices:
            for i, choice in enumerate(choices):
                opt_id = f"{eid}_opt{i}"
                after_effects = []
                if choice.get("att"):
                    after_effects.append(bnum_effect(
                        "char_case", "Attestation",
                        addition("char_case", "Attestation", choice["att"] * ATT_NUDGE_PER_POINT),
                    ))
                if choice.get("asc"):
                    after_effects.append(bnum_effect(
                        "char_case", "Ascription",
                        addition("char_case", "Ascription", choice["asc"] * ASC_NUDGE_PER_POINT),
                    ))
                if choice.get("flag") == "attested-identity":
                    after_effects.append(bnum_effect("char_case", "AttestedIdentity", bnum_const(1)))

                option = {
                    "id": opt_id,
                    "text_script": string_const(choice["label"]),
                    "reactions": [{
                        "id": f"{opt_id}_rxn1",
                        "text_script": string_const(""),
                        "consequence_id": f"page_{choice['to']}",
                        "after_effects": after_effects,
                    }],
                }
                if choice.get("requires") == "attested-identity":
                    option["visibility_script"] = cmp("char_case", "AttestedIdentity", "Greater Than", 0)
                options.append(option)
        elif key == "ante_close":
            # The pilot's single terminal node in frame-theater.html. Here it
            # branches into one of four verdict encounters via explicit
            # visibility-gated options (mutually exclusive + exhaustive over
            # the Attestation/Ascription quadrant), rather than "wild" dynamic
            # routing -- see VERDICT_CONDITIONS.
            for i, (verdict_id, condition) in enumerate(VERDICT_CONDITIONS.items()):
                opt_id = f"{eid}_opt{i}"
                options.append({
                    "id": opt_id,
                    "text_script": string_const("Close the case file."),
                    "visibility_script": condition,
                    "reactions": [{
                        "id": f"{opt_id}_rxn1",
                        "text_script": string_const(""),
                        "consequence_id": verdict_id,
                        "after_effects": [],
                    }],
                })
        else:
            # pass-through node: single "Continue" option
            to = node.get("to")
            options.append({
                "id": f"{eid}_opt0",
                "text_script": string_const("Continue."),
                "reactions": [{
                    "id": f"{eid}_opt0_rxn1",
                    "text_script": string_const(""),
                    "consequence_id": f"page_{to}",
                    "after_effects": [],
                }],
            })

        encounters.append({
            "id": eid,
            "title": key.replace("_", " ").title(),
            "connected_spools": [spool_for(key)],
            "earliest_turn": 0,
            "latest_turn": 999,
            "text_script": string_const(node_text(node)),
            "options": options,
            "acceptability_script": True,
            "desirability_script": bnum_const(0),
            "creation_index": creation_index,
        })
        creation_index += 1

    # ---- the three-tier ending gate (closes README open thread #1) --------
    verdicts = [
        {
            "id": "page_secret_calibrated",
            "title": "Verdict: Calibrated (secret ending)",
            "text": "Six weeks later the coup-simulation traffic stops appearing in the logs, and Commerce closes the file as resolved. Voidt writes the memo anyway: no author, no intention, a standing wave the swarm assembled and then stopped assembling. You verified what could be verified and you did not collapse the rest into a story. That is the whole discipline. It has never once been more than that.",
            "desirability_script": bnum_const(10),
        },
        {
            "id": "page_end_particular_overascription",
            "title": "Verdict: Confidently Wrong (the attractor)",
            "text": "Six weeks later the coup-simulation traffic stops appearing in the logs, and Commerce closes the file as resolved. Somewhere in the writeup a sentence survives that shouldn't: an author, an intention, a hand on the wheel. It reads clean. It reads complete. It is wrong in the specific way that confidence is wrong — high closure, low accuracy — and nobody upstream will ever be able to tell the difference from the prose alone.",
            "desirability_script": bnum_const(10),
        },
        {
            "id": "page_end_lamport_reductive",
            "title": "Verdict: Reductive (Lamport's reverb)",
            "text": "Six weeks later the coup-simulation traffic stops appearing in the logs, and Commerce closes the file as resolved. The writeup calls it a reverb of a thousand idealistic International Studies majors, and every fact in it is true. It attests everything and ascribes nothing, and it will never once have to explain why the thing that stopped had, for a while, seemed to be listening.",
            "desirability_script": bnum_const(10),
        },
        {
            "id": "page_end_unresolved",
            "title": "Verdict: Unresolved",
            "text": "Six weeks later the coup-simulation traffic stops appearing in the logs, and Commerce closes the file as resolved. Nobody wrote a strong enough sentence to be wrong about it. The file goes in a drawer with the shape of a question and no shape of an answer, which is its own kind of honesty, and its own kind of failure.",
            "desirability_script": bnum_const(0),
        },
    ]
    for v in verdicts:
        encounters.append({
            "id": v["id"],
            "title": v["title"],
            "connected_spools": ["spool_endings"],
            "earliest_turn": 0,
            "latest_turn": 999,
            "text_script": string_const(v["text"]),
            "options": [],
            # Redundant with the ante_close option's visibility_script (same
            # VERDICT_CONDITIONS), kept here too as defense-in-depth.
            "acceptability_script": VERDICT_CONDITIONS[v["id"]],
            "desirability_script": v["desirability_script"],
            "creation_index": creation_index,
        })
        creation_index += 1

    spools = [
        {"id": "spool_act1_halcyon", "spool_name": "Act 1 — The Halcyon Interim", "spool_type": "General",
         "creation_index": 0, "starts_active": True, "encounters": [f"page_{k}" for k in ACT1]},
        {"id": "spool_act2_fourth_floor", "spool_name": "Act 2 — The Fourth Floor", "spool_type": "General",
         "creation_index": 1, "starts_active": True, "encounters": [f"page_{k}" for k in ACT2]},
        {"id": "spool_act3_anteroom", "spool_name": "Act 3 — The Anteroom", "spool_type": "General",
         "creation_index": 2, "starts_active": True, "encounters": [f"page_{k}" for k in ACT3]},
        {"id": "spool_endings", "spool_name": "Endings", "spool_type": "General",
         "creation_index": 3, "starts_active": True, "encounters": [v["id"] for v in verdicts]},
    ]

    characters = [
        {"id": cid, "name": name, "bnumber_properties": {}}
        for cid, name in CHAR_NAMES.items()
    ] + [
        {
            "id": "char_case",
            "name": "The Case File",
            "bnumber_properties": {"Attestation": 0, "Ascription": 0, "AttestedIdentity": 0},
        },
    ]

    authored_properties = [
        {"id": "Attestation", "property_name": "Attestation", "property_type": "bounded number",
         "default_value": 0, "creation_index": 0},
        {"id": "Ascription", "property_name": "Ascription", "property_type": "bounded number",
         "default_value": 0, "creation_index": 1},
        {"id": "AttestedIdentity", "property_name": "AttestedIdentity", "property_type": "bounded number",
         "default_value": 0, "creation_index": 2},
    ]

    storyworld = {
        "IFID": "SW-THOUGHTLEADER-PILOT-0001",
        "title": "Thought Leader — Pilot: The Halcyon Interim",
        "storyworld_title": "Thought Leader — Pilot: The Halcyon Interim",
        "about_text": string_const(
            "Agent Kaitlyn Voidt and Agent Dudley Lamport of the Bureau for Emerging Threats "
            "investigate a model that passed its own evaluation. A structured port of the "
            "frame-theater.html pilot, with the three-tier ending (calibrated / confidently-"
            "wrong / reductive / unresolved) gated on the Attestation and Ascription axes "
            "tracked throughout play."
        ),
        "css_theme": "dark",
        "debug_mode": False,
        "display_mode": "default",
        "creation_time": T,
        "modified_time": T,
        "characters": characters,
        "authored_properties": authored_properties,
        "spools": spools,
        "encounters": encounters,
    }
    return storyworld


def spool_for(key):
    if key in ACT1:
        return "spool_act1_halcyon"
    if key in ACT2:
        return "spool_act2_fourth_floor"
    return "spool_act3_anteroom"


if __name__ == "__main__":
    sw = build()
    out_path = __file__.replace("build_pilot.py", "thought-leader-pilot.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sw, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out_path} ({len(sw['encounters'])} encounters)")
