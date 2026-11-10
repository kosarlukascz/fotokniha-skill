"""Read metadata of all photos from Apple Photos into data/fotky.json (read-only, nothing in Photos changes).

Run:  uv run --python 3.12 --with osxphotos python3 SKILL_DIR/tools/nacti_fotky.py --projekt DIR [--od 2014-01-01] [--do 2026-12-31]
Prints the people named in Photos, so you can put the exact names into kniha.json → osoby.
"""
import collections
import datetime as dt
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

try:
    import osxphotos
except ImportError:
    sys.exit("Spusť přes: uv run --python 3.12 --with osxphotos python3 …/nacti_fotky.py")

SCORE_FIELDS = [
    "overall", "curation", "promotion", "highlight_visibility", "behavioral",
    "failure", "harmonious_color", "immersiveness", "interaction",
    "interesting_subject", "intrusive_object_presence", "lively_color", "low_light", "noise",
    "pleasant_camera_tilt", "pleasant_composition", "pleasant_lighting",
    "pleasant_pattern", "pleasant_perspective", "pleasant_post_processing",
    "pleasant_reflection", "pleasant_symmetry", "sharply_focused_subject",
    "tastefully_blurred", "well_chosen_subject", "well_framed_subject",
    "well_timed_shot",
]


def place_info(p):
    pl = p.place
    if not pl:
        return None
    n = pl.names
    first = lambda xs: xs[0] if xs else None
    return {
        "name": pl.name,
        "country": pl.country_code,
        "country_name": first(n.country),
        "state": first(n.state_province),
        "city": first(n.city),
        "sub_admin": first(n.sub_administrative_area),
        "aoi": n.area_of_interest,
        "region": n.region,
        "water": (n.body_of_water or []) + (n.ocean or []) + (n.inland_water or []),
    }


def search(p):
    s = p.search_info
    if not s:
        return None
    return {"venues": s.venues, "activities": s.activities, "holidays": s.holidays, "season": s.season}


def main():
    ap = C.parser(__doc__)
    ap.add_argument("--od", help="od data (RRRR-MM-DD), jinak z kniha.json → od")
    ap.add_argument("--do", dest="do_", help="do data (RRRR-MM-DD), jinak z kniha.json → do")
    a = ap.parse_args()
    P = C.Project(a.projekt)
    cfg = P.cfg(required=False)
    start = dt.datetime.fromisoformat(a.od or cfg.get("od") or "2000-01-01")
    end = dt.datetime.fromisoformat(a.do_ or cfg.get("do") or "2100-01-01") + dt.timedelta(days=1)

    print("Načítám knihovnu Fotek (u velké knihovny to trvá pár minut)…", flush=True)
    db = osxphotos.PhotosDB()
    rows = []
    for p in db.photos(images=True, movies=False):
        d = p.date.replace(tzinfo=None)
        if not (start <= d < end) or p.hidden or p.intrash or p.screenshot:
            continue
        sc = p.score
        lat, lon = p.location
        rows.append({
            "uuid": p.uuid,
            "date": p.date.isoformat(),
            "lat": lat,
            "lon": lon,
            "place": place_info(p),
            "persons": [x.strip() for x in p.persons if x != "_UNKNOWN_"],
            "fav": p.favorite,
            "selfie": p.selfie,
            "shared": p.shared,
            "w": p.width,
            "h": p.height,
            "labels": p.labels,
            "score": {f: (round(v, 4) if isinstance(v, (int, float)) else None)
                      for f in SCORE_FIELDS for v in [getattr(sc, f, None)]} if sc else None,
            "search": search(p),
            "deriv": p.path_derivatives[0] if p.path_derivatives else "",
            "local": bool(p.path),
        })
    rows.sort(key=lambda r: r["date"])
    P.write("fotky.json", rows)
    print(f"{len(rows)} fotek → {P.data / 'fotky.json'}")
    print(f"s polohou: {sum(r['lat'] is not None for r in rows)}, s náhledem: {sum(bool(r['deriv']) for r in rows)}")
    years = collections.Counter(r["date"][:4] for r in rows)
    print("po rocích:", ", ".join(f"{y}: {n}" for y, n in sorted(years.items())))
    persons = collections.Counter(x for r in rows for x in r["persons"])
    print("\nLidé a zvířata pojmenovaní ve Fotkách (počet fotek):")
    for name, n in persons.most_common(30):
        print(f"  {n:6}  {name}")


main()
