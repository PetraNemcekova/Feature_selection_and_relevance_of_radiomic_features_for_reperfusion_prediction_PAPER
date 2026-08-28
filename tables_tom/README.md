# Tabulky článku — generované ze zdrojových dat

Jeden skript na tabulku. Každý přečte stažená data, spočítá čísla a zapíše do
`output/` hotový float — popisek, tabulka, poznámka pod ní. Sedm tabulek,
číslovaných průběžně 1–7; dělení na hlavní text a supplement se tady neřeší.

Popisky jsou převzaté z `paper/sections/06_tables.tex` a `07_supplementary.tex`
a doplněné tak, aby tabulka obstála samostatně v supplementu. **Čísla uvnitř
popisků a poznámek se dopočítávají z týchž dat jako tělo tabulky**, takže se
s ním nemůžou rozejít — včetně mediánů, rozsahů, počtů kombinací nad baseline,
počtu voxelových predikcí nebo záporných vah v boostingu.

## Použití

```bash
cd tables
python3 make_all.py                 # přegeneruje output/
python3 make_all.py --check         # nic nezapíše, jen ověří, že output/ sedí na data
python3 table3_cv_performance.py    # jen jedna tabulka
```

**Jediné, co se nastavuje, je cesta k datům** — `config.py`, proměnná `DATA_DIR`.
Buď se přepíše v souboru, nebo se předá zvenčí:

```bash
DATA_DIR=/jina/cesta/k/datum python3 make_all.py
```

Do datové složky se nikdy nic nezapisuje, čte se jen z ní.

## Co v `output/` vznikne

| Soubor | K čemu |
|---|---|
| `table1_cohorts.tex` … `table7_nadeau_bengio.tex` | hotové floaty s popiskem a poznámkou |
| `all_tables.tex` | vloží všech sedm najednou do rukopisu |
| `supplement_body.tex` | popisky, tabulky a poznámky bez preambule — k vložení do článku |
| `supplement.tex` | samostatný dokument k odeslání: preambule, hlavička, bibliografie |
| `BibFile.bib` | záznamy z `references.py`, které supplement cituje |
| `PROVENANCE.md` | co v tabulkách není spočítané z dat |

### Vložení do rukopisu

Nic se nekopíruje, jen se vkládá odkazem — po přegenerování se tabulka
aktualizuje sama:

```latex
\input{../tables/output/table3_cv_performance}   % jedna tabulka
\input{../tables/output/all_tables}              % všechny naráz
```

Soubory `table1…7.tex` jsou holé `tabular` — popisek a poznámka jsou
v `supplement_body.tex`. Do článku se vloží celý supplement jedním řádkem:

```latex
\usepackage{geometry}          % v preambuli, za elsarticle
...
\clearpage
\newgeometry{margin=15mm}
\input{tables_tom/output/supplement_body}
\restoregeometry
```

`\newgeometry` dá supplementu stejnou šířku sazby jako když se překládá
samostatně, `\restoregeometry` vrátí článku jeho vlastní. Odkazuje se přes
`\ref` na labely
`tab:cohorts`, `tab:hyperparameters`, `tab:cv-performance`,
`tab:external-validation`, `tab:reference-comparison`, `tab:ensemble`,
`tab:nadeau-bengio`. Cestu bere `all_tables.tex` z `\tablesdir`, jehož výchozí
hodnota `../tables/output` platí pro překlad z `paper/`. Odjinud se určí
**před** vložením:

```latex
\providecommand{\tablesdir}{cesta/k/tables/output}
```

Preambule potřebuje `booktabs`, `array` a `amsmath` — v `paper/main.tex` už jsou.
Velikost písma a rozestupy sloupců si každá tabulka nese v sobě, uzavřené ve
složených závorkách, takže se do textu za tabulkou nepropíšou. Všech sedm se
vejde do šířky sazby `elsarticle` (390 pt) bez jediného Overfull.

### Samostatný supplement

```bash
cd tables/output
docker run --rm -v "$PWD:/work" -u "$(id -u):$(id -g)" \
  ghcr.io/tomasvicar/latex-overleaf:TL2025 supplement.tex
```

Vznikne `supplement.pdf` — osm stran A4: hlavička s titulem a autory, sedm
tabulek každá na své straně s popiskem a poznámkou, a seznam literatury.
`BibFile.bib` vedle si generátor skládá z `references.py` — vlastního souboru
s bibliografickými záznamy, které supplement cituje (dnes tři). **Nic se nekopíruje
z `paper/`**: pracovní kopie se s Overleafem rozchází (17 záznamů proti 70), takže
číst odtud by znamenalo vyrábět supplement z něčeho, co se nikde nereprodukuje.
Když do popisku přibude citace, musí přibýt záznam v `references.py`, jinak
generování spadne. Styl `elsarticle-num.bst` si TeX Live najde sám.

