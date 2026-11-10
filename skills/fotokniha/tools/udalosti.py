"""Find the big moments of every year: places and days with the most photos, home included.
A big moment is not only a trip abroad: graduations, weddings, Christmas, a new pet also produce many photos in one place.
Writes data/udalosti.json and prints the top events per year.

Run:  python3 SKILL_DIR/tools/udalosti.py --projekt DIR
"""
import collections
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402

GENERIC = {"Dokument", "Text", "Lidé", "Obloha", "Strom", "Rostlina", "Budova", "Stavba", "Mrak", "Tráva", "Dospělý",
           "Exteriér", "Interiér", "Člověk", "Dav", "Selfie", "Ulice", "Auto", "Vozidlo", "Jídlo", "Nábytek", "Okno",
           "Zeď", "Podlaha", "Strop", "Dveře", "Osvětlení", "Obličej", "Úsměv", "Oblečení", "Ruka",
           "People", "Sky", "Tree", "Plant", "Building", "Structure", "Cloud", "Grass", "Adult", "Outdoor", "Indoor",
           "Person", "Crowd", "Street", "Car", "Vehicle", "Food", "Furniture", "Window", "Wall", "Floor", "Face"}


def pname(r):
    p = r["place"] or {}
    return (p.get("aoi") or [None])[0] or p.get("city") or p.get("sub_admin") or "?"


def main():
    a = C.parser(__doc__).parse_args()
    P = C.Project(a.projekt)
    cfg = P.cfg()
    ps = C.people(cfg)
    rows = P.read("fotky.json")
    trips = P.read("cesty.json")
    trip_of = {u: t["id"] for t in trips for u in t["uuids"]}

    clusters = []  # per day: photos within 6 km of each other
    for d, rs in sorted(C.by_day(rows).items()):
        cl = []
        for r in (r for r in rs if r["lat"] is not None):
            for c in cl:
                if C.km(c["pt"], (r["lat"], r["lon"])) < 6:
                    c["rows"].append(r)
                    break
            else:
                cl.append({"pt": (r["lat"], r["lon"]), "rows": [r]})
        if cl:  # photos without location belong to the day's biggest cluster
            max(cl, key=lambda c: len(c["rows"]))["rows"] += [r for r in rs if r["lat"] is None]
        for c in cl:
            c["day"] = dt.date.fromisoformat(d)
            clusters.append(c)

    events = []  # the same place on consecutive days = one event
    for c in clusters:
        for e in events[-6:]:
            if (c["day"] - e["end"]).days <= 1 and C.km(e["pt"], c["pt"]) < 10:
                e["rows"] += c["rows"]
                e["end"] = c["day"]
                break
        else:
            events.append({"pt": c["pt"], "start": c["day"], "end": c["day"], "rows": list(c["rows"])})

    out = []
    for e in events:
        rs = e["rows"]
        n_main = sum(ps[0] in r["persons"] for r in rs)
        if n_main == 0:
            continue
        labels = collections.Counter(x for r in rs for x in r.get("labels") or [] if x not in GENERIC)
        acts = collections.Counter(x for r in rs for x in ((r.get("search") or {}).get("activities") or []))
        hol = collections.Counter(x for r in rs for x in ((r.get("search") or {}).get("holidays") or []))
        names = collections.Counter(pname(r) for r in rs if r["place"])
        in_trip = collections.Counter(trip_of.get(r["uuid"]) for r in rs)
        tid, k = in_trip.most_common(1)[0]
        out.append({
            "id": str(e["start"]), "start": str(e["start"]), "end": str(e["end"]), "n": len(rs), "main": n_main,
            "both": sum(ps[0] in r["persons"] and any(x in r["persons"] for x in ps[1:]) for r in rs),
            "pt": [round(e["pt"][0], 4), round(e["pt"][1], 4)],
            "places": [x for x, _ in names.most_common(4)],
            "country": next(((r["place"] or {}).get("country") for r in rs if r["place"]), None),
            "labels": [x for x, _ in labels.most_common(6)],
            "hints": [x for x, _ in (hol + acts).most_common(4)],
            "trip": tid if tid and k > len(rs) / 2 else None,
            "uuids": [r["uuid"] for r in rs],
        })
    P.write("udalosti.json", out)

    by_year = collections.defaultdict(list)
    for e in out:
        by_year[e["start"][:4]].append(e)
    print(f"{len(out)} událostí → {P.data / 'udalosti.json'}")
    print("Největší chvíle roku (fotek celkem / s hlavní postavou); [cesta] = součást cesty:")
    for y in sorted(by_year):
        print(f"== {y}")
        for e in sorted(by_year[y], key=lambda e: -(e["n"] + 3 * e["main"]))[:8]:
            span = e["start"][5:] + (".." + e["end"][5:] if e["end"] != e["start"] else "")
            print(f"  {span:12} {e['n']:4}/{e['main']:<3} {'[cesta] ' if e['trip'] else ''}"
                  f"{', '.join(e['places'][:3])} | {', '.join(e['hints'] + e['labels'][:3])}")


main()
