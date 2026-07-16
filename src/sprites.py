"""Authoring tool for THOUGHT LEADER portraits.

48x56 indexed grids. Shading is clipped to the pixels it belongs on, so no
detached chunks. Each character owns its skin ramp.
"""
from PIL import Image
import json

W, H = 48, 56

PALETTE = {
    ':': "#0e131b", '`': "#161e29",            # backdrop
    'r': "#5b6472", 'R': "#8f9aa8",            # rim light, cold key
    'k': "#05070a", 'n': "#0d1219", 's': "#1a2430",

    '#': "#120e18", '%': "#241a2c", '*': "#3d2c44",   # Voidt hair
    'o': "#b0806f", 'O': "#d8a68f", '@': "#efc7ae", '=': "#8e6155",  # Voidt skin
    '-': "#4a2f33",                                    # Voidt brow
    'l': "#7a4150", 'L': "#a76271",                    # Voidt lip
    'a': "#a2647f", 'A': "#c98aa4",                    # Voidt accent

    '1': "#3d2820", '2': "#6d4632", '3': "#96684a",    # Lamport skin
    '4': "#b0805c", '5': "#c99b74",
    '6': "#2b1a12", '7': "#7d4a3f", '8': "#a06a58",    # Lamport brow, lip, lip light
    'h': "#1e1c19", 'H': "#6b675d",                    # cropped hair, graying
    'b': "#332f28", 'B': "#6d6759",                    # beard, salt and pepper
    'g': "#0b1113", 'G': "#16292e", 'q': "#46545a",    # frame, lens, rim highlight
    't': "#6fb3a8", 'T': "#3f6f6a",                    # teal glint, tie

    'e': "#e6ded6", 'p': "#1e1720", 'w': "#ffffff",    # eyes
    'm': "#3a1f28", '_': "#6b4340",                    # mouth interior, soft line
    'c': "#111620", 'C': "#212834", 'v': "#2d3542",    # coat
    'W': "#aeb4bd", 'S': "#7d838c",                    # shirt
    'y': "#d9a441", 'Y': "#f0c469",

    # Marsh — pale, unremarkable, backlit rather than rim-lit
    'd': "#a3786a", 'D': "#cba08e", 'f': "#e4c0ac", 'F': "#f3d8c6",
    'i': "#7a6b55", 'I': "#a99879", 'j': "#6a5340", 'J': "#a06f62",
    'x': "#2b303a", 'X': "#3e444f", 'z': "#2c3f60", 'Z': "#46628e",
    'N': "#1b2942", 'M': "#d5d8db", '0': "#38445a", '9': "#5b6a82",

    # Aldunate — cool key from the other side, paper at the collar
    'u': "#7c5c44", 'U': "#a87c5a", 'P': "#c69b76", 'Q': "#e2c09c",
    'V': "#16141d", 'K': "#2c2838", 'E': "#4a4356",
    '+': "#cdc3a5", '&': "#9d9479",

    # Kiriakou deepfake — warmer Levantine skin, salt-and-pepper hair, glasses.
    '!': "#8a5c40", '$': "#c69069",                    # skin shadow / base
    '<': "#e0b487", '>': "#5a3927",                    # skin light / deep crease
    '^': "#3a6b6a", '~': "#7fd0c4",                    # chroma-bleed teal
    '?': "#a8506a", ';': "#e08098",                    # chroma-bleed magenta
    '/': "#2b2824", '(': "#726b5e",                    # hair dark / gray strand
    '[': "#454038", ']': "#9a9184",                    # hair mid / gray highlight
    '{': "#141414", '}': "#3a3f4a",                    # glasses frame / lens
    '|': "#6f7d8a",                                    # lens catch-light

    # Levin/Will roto colors
    'g': "#5a5f66", 'R': "#a84a3a",                    # grey layer, red tee

    # Will Brown reuses Marsh skin (d/D/f/F) + brown hair (1/2/3)
}

SKIN_V = set('oO@=')
SKIN_L = set('12345')
SKIN_M = set('dDfF')
SKIN_A = set('uUPQ')
SKIN_K = set('!$<>')

# ---------------------------------------------------------------- helpers

def blank():
    return [[' '] * W for _ in range(H)]

def run(g, y, x0, x1, ch):
    if 0 <= y < H:
        for x in range(max(0, x0), min(W - 1, x1) + 1):
            g[y][x] = ch

def shade(g, y, x0, x1, ch, over):
    """Paint only where the pixel is already part of `over` — clips to the face."""
    if 0 <= y < H:
        for x in range(max(0, x0), min(W - 1, x1) + 1):
            if g[y][x] in over:
                g[y][x] = ch

def rect(g, x0, y0, x1, y1, ch):
    for y in range(y0, y1 + 1):
        run(g, y, x0, x1, ch)

def put(g, x, y, ch):
    if 0 <= x < W and 0 <= y < H:
        g[y][x] = ch

def ellipse(g, cx, cy, rx, ry, ch, over=None):
    for y in range(H):
        for x in range(W):
            dx, dy = (x - cx) / rx, (y - cy) / ry
            if dx * dx + dy * dy <= 1.0:
                if over is None or g[y][x] in over:
                    g[y][x] = ch

def backdrop(g):
    rect(g, 0, 0, W - 1, H - 1, ':')
    for y in range(H):
        for x in range(W):
            dx, dy = (x - 24) / 20.0, (y - 22) / 24.0
            if dx * dx + dy * dy < 1.0:
                g[y][x] = '`'
    rect(g, 0, 50, W - 1, H - 1, ':')

def rim(g, mass, y0, y1, x0, x1):
    for y in range(y0, y1):
        for x in range(x0, x1):
            if g[y][x] in mass and g[y][x - 1] not in mass and g[y][x - 1] != 'r':
                g[y][x] = 'r' if y > 17 else 'R'
                break

