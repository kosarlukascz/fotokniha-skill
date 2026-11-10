"""Suggest where the people lived (and other places that are 'home', like parents) from evening photos.

Prints a JSON snippet for kniha.json → "domovy" and "dalsi_mista". Always confirm it with the user.
Run:  python3 SKILL_DIR/tools/domov.py --projekt DIR
"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402


def evening(r):
    h = int(r["date"][11:13])
    return r["lat"] is not None and (h >= 19 or h < 7)


def cell(r):
    return (round(r["lat"], 2), round(r["lon"], 2))  # ~1 km


def city_of(rs):
    c = collections.Counter((r["place"] or {}).get("city") for r in rs if r["place"])
    c.pop(None, None)
    return c.most_common(1)[0][0] if c else "?"


def main():
    a = C.parser(__doc__).parse_args()
    P = C.Project(a.projekt)
    rows = [r for r in P.read("fotky.json") if evening(r)]
    by_year = collections.defaultdict(list)
    for r in rows:
        by_year[int(r["date"][:4])].append(r)

    # home per year = the cell with most evening photos, on many different days
    per_year = {}
    for y, rs in sorted(by_year.items()):
        cells = collections.defaultdict(list)
        for r in rs:
            cells[cell(r)].append(r)
        best = max(cells.values(), key=lambda v: len({r["date"][:10] for r in v}))
        days = len({r["date"][:10] for r in best})
        if days >= 8:
            per_year[y] = (city_of(best), C.median_pt([(r["lat"], r["lon"]) for r in best]), days)

    segments = []
    for y, (city, pt, days) in sorted(per_year.items()):
        s = segments[-1] if segments else None
        if s and s["nazev"] == city and C.km((s["lat"], s["lon"]), pt) < 5 and y - s["do"] <= 2:
            s["do"] = y
        else:
            segments.append({"nazev": city, "lat": round(pt[0], 3), "lon": round(pt[1], 3), "od": y, "do": y})

    # other recurring evening places (parents, partner's family, cottage…)
    home_pts = [(s["lat"], s["lon"]) for s in segments]
    cells = collections.defaultdict(list)
    for r in rows:
        cells[cell(r)].append(r)
    others = []
    for c, rs in cells.items():
        days = {r["date"][:10] for r in rs}
        pt = C.median_pt([(r["lat"], r["lon"]) for r in rs])
        if len(days) < 12 or any(C.km(pt, h) < 10 for h in home_pts):
            continue
        if any(C.km(pt, (o["lat"], o["lon"])) < 10 for o in others):
            continue
        years = sorted({r["date"][:4] for r in rs})
        others.append({"nazev": city_of(rs), "lat": round(pt[0], 3), "lon": round(pt[1], 3),
                       "_dni": len(days), "_roky": f"{years[0]}–{years[-1]}"})
    others.sort(key=lambda o: -o["_dni"])

    print("Domov po rocích (místo s nejvíc večerními fotkami):")
    for y, (city, pt, days) in sorted(per_year.items()):
        print(f"  {y}: {city} ({days} večerů)")
    print("\nNávrh do kniha.json (zkontroluj s uživatelem, názvy můžeš zkrátit):")
    print('"domovy": ' + json.dumps(segments, ensure_ascii=False, indent=1))
    print('"dalsi_mista": ' + json.dumps([{k: v for k, v in o.items() if not k.startswith("_")} for o in others[:8]],
                                        ensure_ascii=False, indent=1))
    print("\nDalší místa, kam často jezdíte na noc (zeptej se, kdo tam bydlí; nepočítají se jako výlety):")
    for o in others[:8]:
        print(f"  {o['nazev']}: {o['_dni']} večerů, {o['_roky']}")


main()
