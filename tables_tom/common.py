"""Sdilene nacitani zdrojovych dat a stavba LaTeXovych tabulek.

Pravidlo: kazde cislo, ktere se objevi ve vygenerovane tabulce, sem musi
pritect ze souboru v datove slozce nebo z kodu v read-only klonu. Co spocitat
nejde, prochazi funkci `manual()` — ta hodnotu propusti, ale zapise ji do
seznamu, ktery `make_all.py` vytiskne do `output/PROVENANCE.md`.
Cilem je, aby slo kdykoli rict, ktera bunka je z dat a ktera z rukopisu.

Generatory vraci HOLOU tabulku -- zadny float, popisek ani poznamku. Text
popisku a poznamky je v modulech jako `CAPTION` a `NOTE` a sesazuje ho az
`make_all.py` do `output/supplement.tex`.

Do datove slozky se nic nezapisuje (PRAVIDLO C. 1 a 2 v CLAUDE.md); vystup jde
vyhradne do `output/`. Kde data lezi, se nastavuje v `config.py` -- je to
jedina konfigurovatelna vec celeho balicku.
"""

from __future__ import annotations

import ast
import collections
import csv
import decimal
import json
import re
import statistics as st
from pathlib import Path

import config

csv.field_size_limit(10 ** 9)

# --------------------------------------------------------------------------
# Cesty
# --------------------------------------------------------------------------

DATA = config.DATA_DIR
OUT = config.OUTPUT_DIR

RESULTS_CSV = DATA / "gdrive/Models_comparicon/final_test_results_all_folds_updated.csv"
RANDOM_CSV = DATA / "gdrive/Models_comparicon/final_random_test_results.csv"
RANDOM_SUMMARY_CSV = DATA / "gdrive/Models_comparicon/final_random_test_results_summary.csv"
HENK_ICC_CSV = DATA / "gdrive/Models_comparicon/henks_icc_test_results_all_folds.csv"

BOOST_SUMMARY_CSV = DATA / "gdrive/Boosting/Boosting_results/overall_metrics_summary.csv"
BOOST_PRED_DIR = DATA / "gdrive/Boosting/Predictions"

HENK_DIR = DATA / "onedrive/results_Henks_pipeline"
HENK_ICC_REPORT = HENK_DIR / "03_feature_selection/icc_selection_report.csv"
HENK_SPLIT_METRICS = HENK_DIR / "07_split_cv/test_set_metrics_across_splits.csv"

#: Titul a autori do hlavicky supplementu se ctou z read-only klonu Overleafu
#: v datove slozce -- ten je reprodukovatelny (`scripts/pull_overleaf.sh`),
#: na rozdil od pracovni kopie v `paper/`, ktera se s nim rozchazi.
OVERLEAF = DATA / "overleaf"

HETERO_REPO = DATA / "heterogeneity"
HETERO_REF = "origin/public_branch"
REGISTRY_IDS_JSON = HETERO_REPO / "Registry_data_IDs.json"

N_SPLITS = 5

# --------------------------------------------------------------------------
# Evidence rucne zadanych hodnot
# --------------------------------------------------------------------------

MANUAL_VALUES: list[tuple[str, str, str]] = []
_CURRENT_TABLE = ["?"]


def set_table(name: str) -> None:
    _CURRENT_TABLE[0] = name


def manual(value, why: str):
    """Hodnota, ktera NENI ze zdrojovych dat. Propusti ji a zaeviduje."""
    MANUAL_VALUES.append((_CURRENT_TABLE[0], str(value), why))
    return value


# --------------------------------------------------------------------------
# Popisky kombinaci
# --------------------------------------------------------------------------

#: f_set_type -> (feature set, ROI); poradi je poradi radku ve vsech tabulkach
FSETS = collections.OrderedDict([
    ("global", ("global", "whole")),
    ("global_skeleton", ("global", "centerline")),
    ("distribution", ("distribution", "whole")),
    ("distribution_skeleton", ("distribution", "centerline")),
    ("voxel", ("voxel", "whole")),
    ("voxel_skeleton", ("voxel", "centerline")),
])

PATIENT_FSETS = [f for f in FSETS if not f.startswith("voxel")]

