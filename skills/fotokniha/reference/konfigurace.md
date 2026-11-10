# kniha.json – nastavení knihy

Šablona je v `template/kniha.example.json`. Soubor je čistý JSON, takže v něm nesmí být komentáře ani čárka za
posledním prvkem. Fotky se ve všech polích odkazují jako `kapitola/číslo`: číslo je z kontaktní tabule
`nahledy/<kapitola>.jpg`, třeba `2019-07-12/08`. Fotka musí být zapsaná ve `vyber.txt`.

## Základ
| pole | význam |
|---|---|
| `titul` | Nápis na titulní straně a obálce, např. „Jana & Petr“. |
| `podtitul` | Pod titulem. Výchozí je rozsah let fotek v knize („2016 – 2025“). |
| `od`, `do` | Které fotky načíst z knihovny (RRRR-MM-DD). |
| `osoby` | Přesná jména z Fotek. **První je hlavní postava knihy**: kapitoly bez ní se nevytvoří a její fotky mají přednost. Další osoby dávají bonus společným fotkám. |

## Domov a cesty
| pole | význam |
|---|---|
| `domovy` | Kde jste bydleli: `{"nazev", "lat", "lon", "od", "do"}` (roky). Návrh vypíše `domov.py`. Dává srdíčka do map a výchozí bod čárkovaných tras. |
| `dalsi_mista` | Místa, kam se jezdí na noc k rodině nebo do práce: `{"nazev", "lat", "lon"}`. Nepočítají se jako výlety. |
| `domovska_zeme` | Kód země (`CZ`, `SK`, …). Je zvýrazněná v mapách a podle ní se počítají „země“ a mapa domova. |
| `daleko_km` | Od kolika km od domova je den výlet nebo cesta. Výchozí 35. |
| `min_fotek` | Kolik fotek musí mít událost nebo jednodenní výlet, aby dostal kapitolu. Výchozí 40. Cesty s přespáním dostanou kapitolu vždy. |
| `udalosti_na_rok` | Kolik největších událostí za rok (mimo cesty) dostane kontaktní tabuli. Výchozí 4. |

## Texty
| pole | význam |
|---|---|
| `roky` | Podtitul u každého letopočtu: `{"2021": "Chorvatsko, stěhování a štěně Rex"}`. Max ~60 znaků (3 řádky). |
| `nazvy_mist` | Přejmenování míst z Fotek: `{"Krkonošský národní park": "Krkonoše"}`. `""` = v popisku jen datum (hodí se pro obecné oblasti u domova). Které názvy zkontrolovat, vypíše `vyber.py --mista` a po vykreslení `kniha.py`. |
| `popisky` | Vlastní popisek místo názvu místa. Pro celou kapitolu `{"2023-02-10": "Promoce v Olomouci"}`, nebo pro jednu fotku `{"2021-06-19/04": "Naše svatba"}`. Datum se přidá samo. |
| `texty.mapa_svet`, `texty.mapa_domov` | Nadpisy úvodní dvoustrany. Výchozí „Kam jsme se spolu podívali“ a „…a doma“. |
| `texty.konec` | Poslední strana. Výchozí „Pokračování příště…“. |
| `texty.cisla` | Až 5 čísel na úvodní dvoustraně: `[hodnota, popisek]`. Automatické hodnoty: `auto:roky`, `auto:zeme`, `auto:vylety` (zaokrouhleno dolů na desítky s „+“), `auto:fotky`. |

## Cesty
`cesty` je slovník podle id kapitoly (datum začátku cesty):
| pole | význam |
|---|---|
| `nazev` | Popisek pod mapkou cesty, např. „Chorvatsko 2019“. Výchozí je hlavní místo + rok. |
| `cil` | Vynutí mapku „kde to je“ (čárkovaná cesta z domova k jednomu bodu) s tímto popiskem. Hodí se pro pobyt na jednom místě, i když fotky jsou rozptýlené. |
| `trasa` | Přesný seznam zastávek road tripu (názvy, jak je ukazuje mapa). Bez něj se zastávky vyberou samy: místa vybraných fotek a největší další zastávky z cesty. |
| `razitko` | `["ITÁLIE", "TOSKÁNSKO"]` = vlastní text razítka. `false` = bez razítka. Výchozí je razítko u každé cesty s přespáním. |
| `mapa` | `false` = cesta nebude mít mapku. |
| `prehled` (v kořeni, ne v `cesty`) | Ruční špendlíky mapy světa `[["Chorvatsko '19 '22", 43.3, 17.0], …]`. Výchozí: cesty do zahraničí seskupené po oblastech. |

## Velké fotky
| pole | význam |
|---|---|
| `cela_strana` | Fotky přes celou stranu: odkaz, nebo `{"foto", "popisek", "zarovnani"}`. `popisek: ""` = bez popisku. `zarovnani`: `nahore`, `dole`, `vlevo`, `vpravo`, `stred` (co z fotky zůstane, když se ořízne na čtverec). |
| `titulni_foto` | Polaroid na titulní straně. |
| `zaver` | Fotky přes celou stranu na konci knihy, stejný formát jako `cela_strana`. Když jsou aspoň dvě, první dvě vyjdou proti sobě na jedné dvoustraně. |

## Tisk
| pole | význam |
|---|---|
| `tisk.profil` | `saal-30x30-professional` (ověřeno), nebo `vlastni`. |
| `tisk.obalka_foto` | Fotka na přední desku. Výchozí je `titulni_foto`. |
| `tisk.obalka_text` | `{"x": 0.5, "y": 0.16, "barva": "#2f2a26", "velikost": 400}`. Poloha nápisu na obálce jako zlomek šířky a výšky. Dej ho do klidného místa fotky (obloha), ne přes obličej. |
| vlastní profil | U `vlastni` doplň `strana_px` (strana včetně spadávky), `spadavka_px`, `dpi`, případně `dvoustrany`, `vnitrni_desky`, `stran_min`, `stran_max`, `obalka: {"w", "h", "spadavka", "dpi"}`. Viz `tisk.md`. |
