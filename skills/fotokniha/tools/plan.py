"""Write a readable plan of the book (what is in it, year by year) into PLAN.md.
Only the part between the markers is regenerated; your own notes above and below stay.

Run:  python3 SKILL_DIR/tools/plan.py --projekt DIR
"""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402
import kniha as K  # noqa: E402

START, END = "<!-- obsah:zacatek (generuje tools/plan.py) -->", "<!-- obsah:konec -->"
MONTHS = ["ledna", "února", "března", "dubna", "května", "června", "července", "srpna", "září", "října", "listopadu",
          "prosince"]


def d(s):
    return f"{int(s[8:10])}. {MONTHS[int(s[5:7]) - 1]}"


def main():
    a = C.parser(__doc__).parse_args()
    K.setup(a.projekt)
    by_year = collections.defaultdict(list)
    for p in K.picks:
        by_year[p["date"][:4]].append(p)
    lines = [START, ""]
    for y in sorted(by_year):
        ps = sorted(by_year[y], key=lambda p: p["date"])
        sub = (K.CFG.get("roky") or {}).get(y, "")
        lines += [f"## {y}" + (f": {sub}" if sub else ""), f"*{C.fotek(len(ps))}*", ""]
        groups = collections.OrderedDict()
        for p in ps:
            groups.setdefault(p["chapter"] if K.is_trip(p["chapter"]) else (p["date"][:10], K.caption(p).rsplit(",", 1)[0]),
                              []).append(p)
        for k, g in groups.items():
            if isinstance(k, str):
                ch = K.chapters[k]
                places = list(dict.fromkeys(n for n in (K.nice_place(q) for q in g) if n))
                span = d(ch["start"]) + (f" – {d(ch['end'])}" if ch["end"] != ch["start"] else "")
                lines.append(f"- **{span}: {K.trip_name(k)}** ({C.fotek(len(g))}): {', '.join(places)}")
            else:
                label = k[1] if not k[1][:1].isdigit() else "doma"
                lines.append(f"- {d(k[0])}: {label}" + (f" ({C.fotek(len(g))})" if len(g) > 1 else ""))
        lines.append("")
    lines.append(END)
    f = K.P.dir / "PLAN.md"
    text = f.read_text() if f.exists() else f"# {K.CFG.get('titul', 'Fotokniha')}\n\n{START}\n{END}\n"
    if START not in text:
        text += f"\n{START}\n{END}\n"
    head, rest = text.split(START, 1)
    tail = rest.split(END, 1)[1] if END in rest else ""
    f.write_text(head + "\n".join(lines) + tail)
    print(f"{len(K.picks)} fotek v {len(by_year)} letech → {f}")


main()
