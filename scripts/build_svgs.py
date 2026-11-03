#!/usr/bin/env python3
"""Draws the animated SVGs for the GDG-TIET org profile README.

    python scripts/build_svgs.py

writes profile/assets/<name>-dark.svg and <name>-light.svg. Change the CONFIG
block, rerun, and commit the new files. The Projects card lists the org's
public repos from the GitHub API; set GITHUB_TOKEN to skip the anonymous rate
limit, e.g.  GITHUB_TOKEN=$(gh auth token) python scripts/build_svgs.py

Each card plays its intro once when the page opens. After that only a few
single-element effects loop (cursors, a slow re-scan, glints); IDLE = False
turns those off too.
"""

import base64
import json
import math
import os
import random
import urllib.request
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

# ── CONFIG ──────────────────────────────────────────────────────────────────

ORG = "GDG-TIET"
NAME = "Google Developer Groups"
CAMPUS = "Thapar Institute of Engineering & Technology"
CITY = "Patiala, Punjab"
FORMERLY = ["DSC Thapar", "GDSC TIET"]

# Follower counts as read off the pages; update them now and then.
INSTAGRAM = {"handle": "@gdg.tiet", "followers": 5560}
LINKEDIN = {"handle": "Google Developer Groups TIET", "followers": 1674}
COUNTED = "nov '26"

# (icon, title, tags). Icons: dev, aiml, iot, design, management, marketing.
# The six areas are the ones the chapter's LinkedIn About lists.
DOMAINS = [
    ("dev", "DEV", "web · app · open source"),
    ("aiml", "AI / ML", "models · data · research"),
    ("iot", "IoT", "hardware · sensors · edge"),
    ("design", "DESIGN", "ui · ux · visual identity"),
    ("management", "MANAGEMENT", "events · operations · people"),
    ("marketing", "MARKETING", "content · social · outreach"),
]

# Event board rows as (name, season), from the Instagram highlights.
# Names up to 16 characters, seasons up to 3.
EVENTS = [
    ("DEVFEST", "'26"),
    ("ORIENTATION", "'26"),
    ("BUILDSPACE", "'26"),
    ("BTC", "'26"),
    ("GUEST SESSIONS", "--"),
    ("SATURNALIA", "'25"),
]

# Core team badges. Each is None (drawn as a classified badge) or a dict with
# name, role and github; with github set, the avatar is fetched and embedded.
TEAM = [None, None, None, None]
TEAM_LABEL = "CORE '26"

# Section headers in README order: header-<name>.svg, spaces become dashes.
SECTIONS = ["about", "domains", "events", "projects", "core team", "connect"]

# Light looping effects after the intros: cursors, a slow re-scan, glints.
IDLE = True

# ── DRAWING ─────────────────────────────────────────────────────────────────

OUT = Path(__file__).resolve().parent.parent / "profile" / "assets"

MONO = "ConsolasFallback,Consolas,'SF Mono',Menlo,'DejaVu Sans Mono','Courier New',monospace"
SANS = "'Segoe UI',Helvetica,Arial,sans-serif"
CHAR = 0.6    # monospace advance as a fraction of font size
FRAME = 0.05  # seconds each scramble frame stays up
GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&*+=<>/?"
INK = "#0d1117"  # dark text on bright accent fills, in both themes

THEMES = {
    "dark": {
        "bg": "#0d1117", "panel": "#161b22", "border": "#30363d",
        "head": "#f0f6fc", "text": "#c9d1d9", "muted": "#8b949e", "dim": "#484f58",
        "cell": "#1a1f27", "skel": "#262c36", "hl": "#ffffff",
        "tile": "#1c2128", "split": "#05070a",
        "accents": ["#4285F4", "#EA4335", "#FBBC04", "#34A853"],
        "accent_text": ["#79a6ff", "#ff7b72", "#FBBC04", "#3fb950"],
        "syn": {"kw": "#ff7b72", "cls": "#f2cc60", "str": "#7ee787", "attr": "#79a6ff",
                "fn": "#d2a8ff", "com": "#8b949e", "pun": "#c9d1d9"},
    },
    "light": {
        "bg": "#ffffff", "panel": "#f6f8fa", "border": "#d0d7de",
        "head": "#1f2328", "text": "#1f2328", "muted": "#59636e", "dim": "#8c959f",
        "cell": "#eceff3", "skel": "#dfe4ea", "hl": "#ffffff",
        "tile": "#24292f", "split": "#0d1117",
        "accents": ["#4285F4", "#EA4335", "#FBBC04", "#34A853"],
        "accent_text": ["#1a73e8", "#d93025", "#b06000", "#188038"],
        "syn": {"kw": "#d93025", "cls": "#b06000", "str": "#188038", "attr": "#1a73e8",
                "fn": "#8250df", "com": "#6e7781", "pun": "#1f2328"},
    },
}
BLUE, RED, YELLOW, GREEN = range(4)

BASE_CSS = f"""@font-face{{src:local('Consolas'),local('Consolas Bold');font-family:'ConsolasFallback';font-display:swap;size-adjust:109%}}
text,tspan{{white-space:pre}}
.fx{{transform-box:fill-box;transform-origin:0 50%}}
.in{{opacity:0;animation:in .4s ease-out both}}
.bar{{transform:scaleX(0);animation:grow .45s ease-out both}}
.frame{{stroke-dasharray:1;stroke-dashoffset:1;fill-opacity:0;animation:draw .9s ease-out both,fill .5s ease-out both}}
.dr{{stroke-dasharray:1;stroke-dashoffset:1;animation:draw .6s ease-out both}}
.pop{{opacity:0;transform-box:fill-box;transform-origin:50% 50%;animation:pop .5s cubic-bezier(.3,1.5,.5,1) both}}
.mv{{opacity:0;animation:mv .55s cubic-bezier(.2,.9,.3,1) both}}
.gy{{transform-box:fill-box;transform-origin:50% 100%;animation:gy .5s ease-out both}}
.roll{{animation:roll 1.5s cubic-bezier(.2,.75,.25,1) both}}
.fr{{opacity:0;animation:fr {FRAME}s step-end}}
.fl,.cur{{opacity:0;animation:in .01s both}}
{".blink{animation:blink 1.1s step-end infinite}" if IDLE else ""}
@keyframes in{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes out{{to{{opacity:0}}}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:none}}}}
@keyframes draw{{to{{stroke-dashoffset:0}}}}
@keyframes fill{{to{{fill-opacity:1}}}}
@keyframes pop{{from{{opacity:0;transform:scale(.3)}}to{{opacity:1;transform:none}}}}
@keyframes mv{{from{{opacity:0;transform:translate(var(--mx,0px),var(--my,0px))}}to{{opacity:1;transform:none}}}}
@keyframes gy{{from{{transform:scaleY(0)}}to{{transform:none}}}}
@keyframes roll{{to{{transform:translateY(var(--to))}}}}
@keyframes fr{{0%,100%{{opacity:1}}}}
@keyframes blink{{50%{{opacity:0}}}}"""

REDUCED_CSS = """@media (prefers-reduced-motion:reduce){
*{animation:none!important}
.in,.px,.fl,.cur,.pop,.mv,.s2,.ag,.stamp,.sbar{opacity:1}
.bar,.tick,.seg,.gy,.pop,.mv,.px,.stamp,.sbar{transform:none}
.frame{stroke-dashoffset:0;fill-opacity:1}
.draw,.dr{stroke-dashoffset:0}
.roll{transform:translateY(var(--to))}
.beam,.tbeam,.vbeam,.glint,.s1,.fr,.idle,.sweep,.gr,.gb,.shine{display:none}
}"""

# 5x7 LED lettering; letters sit one blank column apart.
PIXELS = {
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
}

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Java": "#b07219",
    "Kotlin": "#A97BFF", "Dart": "#00B4AB", "C++": "#f34b7d", "C": "#555555", "HTML": "#e34c26",
    "CSS": "#563d7c", "Jupyter Notebook": "#DA5B0B", "Go": "#00ADD8", "Rust": "#dea584",
    "Swift": "#F05138", "Shell": "#89e051",
}


def esc(s):
    return escape(str(s), {'"': "&quot;"})


def st(*delays, **props):
    """A style attribute carrying animation delays and CSS custom properties."""
    parts = []
    if delays:
        parts.append("animation-delay:" + ",".join(f"{d:.3f}s" for d in delays))
    parts += [f"--{k}:{v}" for k, v in props.items()]
    return f' style="{";".join(parts)}"'


def svg(w, h, label, css, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="{MONO}" role="img" aria-label="{esc(label)}">\n'
        f"<style>\n{BASE_CSS}\n{css.strip()}\n{REDUCED_CSS}\n</style>\n{body}</svg>\n"
    )


def kfmt(n):
    """5560 -> 5.5k, rounding down so it never overstates."""
    return f"{math.floor(n / 100) / 10:g}k" if n >= 1000 else str(n)


def bar(t, x, y, w, h, delay, fill=None):
    return (
        f'<rect class="bar fx" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" '
        f'rx="{min(h / 2, 4):.1f}" fill="{fill or t["skel"]}"{st(delay)}/>\n'
    )


def frame_rect(t, x, y, w, h, d, rx=12, fill=None):
    return (
        f'<rect class="frame" x="{x + .5:.1f}" y="{y + .5:.1f}" width="{w - 1:.1f}" height="{h - 1:.1f}" rx="{rx}" '
        f'fill="{fill or t["panel"]}" stroke="{t["border"]}" pathLength="1"{st(d, d + .3)}/>\n'
    )


