"""Vygeneruje vsechny tabulky do `output/`.

    python3 make_all.py            # prepise output/
    python3 make_all.py --check    # nic nezapise, jen rekne, jestli by se neco zmenilo

`--check` je test reprodukovatelnosti: kdyz projde, obsah `output/` presne
odpovida dnesnim datum. Kdyz neprojde, bud se zmenila data, nebo nekdo sahl
do vygenerovanych souboru rucne.

Co vznikne:
  * `output/table1_cohorts.tex` ... `output/table7_nadeau_bengio.tex` -- HOLE
    tabulky, jen `tabular`. Zadny float, popisek ani poznamka, aby se daly
    vlozit kamkoli;
  * `output/supplement_body.tex` -- popisky, tabulky a poznamky BEZ preambule,
    k vlozeni primo do clanku jednim radkem (jednokrokovy preklad);
  * `output/supplement.tex` -- samostatny dokument, ktery kolem toho fragmentu
    obali preambuli. Preklada se stejnym kontejnerem jako clanek:
        cd output && docker run --rm -v "$PWD:/work" \\
          -u "$(id -u):$(id -g)" ghcr.io/tomasvicar/latex-overleaf:TL2025 \\
          supplement.tex
  * `output/BibFile.bib` -- zaznamy z `references.py`, ktere supplement cituje,
    aby sel prelozit samostatne. `elsarticle-num.bst` se nekopiruje, TeX Live
    si styl najde sam;
  * `output/PROVENANCE.md` -- seznam hodnot, ktere se ze zdroju spocitat nedaji
    a jsou proto zapsane primo v kodu generatoru.

Text popisku a poznamek zije v modulech jako `CAPTION` a `NOTE`; cisla v nich
se dosazuji z tychz dat jako telo tabulky.
"""

import argparse
import importlib
import re
import sys

import common
import derived
import references

#: Poradi je poradi tabulek v supplementu.
MODULES = [
    "table1_cohorts",
    "table2_hyperparameters",
    "table3_cv_performance",
    "table4_external_validation",
    "table5_reference_comparison",
    "table6_ensemble",
    "table7_nadeau_bengio",
]

SUPPLEMENT = "supplement.tex"
SUPPLEMENT_BODY = "supplement_body.tex"
BIBFILE = "BibFile.bib"

#: Vystrahy, ktere se maji objevit na zacatku supplementu.
BANNER = (
    "the captions and notes in this supplement were drafted with AI assistance "
    "and are provisional; every one of them has to be rewritten and checked by "
    "an author before submission"
)

#: Samostatny dokument -- preambule, hlavicka a bibliografie kolem fragmentu.
SUPPLEMENT_HEADER = r"""%% -------------------------------------------------------------------------
%% GENEROVANO: make_all.py -- needitovat rucne.
%% Samostatny supplement k odeslani. Preklad primo v teto slozce:
%%   docker run --rm -v "$PWD:/work" -u "$(id -u):$(id -g)" \
%%     ghcr.io/tomasvicar/latex-overleaf:TL2025 supplement.tex
%%
%% Obsah je ve `supplement_body.tex` vedle, aby sel vlozit i do clanku.
%% BibFile.bib vedle generuje make_all.py z references.py; styl elsarticle-num
%% si TeX Live najde sam, kopie neni potreba.
%% -------------------------------------------------------------------------
\documentclass[a4paper,10pt]{article}
\usepackage[margin=15mm]{geometry}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{array}
\usepackage{booktabs}

%% Poznamky pro spoluautory. Bez volby [show] se nesazi -- to je rezim
%% odesilani. `\usepackage[show]{manuscriptnotes}` je vyvesi na okraj.
\IfFileExists{manuscriptnotes.sty}{%
  \usepackage{manuscriptnotes}%
  %% V rezimu [show] potrebuji poznamky misto na okraji. V rezimu odesilani
  %% zustava sazba presne takova, jaka pujde do casopisu.
  \ifmanuscriptnotes\geometry{right=48mm,marginparwidth=40mm}\fi
}{}

\setlength{\parindent}{0pt}
\pagestyle{plain}

\begin{document}
\providecommand{\tablesdir}{.}

{\large\bfseries Supplementary material for\par}
\smallskip
{\large @TITUL@\par}
\smallskip
@AUTORI@
\bigskip

\input{supplement_body}

\bibliographystyle{elsarticle-num}
\bibliography{BibFile}
\end{document}
"""

