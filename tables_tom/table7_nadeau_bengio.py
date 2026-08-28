"""Tabulka 7 — parova srovnani pipeline korigovanym resampled t-testem.

Dve skupiny radku:

  A. nase ctyri pipeline mezi sebou na global/whole (to, co je dnes v Results
     jednou vetou "|t| <= 1,14");
  B. **nase pipeline proti referencni pipeline van Voorsta**, kterou tabulka 5
     uvadi jen vedle sebe bez jakehokoli testu. Vsechny modely bezely na tychz
     peti vnejsich foldech a tychz pacientech, takze parovy test je primo
     pouzitelny.

Pro srovnani se vsude pouziva AUC; u referencni pipeline `AUC_prob`, protoze
jeji sloupec `AUC` ve ctyrech z peti splitu degeneruje na 50,0 (viz tabulka 5).

Co se ZAMERNE netestuje: radek "our best combinations, pooled" z tabulky 5.
Tech pet kombinaci bylo vybrano podle vysledku na tychz datech, takze by test
proti nim byl zaujaty ve prospech nasi metody. Testuji se proto vsechny ctyri
pipeline daneho datasetu, at uz dopadly jakkoli.
"""

import csv
import collections
import statistics as st

import common
import derived

TITLE = "Pairwise comparison of the pipelines by the corrected resampled $t$-test"

NAME = "table7_nadeau_bengio.tex"

LABEL = "tab:nadeau-bengio"

SOURCES = [common.RESULTS_CSV.name,
           "results_Henks_pipeline/07_split_cv/test_set_metrics_across_splits.csv",
           common.HENK_ICC_CSV.name]

#: Dataset, na kterem se porovnavaji nase pipeline mezi sebou i proti referenci.
FSET = "global"

METHOD_LABEL = {m: f"{sel}--{clf}" for m, (sel, clf) in common.METHODS.items()}

REFERENCE = "Reference pipeline"

#: Oboustranna kriticka hodnota Studentova rozdeleni pro df = 4, alfa = 0,05.
#: Konstanta z tabulek, aby balicek nepotreboval scipy.
T_CRITICAL = {4: 2.776}

CAPTION = (
    "Pairwise comparison of the pipelines by the corrected resampled $t$-test "
    r"of Nadeau and Bengio \cite{{Nadeau2003}}. "
    "The upper block compares the four pipelines of this study with one another "
    "on the whole-thrombus global-based dataset; the lower block compares them, "
    "and our two classifiers restricted to the reference pipeline's own "
    "{n_kept} ICC-filtered features, against the reference pipeline of van "
    r"Voorst et al.\ recomputed on the same cohort. "
    "Every model in the table was evaluated on the same {k} outer folds of the "
    "same {n_patients} patients, which is what makes the paired test applicable. "
    "Because the training sets of $k$-fold cross-validation overlap, the "
    "per-fold differences are not independent and the ordinary paired $t$-test "
    "underestimates their variance; the correction multiplies the variance by "
    r"$1/k + n_{{\text{{test}}}}/n_{{\text{{train}}}}$, here $1/{k} + {n_test}/"
    "{n_train} = {correction}$, which inflates the standard error "
    r"{inflation}-fold at $\mathrm{{df}} = {df}$. "
    "Fold sizes are taken from the data, not assumed. "
    r"Mean $\Delta$AUC is the mean of the {k} per-fold differences in AUC "
    "between pipeline A and pipeline B; a positive value favours A. "
    "$t$ (uncorrected) is the ordinary paired statistic, $t$ (corrected) the "
    "same quantity with the inflated variance. "
    r"The two-sided critical value at $\alpha = 0.05$ and "
    r"$\mathrm{{df}} = {df}$ is {critical}. "
    "Pipeline names combine selector and classifier as in "
    r"Table~\ref{{tab:cv-performance}}."
)

NOTE = r"""
Not one of the {n_pairs} comparisons reaches significance: the largest corrected statistic in absolute value is {max_t}, against a critical value of {critical}.
The four pipelines of this study are therefore statistically indistinguishable from one another, and none of them is distinguishable from the reference pipeline either, in either direction.
For the reference pipeline the compared quantity is AUC$_{{\text{{prob}}}}$, because its plain \texttt{{AUC}} column degenerates to exactly 0.50 in four of the five splits; see Table~\ref{{tab:reference-comparison}}.
The pooled row of Table~\ref{{tab:reference-comparison}} is deliberately absent here: those {n_pool} combinations were picked by their results on these same folds, so testing them against the reference pipeline would be biased in favour of the present study. All four pipelines of the dataset are tested instead, whatever their outcome.
With {k} folds the test has $\mathrm{{df}} = {df}$ and very little power, so these results are an absence of evidence for a difference, not evidence that the pipelines perform identically. The comparison that the data would support best, a DeLong test on the external ROC curves, was not possible because per-patient predicted scores on the Registry were not retained.
"""


