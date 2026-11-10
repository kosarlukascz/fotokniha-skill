"""Build chapters (trips, big events, everyday moments per year) and numbered contact sheets of the best candidates.

Writes data/kapitoly.json and nahledy/<chapter>.jpg. Look at every sheet and write the chosen numbers into vyber.txt.
Run:  python3 SKILL_DIR/tools/kandidati.py --projekt DIR
      python3 SKILL_DIR/tools/kandidati.py --projekt DIR --jen 2019-07-12 --pocet 24   (more candidates for one chapter;
      existing numbers stay, new photos are appended)
"""
import collections
import datetime as dt
import math
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402


def pick(pool, k, ps, need_main=0.4, gap_s=240):
    """Best k photos: Apple's scores, a share with the main person, max a few per day, no near-duplicates."""
    pool = sorted(pool, key=lambda r: C.rank(r, ps), reverse=True)
    days = {r["date"][:10] for r in pool} or {"x"}
    per_day = max(2, math.ceil(k / len(days)) + 1)
    chosen, day_n = [], collections.Counter()

    def ok(r):
        if day_n[r["date"][:10]] >= per_day:
            return False
        t = dt.datetime.fromisoformat(r["date"])
        return all(abs((t - dt.datetime.fromisoformat(c["date"])).total_seconds()) > gap_s for c in chosen)

    with_main = [r for r in pool if ps[0] in r["persons"]]
    for src, cap in ((with_main, round(k * need_main)), (pool, k)):
        for r in src:
            if len(chosen) >= cap:
                break
            if r not in chosen and ok(r):
                chosen.append(r)
                day_n[r["date"][:10]] += 1
    return sorted(chosen, key=lambda r: r["date"])


def sheet(P, cid, title, items):
    out = P.dir / "nahledy" / f"{cid}.jpg"
    out.parent.mkdir(exist_ok=True)
    args = ["magick", "montage"]
    for i, r in enumerate(items, 1):
        args += ["-label", f"{i:02d}", r["deriv"]]
    args += ["-tile", "6x", "-geometry", "300x300+6+6", "-font", C.LABEL_FONT, "-pointsize", "22",
             "-background", "white", "-title", title, str(out)]
    subprocess.run(args, check=True, capture_output=True)
    return out


def size_for(kind, n):
    if kind == "doma":
        return 12
    hi = 24 if kind == "cesta" else 12
    return max(6, min(hi, math.ceil(n / 12 / 3) * 3))