def typed_clip(uid, x, y, h, n, cw, begin, dur, extra=24):
    """A clipPath whose width steps one character at a time, so text inside it types out."""
    n = max(n, 1)
    widths = [k * cw for k in range(n + 1)]
    widths[-1] += extra  # a wide fallback font never clips the last letter
    vals = ";".join(f"{w:.1f}" for w in widths)
    keys = ";".join(f"{k / n:.4f}" for k in range(n + 1))
    return (
        f'<clipPath id="{uid}"><rect x="{x - 1:.1f}" y="{y:.1f}" width="0" height="{h}">'
        f'<animate attributeName="width" values="{vals}" keyTimes="{keys}" calcMode="discrete" '
        f'begin="{begin:.3f}s" dur="{dur:.3f}s" fill="freeze"/></rect></clipPath>'
    )


def ride_cursor(x, y, h, n, cw, begin, dur, color, hide_at, width=None):
    """A block cursor that rides the typing edge, then disappears."""
    n = max(n, 1)
    xs = ";".join(f"{x + k * cw:.1f}" for k in range(n + 1))
    keys = ";".join(f"{k / n:.4f}" for k in range(n + 1))
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width or cw * .9:.1f}" height="{h}" fill="{color}" opacity="0">'
        f'<animate attributeName="x" values="{xs}" keyTimes="{keys}" calcMode="discrete" begin="{begin:.3f}s" dur="{dur:.3f}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="1" begin="{begin:.3f}s"/>'
        f'<set attributeName="opacity" to="0" begin="{hide_at:.3f}s" fill="freeze"/></rect>'
    )


def typewriter(lines, x, y0, lh, fs, begin, uid, cursor, speed=.011, gap=.08):
    """Types lines of (text, color) spans one after another.

    Returns (defs, body, spans) where spans[i] is (start, end) for line i.
    """
    cw = fs * CHAR
    defs, body, spans = [], [], []
    t0 = begin
    for i, line in enumerate(lines):
        y = y0 + i * lh
        n = sum(len(s) for s, _ in line)
        if n == 0:
            spans.append((t0, t0))
            continue
        dur = max(.08, n * speed)
        defs.append(typed_clip(f"{uid}{i}", x, y - fs, fs + 6, n, cw, t0, dur))
        tsp = "".join(f'<tspan fill="{c}">{esc(s)}</tspan>' for s, c in line)
        body.append(f'<text x="{x}" y="{y}" font-size="{fs}" clip-path="url(#{uid}{i})">{tsp}</text>')
        body.append(ride_cursor(x, y - fs + 2, fs + 2, n, cw, t0, dur, cursor, t0 + dur + gap * .8))
        spans.append((t0, t0 + dur))
        t0 += dur + gap
    return defs, body, spans


def end_cursor(x, y, fs, color, at):
    cw = fs * CHAR
    return f'<g class="cur"{st(at)}><rect class="blink" x="{x:.1f}" y="{y - fs + 2:.1f}" width="{cw * .9:.1f}" height="{fs + 2}" fill="{color}"{st(at)}/></g>'


def scramble(text, frames, seed, keep_spaces=True, glyphs=GLYPHS):
    """Frames that settle left to right out of random glyphs; the last frame is the text."""
    rng = random.Random(seed)
    out, n = [], len(text)
    for f in range(frames - 1):
        settled = round(n * f / (frames - 1))
        out.append("".join(
            c if i < settled or (keep_spaces and c == " ") else rng.choice(glyphs)
            for i, c in enumerate(text)
        ))
    out.append(text)
    return out


def frames_svg(frames, attrs, begin, inner=None):
    """Stack frames so each shows for one FRAME, then the last one stays.

    inner(frame_text) can return tspan markup to colour parts of a frame."""
    parts = []
    for k, s in enumerate(frames):
        cls = "fl" if k == len(frames) - 1 else "fr"
        content = inner(s) if inner else esc(s)
        parts.append(f'<text class="{cls}" {attrs}{st(begin + k * FRAME)}>{content}</text>')
    return "".join(parts) + "\n"


def word_size(word, cell):
    pad = max(2.0, round(cell * 0.18, 1))
    return (len(word) * 6 - 1) * cell - pad, 7 * cell - pad


def pixel_word(word, x0, y0, cell, colors, unlit, timing, rng=None, spread=0):
    """LED lettering: a dim cell for every slot, and lit cells that animate in.

    timing(x, y) returns the lit cell's animation delays. With spread set, each
    lit cell flies in from a random offset up to that many pixels away."""
    pad = max(2.0, round(cell * 0.18, 1))
    s = cell - pad
    dim, lit = [], []
    for i, ch in enumerate(word):
        for r, row in enumerate(PIXELS[ch]):
            for c, on in enumerate(row):
                x, y = x0 + (i * 6 + c) * cell, y0 + r * cell
                rect = f'x="{x:.1f}" y="{y:.1f}" width="{s:.1f}" height="{s:.1f}" rx="{s * .22:.1f}"'
                dim.append(f'<rect {rect} fill="{unlit}"/>')
                if on == "#":
                    props = {}
                    if spread:
                        props = {"dx": f"{rng.uniform(-spread, spread):.0f}px", "dy": f"{rng.uniform(-spread, spread) * .6:.0f}px"}
                    lit.append(f'<rect class="px" {rect} fill="{colors[i % len(colors)]}"{st(*timing(x + s / 2, y + s / 2), **props)}/>')
    return "\n".join(dim + lit) + "\n"


def odometer(x, by, value, fs, color, delay, uid, defs):
    """Digits roll up into place; commas and other characters fade in."""
    cw, lh = fs * CHAR, round(fs * 1.3)
    out = []
    for j, ch in enumerate(value):
        cx = x + j * cw
        if not ch.isdigit():
            out.append(f'<text class="in" x="{cx:.1f}" y="{by}" font-size="{fs}" font-weight="bold" fill="{color}"{st(delay + .9)}>{esc(ch)}</text>')
            continue
        defs.append(f'<clipPath id="{uid}{j}"><rect x="{cx - 2:.1f}" y="{by - fs:.1f}" width="{cw + 4:.1f}" height="{lh}"/></clipPath>')
        digits = "".join(
            f'<text x="{cx:.1f}" y="{by + k * lh}" font-size="{fs}" font-weight="bold" fill="{color}">{k % 10}</text>'
            for k in range(20)
        )
        # two runs of 0-9 stacked; the column stops on the digit in the second run
        out.append(f'<g clip-path="url(#{uid}{j})"><g class="roll"{st(delay + j * .07, to=f"-{(10 + int(ch)) * lh}px")}>{digits}</g></g>')
    return "".join(out) + "\n", len(value) * cw


def chrome(t, w, title, top=36):
    """Window title bar: three dots and a centred title."""
    acc = t["accents"]
    dots = "".join(f'<circle cx="{22 + i * 20}" cy="{top / 2}" r="6" fill="{c}"/>' for i, c in enumerate((acc[RED], acc[YELLOW], acc[GREEN])))
    return (
        f'<rect width="{w}" height="{top}" fill="{t["panel"]}"/><rect y="{top}" width="{w}" height="1" fill="{t["border"]}"/>{dots}'
        f'<text x="{w / 2}" y="{top / 2 + 4.5}" text-anchor="middle" font-size="12" fill="{t["muted"]}">{esc(title)}</text>\n'
    )


# ── HERO ────────────────────────────────────────────────────────────────────

