"""Find trips: days with photos far from every home place, merged into trips. Writes data/cesty.json.

Run:  python3 SKILL_DIR/tools/cesty.py --projekt DIR
Needs kniha.json → osoby, domovy (+ optional dalsi_mista, daleko_km).
"""
import collections
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402


def main():
    a = C.parser(__doc__).parse_args()
    P = C.Project(a.projekt)
    cfg = P.cfg()
    ps = C.people(cfg)
    main_person = ps[0]
    anchors = [(h["lat"], h["lon"]) for h in C.homes(cfg) + (cfg.get("dalsi_mista") or [])]
    away_km = cfg.get("daleko_km", 35)
    rows = P.read("fotky.json")

    def away(r):
        return r["lat"] is not None and min(C.km((r["lat"], r["lon"]), x) for x in anchors) > away_km

    days = C.by_day(rows)
    away_days = []
    for d in sorted(days):
        geo = [r for r in days[d] if r["lat"] is not None]
        if geo and sum(away(r) for r in geo) >= max(3, 0.4 * len(geo)):
            away_days.append(d)

    trips = []  # merge consecutive away days, one day without photos may be in between
    for d in away_days:
        dd = dt.date.fromisoformat(d)
        if trips and (dd - trips[-1]["end"]).days <= 2:
            trips[-1]["end"] = dd
            trips[-1]["days"].append(d)
        else:
            trips.append({"start": dd, "end": dd, "days": [d]})

    out = []
    for t in trips:
        ph = [r for d in t["days"] for r in days[d] if r["lat"] is None or away(r)]
        places, countries, aois = collections.Counter(), collections.Counter(), collections.Counter()
        for r in ph:
            p = r["place"]
            if not p:
                continue
            places[p.get("city") or p.get("sub_admin") or p.get("state") or "?"] += 1
            countries[(p.get("country"), p.get("country_name"))] += 1
            for x in p.get("aoi") or []:
                aois[x] += 1
        out.append({
            "id": str(t["start"]), "start": str(t["start"]), "end": str(t["end"]),
            "nights": (t["end"] - t["start"]).days, "n": len(ph),
            "main": sum(main_person in r["persons"] for r in ph),
            "both": sum(main_person in r["persons"] and any(x in r["persons"] for x in ps[1:]) for r in ph),
            "countries": [[cc, name, k] for (cc, name), k in countries.most_common(4)],
            "places": [k for k, _ in places.most_common(8)],
            "aois": [k for k, _ in aois.most_common(8)],
            "people": collections.Counter(x for r in ph for x in r["persons"]).most_common(6),
            "uuids": [r["uuid"] for r in ph],
        })
    P.write("cesty.json", out, indent=1)

    shown = [t for t in out if t["main"] >= 2]
    print(f"{len(out)} cest, z toho {len(shown)} s osobou {main_person} "
          f"({sum(t['nights'] >= 1 for t in shown)} s přespáním) → {P.data / 'cesty.json'}")
    for t in shown:
        span = t["start"] + (f"..{t['end'][5:]}" if t["end"] != t["start"] else "")
        print(f"  {span:17} {t['nights']:2}n  fotek {t['n']:4}  s hl. postavou {t['main']:3} | "
              f"{', '.join(str(c[1]) for c in t['countries'][:2])} | {', '.join(t['places'][:4])}")
    hidden = len(out) - len(shown)
    if hidden:
        print(f"  (+{hidden} cest bez hlavní postavy, např. pracovní nebo s kamarády – do knihy nejdou)")


main()
