"""Print package from kniha/tisk/ (made by kniha.py --tisk): PDFs exactly as the print profile wants them.

Run:  uv run --python 3.12 --with img2pdf python3 SKILL_DIR/tools/tisk.py --projekt DIR
Output: kniha/pdf/vnitrek.pdf (+ obalka.pdf when the profile has a cover). Prints sizes for a final check.
"""
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common as C  # noqa: E402
import kniha as K  # noqa: E402

try:
    import img2pdf
except ImportError:
    sys.exit("Spusť přes: uv run --python 3.12 --with img2pdf python3 …/tisk.py")

SRGB = "/System/Library/ColorSync/Profiles/sRGB Profile.icc"


def sh(*args):
    subprocess.run([str(a) for a in args], check=True, capture_output=True)


def size(f):
    w, h = subprocess.run(["magick", "identify", "-format", "%w %h", str(f)], capture_output=True, text=True).stdout.split()
    return int(w), int(h)


def render_svg(svg, dst, px):
    sv = K.P.dir / "kniha" / "svg" / (dst.stem + ".svg")
    sv.parent.mkdir(parents=True, exist_ok=True)
    sv.write_text(svg)
    png = dst.with_suffix(".png")
    sh(C.chrome(), "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--hide-scrollbars",
       f"--window-size={K.S},{K.S}", f"--force-device-scale-factor={px / K.S}", "--virtual-time-budget=3000",
       f"--screenshot={png}", sv.as_uri())
    sh("magick", png, "-quality", "95", dst)
    png.unlink()


def pages(prof, work):
    src = sorted((K.P.dir / "kniha" / "tisk").glob("str-*.jpg"))
    if not src:
        sys.exit("Chybí kniha/tisk/. Spusť nejdřív kniha.py --tisk.")
    px = prof["strana_px"]
    for f in src[:1]:
        if size(f) != (px, px):
            sys.exit(f"{f.name} má {size(f)} px, profil chce {px} × {px}. Vygeneruj znovu kniha.py --tisk.")
    seq = [("file", f) for f in src]
    if prof.get("vnitrni_desky"):
        seq = [("heart", None)] + seq  # glued to the inside of the front cover, so the title lands on the right
    if len(seq) % 2:
        seq.append(("blank", None))
    lo, hi = prof.get("stran_min", 0), prof.get("stran_max", 10 ** 6)
    if len(seq) < lo:
        print(f"Pozor: kniha má {len(seq)} stran, minimum je {lo}. Doplňuji prázdné strany na konec – lepší je přidat fotky.")
        while len(seq) < lo:
            seq.insert(len(seq) - 1, ("blank", None))
    if len(seq) > hi:
        sys.exit(f"Kniha má {len(seq)} stran, maximum profilu je {hi}.")
    out = []
    for i, (kind, f) in enumerate(seq, 1):
        dst = work / f"strana-{i:03d}.jpg"
        if kind == "file":
            shutil.copy(f, dst)
        elif kind == "heart":
            render_svg(K.doc(K.paper() + K.heart(600, 640, 26, K.ACCENTS[0])), dst, px)
        else:
            render_svg(K.doc(K.paper()), dst, px)
        out.append(dst)
    return out


def spreads(prof, files, work):
    bleed = prof["spadavka_px"]
    out = []
    for k in range(0, len(files), 2):
        dst = work / f"dvoustrana-{k // 2 + 1:02d}.jpg"
        # left page keeps its outer (left) bleed, right page its outer (right) bleed; no bleed at the layflat fold
        sh("magick", "(", files[k], "-gravity", "East", "-chop", f"{bleed}x0", ")",
           "(", files[k + 1], "-gravity", "West", "-chop", f"{bleed}x0", ")",
           "+append", "+repage", "-profile", SRGB, "-quality", "95", "-density", prof["dpi"], "-units", "PixelsPerInch", dst)
        out.append(dst)
    want = (2 * prof["strana_px"] - 2 * bleed, prof["strana_px"])
    assert size(out[0]) == want, (size(out[0]), want)
    return out


def singles(prof, files):
    for f in files:
        sh("magick", f, "-profile", SRGB, "-density", prof["dpi"], "-units", "PixelsPerInch", f)
    return files


