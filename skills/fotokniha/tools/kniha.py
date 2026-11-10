"""Playful photobook layout: polaroid photos, washi tape, handwritten captions, travel stamps and maps.

Every page is an SVG rendered to JPEG by headless Chrome.
  python3 SKILL_DIR/tools/kniha.py --projekt DIR          -> preview (1200 px) in kniha/nahled/ + prehled.jpg
  python3 SKILL_DIR/tools/kniha.py --projekt DIR --tisk   -> print pages in kniha/tisk/ (needs originaly/)
"""
import collections
import hashlib
import json
import math
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

S = 1200  # layout units per page side
PAPER, DOTS, INK, MUTED = "#f7f2e8", "#e7decd", "#2f2a26", "#8b8178"
SEA, LAND, LAND_HOME, BORDER = "#d9e6e6", "#f2e8d5", "#ead5ad", "#bfae8c"
ACCENTS = ["#c65d3b", "#2f7f79", "#d29a2e", "#4f6fa8", "#b9607b"]
TAPES = ["#e8c46a", "#9fc2b5", "#e6a3a3", "#a9bfe0", "#d7b8e0"]
HAND = "Caveat"
STAMP_FONT = "'Arial Narrow', 'Helvetica Neue', Arial, sans-serif"
PER_PAGE = 8  # max photos on a page (the year opener holds 3–6)
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
B_SIDE, B_BOTTOM = .045, .16  # polaroid frame as fraction of tile width

# set by setup()
P = CFG = PROF = None
FINAL = False
OUT = IMG_CACHE = None
PRINT_PX, B = S, 0
picks, chapters, NAME, CAPTIONS, TRIPS, GEO = [], {}, {}, {}, {}, None
HOME_CC, HOME_BBOX, FIRST_YEAR = None, None, 2000
_uid = [0]


def setup(project_dir, final=False):
    global P, CFG, PROF, FINAL, OUT, IMG_CACHE, PRINT_PX, B, picks, chapters, NAME, CAPTIONS, TRIPS, GEO
    global HOME_CC, HOME_BBOX, FIRST_YEAR
    P = C.Project(project_dir)
    CFG = P.cfg()
    PROF = C.profile(CFG)
    FINAL = final
    OUT = P.dir / "kniha" / ("tisk" if final else "nahled")
    IMG_CACHE = P.dir / "kniha" / ("foto_tisk" if final else "foto_nahled")
    if final:
        PRINT_PX = PROF["strana_px"]
        trim = PRINT_PX - 2 * PROF["spadavka_px"]
        B = S * PROF["spadavka_px"] / trim
    picks = P.read("vyber.json")
    if not picks:
        sys.exit("Výběr je prázdný – doplň vyber.txt a spusť vyber.py.")
    chapters = {c["id"]: c for c in P.read("kapitoly.json")}
    NAME = CFG.get("nazvy_mist") or {}
    CAPTIONS = CFG.get("popisky") or {}
    TRIPS = CFG.get("cesty") or {}
    GEO = C.load_geo()
    HOME_CC = CFG.get("domovska_zeme") or collections.Counter(p["cc"] for p in picks if p["cc"]).most_common(1)[0][0]
    HOME_BBOX = C.country_bbox(GEO, HOME_CC)
    FIRST_YEAR = int(min(p["date"] for p in picks)[:4])
    C.homes(CFG)