#: method -> (selektor, klasifikator); poradi je poradi radku uvnitr skupiny
METHODS = collections.OrderedDict([
    ("rf_lasso", ("LASSO", "XGBRF")),
    ("rf_rfi", ("RFI", "XGBRF")),
    ("svc_lasso", ("L1", "LinSVC")),
    ("svc_rfi", ("RFI", "NuSVC")),
])


def combos(fsets=None):
    """Vsechny (f_set_type, method) v poradi tabulek."""
    for f in (fsets if fsets is not None else FSETS):
        for m in METHODS:
            yield f, m


# --------------------------------------------------------------------------
# Nacitani
# --------------------------------------------------------------------------

class Fold(collections.namedtuple("Fold", "auc acc features")):
    """Metriky jedne kombinace na jednom vnejsim foldu.

    `features` jsou indexy sloupcu, ktere selektor ponechal -- ne jen jejich
    pocet. Rozlisit fallback po vynulovani vsech koeficientu (`[0]`) od
    jedineho skutecne vybraneho priznaku jinak nejde.
    """

    @property
    def n_features(self):
        return len(self.features)

    @property
    def is_l1_fallback(self):
        """Selektor nevybral nic a dosadil se index prvniho sloupce."""
        return self.features == [0]


def load_cv():
    """{(f_set_type, method): {split: Fold}} pro splity 0-4."""
    out = collections.defaultdict(dict)
    for row in csv.DictReader(RESULTS_CSV.open()):
        if row["split"] == "all_fold":
            continue
        key = (row["f_set_type"], row["method"])
        out[key][int(row["split"])] = Fold(
            auc=float(row["AUC"]),
            acc=float(row["ACC"]),
            features=list(ast.literal_eval(row["selected_features"])),
        )
    for key, folds in out.items():
        if sorted(folds) != list(range(N_SPLITS)):
            raise SystemExit(f"{RESULTS_CSV.name}: {key} nema vsech {N_SPLITS} foldu")
    return dict(out)


def load_external():
    """{(f_set_type, method): Fold} z radku split == 'all_fold' (Registry)."""
    out = {}
    for row in csv.DictReader(RESULTS_CSV.open()):
        if row["split"] != "all_fold":
            continue
        out[(row["f_set_type"], row["method"])] = Fold(
            auc=float(row["AUC"]),
            acc=float(row["ACC"]),
            features=list(ast.literal_eval(row["selected_features"])),
        )
    return out


def load_null_summary():
    """{(f_set_type, method): (AUC_mean, AUC_std)} z agregatu 100 permutaci."""
    out = {}
    for row in csv.DictReader(RANDOM_SUMMARY_CSV.open()):
        out[(row["f_set_type"], row["method"])] = (
            float(row["AUC_mean"]), float(row["AUC_std"]))
    return out


def load_null_per_iteration(metric="AUC"):
    """{(f_set_type, method): [prumer metriky pres 5 foldu] * 100 permutaci}.

    Cte 261MB soubor po radcich; posledni sloupec (`selected_features`)
    obsahuje carky, proto se stipe jen prvnich sedm poli.
    """
    per = collections.defaultdict(lambda: collections.defaultdict(dict))
    with RANDOM_CSV.open() as fh:
        header = next(fh).rstrip("\n").split(",")
        if header[:7] != ["split", "feature_set", "f_set_type", "method",
                          "iteration", "ACC", "AUC"]:
            raise SystemExit(f"{RANDOM_CSV.name}: necekana hlavicka {header}")
        column = header.index(metric)
        for line in fh:
            p = line.split(",", 7)
            per[(p[2], p[3])][int(p[4])][int(p[0])] = float(p[column])
    out = {}
    for key, iters in per.items():
        out[key] = [st.mean(iters[i][s] for s in range(N_SPLITS))
                    for i in sorted(iters)]
    return out


def load_registry_ids():
    return json.loads(REGISTRY_IDS_JSON.read_text())


