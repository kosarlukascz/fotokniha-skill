"""Turn vyber.txt (chosen numbers from the contact sheets) into data/vyber.json for the book.

vyber.txt, one line per chapter, numbers in order of preference, '#' starts a comment:
    2019-07-12: 08 03 11 01 | Chorvatsko – Makarska, Biokovo
Run:  python3 SKILL_DIR/tools/vyber.py --projekt DIR            (compile + summary per year)
      python3 SKILL_DIR/tools/vyber.py --projekt DIR --mista    (place names in the picks, for kniha.json → nazvy_mist)
"""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402


def compile_picks(P):
    rows = {r["uuid"]: r for r in P.read("fotky.json")}
    chapters = {c["id"]: c for c in P.read("kapitoly.json")}
    f = P.dir / "vyber.txt"
    if not f.exists():
        sys.exit(f"Chybí {f}.")
    out, errors = [], []
    for ln, line in enumerate(f.read_text().splitlines(), 1):
        if line.lstrip().startswith("#") or ":" not in line:
            continue
        cid, rest = line.split(":", 1)
        cid = cid.strip()
        nums, _, note = rest.partition("|")
        c = chapters.get(cid)
        if not c:
            errors.append(f"řádek {ln}: neznámá kapitola {cid}")
            continue
        for n in nums.split():
            if not n.isdigit() or not 1 <= int(n) <= len(c["cands"]):
                errors.append(f"řádek {ln}: {cid} nemá fotku číslo {n}")
                continue
            r = rows[c["cands"][int(n) - 1]]
            p = r["place"] or {}
            out.append({"chapter": cid, "kind": c["kind"], "tile": n.zfill(2), "uuid": r["uuid"],
                        "date": r["date"][:16], "lat": r["lat"], "lon": r["lon"],
                        "city": p.get("city"), "country": p.get("country_name"), "cc": p.get("country"),
                        "aoi": (p.get("aoi") or [])[:2], "persons": r["persons"], "fav": r["fav"],
                        "w": r["w"], "h": r["h"], "deriv": r["deriv"], "note": note.strip()})
    if errors:
        sys.exit("Chyby ve vyber.txt:\n  " + "\n  ".join(errors))
    seen = set()
    dup = [p["uuid"] for p in out if p["uuid"] in seen or seen.add(p["uuid"])]
    if dup:
        print(f"Pozor: {len(dup)} fotek je vybraných dvakrát.")
    out.sort(key=lambda p: p["date"])
    P.write("vyber.json", out, indent=1)
    return out


def main():
    ap = C.parser(__doc__)
    ap.add_argument("--mista", action="store_true", help="vypsat názvy míst u vybraných fotek")
    a = ap.parse_args()
    P = C.Project(a.projekt)
    cfg = P.cfg()
    picks = compile_picks(P)

    if a.mista:
        names = cfg.get("nazvy_mist") or {}
        c = collections.Counter()
        for p in picks:
            raw = p["aoi"][0] if p["aoi"] else (p["city"] or "")
            c[raw] += 1
        print("Místo z Fotek → jak se ukáže v popisku (uprav v kniha.json → nazvy_mist; \"\" = jen datum):")
        for raw, n in sorted(c.items(), key=lambda x: -x[1]):
            print(f"  {n:3}× {raw!r}" + (f" → {names[raw]!r}" if raw in names else ""))
        return

    by_year = collections.defaultdict(list)
    for p in picks:
        by_year[p["date"][:4]].append(p)
    print(f"{C.fotek(len(picks))} ve výběru → {P.data / 'vyber.json'}")
    for y, ps in sorted(by_year.items()):
        kinds = collections.Counter(p["kind"] for p in ps)
        print(f"  {y}: {C.fotek(len(ps)):>10} ({', '.join(f'{k} {n}' for k, n in kinds.items())})")
    print(f"Odhad: zhruba {round(len(picks) / 5) + 6} stran (přesně to ukáže kniha.py).")


if __name__ == "__main__":
    main()