def load_reference_auc():
    """AUC_prob referencni pipeline po splitech, jako podil (SADA A)."""
    per = {}
    for row in csv.DictReader(common.HENK_SPLIT_METRICS.open()):
        if row["measure"] == "AUC_prob" and row["score"]:
            per[int(row["split"])] = float(row["score"]) / 100
    return [per[s] for s in range(common.N_SPLITS)]


def load_our_on_icc_auc():
    """{method: [AUC po splitech]} pro nas klasifikator na 52 ICC priznacich."""
    per = collections.defaultdict(dict)
    for row in csv.DictReader(common.HENK_ICC_CSV.open()):
        per[row["method"]][int(row["split"])] = float(row["AUC"])
    return {m: [v[s] for s in range(common.N_SPLITS)] for m, v in per.items()}


def load_icc_kept():
    return sum(1 for r in csv.DictReader(common.HENK_ICC_REPORT.open())
               if r["kept"] == "True")


def render(stats=None):
    common.set_table("Tabulka 7")
    stats = stats or derived.cv_statistics()

    meta = derived.nb_correction()
    critical = T_CRITICAL.get(meta["df"])
    if critical is None:
        raise SystemExit(f"nemam kritickou hodnotu pro df = {meta['df']}")

    common.manual(
        f"kriticka hodnota t = {critical} pro df = {meta['df']}, alfa = 0,05",
        "tabulkova hodnota Studentova rozdeleni (balicek nepotrebuje scipy)")

    reference = load_reference_auc()
    ours_icc = load_our_on_icc_auc()

    _, own = derived.nadeau_bengio(stats, FSET)
    rows_own = [[METHOD_LABEL[a], METHOD_LABEL[b]] + cells(d, tn, tc, critical)
                for a, b, d, tn, tc in own]

    rows_reference = []
    for method in common.METHODS:
        result = derived.nb_statistic(stats[(FSET, method)].auc, reference,
                                      meta["correction"])
        rows_reference.append([METHOD_LABEL[method], REFERENCE]
                              + cells(*result, critical))
    for method, label in [("rf", "XGBRF"), ("svc", "NuSVC")]:
        result = derived.nb_statistic(ours_icc[method], reference,
                                      meta["correction"])
        rows_reference.append([f"{label} on ICC features", REFERENCE]
                              + cells(*result, critical))

    header = [
        ["Pipeline A", "Pipeline B", r"Mean $\Delta$AUC", "$t$", "$t$",
         r"$|t| > t_{\text{crit}}$"],
        ["", "", "(A $-$ B)", "(uncorrected)", "(corrected)", ""],
    ]
    style = [r"\scriptsize", r"\setlength{\tabcolsep}{3pt}"]
    groups = common.align([rows_own, rows_reference])
    body = common.tabular("llrrrc", header, groups, style)

    labels = common.load_fold_labels()
    all_t = [row[4] for row in rows_own + rows_reference]
    numbers = dict(
        k=meta["k"], n_test=f"{meta['n_test']:.1f}",
        n_train=f"{meta['n_train']:.1f}",
        correction=f"{meta['correction']:.4f}",
        inflation=f"{meta['se_inflation']:.2f}", df=meta["df"],
        critical=f"{critical}", n_kept=load_icc_kept(),
        n_patients=sum(len(v) for v in labels.values()),
        n_pairs=len(rows_own) + len(rows_reference),
        n_pool=5,
        max_t=max(all_t, key=lambda c: abs(float(c.strip("$")))).strip("$").lstrip("+-"),
    )
    return body, numbers


def cells(diff, t_naive, t_corrected, critical):
    return [
        common.signed(diff),
        common.signed(t_naive, 2),
        common.signed(t_corrected, 2),
        "no" if abs(t_corrected) <= critical else "yes",
    ]


if __name__ == "__main__":
    print(common.write(NAME, render()[0], __file__, SOURCES))