#: Fragment ke vlozeni do clanku: popisky, tabulky a poznamky, zadna preambule.
BODY_HEADER = r"""%% -------------------------------------------------------------------------
%% GENEROVANO: make_all.py -- needitovat rucne.
%%
%% Popisky, tabulky a poznamky bez preambule. Do clanku staci jeden radek:
%%
%%     \input{tables_tom/output/supplement_body}
%%
%% Tabulky se vejdou i do uzke sazby `elsarticle` (390 pt), ale zdrobni.
%% Aby vypadaly jako v samostatnem supplementu, obal se vlozeni geometrii:
%%
%%     \usepackage{geometry}          % v preambuli, za elsarticle
%%     ...
%%     \clearpage
%%     \newgeometry{margin=15mm}
%%     \input{tables_tom/output/supplement_body}
%%     \restoregeometry
%%
%% Cislovani S1--S7 misto 1--7 zaridi pred vlozenim:
%%     \setcounter{table}{0}\renewcommand{\thetable}{S\arabic{table}}
%%
%% Preambule potrebuje: booktabs, array, amsmath, amssymb.
%% Cesta k tabulkam se bere z \tablesdir; vychozi hodnota plati pro preklad
%% z korene projektu.
%% -------------------------------------------------------------------------
\providecommand{\tablesdir}{tables_tom/output}

%% Zaloha, kdyby `manuscriptnotes` nebyl nactveny: vysadi se jen kotva,
%% poznamka se zahodi -- tedy tentyz vysledek jako v rezimu odesilani.
\providecommand{\NOTE}[2][]{#1}
\providecommand{\NOTEWARN}[2][]{#1}
\providecommand{\NOTECHECK}[2][]{#1}
\providecommand{\NOTETODO}[2][]{#1}
\providecommand{\NOTEQUERY}[2][]{#1}

{\large\bfseries Supplementary tables\par}
\bigskip
\NOTEWARN{@BANNER@}

"""

SUPPLEMENT_TABLE = r"""\begin{table}[htbp]
\centering
\caption{%(popisek)s}
\label{%(label)s}
\smallskip
\input{\tablesdir/%(soubor)s}
\end{table}

"""

SUPPLEMENT_NOTE = r"""\smallskip
{\footnotesize
\sloppy
\noindent
\textit{Notes to Table~\ref{%(label)s}.}
%(poznamka)s
\par}

"""

PROVENANCE_HEADER = """# Puvod hodnot ve vygenerovanych tabulkach

Generovano skriptem `make_all.py`, needitovat rucne.

Vsechno, co v tabulkach a jejich popiscich stoji a neni v seznamu nize, je
spoctene ze souboru v datove slozce `{data}`. Nize jsou hodnoty, ktere spocitat
nejdou, a poznamky, ktere generatory vystavily.

> **{banner}**

| Tabulka | Hodnota | Odkud / proc |
|---|---|---|
"""


def fill(text, numbers):
    """Dosadi cisla do popisku nebo poznamky.

    Kdyz modul zadna cisla nedodava, nechava se text na pokoji -- jinak by
    `str.format` zakopl o slozene zavorky v LaTeXu.
    """
    return text.format(**numbers) if numbers else text


def build_all():
    """[(modul, jmeno souboru, telo, cisla)] -- statistiky CV se pocitaji jednou."""
    stats = derived.cv_statistics()
    built = []
    for name in MODULES:
        module = importlib.import_module(name)
        body, numbers = module.render(stats)
        built.append((module, module.NAME, body, numbers))
    return built