def main():
    ap = C.parser(__doc__)
    ap.add_argument("--jen", help="přegenerovat jen tuto kapitolu")
    ap.add_argument("--pocet", type=int, help="počet kandidátů (s --jen)")
    ap.add_argument("--prepsat", action="store_true", help="přegenerovat vše, i když už existuje vyber.txt")
    a = ap.parse_args()
    P = C.Project(a.projekt)
    cfg = P.cfg()
    ps = C.people(cfg)
    C.need("magick")
    rows = P.read("fotky.json")
    by_uuid = {r["uuid"]: r for r in rows}
    usable = lambda r: bool(r["deriv"]) and pathlib.Path(r["deriv"]).exists()

    if a.jen:
        chapters = P.read("kapitoly.json")
        ch = next((c for c in chapters if c["id"] == a.jen), None)
        if not ch:
            sys.exit(f"Kapitola {a.jen} neexistuje.")
        pool = [by_uuid[u] for u in ch["pool"] if usable(by_uuid[u])]
        k = a.pocet or len(ch["cands"]) + 6
        new = [r["uuid"] for r in pick(pool, k, ps, need_main=1.0 if ch["kind"] == "doma" else 0.4)
               if r["uuid"] not in ch["cands"]]
        ch["cands"] += new[:max(0, k - len(ch["cands"]))]
        P.write("kapitoly.json", chapters, indent=1)
        print(sheet(P, ch["id"], ch["title"], [by_uuid[u] for u in ch["cands"]]), f"({len(ch['cands'])} fotek)")
        return

    if (P.dir / "vyber.txt").exists() and not a.prepsat:
        sys.exit("vyber.txt už existuje a nové kandidáty by změnily čísla fotek. Pro jednu kapitolu použij --jen, "
                 "jinak --prepsat.")

    min_n = cfg.get("min_fotek", 40)
    per_year = cfg.get("udalosti_na_rok", 4)
    trips = P.read("cesty.json")
    events = P.read("udalosti.json")
    chapters, taken = [], set()

    for t in trips:
        if t["main"] < 2:
            continue
        kind = "cesta" if t["nights"] >= 1 else "vylet"
        if kind == "vylet" and t["n"] < min_n:
            continue
        country = t["countries"][0][1] if t["countries"] else ""
        nights = {0: "bez přespání", 1: "1 noc"}.get(t["nights"], f"{t['nights']} noci" if t["nights"] < 5 else f"{t['nights']} nocí")
        title = f"{t['start']} {', '.join(t['places'][:3])} ({country}, {nights}, {t['n']} fotek)"
        chapters.append({"id": t["id"], "kind": kind, "title": title, "start": t["start"], "end": t["end"],
                         "nights": t["nights"], "n": t["n"], "places": t["places"], "aois": t["aois"],
                         "countries": t["countries"], "pool": t["uuids"]})
        taken.update(t["uuids"])

    by_year = collections.defaultdict(list)
    for e in events:
        if not e["trip"] and e["n"] >= min_n and e["main"] >= 3:
            by_year[e["start"][:4]].append(e)
    ids = {c["id"] for c in chapters}
    for y, evs in by_year.items():
        for e in sorted(evs, key=lambda e: -(e["n"] + 3 * e["main"]))[:per_year]:
            cid = e["id"] if e["id"] not in ids else e["id"] + "-b"
            ids.add(cid)
            title = f"{e['start']} {', '.join(e['places'][:3])} ({e['n']} fotek; {', '.join(e['hints'][:3])})"
            chapters.append({"id": cid, "kind": "udalost", "title": title, "start": e["start"], "end": e["end"],
                             "nights": 0, "n": e["n"], "places": e["places"], "aois": [],
                             "countries": [[e["country"], "", e["n"]]], "pool": e["uuids"]})
            taken.update(e["uuids"])

    years = sorted({r["date"][:4] for r in rows})
    for y in years:
        pool = [r["uuid"] for r in rows if r["date"][:4] == y and r["uuid"] not in taken
                and ps[0] in r["persons"] and not r["shared"]]
        if pool:
            chapters.append({"id": f"{y}-doma", "kind": "doma", "title": f"{y} – běžné chvíle ({len(pool)} fotek)",
                             "start": f"{y}-01-01", "end": f"{y}-12-31", "nights": 0, "n": len(pool),
                             "places": [], "aois": [], "countries": [], "pool": pool})

    chapters.sort(key=lambda c: (c["start"], c["kind"] == "doma"))
    for c in chapters:
        pool = [by_uuid[u] for u in c["pool"] if usable(by_uuid[u])]
        items = pick(pool, size_for(c["kind"], c["n"]), ps, need_main=1.0 if c["kind"] == "doma" else 0.4)
        c["cands"] = [r["uuid"] for r in items]
        if items:
            sheet(P, c["id"], c["title"], items)
        print(f"  {c['id']:14} {c['kind']:8} {len(items):2} kandidátů | {c['title'].removeprefix(c['start'] + ' ')}", flush=True)
    chapters = [c for c in chapters if c["cands"]]
    P.write("kapitoly.json", chapters, indent=1)
    kinds = collections.Counter(c["kind"] for c in chapters)
    print(f"\n{len(chapters)} kapitol ({', '.join(f'{k}: {n}' for k, n in kinds.items())}), "
          f"{sum(len(c['cands']) for c in chapters)} kandidátů → {P.dir / 'nahledy'}")


main()
