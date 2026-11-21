#!/usr/bin/env python3
"""Render the v2 edition of The World Chronicle broadsheet (1024x1024).

v1 was a one-shot render whose third column ran off the canvas and whose
body text was set below a legible size. v2 lays out from measured text:
every string is wrapped to its column width, fitted to a line budget, and
ellipsized rather than clipped, so nothing crosses the 1024px edge.
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W = H = 1024
M = 20
OUT = Path(__file__).resolve().parent / "entry.png"

# ---------------------------------------------------------------- palette
BG = (10, 16, 28)
PANEL = (16, 25, 41)
PANEL_ALT = (13, 21, 35)
INK = (233, 239, 248)
MUTED = (146, 163, 186)
DIM = (104, 120, 143)
AMBER = (232, 180, 74)
CYAN = (79, 195, 217)
RED = (226, 86, 74)
GREEN = (91, 191, 138)
VIOLET = (170, 140, 232)
RULE = (38, 52, 74)
RULE_SOFT = (28, 40, 58)

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


# ---------------------------------------------------------------- text
def tw(draw: ImageDraw.ImageDraw, text: str, f) -> float:
    return draw.textlength(text, font=f)


def wrap(draw, text: str, f, max_w: int) -> list[str]:
    """Greedy word wrap; a word longer than the column is hard-split."""
    words, lines, cur = text.split(), [], ""
    for word in words:
        cand = word if not cur else f"{cur} {word}"
        if tw(draw, cand, f) <= max_w:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        if tw(draw, word, f) <= max_w:
            cur = word
        else:
            chunk = ""
            for ch in word:
                if tw(draw, chunk + ch, f) <= max_w:
                    chunk += ch
                else:
                    lines.append(chunk)
                    chunk = ch
            cur = chunk
    if cur:
        lines.append(cur)
    return lines


def ellipsize(draw, text: str, f, max_w: int) -> str:
    if tw(draw, text, f) <= max_w:
        return text
    out = text
    while out and tw(draw, out + "\u2026", f) > max_w:
        out = out[:-1].rstrip()
    return out + "\u2026"


def fit_lines(draw, text: str, f, max_w: int, max_lines: int) -> list[str]:
    """Wrap into at most max_lines; last line is ellipsized, never clipped."""
    lines = wrap(draw, text, f, max_w)
    if len(lines) <= max_lines:
        return lines
    kept = lines[:max_lines]
    kept[-1] = ellipsize(draw, " ".join(kept[-1:] + lines[max_lines:]), f, max_w)
    return kept


def fit_font(draw, text: str, name: str, sizes: list[int], max_w: int,
             max_lines: int, max_h: int | None = None) -> tuple:
    """Pick the largest size whose wrapped lines fit width, count and height."""
    for size in sizes:
        f = font(name, size)
        lines = fit_lines(draw, text, f, max_w, max_lines)
        lh = int(size * 1.18)
        if max_h is not None and len(lines) * lh > max_h:
            continue
        if all(tw(draw, ln, f) <= max_w for ln in lines):
            return f, lines, lh
    f = font(name, sizes[-1])
    return f, fit_lines(draw, text, f, max_w, max_lines), int(sizes[-1] * 1.18)


def tracked(draw, x, y, text, f, fill, spacing=1.6, anchor_left=True):
    """Draw letter-spaced caps; returns the width used."""
    adv = sum(tw(draw, ch, f) + spacing for ch in text) - spacing
    cx = x if anchor_left else x - adv
    for ch in text:
        draw.text((cx, y), ch, font=f, fill=fill)
        cx += tw(draw, ch, f) + spacing
    return adv


# ---------------------------------------------------------------- chrome
def panel(draw, box, fill=PANEL, outline=RULE, radius=4, top_rule=None):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1)
    if top_rule:
        draw.rounded_rectangle((x0, y0, x1, y0 + 2), radius=1, fill=top_rule)


def rule(draw, x0, y, x1, color=RULE, width=1):
    draw.line([(x0, y), (x1, y)], fill=color, width=width)


# ---------------------------------------------------------------- content
TICKER = [
    ("BRENT", "$74.90", "+0.4%", GREEN),
    ("GOLD", "$2,704", "+0.6%", GREEN),
    ("S&P 500", "5,918", "-0.1%", RED),
    ("NIKKEI", "38,760", "+0.3%", GREEN),
    ("EUR/USD", "1.054", "-0.2%", RED),
    ("US 10Y", "4.42%", "+2bp", RED),
    ("BTC", "$92,450", "+1.8%", GREEN),
    ("GLOBAL CO\u2082", "424.1 ppm", "+0.3", AMBER),
]

SECTIONS = [
    ("EUROPE & CENTRAL EURASIA", AMBER, [
        ("NATO-Russia Protocol Signed",
         "Allied command confirms defense and de-escalation posture as Baltic air policing expands."),
        ("Poland Deploys Patriot Air Defense Units",
         "Air defense command activates 24/7 radar watch across Lublin and Podkarpackie border districts."),
        ("EU Advances \u20ac150B Defense Loan Facility",
         "Brussels approves an emergency funding pool to secure regional ammunition and air-shield supply."),
        ("Ukraine Grid Restored After Kh-101 Strikes",
         "Emergency repairs restore 92% of power to western regions within 36 hours of the barrage."),
        ("UK-EU Security & Energy Compact Inked",
         "London and Brussels formalize a pact on North Sea offshore wind and infrastructure protection."),
        ("Baltic Undersea Cable Surveillance Tripled",
         "Joint maritime patrols begin round-the-clock watch over seabed energy and data infrastructure."),
    ]),
    ("MIDDLE EAST & GULF", RED, [
        ("Hormuz Tanker Catches Fire off Kharg",
         "UAE proposes maritime security patrols as the Strait of Hormuz shipping alert is raised."),
        ("Riyadh Air Defense Intercepts Drone Swarm",
         "Saudi forces down eight long-range unmanned aerial vehicles approaching energy facilities."),
        ("Coalition Strikes Target Houthi Depots",
         "Intensive raids hit weapons storage and launch facilities across the Hodeidah corridor."),
        ("Suez Canal Dual-Channel Deepening at 92%",
         "Southern expansion nears completion to double annual transit capacity and lower fees."),
        ("Qatar Inks 30-Year Clean LNG Pact with Japan",
         "Long-term delivery contracts underwrite grid stability for Asian manufacturing sectors."),
        ("Morocco Expands Ouarzazate Solar to 12 GW",
         "Molten-salt storage at the mega-facility supplies power through nocturnal demand peaks."),
    ]),
    ("ASIA-PACIFIC", GREEN, [
        ("ICJ Myanmar Genocide Ruling Spurs Action",
         "Global calls mount for enforcement of the ruling under the 1948 convention."),
        ("Shenzhen Trilateral Hotline Protocols Set",
         "Technical working groups establish direct military communications between nuclear powers."),
        ("China EAST Tokamak Achieves Steady Core",
         "Superconducting reactor sustains 106M\u00b0C plasma confinement in a milestone run."),
        ("Indonesia Nusantara Green Megapark Opens",
         "The new forest capital links government administration to a coastal logistics harbor."),
        ("South Korea & Japan Semiconductor Compact",
         "Tokyo and Seoul establish a joint silicon supply buffer against regional shocks."),
        ("Australia Power Grid Hits 88% Clean Peak",
         "The national electricity market sets a clean-output record led by rooftop solar."),
    ]),
    ("AMERICAS & TRANS-PACIFIC", CYAN, [
        ("Novida Board Names Interim Leadership Slate",
         "The tech giant stabilizes governance after a supply review and executive departures."),
        ("US-Thailand Bilateral Trade Pact Enters Force",
         "Washington and Bangkok eliminate tariffs on 97% of high-tech and defense goods."),
        ("US Senate Passes $65B Grid Modernization Bill",
         "Bipartisan legislation directs capital grants to ultra-high-voltage transmission lines."),
        ("Amazon Deforestation Drops to 14-Year Low",
         "Brazil's environmental agency confirms a 48% reduction in unauthorized clearing."),
        ("Canada Unveils Sovereign Critical Mineral Reserve",
         "Ottawa launches a national stockpile to guarantee domestic lithium and nickel supply."),
        ("Panama Canal Completes Recycled Water Locks",
         "A new reservoir system protects global maritime throughput during dry spells."),
    ]),
    ("CLIMATE, DIPLOMACY & AFRICA", VIOLET, [
        ("COP31 Opens in Baku with $30B Climate Fund",
         "Negotiators work past midnight on loss-and-damage financing contributions."),
        ("AfCFTA Single Digital Window Clears 1.2M Cargo",
         "The pan-African customs system cuts cargo clearance times by two-thirds."),
        ("Kenya Expands Olkaria Geothermal Capacity",
         "The East African nation brings an additional 150 MW of clean baseload online."),
        ("South Africa Breaks Ground on Saldanha Hub",
         "Transnet begins a continental deepwater green hydrogen bunkering terminal."),
        ("Nigeria AKK Pipeline Delivers 2.8B cfd Gas",
         "The trans-regional corridor powers new industrial generation across the north."),
        ("Africa CDC Mobile Sequencing Network Deployed",
         "Twenty field genomic laboratories establish real-time monitoring across river basins."),
    ]),
    ("SCIENCE, SPACE & ADVANCED TECH", AMBER, [
        ("BepiColombo Executes Mercury Gravity Flyby",
         "ESA and JAXA capture the closest imagery yet while planning orbital insertion."),
        ("JWST Detects Organic Signatures on Exoplanet",
         "Infrared spectroscopy finds methane and carbon compounds in a habitable-zone system."),
        ("WHO Geneva Assembly Formally Adopts Treaty",
         "The binding pandemic accord guarantees equitable pathogen data sharing."),
        ("Solid-State Ceramic Battery Hits 1,200 Wh/kg",
         "The next-gen cell completes 3,500 continuous cycles with zero degradation."),
        ("Autonomous Submersibles Map Mariana Trench",
         "A robotic swarm delivers sub-millimeter bathymetric maps of benthic trenches."),
        ("CERN Superconducting Cavity Sets Field Mark",
         "An accelerator prototype achieves a record terascale energy gradient."),
    ]),
]

LEAD = (
    "Rutte Arrives in Warsaw as Poland Bolsters Border Air Defense After Missile Alert",
    "NATO Secretary General Mark Rutte arrived in Warsaw on Saturday for emergency consultations "
    "following an overnight cruise missile incident near Nowy L\u0119bork in south-eastern Poland. "
    "Polish Armed Forces deployed enhanced Patriot radar surveillance along eastern frontiers "
    "while NATO confirmed heightened joint air policing.",
    ["NATO ARTICLE 4 CONSULTATIONS", "POLISH AIR SHIELD ACTIVE", "PATRIOT RADAR SURVEILLANCE"],
)

# label, name, lon, lat, colour, label dx/dy, label anchored right
HOTSPOTS = [
    ("A", "Warsaw", 21.0, 52.2, AMBER, (-9, -14), True),
    ("B", "Strait of Hormuz", 56.5, 26.5, RED, (7, 5), False),
    ("C", "Baku \u2014 COP31", 49.9, 40.4, VIOLET, (8, -12), False),
    ("D", "Riyadh", 46.7, 24.7, RED, (-10, 5), True),
    ("E", "Shenzhen", 114.1, 22.5, CYAN, (6, -13), False),
    ("F", "Mercury flyby", None, None, GREEN, (0, 0), False),
]

# Coarse low-poly coastlines, lon/lat. Decorative, not survey-grade.
LAND = [
    [(-168, 65), (-140, 70), (-120, 72), (-95, 74), (-75, 72), (-52, 60), (-60, 48),
     (-72, 42), (-80, 26), (-97, 26), (-105, 20), (-117, 32), (-125, 40), (-130, 55), (-140, 60)],
    [(-55, 82), (-20, 82), (-22, 70), (-45, 60), (-58, 68)],
    [(-80, 10), (-60, 12), (-50, 0), (-35, -6), (-38, -22), (-55, -35), (-66, -50),
     (-75, -52), (-72, -40), (-78, -20), (-81, -5)],
    [(-10, 60), (0, 71), (20, 70), (40, 68), (45, 55), (40, 45), (28, 40), (20, 38),
     (10, 44), (0, 43), (-9, 44)],
    [(-17, 15), (-10, 30), (10, 37), (32, 31), (43, 12), (51, 12), (40, -10), (38, -25),
     (25, -34), (15, -30), (8, -5), (0, 5)],
    [(45, 55), (60, 70), (90, 75), (120, 73), (160, 70), (179, 66), (179, 55), (140, 45),
     (130, 35), (122, 25), (110, 10), (100, 5), (95, 20), (80, 8), (70, 22), (60, 25),
     (48, 30), (45, 40)],
    [(113, -22), (130, -12), (142, -11), (153, -27), (150, -38), (135, -35), (115, -35)],
    [(95, 5), (120, 0), (140, -5), (130, -8), (110, -6)],
    [(130, 32), (142, 45), (145, 40), (136, 33)],
    [(-6, 50), (-2, 58), (2, 52), (-4, 50)],
    [(44, -13), (50, -16), (47, -25), (43, -22)],
    [(166, -46), (174, -41), (178, -38), (172, -44)],
]


# ---------------------------------------------------------------- pieces
def draw_header(draw):
    mast = "THE WORLD CHRONICLE"
    f = None
    size = 52
    while size > 30:
        f = font("serif_bold", size)
        if tw(draw, mast, f) <= 740:
            break
        size -= 2

    t = draw.textbbox((0, 0), mast, font=f)
    draw.text((M, 18 - t[1] + 4), mast, font=f, fill=INK)

    kicker = "INTERNATIONAL DAILY DISPATCH \u00b7 36 VERIFIED BULLETINS \u00b7 6 CONTINENTS \u00b7 VOL. XXVI NO. 325"
    tracked(draw, M, 74, kicker, font("sans_bold", 8), MUTED, spacing=0.7)

    # date plate
    box = (W - M - 236, 16, W - M, 84)
    draw.rounded_rectangle(box, radius=3, fill=(15, 34, 52), outline=CYAN, width=1)
    tracked(draw, box[0] + 12, box[1] + 9, "SATURDAY \u00b7 21 NOVEMBER 2026",
            font("sans_bold", 9), CYAN, spacing=0.4)
    draw.text((box[0] + 12, box[1] + 26), "GLOBAL UTC SUMMARY EDITION",
              font=font("sans_bold", 12), fill=INK)
    rule(draw, box[0] + 12, box[1] + 45, box[2] - 12, RULE)
    tracked(draw, box[0] + 12, box[1] + 51, "NIGHT FINAL \u00b7 22:00 UTC",
            font("sans", 8), MUTED, spacing=0.4)

    rule(draw, M, 92, W - M, AMBER, 2)
    draw_ticker(draw, 100)


def draw_ticker(draw, y):
    f_lbl, f_val, f_pct = font("sans_bold", 7), font("sans_bold", 8), font("sans", 7)
    gap = 14
    widths = []
    for name, val, pct, _ in TICKER:
        widths.append(tw(draw, name, f_lbl) + 4 + tw(draw, val, f_val) + 4 + tw(draw, pct, f_pct))
    free = (W - 2 * M) - sum(widths)
    gap = max(8, free / (len(TICKER) - 1))
    x = M
    for (name, val, pct, col), w in zip(TICKER, widths):
        tracked(draw, x, y + 1, name, f_lbl, DIM, spacing=0.4)
        nx = x + tw(draw, name, f_lbl) + 4
        draw.text((nx, y - 1), val, font=f_val, fill=INK)
        px = nx + tw(draw, val, f_val) + 4
        draw.text((px, y), pct, font=f_pct, fill=col)
        x += w + gap
    rule(draw, M, 116, W - M, RULE_SOFT)


def draw_lead(draw, box):
    x0, y0, x1, y1 = box
    panel(draw, box, PANEL, RULE, 4, RED)

    chip_w = tw(draw, "GLOBAL LEAD", font("sans_bold", 8)) + 18
    draw.rounded_rectangle((x0 + 14, y0 + 12, x0 + 14 + chip_w, y0 + 30),
                           radius=2, fill=RED)
    tracked(draw, x0 + 23, y0 + 16, "GLOBAL LEAD", font("sans_bold", 8), (18, 20, 26), 0.6)

    kicker = "WARSAW & BRUSSELS \u00b7 NATO DEFENSE CONSULTATIONS"
    tracked(draw, x0 + 24 + chip_w, y0 + 16, kicker, font("sans_bold", 8), MUTED, 0.7)

    headline, deck, tags = LEAD
    hw = (x1 - x0) - 28
    f, lines, lh = fit_font(draw, headline, "serif_bold", [25, 24, 23, 22, 21, 20], hw, 2, 66)
    ty = y0 + 38
    for ln in lines:
        draw.text((x0 + 14, ty), ln, font=f, fill=INK)
        ty += lh

    fd = font("serif", 10)
    dlines = fit_lines(draw, deck, fd, hw - 40, 3)
    dy = ty + 6
    for ln in dlines:
        draw.text((x0 + 14, dy), ln, font=fd, fill=MUTED)
        dy += 13

    # tag strip pinned to the panel floor
    strip_y = y1 - 30
    rule(draw, x0 + 14, strip_y, x1 - 14, RULE)
    tx = x0 + 14
    for i, tag in enumerate(tags):
        ft = font("sans_bold", 8)
        w = tw(draw, tag, ft) + 16
        col = (CYAN, AMBER, GREEN)[i % 3]
        draw.rounded_rectangle((tx, strip_y + 7, tx + w, strip_y + 23), radius=2,
                               outline=col, width=1)
        draw.text((tx + 8, strip_y + 10), tag, font=ft, fill=col)
        tx += w + 8


def draw_map(draw, box, hotspots):
    x0, y0, x1, y1 = box
    panel(draw, box, PANEL_ALT, RULE, 4, CYAN)

    tracked(draw, x0 + 12, y0 + 10, "GLOBAL GEOPOLITICAL LOCATOR MAP", font("sans_bold", 8.5), INK, 0.5)
    tracked(draw, x1 - 12 - 58, y0 + 11, "21 NOV 2026", font("sans", 7), DIM, 0.3)

    mx0, my0, mx1, my1 = x0 + 12, y0 + 28, x1 - 12, y0 + 152
    lon_min, lon_max = -175, 185
    lat_min, lat_max = -58, 80

    def proj(lon, lat):
        px = mx0 + (lon - lon_min) / (lon_max - lon_min) * (mx1 - mx0)
        py = my0 + (lat_max - lat) / (lat_max - lat_min) * (my1 - my0)
        return px, py

    # graticule
    for lon in range(-150, 181, 30):
        px, _ = proj(lon, 0)
        draw.line([(px, my0), (px, my1)], fill=(26, 40, 58), width=1)
    for lat in range(-40, 81, 20):
        _, py = proj(0, lat)
        draw.line([(mx0, py), (mx1, py)], fill=(26, 40, 58), width=1)
    # equator
    _, eq = proj(0, 0)
    draw.line([(mx0, eq), (mx1, eq)], fill=(34, 54, 74), width=1)

    for poly in LAND:
        pts = [proj(lon, lat) for lon, lat in poly]
        draw.polygon(pts, fill=(30, 45, 63), outline=(58, 82, 108))

    # hotspots
    for label, name, lon, lat, col, *rest in hotspots:
        if lon is None:
            continue
        px, py = proj(lon, lat)
        ox, oy = rest[0] if rest else (8, -5)
        draw.ellipse((px - 6, py - 6, px + 6, py + 6), outline=col, width=1)
        draw.ellipse((px - 2.2, py - 2.2, px + 2.2, py + 2.2), fill=col)
        draw.text((px + ox, py + oy), label, font=font("sans_bold", 7), fill=col)

    # legend, two columns
    lx, ly = x0 + 12, y0 + 164
    col_w = (x1 - x0 - 24) // 2
    for i, (label, name, lon, lat, col, *rest) in enumerate(hotspots):
        cx = lx + (i % 2) * col_w
        cy = ly + (i // 2) * 15
        draw.ellipse((cx, cy + 2, cx + 5, cy + 7), fill=col)
        draw.text((cx + 9, cy), f"{label}  {ellipsize(draw, name, font('sans', 7.5), col_w - 20)}",
                  font=font("sans", 7.5), fill=MUTED)

    rule(draw, x0 + 12, y1 - 30, x1 - 12, RULE_SOFT)
    draw.text((x0 + 12, y1 - 23), "Equirectangular locator \u00b7 hotspots keyed to sections",
              font=font("sans", 6.8), fill=DIM)


def draw_story(draw, x, y, w, h, idx, headline, summary, accent):
    """One bulletin inside a fixed cell; text is fitted, never clipped."""
    num_f = font("sans_bold", 8)
    num = f"{idx:02d}"
    draw.text((x, y + 1), num, font=num_f, fill=accent)
    draw.line([(x, y + 12), (x + 14, y + 12)], fill=accent, width=1)

    tx, twidth = x + 22, w - 22
    fh, hlines, hlh = fit_font(draw, headline, "sans_bold", [9.8, 9.4, 9.0, 8.6], twidth, 2, 22)
    cy = y - 1
    for ln in hlines:
        draw.text((tx, cy), ln, font=fh, fill=INK)
        cy += hlh

    remaining = (y + h) - (cy + 2)
    lines_room = max(1, int(remaining // 9.4))
    fs, slines, slh = fit_font(draw, summary, "sans", [7.8, 7.4, 7.0, 6.6],
                               twidth, min(3, lines_room), remaining)
    for ln in slines:
        draw.text((tx, cy + 1), ln, font=fs, fill=MUTED)
        cy += slh


def draw_sections(draw, top, bottom):
    cols, gap = 3, 14
    col_w = (W - 2 * M - (cols - 1) * gap) / cols
    row_gap = 12
    row_h = (bottom - top - row_gap) / 2
    for i, (title, accent, stories) in enumerate(SECTIONS):
        col, row = i % cols, i // cols
        x0 = M + col * (col_w + gap)
        y0 = top + row * (row_h + row_gap)
        x1, y1 = x0 + col_w, y0 + row_h
        panel(draw, (x0, y0, x1, y1), PANEL, RULE, 4, accent)

        f = font("sans_bold", 9)
        label = ellipsize(draw, title, f, col_w - 44)
        tracked(draw, x0 + 10, y0 + 11, label, f, accent, 0.6)
        badge = f"{len(stories)}"
        bw = tw(draw, badge, font("sans_bold", 7)) + 10
        draw.rounded_rectangle((x1 - 10 - bw, y0 + 9, x1 - 10, y0 + 21),
                               radius=2, fill=(24, 36, 54), outline=RULE)
        draw.text((x1 - 10 - bw / 2, y0 + 11), badge, font=font("sans_bold", 7),
                  fill=MUTED, anchor="ma")
        rule(draw, x0 + 10, y0 + 26, x1 - 10, RULE_SOFT)

        body_top = y0 + 32
        body_bottom = y1 - 8
        cell_h = (body_bottom - body_top) / len(stories)
        for j, (headline, summary) in enumerate(stories):
            sy = body_top + j * cell_h
            if j:
                rule(draw, x0 + 10, sy - 3, x1 - 10, RULE_SOFT)
            draw_story(draw, x0 + 10, sy + 2, col_w - 20, cell_h - 5,
                       j + 1, headline, summary, accent)


def draw_footer(draw, y):
    rule(draw, M, y - 12, W - M, AMBER, 1)
    tracked(draw, M, y, "MAKE.FUN VERIFIED SUMMATION \u00b7 36 CONCURRENT BULLETINS \u00b7 6 CONTINENTS \u00b7 SATURDAY, 21 NOVEMBER 2026",
            font("sans_bold", 7.5), MUTED, 0.4)
    right = "ACCURACY & SATELLITE AUDITED"
    f = font("sans_bold", 7.5)
    tracked(draw, W - M - sum(tw(draw, c, f) + 0.4 for c in right) + 0.4, y,
            right, f, AMBER, 0.4)


# ---------------------------------------------------------------- render
def main():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw_header(draw)

    lead_top, lead_bottom = 124, 366
    draw_lead(draw, (M, lead_top, 664, lead_bottom))
    draw_map(draw, (676, lead_top, W - M, lead_bottom), HOTSPOTS)

    draw_sections(draw, 378, 980)
    draw_footer(draw, 1006)

    img.save(OUT, format="PNG", optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