def hero(t):
    W, H, TOP, SB = 1000, 540, 36, 32
    BOT = H - SB
    acc, act = t["accents"], t["accent_text"]
    rng = random.Random("hero")
    SCAN0, SCAN = 1.05, 1.35   # the lock-on scan line
    locked = SCAN0 + SCAN
    RX, RY, RR = 900, 438, 56  # radar
    SPIN0, SPIN = 1.0, 1.2
    color = {"dim": t["dim"], "text": t["text"], "head": t["head"], "muted": t["muted"],
             "blue": act[BLUE], "green": act[GREEN], "yellow": act[YELLOW]}

    def timing(x, y):  # fly in, then flash as the scan line crosses
        return .1 + rng.random() * .5 + (x - 60) / 440 * .3, SCAN0 + (y - TOP) / (BOT - TOP) * SCAN

    # terminal log
    X, fs = 556, 14
    cw = fs * CHAR
    ig, li = kfmt(INSTAGRAM["followers"]), kfmt(LINKEDIN["followers"])
    lineage = " → ".join([n.split()[0].lower() for n in FORMERLY] + ["gdg"])
    rows = [("link", CITY.lower()), ("handshake", "google for developers"), ("lineage", lineage),
            ("mount", f"/domains · {len(DOMAINS)} found"), ("signal", f"ig {ig} · in {li}")]
    log = [[("$ ", color["green"]), (f"ssh guest@{ORG.lower()}", color["head"])]]
    for key, val in rows:
        base = 2 + 11 + len(val)
        log.append([("› ", color["dim"]), (f"{key:<11}", color["blue"]), (val, color["text"]), (" " + "." * max(2, 36 - base), color["dim"])])
    log.append([("› ", color["dim"]), (f"{'scan':<11}", color["blue"])])
    tdefs, tbody, spans = typewriter(log, X, 86, 25, fs, .45, "l", t["text"])
    scan_row = spans[-1][1]
    granted = scan_row + .75
    welcome = granted + .55
    bar_up = granted + .25

    blips = []
    for k in range(len(DOMAINS)):
        a = (k + rng.uniform(.15, .85)) * 360 / len(DOMAINS)
        blips.append((a, rng.uniform(18, RR - 8), acc[k % 4], SPIN0 + a / 360 * SPIN))
    found = max(b[3] for b in blips) + .2

    css = f"""
.px{{opacity:0;transform-box:fill-box;transform-origin:50% 50%;animation:fly .9s cubic-bezier(.16,.84,.24,1) both,flash .5s ease-out both}}
@keyframes fly{{0%{{opacity:0;transform:translate(var(--dx),var(--dy)) scale(.15) rotate(120deg)}}45%{{opacity:1}}100%{{opacity:1;transform:none}}}}
@keyframes flash{{30%{{fill:{t['hl']}}}}}
.beam{{opacity:0;animation:sweep {SCAN}s linear {SCAN0}s both}}
@keyframes sweep{{0%{{opacity:0;transform:none}}6%{{opacity:1}}92%{{opacity:1}}100%{{opacity:0;transform:translateY({BOT - TOP}px)}}}}
.idle{{opacity:0;{f"animation:idle 10s linear {welcome + 4:.2f}s infinite" if IDLE else "display:none"}}}
@keyframes idle{{0%{{opacity:0;transform:none}}2%{{opacity:1}}16%{{opacity:1}}18%,100%{{opacity:0;transform:translateY({BOT - TOP}px)}}}}
.s1{{animation:out .2s ease-out {locked:.2f}s both}}
.s2{{opacity:0;animation:in .3s ease-out {locked:.2f}s both}}
.sweep{{opacity:0;transform-box:view-box;transform-origin:{RX}px {RY}px;animation:in .2s {SPIN0}s both,spin {SPIN}s linear {SPIN0}s 2 both,out .5s ease-out {SPIN0 + 2 * SPIN:.2f}s forwards}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.ping{{opacity:0;transform-box:fill-box;transform-origin:50% 50%;animation:ping 1s ease-out forwards}}
@keyframes ping{{0%{{opacity:.9;transform:scale(.3)}}100%{{opacity:0;transform:scale(2.8)}}}}
.ag{{opacity:0;animation:flick .6s linear both}}
@keyframes flick{{0%{{opacity:0}}8%{{opacity:1}}16%{{opacity:.15}}26%{{opacity:1}}38%{{opacity:.4}}48%,100%{{opacity:1}}}}
.gr,.gb{{opacity:0;animation:jit .55s steps(1) forwards}}
@keyframes jit{{0%{{opacity:.85;transform:translate(var(--jx),0)}}20%{{transform:translate(calc(var(--jx) * -.6),1px)}}40%{{transform:translate(calc(var(--jx) * .8),-1px)}}60%{{transform:translate(calc(var(--jx) * -.3),0)}}80%{{opacity:.6;transform:translate(calc(var(--jx) * .2),0)}}100%{{opacity:0;transform:none}}}}
.sbar{{opacity:0;animation:up .5s cubic-bezier(.2,.8,.2,1) {bar_up:.2f}s both}}
@keyframes up{{from{{opacity:0;transform:translateY({SB}px)}}to{{opacity:1;transform:none}}}}
"""
    stops = "".join(f'<stop offset="{k / 4}" stop-color="{c}"/><stop offset="{(k + 1) / 4}" stop-color="{c}"/>' for k, c in enumerate(acc))
    bx, bw = X + 13 * cw, 220
    defs = [
        "<defs>",
        f'<clipPath id="card"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14"/></clipPath>',
        f'<clipPath id="body"><rect y="{TOP + 1}" width="{W}" height="{BOT - TOP - 1}"/></clipPath>',
        f'<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{acc[BLUE]}" stop-opacity="0"/>'
        f'<stop offset=".75" stop-color="{acc[BLUE]}" stop-opacity=".10"/><stop offset="1" stop-color="{acc[BLUE]}" stop-opacity=".34"/></linearGradient>',
        f'<linearGradient id="prog" gradientUnits="userSpaceOnUse" x1="{bx:.1f}" y1="0" x2="{bx + bw:.1f}" y2="0">{stops}</linearGradient>',
        f'<pattern id="crt" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="{t["head"]}" fill-opacity=".03"/></pattern>',
        *tdefs,
        "</defs>",
    ]
    b = [
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["bg"]}"/>',
        f'<g clip-path="url(#card)">{chrome(t, W, f"guest@{ORG.lower()}: ~ — boot")}'
        f'<rect y="{TOP + 1}" width="{W}" height="{BOT - TOP}" fill="url(#crt)"/></g>',
    ]

    # left: LED lettering inside a viewfinder that locks on
    L, T, R, B, k = 32, 62, 508, 404, 20
    cx = (L + R) / 2
    corners = [
        (f"M{L},{T + k}V{T}H{L + k}", "-14px", "-14px"), (f"M{R - k},{T}H{R}V{T + k}", "14px", "-14px"),
        (f"M{L},{B - k}V{B}H{L + k}", "-14px", "14px"), (f"M{R - k},{B}H{R}V{B - k}", "14px", "14px"),
    ]
    for d, mx, my in corners:
        b.append(f'<path class="mv" d="{d}" fill="none" stroke="{t["muted"]}" stroke-width="2" stroke-linecap="round"{st(.05, mx=mx, my=my)}/>')
        b.append(f'<path class="in" d="{d}" fill="none" stroke="{act[GREEN]}" stroke-width="2.5" stroke-linecap="round"{st(locked)}/>')
    b.append(f'<text class="s1" x="{L}" y="54" font-size="10" letter-spacing="2" fill="{t["muted"]}">+ ACQUIRING TARGET ...</text>')
    b.append(f'<text class="s2" x="{L}" y="54" font-size="10" letter-spacing="2" fill="{act[GREEN]}">● TARGET LOCKED: {ORG}</text>')
    gw, _ = word_size("GDG", 24)
    b.append(pixel_word("GDG", cx - gw / 2, 84, 24, [acc[BLUE], acc[RED], acc[YELLOW]], t["cell"], timing, rng, 160))
    tw, _ = word_size("TIET", 17)
    b.append(pixel_word("TIET", cx - tw / 2, 268, 17, [acc[GREEN]], t["cell"], timing, rng, 160))
    b.append(frames_svg(scramble(NAME.upper(), 16, "tag1"), f'x="{cx}" y="442" text-anchor="middle" font-size="16" font-weight="bold" letter-spacing="5" fill="{t["head"]}"', locked - .1))
    b.append(frames_svg(scramble(CAMPUS.upper(), 16, "tag2"), f'x="{cx}" y="466" text-anchor="middle" font-size="11" letter-spacing="1.5" fill="{t["muted"]}"', locked + .15))
    b.append(f'<line x1="532" y1="62" x2="532" y2="{BOT - 20}" stroke="{t["border"]}" stroke-dasharray="2 5"/>')

    # right: terminal
    b += tbody
    for i, (s0, s1) in enumerate(spans[1:-1], start=1):
        b.append(f'<text class="pop" x="{X + 38 * cw:.1f}" y="{86 + i * 25}" font-size="{fs}" font-weight="bold" fill="{act[GREEN]}"{st(s1 + .06)}>[ OK ]</text>')
    sy = 86 + (len(log) - 1) * 25
    b.append(f'<rect x="{bx:.1f}" y="{sy - 9}" width="{bw}" height="8" rx="4" fill="{t["cell"]}"/>')
    b.append(f'<rect x="{bx:.1f}" y="{sy - 9}" width="0" height="8" rx="4" fill="url(#prog)"><animate attributeName="width" from="0" to="{bw}" begin="{scan_row:.2f}s" dur=".6s" fill="freeze"/></rect>')
    b.append(f'<text class="in" x="{bx + bw + 12:.1f}" y="{sy}" font-size="{fs}" fill="{t["muted"]}"{st(scan_row + .6)}>100%</text>')
    gy_ = sy + 54
    b.append(bar(t, X - 6, gy_ - 24, 252, 32, granted, fill=acc[GREEN] + "26"))
    ag = f'x="{X + 4}" y="{gy_}" font-size="24" font-weight="bold" letter-spacing="2"'
    b.append(f'<text class="gr" {ag} fill="{acc[RED]}"{st(granted, jx="-5px")}>ACCESS GRANTED</text>')
    b.append(f'<text class="gb" {ag} fill="{acc[BLUE]}"{st(granted, jx="5px")}>ACCESS GRANTED</text>')
    b.append(f'<text class="ag" {ag} fill="{act[GREEN]}"{st(granted)}>ACCESS GRANTED</text>')
    wdefs, wbody, wspans = typewriter([[("welcome, builder. scroll down ↓", t["muted"])]], X, gy_ + 28, 25, 13, welcome, "w", t["text"], speed=.03)
    defs[-1:-1] = wdefs
    b += wbody
    b.append(f'<text class="in" x="{X}" y="{gy_ + 62}" font-size="{fs}" fill="{act[GREEN]}"{st(wspans[0][1] + .1)}>$</text>')
    b.append(end_cursor(X + 2 * cw, gy_ + 62, fs, t["text"], wspans[0][1] + .1))

    # radar, bottom right
    b.append(f'<g class="in"{st(SPIN0 - .3)}>')
    for r in (RR, RR * .66, RR * .33):
        b.append(f'<circle cx="{RX}" cy="{RY}" r="{r:.1f}" fill="none" stroke="{t["border"]}"/>')
    b.append(f'<path d="M{RX - RR},{RY}H{RX + RR}M{RX},{RY - RR}V{RY + RR}" stroke="{t["border"]}" stroke-dasharray="2 3"/></g>')
    trail = math.radians(-55)
    b.append(
        f'<g class="sweep"><path d="M{RX},{RY}L{RX},{RY - RR}A{RR},{RR} 0 0 0 {RX + RR * math.sin(trail):.1f},{RY - RR * math.cos(trail):.1f}Z" fill="{acc[GREEN]}" fill-opacity=".16"/>'
        f'<line x1="{RX}" y1="{RY}" x2="{RX}" y2="{RY - RR}" stroke="{acc[GREEN]}" stroke-width="1.5"/></g>'
    )
    for a, rr, c, at in blips:
        px, py = RX + rr * math.sin(math.radians(a)), RY - rr * math.cos(math.radians(a))
        b.append(f'<circle class="ping" cx="{px:.1f}" cy="{py:.1f}" r="4" fill="none" stroke="{c}" stroke-width="1.5"{st(at)}/>')
        b.append(f'<circle class="pop" cx="{px:.1f}" cy="{py:.1f}" r="3.2" fill="{c}"{st(at)}/>')
    legend = [("sector", "tiet · patiala", t["head"], SPIN0), ("domains", f"{len(DOMAINS):02d} detected", t["head"], found),
              ("status", "online", act[GREEN], found + .3)]
    for i, (key, val, c, at) in enumerate(legend):
        b.append(f'<text class="in" x="{X}" y="{RY - 22 + i * 21}" font-size="12"{st(at)}><tspan fill="{t["muted"]}">{key:<9}</tspan><tspan fill="{c}">{esc(val)}</tspan></text>')

    # scan lines, drawn over everything in the body
    beam = (
        f'<rect y="{TOP - 90}" width="{W}" height="90" fill="url(#beam)"/>'
        f'<rect y="{TOP - 2}" width="{W}" height="2" fill="{acc[BLUE]}" fill-opacity=".75"/>'
    )
    b.append(f'<g clip-path="url(#card)"><g clip-path="url(#body)"><g class="beam">{beam}</g><g class="idle" opacity=".5">{beam}</g></g></g>')

    # powerline status bar
    sb = [f'<g clip-path="url(#card)"><g class="sbar"><rect y="{BOT}" width="{W}" height="{SB}" fill="{t["panel"]}"/>'
          f'<rect y="{BOT}" width="{W}" height="1" fill="{t["border"]}"/>']
    segs, x = [], 0
    for label, fill in (("ONLINE", acc[GREEN]), (ORG.lower(), acc[BLUE])):
        w = len(label) * 7.2 + (28 if x == 0 else 38)
        segs.append((x, w, label, fill))
        x += w
    for sx, w, label, fill in reversed(segs):  # right to left, so each arrow sits on top of the next segment
        sb.append(f'<path d="M{sx:.1f},{BOT}H{sx + w:.1f}L{sx + w + 12:.1f},{BOT + 16}L{sx + w:.1f},{H}H{sx:.1f}Z" fill="{fill}"/>')
        sb.append(f'<text x="{sx + (14 if sx == 0 else 26):.1f}" y="{BOT + 21}" font-size="12" font-weight="bold" fill="{INK}">{esc(label)}</text>')
    sb.append(f'<text x="{x + 26:.1f}" y="{BOT + 21}" font-size="12" fill="{t["muted"]}">{esc(CAMPUS.lower())} · {esc(CITY.lower())}</text>')
    season = f"'{date.today().year % 100:02d}"
    sw = len(season) * 7.2 + 30
    sb.append(f'<path d="M{W - sw:.1f},{BOT + 16}L{W - sw + 12:.1f},{BOT}H{W}V{H}H{W - sw + 12:.1f}Z" fill="{acc[YELLOW]}"/>')
    sb.append(f'<text x="{W - sw / 2 + 5:.1f}" y="{BOT + 21}" text-anchor="middle" font-size="12" font-weight="bold" fill="{INK}">{season}</text>')
    sb.append(f'<text x="{W - sw - 10:.1f}" y="{BOT + 21}" text-anchor="end" font-size="12" fill="{t["muted"]}">ig {ig} · in {li} · utf-8</text>')
    sb.append("</g></g>")
    b += sb
    b.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{t["border"]}"/>')
    label = (f"{ORG} boot screen: LED pixels fly in and lock into the letters GDG TIET under a scan line, "
             f"a terminal runs an access handshake ending in ACCESS GRANTED, and a radar finds {len(DOMAINS)} domains")
    return svg(W, H, label, css, "\n".join(defs) + "\n" + "\n".join(b) + "\n")