def supplement_body_text(built):
    """Fragment: popisky, tabulky a poznamky, bez preambule."""
    out = [BODY_HEADER.replace("@BANNER@", BANNER)]
    for module, filename, _, numbers in built:
        out.append(SUPPLEMENT_TABLE % dict(
            popisek=fill(module.CAPTION, numbers), label=module.LABEL,
            soubor=filename.rsplit(".", 1)[0]))
        note = getattr(module, "NOTE", None)
        if note:
            out.append(SUPPLEMENT_NOTE % dict(
                label=module.LABEL, poznamka=fill(note, numbers).strip()))
        out.append("\\clearpage\n\n")
    return "".join(out)


def supplement_text():
    """Preambule, hlavicka s titulem a autory, bibliografie."""
    title, authors = common.load_manuscript_frontmatter()
    if title is None:
        title = common.manual(
            "[title of the article]",
            "titul clanku -- klon Overleafu v data/overleaf/ neni stazeny")
    return (SUPPLEMENT_HEADER
            .replace("@TITUL@", title)
            .replace("@AUTORI@", ", ".join(authors) if authors else "[authors]"))


def cited_keys(body):
    """Klice ze vsech \\cite v supplementu, v poradi vyskytu, bez duplicit."""
    keys = []
    for group in re.findall(r"\\cite[tp]?\{([^}]*)\}", body):
        for key in group.split(","):
            key = key.strip()
            if key and key not in keys:
                keys.append(key)
    return keys


def bibliography_text(body):
    """Minimalni `.bib` -- jen zaznamy, ktere supplement cituje."""
    keys = cited_keys(body)
    missing = [k for k in keys if k not in references.ENTRIES]
    if missing:
        raise SystemExit(
            "citace bez zaznamu v references.py: " + ", ".join(missing))
    header = ("%% GENEROVANO: make_all.py -- needitovat rucne.\n"
              "%% Zaznamy jsou v references.py; sem se davaji jen ty, ktere\n"
              "%% supplement doopravdy cituje.\n"
              f"%% Zaznamu: {len(keys)}.\n\n")
    return header + "\n\n".join(references.ENTRIES[k].strip() for k in keys) + "\n"


def provenance_text():
    rows = [f"| {table} | `{value}` | {why} |"
            for table, value, why in common.MANUAL_VALUES]
    return (PROVENANCE_HEADER.format(data=common.DATA, banner=BANNER)
            + "\n".join(rows) + "\n")


def check(built):
    problems = []
    generated = [(filename, body) for _, filename, body, _ in built]
    generated.append((SUPPLEMENT_BODY, supplement_body_text(built)))
    generated.append((SUPPLEMENT, supplement_text()))
    generated.append((BIBFILE, bibliography_text(supplement_body_text(built))))
    for filename, latex in generated:
        path = common.OUT / filename
        if not path.exists():
            problems.append(f"{filename}: chybi")
            continue
        current = common.HEADER_PATTERN.sub("", path.read_text())
        if current != common.HEADER_PATTERN.sub("", latex):
            problems.append(f"{filename}: obsah se lisi od toho, co plyne z dat")
    if problems:
        print("ROZDIL:", file=sys.stderr)
        for line in problems:
            print("  " + line, file=sys.stderr)
        return 1
    print(f"output/ odpovida datum v {common.DATA} ({len(built)} tabulek)")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="nic nezapisovat, jen porovnat s obsahem output/")
    args = parser.parse_args()

    built = build_all()
    if args.check:
        return check(built)

    for module, filename, body, _ in built:
        path = common.write(filename, body, module.__file__, module.SOURCES)
        print(path.name)

    (common.OUT / SUPPLEMENT_BODY).write_text(supplement_body_text(built))
    print(SUPPLEMENT_BODY)
    (common.OUT / SUPPLEMENT).write_text(supplement_text())
    print(SUPPLEMENT)
    (common.OUT / BIBFILE).write_text(bibliography_text(supplement_body_text(built)))
    print(BIBFILE)
    (common.OUT / "PROVENANCE.md").write_text(provenance_text())
    print("PROVENANCE.md")
    print("\nPOZOR: " + BANNER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
