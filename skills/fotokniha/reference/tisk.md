# Tisk a objednávka

## Doporučení
Výchozí volba je **Saal Digital, Fotokniha Professional Line 30 × 30 cm**. Je to layflat (dvoustrany leží rovně
a fotka přes dvoustranu nemá zlom), má matný nebo lesklý fotopapír a dá se objednat z hotového PDF. V listopadu 2026
stála od 2 565 Kč za 26 stran a každá další strana něco přidá; přesnou cenu ukáže konfigurátor. Na obálku
se hodí akryl s fotkou. Saal často mívá slevové akce, kód vyhledej těsně před objednávkou.

## Saal Digital 30 × 30 Professional Line (profil `saal-30x30-professional`)
Ověřeno 9. 11. 2026 podle saal-digital.cz/fotokniha/profesionalni-zona/ (tabulky rozměrů se načítají
až JavaScriptem, takže je čti v prohlížeči):
- **Vnitřek**: jedna stránka PDF = jedna dvoustrana, 7016 × 3543 px při 300 dpi včetně spadávky 35 px
  (3 mm) na vnějších okrajích. Ve hřbetu u layflat spadávka není. 26–130 stran, sRGB, bez ořezových značek.
- **První strana první dvoustrany je vnitřek předních desek**, poslední strana poslední dvoustrany je vnitřek
  zadních desek. `tisk.py` proto dá na začátek stranu papíru se srdíčkem a titulní strana knihy vyjde vpravo.
- **Obálka** (přední deska): 4583 × 4819 px při 400 dpi včetně spadávky 47 px.
- Vnitřek a obálka se nahrávají jako dvě samostatná PDF.

Postup objednávky:
1. Na saal-digital.cz zvol Fotokniha → Professional Line → 30 × 30, typ obálky a papír.
2. Vyber „Nahrávání PDF“ a nahraj `kniha/pdf/vnitrek.pdf` a `kniha/pdf/obalka.pdf`.
3. Náhled ukáže obálku a všechny dvoustrany. Počet obrázků = 1 obálka + počet dvoustran. Prázdná polovina
   první dvoustrany je vnitřek desek, to je správně.
4. Zkontroluj, že počet stran v konfigurátoru odpovídá PDF (`tisk.py` ho vypíše), zadej slevový kód a objednej.

## Jiná tiskárna
Rozvržení je čtvercové, takže funguje jen se čtvercovou knihou. Na webu tiskárny najdi specifikaci pro nahrání
PDF a zapiš ji do `kniha.json` jako vlastní profil:
```json
"tisk": {"profil": "vlastni", "strana_px": 2504, "spadavka_px": 35, "dpi": 300,
         "dvoustrany": false, "vnitrni_desky": false, "stran_min": 24, "stran_max": 100}
```
- `strana_px`: jedna strana **včetně** spadávky v pixelech (cm ÷ 2,54 × dpi).
- `dvoustrany`: `true`, když tiskárna chce jednu stránku PDF na dvoustranu (layflat), jinak `false` (PDF po stranách).
- `vnitrni_desky`: `true`, když se první a poslední strana lepí na vnitřek desek.
- `obalka`: jen když tiskárna bere obálku jako samostatné PDF ve známém rozměru (`w`, `h`, `spadavka`, `dpi`).
  Obálky přes hřbet (záda + hřbet + přední deska) nástroj neumí. Takovou obálku udělej v editoru tiskárny.
Hodnoty nikdy neodhaduj. Když specifikaci nenajdeš, zeptej se uživatele nebo podpory tiskárny.
Ověřený profil můžeš doplnit do `PROFILES` v `tools/common.py`, ať ho mají i ostatní.

## Kontrola před nahráním
- `tisk.py` vypíše rozměry v px a mm. Musí přesně odpovídat specifikaci.
- Prohlédni si pár dvoustran z `kniha/pdf/vnitrek.pdf` (ve Finderu mezerníkem). Zkontroluj, že nic důležitého
  není do 5 mm od okraje a že titulní strana je vpravo.
- Fotky přes celou stranu mají mít aspoň ~250 dpi, tedy u 30 cm aspoň 3000 px na kratší straně.