# ---------------------------------------------------------------- helpers
def h01(s, salt=""):
    return int(hashlib.md5((s + salt).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def text_w(t, fs):
    return len(t) * fs * 0.43


def key(p):
    return p["chapter"], p["tile"]


def tx(name, default):
    return (CFG.get("texty") or {}).get(name, default)


PREFIXES = re.compile(r"^(chráněná krajinná oblast|národní park|národni park|přírodní rezervace|národní přírodní "
                      r"rezervace|národní přírodní památka|přírodní památka|nationalpark) ", re.I)
UNCURATED = {}  # shown name -> raw name from Photos, for names not set in kniha.json → nazvy_mist
DRAWN = set()   # names that really appear in captions and map labels


def nice_place(p):
    raw = p["aoi"][0] if p.get("aoi") else (p.get("city") or "")
    if raw in NAME:
        out = NAME[raw]
    else:
        out = re.sub(r"^(.+?)[ -]\d{1,2}$", r"\1", raw)  # city districts: "Praha 5" -> "Praha"
        out = PREFIXES.sub("", out)
        out = NAME.get(out, out)
    if raw and raw not in NAME and out:
        UNCURATED[out] = raw
    return out


def short_city(city):
    city = city or ""
    return NAME.get(city) or city


def date_cz(d):
    return f"{int(d[8:10])}. {int(d[5:7])}."


def trip_cfg(cid):
    return TRIPS.get(cid) or {}


def trip_picks(cid):
    return [p for p in picks if p["chapter"] == cid]


def trip_name(cid):
    """Map/plan title of a trip: kniha.json → cesty.<id>.nazev, else the main place + year."""
    t = trip_cfg(cid)
    if t.get("nazev"):
        return t["nazev"]
    names = collections.Counter(nice_place(p) for p in trip_picks(cid) if nice_place(p))
    place = names.most_common(1)[0][0] if names else (chapters[cid]["places"] or ["Výlet"])[0]
    return f"{place} {cid[:4]}"


def trip_short(cid):
    t = trip_cfg(cid)
    return t.get("cil") or re.sub(r"\s+\d{4}$", "", trip_name(cid))


def is_trip(cid):
    return chapters.get(cid, {}).get("kind") in ("cesta", "vylet")


def caption(p):
    k = f"{p['chapter']}/{p['tile']}"
    if k in CAPTIONS:
        pl = CAPTIONS[k]
    elif p["chapter"] in CAPTIONS:
        pl = CAPTIONS[p["chapter"]]
    else:
        pl = nice_place(p) or (trip_short(p["chapter"]) if is_trip(p["chapter"]) else "")
    DRAWN.add(pl)
    return f"{pl}, {date_cz(p['date'])}" if pl else date_cz(p["date"])


def image_for(p):
    """Auto-oriented JPEG for the page: originals for print, Photos thumbnails for the preview."""
    IMG_CACHE.mkdir(parents=True, exist_ok=True)
    dst = IMG_CACHE / f"{p['uuid']}.jpg"
    if not dst.exists():
        orig = next((P.dir / "originaly").rglob(f"*{p['uuid']}*.jp*g"), None) if (P.dir / "originaly").exists() else None
        if FINAL:
            if orig is None:
                sys.exit(f"Chybí originál fotky {p['uuid']} ({p['date']}). Spusť tools/originaly.py.")
            src, size = orig, "3400x3400>"
        else:
            src = p["deriv"] if p["deriv"] and pathlib.Path(p["deriv"]).exists() else orig
            if src is None:
                sys.exit(f"Fotka {p['uuid']} ({p['date']}) nemá náhled ani originál.")
            size = "1100x1100>"
        subprocess.run(["magick", str(src), "-auto-orient", "-resize", size, "-colorspace", "sRGB",
                        "-quality", "90", str(dst)], check=True, capture_output=True)
    if "dims" not in p:
        o = subprocess.run(["magick", "identify", "-format", "%w %h", str(dst)], capture_output=True, text=True).stdout
        p["dims"] = tuple(map(int, o.split()))
    return dst


_ROWS = {}


def all_rows():
    if not _ROWS:
        _ROWS.update({r["uuid"]: r for r in P.read("fotky.json")})
    return _ROWS


def as_pick(r):
    pl = r["place"] or {}
    return {"date": r["date"], "lat": r["lat"], "lon": r["lon"], "aoi": (pl.get("aoi") or [])[:2],
            "city": pl.get("city"), "cc": pl.get("country")}


def route_stops(cid):
    """Stops on a road-trip map: every place of the chosen photos, plus the trip's other big stops from all its photos
    (not only the chosen ones), in the order they were visited. Transit stops far away are left out.
    Override: kniha.json → cesty.<id>.trasa = ["Florencie", "Siena", ...]."""
    chosen = stops(trip_picks(cid))
    rows = all_rows()
    pool = [as_pick(rows[u]) for u in chapters.get(cid, {}).get("pool") or [] if u in rows]
    st = stops(pool) if pool else []
    want = trip_cfg(cid).get("trasa")
    if want:
        by_name = {c["name"]: c for c in st + chosen}
        missing = [n for n in want if n not in by_name]
        if missing:
            print(f"Pozor: cesta {cid} nemá zastávky {missing}; dostupné: {sorted(by_name)}")
        return [by_name[n] for n in want if n in by_name]
    if not chosen or not st:
        return chosen
    center = (sum(c["pt"][0] for c in chosen) / len(chosen), sum(c["pt"][1] for c in chosen) / len(chosen))
    reach = max(60, 1.5 * max(C.km(c["pt"], center) for c in chosen))
    total = sum(c["n"] for c in st)
    names = {c["name"] for c in chosen}
    extra = [c for c in st if c["n"] >= max(4, total * .06) and c["name"] not in names
             and C.km(c["pt"], center) <= reach and all(C.km(c["pt"], x["pt"]) >= 8 for x in chosen)]
    extra = sorted(extra, key=lambda c: -c["n"])[:max(0, 8 - len(chosen))]
    return sorted(chosen + extra, key=lambda c: c["d"])


def home_pt(year):
    h = C.home_for(CFG, year)
    return (h["lat"], h["lon"])


# ---------------------------------------------------------------- maps
def heart(x, y, s, color):
    return (f'<path d="M{x:.1f},{y + s * .55:.1f} C{x - s * 1.1:.1f},{y - s * .2:.1f} {x - s * .55:.1f},{y - s * .95:.1f} '
            f'{x:.1f},{y - s * .35:.1f} C{x + s * .55:.1f},{y - s * .95:.1f} {x + s * 1.1:.1f},{y - s * .2:.1f} '
            f'{x:.1f},{y + s * .55:.1f}Z" fill="{color}" stroke="#fff" stroke-width="{s * .18:.1f}"/>')


def map_svg(w, h, bbox, pins, homes=(), routes=(), color="#c65d3b", fs=26, numbered=False):
    """pins: [(label, lat, lon, strong)], homes: [(label, lat, lon)], routes: [[(lat, lon), ...]]"""
    _uid[0] += 1
    cid = f"clip{_uid[0]}"
    lon0, lat0, lon1, lat1 = bbox
    kx = math.cos(math.radians((lat0 + lat1) / 2))
    s = min(w / ((lon1 - lon0) * kx), h / (lat1 - lat0))
    clon, clat = (lon0 + lon1) / 2, (lat0 + lat1) / 2
    proj = lambda lat, lon: (w / 2 + (lon - clon) * kx * s, h / 2 - (lat - clat) * s)
    vl0, vl1 = clon - w / 2 / kx / s - .5, clon + w / 2 / kx / s + .5
    vb0, vb1 = clat - h / 2 / s - .5, clat + h / 2 / s + .5
    out = [f'<defs><clipPath id="{cid}"><rect width="{w:.1f}" height="{h:.1f}"/></clipPath></defs>',
           f'<g clip-path="url(#{cid})"><rect width="{w:.1f}" height="{h:.1f}" fill="{SEA}"/>']
    for kind in ("countries", "lakes"):
        for f in GEO[kind]:
            b = f["bb"]
            if b[2] < vl0 or b[0] > vl1 or b[3] < vb0 or b[1] > vb1:
                continue
            pts, last = [], None
            for lon, lat in f["ring"]:
                x, y = proj(lat, lon)
                if last is None or abs(x - last[0]) + abs(y - last[1]) > 1.2:
                    pts.append(f"{x:.1f},{y:.1f}")
                    last = (x, y)
            if len(pts) < 3:
                continue
            if kind == "lakes":
                out.append(f'<path d="M{" L".join(pts)}Z" fill="{SEA}"/>')
            else:
                fill = LAND_HOME if f["a2"] == HOME_CC else LAND
                out.append(f'<path d="M{" L".join(pts)}Z" fill="{fill}" stroke="{BORDER}" stroke-width="1" '
                           f'stroke-dasharray="3 2" stroke-linejoin="round"/>')
    for route in routes:
        xy = [proj(*q) for q in route]
        d = f"M{xy[0][0]:.1f},{xy[0][1]:.1f}"
        for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            dx, dy = x1 - x0, y1 - y0
            d += f" Q{mx - dy * .18:.1f},{my + dx * .18:.1f} {x1:.1f},{y1:.1f}"
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{max(2.2, fs * .09):.1f}" '
                   f'stroke-dasharray="{fs * .35:.0f} {fs * .3:.0f}" stroke-linecap="round" opacity=".85"/>')
    occupied, marks, labels = [], [], []
    for lab, lat, lon in homes:
        x, y = proj(lat, lon)
        marks.append(heart(x, y, fs * .45, color))
        occupied.append((x - fs * .5, y - fs * .5, x + fs * .5, y + fs * .5))
    for i, (lab, lat, lon, strong) in enumerate(pins):
        x, y = proj(lat, lon)
        r = fs * (.26 if strong else .17)
        marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{color if strong else MUTED}" '
                     f'stroke="#fff" stroke-width="{r * .45:.1f}"/>')
        if numbered:
            marks.append(f'<text x="{x:.1f}" y="{y + r * .45:.1f}" font-family="{STAMP_FONT}" font-weight="700" '
                         f'font-size="{r * 1.2:.1f}" fill="#fff" text-anchor="middle">{i + 1}</text>')
        occupied.append((x - r, y - r, x + r, y + r))
    items = [(lab, *proj(lat, lon), fs, fs * .4) for lab, lat, lon, strong in pins if lab and strong]
    items += [(lab, *proj(lat, lon), fs * .85, fs * .62) for lab, lat, lon in homes if lab]
    items += [(lab, *proj(lat, lon), fs * .8, fs * .3) for lab, lat, lon, strong in pins if lab and not strong]
    for lab, x, y, f, m in items:  # first label position that fits and does not collide
        tw, th = text_w(lab, f), f * .8
        for dx, dy, anchor in ((m, f * .32, "start"), (-m, f * .32, "end"), (0, -m - f * .1, "middle"),
                               (0, m + f * .7, "middle"), (m * .9, -m * .8, "start"), (-m * .9, -m * .8, "end"),
                               (m * .9, m + f * .6, "start"), (-m * .9, m + f * .6, "end")):
            x0 = x + dx - (tw if anchor == "end" else tw / 2 if anchor == "middle" else 0)
            box = (x0, y + dy - th, x0 + tw, y + dy + th * .15)
            if box[0] < 4 or box[2] > w - 4 or box[1] < 4 or box[3] > h - 4:
                continue
            if any(not (box[2] < o[0] or box[0] > o[2] or box[3] < o[1] or box[1] > o[3]) for o in occupied):
                continue
            occupied.append(box)
            DRAWN.add(lab)
            labels.append(f'<text x="{x + dx:.1f}" y="{y + dy:.1f}" font-family="{HAND}" font-size="{f:.1f}" '
                          f'font-weight="600" fill="{INK}" text-anchor="{anchor}" stroke="{PAPER}" '
                          f'stroke-width="{f * .22:.1f}" paint-order="stroke" stroke-linejoin="round">{esc(lab)}</text>')
            break
    out += marks + labels + ["</g>"]
    return "".join(out)