def edge_stub(g, y0, y1, skin, ch, depth, xmin=0, xmax=W - 1):
    """Paint `depth` pixels inward from the face contour on each row — stubble
    that follows the jaw rather than a rectangle laid over it."""
    for y in range(y0, y1 + 1):
        xs = [x for x in range(xmin, xmax + 1) if g[y][x] in skin]
        if not xs: continue
        for d in range(depth):
            if xs[0] + d <= xs[-1] - d:
                put(g, xs[0] + d, y, ch)
                put(g, xs[-1] - d, y, ch)

def despeckle(g, group):
    """A pixel of `group` with at most one neighbour of `group` is noise at this
    scale; hand it to whatever surrounds it."""
    for _ in range(2):
        kills = []
        for y in range(H):
            for x in range(W):
                if g[y][x] not in group: continue
                nb = [(b, a) for b in range(max(0, y - 1), min(H, y + 2))
                             for a in range(max(0, x - 1), min(W, x + 2)) if (b, a) != (y, x)]
                same = [1 for b, a in nb if g[b][a] in group]
                if len(same) <= 1:
                    others = [g[b][a] for b, a in nb if g[b][a] not in group]
                    if others:
                        kills.append((x, y, max(set(others), key=others.count)))
        for x, y, ch in kills:
            g[y][x] = ch

def rim_right(g, mass, y0, y1, x0, x1):
    """Rim light entering from the right. Aldunate is not lit by the desk lamp."""
    for y in range(y0, y1):
        for x in range(x1, x0, -1):
            if x + 1 < W and g[y][x] in mass and g[y][x + 1] not in mass and g[y][x + 1] != 'r':
                g[y][x] = 'r' if y > 17 else 'R'
                break

def backdrop_door(g):
    """Marsh gets no rim light. He gets a doorway behind him, which is worse."""
    rect(g, 0, 0, W - 1, H - 1, ':')
    rect(g, 10, 0, 37, 53, 'n')
    rect(g, 12, 0, 35, 51, '0')
    rect(g, 15, 0, 32, 49, '9')
    rect(g, 0, 51, W - 1, H - 1, ':')

def shoulder_rim(g):
    for y in range(44, H):
        for x in range(W):
            if g[y][x] in 'cCv' and y > 0 and g[y - 1][x] not in 'cCvr':
                g[y][x] = 'r'

# ---------------------------------------------------------------- VOIDT

