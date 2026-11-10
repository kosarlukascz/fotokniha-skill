"""Count outings together: days out (nature, mountains, castles, cities) away from home, merged into trips.
Shopping centres, airports, hospitals and schools do not count. Writes data/vylety.json; the number goes to the book's stats.

Run:  python3 SKILL_DIR/tools/vylety.py --projekt DIR
"""
import collections
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

NOT_OUTING = ("Centrum", "Forum", "Galerie", "OC ", "IKEA", "Lidl", "Kaufland", "Mall", "Palladium", "Letiště",
              "Nemocnice", "univerzit", "Univerzit", "Škola", "škola", "Albert", "Tesco", "Penny", "Globus",
              "Obchodní", "Nákupní", "Airport", "Hospital", "University", "School", "Shopping", "Center", "Centre")
OUTDOOR = {"Turistika", "Aktivita", "Zimní sport", "Pláž", "Hiking", "Activity", "Winter Sport", "Beach"}


def main():
    a = C.parser(__doc__).parse_args()
    P = C.Project(a.projekt)
    cfg = P.cfg()
    main_person = C.people(cfg)[0]
    rows = P.read("fotky.json")

    # exact home spots: the most frequent ~100 m evening cells within each home period + configured places
    spots = [(h["lat"], h["lon"]) for h in C.homes(cfg) + (cfg.get("dalsi_mista") or [])]
    for h in C.homes(cfg):
        c = collections.Counter()
        for r in rows:
            y = int(r["date"][:4])
            if r["lat"] is not None and h.get("od", 0) <= y <= h.get("do", 9999) and int(r["date"][11:13]) >= 18:
                c[(round(r["lat"], 3), round(r["lon"], 3))] += 1
        spots += [k for k, _ in c.most_common(4)]

    outing_days = {}
    for d, rs in C.by_day(rows).items():
        if not any(main_person in r["persons"] for r in rs):
            continue
        good = []
        for r in rs:
            if r["lat"] is None:
                continue
            dist = min(C.km((r["lat"], r["lon"]), h) for h in spots)
            if dist < 8:
                continue
            aoi = ((r["place"] or {}).get("aoi") or [""])[0]
            if any(b in aoi for b in NOT_OUTING):
                continue
            acts = set((r.get("search") or {}).get("activities") or [])
            if dist > 35 or aoi or acts & OUTDOOR:
                good.append(r)
        if len(good) >= 3:
            outing_days[d] = good

    trips = []
    for d in sorted(outing_days):
        dd = dt.date.fromisoformat(d)
        if trips and (dd - trips[-1]["end"]).days <= 1:
            trips[-1]["end"] = dd
            trips[-1]["days"].append(d)
        else:
            trips.append({"start": dd, "end": dd, "days": [d]})

    def place(t):
        c = collections.Counter(((r["place"] or {}).get("aoi") or [(r["place"] or {}).get("city")])[0]
                                for d in t["days"] for r in outing_days[d])
        return c.most_common(1)[0][0]

    def where(t):
        rs = [r for d in t["days"] for r in outing_days[d]]
        lat, lon = C.median_pt([(r["lat"], r["lon"]) for r in rs])
        cc = collections.Counter((r["place"] or {}).get("country") for r in rs).most_common(1)[0][0]
        return {"lat": round(lat, 4), "lon": round(lon, 4), "cc": cc}

    out = [{"start": str(t["start"]), "end": str(t["end"]), "place": place(t), **where(t)} for t in trips]
    P.write("vylety.json", out, indent=1)
    per_year = collections.Counter(t["start"][:4] for t in out)
    print(f"{len(outing_days)} dní venku → {len(out)} výletů → {P.data / 'vylety.json'}")
    print("po rocích:", ", ".join(f"{y}: {n}" for y, n in sorted(per_year.items())))


main()