# ── SECTION HEADER ──────────────────────────────────────────────────────────

def header(t, i, name):
    W, H = 1000, 60
    acc, act = t["accents"][i % 4], t["accent_text"][i % 4]
    title = name.upper()
    n, fs, ls = len(title), 22, 3
    step = fs * CHAR + ls
    tx, t0 = 54, .25
    typing = max(.3, n * .07)
    t_end = t0 + typing
    path = f"~/{ORG.lower()}/{name.lower().replace(' ', '-')}"
    line_x1 = tx + n * step + 16
    line_x2 = W - len(path) * 12 * CHAR - 16
    gw = 70
    travel = line_x2 - line_x1 - gw
    if IDLE:
        glint = (f"animation:glint 7s ease-in-out {t_end + .45:.2f}s infinite}}\n@keyframes glint{{0%{{opacity:0;transform:none}}2%{{opacity:1}}12%{{opacity:1}}"
                 f"14%,100%{{opacity:0;transform:translateX({travel:.0f}px)}}}}")
    else:
        glint = (f"animation:glint 1s ease-in-out {t_end + .45:.2f}s both}}\n@keyframes glint{{0%{{opacity:0;transform:none}}15%{{opacity:1}}85%{{opacity:1}}"
                 f"100%{{opacity:0;transform:translateX({travel:.0f}px)}}}}")
    css = f"""
.tick{{transform-box:fill-box;transform-origin:50% 50%;transform:scaleY(0);animation:tick .35s ease-out .05s forwards}}
@keyframes tick{{to{{transform:none}}}}
.draw{{stroke-dasharray:1;stroke-dashoffset:1;animation:draw .8s ease-out {t_end:.2f}s forwards}}
.glint{{opacity:0;{glint}
"""
    b = [
        "<defs>",
        typed_clip("typ", tx - 1, 8, 44, n, step, t0, typing),
        f'<linearGradient id="gl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{acc}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{acc}"/><stop offset="1" stop-color="{acc}" stop-opacity="0"/></linearGradient>',
        "</defs>",
        f'<rect class="tick" x="0" y="17" width="4" height="26" rx="2" fill="{acc}"/>',
        f'<text class="in" x="14" y="37" font-size="13" font-weight="bold" fill="{act}"{st(.15)}>'
        f'{i + 1:02d}<tspan fill="{t["dim"]}" font-weight="normal"> /</tspan></text>',
        f'<text x="{tx}" y="39" font-size="{fs}" font-weight="bold" letter-spacing="{ls}" fill="{t["head"]}" clip-path="url(#typ)">{esc(title)}</text>',
        ride_cursor(tx + 2, 17, 26, n, step, t0, typing, acc, t_end + .5, width=11),
        f'<line class="draw" x1="{line_x1:.1f}" y1="30" x2="{line_x2:.1f}" y2="30" stroke="{t["border"]}" stroke-width="1.5" pathLength="1"/>',
        f'<rect class="glint" x="{line_x1:.1f}" y="28.5" width="{gw}" height="3" rx="1.5" fill="url(#gl)"/>',
        f'<text class="in" x="{W}" y="35" text-anchor="end" font-size="12" fill="{t["muted"]}"{st(t_end + .3)}>{esc(path)}</text>',
    ]
    return svg(W, H, f"Section {i + 1:02d}: {title}", css, "\n".join(b) + "\n")


# ── ABOUT: an editor typing a class ─────────────────────────────────────────

