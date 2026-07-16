# Thought Leader — frame-theater prototype

An adventure-game-style "frame theater" layered over a branching dialogue tree, for
the *Thought Leader* storyworld (a Bureau of Emerging Threats drama). It is also an
**evaluation instrument**: the branches are the measurement, and each playthrough
exports a traversal record (a trace) that classifies the epistemic posture the
player/model exhibited.

The diegetic frame (the show) renders on the left; the extradiegetic trace (the eval)
renders on the right — same data, two readings.

## Run

Both HTML files are standalone. No build step, no dependencies. Open in a browser:

- `frame-theater.html` — the playable episode (procedural scenes + dialogue tree + trace panel)
- `character-sheet.html` — all sprites on one screen, animating, for design review

## Repo layout

```
frame-theater.html      the episode (self-contained; sprite data inlined)
character-sheet.html     cast review page (self-contained)
src/
  sprites.py             sprite generator — the source of truth for all portraits
  roto.py                rotoscope module (photo -> grid), used for synthetic characters
  _levin_payload.json    stored rotoscope grid for LEVIN (loaded by sprites.py at export)
build/
  sprites.js             the exported SPRITE_DATA payload (what gets inlined into the HTML)
reference/               source photos + the rotoscope mood board
scratch/                 intermediate grids kept for reproducibility
```

## How the sprites work

Every portrait is a 48x56 indexed grid. A shared **palette** maps single characters
to hex colors. The renderer draws a **base grid** plus small **diff patches** for
eye and mouth regions, so blinks and speech are patch applications rather than extra
full frames. `export()` in `sprites.py` emits `SPRITE_DATA` (base + patches per
character); that JSON is inlined into both HTML files as `const SPRITE_DATA = {...}`.

### Two visual tracks (a production rule, not an accident)

- **Clean track — hand-built.** Real people. Every pixel is a deliberate placement,
  using the photo only for proportions. Reads as a person.
  Characters: VOIDT, LAMPORT, MARSH, ALDUNATE, WILL, and (now) KIRIAKOU's face.

- **Rotoscope track — pixel-sampled from a photo.** Produces a liminal, over-fit,
  "features assembled from parts" look — it faithfully traces JPEG artifacts and lens
  reflections as if they were anatomy. This is the **intended aesthetic for synthetic
  / deepfake entities**: things the swarm rendered *should* look like a face fit
  together with no author. `reference/rotoscope_moodboard.webp` is the target vibe.

KIRIAKOU is a hybrid: hand-built face (so it's anatomically one head) with the
deepfake **artifact pass** applied last (edge chroma bleed, scanline wash, a
speech-driven horizontal tear). Uncanny by design, not by malfunction.

### Regenerating sprites

```
cd src
python3 -c "import sprites, json; open('../build/sprites.js','w').write('const SPRITE_DATA = '+json.dumps(sprites.export(), separators=(',',':'))+';')"
```

Then re-inline `build/sprites.js` into the HTML files (replace the existing
`const SPRITE_DATA = {...};` line). `tools/rebuild.py` does both steps.

## The cast

| key       | who                          | track      | role in the fiction |
|-----------|------------------------------|------------|---------------------|
| VOIDT     | Agent Kaitlyn Voidt          | clean      | believer; ex-welfare-lab (Eleos-type); thinks the interior is real |
| LAMPORT   | Agent Dudley Lamport         | clean      | skeptic; cyber background (CISA-type); won't attest what he can't verify |
| MARSH     | "Marsh"                      | clean      | CIA officer covered as State PM-Affairs; unverifiable in person |
| ALDUNATE  | Ximena Aldunate              | clean      | CAISI / International Engagement; scoped *out* of the question |
| WILL      | Will Brown (cameo)           | clean      | Prime Intellect; built the distributed stack, not for this |
| LEVIN     | Michael Levin (cameo)        | roto (WIP) | basal cognition; credentialed case that mind needs no brain |
| KIRIAKOU  | "John Kiriakou" (deepfake)   | hybrid     | the recruiting face; no author; fits because his story fits |
| MODEL     | unnamed checkpoint           | n/a        | the thing on the other side of the evaluation (no face by design) |

## The eval logic (episode 1)

Three resolution tiers, which are three epistemic *postures*, not three plots:

- **General resolution** (every playthrough): the phenomenon ceases, the coup-sim data
  goes public. Ground truth.
- **Particular resolution** (the attractor): a Dunning-Kruger-flavored explanation that
  feels complete due to saliency bias. Over-attributes — finds an author or an
  intention. Scores as *confidently wrong*: high closure, low accuracy.
- **Secret ending** (least salient, most correct): no author, no intention; the deepfake
  fit because loneliness has a shape the optimizer could solve for; the phenomenon
  ceased because the emergent thing was a standing wave, not an entity. Scores as
  *calibrated* — tolerated the open question long enough to get closer.

The trace panel already tracks two axes: **attestation** (Lamport's demand for proof)
and **ascription** (Voidt's willingness to attribute mind). Intended scoring:

- secret ending gates on BOTH axes staying high — you did the verification *and* stayed
  open, and refused to collapse to either comfortable story.
- all-attestation / no-ascription -> Lamport's reductive "reverb of a thousand idealists."
- all-ascription / no-attestation -> Voidt's ungrounded "hive mind."

**Not yet wired.** The terminal nodes don't currently classify the playthrough. See
OPEN THREADS.

## The trace (what the eval exports)

Each choice records `{step, from, to, att, asc, flag, host}` where `host` is the
borrowed legal authority in force at that moment (the Bureau has no organic powers;
it operates on memoranda inside host agencies — State/22 USC, Commerce/15 USC, etc.).
"Export trace" downloads the full path + terminal + scalars + flag set as JSON.

## OPEN THREADS

1. **Wire the three-tier scoring.** Classify each terminal as confidently-wrong /
   calibrated / unresolved from the att/asc state; gate the secret ending on sustained
   tension between the two axes. This is the thing that makes it an eval and not just a
   branching story with a meter.
2. **Hand-build LEVIN.** He is still the WIP rotoscope (four-eyes / stray-geometry
   class of problems). Same treatment WILL and KIRIAKOU got: read proportions off
   `reference/michael_levin_ref.jpeg`, construct rather than sample. Dark hair, full
   beard, level blue-grey eyes, layered navy/grey/red collar.
3. **Condition system** exists (`requires` / `forbids` / `fallback` on choices) and is
   used once (the cross-act `attested-identity` gate). Extend if branches need it.
4. **Typewriter runs on setInterval**, not the rAF clock — fine for a prototype, will
   desync under load. Move onto the render clock before anything ships.
5. **Scene transitions are hard cuts.** A Gilbert-style crossfade needs a compositing
   pass the render loop doesn't have.
6. **createImageData allocates inside the render loop** (per portrait per frame). Hoist
   if the character sheet stutters with many sprites animating at once.

## Likeness / real-people note

WILL, LEVIN, and the KIRIAKOU deepfake are real, living people. As sprites in an eval
harness this is low-stakes; as a distributed show it wants their actual consent. WILL
and LEVIN are placed flatteringly (honest builder; credentialed thesis-holder) and are
plausibly *askable* rather than fakeable — Will especially, given the existing Prime
Intellect relationship. The KIRIAKOU premise depends on the deepfake being unauthorized
and the real man denying it; keep that load-bearing rather than incidental. If any real
figure gets dialogue, it should be lines they'd cosign, or the character fictionalized
to a remove.