def fit_bbox(points, pad=0.25, min_span=1.0, include=None):
    lats = [q[0] for q in points]
    lons = [q[1] for q in points]
    b = [min(lons), min(lats), max(lons), max(lats)]
    if include:
        b = [min(b[0], include[0]), min(b[1], include[1]), max(b[2], include[2]), max(b[3], include[3])]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    sx = max(b[2] - b[0], min_span / math.cos(math.radians(cy))) * (1 + pad)
    sy = max(b[3] - b[1], min_span * .6) * (1 + pad)
    return (cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2)


def stops(photos, radius=8):
    cl = []
    for p in sorted(photos, key=lambda p: p["date"]):
        if p["lat"] is None:
            continue
        name = nice_place(p) or short_city(p["city"])
        for c in cl:
            if C.km(c["pt"], (p["lat"], p["lon"])) < radius or (name and c["name"] == name):
                c["n"] += 1
                break
        else:
            cl.append({"pt": (p["lat"], p["lon"]), "name": name, "n": 1, "d": p["date"]})
    return cl


# ---------------------------------------------------------------- page elements
def defs():
    return (f'<defs><style>@font-face{{font-family:{HAND};src:url("{C.FONT.as_uri()}")}}</style>'
            '<filter id="sh" x="-10%" y="-10%" width="120%" height="125%"><feDropShadow dx="0" dy="3" stdDeviation="4" '
            'flood-color="#3a2a1a" flood-opacity=".22"/></filter>'
            f'<pattern id="dots" width="30" height="30" patternUnits="userSpaceOnUse"><circle cx="15" cy="15" r="1.3" '
            f'fill="{DOTS}"/></pattern></defs>')