def voidt(eyes="open", mouth="closed"):
    g = blank()
    backdrop(g)

    ellipse(g, 24, 21, 13, 16, '#')
    for y in range(20, 42):
        t = (y - 20) / 21.0
        inset = int(t * t * 5)
        run(g, y, 11 + inset, 15 + inset // 2, '#')
        run(g, y, 32 - inset // 2, 36 - inset, '#')
    run(g, 42, 17, 19, '#'); run(g, 42, 28, 30, '#')
    run(g, 43, 18, 19, '%'); run(g, 43, 28, 29, '%')

    ellipse(g, 24, 15, 10, 7, '%')
    ellipse(g, 21, 12, 5, 3, '*')
    run(g, 10, 27, 30, '*'); run(g, 11, 28, 31, '*')
    run(g, 18, 12, 13, '%'); run(g, 22, 12, 13, '%')
    run(g, 18, 34, 35, '%'); run(g, 24, 34, 35, '%')

    rim(g, '#%*', 7, 34, 9, 20)
    for y in range(6, 12):
        for x in range(28, 38):
            if g[y][x] in '#%*' and g[y - 1][x] not in '#%*':
                g[y][x] = 'r'

    # face
    ellipse(g, 24, 26, 8, 12, 'O')
    ellipse(g, 24, 25, 6, 9, '@')
    run(g, 15, 18, 29, 'O'); run(g, 16, 17, 30, 'O')
    run(g, 16, 20, 27, '@'); run(g, 17, 19, 28, '@')

    # fringe
    run(g, 14, 16, 31, '#')
    run(g, 15, 16, 19, '#'); run(g, 15, 30, 31, '#')
    put(g, 20, 15, '%'); put(g, 29, 15, '%')
    run(g, 16, 16, 17, '#'); put(g, 31, 16, '#')
    run(g, 16, 21, 22, '#'); put(g, 21, 17, '%')

    # shading, clipped to skin
    shade(g, 27, 16, 17, 'o', SKIN_V); shade(g, 28, 16, 17, 'o', SKIN_V)
    shade(g, 27, 30, 31, 'o', SKIN_V); shade(g, 28, 30, 31, 'o', SKIN_V)
    shade(g, 33, 17, 19, 'o', SKIN_V); shade(g, 33, 28, 30, 'o', SKIN_V)
    shade(g, 35, 18, 29, 'o', SKIN_V)
    shade(g, 36, 19, 28, 'o', SKIN_V); shade(g, 37, 20, 27, 'o', SKIN_V)
    shade(g, 38, 21, 26, '=', SKIN_V)

    despeckle(g, SKIN_V)

    # brows
    run(g, 19, 18, 22, '-'); put(g, 17, 20, '-')
    run(g, 19, 25, 29, '-'); put(g, 30, 20, '-')

    if eyes == "open":
        run(g, 21, 18, 22, 'e'); run(g, 22, 18, 22, 'e')
        run(g, 21, 25, 29, 'e'); run(g, 22, 25, 29, 'e')
        rect(g, 19, 21, 21, 22, 'p'); rect(g, 26, 21, 28, 22, 'p')
        put(g, 19, 21, 'w'); put(g, 26, 21, 'w')
        run(g, 20, 18, 22, '-'); run(g, 20, 25, 29, '-')
        put(g, 23, 22, 'o'); put(g, 24, 22, 'o')
    else:
        run(g, 21, 18, 22, '-'); run(g, 21, 25, 29, '-')
        run(g, 22, 18, 22, 'o'); run(g, 22, 25, 29, 'o')
    shade(g, 23, 18, 21, 'o', SKIN_V); shade(g, 23, 26, 29, 'o', SKIN_V)

    # nose
    shade(g, 26, 23, 24, 'o', SKIN_V); shade(g, 27, 23, 25, 'o', SKIN_V)
    shade(g, 28, 22, 25, 'o', SKIN_V)
    put(g, 23, 28, '='); put(g, 25, 28, '=')

    if mouth == "closed":
        run(g, 32, 21, 26, 'l'); run(g, 33, 22, 25, 'L')
    elif mouth == "mid":
        run(g, 32, 21, 26, 'l'); run(g, 33, 22, 25, 'm'); run(g, 34, 22, 25, 'L')
    else:
        run(g, 31, 22, 26, 'l'); rect(g, 22, 32, 25, 33, 'm'); run(g, 34, 22, 25, 'L')

    # neck, coat, scarf
    rect(g, 20, 39, 27, 44, 'O'); rect(g, 20, 39, 27, 41, '=')
    rect(g, 4, 46, 43, 55, 'C'); rect(g, 2, 49, 45, 55, 'C')
    run(g, 46, 4, 43, 'v'); rect(g, 0, 52, 47, 55, 'c')
    for i, y in enumerate(range(45, 56)):
        run(g, y, 17 - i // 2, 20 - i // 2, 'c')
        run(g, y, 27 + i // 2, 30 + i // 2, 'c')
    rect(g, 19, 43, 28, 47, 'a')
    run(g, 43, 20, 27, 'A'); run(g, 44, 19, 22, 'A')
    put(g, 18, 45, 'a'); put(g, 29, 45, 'a')

    shoulder_rim(g)
    return g

# ---------------------------------------------------------------- LAMPORT

def lamport(eyes="open", mouth="closed"):
    g = blank()
    backdrop(g)

    # skull: long, high forehead, narrow nose bridge
    ellipse(g, 24, 27, 9, 13, '3')
    ellipse(g, 24, 26, 7, 10, '4')
    ellipse(g, 24, 23, 5, 6, '5')
    run(g, 14, 18, 30, '3'); run(g, 15, 17, 31, '3')
    run(g, 15, 20, 28, '4'); run(g, 16, 19, 29, '4')

    # close-cropped hair, receded at the temples, graying at the sides
    run(g, 13, 19, 29, 'h'); run(g, 12, 20, 28, 'h'); run(g, 11, 22, 27, 'h')
    for y in range(14, 24):
        run(g, y, 14, 16, 'h'); run(g, y, 32, 34, 'h')
    run(g, 19, 14, 15, 'H'); run(g, 20, 14, 16, 'H'); run(g, 21, 14, 15, 'H')
    run(g, 20, 33, 34, 'H'); run(g, 21, 32, 34, 'H'); run(g, 22, 33, 34, 'H')
    put(g, 24, 12, 'H'); put(g, 26, 11, 'H')

    # ears
    run(g, 24, 14, 15, '2'); run(g, 25, 14, 15, '2'); put(g, 15, 26, '2')
    run(g, 24, 33, 34, '2'); run(g, 25, 33, 34, '2'); put(g, 33, 26, '2')

    # brow ridge, lifted clear of the frame
    run(g, 19, 17, 22, '6'); run(g, 18, 18, 21, '6')
    run(g, 19, 26, 31, '6'); run(g, 18, 27, 30, '6')
    shade(g, 20, 17, 21, '2', SKIN_L); shade(g, 20, 27, 31, '2', SKIN_L)
    shade(g, 21, 23, 25, '2', SKIN_L); put(g, 24, 18, '2')

    if eyes == "open":
        run(g, 23, 18, 21, 'e'); run(g, 24, 18, 21, 'e')
        run(g, 23, 27, 30, 'e'); run(g, 24, 27, 30, 'e')
        rect(g, 19, 23, 20, 24, 'p'); rect(g, 28, 23, 29, 24, 'p')
        put(g, 19, 23, 'w'); put(g, 28, 23, 'w')
    else:
        run(g, 23, 18, 21, '_'); run(g, 23, 27, 30, '_')
        run(g, 24, 18, 21, '2'); run(g, 24, 27, 30, '2')

    # glasses: thin rims a row below the brow, top edge catching light
    run(g, 22, 17, 21, 'g'); run(g, 22, 27, 31, 'g')
    rect(g, 16, 23, 16, 25, 'g'); rect(g, 22, 23, 22, 25, 'g')
    rect(g, 26, 23, 26, 25, 'g'); rect(g, 32, 23, 32, 25, 'g')
    run(g, 26, 17, 21, 'g'); run(g, 26, 27, 31, 'g')
    run(g, 23, 23, 25, 'g')
    run(g, 23, 13, 15, 'g'); run(g, 23, 33, 35, 'g')
    put(g, 18, 22, 'q'); put(g, 19, 22, 'q'); put(g, 29, 22, 'q')
    put(g, 17, 25, 'G'); put(g, 31, 25, 'G')
    put(g, 17, 23, 't'); put(g, 18, 23, 't')

    # nose: a lit ridge with shadow on one side only. Filling the whole nose
    # with shadow reads as pigmentation, not as form.
    for y in range(24, 29):
        shade(g, y, 24, 24, '5', SKIN_L)      # ridge, catching the key
        shade(g, y, 23, 23, '4', SKIN_L)
        shade(g, y, 25, 25, '3', SKIN_L)      # the turn away from the light
    shade(g, 27, 26, 26, '2', SKIN_L)
    shade(g, 28, 22, 26, '3', SKIN_L)         # broader base
    run(g, 29, 23, 25, '2')                   # underside
    put(g, 22, 29, '1'); put(g, 26, 29, '1')  # nostrils
    put(g, 24, 28, '5')

    # cheek: one pixel of turn, following the bone. Not a band across the face.
    shade(g, 28, 19, 19, '3', SKIN_L); shade(g, 29, 19, 20, '3', SKIN_L)
    shade(g, 30, 20, 21, '3', SKIN_L)
    shade(g, 28, 29, 29, '3', SKIN_L); shade(g, 29, 28, 29, '3', SKIN_L)
    shade(g, 30, 27, 28, '3', SKIN_L)
    shade(g, 27, 16, 17, '2', SKIN_L); shade(g, 28, 16, 17, '2', SKIN_L)
    shade(g, 27, 31, 32, '2', SKIN_L); shade(g, 28, 31, 32, '2', SKIN_L)

    # beard: close-cropped, tracing the jaw. Moustache and chin are pulled apart
    # so a lit band of upper lip sits between the hair and the mouth.
    edge_stub(g, 26, 30, SKIN_L, 'b', 1, 16, 32)   # sideburns, clear of the ears
    edge_stub(g, 30, 40, SKIN_L, 'b', 2, 15, 33)   # jawline, overlapping the above
    for y, (x0, x1) in ((36, (20, 28)), (37, (19, 29)), (38, (19, 29)),
                        (39, (20, 28)), (40, (22, 26))):
        shade(g, y, x0, x1, 'b', SKIN_L | {'b'})   # chin, explicit rows: an
                                                   # ellipse leaves lone vertex pixels
    run(g, 30, 21, 27, 'b'); run(g, 31, 22, 26, 'b')    # moustache
    shade(g, 32, 21, 27, '4', SKIN_L)                   # upper lip, lit
    shade(g, 35, 21, 27, '2', SKIN_L)                   # under the lower lip

    # gray where a beard grays first
    put(g, 21, 30, 'B'); put(g, 27, 30, 'B')
    put(g, 17, 32, 'B'); put(g, 18, 33, 'B')
    put(g, 31, 32, 'B'); put(g, 30, 33, 'B')
    run(g, 38, 20, 22, 'B'); run(g, 38, 27, 28, 'B')

    # mouth sits on lit skin, two values clear of the beard
    if mouth == "closed":
        run(g, 33, 21, 27, '7'); run(g, 34, 22, 26, '8')
    elif mouth == "mid":
        run(g, 33, 21, 27, '7'); run(g, 34, 22, 26, 'm'); run(g, 35, 23, 25, '8')
    else:
        run(g, 32, 22, 26, '7'); rect(g, 22, 33, 26, 34, 'm'); run(g, 35, 22, 26, '8')

    despeckle(g, SKIN_L)
    despeckle(g, 'bB')
    rim(g, 'hHbB345', 11, 40, 12, 22)

    # neck, shirt, tie
    rect(g, 20, 41, 28, 45, '3'); rect(g, 20, 41, 28, 43, '2')
    rect(g, 3, 46, 44, 55, 'C'); rect(g, 1, 49, 46, 55, 'C')
    run(g, 46, 3, 44, 'v'); rect(g, 0, 53, 47, 55, 'c')
    for i, y in enumerate(range(45, 56)):
        run(g, y, 16 - i // 2, 19 - i // 2, 'c')
        run(g, y, 28 + i // 2, 31 + i // 2, 'c')
    for i, y in enumerate(range(44, 52)):
        run(g, y, 19 + i // 2, 28 - i // 2, 'W')
        put(g, 19 + i // 2, y, 'S'); put(g, 28 - i // 2, y, 'S')
    rect(g, 22, 47, 25, 55, 'T')
    run(g, 47, 22, 25, 'T'); put(g, 23, 48, 't')

    shoulder_rim(g)
    return g

# ---------------------------------------------------------------- MARSH

def marsh(eyes="open", mouth="closed"):
    g = blank()
    backdrop_door(g)

    ellipse(g, 24, 26, 8, 12, 'D')
    ellipse(g, 24, 25, 6, 9, 'f')
    ellipse(g, 24, 22, 4, 3, 'F')

    # hair: side part, thinning, combed. Nothing about it is memorable.
    ellipse(g, 24, 15, 10, 6, 'i')
    run(g, 16, 17, 31, 'f'); run(g, 17, 18, 30, 'f')     # receded forehead
    run(g, 15, 16, 19, 'i'); run(g, 15, 29, 32, 'i')
    run(g, 16, 15, 17, 'i'); run(g, 16, 31, 33, 'i')
    run(g, 13, 23, 30, 'I'); run(g, 14, 25, 31, 'I')     # comb sheen
    for y in range(11, 17): put(g, 21, y, 'j')           # the part

    run(g, 20, 18, 21, 'j'); run(g, 20, 27, 30, 'j')     # brows, sparse

    if eyes == "open":
        run(g, 22, 18, 21, 'e'); run(g, 22, 27, 30, 'e')
        rect(g, 19, 22, 20, 22, 'p'); rect(g, 28, 22, 29, 22, 'p')
        put(g, 19, 22, 'w'); put(g, 28, 22, 'w')
    else:
        run(g, 22, 18, 21, 'j'); run(g, 22, 27, 30, 'j')
    shade(g, 23, 18, 21, 'd', SKIN_M); shade(g, 23, 27, 30, 'd', SKIN_M)

    for y in range(25, 29):                               # nose, small
        shade(g, y, 24, 24, 'f', SKIN_M); shade(g, y, 25, 25, 'd', SKIN_M)
    shade(g, 29, 22, 26, 'd', SKIN_M)
    put(g, 22, 29, 'j'); put(g, 26, 29, 'j')

    # the polite smile, corners lifted
    if mouth == "closed":
        run(g, 33, 21, 27, 'J'); put(g, 20, 32, 'J'); put(g, 28, 32, 'J')
    elif mouth == "mid":
        run(g, 33, 21, 27, 'J'); run(g, 34, 22, 26, 'm')
    else:
        run(g, 32, 22, 26, 'J'); rect(g, 22, 33, 26, 34, 'm'); run(g, 35, 22, 26, 'J')

    shade(g, 31, 19, 20, 'd', SKIN_M); shade(g, 31, 28, 29, 'd', SKIN_M)
    shade(g, 36, 20, 28, 'd', SKIN_M); shade(g, 37, 21, 27, 'd', SKIN_M)
    despeckle(g, SKIN_M)

    rect(g, 20, 39, 28, 44, 'D'); rect(g, 20, 39, 28, 41, 'd')
    rect(g, 3, 45, 44, 55, 'X'); rect(g, 1, 48, 46, 55, 'X')
    rect(g, 0, 53, 47, 55, 'x')
    for i, y in enumerate(range(45, 56)):
        run(g, y, 16 - i // 2, 19 - i // 2, 'x')
        run(g, y, 28 + i // 2, 31 + i // 2, 'x')
    for i, y in enumerate(range(45, 53)):
        run(g, y, 20 + i // 2, 27 - i // 2, 'W')
        put(g, 20 + i // 2, y, 'S'); put(g, 27 - i // 2, y, 'S')
    rect(g, 22, 47, 25, 55, 'z'); put(g, 23, 48, 'Z'); put(g, 23, 51, 'Z')

    # lanyard, and a badge whose photograph is a blank rectangle
    for i in range(7):
        put(g, 18 + i, 46 + i, 'N'); put(g, 30 - i, 46 + i, 'N')
    rect(g, 19, 51, 27, 55, 'M')
    rect(g, 20, 52, 22, 55, 'S')
    run(g, 53, 24, 26, 'x'); run(g, 55, 24, 25, 'x')

    return g

# ---------------------------------------------------------------- ALDUNATE

def aldunate(eyes="open", mouth="closed"):
    g = blank()
    backdrop(g)

    ellipse(g, 24, 18, 9, 10, 'V')
    for y in range(19, 26):
        run(g, y, 14, 16, 'V'); run(g, y, 32, 34, 'V')
    for y in range(24, 32):                               # hair gathered behind
        t = (y - 24) / 8.0
        run(g, y, 13 + int(t * 2), 15, 'V')
        run(g, y, 33, 35 - int(t * 2), 'V')
    ellipse(g, 21, 14, 5, 3, 'K')
    run(g, 12, 24, 29, 'K'); put(g, 26, 12, 'E'); put(g, 27, 13, 'E')

    ellipse(g, 24, 27, 7, 12, 'U')
    ellipse(g, 24, 26, 5, 9, 'P')
    ellipse(g, 24, 23, 3, 3, 'Q')
    run(g, 17, 19, 29, 'U'); run(g, 18, 19, 29, 'P')      # forehead below the hairline
    run(g, 16, 18, 30, 'V')

    # cheekbones: a single turn, high
    shade(g, 28, 17, 18, 'u', SKIN_A); shade(g, 29, 18, 19, 'u', SKIN_A)
    shade(g, 28, 30, 31, 'u', SKIN_A); shade(g, 29, 29, 30, 'u', SKIN_A)
    shade(g, 34, 18, 20, 'u', SKIN_A); shade(g, 34, 28, 30, 'u', SKIN_A)
    shade(g, 36, 20, 28, 'u', SKIN_A); shade(g, 37, 21, 27, 'u', SKIN_A)

    run(g, 20, 18, 22, '6'); run(g, 20, 26, 30, '6')      # brows, level

    if eyes == "open":
        run(g, 22, 18, 21, 'e'); run(g, 23, 18, 21, 'e')
        run(g, 22, 27, 30, 'e'); run(g, 23, 27, 30, 'e')
        rect(g, 19, 22, 20, 23, 'p'); rect(g, 28, 22, 29, 23, 'p')
        put(g, 19, 22, 'w'); put(g, 28, 22, 'w')
        run(g, 21, 18, 21, '6'); run(g, 21, 27, 30, '6')
    else:
        run(g, 22, 18, 21, '6'); run(g, 22, 27, 30, '6')
        run(g, 23, 18, 21, 'u'); run(g, 23, 27, 30, 'u')
    shade(g, 24, 18, 21, 'u', SKIN_A); shade(g, 24, 27, 30, 'u', SKIN_A)

    for y in range(25, 29):
        shade(g, y, 24, 24, 'Q', SKIN_A); shade(g, y, 25, 25, 'u', SKIN_A)
    shade(g, 29, 23, 25, 'u', SKIN_A)
    put(g, 22, 30, '6'); put(g, 26, 30, '6')

    if mouth == "closed":
        run(g, 32, 21, 27, '7'); run(g, 33, 22, 26, '8')
    elif mouth == "mid":
        run(g, 32, 21, 27, '7'); run(g, 33, 22, 26, 'm'); run(g, 34, 23, 25, '8')
    else:
        run(g, 31, 22, 26, '7'); rect(g, 22, 32, 26, 33, 'm'); run(g, 34, 22, 26, '8')

    put(g, 16, 28, 'y'); put(g, 16, 29, 'Y')              # one earring

    despeckle(g, SKIN_A)
    rim_right(g, 'VKEuUPQ', 8, 40, 26, 38)

    rect(g, 21, 39, 27, 44, 'U'); rect(g, 21, 39, 27, 41, 'u')
    rect(g, 5, 45, 42, 55, 'C'); rect(g, 2, 48, 45, 55, 'C')
    rect(g, 0, 53, 47, 55, 'c')
    for i, y in enumerate(range(45, 56)):                 # high, severe collar
        run(g, y, 17 - i // 2, 20 - i // 2, 'c')
        run(g, y, 28 + i // 2, 31 + i // 2, 'c')
    for i, y in enumerate(range(45, 54)):                 # the paper at her throat
        run(g, y, 21 + i // 3, 27 - i // 3, '+')
        put(g, 21 + i // 3, y, '&'); put(g, 27 - i // 3, y, '&')

    shoulder_rim(g)
    return g

# ---------------------------------------------------------------- KIRIAKOU

def kiriakou(eyes="open", mouth="closed", glitch=0):
    """John Kiriakou deepfake — hand-built. CLEAN-SHAVEN. Grey coif with volume,
    swept back. Bulbous Greek nose. Sleek defined jawline, no jowls, no beard.
    Heavy dark rectangular glasses. Deepfake artifacts applied last."""
    g = blank()
    rect(g, 0, 0, W - 1, H - 1, 'k')
    for y in range(0, H, 2):
        run(g, y, 0, W - 1, 'n')
    ellipse(g, 24, 28, 15, 19, ':')

    # ---- head: long, SLEEK. Narrow jaw, no width at the bottom. ----
    ellipse(g, 24, 27, 8, 12, '!')
    ellipse(g, 24, 26, 6, 10, '$')
    ellipse(g, 24, 23, 5, 5, '<')
    # jaw tapers hard: explicit narrowing rows
    for y, half in ((33, 7), (34, 7), (35, 6), (36, 6), (37, 5), (38, 5), (39, 4), (40, 4)):
        for x in range(W):
            if abs(x - 24) <= half:
                if g[y][x] not in ('k', 'n'): pass
                g[y][x] = '!' if abs(x - 24) > half - 2 else '$'
            else:
                if g[y][x] in SKIN_K: g[y][x] = ':'

    # ---- GREY COIF: full, with volume, swept back. Rows 7-16. ----
    ellipse(g, 24, 12, 12, 6, '(')            # the coif mass — grey, wide
    ellipse(g, 24, 11, 10, 4, ']')            # lifted, lighter grey on top
    run(g, 7, 19, 29, '(')                    # crown height
    run(g, 8, 17, 31, '(')
    # darker roots / underside so it isn't a flat grey helmet
    run(g, 15, 15, 33, '/'); run(g, 16, 16, 32, '[')
    for y in range(12, 17):
        run(g, y, 14, 16, '['); run(g, y, 32, 34, '[')
    # sweep: diagonal strands running back from the left part
    for i, x in enumerate(range(17, 32, 2)):
        yy = 9 + (i % 3)
        put(g, x, yy, ']'); put(g, x + 1, yy + 1, '(')
    put(g, 20, 8, ']'); put(g, 26, 8, ']'); put(g, 29, 9, '(')
    # temples: hair comes down slightly at the sides but forehead stays open
    run(g, 17, 14, 16, '('); run(g, 17, 32, 34, '(')
    run(g, 18, 14, 15, '['); run(g, 18, 33, 34, '[')

    # ---- forehead: high, open, lined ----
    for y in range(16, 22):
        run(g, y, 17, 31, '$')
    run(g, 17, 18, 30, '<'); run(g, 18, 18, 30, '<'); run(g, 19, 19, 29, '<')
    run(g, 20, 20, 28, '!')                   # worry line

    # ---- brow: heavy, dark ----
    run(g, 22, 17, 22, '>'); run(g, 21, 18, 21, '>')
    run(g, 22, 26, 31, '>'); run(g, 21, 27, 30, '>')
    put(g, 24, 21, '!')

    # ---- eyes: one per side ----
    if eyes == "open":
        run(g, 25, 18, 21, 'e'); run(g, 25, 27, 30, 'e')
        put(g, 19, 25, 'p'); put(g, 20, 25, 'p')
        put(g, 28, 25, 'p'); put(g, 29, 25, 'p')
        put(g, 19, 25, 'w'); put(g, 28, 25, 'w')
        run(g, 26, 18, 21, 'e'); run(g, 26, 27, 30, 'e')
        shade(g, 27, 18, 21, '!', SKIN_K); shade(g, 27, 27, 30, '!', SKIN_K)
    else:
        run(g, 25, 18, 21, '>'); run(g, 25, 27, 30, '>')
        run(g, 26, 18, 21, '!'); run(g, 26, 27, 30, '!')

    # ---- glasses: two lenses, thin bridge ----
    run(g, 24, 16, 22, '{'); run(g, 28, 16, 22, '{')
    for y in range(25, 28): put(g, 16, y, '{'); put(g, 22, y, '{')
    run(g, 24, 26, 32, '{'); run(g, 28, 26, 32, '{')
    for y in range(25, 28): put(g, 26, y, '{'); put(g, 32, y, '{')
    run(g, 24, 23, 25, '{')
    put(g, 15, 25, '{'); put(g, 33, 25, '{')
    for y in range(25, 28):
        for x in list(range(17, 22)) + list(range(27, 32)):
            if g[y][x] in (' ', ':'): g[y][x] = '}'
    put(g, 17, 27, '|'); put(g, 18, 27, '|')

    # ---- BULBOUS GREEK NOSE: long bridge, wide fleshy ball at the tip ----
    # narrow at the top, widening down, with a rounded bulb at 30-32
    for y in range(26, 30):
        shade(g, y, 23, 23, '<', SKIN_K)      # lit bridge
        shade(g, y, 24, 24, '$', SKIN_K)
        shade(g, y, 25, 25, '!', SKIN_K)      # shadow side
    # the bulb: wider, rounded, catching light on top
    run(g, 30, 21, 27, '$')
    run(g, 31, 21, 27, '$')
    run(g, 30, 22, 26, '<')                   # lit crown of the bulb
    run(g, 31, 23, 25, '<')
    run(g, 32, 21, 27, '!')                   # underside shadow
    put(g, 21, 31, '>'); put(g, 27, 31, '>')  # nostril wings
    put(g, 21, 32, '>'); put(g, 27, 32, '>')
    put(g, 22, 32, '>'); put(g, 26, 32, '>')  # nostrils

    # ---- nasolabial folds, but CLEAN-SHAVEN cheeks ----
    put(g, 20, 33, '>'); put(g, 20, 34, '>')
    put(g, 28, 33, '>'); put(g, 28, 34, '>')

    # ---- mouth: flat, level. No moustache, no beard. ----
    if mouth == "closed":
        run(g, 36, 21, 27, '>'); run(g, 37, 22, 26, '!')
    elif mouth == "mid":
        run(g, 36, 21, 27, '>'); run(g, 37, 22, 26, 'm')
    else:
        run(g, 35, 22, 26, '>'); rect(g, 22, 36, 26, 37, 'm'); run(g, 38, 22, 26, '!')
    shade(g, 35, 21, 27, '$', SKIN_K)          # lit upper lip
    shade(g, 39, 22, 26, '!', SKIN_K)          # chin crease

    # ---- clean sleek jaw shading (definition without a beard) ----
    for y in range(33, 40):
        xs = [x for x in range(14, 34) if g[y][x] in SKIN_K]
        if xs:
            for x in (xs[0], xs[-1]):
                g[y][x] = '!'                  # jaw edge shadow only
    despeckle(g, SKIN_K)

    # ---- collar ----
    rect(g, 21, 40, 27, 46, '$'); rect(g, 21, 40, 27, 43, '!')
    rect(g, 3, 47, 44, 55, 'x'); rect(g, 1, 50, 46, 55, 'x')
    rect(g, 0, 53, 47, 55, 'k')
    run(g, 47, 15, 32, 'X'); run(g, 48, 14, 33, 'X')
    put(g, 24, 49, '{')

    # ---- deepfake artifacts, last ----
    MASS = SKIN_K | set('/[(]{}|>')
    for y in range(7, 46):
        for x in range(W):
            if g[y][x] in MASS:
                if x > 0 and g[y][x-1] == ':':
                    g[y][x-1] = '^' if (x + y) % 2 else '?'
                break
        for x in range(W-1, -1, -1):
            if g[y][x] in MASS:
                if x < W-1 and g[y][x+1] == ':':
                    g[y][x+1] = '~' if (x + y) % 3 else ';'
                break
    if glitch:
        ty = 24 + int(glitch * 14)
        if 0 <= ty < H:
            row = g[ty][:]
            g[ty] = ([':'] * 2) + row[:W - 2]
            for x in range(W):
                if g[ty][x] in SKIN_K: g[ty][x] = '~' if x % 2 else ';'
    for y in range(0, H, 4):
        for x in range(W):
            if g[y][x] in '$<':
                g[y][x] = {'$':'!', '<':'$'}[g[y][x]]

    return g


def will(eyes="open", mouth="closed"):
    """Will Brown, hand-built: long face, ash-brown hair parted centre and falling
    in two curtains past the shoulders, thin wire glasses, light beard, black tee.
    Reuses Marsh skin (dDfF/j/J) + brown hair (123)."""
    g = blank()
    backdrop(g)

    ellipse(g, 24, 12, 11, 7, '1')
    ellipse(g, 24, 11, 9, 5, '2')
    run(g, 6, 20, 28, '1'); run(g, 7, 18, 30, '1')
    for y in range(7, 16):
        put(g, 24, y, '2'); put(g, 23, y, '1'); put(g, 25, y, '1')
    put(g, 24, 8, '3')
    for y in range(10, 53):
        t = (y - 10) / 43.0
        lx0 = 9 + int(t * 2); lx1 = 15 - int(t * 1)
        run(g, y, lx0, lx1, '1'); put(g, lx0 + 1, y, '2')
        rx1 = 38 - int(t * 2); rx0 = 32 + int(t * 1)
        run(g, y, rx0, rx1, '1'); put(g, rx1 - 1, y, '2')
    for y in range(14, 46, 6):
        put(g, 11, y, '3'); put(g, 36, y + 2, '3')

    ellipse(g, 24, 30, 8, 14, 'D')
    ellipse(g, 24, 29, 6, 11, 'f')
    ellipse(g, 24, 25, 4, 5, 'F')
    run(g, 16, 18, 30, 'D'); run(g, 17, 17, 31, 'D')
    run(g, 17, 19, 29, 'f'); run(g, 18, 20, 28, 'f')
    run(g, 15, 16, 32, '1'); run(g, 16, 15, 17, '1'); run(g, 16, 31, 33, '1')
    put(g, 24, 15, '2')

    run(g, 20, 17, 21, 'j'); run(g, 20, 27, 31, 'j')
    if eyes == "open":
        run(g, 22, 17, 21, 'e'); run(g, 22, 27, 31, 'e')
        rect(g, 18, 22, 19, 22, 'p'); rect(g, 29, 22, 30, 22, 'p')
        put(g, 18, 22, 'w'); put(g, 29, 22, 'w')
        run(g, 21, 17, 21, 'j'); run(g, 21, 27, 31, 'j')
    else:
        run(g, 22, 17, 21, 'j'); run(g, 22, 27, 31, 'j')
    shade(g, 23, 17, 20, 'd', SKIN_M); shade(g, 23, 28, 31, 'd', SKIN_M)

    for cx in (19, 29):
        run(g, 21, cx-2, cx+2, 'j'); run(g, 24, cx-2, cx+2, 'j')
        for yy in range(22, 24): put(g, cx-3, yy, 'j'); put(g, cx+3, yy, 'j')
    run(g, 22, 22, 26, 'j')
    put(g, 15, 22, 'j'); put(g, 33, 22, 'j')

    for y in range(24, 30):
        shade(g, y, 24, 24, 'f', SKIN_M); shade(g, y, 25, 25, 'd', SKIN_M)
    shade(g, 30, 22, 26, 'd', SKIN_M)
    put(g, 22, 30, 'j'); put(g, 26, 30, 'j')

    if mouth == "closed":
        run(g, 34, 21, 27, 'J'); put(g, 20, 33, 'J'); put(g, 28, 33, 'J')
    elif mouth == "mid":
        run(g, 34, 21, 27, 'J'); run(g, 35, 22, 26, 'm')
    else:
        run(g, 33, 22, 26, 'J'); rect(g, 22, 34, 26, 35, 'm'); run(g, 36, 22, 26, 'J')

    for y in range(31, 42):
        xs = [x for x in range(14, 34) if g[y][x] in SKIN_M]
        if xs:
            for x in (xs[0], xs[0]+1, xs[-1], xs[-1]-1):
                if 0 <= x < W and g[y][x] in SKIN_M: g[y][x] = 'j'
    run(g, 32, 21, 27, 'j')
    run(g, 37, 22, 26, 'j'); run(g, 38, 23, 25, 'j')
    put(g, 24, 33, 'j')
    despeckle(g, SKIN_M)

    rect(g, 3, 46, 44, 55, 'x'); rect(g, 1, 50, 46, 55, 'x')
    rect(g, 0, 53, 47, 55, 'k')
    run(g, 46, 16, 31, 'j'); run(g, 47, 15, 32, 'j')
    for x in range(18, 30, 2): put(g, x, 53, 'S')

    shoulder_rim(g)
    return g


def model(eyes="open", mouth="closed", ghost=False):
    g = blank()
    rect(g, 0, 0, W - 1, H - 1, 'k')
    for y in range(0, H, 2):
        run(g, y, 0, W - 1, 'n')

    rect(g, 6, 8, 41, 47, 'n'); rect(g, 7, 9, 40, 46, 'k')
    run(g, 8, 6, 41, 's'); run(g, 47, 6, 41, 's')
    rect(g, 6, 8, 6, 47, 's'); rect(g, 41, 8, 41, 47, 's')

    if ghost:
        ellipse(g, 24, 27, 7, 10, 'n')
        run(g, 23, 18, 21, 's'); run(g, 23, 27, 30, 's')
        run(g, 33, 21, 27, 's')

    rect(g, 11, 20, 13, 22, 'y')
    if eyes == "closed":
        rect(g, 11, 20, 13, 22, 'k')
    run(g, 21, 16, 30, 's')

    if mouth == "closed":
        run(g, 28, 11, 22, 's')
    elif mouth == "mid":
        run(g, 28, 11, 27, 's'); run(g, 30, 11, 18, 's')
    else:
        run(g, 28, 11, 33, 'y'); run(g, 30, 11, 24, 's'); run(g, 32, 11, 29, 's')

    return g

# ---------------------------------------------------------------- render + export

def to_img(g, scale=8):
    im = Image.new("RGB", (W * scale, H * scale), (5, 6, 9))
    px = im.load()
    for y in range(H):
        for x in range(W):
            c = PALETTE.get(g[y][x])
            if not c: continue
            rgb = (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16))
            for dy in range(scale):
                for dx in range(scale):
                    px[x * scale + dx, y * scale + dy] = rgb
    return im

def grid_to_rows(g):
    return ["".join(r) for r in g]

def diff_patch(base, var):
    cells = [(x, y) for y in range(H) for x in range(W) if base[y][x] != var[y][x]]
    if not cells: return None
    xs, ys = [c[0] for c in cells], [c[1] for c in cells]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return {"x": x0, "y": y0, "rows": ["".join(var[y][x0:x1 + 1]) for y in range(y0, y1 + 1)]}

def export():
    out = {"w": W, "h": H, "pal": PALETTE, "sprites": {}}
    for name, fn in (("VOIDT", voidt), ("LAMPORT", lamport), ("MODEL", model),
                     ("MARSH", marsh), ("ALDUNATE", aldunate), ("WILL", will)):
        base = fn("open", "closed")
        out["sprites"][name] = {
            "base": grid_to_rows(base),
            "eyesClosed": diff_patch(base, fn("closed", "closed")),
            "mouthMid":   diff_patch(base, fn("open", "mid")),
            "mouthOpen":  diff_patch(base, fn("open", "open")),
        }
    # KIRIAKOU hand-built with deepfake artifacts (glitch on speech).
    _kb = kiriakou("open", "closed")
    out["sprites"]["KIRIAKOU"] = {
        "base": grid_to_rows(_kb),
        "eyesClosed": diff_patch(_kb, kiriakou("closed", "closed")),
        "mouthMid":   diff_patch(_kb, kiriakou("open", "mid", glitch=0.3)),
        "mouthOpen":  diff_patch(_kb, kiriakou("open", "open", glitch=0.6)),
    }
    # LEVIN still stored roto (WIP).
    import json as _json, os as _os
    _d = _os.path.dirname(__file__)
    with open(_os.path.join(_d, "_levin_payload.json")) as _f:
        out["sprites"]["LEVIN"] = _json.load(_f)
    out["sprites"]["MODEL"]["ghost"] = diff_patch(
        model("open", "closed"), model("open", "closed", ghost=True))
    return out

if __name__ == "__main__":
    cast = [voidt(), lamport(), model(), marsh(), aldunate(), kiriakou()]
    sheet = Image.new("RGB", (W * 8 * 6 + 70, H * 8 + 20), (5, 6, 9))
    for i, g in enumerate(cast):
        sheet.paste(to_img(g), (10 + i * (W * 8 + 10), 10))
    sheet.save("sheet.png")

    strip = Image.new("RGB", (W * 6 * 4 + 40, H * 6 + 20), (5, 6, 9))
    for i, g in enumerate([kiriakou("closed"), kiriakou("open", "mid", glitch=0.3),
                           kiriakou("open", "open", glitch=0.6), kiriakou("open", "closed")]):
        strip.paste(to_img(g, 6), (10 + i * (W * 6 + 6), 10))
    strip.save("variants.png")

    small = Image.new("RGB", (W * 2 * 6 + 70, H * 2 + 20), (12, 15, 22))
    for i, g in enumerate(cast):
        small.paste(to_img(g, 2), (10 + i * (W * 2 + 10), 10))
    small.resize((small.width * 3, small.height * 3), Image.NEAREST).save("actualsize.png")
    print("ok")