Titul a autoři v hlavičce se čtou z read-only klonu Overleafu
(`data/overleaf/<ID>/main.tex`) — ten je reprodukovatelný přes
`scripts/pull_overleaf.sh`.

## Poznámky pro spoluautory

Nedodělky nejsou psané jako `[TODO]` do textu, ale přes příkazy balíčku
`manuscriptnotes`, takže **v režimu odesílání zmizí**:

| Příkaz | Kde |
|---|---|
| `\NOTETODO` | co ještě chybí dopočítat nebo doplnit (tab. 1 dvakrát, 3) |
| `\NOTEWARN` | rozpory, které mají blokovat odeslání (tab. 1, 4) |
| `\NOTEQUERY` | rozhodnutí, které musí udělat autor (tab. 5 dvakrát) |

`\usepackage{manuscriptnotes}` je nesází, `\usepackage[show]{manuscriptnotes}`
je vyvěsí na okraj — a supplement si v tom režimu sám rozšíří pravý okraj, aby
se tam vešly. Když balíček není po ruce, fragment si definuje náhradní příkazy,
které se chovají jako režim odesílání, takže překlad nespadne.

**Na začátku supplementu je `\NOTEWARN`, že popisky jsou AI koncept a musí je
autor přepsat.** Totéž vypíše `make_all.py` na konci každého běhu a stojí to
i v `PROVENANCE.md`.

## Co která tabulka je

| Soubor | Tabulka | Hlavní zdroj |
|---|---|---|
| `table1_cohorts.py` | výběr pacientů v obou kohortách | popisky foldů + `Registry_data_IDs.json`; **vylučovací kaskáda je z rukopisu, ne z dat** |
| `table2_hyperparameters.py` | prohledávané prostory hyperparametrů | AST zdrojáků v `heterogeneity@origin/public_branch` |
| `table3_cv_performance.py` | křížová validace, všech 24 kombinací | `final_test_results_all_folds_updated.csv` + permutační baseline |
| `table4_external_validation.py` | externí validace na Registry | tentýž CSV, řádky `split == "all_fold"` |
| `table5_reference_comparison.py` | srovnání s pipeline van Voorsta | `results_Henks_pipeline/` + `henks_icc_test_results_all_folds.csv` |
| `table6_ensemble.py` | 15 konfigurací AdaBoostu proti svým členům | `Boosting_results/overall_metrics_summary.csv` |
| `table7_nadeau_bengio.py` | párová srovnání pipeline korigovaným t-testem | `final_test_results_all_folds_updated.csv` |

Tabulka 3 je sloučením toho, co v rukopisu bylo rozdělené na Table 3 (16
pacientských kombinací s permutačními sloupci) a Table S1 (všech 24 s rozsahem
přes foldy). Dělení dávalo smysl jen kvůli hlavnímu textu a supplementu.

`common.py` je sdílené načítání a sazba, `derived.py` odvozené statistiky
(mediány, permutační *p*, Benjamini–Hochberg, Nadeau–Bengio) — počítají se
jednou pro všechny tabulky, aby se nemohly rozejít.

## Co v tabulkách není z dat

Po každém běhu vznikne `output/PROVENANCE.md` — seznam všech hodnot, které se
ze zdrojů spočítat nedají a jsou proto napsané v kódu generátoru. Dnes je to
vylučovací kaskáda v tabulce 1, publikovaná čísla van Voorsta v tabulce 5 a
poznámky k otevřeným otázkám. Všechno ostatní je spočtené.

## Pojistky

Generátory raději spadnou, než by vysadily zastaralé číslo:

- chybí-li kombinaci fold, `load_cv()` skončí chybou;
- nesedí-li vylučovací kaskáda tabulky 1 na 141 pacientů z uložených foldů,
  skript spadne;
- objeví-li se v optimalizačním kódu nový hyperparametr nebo tvar meze, který
  parser neumí přeložit, tabulka 2 spadne;
- tabulka 5 ověřuje, že referenční pipeline běžela na týchž popiscích jako naše
  (sloupec se ve zdroji jmenuje `TICI_2B-3`, ale počty pozitivních na fold
  odpovídají 82/141 eTICI 2C–3 této práce);
- tabulka 4 kontroluje, že směr posunu na Registry pořád sleduje výhradně
  hodnotu z křížové validace — na tom stojí věta v poznámce pod ní;
- tabulka 6 spadne, kdyby některá konfigurace ensemblu začala překonávat svého
  nejlepšího člena, protože poznámka tvrdí opak;
- `make_all.py --check` ohlásí každý rozdíl mezi `output/` a tím, co plyne z dat.