def paper():
    e = f'x="{-B - 2:.2f}" y="{-B - 2:.2f}" width="{S + 2 * B + 4:.2f}" height="{S + 2 * B + 4:.2f}"'
    return f'<rect {e} fill="{PAPER}"/><rect {e} fill="url(#dots)"/>'


def tape(x, y, w, seed, angle=None):
    c = TAPES[int(h01(seed, "tc") * len(TAPES))]
    a = angle if angle is not None else (h01(seed, "ta") - .5) * 16
    th = w * .26
    return (f'<rect x="{x - w / 2:.1f}" y="{y - th / 2:.1f}" width="{w:.1f}" height="{th:.1f}" fill="{c}" opacity=".78" '
            f'transform="rotate({a:.1f} {x:.1f} {y:.1f})"/>')


def tile_aspect(img_aspect):
    return 1 / ((1 - 2 * B_SIDE) / img_aspect + B_SIDE + B_BOTTOM)


def polaroid(x, y, w, seed, inner, cap, img_aspect, tape_on=True):
    b, bb = w * B_SIDE, w * B_BOTTOM
    iw = w - 2 * b
    ih = iw / img_aspect
    h = ih + b + bb
    rot = (h01(seed, "rot") - .5) * 5
    cx, cy = x + w / 2, y + h / 2
    g = [f'<g transform="rotate({rot:.2f} {cx:.1f} {cy:.1f})">',
         f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#fffdf8" filter="url(#sh)"/>',
         f'<g transform="translate({x + b:.1f} {y + b:.1f})">{inner(iw, ih)}</g>']
    if cap:
        fs = min(bb * .58, (w - 2 * b) / max(1, len(cap)) * 2.1)
        g.append(f'<text x="{cx:.1f}" y="{y + b + ih + bb * .66:.1f}" font-family="{HAND}" font-size="{fs:.1f}" '
                 f'fill="{INK}" text-anchor="middle">{esc(cap)}</text>')
    if tape_on:
        mode = int(h01(seed, "tm") * 3)
        if mode == 0:
            g.append(tape(cx, y + 2, w * .32, seed))
        elif mode == 1:
            g.append(tape(x + w * .08, y + w * .06, w * .22, seed + "a", -40))
            g.append(tape(x + w * .92, y + w * .06, w * .22, seed + "b", 40))
    g.append("</g>")
    return "".join(g), (x, y, w, h)


def photo_inner(path):
    href = path.as_uri()
    return lambda iw, ih: f'<image href="{href}" width="{iw:.1f}" height="{ih:.1f}" preserveAspectRatio="xMidYMid slice"/>'


def stamp(cx, cy, r, country, city, when, color, seed):
    _uid[0] += 1
    u = _uid[0]
    rot = (h01(seed, "st") - .5) * 36
    city_fs = min(r * .42, r * 1.55 / max(3, len(city)) * 1.9)
    return (f'<g transform="rotate({rot:.1f} {cx:.1f} {cy:.1f})" opacity=".76" style="mix-blend-mode:multiply" '
            f'fill="none" stroke="{color}">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke-width="{r * .06:.1f}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * .78:.1f}" stroke-width="{r * .025:.1f}"/>'
            f'<path id="ta{u}" d="M{cx - r * .89:.1f},{cy} A{r * .89:.1f},{r * .89:.1f} 0 0 1 {cx + r * .89:.1f},{cy}"/>'
            f'<path id="tb{u}" d="M{cx - r * .89:.1f},{cy} A{r * .89:.1f},{r * .89:.1f} 0 0 0 {cx + r * .89:.1f},{cy}"/>'
            f'<text font-family="{STAMP_FONT}" font-weight="700" font-size="{r * .2:.1f}" fill="{color}" stroke="none" '
            f'letter-spacing="{r * .03:.1f}"><textPath href="#ta{u}" startOffset="50%" text-anchor="middle" '
            f'dominant-baseline="middle">{esc(country)}</textPath></text>'
            f'<text font-family="{STAMP_FONT}" font-weight="700" font-size="{r * .17:.1f}" fill="{color}" stroke="none" '
            f'letter-spacing="{r * .03:.1f}"><textPath href="#tb{u}" startOffset="50%" text-anchor="middle" '
            f'dominant-baseline="middle">{esc(when)}</textPath></text>'
            f'<text x="{cx}" y="{cy + city_fs * .36:.1f}" font-family="{STAMP_FONT}" font-weight="700" '
            f'font-size="{city_fs:.1f}" fill="{color}" stroke="none" text-anchor="middle">{esc(city)}</text>'
            f'<text x="{cx}" y="{cy - r * .4:.1f}" font-size="{r * .2:.1f}" fill="{color}" stroke="none" '
            f'text-anchor="middle">★</text></g>')