def about(t):
    W, TOP, lh, fs = 1000, 40, 24, 14
    GUT, X = 52, 70
    cw = fs * CHAR
    syn, acc = t["syn"], t["accents"]

    def q(s):
        return f'"{s}"'

    def lst(items):
        spans = [("[", "pun")]
        for k, it in enumerate(items):
            spans += ([(", ", "pun")] if k else []) + [(q(it), "str")]
        return spans + [("]", "pun")]

    def attr(name, spans):
        return [(f"    {name:<10} ", "attr"), ("= ", "pun")] + spans

    code = [
        [("# the community behind this org", "com")],
        [("class ", "kw"), ("GDG_TIET", "cls"), ("(", "pun"), ("Community", "cls"), ("):", "pun")],
        attr("campus", [(q(CAMPUS), "str")]),
        attr("city", [(q(CITY), "str")]),
        attr("powered_by", [(q("Google for Developers"), "str")]),
        attr("formerly", lst(FORMERLY)),
        attr("domains", lst([d[1].lower().replace(" ", "") for d in DOMAINS])),
        [],
        [("    def ", "kw"), ("why", "fn"), ("(", "pun"), ("self", "attr"), ("):", "pun")],
        [("        # open to every branch, not just computer science", "com")],
        [("        return ", "kw"), (q("learn the vast, ever-growing world of tech, together"), "str")],
    ]
    y0 = TOP + 30
    H = y0 + (len(code) - 1) * lh + 44
    SBY = H - 24
    lines = [[(s, syn[k]) for s, k in line] for line in code]
    tdefs, tbody, spans = typewriter(lines, X, y0, lh, fs, .35, "c", t["text"], speed=.007, gap=.05)
    done = spans[-1][1]

    starts = [s for s, _ in spans]
    total = done - starts[0]
    keys = ";".join(f"{(s - starts[0]) / total:.4f}" for s in starts)
    ys = ";".join(f"{y0 + i * lh - 17}" for i in range(len(code)))
    css = ""
    b = [
        "<defs>",
        f'<clipPath id="card"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14"/></clipPath>',
        *tdefs, "</defs>",
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["bg"]}"/>',
        '<g clip-path="url(#card)">',
        f'<rect width="{W}" height="{TOP}" fill="{t["panel"]}"/><rect y="{TOP}" width="{W}" height="1" fill="{t["border"]}"/>',
    ]
    for i, c in enumerate((acc[RED], acc[YELLOW], acc[GREEN])):
        b.append(f'<circle cx="{22 + i * 20}" cy="{TOP / 2}" r="6" fill="{c}"/>')
    # tabs
    b.append(f'<path d="M86,{TOP + 1}V12Q86,7 91,7H231Q236,7 236,12V{TOP + 1}Z" fill="{t["bg"]}"/>')
    b.append(f'<rect x="86" y="7" width="150" height="2" rx="1" fill="{acc[BLUE]}"/>')
    b.append(f'<circle cx="102" cy="25" r="3.5" fill="{acc[YELLOW]}"/><text x="113" y="29" font-size="12" fill="{t["head"]}">gdg_tiet.py</text>')
    b.append(f'<text x="258" y="29" font-size="12" fill="{t["dim"]}">README.md</text><text x="358" y="29" font-size="12" fill="{t["dim"]}">events.json</text>')
    # current-line highlight follows the typing
    b.append(f'<rect x="{GUT + 1}" y="{y0 - 17}" width="{W - GUT - 112}" height="{lh}" fill="{t["head"]}" fill-opacity=".045">'
             f'<animate attributeName="y" values="{ys}" keyTimes="{keys}" calcMode="discrete" begin="{starts[0]:.2f}s" dur="{total:.2f}s" fill="freeze"/></rect>')
    b.append(f'<rect x="{GUT}" y="{TOP + 1}" width="1" height="{SBY - TOP - 1}" fill="{t["border"]}"/>')
    b.append(f'<rect x="{W - 110}" y="{TOP + 1}" width="1" height="{SBY - TOP - 1}" fill="{t["border"]}"/>')
    for i, line in enumerate(code):
        y = y0 + i * lh
        b.append(f'<text class="in" x="{GUT - 12}" y="{y}" text-anchor="end" font-size="12" fill="{t["dim"]}"{st(starts[i])}>{i + 1}</text>')
        n = sum(len(s) for s, _ in line)
        if n:
            first = next(k for s, k in line if s.strip())
            b.append(f'<rect class="in" x="{W - 98 + (len(line[0][0]) - len(line[0][0].lstrip())) * 1.2:.1f}" y="{TOP + 16 + i * 6}" '
                     f'width="{min(80, n * .95):.1f}" height="3" rx="1.5" fill="{syn[first]}" fill-opacity=".75"{st(starts[i])}/>')
    b.append(f'<rect class="in" x="{W - 104}" y="{TOP + 10}" width="98" height="{len(code) * 6 + 12}" rx="3" fill="{t["head"]}" fill-opacity=".04"{st(.3)}/>')
    b += tbody
    last_n = sum(len(s) for s, _ in code[-1])
    b.append(end_cursor(X + last_n * cw, y0 + (len(code) - 1) * lh, fs, t["text"], done + .05))
    # status bar
    b.append(f'<rect y="{SBY}" width="{W}" height="24" fill="{acc[BLUE]}"/>')
    b.append(f'<text x="14" y="{SBY + 16}" font-size="11" fill="#ffffff" font-weight="bold">NORMAL</text>'
             f'<text x="80" y="{SBY + 16}" font-size="11" fill="#ffffff">git:main   0 problems</text>')
    b.append(f'<text class="in" x="{W - 14}" y="{SBY + 16}" text-anchor="end" font-size="11" fill="#ffffff"{st(done)}>'
             f'Ln {len(code)}, Col {last_n + 1}   UTF-8   Python   {ORG}</text>')
    b.append("</g>")
    b.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{t["border"]}"/>')
    label = (f"An editor typing out a Python class that describes {ORG}: {CAMPUS}, {CITY}, powered by Google for Developers, "
             f"formerly {' and '.join(FORMERLY)}, with domains {', '.join(d[1] for d in DOMAINS)}")
    return svg(W, H, label, css, "\n".join(b) + "\n")


# ── DOMAINS: tiles with self-drawing icons ──────────────────────────────────

