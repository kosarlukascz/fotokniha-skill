---
name: fotokniha
description: >-
  Fotokniha z Apple Fotek na Macu. Projde celou knihovnu fotek (lidi, místa, Applem hodnocená kvalita), najde dovolené,
  výlety a velké chvíle každého roku, pomůže vybrat nejlepší fotky a vysází hravou knihu (polaroidy, washi pásky,
  ručně psané popisky, mapky cest, cestovní razítka) včetně tiskových PDF pro Saal Digital.
  Použij, když chce uživatel udělat fotoknihu, album nebo dárek z fotek (k Vánocům, výročí, narozeninám, pro partnera,
  rodiče nebo dítě), vybrat nejlepší fotky z dovolených či z celých let nebo připravit knihu k tisku, i když slovo
  „skill“ neřekne. Spouštěcí fráze: „fotokniha“, „kniha z našich fotek“, „dárek z fotek“, „vyber nejlepší fotky
  z dovolených“, „naše roky spolu v knize“.
---

# Fotokniha z Apple Fotek

Pomáháš udělat osobní fotoknihu z knihovny Apple Fotek: od tisíců fotek přes výběr až po PDF, které jde rovnou do tisku.
Technickou práci děláš ty (čtení knihovny, hledání cest a událostí, předvýběr, sazba, tisková data). Uživatel ví,
co se na fotkách děje, rozhoduje o výběru a schvaluje vzhled.

**Složka skillu** (dále `SKILL_DIR`) je ta, kterou ti systém ukázal při načtení („Base directory“). Je v ní
`tools/` (nástroje), `template/kniha.example.json` (šablona nastavení) a `reference/` (podrobnosti; čti je, až je potřebuješ).
Nástroje se spouští `python3 SKILL_DIR/tools/<nástroj>.py --projekt <složka projektu>`.

## Jak mluvit s uživatelem
- Česky, stručně, bez žargonu. Místo „JSON“ a „UUID“ říkej „nastavení“ a „fotka“.
- Ptej se jen na to, co víš jen on: komu je kniha, za jaké období, kdo je kdo, co se na které akci dělo, co vynechat.
  Technické volby (rozvržení, rozlišení, formát PDF) udělej sám.
- **Neodhaduj, co bylo na akci.** Když 14. 6. v Olomouci vznikne 120 fotek ve společenském, může to být promoce, svatba
  i ples. Zeptej se jednou větou. Špatný popisek se v tištěné knize opravit nedá.
- Výsledek ukazuj obrázkem (`kniha/nahled/prehled.jpg`, jednotlivé dvoustrany), ne dlouhým popisem.
- Na konci kroku řekni, co je hotové, co jsi zjistil a co navrhuješ dál.

## Soukromí a překvapení
Fotokniha bývá dárek a často překvapení.
- **Knihovnu Fotek jen čteš.** Ve Fotkách nic nevytvářej ani neměň (alba, klíčová slova, oblíbené, úpravy, jména lidí).
  Fotky se synchronizují přes iCloud na všechna zařízení a sdílenou knihovnu, takže by to obdarovaný mohl uvidět.
  Celý výběr žije jen ve složce projektu.
- Fotky, kontaktní tabule ani náhledy nikam nenahrávej. Ven jdou jen tisková PDF, a ta nahrává uživatel sám.
- Bez ptaní vynech intimní fotky a nahotu, detailní plavkové fotky, doklady, účtenky a snímky obrazovky.
  Vynech také cesty bez hlavní postavy knihy (pracovní cesty, pánské a dámské jízdy). Na další hranice se zeptej
  (bývalí partneři, smutné události, nemocnice).

## Co je potřeba
- Mac s aplikací Fotky. Nejlíp funguje, když jsou ve Fotkách pojmenovaní lidé (album Lidé a zvířata).
- Programy `uv`, ImageMagick (`magick`) a Google Chrome. Zkontroluj `which uv magick` a Chrome v `/Applications`.
  Co chybí, nainstaluj po souhlasu přes Homebrew: `brew install uv imagemagick`, `brew install --cask google-chrome`.
- Když čtení knihovny skončí chybou oprávnění, musí uživatel dát aplikaci, ve které běžíš (Terminál, iTerm, Claude),
  **Úplný přístup k disku** (Nastavení systému → Soukromí a zabezpečení).
- Místo na disku: asi 5 MB na každou vybranou fotku (originály) a 100–200 MB na tisková data.

## Složka projektu
Navrhni `~/Fotokniha-<jméno>` a zkopíruj do ní šablonu `SKILL_DIR/template/kniha.example.json` jako `kniha.json`.
```
kniha.json      nastavení knihy (popis všech polí: reference/konfigurace.md)
vyber.txt       vybrané fotky: čísla z kontaktních tabulí, po kapitolách
PLAN.md         čitelný plán knihy po rocích (tools/plan.py)
data/           metadata z Fotek a mezivýsledky (fotky, cesty, události, výlety, kapitoly, výběr)
nahledy/        kontaktní tabule s očíslovanými kandidáty
originaly/      originály vybraných fotek v plném rozlišení
kniha/nahled/   náhled stran, dvoustran a celé knihy (prehled.jpg)
kniha/tisk/     tiskové strany;  kniha/pdf/  PDF k objednávce
```

