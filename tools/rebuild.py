#!/usr/bin/env python3
"""Regenerate sprites and re-inline them into both HTML files.

Usage:  python3 tools/rebuild.py
Run from the repo root.
"""
import json, re, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)
import sprites  # noqa: E402

def main():
    data = sprites.export()
    payload = "const SPRITE_DATA = " + json.dumps(data, separators=(",", ":")) + ";"

    build = os.path.join(ROOT, "build", "sprites.js")
    with open(build, "w") as f:
        f.write(payload)
    print(f"wrote {build}  ({len(payload)} bytes, {len(data['sprites'])} sprites)")

    # sanity: no backslash contamination, every cell char is in the palette
    pal = set(data["pal"])
    bad = set()
    for name, sp in data["sprites"].items():
        blocks = [sp["base"]] + [sp[k]["rows"] for k in ("eyesClosed", "mouthMid", "mouthOpen")
                                 if sp.get(k)]
        for rows in blocks:
            for r in rows:
                for c in r:
                    if c != " " and c not in pal:
                        bad.add(f"{name}:{c!r}")
        if len(sp["base"]) != data["h"] or any(len(r) != data["w"] for r in sp["base"]):
            bad.add(f"{name}:dims")
    assert "\\" not in payload, "backslash in payload — will break JSON/JS"
    assert not bad, f"palette/dim errors: {bad}"

    for name in ("frame-theater.html", "character-sheet.html"):
        path = os.path.join(ROOT, name)
        html = open(path).read()
        html, n = re.subn(r"const SPRITE_DATA = \{.*?\};\n", payload + "\n",
                          html, count=1, flags=re.S)
        assert n == 1, f"could not find SPRITE_DATA line in {name}"
        open(path, "w").write(html)
        print(f"inlined into {name}")

    print("ok — all sprites valid, both HTML files updated")

if __name__ == "__main__":
    main()
