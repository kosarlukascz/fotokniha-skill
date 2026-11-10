"""Shared helpers for the fotokniha tools: project paths, config, print profiles, geo math, map data."""
import argparse
import collections
import json
import math
import os
import pathlib
import shutil
import statistics
import sys
import urllib.request

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"
FONT = ASSETS / "Caveat.ttf"
LABEL_FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"  # contact-sheet numbers (macOS)
GEO_CACHE = pathlib.Path.home() / ".cache" / "fotokniha" / "svet.json"
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson"

# Print profiles. Only add a profile after checking the printer's own spec page; the numbers must be exact.
PROFILES = {
    "saal-30x30-professional": {
        "popis": "Saal Digital, Fotokniha Professional Line 30 × 30 cm (layflat), nahrání PDF",
        "strana_px": 3543,      # one page incl. bleed, 300 dpi (29.4 cm trim + 2 × 3 mm)
        "spadavka_px": 35,      # bleed on each outer edge
        "dpi": 300,
        "dvoustrany": True,     # one PDF page = one double spread, no bleed at the layflat fold
        "vnitrni_desky": True,  # 1st page of the 1st spread = inside of the front cover, last page = inside of the back cover
        "stran_min": 26,
        "stran_max": 130,
        "obalka": {"w": 4583, "h": 4819, "spadavka": 47, "dpi": 400},  # front cover only
        "overeno": "2026-11-09, saal-digital.cz/fotokniha/profesionalni-zona/",
    },
}

BAD_LABELS = {  # Apple Photos labels come in the system language
    "Dokument", "Text", "Účtenka", "Snímek obrazovky", "Rukopis", "Tabule", "Monitor", "Počítač",
    "Document", "Receipt", "Screenshot", "Handwriting", "Whiteboard", "Computer",
}


# ---------------------------------------------------------------- project
def parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--projekt", default=".", help="složka projektu fotoknihy (výchozí: aktuální složka)")
    return p


class Project:
    def __init__(self, path):
        self.dir = pathlib.Path(path).expanduser().resolve()
        self.data = self.dir / "data"

    @property
    def cfg_path(self):
        return self.dir / "kniha.json"

    def cfg(self, required=True):
        if not self.cfg_path.exists():
            if required:
                sys.exit(f"Chybí {self.cfg_path}. Zkopíruj šablonu template/kniha.example.json a vyplň ji.")
            return {}
        try:
            return json.loads(self.cfg_path.read_text())
        except json.JSONDecodeError as e:
            sys.exit(f"kniha.json není platný JSON: {e}")

    def read(self, name, required=True):
        f = self.data / name
        if not f.exists():
            if required:
                sys.exit(f"Chybí {f}. Spusť nejdřív předchozí krok.")
            return None
        return json.loads(f.read_text())

    def write(self, name, obj, indent=None):
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / name).write_text(json.dumps(obj, ensure_ascii=False, indent=indent))


def people(cfg):
    ps = cfg.get("osoby") or []
    if not ps:
        sys.exit('V kniha.json chybí "osoby" (jména lidí přesně jako v aplikaci Fotky, první je hlavní postava knihy).')
    return ps


def profile(cfg):
    t = dict(cfg.get("tisk") or {})
    name = t.get("profil", "saal-30x30-professional")
    if name not in PROFILES and name != "vlastni":
        sys.exit(f"Neznámý tiskový profil {name!r}. Známé: {', '.join(PROFILES)} nebo \"vlastni\".")
    prof = dict(PROFILES.get(name, {}))
    prof.update({k: v for k, v in t.items() if k not in ("profil", "obalka_foto", "obalka_text")})
    for k in ("strana_px", "spadavka_px", "dpi"):
        if k not in prof:
            sys.exit(f'Tiskový profil "vlastni" potřebuje v kniha.json → tisk hodnotu {k}.')
    prof.setdefault("dvoustrany", False)
    prof.setdefault("vnitrni_desky", False)
    prof["nazev"] = name
    return prof


def ref(s):
    """'2019-07-12/08' -> ('2019-07-12', '08')"""
    cid, _, tile = str(s).rpartition("/")
    if not cid:
        sys.exit(f"Odkaz na fotku {s!r} musí mít tvar kapitola/číslo, např. 2019-07-12/08.")
    return cid, tile.zfill(2)


def homes(cfg):
    hs = cfg.get("domovy") or []
    if not hs:
        sys.exit('V kniha.json chybí "domovy" (kde jste bydleli a kdy). Návrh vypíše tools/domov.py.')
    return hs