def stamp_text(cid):
    """(country line, place line) for a trip's passport stamp, or None. Auto for trips with a night away."""
    t = trip_cfg(cid)
    if t.get("razitko") is False:
        return None
    if isinstance(t.get("razitko"), list):
        return tuple(t["razitko"])
    if chapters.get(cid, {}).get("kind") != "cesta":
        return None
    c = collections.Counter(p["country"] for p in trip_picks(cid) if p["country"])
    country = c.most_common(1)[0][0] if c else ""
    return country.upper(), trip_short(cid).upper()


# ---------------------------------------------------------------- tiles & justified layout
class Tile:
    def __init__(self, kind, seed, aspect, inner, cap, photo=None, trip=None):
        self.kind, self.seed, self.aspect, self.inner, self.cap = kind, seed, aspect, inner, cap
        self.photo, self.trip = photo, trip


def photo_tile(p):
    path = image_for(p)
    w, h = p["dims"]
    return Tile("photo", p["uuid"], w / h, photo_inner(path), caption(p), photo=p, trip=p["chapter"])


def has_map(cid):
    return chapters.get(cid, {}).get("kind") == "cesta" and trip_cfg(cid).get("mapa", True)


def itinerary_tile(cid, color):
    chosen = [c["pt"] for c in stops(trip_picks(cid))]
    if not chosen:
        return None
    spread = max((C.km(a, b) for a in chosen for b in chosen), default=0)
    st = route_stops(cid) if spread >= 60 or trip_cfg(cid).get("trasa") else []
    pts = [c["pt"] for c in st] or chosen
    if len(st) >= 2 and not trip_cfg(cid).get("cil"):
        # road trip: zoom to the region, stops joined by the route
        bbox = fit_bbox(pts, pad=.45, min_span=1.1)
        pins = [(c["name"], *c["pt"], True) for c in st]
        inner = lambda iw, ih: map_svg(iw, ih, bbox, pins, routes=[pts], color=color, fs=iw / 15)
    else:
        # one place: show where it is, with a dashed line from home
        home = home_pt(int(cid[:4]))
        dest = (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts))
        bbox = fit_bbox([home, dest], pad=.5, min_span=3.0)
        pins = [(trip_short(cid), *dest, True)]
        inner = lambda iw, ih: map_svg(iw, ih, bbox, pins, homes=[("", *home)], routes=[[home, dest]],
                                       color=color, fs=iw / 13)
    return Tile("map", "map" + cid, 1.3, inner, trip_name(cid), trip=cid)


def justify(tiles, W, H, gap, max_h):
    """Best split of tiles into up to 3 rows of up to 4, rows scaled to full width (justified gallery)."""
    n = len(tiles)
    if not n:
        return []
    best = None
    for mask in range(1 << (n - 1)):
        rows, cur = [], [tiles[0]]
        for i in range(1, n):
            if mask >> (i - 1) & 1:
                rows.append(cur)
                cur = []
            cur.append(tiles[i])
        rows.append(cur)
        if len(rows) > 3 or any(len(r) > 4 for r in rows):
            continue
        hs = [min(max_h, (W - gap * (len(r) - 1)) / sum(tile_aspect(t.aspect) for t in r)) for r in rows]
        total = sum(hs) + gap * (len(rows) - 1)
        sc = min(1, H / total)
        area = sum(sc * sc * hh * hh * sum(tile_aspect(t.aspect) for t in r) for r, hh in zip(rows, hs))
        score = area / (W * H) - .04 * (max(hs) / min(hs) - 1)
        if best is None or score > best[0]:
            best = (score, rows, [hh * sc for hh in hs])
    _, rows, hs = best
    y = (H - sum(hs) - gap * (len(rows) - 1)) / 2
    placed = []
    for r, hh in zip(rows, hs):
        widths = [hh * tile_aspect(t.aspect) for t in r]
        x = (W - sum(widths) - gap * (len(r) - 1)) / 2
        for t, ww in zip(r, widths):
            placed.append((t, x, y, ww))
            x += ww + gap
        y += hh + gap
    return placed


def tiles_svg(tiles, ox, oy, W, H, max_h, stamped, color):
    out, first_rect = [], {}
    for t, x, y, w in justify(tiles, W, H, gap=46, max_h=max_h):
        svg, rect = polaroid(ox + x, oy + y, w, t.seed, t.inner, t.cap, t.aspect, tape_on=h01(t.seed, "tape") < .55)
        out.append(svg)
        if t.trip not in stamped and t.trip not in first_rect and stamp_text(t.trip):
            first_rect[t.trip] = rect
    for cid, (x, y, w, h) in first_rect.items():
        country, city = stamp_text(cid)
        when = f"{ROMAN[int(cid[5:7]) - 1]} · {cid[:4]}"
        r = 56
        out.append(stamp(round(x + w - r * .35), round(y + r * .35), r, country, city, when, color, cid))
        stamped.add(cid)
    return "".join(out)