## Postup

### 1. Krátký rozhovor
Zjisti, pro koho kniha je a k jaké příležitosti, za jaké období (třeba „od seznámení po těhotenství“), do kdy musí
být doma (počítej s rezervou aspoň dva týdny na tisk a dopravu) a jestli jde o překvapení. Formát doporuč podle
rozpočtu; výchozí je Saal Digital Professional Line 30 × 30 cm (layflat, od 26 stran), viz `reference/tisk.md`.
Založ projekt a vyplň v `kniha.json` pole `titul`, `od` a `do`.

### 2. Načtení knihovny
```
uv run --python 3.12 --with osxphotos python3 SKILL_DIR/tools/nacti_fotky.py --projekt P
```
Nástroj vypíše pojmenované lidi a zvířata. Do `osoby` dej přesná jména, **první je hlavní postava knihy** (u dárku
pro partnera je to partner), další jsou lidé, se kterými jsou společné fotky nejcennější. Když lidé ve Fotkách
pojmenovaní nejsou, nejde poznat, kde kdo je. Pak se zeptej, jestli je může pojmenovat. Jde o změnu ve Fotkách,
takže u překvapení jen tehdy, když nemají sdílenou knihovnu.

### 3. Domov, cesty, velké chvíle a výlety
```
python3 SKILL_DIR/tools/domov.py --projekt P      # návrh, kde a kdy jste bydleli
python3 SKILL_DIR/tools/cesty.py --projekt P      # dovolené a výlety daleko od domova
python3 SKILL_DIR/tools/udalosti.py --projekt P   # největší chvíle každého roku, i doma
python3 SKILL_DIR/tools/vylety.py --projekt P     # kolikrát jste byli spolu venku (číslo do knihy)
```
- Návrh z `domov.py` ukaž uživateli a potvrď. Místa, kam se jezdí na noc k rodině, patří do `dalsi_mista`,
  aby se nepočítala jako výlety.
- Z výpisu `udalosti.py` sestav pro každý rok 3–5 největších chvil. **Velikost poznáš podle počtu fotek na jednom
  místě, ne podle exotiky.** Promoce, Vánoce nebo nové kotě doma s 150 fotkami jsou důležitější než zastávka
  v cizině s osmi fotkami. Co z výpisu nepoznáš (svatba čí? promoce čí?), zjisti od uživatele.

### 4. Kandidáti a výběr fotek
```
python3 SKILL_DIR/tools/kandidati.py --projekt P
```
Nástroj sestaví kapitoly a pro každou udělá kontaktní tabuli `nahledy/<kapitola>.jpg` s očíslovanými nejlepšími
kandidáty. Kapitoly jsou cesty s přespáním (`cesta`), jednodenní výlety (`vylet`), velké chvíle doma (`udalost`)
a běžné chvíle roku (`<rok>-doma`). **Každou tabuli si prohlédni** a do `vyber.txt` zapiš čísla podle pořadí,
v jakém je chceš:
```
2019-07-12: 08 03 11 01 05 | Chorvatsko – Makarska, Biokovo, západ slunce
2023-02-10: 04 02 | promoce v Olomouci
```
Pravidla výběru jsou v části „Jak vybírat“ níže. Když má kapitola málo dobrých kandidátů, přidej je:
`kandidati.py --jen <kapitola> --pocet 24`. Čísla, která už máš, zůstanou.
Tabulí bývá 50–100. Zapisuj výběr do `vyber.txt` průběžně, ať se při dlouhé práci nic neztratí. U velké knihovny
rozděl prohlížení po letech mezi pomocné agenty. Každý dostane cestu k tabulím, výpis kapitol a pravidla výběru
a vrátí hotové řádky do `vyber.txt`. Celek pak zkontroluješ v náhledu.

Potom:
```
python3 SKILL_DIR/tools/vyber.py --projekt P          # kontrola a počty po rocích
python3 SKILL_DIR/tools/vyber.py --projekt P --mista  # názvy míst pro popisky → kniha.json: nazvy_mist
```
Do `kniha.json` doplň `roky` (podtitul každého roku), `cesty` (název mapky, např. „Chorvatsko 2019“), `popisky`
(akce: „Promoce v Olomouci“, „Vánoce 2021“), `cela_strana`, `titulni_foto`, `zaver` a `tisk.obalka_foto`.
Formát polí je v `reference/konfigurace.md`.