def cover(prof, work):
    cv = prof["obalka"]
    W, H, b, dpi = cv["w"], cv["h"], cv["spadavka"], cv["dpi"]
    t = K.CFG.get("tisk") or {}
    ref = t.get("obalka_foto") or K.CFG.get("titulni_foto")
    if not ref:
        sys.exit('Chybí fotka na obálku: kniha.json → tisk.obalka_foto (např. "2025-08-02/05").')
    p = K.find(C.ref(ref), "obalka_foto")
    orig = next((K.P.dir / "originaly").rglob(f"*{p['uuid']}*.jp*g"), None)
    if orig is None:
        sys.exit(f"Chybí originál fotky na obálku ({ref}). Spusť originaly.py.")
    photo = work / "obalka_foto.jpg"
    sh("magick", orig, "-auto-orient", "-colorspace", "sRGB", "-resize", f"{W}x{H}^", "-gravity", "center",
       "-extent", f"{W}x{H}", "-quality", "95", photo)
    o = t.get("obalka_text") or {}
    x, y = W * o.get("x", .5), b + H * o.get("y", .16)
    ink, fs = o.get("barva", K.INK), o.get("velikost", 400)
    a, z = K.years_span()
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W / 4}" height="{H / 4}" viewBox="0 0 {W} {H}">
<defs><style>@font-face{{font-family:Caveat;src:url("{C.FONT.as_uri()}")}}</style>
<filter id="s"><feDropShadow dx="0" dy="0" stdDeviation="18" flood-color="#fff6e6" flood-opacity=".9"/></filter></defs>
<image href="{photo.as_uri()}" width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice"/>
<text x="{x}" y="{y}" font-family="Caveat" font-weight="700" font-size="{fs}" fill="{ink}" text-anchor="middle"
 filter="url(#s)">{K.esc(K.CFG.get("titul", ""))}</text>
<text x="{x}" y="{y + fs * .6}" font-family="Caveat" font-size="{fs * .45}" fill="{ink}" text-anchor="middle"
 filter="url(#s)">{K.esc(K.CFG.get("podtitul", f"{a} – {z}"))}</text>
</svg>"""
    sv = work / "obalka.svg"
    sv.write_text(svg)
    png = work / "obalka.png"
    sh(C.chrome(), "--headless=new", "--disable-gpu", "--allow-file-access-from-files", "--hide-scrollbars",
       f"--window-size={-(-W // 4)},{-(-H // 4)}", "--force-device-scale-factor=4", "--virtual-time-budget=4000",
       f"--screenshot={png}", sv.as_uri())
    jpg = work / "obalka.jpg"
    sh("magick", png, "-crop", f"{W}x{H}+0+0", "+repage", "-profile", SRGB, "-quality", "95",
       "-density", dpi, "-units", "PixelsPerInch", jpg)
    png.unlink()
    assert size(jpg) == (W, H), size(jpg)
    return jpg


def mm(px, dpi):
    return round(px / dpi * 25.4, 1)


def main():
    ap = C.parser(__doc__)
    a = ap.parse_args()
    K.setup(a.projekt, final=True)
    C.need("magick")
    prof = K.PROF
    out = K.P.dir / "kniha" / "pdf"
    work = K.P.dir / "kniha" / "pdf_prace"
    for d in (out, work):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    files = pages(prof, work)
    parts = spreads(prof, files, work) if prof.get("dvoustrany") else singles(prof, files)
    (out / "vnitrek.pdf").write_bytes(img2pdf.convert([str(f) for f in parts]))
    w, h = size(parts[0])
    print(f"vnitrek.pdf: {len(files)} stran = {len(parts)} stránek PDF po {mm(w, prof['dpi'])} × {mm(h, prof['dpi'])} mm "
          f"({w} × {h} px, {prof['dpi']} dpi)")
    if prof.get("obalka"):
        cj = cover(prof, work)
        (out / "obalka.pdf").write_bytes(img2pdf.convert([str(cj)]))
        cv = prof["obalka"]
        print(f"obalka.pdf: {mm(cv['w'], cv['dpi'])} × {mm(cv['h'], cv['dpi'])} mm ({cv['w']} × {cv['h']} px, {cv['dpi']} dpi)")
    shutil.rmtree(work)
    print(f"Profil: {prof.get('popis', prof['nazev'])} → {out}")


main()