# ---------------------------------------------------------------- pages
def doc(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" '
            f'viewBox="{-B:.3f} {-B:.3f} {S + 2 * B:.3f} {S + 2 * B:.3f}">{defs()}{body}</svg>')


def year_color(y):
    return ACCENTS[(int(y) - FIRST_YEAR) % len(ACCENTS)]


def year_map(y, ps, w, h, color):
    hl = home_pt(int(y))
    pins, seen = [], []
    for c in stops(ps, radius=15):
        if C.km(c["pt"], hl) < 30 or any(C.km(c["pt"], s) < 15 for s in seen):
            continue
        seen.append(c["pt"])
        pins.append((c["name"], *c["pt"], C.km(c["pt"], hl) > 60))
    pts = [q[1:3] for q in pins] + [hl]
    bbox = fit_bbox(pts, pad=.18, min_span=1.0, include=HOME_BBOX)
    routes = [[hl, q[1:3]] for q in pins if q[3]]
    return map_svg(w, h, bbox, pins, homes=[("", *hl)], routes=routes, color=color, fs=24)


def wrap(text, width, max_lines):
    lines, cur = [], ""
    for wd in text.split():
        if len(cur + " " + wd) > width and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    if cur:
        lines.append(cur)
    return lines[:max_lines]


def opener_page(y, ps_year, tiles, stamped):
    color = year_color(y)
    body = [paper(), f'<text x="70" y="230" font-family="{HAND}" font-size="210" font-weight="700" fill="{color}">{y}</text>']
    for i, ln in enumerate(wrap((CFG.get("roky") or {}).get(y, ""), 22, 3)):
        body.append(f'<text x="78" y="{300 + i * 50}" font-family="{HAND}" font-size="46" fill="{INK}">{esc(ln)}</text>')
    mw, mh, mx, my = 560, 400, 575, 60
    inner = year_map(y, ps_year, mw - 24, mh - 24, color)
    body.append(f'<g transform="rotate(1.8 {mx + mw / 2} {my + mh / 2})"><rect x="{mx}" y="{my}" width="{mw}" '
                f'height="{mh}" fill="#fffdf8" filter="url(#sh)"/><g transform="translate({mx + 12} {my + 12})">{inner}</g>'
                f'{tape(mx + mw / 2, my + 4, 150, "ym" + y, -3)}</g>')
    body.append(tiles_svg(tiles, 70, 500, S - 140, S - 500 - 60, 400, stamped, color))
    return doc("".join(body))


def grid_page(y, tiles, stamped):
    return doc(paper() + tiles_svg(tiles, 70, 60, S - 140, S - 120, 470, stamped, year_color(y)))


ALIGN = {"nahore": "xMidYMin", "dole": "xMidYMax", "vlevo": "xMinYMid", "vpravo": "xMaxYMid", "stred": "xMidYMid"}


def full_page(p, entry):
    path = image_for(p)
    cap = entry["popisek"] if "popisek" in entry else caption(p)
    body = [paper(),
            f'<image href="{path.as_uri()}" x="{-B:.2f}" y="{-B:.2f}" width="{S + 2 * B:.2f}" height="{S + 2 * B:.2f}" '
            f'preserveAspectRatio="{ALIGN.get(entry.get("zarovnani", "stred"), "xMidYMid")} slice"/>']
    if cap:
        fs = 44
        tw = text_w(cap, fs) + 60
        x, y = 70, S - 150
        body.append(f'<g transform="rotate(-2.5 {x + tw / 2} {y + 40})"><rect x="{x}" y="{y}" width="{tw:.0f}" height="78" '
                    f'fill="#fffdf8" filter="url(#sh)"/><text x="{x + 30}" y="{y + 54}" font-family="{HAND}" '
                    f'font-size="{fs}" fill="{INK}">{esc(cap)}</text>{tape(x + tw / 2, y, 120, cap)}</g>')
    return doc("".join(body))


def years_span():
    ys = sorted({p["date"][:4] for p in picks})
    return ys[0], ys[-1]


def title_page(p):
    a, b = years_span()
    body = [paper(),
            f'<text x="600" y="215" font-family="{HAND}" font-size="140" font-weight="700" fill="{INK}" '
            f'text-anchor="middle">{esc(CFG.get("titul", ""))}</text>',
            f'<text x="600" y="290" font-family="{HAND}" font-size="54" fill="{ACCENTS[0]}" text-anchor="middle">'
            f'{esc(CFG.get("podtitul", f"{a} – {b}"))}</text>']
    if p:
        path = image_for(p)
        w, h = p["dims"]
        svg, _ = polaroid(390, 360, 420, "title", photo_inner(path), "", w / h)
        body.append(svg)
    body.append(heart(860, 1000, 22, ACCENTS[0]))
    return doc("".join(body))


def overview_pins():
    """Trips abroad grouped by place: [(label 'Chorvatsko '19 '22', lat, lon)]. Override: kniha.json → prehled."""
    if CFG.get("prehled"):
        return [tuple(x) for x in CFG["prehled"]]
    groups = []
    for cid in sorted({p["chapter"] for p in picks if is_trip(p["chapter"])}):
        ps = [p for p in trip_picks(cid) if p["lat"] is not None]
        cc = collections.Counter(p["cc"] for p in ps).most_common(1)
        if not ps or not cc or cc[0][0] == HOME_CC:
            continue
        pt = (sum(p["lat"] for p in ps) / len(ps), sum(p["lon"] for p in ps) / len(ps))
        yy = "'" + cid[2:4]
        for g in groups:
            if C.km(g["pt"], pt) < 150:
                if yy not in g["years"]:
                    g["years"].append(yy)
                break
        else:
            groups.append({"name": trip_short(cid), "pt": pt, "years": [yy]})
    return [(f"{g['name']} {' '.join(g['years'])}", *g["pt"]) for g in groups]