def load_fold_labels():
    """{split: [bool]} — skutecne popisky pacientu vnejsich testovacich foldu.

    Bere je z ulozenych predikcnich vektoru, ktere jsou jediny soubor v `data/`,
    kde jsou popisky pacientu primo. Vsech 16 pacientskych modelu ma tytez
    splity, takze staci jeden z nich; shoda se overuje.
    """
    labels = {}
    for split in range(N_SPLITS):
        seen = None
        for fset in PATIENT_FSETS:
            for method in METHODS:
                path = BOOST_PRED_DIR / f"{split}_split_{fset}_{method}_patient_results.csv"
                row = next(csv.DictReader(path.open()))
                lab = [bool(x) for x in ast.literal_eval(row["original_label"])]
                if seen is None:
                    seen = lab
                elif lab != seen:
                    raise SystemExit(f"split {split}: {path.name} ma jine popisky")
        labels[split] = seen
    return labels


def load_prediction_lengths():
    """{f_set_type: [pocet predikci na split]} z ulozenych predikcnich vektoru.

    U pacientskych sad je to pocet pacientu testovaciho foldu, u voxelovych
    pocet voxelu -- prave to je doklad, ze jejich metriky nejsou soumeritelne.
    """
    out = {}
    for fset in FSETS:
        lengths = []
        for split in range(N_SPLITS):
            path = BOOST_PRED_DIR / f"{split}_split_{fset}_rf_lasso_patient_results.csv"
            row = next(csv.DictReader(path.open()))
            lengths.append(len(ast.literal_eval(row["original_label"])))
        out[fset] = lengths
    return out


def load_boosting_alpha(config="type1_all_featuresets"):
    """[alfa] vsech boostovacich kol jedne konfigurace, pres vsechny foldy."""
    path = (DATA / "gdrive/Boosting/Boosting_results" / config
            / "feature_weights_long.csv")
    return [float(r["alpha"]) for r in csv.DictReader(path.open())]


def load_boosting_accuracy():
    """{config: [accuracy] * 5 foldu}."""
    out = collections.defaultdict(list)
    for row in csv.DictReader(BOOST_SUMMARY_CSV.open()):
        out[row["config"]].append((int(row["test_split"]), float(row["accuracy"])))
    return {c: [a for _, a in sorted(v)] for c, v in out.items()}


def load_manuscript_frontmatter():
    """(titul, [autori]) z klonu Overleafu v `data/overleaf/<ID>/main.tex`.

    Cte se, nezapisuje. Kdyz klon neni stazeny, vraci se (None, []) a hlavicka
    se sestavi bez nich -- generovani kvuli tomu nepadne, ale `make_all.py`
    to vypise do PROVENANCE.md.
    """
    candidates = sorted(OVERLEAF.glob("*/main.tex")) if OVERLEAF.exists() else []
    if not candidates:
        return None, []
    text = re.sub(r"(?<!\\)%.*", "", candidates[0].read_text())
    title = re.search(r"\\title\{(.+?)\}\s*$", text, re.M)
    authors = re.findall(r"\\author(?:\[[^\]]*\])?\{(.+?)\}\s*$", text, re.M)
    clean = [re.sub(r"\\corref\{[^}]*\}", "", a).replace("~", " ").strip()
             for a in authors]
    return (title.group(1).strip() if title else None), clean


def read_hetero(path: str) -> str:
    """Zdrojak z read-only klonu, z vetve `public_branch` (jen cteni)."""
    import subprocess
    return subprocess.run(
        ["git", "-C", str(HETERO_REPO), "show", f"{HETERO_REF}:{path}"],
        check=True, capture_output=True, text=True).stdout


# --------------------------------------------------------------------------
# Statistika
# --------------------------------------------------------------------------

def quartiles(values):
    """(Q1, median, Q3) linearni interpolaci, jako numpy.percentile."""
    q1, _, q3 = st.quantiles(values, n=4, method="inclusive")
    return q1, st.median(values), q3