def home_for(cfg, year):
    hs = homes(cfg)
    for h in hs:
        if int(h.get("od", 0)) <= year <= int(h.get("do", 9999)):
            return h
    return min(hs, key=lambda h: min(abs(year - int(h.get("od", year))), abs(year - int(h.get("do", year)))))


# ---------------------------------------------------------------- geo
def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(x))


def median_pt(pts):
    return (statistics.median(p[0] for p in pts), statistics.median(p[1] for p in pts))


def load_geo():
    """World countries + lakes (Natural Earth 1:10m, public domain), simplified and cached in ~/.cache/fotokniha."""
    if GEO_CACHE.exists():
        return json.loads(GEO_CACHE.read_text())
    GEO_CACHE.parent.mkdir(parents=True, exist_ok=True)
    print("Stahuji mapové podklady Natural Earth (jednou, asi 18 MB)…", flush=True)

    def rings(g):
        if g["type"] == "Polygon":
            return [g["coordinates"][0]]
        if g["type"] == "MultiPolygon":
            return [poly[0] for poly in g["coordinates"]]
        return []

    out = {"countries": [], "lakes": []}
    for name, kind in (("ne_10m_admin_0_countries", "countries"), ("ne_10m_lakes", "lakes")):
        with urllib.request.urlopen(NE_URL.format(name), timeout=120) as r:
            features = json.load(r)["features"]
        for f in features:
            a2 = f["properties"].get("ISO_A2_EH") or f["properties"].get("ISO_A2")
            for ring in rings(f["geometry"]):
                lons, lats = [q[0] for q in ring], [q[1] for q in ring]
                simp = []
                for lon, lat in ring:
                    if not simp or abs(lon - simp[-1][0]) + abs(lat - simp[-1][1]) > 0.004:
                        simp.append((round(lon, 3), round(lat, 3)))
                if len(simp) >= 3:
                    out[kind].append({"a2": a2, "bb": [min(lons), min(lats), max(lons), max(lats)], "ring": simp})
    GEO_CACHE.write_text(json.dumps(out, separators=(",", ":")))
    return out


def country_bbox(geo, a2):
    """Bounding box of a country's largest polygon (ignores overseas territories)."""
    best = None
    for f in geo["countries"]:
        if f["a2"] != a2:
            continue
        b = f["bb"]
        area = (b[2] - b[0]) * (b[3] - b[1])
        if best is None or area > best[0]:
            best = (area, b)
    if best is None:
        return None
    b = best[1]
    px, py = (b[2] - b[0]) * .03, (b[3] - b[1]) * .03
    return (b[0] - px, b[1] - py, b[2] + px, b[3] + py)


# ---------------------------------------------------------------- photos
def rank(r, ps):
    """Apple's aesthetic score + bonuses for the book's people, favourites; penalties for documents and shared photos."""
    s = r.get("score") or {}
    present = set(r["persons"])
    v = (s.get("overall") or 0) + 0.5 * (s.get("curation") or 0)
    if ps[0] in present and any(p in present for p in ps[1:]):
        v += 0.35
    elif ps[0] in present:
        v += 0.2
    if r.get("fav"):
        v += 0.3
    if set(r.get("labels") or []) & BAD_LABELS:
        v -= 1.0
    if r.get("shared"):
        v -= 0.2
    return v


def fotek(n):
    return f"{n} fotka" if n == 1 else (f"{n} fotky" if 2 <= n <= 4 else f"{n} fotek")


def by_day(rows):
    d = collections.defaultdict(list)
    for r in rows:
        d[r["date"][:10]].append(r)
    return d


# ---------------------------------------------------------------- external programs
def chrome():
    cands = [os.environ.get("FOTOKNIHA_CHROME", ""),
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Chromium.app/Contents/MacOS/Chromium",
             "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
             "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"]
    for c in cands:
        if c and pathlib.Path(c).exists():
            return c
    sys.exit("Nenašel jsem Google Chrome (ani Chromium/Edge/Brave). Je potřeba na vykreslení stran: brew install --cask google-chrome")


def need(*programs):
    missing = [p for p in programs if not shutil.which(p)]
    if missing:
        brew = {"magick": "imagemagick"}
        sys.exit(f"Chybí program(y): {', '.join(missing)}. Na Macu: brew install {' '.join(brew.get(p, p) for p in missing)}")