def stats_values():
    out = []
    for value, label in (tx("cisla", None) or [["auto:roky", "let"], ["auto:zeme", "zemí"], ["auto:vylety", "výletů"]])[:5]:
        if value == "auto:roky":
            a, b = years_span()
            value = str(int(b) - int(a) + 1)
        elif value == "auto:zeme":
            value = str(len({p["cc"] for p in picks if p["cc"] and p["cc"] != HOME_CC and is_trip(p["chapter"])}))
        elif value == "auto:vylety":
            n = len(P.read("vylety.json", required=False) or [])
            value = f"{n // 10 * 10}+" if n >= 20 else str(n)
        elif value == "auto:fotky":
            value = str(len(picks))
        out.append((value, label))
    return out


def overview_pages():
    last_home = C.homes(CFG)[-1]
    hp = (last_home["lat"], last_home["lon"])
    pins_abroad = overview_pins()
    left = [paper(), f'<text x="70" y="150" font-family="{HAND}" font-size="96" font-weight="700" fill="{INK}">'
                     f'{esc(tx("mapa_svet", "Kam jsme se spolu podívali"))}</text>']
    pins = [(lab, lat, lon, True) for lab, lat, lon in pins_abroad]
    bbox = fit_bbox([q[1:3] for q in pins_abroad] + [hp], pad=.12, min_span=8)
    routes = [[hp, (lat, lon)] for _, lat, lon in pins_abroad]
    inner = map_svg(1036, 900, bbox, pins, homes=[("", *hp)], routes=routes, color=ACCENTS[0], fs=27)
    left.append(f'<g transform="rotate(-1 600 700)"><rect x="70" y="210" width="1060" height="924" fill="#fffdf8" '
                f'filter="url(#sh)"/><g transform="translate(82 222)">{inner}</g>'
                f'{tape(220, 214, 170, "ov1", -8)}{tape(980, 214, 170, "ov2", 7)}</g>')

    right = [paper(), f'<text x="70" y="150" font-family="{HAND}" font-size="96" font-weight="700" fill="{INK}">'
                      f'{esc(tx("mapa_domov", "…a doma"))}</text>']
    # every outing in the home country (tools/vylety.py) + the chosen photos taken there
    outings = [{"date": o["start"], "lat": o["lat"], "lon": o["lon"], "aoi": [o["place"]], "city": None}
               for o in P.read("vylety.json", required=False) or [] if o.get("cc") == HOME_CC and "lat" in o]
    home_ps = [p for p in picks if p["lat"] is not None and p["cc"] == HOME_CC] + outings
    homes = {}
    for h in C.homes(CFG):
        homes.setdefault(h["nazev"], (h["lat"], h["lon"]))
    pins = [(c["name"], *c["pt"], True) for c in stops(home_ps, radius=9)
            if not any(C.km(c["pt"], h) < 18 for h in homes.values())]
    bbox = HOME_BBOX or fit_bbox([q[1:3] for q in pins] + list(homes.values()), pad=.1)
    inner = map_svg(1036, 640, bbox, pins, homes=[(n, *v) for n, v in homes.items()], color=ACCENTS[1], fs=25)
    right.append(f'<g transform="rotate(1.2 600 520)"><rect x="70" y="200" width="1060" height="664" fill="#fffdf8" '
                 f'filter="url(#sh)"/><g transform="translate(82 212)">{inner}</g>{tape(600, 204, 190, "ov3", 2)}</g>')
    stats = stats_values()
    x0 = 600 - len(stats) * 105
    for i, (num, label) in enumerate(stats):
        cx = x0 + i * 210 + 105
        right.append(f'<text x="{cx}" y="1015" font-family="{HAND}" font-size="110" font-weight="700" '
                     f'fill="{ACCENTS[i % len(ACCENTS)]}" text-anchor="middle">{esc(num)}</text>'
                     f'<text x="{cx}" y="1075" font-family="{HAND}" font-size="40" fill="{INK}" '
                     f'text-anchor="middle">{esc(label)}</text>')
    return doc("".join(left)), doc("".join(right))


def end_page():
    return doc(paper() + f'<text x="600" y="590" font-family="{HAND}" font-size="96" font-weight="700" fill="{INK}" '
                         f'text-anchor="middle">{esc(tx("konec", "Pokračování příště…"))}</text>'
               + heart(600, 690, 30, ACCENTS[0]))


# ---------------------------------------------------------------- book assembly
def chunks(seq, size, n=None):
    n = n or max(1, math.ceil(len(seq) / size))
    base, extra = divmod(len(seq), n)
    out, i = [], 0
    for k in range(n):
        m = base + (1 if k < extra else 0)
        out.append(seq[i:i + m])
        i += m
    return out


def entries(name):
    """kniha.json list of photo refs or {"foto": ref, "popisek": .., "zarovnani": ..} -> {(chapter, tile): entry}"""
    out = {}
    for e in CFG.get(name) or []:
        e = {"foto": e} if isinstance(e, str) else dict(e)
        out[C.ref(e["foto"])] = e
    return out


