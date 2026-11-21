#!/usr/bin/env python3
"""Render the v3 edition of The World Chronicle (1024x1024).

v3 keeps the measured-text layout of v2 but replaces photo-style panels
with procedural vector illustrations: thirteen cards, each drawn from
polygons, lines and arcs with ImageDraw, plus a hand-built theatre map.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W = H = 1024
M = 20
OUT = Path(__file__).resolve().parent / "entry.png"

# ---------------------------------------------------------------- palette
BG = (10, 16, 28)
PANEL = (16, 25, 41)
PANEL_ALT = (13, 21, 35)
ILLO = (11, 18, 30)
INK = (233, 239, 248)
MUTED = (146, 163, 186)
DIM = (104, 120, 143)
AMBER = (232, 180, 74)
CYAN = (79, 195, 217)
RED = (226, 86, 74)
GREEN = (91, 191, 138)
VIOLET = (170, 140, 232)
RULE = (38, 52, 74)
RULE_SOFT = (26, 38, 56)

# ---------------------------------------------------------------- fonts
FDIR = "/usr/share/fonts/truetype/liberation"
FONTS = {
    "serif": f"{FDIR}/LiberationSerif-Regular.ttf",
    "serif_bold": f"{FDIR}/LiberationSerif-Bold.ttf",
    "serif_italic": f"{FDIR}/LiberationSerif-Italic.ttf",
    "sans": f"{FDIR}/LiberationSans-Regular.ttf",
    "sans_bold": f"{FDIR}/LiberationSans-Bold.ttf",
    "mono": f"{FDIR}/LiberationMono-Regular.ttf",
}
_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    key = (name, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(FONTS[name], size)
    return _cache[key]


# ---------------------------------------------------------------- colour
def blend(a, b, t: float):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


# ---------------------------------------------------------------- text
def tw(draw: ImageDraw.ImageDraw, text: str, f) -> float:
    return draw.textlength(text, font=f)


def wrap(draw, text: str, f, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if tw(draw, trial, f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def ellipsize(draw, text: str, f, max_w: int) -> str:
    if tw(draw, text, f) <= max_w:
        return text
    while text and tw(draw, text + "\u2026", f) > max_w:
        text = text[:-1]
    return text.rstrip() + "\u2026"


def fit_lines(draw, text: str, f, max_w: int, max_lines: int) -> list[str]:
    lines = wrap(draw, text, f, max_w)
    if len(lines) <= max_lines:
        return lines
    kept = lines[:max_lines]
    kept[-1] = ellipsize(draw, " ".join(lines[max_lines - 1:]), f, max_w)
    return kept


def tracked(draw, x, y, text, f, fill, spacing=1.0):
    cx = x
    for ch in text:
        draw.text((cx, y), ch, font=f, fill=fill)
        cx += tw(draw, ch, f) + spacing
    return cx


def tracked_width(draw, text, f, spacing=1.0):
    return sum(tw(draw, c, f) + spacing for c in text) - spacing


# ---------------------------------------------------------------- chrome
def panel(draw, box, fill=PANEL, outline=RULE, radius=4, top_rule=None):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1)
    if top_rule:
        draw.rounded_rectangle((box[0], box[1], box[2], box[1] + 3),
                               radius=radius, fill=top_rule)


def rule(draw, x0, y, x1, color=RULE, width=1):
    draw.line((x0, y, x1, y), fill=color, width=width)


def dashed(draw, p0, p1, fill, width=1, segments=7):
    for i in range(segments):
        t0, t1 = i / segments, (i + 0.55) / segments
        draw.line((p0[0] + (p1[0] - p0[0]) * t0, p0[1] + (p1[1] - p0[1]) * t0,
                   p0[0] + (p1[0] - p0[0]) * t1, p0[1] + (p1[1] - p0[1]) * t1),
                  fill=fill, width=width)


def ellipse_pts(cx, cy, rx, ry, n=72, start=0.0, end=math.tau):
    return [(cx + rx * math.cos(start + (end - start) * i / n),
             cy + ry * math.sin(start + (end - start) * i / n)) for i in range(n + 1)]


def illo_frame(draw, box, ac):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=3, fill=ILLO, outline=blend(RULE, ac, 0.22))
    draw.line((x0 + 6, y1 - 0.5, x1 - 6, y1 - 0.5), fill=blend(ILLO, ac, 0.35))
    # corner registration ticks
    for cx, cy, dx, dy in ((x0 + 4, y0 + 4, 1, 1), (x1 - 4, y0 + 4, -1, 1),
                           (x0 + 4, y1 - 4, 1, -1), (x1 - 4, y1 - 4, -1, -1)):
        draw.line((cx, cy, cx + dx * 5, cy), fill=blend(ILLO, ac, 0.5))
        draw.line((cx, cy, cx, cy + dy * 5), fill=blend(ILLO, ac, 0.5))


def mapper(box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    return lambda u, v: (x0 + u * w, y0 + v * h)


def star4(draw, cx, cy, r, fill=None, outline=None):
    pts = [(cx, cy - r), (cx + r * 0.22, cy - r * 0.22), (cx + r, cy),
           (cx + r * 0.22, cy + r * 0.22), (cx, cy + r),
           (cx - r * 0.22, cy + r * 0.22), (cx - r, cy),
           (cx - r * 0.22, cy - r * 0.22)]
    draw.polygon(pts, fill=fill, outline=outline)


# ---------------------------------------------------------------- illustration: NATO
def draw_illo_nato(draw, box, ac=CYAN):
    illo_frame(draw, box, ac)
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = min(x1 - x0, y1 - y0) * 0.40
    draw.ellipse((cx - r * 1.10, cy - r * 1.10, cx + r * 1.10, cy + r * 1.10),
                 outline=blend(ILLO, ac, 0.30))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=blend(ILLO, ac, 0.70))
    for i in range(12):
        a = i * math.tau / 12 - math.pi / 2
        r0, r1 = r * 1.02, r * 1.09 if i % 3 else r * 1.16
        draw.line((cx + r0 * math.cos(a), cy + r0 * math.sin(a),
                   cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
                  fill=blend(ILLO, ac, 0.45 if i % 3 else 0.85))
    star4(draw, cx, cy, r * 0.94, fill=blend(ILLO, ac, 0.20), outline=ac)
    star4(draw, cx, cy, r * 0.46, fill=ac)
    for sx in (0.10, 0.90):
        draw.line((x0 + (x1 - x0) * sx, y0 + 12, x0 + (x1 - x0) * sx, y1 - 12),
                  fill=blend(ILLO, ac, 0.18))


# ---------------------------------------------------------------- illustration: jet
def draw_illo_jet(draw, box, ac=CYAN):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    body = P([(0.86, 0.50), (0.70, 0.455), (0.30, 0.465), (0.20, 0.50),
              (0.30, 0.535), (0.70, 0.545)])
    wing_u = P([(0.58, 0.475), (0.47, 0.20), (0.40, 0.20), (0.43, 0.475)])
    wing_l = P([(0.58, 0.525), (0.47, 0.80), (0.40, 0.80), (0.43, 0.525)])
    tail_u = P([(0.28, 0.470), (0.22, 0.33), (0.17, 0.33), (0.19, 0.472)])
    tail_l = P([(0.28, 0.530), (0.22, 0.67), (0.17, 0.67), (0.19, 0.528)])
    for shape in (wing_u, wing_l):
        draw.polygon(shape, fill=blend(ILLO, ac, 0.16), outline=blend(ILLO, ac, 0.75))
    for shape in (tail_u, tail_l):
        draw.polygon(shape, fill=blend(ILLO, ac, 0.22), outline=blend(ILLO, ac, 0.6))
    draw.polygon(body, fill=blend(ILLO, ac, 0.30), outline=ac)
    draw.line(P([(0.72, 0.50), (0.34, 0.50)]), fill=blend(ILLO, ac, 0.6))
    draw.arc(P([(0.58, 0.455), (0.74, 0.545)]), 90, 270, fill=INK, width=1)
    for i in range(4):
        x = 0.17 - i * 0.045
        draw.line(P([(x, 0.47 + i * 0.005), (x - 0.03, 0.47 + i * 0.005)]),
                  fill=blend(ILLO, ac, 0.5))
        draw.line(P([(x, 0.53 - i * 0.005), (x - 0.03, 0.53 - i * 0.005)]),
                  fill=blend(ILLO, ac, 0.5))
    draw.ellipse((m(0.86, 0.485)[0], m(0.86, 0.485)[1],
                  m(0.885, 0.515)[0], m(0.885, 0.515)[1]), outline=ac)


# ---------------------------------------------------------------- illustration: F1
def draw_illo_f1(draw, box, ac=RED):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    for wx in (0.31, 0.71):
        for rr, col in ((0.175, blend(ILLO, ac, 0.55)), (0.115, ILLO), (0.045, ac)):
            cx, cy = m(wx, 0.76)
            rr_px = rr * (box[3] - box[1])
            draw.ellipse((cx - rr_px, cy - rr_px, cx + rr_px, cy + rr_px),
                         fill=col if rr > 0.05 else None, outline=col, width=1)
        cx, cy = m(wx, 0.76)
        r_in = 0.045 * (box[3] - box[1])
        draw.ellipse((cx - r_in, cy - r_in, cx + r_in, cy + r_in),
                     fill=blend(ILLO, ac, 0.35), outline=ac)
    chassis = P([(0.14, 0.68), (0.22, 0.60), (0.42, 0.58), (0.50, 0.46),
                 (0.60, 0.46), (0.64, 0.58), (0.86, 0.62), (0.90, 0.68)])
    draw.polygon(chassis, fill=blend(ILLO, ac, 0.22), outline=ac)
    draw.line(P([(0.58, 0.47), (0.66, 0.47)]), fill=INK)
    draw.arc(P([(0.51, 0.40), (0.65, 0.55)]), 180, 360, fill=blend(ILLO, ac, 0.8))
    draw.line(P([(0.83, 0.40), (0.86, 0.62)]), fill=ac, width=2)
    draw.line(P([(0.78, 0.40), (0.90, 0.40)]), fill=ac, width=2)
    draw.line(P([(0.80, 0.40), (0.80, 0.44)]), fill=ac)
    draw.line(P([(0.88, 0.40), (0.88, 0.44)]), fill=ac)
    draw.line(P([(0.10, 0.70), (0.20, 0.70)]), fill=blend(ILLO, ac, 0.8), width=2)
    for i in range(3):
        y = 0.50 + i * 0.055
        draw.line(P([(0.04, y), (0.12, y)]), fill=blend(ILLO, ac, 0.45))


# ---------------------------------------------------------------- illustration: tanker
def draw_illo_tanker(draw, box, ac=AMBER):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    hull = P([(0.06, 0.60), (0.10, 0.76), (0.84, 0.76), (0.94, 0.62), (0.90, 0.60)])
    draw.polygon(hull, fill=blend(ILLO, ac, 0.16), outline=blend(ILLO, ac, 0.85))
    draw.line(P([(0.08, 0.66), (0.92, 0.66)]), fill=blend(ILLO, ac, 0.4))
    for i in range(3):
        x = 0.16 + i * 0.16
        draw.ellipse((m(x, 0.575)[0] - 2, m(x, 0.575)[1] - 2,
                      m(x, 0.575)[0] + 2, m(x, 0.575)[1] + 2),
                     outline=ac)
        draw.line(P([(x, 0.55), (x + 0.02, 0.60)]), fill=blend(ILLO, ac, 0.8))
    draw.line(P([(0.14, 0.55), (0.62, 0.55)]), fill=blend(ILLO, ac, 0.7))
    for x in (0.20, 0.30, 0.40, 0.50):
        draw.line(P([(x, 0.55), (x, 0.59)]), fill=blend(ILLO, ac, 0.5))
    superbox = P([(0.68, 0.42), (0.84, 0.42), (0.84, 0.60), (0.68, 0.60)])
    draw.polygon(superbox, fill=blend(ILLO, ac, 0.30), outline=ac)
    for i in range(3):
        y = 0.46 + i * 0.05
        draw.line(P([(0.70, y), (0.82, y)]), fill=blend(ILLO, ac, 0.85))
    draw.line(P([(0.74, 0.42), (0.74, 0.31)]), fill=ac, width=2)
    draw.line(P([(0.72, 0.31), (0.76, 0.31)]), fill=ac, width=2)
    for i in range(5):
        x = 0.14 + i * 0.17
        draw.line(P([(x, 0.82), (x + 0.07, 0.82)]), fill=blend(ILLO, ac, 0.35))


# ---------------------------------------------------------------- illustration: COP31
def draw_illo_cop31(draw, box, ac=GREEN):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    cx, cy = m(0.34, 0.50)
    r = min(box[2] - box[0], box[3] - box[1]) * 0.36
    draw.ellipse((cx - r, cy - r, cx + r, cy + r),
                 fill=blend(ILLO, ac, 0.10), outline=ac)
    for k in (-0.55, 0.0, 0.55):
        draw.arc((cx - r, cy - r * abs(k) - 0.1, cx + r, cy + r * abs(k) + 0.1),
                 0, 360, fill=blend(ILLO, ac, 0.55))
    draw.arc((cx - r * 0.55, cy - r, cx + r * 0.55, cy + r), 0, 360,
             fill=blend(ILLO, ac, 0.45))
    draw.arc((cx - r, cy - r, cx + r, cy + r), 0, 360, fill=ac)
    leaf = P([(0.62, 0.70), (0.60, 0.52), (0.68, 0.36), (0.80, 0.32),
              (0.82, 0.46), (0.76, 0.62)])
    draw.polygon(leaf, fill=blend(ILLO, ac, 0.25), outline=ac)
    draw.line(P([(0.62, 0.70), (0.79, 0.38)]), fill=ac)
    for i in range(3):
        x = 0.72 + i * 0.075
        h = 0.10 + i * 0.085
        draw.rectangle((m(x, 0.78 - h)[0], m(x, 0.78 - h)[1],
                        m(x + 0.045, 0.78)[0], m(x, 0.78)[1]),
                       fill=blend(ILLO, ac, 0.35 + i * 0.15))
    draw.line(P([(0.66, 0.78), (0.94, 0.78)]), fill=blend(ILLO, ac, 0.6))


# ---------------------------------------------------------------- illustration: Brexit
def draw_illo_brexit(draw, box, ac=VIOLET):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    cx, cy = m(0.27, 0.50)
    rx, ry = (box[2] - box[0]) * 0.155, (box[3] - box[1]) * 0.36
    for i in range(12):
        if i in (10, 11):
            continue
        a = -math.pi / 2 + i * math.tau / 12
        star4(draw, cx + rx * math.cos(a), cy + ry * math.sin(a), 3.4,
              fill=blend(ILLO, ac, 0.55), outline=ac)
    draw.arc((cx - rx, cy - ry, cx + rx, cy + ry), -70, 200,
             fill=blend(ILLO, ac, 0.3))
    dashed(draw, m(0.53, 0.12), m(0.55, 0.88), blend(ILLO, ac, 0.55), 1, 9)
    draw.line(P([(0.58, 0.38), (0.88, 0.38)]), fill=ac, width=2)
    draw.polygon(P([(0.88, 0.38), (0.83, 0.33), (0.83, 0.43)]), fill=ac)
    draw.line(P([(0.58, 0.62), (0.88, 0.62)]), fill=blend(ILLO, ac, 0.6), width=2)
    draw.polygon(P([(0.90, 0.62), (0.85, 0.57), (0.85, 0.67)]),
                 fill=blend(ILLO, ac, 0.6))
    for i in range(3):
        y = 0.44 + i * 0.02
        draw.line(P([(0.60, y), (0.74, y)]), fill=blend(ILLO, ac, 0.35))


# ---------------------------------------------------------------- illustration: oil
def draw_illo_oil(draw, box, ac=AMBER):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    draw.line(P([(0.04, 0.84), (0.96, 0.84)]), fill=blend(ILLO, ac, 0.55))
    draw.polygon(P([(0.40, 0.84), (0.56, 0.84), (0.49, 0.46)]),
                 fill=blend(ILLO, ac, 0.20), outline=blend(ILLO, ac, 0.8))
    draw.line(P([(0.48, 0.70), (0.56, 0.84)]), fill=blend(ILLO, ac, 0.6))
    draw.line(P([(0.50, 0.62), (0.41, 0.84)]), fill=blend(ILLO, ac, 0.6))
    draw.polygon(P([(0.18, 0.34), (0.66, 0.44), (0.66, 0.50), (0.18, 0.40)]),
                 fill=blend(ILLO, ac, 0.38), outline=ac)
    draw.line(P([(0.48, 0.46), (0.66, 0.47)]), fill=blend(ILLO, ac, 0.8))
    draw.arc(P([(0.12, 0.28), (0.26, 0.41)]), 150, 340, fill=ac)
    draw.line(P([(0.19, 0.38), (0.19, 0.84)]), fill=ac)
    draw.line(P([(0.16, 0.84), (0.22, 0.84)]), fill=ac, width=2)
    draw.line(P([(0.17, 0.78), (0.21, 0.78)]), fill=blend(ILLO, ac, 0.8))
    cx, cy = m(0.70, 0.52)
    r = 0.075 * (box[3] - box[1])
    draw.ellipse((cx - r, cy - r, cx + r, cy + r),
                 fill=blend(ILLO, ac, 0.25), outline=ac)
    draw.ellipse((cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35),
                 outline=blend(ILLO, ac, 0.8))
    draw.line(P([(0.70, 0.60), (0.70, 0.72)]), fill=blend(ILLO, ac, 0.7))
    draw.polygon(P([(0.86, 0.84), (0.86, 0.52), (0.95, 0.52), (0.95, 0.84)]),
                 fill=blend(ILLO, ac, 0.14), outline=blend(ILLO, ac, 0.7))
    for y in (0.61, 0.70, 0.79):
        draw.line(P([(0.87, y), (0.94, y)]), fill=blend(ILLO, ac, 0.5))


# ---------------------------------------------------------------- illustration: AI
def draw_illo_ai(draw, box, ac=CYAN):
    illo_frame(draw, box, ac)
    m = mapper(box)
    layers = [(0.16, 4), (0.42, 5), (0.68, 4), (0.90, 3)]
    pts = []
    for x, n in layers:
        ys = [0.20 + i * (0.60 / (n - 1)) for i in range(n)]
        pts.append([m(x, y) for y in ys])
    for li in range(len(pts) - 1):
        for a in pts[li]:
            for b in pts[li + 1]:
                draw.line((a, b), fill=blend(ILLO, ac, 0.18))
    path = [pts[0][1], pts[1][2], pts[2][1], pts[3][1]]
    for i in range(len(path) - 1):
        draw.line((path[i], path[i + 1]), fill=blend(ILLO, ac, 0.85), width=2)
    for li, layer in enumerate(pts):
        for node in layer:
            on_path = any(abs(node[0] - p[0]) < 0.5 and abs(node[1] - p[1]) < 0.5
                          for p in path)
            r = 4.2 if li in (1, 2) else 3.4
            draw.ellipse((node[0] - r, node[1] - r, node[0] + r, node[1] + r),
                         fill=ac if on_path else blend(ILLO, ac, 0.35),
                         outline=ac if on_path else blend(ILLO, ac, 0.7))
    draw.line((m(0.12, 0.12), m(0.94, 0.12)), fill=blend(ILLO, ac, 0.16))


# ---------------------------------------------------------------- illustration: space
def draw_illo_space(draw, box, ac=VIOLET):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    cx, cy = m(0.50, 0.52)
    rx, ry = (box[2] - box[0]) * 0.40, (box[3] - box[1]) * 0.30
    draw.line(ellipse_pts(cx, cy, rx, ry), fill=blend(ILLO, ac, 0.28))
    draw.line(ellipse_pts(cx, cy, rx * 0.72, ry * 0.72), fill=blend(ILLO, ac, 0.18))
    for sx, sy in ((0.10, 0.16), (0.90, 0.22), (0.80, 0.78), (0.20, 0.72), (0.68, 0.10)):
        px, py = m(sx, sy)
        draw.line((px - 2, py, px + 2, py), fill=blend(ILLO, ac, 0.6))
        draw.line((px, py - 2, px, py + 2), fill=blend(ILLO, ac, 0.6))
    body = P([(0.50, 0.10), (0.56, 0.28), (0.56, 0.62), (0.44, 0.62), (0.44, 0.28)])
    draw.polygon(body, fill=blend(ILLO, ac, 0.28), outline=ac)
    for side in (-1, 1):
        fin = P([(0.50 + side * 0.06, 0.50), (0.50 + side * 0.11, 0.68),
                 (0.50 + side * 0.06, 0.63)])
        draw.polygon(fin, fill=blend(ILLO, ac, 0.40), outline=ac)
    draw.line(P([(0.44, 0.55), (0.56, 0.55)]), fill=blend(ILLO, ac, 0.8))
    draw.ellipse((m(0.47, 0.32)[0], m(0.47, 0.32)[1],
                  m(0.53, 0.41)[0], m(0.53, 0.41)[1]), outline=ac)
    draw.polygon(P([(0.455, 0.62), (0.545, 0.62), (0.50, 0.82)]),
                 fill=blend(ILLO, ac, 0.18), outline=blend(ILLO, ac, 0.6))
    draw.polygon(P([(0.475, 0.62), (0.525, 0.62), (0.50, 0.74)]), fill=ac)


# ---------------------------------------------------------------- illustration: shipping
def draw_illo_shipping(draw, box, ac=CYAN):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    draw.polygon(P([(0.05, 0.58), (0.09, 0.74), (0.86, 0.74), (0.95, 0.60), (0.91, 0.58)]),
                 fill=blend(ILLO, ac, 0.14), outline=blend(ILLO, ac, 0.8))
    draw.line(P([(0.06, 0.66), (0.93, 0.66)]), fill=blend(ILLO, ac, 0.45))
    draw.line(P([(0.07, 0.58), (0.90, 0.58)]), fill=blend(ILLO, ac, 0.9))
    cols, cw = 7, 0.075
    for row, y in ((0, 0.46), (1, 0.36)):
        for c in range(cols):
            x = 0.22 + c * cw
            draw.rectangle((m(x, y)[0], m(x, y)[1],
                            m(x + cw * 0.88, y + 0.08)[0], m(x + cw * 0.88, y + 0.08)[1]),
                           fill=blend(ILLO, ac, 0.22 + 0.06 * ((c + row) % 3)),
                           outline=blend(ILLO, ac, 0.55))
    draw.polygon(P([(0.80, 0.36), (0.90, 0.36), (0.90, 0.58), (0.80, 0.58)]),
                 fill=blend(ILLO, ac, 0.30), outline=ac)
    draw.line(P([(0.80, 0.44), (0.90, 0.44)]), fill=blend(ILLO, ac, 0.9))
    draw.line(P([(0.84, 0.36), (0.84, 0.26), (0.88, 0.26), (0.88, 0.36)]),
              fill=ac)
    for i in range(4):
        x = 0.12 + i * 0.22
        draw.arc(P([(x, 0.78), (x + 0.22, 0.92)]), 200, 340,
                 fill=blend(ILLO, ac, 0.30))


# ---------------------------------------------------------------- illustration: solar
def draw_illo_solar(draw, box, ac=GREEN):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    cx, cy = m(0.13, 0.24)
    r = 0.11 * (box[3] - box[1])
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=blend(ILLO, ac, 0.45), outline=ac)
    for i in range(8):
        a = i * math.tau / 8
        draw.line((cx + r * 1.35 * math.cos(a), cy + r * 1.35 * math.sin(a),
                   cx + r * 1.85 * math.cos(a), cy + r * 1.85 * math.sin(a)),
                  fill=blend(ILLO, ac, 0.6))
    draw.line(P([(0.04, 0.88), (0.96, 0.88)]), fill=blend(ILLO, ac, 0.5))
    for row, (y0, y1, sh) in enumerate(((0.30, 0.50, 0.0), (0.56, 0.80, 0.03))):
        for c in range(3):
            x0 = 0.26 + c * 0.235 + sh
            x1 = x0 + 0.20
            quad = P([(x0, y1), (x0 + 0.03, y0), (x1 + 0.03, y0), (x1, y1)])
            draw.polygon(quad, fill=blend(ILLO, ac, 0.16 + 0.06 * row), outline=ac)
            for k in (1, 2):
                f = k / 3
                draw.line(P([(x0 + 0.03 * f, y1 - (y1 - y0) * 0.0),
                             (x0 + 0.03 * f + 0.02, y0)]), fill=blend(ILLO, ac, 0.45))
            draw.line(P([(x0 + 0.035, y0 + (y1 - y0) * 0.5),
                         (x1 + 0.005, y0 + (y1 - y0) * 0.5)]),
                      fill=blend(ILLO, ac, 0.45))
            mx = (x0 + x1) / 2 + 0.015
            draw.line(P([(mx, y1), (mx, 0.88)]), fill=blend(ILLO, ac, 0.55))


# ---------------------------------------------------------------- illustration: finance
def draw_illo_finance(draw, box, ac=AMBER):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    d = draw
    draw.line(P([(0.08, 0.16), (0.08, 0.84)]), fill=blend(ILLO, ac, 0.45))
    draw.line(P([(0.08, 0.84), (0.94, 0.84)]), fill=blend(ILLO, ac, 0.45))
    for i in range(1, 4):
        y = 0.16 + i * 0.17
        d.line(P([(0.08, y), (0.94, y)]), fill=blend(ILLO, ac, 0.10))
    candles = [(0.18, 0.60, 0.40, True), (0.29, 0.52, 0.30, True),
               (0.40, 0.46, 0.56, False), (0.51, 0.38, 0.30, True),
               (0.62, 0.28, 0.44, False), (0.73, 0.32, 0.18, True),
               (0.84, 0.20, 0.14, True)]
    for x, body_top, body_bot, up in candles:
        col = GREEN if up else RED
        mid = (body_top + body_bot) / 2
        d.line(P([(x + 0.02, body_top - 0.05), (x + 0.02, body_bot + 0.05)]), fill=col)
        d.rectangle((m(x, body_top)[0], m(x, body_top)[1],
                     m(x + 0.05, max(body_bot, body_top + 0.02))[0],
                     m(x + 0.05, max(body_bot, body_top + 0.02))[1]),
                    fill=blend(ILLO, col, 0.55), outline=col)
    trend = [(0.16, 0.66), (0.28, 0.55), (0.40, 0.59), (0.52, 0.42),
             (0.64, 0.46), (0.76, 0.30), (0.90, 0.22)]
    d.line([m(u, v) for u, v in trend], fill=ac, width=2)
    dashed(d, m(0.76, 0.30), m(0.94, 0.14), blend(ILLO, ac, 0.7))
    exh, ey = m(0.90, 0.22)
    d.ellipse((exh - 3, ey - 3, exh + 3, ey + 3), fill=ac)
    for i in range(3):
        y = 0.24 + i * 0.17
        d.line(P([(0.045, y), (0.08, y)]), fill=blend(ILLO, ac, 0.4))


# ---------------------------------------------------------------- illustration: airlift
def draw_illo_airlift(draw, box, ac=RED):
    illo_frame(draw, box, ac)
    m = mapper(box)
    P = lambda pts: [m(u, v) for u, v in pts]
    fus = P([(0.08, 0.24), (0.24, 0.15), (0.66, 0.15), (0.84, 0.22),
             (0.90, 0.26), (0.88, 0.31), (0.30, 0.31), (0.10, 0.30)])
    draw.polygon(fus, fill=blend(ILLO, ac, 0.26), outline=ac)
    draw.polygon(P([(0.10, 0.24), (0.16, 0.05), (0.23, 0.05), (0.27, 0.24)]),
                 fill=blend(ILLO, ac, 0.34), outline=ac)
    draw.polygon(P([(0.34, 0.31), (0.44, 0.40), (0.54, 0.40), (0.56, 0.31)]),
                 fill=blend(ILLO, ac, 0.18), outline=blend(ILLO, ac, 0.75))
    for i in range(4):
        x = 0.58 + i * 0.045
        draw.ellipse((m(x, 0.215)[0] - 1.3, m(x, 0.215)[1] - 1.3,
                      m(x, 0.215)[0] + 1.3, m(x, 0.215)[1] + 1.3), fill=INK)
    draw.line(P([(0.88, 0.31), (0.92, 0.36)]), fill=ac)
    for i, x in enumerate((0.24, 0.48, 0.72)):
        dashed(draw, m(x, 0.40), m(x, 0.52), blend(ILLO, ac, 0.45), 1, 4)
        cx, cy = m(x, 0.58)
        draw.arc((cx - 0.055 * (box[2] - box[0]), cy - 0.07 * (box[3] - box[1]),
                  cx + 0.055 * (box[2] - box[0]), cy + 0.07 * (box[3] - box[1])),
                 180, 360, fill=ac, width=2)
        for side in (-1, 1):
            draw.line((cx + side * 0.052 * (box[2] - box[0]), cy,
                       cx + side * 0.030 * (box[2] - box[0]), cy + 0.10 * (box[3] - box[1])),
                      fill=blend(ILLO, ac, 0.6))
        bx, by = m(x, 0.72)
        draw.rectangle((bx - 7, by, bx + 7, by + 9),
                       fill=blend(ILLO, ac, 0.20), outline=ac)
        draw.line((bx - 7, by + 3, bx + 7, by + 3), fill=blend(ILLO, ac, 0.5))
    draw.line(P([(0.06, 0.90), (0.94, 0.90)]), fill=blend(ILLO, ac, 0.55))


# ---------------------------------------------------------------- content
CARDS = [
    ("STRATEGY", "NATO Recalibrates The Eastern Flank", "31",
     "Ministers endorse a new forward-presence cycle from Tallinn to Bucharest.",
     CYAN, draw_illo_nato),
    ("DEFENCE", "Sixth-Generation Fighter Clears Trials", "2031",
     "Prototype completes its first full sensor-fusion sortie over the North Sea.",
     CYAN, draw_illo_jet),
    ("MOTORSPORT", "The Title Fight Enters Its Final Act", "3",
     "Three rounds remain and four drivers sit inside a single win of the crown.",
     RED, draw_illo_f1),
    ("ENERGY", "Tanker Rates Spike As Routes Shift", "+38%",
     "Longer voyages and tighter tonnage push charter costs to a two-year high.",
     AMBER, draw_illo_tanker),
    ("CLIMATE", "COP31 Seals The Loss-And-Damage Ledger", "$120bn",
     "Delegates agree a first replenishment round and a five-year review clock.",
     GREEN, draw_illo_cop31),
    ("TRADE", "The Brexit Review Opens A New Chapter", "2026",
     "Brussels and London table a slimmed customs protocol for the Irish Sea.",
     VIOLET, draw_illo_brexit),
    ("COMMODITIES", "Oil Holds Above $80 On Supply Cuts", "$82",
     "Producers extend voluntary curbs while inventories draw for a fourth week.",
     AMBER, draw_illo_oil),
    ("TECHNOLOGY", "AI Moves From The Demo To The Desk", "42%",
     "Firms report routine model use in drafting, triage and code review.",
     CYAN, draw_illo_ai),
    ("SCIENCE", "Crewed Test Flight Slips To Spring", "Q2",
     "Engineers replace a pressurisation valve and requalify the upper stage.",
     VIOLET, draw_illo_space),
    ("LOGISTICS", "Red Sea Rerouting Stretches Fleets", "14d",
     "Cape diversions add two weeks per rotation and soak up spare capacity.",
     CYAN, draw_illo_shipping),
    ("ENERGY", "Solar Additions Break Another Record", "512GW",
     "Utility-scale builds lead a year of falling module prices and grid queues.",
     GREEN, draw_illo_solar),
    ("MARKETS", "Central Banks Signal A Longer Plateau", "4.25%",
     "Hold guidance extends into the new year as services inflation cools slowly.",
     AMBER, draw_illo_finance),
    ("AIRLIFT", "The Humanitarian Airlift Reaches The Interior", "218",
     "Sorties deliver food and medical kits to valleys cut off by the monsoon.",
     RED, draw_illo_airlift),
]

NUMBERS = [
    ("THEATRES MONITORED", "13", "+2 this week", CYAN),
    ("BULLETINS VERIFIED", "36", "all sources", GREEN),
    ("MARKETS TRACKED", "24", "-0.4% avg", AMBER),
    ("SATELLITES AUDITED", "6", "100% pass", VIOLET),
]


# ---------------------------------------------------------------- header
def draw_header(draw):
    mast = "THE WORLD CHRONICLE"
    size = 48
    f = font("serif_bold", size)
    while tw(draw, mast, f) > 700 and size > 30:
        size -= 2
        f = font("serif_bold", size)
    t = draw.textbbox((0, 0), mast, font=f)
    draw.text((M, 14 - t[1]), mast, font=f, fill=INK)

    tracked(draw, M, 66, "ILLUSTRATED ATLAS EDITION \u00b7 THIRTEEN PROCEDURAL PLATES",
            font("sans_bold", 7.5), MUTED, 0.9)
    tracked(draw, M, 78, "VOL. XXVI NO. 326 \u00b7 SATURDAY, 21 NOVEMBER 2026 \u00b7 NIGHT FINAL",
            font("sans", 7), DIM, 0.7)

    box = (W - M - 214, 14, W - M, 82)
    draw.rounded_rectangle(box, radius=3, fill=(15, 34, 52), outline=CYAN)
    tracked(draw, box[0] + 11, box[1] + 9, "GLOBAL UTC SUMMARY", font("sans_bold", 8),
            CYAN, 0.6)
    draw.text((box[0] + 11, box[1] + 24), "22:00 UTC", font=font("serif_bold", 22), fill=INK)
    rule(draw, box[0] + 11, box[1] + 51, box[2] - 11, RULE)
    tracked(draw, box[0] + 11, box[1] + 56, "36 BULLETINS \u00b7 6 CONTINENTS",
            font("sans", 7), MUTED, 0.4)

    rule(draw, M, 92, W - M, AMBER, 2)
    rule(draw, M, 95, W - M, RULE, 1)


# ---------------------------------------------------------------- numbers strip
def draw_numbers_strip(draw, box, items):
    x0, y0, x1, y1 = box
    panel(draw, box, PANEL_ALT, RULE, 3)
    n = len(items)
    cell = (x1 - x0) / n
    for i, (label, value, note, col) in enumerate(items):
        cx = x0 + i * cell
        if i:
            draw.line((cx, y0 + 8, cx, y1 - 8), fill=RULE)
        pad = 14
        tracked(draw, cx + pad, y0 + 9, label, font("sans_bold", 6.5), DIM, 0.7)
        fv = font("serif_bold", 19)
        draw.text((cx + pad, y0 + 18), value, font=fv, fill=col)
        vx = cx + pad + tw(draw, value, fv) + 8
        draw.text((vx, y0 + 26), note, font=font("sans", 7), fill=MUTED)


# ---------------------------------------------------------------- card
def draw_card(draw, box, idx, card, feature=False):
    kicker, title, stat, caption, ac, illo = card
    x0, y0, x1, y1 = box
    panel(draw, box, PANEL, RULE, 4, ac if feature else None)

    if feature:
        split = x0 + (x1 - x0) * 0.54
        ibox = (split + 6, y0 + 8, x1 - 8, y1 - 8)
        illo(draw, ibox, ac)
        tx, tw_ = x0 + 16, split - x0 - 32
        tracked(draw, tx, y0 + 13, f"{idx:02d} / {kicker}", font("sans_bold", 7), ac, 0.8)
        ft = font("serif_bold", 19)
        ty = y0 + 28
        for ln in fit_lines(draw, title, ft, tw_, 2):
            draw.text((tx, ty), ln, font=ft, fill=INK)
            ty += 21
        fcap = font("serif", 9.5)
        ty += 3
        for ln in fit_lines(draw, caption, fcap, tw_, 2):
            draw.text((tx, ty), ln, font=fcap, fill=MUTED)
            ty += 11
        fs = font("serif_bold", 22)
        draw.text((tx, y1 - 33), stat, font=fs, fill=ac)
        draw.text((tx + tw(draw, stat, fs) + 6, y1 - 26), "SORTIES VERIFIED",
                  font=font("sans_bold", 6.5), fill=DIM)
        return

    ibox = (x0 + 6, y0 + 6, x1 - 6, y0 + 84)
    illo(draw, ibox, ac)

    row_y = y0 + 92
    draw.rounded_rectangle((x0 + 8, row_y - 1, x0 + 25, row_y + 11), radius=2, fill=ac)
    draw.text((x0 + 11, row_y + 1), f"{idx:02d}", font=font("sans_bold", 7), fill=(14, 20, 30))
    tracked(draw, x0 + 30, row_y + 1, kicker, font("sans_bold", 6.5), DIM, 0.7)

    fs = font("sans_bold", 9)
    draw.text((x1 - 8 - tw(draw, stat, fs), row_y), stat, font=fs, fill=ac)

    ft = font("serif_bold", 11)
    ty = row_y + 15
    for ln in fit_lines(draw, title, ft, x1 - x0 - 18, 2):
        draw.text((x0 + 8, ty), ln, font=ft, fill=INK)
        ty += 12

    fc = font("sans", 7)
    cy = y1 - 21
    for ln in fit_lines(draw, caption, fc, x1 - x0 - 16, 2):
        draw.text((x0 + 8, cy), ln, font=fc, fill=MUTED)
        cy += 9


# ---------------------------------------------------------------- map
LAND = [
    # North America
    [(0.04, 0.22), (0.12, 0.13), (0.22, 0.15), (0.27, 0.23), (0.24, 0.33),
     (0.19, 0.36), (0.17, 0.47), (0.13, 0.41), (0.10, 0.31), (0.05, 0.27)],
    # Greenland
    [(0.29, 0.06), (0.355, 0.08), (0.34, 0.17), (0.295, 0.18)],
    # South America
    [(0.21, 0.50), (0.285, 0.48), (0.315, 0.56), (0.285, 0.70),
     (0.24, 0.79), (0.205, 0.65), (0.195, 0.55)],
    # Europe
    [(0.43, 0.20), (0.50, 0.17), (0.545, 0.22), (0.525, 0.29),
     (0.462, 0.30), (0.428, 0.26)],
    # Africa
    [(0.44, 0.34), (0.525, 0.32), (0.575, 0.40), (0.552, 0.53),
     (0.505, 0.64), (0.462, 0.59), (0.44, 0.46)],
    # Asia
    [(0.545, 0.16), (0.65, 0.11), (0.775, 0.15), (0.845, 0.24),
     (0.80, 0.33), (0.715, 0.34), (0.665, 0.41), (0.60, 0.36), (0.56, 0.26)],
    # India
    [(0.665, 0.36), (0.705, 0.38), (0.695, 0.47), (0.663, 0.44)],
    # Indonesia
    [(0.755, 0.44), (0.825, 0.46), (0.805, 0.52), (0.74, 0.50)],
    # Australia
    [(0.795, 0.62), (0.885, 0.60), (0.925, 0.68), (0.862, 0.74), (0.80, 0.70)],
]

HOTSPOTS = [
    ("WASHINGTON", 0.175, 0.275, "right"),
    ("BRUSSELS", 0.487, 0.225, "right"),
    ("RIYADH", 0.575, 0.395, "right"),
    ("NAIROBI", 0.523, 0.535, "right"),
    ("TAIPEI", 0.735, 0.335, "left"),
    ("CANBERRA", 0.868, 0.688, "left"),
]


def draw_map(draw, box, hotspots):
    x0, y0, x1, y1 = box
    panel(draw, box, PANEL_ALT, RULE, 4, CYAN)
    tracked(draw, x0 + 12, y0 + 10, "GLOBAL THEATRE MAP", font("sans_bold", 8), INK, 0.7)
    tracked(draw, x1 - 12 - tracked_width(draw, "21 NOV", font("sans", 7), 0.3),
            y0 + 10, "21 NOV", font("sans", 7), DIM, 0.3)

    mx0, my0 = x0 + 14, y0 + 30
    mx1, my1 = x1 - 14, y1 - 26
    mw, mh = mx1 - mx0, my1 - my0

    for i in range(1, 7):
        gx = mx0 + mw * i / 7
        draw.line((gx, my0, gx, my1), fill=blend(PANEL_ALT, RULE, 0.4))
    for i in range(1, 4):
        gy = my0 + mh * i / 4
        draw.line((mx0, gy, mx1, gy), fill=blend(PANEL_ALT, RULE, 0.4))
    draw.rectangle((mx0, my0, mx1, my1), outline=RULE)

    for poly in LAND:
        pts = [(mx0 + u * mw, my0 + v * mh) for u, v in poly]
        draw.polygon(pts, fill=blend(PANEL_ALT, CYAN, 0.16), outline=blend(PANEL_ALT, CYAN, 0.55))

    # equatorial belt
    dashed(draw, (mx0, my0 + mh * 0.55), (mx1, my0 + mh * 0.55),
           blend(PANEL_ALT, AMBER, 0.35), 1, 10)

    for label, u, v, side in hotspots:
        px, py = mx0 + u * mw, my0 + v * mh
        draw.ellipse((px - 7, py - 7, px + 7, py + 7), outline=blend(PANEL_ALT, RED, 0.45))
        draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=RED)
        draw.line((px - 11, py, px - 7, py), fill=RED)
        draw.line((px + 7, py, px + 11, py), fill=RED)
        f = font("sans_bold", 6)
        lx = px - 13 - tw(draw, label, f) if side == "right" else px + 13
        draw.text((lx, py - 7), label, font=f, fill=INK)

    tracked(draw, x0 + 12, y1 - 17, "SIX AUDITED THEATRES \u00b7 LIVE FEED", font("sans", 6.5),
            DIM, 0.4)


# ---------------------------------------------------------------- footer
def draw_footer(draw, y):
    rule(draw, M, y - 12, W - M, AMBER, 1)
    tracked(draw, M, y, "THE WORLD CHRONICLE \u00b7 ILLUSTRATED ATLAS EDITION \u00b7 13 PLATES \u00b7 36 BULLETINS \u00b7 6 CONTINENTS",
            font("sans_bold", 7), MUTED, 0.4)
    right = "PROCEDURAL VECTOR \u00b7 v3"
    f = font("sans_bold", 7)
    tracked(draw, W - M - tracked_width(draw, right, f, 0.4), y, right, f, AMBER, 0.4)


# ---------------------------------------------------------------- render
def main():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw_header(draw)
    draw_numbers_strip(draw, (M, 104, W - M, 150), NUMBERS)

    # cards: 3 columns, four rows, plus a wide feature plate
    gap = 8
    ax0, ax1 = M, 700
    cw = (ax1 - ax0 - 2 * gap) / 3
    top = 162
    ch, fh = 155, 136

    positions = []
    for row in range(4):
        for col in range(3):
            x0 = ax0 + col * (cw + gap)
            y0 = top + row * (ch + gap)
            positions.append((x0, y0, x0 + cw, y0 + ch))

    for i, (card, box) in enumerate(zip(CARDS[:12], positions), start=1):
        draw_card(draw, box, i, card)

    feature_y = top + 4 * (ch + gap)
    draw_card(draw, (ax0, feature_y, ax1, feature_y + fh), 13, CARDS[12], feature=True)

    # sidebar: map + edition index
    draw_map(draw, (ax1 + gap, top, W - M, top + 300), HOTSPOTS)

    ix0, iy0, ix1 = ax1 + gap, top + 308, W - M
    panel(draw, (ix0, iy0, ix1, feature_y + fh), PANEL, RULE, 4)
    tracked(draw, ix0 + 12, iy0 + 9, "IN THIS EDITION", font("sans_bold", 8), INK, 0.7)
    rule(draw, ix0 + 12, iy0 + 22, ix1 - 12, RULE)

    row_h = (feature_y + fh - (iy0 + 26) - 10) / 13
    for i, (kicker, title, stat, caption, ac, _) in enumerate(CARDS, start=1):
        ry = iy0 + 26 + (i - 1) * row_h
        draw.ellipse((ix0 + 12, ry + 4, ix0 + 17, ry + 9), fill=ac)
        draw.text((ix0 + 22, ry + 1), f"{i:02d}", font=font("sans_bold", 6.5), fill=DIM)
        draw.text((ix0 + 38, ry), ellipsize(draw, title, font("serif_bold", 8.5), ix1 - ix0 - 82),
                  font=font("serif_bold", 8.5), fill=INK)
        fs = font("sans_bold", 6.5)
        draw.text((ix1 - 12 - tw(draw, stat, fs), ry + 1), stat, font=fs, fill=ac)
        if i < 13:
            rule(draw, ix0 + 22, ry + row_h - 3, ix1 - 12, RULE_SOFT)

    draw_footer(draw, 1006)

    img.save(OUT, format="PNG", optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