def icon(kind, cx, cy, c, t, d):
    s = f'stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    out = []
    if kind == "dev":
        out.append(f'<path class="mv" d="M{cx - 6},{cy - 12}L{cx - 16},{cy}L{cx - 6},{cy + 12}" {s}{st(d, mx="9px")}/>')
        out.append(f'<path class="mv" d="M{cx + 6},{cy - 12}L{cx + 16},{cy}L{cx + 6},{cy + 12}" {s}{st(d, mx="-9px")}/>')
        out.append(f'<path class="dr" d="M{cx + 4},{cy - 14}L{cx - 4},{cy + 14}" pathLength="1" {s}{st(d + .35)}/>')
    elif kind == "aiml":
        layers = [[-12, 0, 12], [-15, -5, 5, 15], [-7, 7]]
        xs = [cx - 15, cx, cx + 15]
        for li in range(2):
            for ya in layers[li]:
                for yb in layers[li + 1]:
                    out.append(f'<line class="dr" x1="{xs[li]}" y1="{cy + ya}" x2="{xs[li + 1]}" y2="{cy + yb}" stroke="{c}" '
                               f'stroke-opacity=".45" stroke-width="1.2" pathLength="1"{st(d + li * .25)}/>')
        for li, ys in enumerate(layers):
            for j, ya in enumerate(ys):
                out.append(f'<circle class="pop" cx="{xs[li]}" cy="{cy + ya}" r="3.2" fill="{c}"{st(d + .15 + li * .25 + j * .04)}/>')
    elif kind == "iot":
        out.append(f'<rect class="pop" x="{cx - 8}" y="{cy + 2}" width="16" height="14" rx="3" {s}{st(d)}/>')
        out.append(f'<path class="dr" d="M{cx - 8},{cy + 6}H{cx - 13}M{cx - 8},{cy + 12}H{cx - 13}M{cx + 8},{cy + 6}H{cx + 13}M{cx + 8},{cy + 12}H{cx + 13}" pathLength="1" {s}{st(d + .2)}/>')
        out.append(f'<circle class="pop" cx="{cx}" cy="{cy - 3}" r="2.2" fill="{c}"{st(d + .3)}/>')
        a = math.radians(42)
        for k, r in enumerate((7, 13, 19)):
            x1, y1, x2 = cx - r * math.sin(a), cy - 3 - r * math.cos(a), cx + r * math.sin(a)
            out.append(f'<path class="in" d="M{x1:.1f},{y1:.1f}A{r},{r} 0 0 1 {x2:.1f},{y1:.1f}" {s}{st(d + .4 + k * .15)}/>')
    elif kind == "design":
        p0, c1, c2, p1 = (cx - 18, cy + 12), (cx - 10, cy - 20), (cx + 10, cy + 20), (cx + 18, cy - 12)
        thin = f'stroke="{t["muted"]}" stroke-width="1.2" fill="none"'
        out.append(f'<path class="dr" d="M{p0[0]},{p0[1]}L{c1[0]},{c1[1]}" pathLength="1" {thin}{st(d)}/>')
        out.append(f'<path class="dr" d="M{p1[0]},{p1[1]}L{c2[0]},{c2[1]}" pathLength="1" {thin}{st(d + .1)}/>')
        out.append(f'<path class="dr" d="M{p0[0]},{p0[1]}C{c1[0]},{c1[1]} {c2[0]},{c2[1]} {p1[0]},{p1[1]}" pathLength="1" {s}{st(d + .2)}/>')
        for px, py in (p0, p1):
            out.append(f'<rect class="pop" x="{px - 3.5}" y="{py - 3.5}" width="7" height="7" fill="{t["panel"]}" stroke="{c}" stroke-width="1.6"{st(d + .1)}/>')
        for px, py in (c1, c2):
            out.append(f'<circle class="pop" cx="{px}" cy="{py}" r="2.6" fill="{t["muted"]}"{st(d + .15)}/>')
    elif kind == "management":
        colx = [cx - 18, cx - 5, cx + 8]
        for x in colx:
            out.append(f'<rect class="in" x="{x - 1}" y="{cy - 17}" width="12" height="34" rx="3" fill="none" stroke="{t["dim"]}" stroke-width="1.2"{st(d)}/>')
        for k, (ci, ri) in enumerate([(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (2, 0)]):
            out.append(f'<rect class="mv" x="{colx[ci] + 1}" y="{cy - 14 + ri * 10}" width="8" height="7" rx="1.5" fill="{c}" '
                       f'fill-opacity="{1 - ri * .25}"{st(d + .2 + k * .09, my="-10px")}/>')
    elif kind == "marketing":
        out.append(f'<path class="dr" d="M{cx - 18},{cy - 16}V{cy + 16}H{cx + 18}" pathLength="1" stroke="{t["dim"]}" stroke-width="1.6" fill="none"{st(d)}/>')
        pts = [(cx - 14, cy + 9), (cx - 6, cy + 2), (cx + 1, cy + 6), (cx + 9, cy - 5), (cx + 16, cy - 13)]
        out.append(f'<polyline class="dr" points="{" ".join(f"{x},{y}" for x, y in pts)}" pathLength="1" {s}{st(d + .2)}/>')
        out.append(f'<path class="pop" d="M{cx + 9},{cy - 13}H{cx + 16}V{cy - 6}" {s}{st(d + .75)}/>')
        for k, (x, y) in enumerate(pts[:-1]):
            out.append(f'<circle class="pop" cx="{x}" cy="{y}" r="2" fill="{c}"{st(d + .3 + k * .1)}/>')
    return "".join(out) + "\n"


def domains(t):
    W, cols, gap, th = 1000, 3, 20, 170
    tw = (W - gap * (cols - 1)) / cols
    rows = -(-len(DOMAINS) // cols)
    H = rows * th + (rows - 1) * gap
    acc, act = t["accents"], t["accent_text"]
    rng = random.Random("domains")
    css = f"""
.tbeam{{opacity:0;animation:tsweep .9s ease-in-out both}}
@keyframes tsweep{{0%{{opacity:0;transform:none}}10%{{opacity:1}}85%{{opacity:1}}100%{{opacity:0;transform:translateY({th + 60}px)}}}}
.idle{{opacity:0;{"animation:idle 11s linear 6s infinite" if IDLE else "display:none"}}}
@keyframes idle{{0%{{opacity:0;transform:none}}2%{{opacity:1}}14%{{opacity:1}}16%,100%{{opacity:0;transform:translateY({H + 80}px)}}}}
"""
    defs, b = ["<defs>"], []
    for k, c in enumerate(acc):
        defs.append(f'<linearGradient id="tb{k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c}" stop-opacity="0"/>'
                    f'<stop offset="1" stop-color="{c}" stop-opacity=".22"/></linearGradient>')
    defs.append(f'<linearGradient id="ib" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["head"]}" stop-opacity="0"/>'
                f'<stop offset="1" stop-color="{t["head"]}" stop-opacity=".05"/></linearGradient>')
    for i, (kind, title, tags) in enumerate(DOMAINS):
        r, c = divmod(i, cols)
        x, y = c * (tw + gap), r * (th + gap)
        d = .2 + i * .14
        a, at = acc[i % 4], act[i % 4]
        defs.append(f'<clipPath id="t{i}"><rect x="{x + .5:.1f}" y="{y + .5:.1f}" width="{tw - 1:.1f}" height="{th - 1:.1f}" rx="12"/></clipPath>')
        b.append(frame_rect(t, x, y, tw, th, d))
        b.append(
            f'<g clip-path="url(#t{i})"><rect class="in" x="{x:.1f}" y="{y}" width="{tw:.1f}" height="3" fill="{a}"{st(d + .4)}/>'
            f'<g class="tbeam"{st(d + .35)}><rect x="{x:.1f}" y="{y - 60}" width="{tw:.1f}" height="60" fill="url(#tb{i % 4})"/>'
            f'<rect x="{x:.1f}" y="{y - 2}" width="{tw:.1f}" height="2" fill="{a}" fill-opacity=".6"/></g></g>\n'
        )
        b.append(f'<rect class="pop" x="{x + 22:.1f}" y="{y + 24}" width="56" height="56" rx="14" fill="{a}" fill-opacity=".1" stroke="{a}" stroke-opacity=".35"{st(d + .3)}/>\n')
        b.append(icon(kind, x + 50, y + 52, a, t, d + .45))
        b.append(frames_svg(scramble(title, 10, f"dom{i}"), f'x="{x + 96:.1f}" y="{y + 50}" font-size="19" font-weight="bold" letter-spacing="1" fill="{t["head"]}"', d + .4))
        b.append(f'<text class="in" x="{x + 96:.1f}" y="{y + 72}" font-size="12" fill="{t["muted"]}"{st(d + .75)}>{esc(tags)}</text>\n')
        b.append(f'<line class="in" x1="{x + 22:.1f}" y1="{y + 108}" x2="{x + tw - 22:.1f}" y2="{y + 108}" stroke="{t["border"]}" stroke-dasharray="3 5"{st(d + .5)}/>\n')
        b.append(f'<text class="in" x="{x + 22:.1f}" y="{y + 142}" font-size="12" font-weight="bold" fill="{at}"{st(d + .6)}>{i + 1:02d}'
                 f'<tspan fill="{t["dim"]}" font-weight="normal">  ~/domains/{kind}</tspan></text>\n')
        for k in range(12):
            h = rng.uniform(4, 22)
            bx = x + tw - 22 - 12 * 7 + k * 7
            b.append(f'<rect class="gy" x="{bx:.1f}" y="{y + 147 - h:.1f}" width="4" height="{h:.1f}" rx="1" fill="{a}" fill-opacity=".55"{st(d + .6 + k * .035)}/>')
        b.append("\n")
    defs.append("</defs>\n")
    b.append(f'<g class="idle"><rect y="-80" width="{W}" height="80" fill="url(#ib)"/></g>')
    label = f"{ORG} domains, one tile each with an icon that draws itself: " + "; ".join(f"{title}: {tags}" for _, title, tags in DOMAINS)
    return svg(W, H, label, css, "\n".join(defs) + "".join(b))


# ── EVENTS: a split-flap board ──────────────────────────────────────────────

def events(t):
    W = 1000
    tw_, th_, step, colgap = 36, 46, 39, 22
    cols = [2, 16, 3]
    total = sum(n * step - 3 for n in cols) + colgap * (len(cols) - 1)
    x0 = (W - total) / 2
    xs, starts, x = [], [], x0
    for n in cols:
        starts.append(x)
        xs += [x + k * step for k in range(n)]
        x += n * step - 3 + colgap
    top, rowh = 92, th_ + 10
    H = top + len(EVENTS) * rowh - 10 + 26
    acc, act = t["accents"], t["accent_text"]
    flap = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'-"
    css = ""
    b = [
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["panel"]}" stroke="{t["border"]}"/>',
        f'<circle class="in" cx="26" cy="24" r="4" fill="{acc[RED]}"/>',
        f'<text x="40" y="28" font-size="12" font-weight="bold" letter-spacing="3" fill="{t["head"]}">EVENT BOARD</text>',
        f'<text x="{W - 24}" y="28" text-anchor="end" font-size="11" letter-spacing="1" fill="{t["muted"]}">source  {esc(INSTAGRAM["handle"])} highlights</text>',
        f'<rect y="46" width="{W}" height="1" fill="{t["border"]}"/>',
    ]
    for label, sx in zip(("NO", "EVENT", "SEASON"), starts):
        b.append(f'<text x="{sx:.1f}" y="78" font-size="10" letter-spacing="2" fill="{t["muted"]}">{label}</text>')
    for r, (name, season) in enumerate(EVENTS):
        y = top + r * rowh
        begin = .35 + r * .2
        for x in xs:
            b.append(f'<rect x="{x:.1f}" y="{y}" width="{tw_}" height="{th_}" rx="4" fill="{t["tile"]}"/>'
                     f'<rect x="{x:.1f}" y="{y}" width="{tw_}" height="{th_ / 2}" rx="4" fill="#ffffff" fill-opacity=".045"/>'
                     f'<rect x="{x:.1f}" y="{y + th_ / 2 - .75}" width="{tw_}" height="1.5" fill="{t["split"]}"/>')
        text = f"{r + 1:02d}" + name.upper()[:16].ljust(16) + season[:3].ljust(3)
        frames = scramble(text, 14, f"ev{r}", keep_spaces=False, glyphs=flap)

        def colour(s, r=r):
            return (f'<tspan fill="{acc[r % 4]}">{esc(s[:2])}</tspan><tspan fill="#f0f6fc">{esc(s[2:18])}</tspan>'
                    f'<tspan fill="{acc[YELLOW]}">{esc(s[18:])}</tspan>')

        xattr = " ".join(f"{x + tw_ / 2:.1f}" for x in xs)
        b.append(frames_svg(frames, f'x="{xattr}" y="{y + th_ / 2 + 9}" text-anchor="middle" font-size="24" font-weight="bold"', begin, colour))
        settled = begin + 14 * FRAME
        b.append(f'<circle cx="{x0 - 30:.1f}" cy="{y + th_ / 2}" r="5" fill="{t["cell"]}"/>'
                 f'<circle class="pop" cx="{x0 - 30:.1f}" cy="{y + th_ / 2}" r="5" fill="{acc[GREEN]}"{st(settled)}/>')
    label = f"{ORG} event board, split-flap style: " + ", ".join(f"{n} {s}" for n, s in EVENTS)
    return svg(W, H, label, css, "\n".join(b) + "\n")


# ── PROJECTS: the org's public repos, as a terminal listing ─────────────────

def org_repos():
    req = urllib.request.Request(
        f"https://api.github.com/orgs/{ORG}/repos?type=public&per_page=100",
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"{ORG}-readme"},
    )
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            repos = json.load(r)
    except OSError as e:
        print(f"  could not list repos ({e}); drawing the empty state")
        return []
    repos = [r for r in repos if not r["name"].startswith(".") and not r["fork"] and not r["archived"]]
    repos.sort(key=lambda r: (r["stargazers_count"], r["pushed_at"] or ""), reverse=True)
    return [{"name": r["name"], "description": r["description"] or "", "language": r["language"], "stars": r["stargazers_count"]}
            for r in repos[:6]]