### 5. Náhled a ladění
```
python3 SKILL_DIR/tools/kniha.py --projekt P   # → kniha/nahled/: strany, dvoustrany, prehled.jpg
python3 SKILL_DIR/tools/plan.py --projekt P    # → PLAN.md
```
Nejdřív si sám prohlédni `prehled.jpg` a každou dvoustranu. Zkontroluj, že titulní strana je vpravo, obě mapy
na úvodní dvoustraně jsou proti sobě a závěrečná dvojice fotek také. Nesmí tam být strana s jedinou fotkou,
překrývající se popisky v mapách ani useknutá hlava na fotce přes celou stranu (pomůže `zarovnani`).
Pak ukaž uživateli `prehled.jpg` a pár dvoustran. Připomínky zapracuj do `vyber.txt` a `kniha.json`
a vygeneruj náhled znovu. Opakuj, dokud nebude spokojený.

### 6. Tisk
```
python3 SKILL_DIR/tools/originaly.py --projekt P           # originály z Fotek/iCloudu (u 200 fotek ~20 min)
python3 SKILL_DIR/tools/kniha.py --projekt P --tisk        # tiskové strany z originálů
uv run --python 3.12 --with img2pdf python3 SKILL_DIR/tools/tisk.py --projekt P   # → kniha/pdf/
```
`tisk.py` vypíše rozměry PDF. Porovnej je s požadavky tiskárny. Jak objednat a nahrát PDF, je v `reference/tisk.md`.
Před objednávkou vyhledej aktuální slevový kód tiskárny (obvykle bývá nějaká akce).

### 7. Po objednávce
Do `PLAN.md` zapiš, co a kdy bylo objednáno. Na přání ukliď, co jde vygenerovat znovu: `kniha/foto_*`, `kniha/svg`,
`kniha/tisk`, `nahledy/`. Nech `kniha.json`, `vyber.txt`, `data/`, `originaly/`, `kniha/pdf/` a `kniha/nahled/`,
aby šla kniha opravit nebo dotisknout bez nového stahování.

## Jak vybírat (co se osvědčilo)
- **Většina fotek malá**: polaroidy, nejvýš 8 na stranu. Na celou stranu dej jen 4–6 nejsilnějších fotek celé
  knihy (krajina nebo momentka, ne selfie). Musí mít aspoň ~3000 px na kratší straně (rozměry jsou ve `vyber.json`).
- **Počet fotek odpovídá velikosti chvíle**: do 60 fotek 1 fotka, 60–150 fotek 2–4, velká dovolená 5–10.
  Místa s méně než ~40 fotkami vynech. Výjimkou jsou zastávky větších cest a roky, odkud je fotek málo celkově.
- **Každá dovolená s přespáním dostane mapku**, i víkend ve městě. Mapky dělá kniha sama, ty jen pohlídej název.
- Přednost mají fotky hlavní postavy a společné fotky. Ke každé cestě ale patří i jedna nebo dvě fotky místa.
  Nedávej dvě skoro stejné fotky. Střídej celé postavy, detaily a krajinu.
- **Nadpis roku je o lidech z knihy**: jejich cesty a milníky (promoce, stěhování, nový mazlíček, těhotenství).
  Svatby a oslavy kamarádů můžou být na fotkách, do nadpisu ale nepatří. Osobní věty (třeba u prvního roku
  „první rande a společný začátek“) nech napsat uživatele, nebo mu dej návrh ke schválení.
- **Popisky** jsou místo a datum. Když Fotky u domova dají jen obecnou oblast (CHKO, okres), nastav v `nazvy_mist`
  prázdný text a ukáže se jen datum.
- **Výlety v číslech** počítej jako každý den spolu venku mimo domov (`vylety.py`), ne jen dovolené. Číslo má být
  velké a pravdivé.

## Co kniha obsahuje
Titulní strana (vpravo, naproti vnitřku desek), úvodní dvoustrana s mapou světa („Kam jsme se spolu podívali“),
mapou domova se srdíčky v místech, kde jste bydleli, a čísly (roky, země, výlety a vlastní hodnoty). Každý rok
začíná velkým barevným letopočtem, podtitulem a mapkou roku s čárkovanými trasami z domova. Fotky jsou polaroidy
s washi páskou a ručně psaným popiskem, dovolené mají mapku (road trip s očíslovanými zastávkami, nebo „kde to je“
s cestou z domova) a razítko jako v pasu. Pak přijde pár fotek přes celou stranu, závěrečná dvojice přes
dvoustranu a „Pokračování příště…“. Rozvržení je čtvercové.

## Časté problémy
- `nacti_fotky.py` hlásí chybu oprávnění: chybí Úplný přístup k disku (viz výše), pak aplikaci restartuj.
- Fotka nemá náhled (je jen v iCloudu): kandidáti ji přeskočí. Do knihy ji dostaneš přes `originaly.py`, který stáhne originál.
- `originaly.py` nestáhne vše napoprvé: spusť ho znovu, dotáhne zbytek.
- Strana vyjde přeplněná nebo prázdná: uber nebo přidej fotky v daném roce. Rozvržení se přepočítá samo.
