"""Export full-resolution originals of the chosen photos into originaly/ (needed for print).

Uses osxphotos; photos stored only in iCloud are downloaded through the Photos app (can take ~10 s per photo).
Edited photos are exported in their edited form. Nothing in the Photos library changes.
Run:  python3 SKILL_DIR/tools/originaly.py --projekt DIR
"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402


def wanted(P, cfg):
    uuids = [p["uuid"] for p in P.read("vyber.json")]
    return list(dict.fromkeys(uuids))


def missing(dest, uuids):
    have = {f.name for f in dest.rglob("*.jp*g")} if dest.exists() else set()
    return [u for u in uuids if not any(u in n for n in have)]


def main():
    a = C.parser(__doc__).parse_args()
    P = C.Project(a.projekt)
    cfg = P.cfg()
    C.need("uv")
    dest = P.dir / "originaly"
    uuids = wanted(P, cfg)
    todo = missing(dest, uuids)
    if not todo:
        print(f"Všech {len(uuids)} originálů už je v {dest}.")
        return
    lst = P.data / "originaly_uuid.txt"
    lst.write_text("\n".join(todo) + "\n")
    print(f"Exportuji {len(todo)} z {len(uuids)} originálů do {dest} (fotky z iCloudu se stahují, chvíli to trvá)…", flush=True)
    cmd = ["uv", "tool", "run", "--python", "3.12", "--from", "osxphotos", "osxphotos", "export", str(dest),
           "--uuid-from-file", str(lst), "--download-missing", "--skip-live", "--skip-original-if-edited",
           "--convert-to-jpeg", "--directory", "{created.year}", "--filename", "{created.strftime,%Y-%m-%d_%H%M}_{uuid}",
           "--retry", "2"]
    if (dest / ".osxphotos_export.db").exists():
        cmd.append("--update")
    dest.mkdir(exist_ok=True)
    subprocess.run(cmd, input="y\n", text=True)
    left = missing(dest, uuids)
    if left:
        print(f"Chybí ještě {len(left)} originálů – spusť skript znovu (iCloud někdy napoprvé nestáhne vše):")
        for u in left[:20]:
            print("  ", u)
        sys.exit(1)
    print(f"Hotovo: {len(uuids)} originálů v {dest}")


main()