def projects(t, repos):
    W, TOP, fs, lh, X = 1000, 36, 14, 26, 28
    act = t["accent_text"]
    lines = [[("$ ", act[GREEN]), (f"gh repo list {ORG} --visibility public", t["head"])]]
    if repos:
        lines.append([(f"  {'NAME':<24}{'DESCRIPTION':<46}{'LANG':<14}STARS", t["dim"])])
        for r in repos:
            desc = r["description"] if len(r["description"]) <= 44 else r["description"][:43] + "…"
            lang = r["language"] or "-"
            lines.append([("  ", t["text"]), (f"{r['name'][:22]:<24}", act[BLUE]), (f"{desc:<46}", t["text"]),
                          ("● ", LANG_COLORS.get(lang, t["muted"])), (f"{lang[:11]:<12}", t["muted"]), (str(r["stars"]), act[YELLOW])])
        lines.append([("$ ", act[GREEN])])
    else:
        lines.append([("  scanning org ", t["muted"]), ("." * 30, t["dim"]), (" 0 public repos", act[YELLOW])])
        lines.append([("  no public builds yet. the first one could be yours.", t["muted"])])
        lines.append([])
        lines.append([("$ ", act[GREEN]), ("git push origin main", t["head"])])
    y0 = TOP + 34
    H = y0 + (len(lines) - 1) * lh + 26
    tdefs, tbody, spans = typewriter(lines, X, y0, lh, fs, .3, "p", t["text"], speed=.012)
    last_n = sum(len(s) for s, _ in lines[-1])
    b = [
        "<defs>", f'<clipPath id="card"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14"/></clipPath>', *tdefs, "</defs>",
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["bg"]}"/>',
        f'<g clip-path="url(#card)">{chrome(t, W, f"gh — {ORG.lower()}/projects")}</g>',
        *tbody,
        end_cursor(X + last_n * fs * CHAR, y0 + (len(lines) - 1) * lh, fs, t["text"], spans[-1][1] + .05),
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{t["border"]}"/>',
    ]
    if repos:
        label = f"{ORG} public repos: " + ", ".join(r["name"] for r in repos)
    else:
        label = f"A terminal listing {ORG}'s public repos: none yet, with git push origin main typed at the prompt"
    return svg(W, H, label, "", "\n".join(b) + "\n")


# ── CORE TEAM: ID badges ────────────────────────────────────────────────────

def avatar_data(user):
    try:
        with urllib.request.urlopen(f"https://github.com/{user}.png?size=144", timeout=15) as r:
            return f"data:{r.headers.get_content_type()};base64," + base64.b64encode(r.read()).decode()
    except OSError as e:
        print(f"  avatar for {user} failed ({e}); drawing a silhouette")
        return None


