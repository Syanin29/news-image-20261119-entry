#!/usr/bin/env python3
"""Render the front page for Thursday 19 November 2026 — 31 verified stories.

Deterministic 1024x1024 PNG (fixed seed, no timestamps, no metadata).
Byte-identical on repeated runs. Output <= 1 MiB.

Usage:
  python3 render.py            # v1 light front page -> entry.png
  python3 render.py v2         # -> variants/v2-entry.png, etc.
Styles: v1 light front page, v2 dark edition, v3 map-led, v4 photo-led,
        v5 broadsheet, v6 stat-led. All six share the same story data and
        the same band primitives; only arrangement and palette differ.
"""

import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
WORK = HERE  # render.py lives in the entry repo; assets/fonts beside it
WIDTH, HEIGHT = 1024, 1024
SEED = 20261119
MAX_BYTES = 1024 * 1024

# ---------------------------------------------------------------------------
# Story data — 31 verified stories for Thu 19 Nov 2026.
# (headline, explainer, stat, map_marker_or_None, photo_or_None)
# Sources: see NEWS-SOURCES.md / facts-2026-11-19.md in the work dir.
# ---------------------------------------------------------------------------

HERO = (
    "TRUMP, XI & PUTIN MEET IN SHENZHEN",
    "First-ever trilateral of the three nuclear giants, on the APEC "
    "sidelines \u2014 disarmament on the table, New START expiring",
    "FIRST-EVER \u00d73",
    1,
    "earth-night.jpg",
)

FEATURES = [
    (
        "GTA VI LAUNCHES WORLDWIDE",
        "Vice City returns after 13 years; $1.18bn in pre-orders",
        "$1.18BN",
        3,
        None,
    ),
    (
        "VOYAGER 1 HITS ONE LIGHT-DAY",
        "Launched 1977, now ~26bn km out; signals take a day each way",
        "26BN KM",
        None,
        None,
    ),
    (
        "EU'S \u20ac45BN UKRAINE LOAN",
        "Brussels borrows \u20ac45bn for Kyiv's 2026 gap; repaid via reparations",
        "\u20ac45BN",
        4,
        None,
    ),
    (
        "CYCLONE AKVAN NEARS INDIA",
        "Very severe by tonight; landfall forecast noon Fri, \u226521 cm of rain",
        "RED ALERT",
        5,
        None,
    ),
]

LIST_STORIES = [
    ("AUSTRALIA SANCTIONS ISRAELI SETTLEMENTS", "FRESH SANCTIONS", 6),
    ("ISRAEL GROUND OP BEYOND GAZA LINE", "GAZA", 7),
    ("SAUDI-LED STRIKES ON YEMEN", "HORMUZ", 8),
    ("US\u2013IRAN FIRE EXCHANGED AGAIN", "QESHM STRUCK", 8),
    ("FED MINUTES: MORE HIKES LIKELY", "HIKES AHEAD", 9),
    ("NVIDIA'S ACTING CEO ACTS", "KRESS ACTS", 9),
    ("ANTHROPIC IPO RAISES $81.3BN", "$81.3BN", 9),
    ("ENGLAND SEAL ODI SERIES 2\u20131", "DUCKETT 133", 11),
    ("UK INFLATION 3.6%", "3.6%", 10),
    ("GOLD SLIDES TO $3,787.65", "\u22121.6%", 10),
    ("TAKE-TWO +8% ON GTA ROLLOUT", "+8%", 3),
    ("SPAIN GENERAL STRIKE", "STRIKE", 12),
    ("PELTOLA TAKES ALASKA SENATE SEAT", "56\u201344", 13),
    ("INDIA\u2013JAPAN DEFENCE REVIEW", "TOKYO", 14),
    ("LPG TANKER SANK OFF BULGARIA", "HIT BY FIRE", 15),
    ("MYANMAR GENOCIDE VERDICT", "ICJ VERDICT", 16),
    ("MCDONALD'S ABUSE CASE GOES ON", "CASE GOES ON", 10),
    ("LYNCH YACHT REPORT", "HIGH WINDS", 10),
    ("NSA NETWORK OUTAGE", "NSA DOWN", 9),
    ("DEUTSCHE BANK'S $582M EPSTEIN LINK", "$582M", 9),
    ("SOMALIA ACCUSES UAE", "SECRET BASES", 8),
    ("US GREEN-CARD RULES TOUGHER", "TOUGHER RULES", 9),
]