def benjamini_hochberg(pvalues):
    """BH korekce; vraci q-hodnoty ve vstupnim poradi."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    q = [0.0] * m
    running = 1.0
    for rank, idx in reversed(list(enumerate(order, start=1))):
        running = min(running, pvalues[idx] * m / rank)
        q[idx] = running
    return q


def permutation_p(real_mean, null_means):
    """p = (b + 1) / (m + 1), b = pocet permutaci s prumerem >= realnym."""
    b = sum(1 for x in null_means if x >= real_mean)
    return (b + 1) / (len(null_means) + 1)


def kappa_index(real_mean, null_mean):
    """kappa-typovy index: podil dosazeneho zlepseni na maximalne moznem."""
    return (real_mean - null_mean) / (1 - null_mean)


# --------------------------------------------------------------------------
# Formatovani
# --------------------------------------------------------------------------

def _round(x, digits):
    """Zaokrouhleni pulky NAHORU, ne ke sude cifre a ne pres binarni float.

    `f"{0.7875:.3f}"` da 0.787, protoze 0,7875 je v plovouci radove carce
    ulozeno o kousek min. Pres Decimal(str(x)) se pracuje s tou hodnotou,
    ktera je zapsana ve zdrojovem CSV, a pul se zaokrouhluje nahoru.
    """
    quantum = decimal.Decimal(1).scaleb(-digits)
    value = decimal.Decimal(str(x)).quantize(quantum, rounding=decimal.ROUND_HALF_UP)
    return f"{value:.{digits}f}"


def f3(x):
    return _round(x, 3)


def f4(x):
    return _round(x, 4)


def signed(x, digits=3):
    value = _round(x, digits)
    return f"$+{value}$" if x >= 0 else f"${value}$"


def f3m(x):
    """Tri desetinna mista v matematickem rezimu -- kvuli spravnemu minusu."""
    return f"${_round(x, 3)}$"


def integer(x):
    return f"{int(round(x))}" if abs(x - round(x)) < 1e-9 else f"{x:g}"


def iqr_cell(values):
    q1, med, q3 = quartiles(values)
    return f"{f3(med)} [{f3(q1)}--{f3(q3)}]"


def range_cell(values):
    return f"{f3(min(values))}--{f3(max(values))}"


def tabular(colspec, header, groups, style=()):
    """Holy `tabular` s booktabs. Zadny float, zadny popisek, zadny label.

    header: seznam radku hlavicky (kazdy uz jako seznam bunek)
    groups: seznam skupin radku; mezi skupinami se sazi \\midrule.
            Radek zadany jako retezec (napr. r"\\addlinespace") jde do vystupu
            doslova.
    style:  prikazy velikosti pisma a rozestupu sloupcu. Obali se slozenymi
            zavorkami, aby se pri prostem \\input nepropsaly do textu za
            tabulkou.
    """
    lines = []
    if style:
        lines.append("{" + "".join(style) + "%")
    lines.append(r"\begin{tabular}{" + colspec + "}")
    lines.append(r"\toprule")
    for cells in header:
        lines.append(" & ".join(cells) + r" \\")
    lines.append(r"\midrule")
    for i, rows in enumerate(groups):
        if i:
            lines.append(r"\midrule")
        for cells in rows:
            if isinstance(cells, str):
                lines.append(cells)
            else:
                lines.append(" & ".join(cells) + r" \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}" + ("}" if style else ""))
    return "\n".join(lines) + "\n"


def align(groups):
    """Zarovna sloupce mezerami, aby byl vystup citelny i ve zdrojaku."""
    rows = [r for g in groups for r in g if not isinstance(r, str)]
    if not rows:
        return groups
    width = max(len(r) for r in rows)
    widths = [0] * width
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(c))
    return [[r if isinstance(r, str)
             else [c.ljust(widths[i]) if i < len(r) - 1 else c
                   for i, c in enumerate(r)]
             for r in g] for g in groups]


HEADER = """%% ---------------------------------------------------------------------------
%% GENEROVANO: {script}
%% Needitovat rucne -- zmeny prepise dalsi beh `python3 make_all.py`.
%% Zdroje: {sources}
%% ---------------------------------------------------------------------------
"""


#: Hlavicka se pri porovnavani (`make_all.py --check`) odstrihne.
HEADER_PATTERN = re.compile(r"\A(?:%%.*\n)+")


def write(name, latex, script, sources):
    """Zapise jednu tabulku do `output/`; vraci cestu."""
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    header = HEADER.format(script=Path(script).name, sources=", ".join(sources))
    path.write_text(header + latex)
    return path