def team(t, avatars):
    W, gap, H = 1000, 20, 252
    n = len(TEAM)
    bw = (W - gap * (n - 1)) / n
    acc, act = t["accents"], t["accent_text"]
    rng = random.Random("team")
    css = """
.stamp{opacity:0;transform-box:fill-box;transform-origin:50% 50%;animation:stamp .35s cubic-bezier(.3,1.4,.5,1) both}
@keyframes stamp{from{opacity:0;transform:scale(1.8)}to{opacity:.92;transform:none}}
.tbeam{opacity:0;animation:laser .9s ease-in-out both}
@keyframes laser{0%{opacity:0;transform:none}10%{opacity:1}50%{transform:translateY(26px)}90%{opacity:1}100%{opacity:0;transform:none}}
"""
    defs = ["<defs>", f'<pattern id="hz" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                      f'<rect width="4" height="8" fill="{t["muted"]}" fill-opacity=".4"/></pattern>']
    b = []
    for i, m in enumerate(TEAM):
        m = m or {}
        x = i * (bw + gap)
        cx, cy = x + bw / 2, 106
        d = .2 + i * .15
        a, at = acc[i % 4], act[i % 4]
        defs.append(f'<clipPath id="b{i}"><rect x="{x + .5:.1f}" y=".5" width="{bw - 1:.1f}" height="{H - 1}" rx="14"/></clipPath>')
        defs.append(f'<clipPath id="av{i}"><circle cx="{cx:.1f}" cy="{cy}" r="34"/></clipPath>')
        b.append(frame_rect(t, x, 0, bw, H, d, rx=14))
        b.append(f'<g clip-path="url(#b{i})"><rect class="in" x="{x:.1f}" y="0" width="{bw:.1f}" height="4" fill="{a}"{st(d + .3)}/></g>')
        b.append(f'<g class="in"{st(d + .35)}>'
                 f'<rect x="{cx - 20:.1f}" y="14" width="40" height="8" rx="4" fill="{t["bg"]}" stroke="{t["border"]}"/>'
                 f'<text x="{x + 18:.1f}" y="48" font-size="10" font-weight="bold" letter-spacing="3" fill="{at}">GDG · TIET</text>')
        cwid = len(TEAM_LABEL) * 8 + 14
        b.append(f'<rect x="{x + bw - 14 - cwid:.1f}" y="35" width="{cwid}" height="18" rx="9" fill="{a}" fill-opacity=".12" stroke="{a}" stroke-opacity=".6"/>'
                 f'<text x="{x + bw - 14 - cwid / 2:.1f}" y="48" text-anchor="middle" font-size="10" font-weight="bold" letter-spacing="2" fill="{at}">{esc(TEAM_LABEL)}</text></g>')
        b.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="34" fill="{t["cell"]}"/>')
        if avatars[i]:
            b.append(f'<image class="in" href="{avatars[i]}" x="{cx - 34:.1f}" y="{cy - 34}" width="68" height="68" clip-path="url(#av{i})"{st(d + .5)}/>')
        else:
            b.append(f'<g class="in" clip-path="url(#av{i})"{st(d + .45)}><circle cx="{cx:.1f}" cy="{cy - 8}" r="12" fill="{t["dim"]}"/>'
                     f'<path d="M{cx - 24:.1f},{cy + 36}Q{cx - 24:.1f},{cy + 10} {cx:.1f},{cy + 10}Q{cx + 24:.1f},{cy + 10} {cx + 24:.1f},{cy + 36}Z" fill="{t["dim"]}"/></g>')
        b.append(f'<circle class="dr" cx="{cx:.1f}" cy="{cy}" r="38" fill="none" stroke="{a}" stroke-width="2" pathLength="1"{st(d + .3)}/>')
        if m.get("name"):
            b.append(frames_svg(scramble(m["name"], 10, f"tm{i}"), f'x="{cx:.1f}" y="170" text-anchor="middle" font-size="15" font-weight="bold" fill="{t["head"]}"', d + .6))
        else:
            b.append(bar(t, cx - 62, 157, 124, 16, d + .6, fill="url(#hz)"))
        if m.get("role"):
            b.append(f'<text class="in" x="{cx:.1f}" y="192" text-anchor="middle" font-size="11" fill="{t["muted"]}"{st(d + .8)}>{esc(m["role"])}</text>')
        else:
            b.append(bar(t, cx - 36, 184, 72, 8, d + .7))
        # barcode with a laser pass
        bx, bars = x + 30, []
        while bx < x + bw - 32:
            w = rng.choice((1, 1, 2, 3))
            bars.append(f'<rect x="{bx:.1f}" y="206" width="{w}" height="22" fill="{t["head"]}" fill-opacity=".7"/>')
            bx += w + rng.choice((1, 2, 2, 3))
        b.append(f'<g class="in"{st(d + .7)}>{"".join(bars)}</g>')
        b.append(f'<rect class="tbeam" x="{x + 22:.1f}" y="204" width="{bw - 44:.1f}" height="2" rx="1" fill="{acc[RED]}"{st(d + 1.0)}/>')
        b.append(f'<text class="in" x="{cx:.1f}" y="243" text-anchor="middle" font-size="9" letter-spacing="2" fill="{t["dim"]}"{st(d + .8)}>ID {ORG}-{i + 1:03d}</text>')
        if not m.get("name"):
            b.append(f'<g transform="rotate(-12 {cx:.1f} {cy})"><g class="stamp"{st(d + 1.2)}>'
                     f'<rect x="{cx - 64:.1f}" y="{cy - 14}" width="128" height="28" rx="3" fill="{t["panel"]}" fill-opacity=".6" stroke="{act[RED]}" stroke-width="2"/>'
                     f'<text x="{cx:.1f}" y="{cy + 5}" text-anchor="middle" font-size="14" font-weight="bold" letter-spacing="3" fill="{act[RED]}">CLASSIFIED</text></g></g>')
        b.append("\n")
    defs.append("</defs>\n")
    named = [m["name"] for m in TEAM if m and m.get("name")]
    label = f"{ORG} {TEAM_LABEL} badges: " + (", ".join(named) if named else "identities classified until the team is announced")
    return svg(W, H, label, css, "\n".join(defs) + "".join(b))


# ── CONNECT: social cards with rolling follower counts ──────────────────────

def connect_card(t, kind):
    W, H = 490, 164
    acc, act = t["accents"], t["accent_text"]
    info = INSTAGRAM if kind == "instagram" else LINKEDIN
    ai = RED if kind == "instagram" else BLUE
    css = f"""
.shine{{opacity:0;{"animation:shine 8s ease-in-out 3s infinite" if IDLE else "display:none"}}}
@keyframes shine{{0%{{opacity:0;transform:none}}3%{{opacity:1}}14%{{opacity:1}}16%,100%{{opacity:0;transform:translateX({W + 200}px)}}}}
"""
    defs = ["<defs>", f'<clipPath id="card"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14"/></clipPath>',
            '<linearGradient id="ig" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#feda75"/><stop offset=".25" stop-color="#fa7e1e"/>'
            '<stop offset=".5" stop-color="#d62976"/><stop offset=".75" stop-color="#962fbf"/><stop offset="1" stop-color="#4f5bd5"/></linearGradient>',
            f'<linearGradient id="sh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["head"]}" stop-opacity="0"/>'
            f'<stop offset=".5" stop-color="{t["head"]}" stop-opacity=".07"/><stop offset="1" stop-color="{t["head"]}" stop-opacity="0"/></linearGradient>']
    b = [frame_rect(t, 0, 0, W, H, .1, rx=14)]
    b.append(f'<g clip-path="url(#card)"><rect class="in" width="{W}" height="3" fill="{acc[ai]}"{st(.4)}/>'
             f'<g transform="skewX(-20)"><rect class="shine" x="-180" y="0" width="90" height="{H}" fill="url(#sh)"/></g></g>')
    ix, iy = 24, 50
    if kind == "instagram":
        glyph = (f'<rect x="{ix}" y="{iy}" width="64" height="64" rx="18" fill="url(#ig)"/>'
                 f'<rect x="{ix + 15}" y="{iy + 15}" width="34" height="34" rx="10" fill="none" stroke="#fff" stroke-width="3.2"/>'
                 f'<circle cx="{ix + 32}" cy="{iy + 32}" r="8" fill="none" stroke="#fff" stroke-width="3.2"/>'
                 f'<circle cx="{ix + 42}" cy="{iy + 22}" r="2.3" fill="#fff"/>')
        platform, cta = "INSTAGRAM", "FOLLOW  →"
    else:
        glyph = (f'<rect x="{ix}" y="{iy}" width="64" height="64" rx="14" fill="#0A66C2"/>'
                 f'<text x="{ix + 32}" y="{iy + 45}" text-anchor="middle" font-family="{SANS}" font-size="34" font-weight="bold" fill="#fff">in</text>')
        platform, cta = "LINKEDIN", "CONNECT  →"
    b.append(f'<g class="pop"{st(.35)}>{glyph}</g>')
    b.append(f'<text class="in" x="108" y="50" font-size="11" letter-spacing="3" fill="{t["muted"]}"{st(.4)}>{platform}</text>')
    hs = 20 if len(info["handle"]) <= 16 else 16
    b.append(frames_svg(scramble(info["handle"], 10, kind), f'x="108" y="78" font-size="{hs}" font-weight="bold" fill="{t["head"]}"', .45))
    body, width = odometer(108, 124, f"{info['followers']:,}", 30, t["head"], .7, "o", defs)
    b.append(body)
    b.append(f'<text class="in" x="{108 + width + 10:.1f}" y="124" font-size="13" fill="{t["muted"]}"{st(1.4)}>followers</text>')
    b.append(f'<text class="in" x="108" y="146" font-size="10" letter-spacing="1" fill="{t["dim"]}"{st(1.5)}>counted {COUNTED}</text>')
    cwid = len(cta) * 7.2 + 28
    b.append(f'<g class="pop"{st(1.3)}><rect x="{W - 24 - cwid:.1f}" y="{H - 50}" width="{cwid:.1f}" height="28" rx="14" fill="{acc[ai]}" fill-opacity=".12" stroke="{acc[ai]}" stroke-opacity=".7"/>'
             f'<text x="{W - 24 - cwid / 2:.1f}" y="{H - 31.5}" text-anchor="middle" font-size="12" font-weight="bold" letter-spacing="1" fill="{act[ai]}">{cta}</text></g>')
    defs.append("</defs>")
    label = f"{platform.title()}: {info['handle']}, {info['followers']:,} followers (counted {COUNTED})"
    return svg(W, H, label, css, "\n".join(defs) + "\n" + "\n".join(b) + "\n")


# ── FOOTER ──────────────────────────────────────────────────────────────────

def footer(t):
    W, H = 1000, 128
    acc = t["accents"]
    cell = 7
    mw, mh = word_size("GDG", cell)
    mx, my = (W - mw) / 2, 12
    base = my + mh / 2
    sweep0, sweep = .95, .7
    css = f"""
.vbeam{{opacity:0;animation:vsweep {sweep}s linear {sweep0}s both}}
@keyframes vsweep{{0%{{opacity:0;transform:none}}10%{{opacity:1}}90%{{opacity:1}}100%{{opacity:0;transform:translateX({mw + 24:.0f}px)}}}}
.px{{opacity:0;animation:in .3s ease-out both}}
"""

    def sweep_at(x, y):
        return (sweep0 + (x - mx) / mw * sweep,)

    def ekg(x1, x2):
        mid = (x1 + x2) / 2
        return (f"M{x1:.1f},{base}H{mid - 40:.1f}l8,-7l8,14l6,-26l7,34l6,-18l5,3H{x2:.1f}")

    left, right = ekg(0, mx - 20), ekg(mx + mw + 20, W)
    b = ["<defs>",
         f'<linearGradient id="kl" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{mx:.0f}" y2="0"><stop offset="0" stop-color="{acc[BLUE]}" stop-opacity="0"/><stop offset=".5" stop-color="{acc[BLUE]}"/><stop offset="1" stop-color="{acc[RED]}"/></linearGradient>',
         f'<linearGradient id="kr" gradientUnits="userSpaceOnUse" x1="{mx + mw:.0f}" y1="0" x2="{W}" y2="0"><stop offset="0" stop-color="{acc[YELLOW]}"/><stop offset=".5" stop-color="{acc[GREEN]}"/><stop offset="1" stop-color="{acc[GREEN]}" stop-opacity="0"/></linearGradient>',
         f'<linearGradient id="vb" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{acc[BLUE]}" stop-opacity="0"/><stop offset="1" stop-color="{acc[BLUE]}" stop-opacity=".35"/></linearGradient>',
         "</defs>",
         f'<path class="dr" d="{left}" fill="none" stroke="url(#kl)" stroke-width="2" stroke-linejoin="round" pathLength="1" style="animation-duration:.9s;animation-delay:.1s"/>',
         f'<path class="dr" d="{right}" fill="none" stroke="url(#kr)" stroke-width="2" stroke-linejoin="round" pathLength="1" style="animation-duration:.9s;animation-delay:1.55s"/>']
    b.append(pixel_word("GDG", mx, my, cell, [acc[BLUE], acc[RED], acc[YELLOW]], t["cell"], sweep_at))
    b.append(f'<g class="vbeam"><rect x="{mx - 24:.1f}" y="{my - 4}" width="24" height="{mh + 8:.0f}" fill="url(#vb)"/>'
             f'<rect x="{mx - 2:.1f}" y="{my - 4}" width="2" height="{mh + 8:.0f}" fill="{acc[BLUE]}" fill-opacity=".7"/></g>')
    b.append(frames_svg(scramble("END OF TRANSMISSION", 12, "eot"), f'x="{W / 2}" y="94" text-anchor="middle" font-size="11" letter-spacing="4" fill="{t["muted"]}"', 1.9))
    b.append(f'<text class="in" x="{W / 2}" y="116" text-anchor="middle" font-size="12" fill="{t["dim"]}"{st(2.4)}>'
             f'{esc(NAME)} · {esc(CAMPUS)} · {esc(CITY)}</text>')
    return svg(W, H, f"End of transmission: {NAME}, {CAMPUS}, {CITY}", css, "\n".join(b) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    repos = org_repos()
    avatars = [avatar_data(m["github"]) if m and m.get("github") else None for m in TEAM]
    written = set()
    for theme, t in THEMES.items():
        files = {
            "hero": hero(t), "about": about(t), "domains": domains(t), "events": events(t),
            "projects": projects(t, repos), "team": team(t, avatars), "footer": footer(t),
            "connect-instagram": connect_card(t, "instagram"), "connect-linkedin": connect_card(t, "linkedin"),
        }
        for i, name in enumerate(SECTIONS):
            files[f"header-{name.lower().replace(' ', '-')}"] = header(t, i, name)
        for name, text in files.items():
            path = OUT / f"{name}-{theme}.svg"
            path.write_text(text, encoding="utf-8", newline="\n")
            written.add(path.name)
    for old in OUT.glob("*.svg"):
        if old.name not in written:
            old.unlink()
            print(f"  removed stale {old.name}")
    print(f"wrote {len(written)} files to {OUT} ({len(repos)} repos listed)")


if __name__ == "__main__":
    main()