def find(k, what):
    p = next((p for p in picks if key(p) == k), None)
    if p is None:
        sys.exit(f"{what}: fotka {k[0]}/{k[1]} není ve výběru (vyber.txt).")
    return p


def build(extra_pages=0):
    full = entries("cela_strana")
    closing = entries("zaver")
    for k in list(full) + list(closing):
        find(k, "cela_strana/zaver")
    title = find(C.ref(CFG["titulni_foto"]), "titulni_foto") if CFG.get("titulni_foto") else None
    skip = set(closing) | ({key(title)} if title else set())
    body = [p for p in picks if key(p) not in skip]
    by_year = collections.defaultdict(list)
    for p in sorted(body, key=lambda p: p["date"]):
        by_year[p["date"][:4]].append(p)

    pages = [title_page(title), *overview_pages()]
    stamped = set()
    for y, ps in sorted(by_year.items()):
        seq = []
        for p in ps:
            if key(p) in full:
                seq.append(("full", p))
                continue
            if has_map(p["chapter"]) and not any(k == "tile" and t.kind == "map" and t.trip == p["chapter"] for k, t in seq):
                mt = itinerary_tile(p["chapter"], year_color(y))
                if mt:
                    seq.append(("tile", mt))
            seq.append(("tile", photo_tile(p)))
        tiles = [t for k, t in seq if k == "tile"]
        heroes = [p for k, p in seq if k == "full"]
        extra = extra_pages if y == max(by_year) else 0
        if len(tiles) <= 6 and not extra:
            groups = [tiles]
        else:
            k = max(1, math.ceil((len(tiles) - 6) / PER_PAGE)) + extra
            o = min(6, max(3, len(tiles) - PER_PAGE * k))
            groups = [tiles[:o]] + [g for g in chunks(tiles[o:], PER_PAGE, k) if g]
        for gi, g in enumerate(groups):
            pages.append(opener_page(y, ps, g, stamped) if gi == 0 else grid_page(y, g, stamped))
            last = max((t.photo["date"] for t in g if t.photo), default="")
            for hp in [h for h in heroes if h["date"] <= last]:
                pages.append(full_page(hp, full[key(hp)]))
                heroes.remove(hp)
        pages += [full_page(hp, full[key(hp)]) for hp in heroes]

    # page 1 is a right-hand page, so even pages are on the left. Two or more closing photos: the first two face each other.
    if len(closing) >= 2 and (len(pages) + 1) % 2 != 0:
        if extra_pages:
            return None  # spreading the last year over one more page did not fix it
        alt = build(1)
        if alt is not None:
            return alt
        pages.append(doc(paper() + heart(600, 600, 30, ACCENTS[0])))  # a quiet page with a heart instead
    pages += [full_page(find(k, "zaver"), e) for k, e in closing.items()]
    pages.append(end_page())
    return pages


def render(pages):
    C.need("magick")
    chrome = C.chrome()
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*"):
        f.unlink()
    svgdir = P.dir / "kniha" / "svg"
    svgdir.mkdir(parents=True, exist_ok=True)
    scale = PRINT_PX / S if FINAL else 1
    files = []
    for i, svg in enumerate(pages, 1):
        sv = svgdir / f"str-{i:02d}.svg"
        sv.write_text(svg)
        png = OUT / f"str-{i:02d}.png"
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--hide-scrollbars",
                        f"--window-size={S},{S}", f"--force-device-scale-factor={scale}", "--virtual-time-budget=4000",
                        f"--screenshot={png}", sv.as_uri()], check=True, capture_output=True)
        jpg = png.with_suffix(".jpg")
        subprocess.run(["magick", str(png), "-quality", "95" if FINAL else "88", str(jpg)], check=True)
        png.unlink()
        files.append(jpg)
        print(f"strana {i}/{len(pages)}", end="\r", flush=True)
    print()
    if not FINAL:  # spreads as they will be bound: an empty page (inside of the cover) first
        blank = OUT / "_blank.jpg"
        subprocess.run(["magick", "-size", f"{S}x{S}", "xc:#e9e5df", str(blank)], check=True)
        seq = [blank, *files] + ([blank] if len(files) % 2 == 0 else [])
        spreads = []
        for k in range(0, len(seq), 2):
            sp = OUT / f"dvoustrana-{k // 2 + 1:02d}.jpg"
            subprocess.run(["magick", str(seq[k]), str(seq[k + 1]), "+append", "-resize", "50%", str(sp)], check=True)
            spreads.append(sp)
        blank.unlink()
        subprocess.run(["magick", "montage", *map(str, spreads), "-tile", "4x", "-geometry", "600x300+10+10",
                        "-background", "#d9d3ca", str(OUT / "prehled.jpg")], check=True)
    print(f"{len(files)} stran → {OUT}")
    check = sorted(n for n in DRAWN if n in UNCURATED)
    if check:
        print("Názvy míst převzaté z Fotek (zkontroluj, jak se ukážou; oprava v kniha.json → nazvy_mist):")
        print("  " + ", ".join(f"{n} ({UNCURATED[n]})" if UNCURATED[n] != n else n for n in check))
    return files


if __name__ == "__main__":
    ap = C.parser(__doc__)
    ap.add_argument("--tisk", action="store_true", help="tiskové rozlišení z originálů")
    a = ap.parse_args()
    setup(a.projekt, final=a.tisk)
    render(build())