TICKER = [
    ("CMA AWARDS 2026", "Swift & Powell on the red carpet"),
    ("PRINCE HARRY: I'D REJOIN ARMY", "Warns of the Russia threat"),
    ("BIDEN MEMOIR OUT", "Putin 'slouched like a teenager'"),
    ("CANADA RECALIBRATES CHINA TIES", "Carney seeks the right US deal"),
]

# map marker number -> (lon, lat, display_dx_px, display_dy_px)
MARKERS = {
    1: (114.1, 22.5, 0, -16),
    2: (121.0, 14.6, 0, 16),
    3: (-80.2, 25.8, -6, 14),
    4: (4.4, 50.8, 0, -16),
    5: (80.9, 16.2, 0, 16),
    6: (149.1, -35.3, 0, -16),
    7: (34.5, 31.5, -4, -16),
    8: (56.5, 26.6, 0, 16),
    9: (-77.0, 38.9, 0, -16),
    10: (-0.1, 51.5, -16, 2),
    11: (147.3, -42.9, 0, 14),
    12: (-3.7, 40.4, -2, 16),
    13: (-150.0, 64.0, 0, 18),
    14: (139.7, 35.7, 0, -16),
    15: (28.0, 43.0, 14, 12),
    16: (4.3, 52.1, 16, 12),
}

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------

LIGHT = dict(
    paper=(247, 243, 234), ink=(22, 22, 22), sub=(74, 74, 74),
    rule=(22, 22, 22), accent=(178, 34, 34), accent2=(18, 92, 140),
    card=(255, 255, 255), card_edge=(205, 198, 184), chip=(22, 22, 22),
    chip_text=(255, 255, 255), map_dot=(52, 84, 122), map_bg=(233, 230, 220),
    marker=(178, 34, 34), ticker_bg=(22, 22, 22), ticker_text=(247, 243, 234),
    shadow=(0, 0, 0, 38), grain=14,
)
DARK = dict(
    paper=(16, 24, 40), ink=(238, 238, 232), sub=(176, 184, 196),
    rule=(238, 238, 232), accent=(255, 92, 92), accent2=(96, 196, 255),
    card=(28, 38, 58), card_edge=(62, 76, 100), chip=(238, 238, 232),
    chip_text=(16, 24, 40), map_dot=(120, 170, 220), map_bg=(22, 32, 52),
    marker=(255, 92, 92), ticker_bg=(238, 238, 232), ticker_text=(16, 24, 40),
    shadow=(0, 0, 0, 70), grain=10,
)

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

def font(name, size):
    return ImageFont.truetype(str(HERE / "fonts" / name), size)


def fonts_for(scale=1.0):
    s = lambda n: max(8, int(n * scale))
    return dict(
        masthead=font("PlayfairDisplay.ttf", s(52)),
        dateline=font("Inter.ttf", s(13)),
        kicker=font("Archivo.ttf", s(13)),
        hero=font("Archivo.ttf", s(34)),
        hero_stat=font("Archivo.ttf", s(15)),
        body=font("Inter.ttf", s(14)),
        feature=font("Archivo.ttf", s(19)),
        feature_stat=font("Archivo.ttf", s(12)),
        list_head=font("Archivo.ttf", s(13)),
        list_stat=font("Archivo.ttf", s(11)),
        map_label=font("Inter.ttf", s(11)),
        map_title=font("Archivo.ttf", s(14)),
        ticker=font("Archivo.ttf", s(13)),
        big_stat=font("Archivo.ttf", s(30)),
    )

# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def wrap(draw, text, fnt, max_w):
    """Greedy word wrap; returns list of lines that fit max_w."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def shrink_to_fit(draw, text, fnt_path, size, max_w, min_size=8):
    """Largest font size (<= size) whose text fits max_w; returns font."""
    while size > min_size:
        f = ImageFont.truetype(str(HERE / "fonts" / fnt_path), size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 1
    return ImageFont.truetype(str(HERE / "fonts" / fnt_path), min_size)


def cover(img, w, h):
    """Resize+crop an image to cover w x h (centre crop)."""
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    img = img.resize((int(iw * scale) + 1, int(ih * scale) + 1), Image.LANCZOS)
    x = (img.width - w) // 2
    y = (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))

# ---------------------------------------------------------------------------
# Texture helpers — grain, glow, soft shadow (the anti-flat kit)
# ---------------------------------------------------------------------------

def add_grain(img, amount, seed=SEED):
    rnd = random.Random(seed)
    w, h = img.size
    grain = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = grain.load()
    for _ in range(w * h // 90):
        x, y = rnd.randrange(w), rnd.randrange(h)
        v = rnd.choice((0, 255))
        px[x, y] = (v, v, v, amount)
    out = Image.alpha_composite(img.convert("RGBA"), grain)
    return out.convert("RGB")


def soft_shadow(base, box, blur=6, alpha=38):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle(box, fill=(0, 0, 0, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(layer)


def glow_spot(base, cx, cy, r, color, alpha=90):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(r // 2))
    base.alpha_composite(layer)

# ---------------------------------------------------------------------------
# Dotted world map from Natural Earth coastline data
# ---------------------------------------------------------------------------

def load_land():
    data = json.loads((HERE / "ne_110m_land.geojson").read_text())
    polys = []
    for feat in data["features"]:
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            polys.append(geom["coordinates"])
        elif geom["type"] == "MultiPolygon":
            polys.extend(geom["coordinates"])
    return polys


def point_in_poly(x, y, poly):
    inside = False
    ring = poly[0]
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


def draw_dotted_map(img, box, pal, fnt, title="WHERE IT HAPPENED \u2014 16 PLACES"):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    draw = ImageDraw.Draw(img)
    draw.rectangle(box, fill=pal["map_bg"])
    polys = load_land()
    boxes = []
    for p in polys:
        xs = [pt[0] for pt in p[0]]
        ys = [pt[1] for pt in p[0]]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    step = 7
    for gy in range(y0 + 8, y1 - 6, step):
        for gx in range(x0 + 8, x1 - 6, step):
            lon = (gx - x0) / w * 360 - 180
            lat = 90 - (gy - y0) / h * 180
            hit = False
            for (bx0, by0, bx1, by1), p in zip(boxes, polys):
                if bx0 <= lon <= bx1 and by0 <= lat <= by1:
                    if point_in_poly(lon, lat, p):
                        hit = True
                        break
            if hit:
                r = 1.7
                draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=pal["map_dot"])
    # graticule: faint latitude lines for depth
    for frac in (0.25, 0.5, 0.75):
        yy = y0 + int(h * frac)
        draw.line([(x0, yy), (x1, yy)], fill=pal["card_edge"], width=1)
    # markers: true spot + leader line to an offset numbered dot (declutters
    # tight clusters such as Europe, Gaza/Hormuz and Shenzhen/Manila)
    for num, (lon, lat, dx, dy) in MARKERS.items():
        mx = x0 + (lon + 180) / 360 * w
        my = y0 + (90 - lat) / 180 * h
        cx, cy = mx + dx, my + dy
        if dx or dy:
            draw.line([(mx, my), (cx, cy)], fill=pal["marker"], width=1)
            draw.ellipse([mx - 2, my - 2, mx + 2, my + 2], fill=pal["marker"])
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=pal["marker"],
                     outline=(255, 255, 255), width=2)
        draw.text((cx, cy - 1), str(num), font=fnt, fill=(255, 255, 255),
                  anchor="mm")
    if h < 180:  # short map: title to the right, clear of the Alaska marker
        draw.text((x1 - 10, y0 + 6), title, font=fnt, fill=pal["sub"],
                  anchor="ra")
    else:
        draw.text((x0 + 10, y0 + 6), title, font=fnt, fill=pal["sub"])
    # Cyclone photo inset in the empty south-Pacific corner (texture +
    # a second photo layer for the map band).
    inset = Image.open(HERE / "assets" / "cyclone.jpg").convert("RGB")
    inset = cover(inset, 132, 66)
    ix, iy = x0 + 10, y1 - 84
    img.paste(inset, (ix, iy))
    d2 = ImageDraw.Draw(img)
    d2.rectangle([ix, iy, ix + 132, iy + 66], outline=pal["card_edge"], width=2)
    d2.rectangle([ix, iy + 66, ix + 132, iy + 82], fill=pal["chip"])
    d2.text((ix + 66, iy + 74), "CYCLONE AKVAN",
            font=fnt, fill=pal["chip_text"], anchor="mm")


# ---------------------------------------------------------------------------
# Bands — each draws into (img, x0, y, width, height, pal, F)
# ---------------------------------------------------------------------------

def band_masthead(img, y, h, pal, F):
    d = ImageDraw.Draw(img)
    d.rectangle([0, y, WIDTH, y + h], fill=pal["paper"])
    d.text((WIDTH // 2, y + 8), "WORLD NEWS", font=F["masthead"],
           fill=pal["ink"], anchor="ma")
    d.line([(28, y + h - 30), (WIDTH - 28, y + h - 30)], fill=pal["rule"], width=2)
    d.text((WIDTH // 2, y + h - 26),
           "THURSDAY, 19 NOVEMBER 2026  \u2022  31 STORIES  \u2022  6 CONTINENTS",
           font=F["dateline"], fill=pal["sub"], anchor="ma")
    return y + h


def band_hero(img, y, h, pal, F, photo=True):
    """Hero: photo left, top-story text right (or full-width text if no photo)."""
    d = ImageDraw.Draw(img)
    pad = 28
    if photo:
        pw = 560
        px0, py0, px1, py1 = pad, y + 10, pad + pw, y + h - 10
        earth = Image.open(HERE / "assets" / HERO[4]).convert("RGB")
        earth = cover(earth, px1 - px0, py1 - py0)
        # warm gradient wash over the photo's lower half for legibility
        wash = Image.new("RGBA", earth.size, (0, 0, 0, 0))
        wd = ImageDraw.Draw(wash)
        for i in range(earth.height // 2, earth.height):
            a = int(150 * (i - earth.height // 2) / (earth.height // 2))
            wd.line([(0, i), (earth.width, i)], fill=(10, 10, 30, a))
        earth = Image.alpha_composite(earth.convert("RGBA"), wash).convert("RGB")
        img.paste(earth, (px0, py0))
        d.rectangle([px0, py0, px1, py1], outline=pal["card_edge"], width=2)
        d.text((px0 + 12, py1 - 30), "EARTH AT NIGHT \u2014 THE DAY IN ONE GLOBE",
               font=F["map_label"], fill=(255, 255, 255))
        tx0 = px1 + 22
        tw = WIDTH - pad - tx0
    else:
        tx0, tw = pad, WIDTH - 2 * pad
    d.text((tx0, y + 12), "TOP STORY \u2014 SHENZHEN", font=F["kicker"],
           fill=pal["accent"])
    # headline wrapped at 34pt, falling back smaller if it needs >3 lines
    size = 34
    while size > 24:
        f = ImageFont.truetype(str(HERE / "fonts" / "Archivo.ttf"), size)
        if len(wrap(d, HERO[0], f, tw)) <= 3:
            break
        size -= 2
    head_f = ImageFont.truetype(str(HERE / "fonts" / "Archivo.ttf"), size)
    yy = y + 34
    for ln in wrap(d, HERO[0], head_f, tw):
        d.text((tx0, yy), ln, font=head_f, fill=pal["ink"])
        yy += size + 4
    yy += 6
    for ln in wrap(d, HERO[1], F["body"], tw):
        d.text((tx0, yy), ln, font=F["body"], fill=pal["sub"])
        yy += 19
    yy += 10
    d.rounded_rectangle([tx0, yy, tx0 + 168, yy + 30], radius=4, fill=pal["chip"])
    d.text((tx0 + 84, yy + 15), HERO[2], font=F["hero_stat"],
           fill=pal["chip_text"], anchor="mm")
    d.text((tx0 + 182, yy + 15), "APEC \u00b7 21 ECONOMIES", font=F["feature_stat"],
           fill=pal["sub"], anchor="lm")
    return y + h


def band_features(img, y, h, pal, F, photo_card=True):
    d = ImageDraw.Draw(img)
    pad, gap = 28, 14
    cw = (WIDTH - 2 * pad - 3 * gap) // 4
    for i, (head, expl, stat, _mk, photo) in enumerate(FEATURES):
        x0 = pad + i * (cw + gap)
        x1 = x0 + cw
        y0, y1 = y + 8, y + h - 8
        img_rgba = img.convert("RGBA")
        soft_shadow(img_rgba, (x0 + 3, y0 + 4, x1 + 3, y1 + 4))
        img.paste(img_rgba.convert("RGB"), (0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([x0, y0, x1, y1], fill=pal["card"], outline=pal["card_edge"])
        bar = pal["accent"] if i % 2 == 0 else pal["accent2"]
        d.rectangle([x0, y0, x1, y0 + 5], fill=bar)
        yy = y0 + 12
        if photo and photo_card and i == 3:
            thumb = Image.open(HERE / "assets" / photo).convert("RGB")
            thumb = cover(thumb, cw - 20, 52)
            img.paste(thumb, (x0 + 10, yy))
            d.rectangle([x0 + 10, yy, x0 + cw - 10, yy + 52],
                        outline=pal["card_edge"])
            yy += 60
        d.text((x0 + 10, yy), f"0{i + 2}", font=F["kicker"], fill=bar)
        yy += 18
        size = 19
        while size > 15:
            f = ImageFont.truetype(str(HERE / "fonts" / "Archivo.ttf"), size)
            if len(wrap(d, head, f, cw - 20)) <= 3:
                break
            size -= 1
        hf = ImageFont.truetype(str(HERE / "fonts" / "Archivo.ttf"), size)
        for ln in wrap(d, head, hf, cw - 20):
            d.text((x0 + 10, yy), ln, font=hf, fill=pal["ink"])
            yy += size + 2
        yy += 4
        lines_avail = max(0, (y1 - 26 - yy) // 15)
        for ln in wrap(d, expl, F["feature_stat"], cw - 20)[:lines_avail]:
            d.text((x0 + 10, yy), ln, font=F["feature_stat"], fill=pal["sub"])
            yy += 15
        d.text((x0 + 10, y1 - 12), stat, font=F["feature_stat"],
               fill=pal["accent"], anchor="la")
    return y + h


def band_list(img, y, h, pal, F, cols=2):
    d = ImageDraw.Draw(img)
    pad = 28
    d.text((pad, y + 4), "THE REST OF THE DAY", font=F["map_title"], fill=pal["ink"])
    d.line([(pad, y + 26), (WIDTH - pad, y + 26)], fill=pal["rule"], width=1)
    col_w = (WIDTH - 2 * pad - 20) // cols
    rows = (len(LIST_STORIES) + cols - 1) // cols
    row_h = (h - 34) // rows
    for idx, (head, stat, _mk) in enumerate(LIST_STORIES):
        c, r = idx % cols, idx // cols
        x0 = pad + c * (col_w + 20)
        yy = y + 34 + r * row_h
        d.text((x0, yy), f"{idx + 6:02d}", font=F["list_stat"], fill=pal["accent"])
        stat_w = d.textlength(stat, font=F["list_stat"])
        head_max = col_w - 26 - int(stat_w) - 10
        f = shrink_to_fit(d, head, "Archivo.ttf", 13, head_max, min_size=9)
        shown = head
        while d.textlength(shown, font=f) > head_max and len(shown) > 12:
            shown = shown.rsplit(" ", 1)[0] + "\u2026"
        d.text((x0 + 26, yy), shown, font=f, fill=pal["ink"])
        d.text((x0 + col_w, yy), stat, font=F["list_stat"], fill=pal["sub"],
               anchor="ra")
        d.line([(x0, yy + 17), (x0 + col_w, yy + 17)], fill=pal["card_edge"])
    return y + h


def band_ticker(img, y, h, pal, F):
    d = ImageDraw.Draw(img)
    d.rectangle([0, y, WIDTH, y + h], fill=pal["ticker_bg"])
    parts = [f"{h}: {e}" for h, e in TICKER]
    text = "  \u2022  ".join(parts)
    f = shrink_to_fit(d, text, "Archivo.ttf", 13, WIDTH - 56)
    d.text((WIDTH // 2, y + h // 2 - 14), text, font=f,
           fill=pal["ticker_text"], anchor="ma")
    d.text((WIDTH // 2, y + h - 16),
           "ALL STORIES VERIFIED 19 NOV 2026 \u2014 SOURCES IN NEWS-SOURCES.md",
           font=F["map_label"], fill=pal["ticker_text"], anchor="ma")
    return y + h


def band_stats(img, y, h, pal, F):
    """Big-number strip used by the stat-led variant."""
    d = ImageDraw.Draw(img)
    items = [("$1.18BN", "GTA VI PRE-ORDERS"), ("26BN KM", "VOYAGER 1"),
             ("\u20ac45BN", "EU UKRAINE LOAN"), ("99/100", "GTA VI SCORE"),
             ("133", "DUCKETT'S TON")]
    cw = WIDTH // len(items)
    for i, (num, label) in enumerate(items):
        x0 = i * cw
        d.text((x0 + cw // 2, y + 8), num, font=F["big_stat"],
               fill=pal["accent"] if i % 2 == 0 else pal["accent2"], anchor="ma")
        d.text((x0 + cw // 2, y + 48), label, font=F["feature_stat"],
               fill=pal["sub"], anchor="ma")
        if i:
            d.line([(x0, y + 10), (x0, y + h - 10)], fill=pal["card_edge"])
    return y + h

# ---------------------------------------------------------------------------
# Layouts — six genuinely different arrangements of the same bands
# ---------------------------------------------------------------------------

def render(style):
    pal = DARK if style == "v2" else LIGHT
    F = fonts_for()
    img = Image.new("RGB", (WIDTH, HEIGHT), pal["paper"])
    if style == "v1":  # light front page
        y = band_masthead(img, 0, 96, pal, F)
        y = band_hero(img, y, 238, pal, F)
        y = band_features(img, y, 158, pal, F)
        draw_dotted_map(img, (28, y + 6, WIDTH - 28, y + 224), pal, F["map_label"])
        y += 230
        y = band_list(img, y, 244, pal, F)
        y = band_ticker(img, y, 58, pal, F)
    elif style == "v2":  # dark edition, same geometry
        y = band_masthead(img, 0, 96, pal, F)
        y = band_hero(img, y, 238, pal, F)
        y = band_features(img, y, 158, pal, F)
        draw_dotted_map(img, (28, y + 6, WIDTH - 28, y + 224), pal, F["map_label"])
        y += 230
        y = band_list(img, y, 244, pal, F)
        y = band_ticker(img, y, 58, pal, F)
    elif style == "v3":  # map-led: map first, hero second
        y = band_masthead(img, 0, 96, pal, F)
        draw_dotted_map(img, (28, y + 6, WIDTH - 28, y + 300), pal, F["map_label"])
        y += 306
        y = band_hero(img, y, 210, pal, F)
        y = band_features(img, y, 158, pal, F)
        y = band_list(img, y, 192, pal, F)
        y = band_ticker(img, y, 58, pal, F)
    elif style == "v4":  # photo-led: tall hero photo, compact rest
        y = band_masthead(img, 0, 96, pal, F)
        y = band_hero(img, y, 330, pal, F)
        y = band_features(img, y, 150, pal, F)
        draw_dotted_map(img, (28, y + 6, WIDTH - 28, y + 150), pal, F["map_label"])
        y += 156
        y = band_list(img, y, 232, pal, F)
        y = band_ticker(img, y, 58, pal, F)
    elif style == "v5":  # broadsheet: 3-column list, map at the foot
        y = band_masthead(img, 0, 96, pal, F)
        y = band_hero(img, y, 200, pal, F, photo=False)
        y = band_features(img, y, 158, pal, F, photo_card=False)
        y = band_list(img, y, 356, pal, F, cols=3)
        draw_dotted_map(img, (28, y + 6, WIDTH - 28, y + 150), pal, F["map_label"])
        y += 156
        y = band_ticker(img, y, 58, pal, F)
    elif style == "v6":  # stat-led: big numbers, then hero, then list
        y = band_masthead(img, 0, 96, pal, F)
        y = band_stats(img, y, 76, pal, F)
        y = band_hero(img, y, 220, pal, F)
        y = band_features(img, y, 158, pal, F)
        draw_dotted_map(img, (28, y + 6, WIDTH - 28, y + 150), pal, F["map_label"])
        y += 156
        y = band_list(img, y, 260, pal, F)
        y = band_ticker(img, y, 58, pal, F)
    else:
        raise SystemExit(f"unknown style {style}")
    # vignette + grain over everything (texture, anti-flat)
    vig = Image.new("RGBA", img.size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(vig)
    vd.rectangle([0, 0, WIDTH, 26], fill=(0, 0, 0, 18))
    vd.rectangle([0, HEIGHT - 26, WIDTH, HEIGHT], fill=(0, 0, 0, 18))
    img = Image.alpha_composite(img.convert("RGBA"), vig).convert("RGB")
    img = add_grain(img, pal["grain"])
    return img


def save(img, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)
    data = path.read_bytes()
    assert len(data) <= MAX_BYTES, f"{path}: {len(data)} bytes over 1 MiB"
    return len(data)


def main():
    style = sys.argv[1] if len(sys.argv) > 1 else "v1"
    img = render(style)
    if style == "v1":
        n = save(img, HERE / "entry.png")
        print(f"v1 -> entry.png ({n} bytes, 1024x1024)")
    else:
        n = save(img, HERE / "variants" / f"{style}-entry.png")
        print(f"{style} -> variants/{style}-entry.png ({n} bytes, 1024x1024)")


if __name__ == "__main__":
    main()
