"""Table 5 — srovnani s referencni pipeline van Voorsta na tychz 141 pacientech.

Ctyri z peti radku jsou z dat:
  1. nase nejlepsi kombinace slucene pres foldy (POOL nize),
  2. jeho pipeline prepocitana na nasich datech -- `07_split_cv/`, SADA A,
  3.-4. nas klasifikator na jeho 52 ICC priznacich.
Posledni radek je hodnota, jak ji publikoval on; ta ve zdrojovych datech neni
a prochazi proto pres `common.manual()`.

SADA A vs. SADA B (otevrena otazka B5): ve `07_split_cv/` jsou dve neslucitelne
sady cisel. Tabulka uvadi SADU A (`test_set_metrics_across_splits.csv`, test na
vyclenenem foldu, 29+28+28+28+28 = 141), protoze je metodicky soumeritelna
s nasi pipeline. SADA B (`split_*/summary_test_results.csv`) pocita na 34
pacientech na split, dohromady 170, a cte ji obrazek vybrany do clanku.
Skript spocita obe a rozdil vypise do PROVENANCE.md.

Ke srovnani se pouziva `AUC_prob`, ne `AUC`: sloupec `AUC` ve ctyrech z peti
splitu degeneruje presne na 50,0, protoze model predikuje vetsinovou tridu.
"""

import collections
import csv
import statistics as st

import common
import derived

TITLE = "Comparison with the reference pipeline of van Voorst et al."

NAME = "table5_reference_comparison.tex"

LABEL = "tab:reference-comparison"

DASH = "---"

SOURCES =[common.RESULTS_CSV.name, "results_Henks_pipeline/07_split_cv/", "results_Henks_pipeline/03_feature_selection/icc_selection_report.csv", common.HENK_ICC_CSV.name]

CAPTION = (
    "Comparison with the reference pipeline of van Voorst et al. "
    r"\cite{{vanVoorst2022}} "
    "The first row summarizes the present study; rows two to four were computed "
    "on the MR CLEAN NO-IV development cohort with the same five outer folds as "
    r"in Table~\ref{{tab:cv-performance}}, so that the comparison is made within "
    "one dataset rather than across publications; the last row is the value "
    "reported in the original publication, on a different cohort and for a "
    "different endpoint. "
    "ICC, intraclass correlation coefficient: of the {n_features} features the "
    r"reference pipeline extracts, the {n_kept} with ICC $\geq$ {icc_threshold} "
    "are retained and the rest discarded. "
    r"AUC$_{{\text{{prob}}}}$ denotes the AUC computed from the predicted class "
    "probabilities, and is the quantity reported for the reference pipeline. "
    "Values are medians with the interquartile range in brackets, or means "
    r"$\pm$ standard deviation across folds, as indicated in the note below. "
    "An em dash marks a quantity the row does not have: the pooled row spans "
    "combinations with different accuracies, and the published row reports "
    "neither a range nor an accuracy."
)

NOTE = r"""
The first row pools {n_pooled} fold results, {n_pool} combinations $\times$ {k} outer folds, and its bracketed values are the interquartile range; the second row is a mean $\pm$ standard deviation over the {k} splits; rows three and four are medians over the {k} folds, with no further feature selection applied to the {n_kept} ICC-filtered features.
The last row is quoted from the publication: thrombus radiomics for eTICI $\geq$ 2B, a more permissive endpoint than the eTICI 2C--3 outcome of this article, as a mean over 100 bootstrap samples of 100 patients.
The plain \texttt{{AUC}} column of the reference pipeline degenerates to exactly 0.50 in {n_degenerate} of the five splits, because the fitted model assigns the majority class to every patient in those splits and its hard predictions therefore carry no ranking information.
AUC$_{{\text{{prob}}}}$, computed from the predicted probabilities, is the only quantity of that pipeline that is comparable with the AUC values reported elsewhere in this article, and it is the one used here.
By median accuracy the reference pipeline and both of our classifiers restricted to its {n_kept} ICC-filtered features stay below the majority-class accuracy of {baseline}, although the reference pipeline exceeds it in one individual split.
Rows two to four were recomputed against the eTICI 2C--3 outcome of this article --- the stored label column is named \texttt{{TICI\_2B-3}}, but its per-fold positive counts are exactly the {n_positive}/{n_patients} of this study --- and are directly comparable with the first row, whereas the published {published_auc} of the last row was obtained for eTICI $\geq$ 2B in a different cohort and differs from them in endpoint and cohort as much as in pipeline.
\NOTEQUERY{{the pool of the first row omits one whole-thrombus combination that also discriminated in cross-validation, and the reason is not documented in the source material}}
\NOTEQUERY{{decide which of the two mutually incompatible sets of numbers in the source data applies before this table is finalized: {set_a} against {set_b}}}
"""


#: Pool "nasich nejlepsich kombinaci" pro prvni radek -- 5 kombinaci x 5 foldu.
#: POZOR: vynechava global/whole RFI--XGBRF (CV median 0,673 vs. jeho 0,643)
#: a duvod neni nikde zdokumentovany. Viz OTAZKY, bod k Table 5.
POOL = [
    ("global", "rf_lasso"),
    ("global", "svc_lasso"),
    ("global", "svc_rfi"),
    ("distribution", "rf_rfi"),
    ("distribution", "svc_rfi"),
]


def load_reference_set_a():
    """SADA A: metriky na vyclenenem testovacim foldu, {measure: {split: score}}."""
    per = collections.defaultdict(dict)
    n_test = {}
    for row in csv.DictReader(common.HENK_SPLIT_METRICS.open()):
        split = int(row["split"])
        n_test[split] = int(row["n_test"])
        if row["score"]:
            per[row["measure"]][split] = float(row["score"])
    return per, n_test


def load_reference_set_b():
    """SADA B: `split_*/summary_test_results.csv`, {measure: {split: score}}."""
    per = collections.defaultdict(dict)
    n_pred = {}
    for split in range(common.N_SPLITS):
        path = common.HENK_DIR / f"07_split_cv/split_{split}/summary_test_results.csv"
        for row in csv.DictReader(path.open()):
            if row["score"]:
                per[row["measure"]][split] = float(row["score"])
        # pocet hodnocenych pacientu neni ulozeny primo; plyne z podilu a poctu
        n_pred[split] = round(per["y_pred=1_abs"][split]
                              / (per["y_pred=1_%"][split] / 100))
    return per, n_pred


def load_icc_report():
    """(pocet priznaku, pocet ponechanych, prah ICC dopocteny z dat)."""
    rows = list(csv.DictReader(common.HENK_ICC_REPORT.open()))
    kept = [float(r["icc"]) for r in rows if r["kept"] == "True"]
    dropped = [float(r["icc"]) for r in rows if r["kept"] != "True"]
    if kept and dropped and min(kept) <= max(dropped):
        raise SystemExit("ICC filtr neni prosty prah -- prepsat popisek")
    return len(rows), len(kept), min(kept)


def load_our_on_icc():
    """{method: {split: (ACC, AUC)}} z `henks_icc_test_results_all_folds.csv`."""
    out = collections.defaultdict(dict)
    for row in csv.DictReader(common.HENK_ICC_CSV.open()):
        out[row["method"]][int(row["split"])] = (float(row["ACC"]), float(row["AUC"]))
    return out


def check_labels_match(set_a):
    """Overi, ze referencni pipeline bezela na TYCHZ popiscich jako nase.

    Sloupec `yvar` se ve zdrojovych souborech jmenuje `TICI_2B-3`, ale clanek
    modeluje eTICI 2C-3. Porovnani poctu pozitivnich na fold rozhodne, ktere
    popisky to doopravdy byly.
    """
    ours = common.load_fold_labels()
    theirs = {s: int(v) for s, v in set_a["y_true=1_abs"].items()}
    mine = {s: sum(lab) for s, lab in ours.items()}
    if theirs != mine:
        raise SystemExit(
            "referencni pipeline nebezela na tychz popiscich: "
            f"jejich {theirs} vs. nase {mine}")
    return sum(mine.values()), sum(len(v) for v in ours.values())


def render(stats=None):
    common.set_table("Tabulka 5")
    stats = stats or derived.cv_statistics()

    pooled = [x for key in POOL for x in stats[key].auc]
    q1, med, q3 = common.quartiles(pooled)

    set_a, n_test = load_reference_set_a()
    set_b, n_pred_b = load_reference_set_b()
    n_positive, n_total = check_labels_match(set_a)

    auc_a = [set_a["AUC_prob"][s] / 100 for s in range(common.N_SPLITS)]
    # SADA B se do tabulky nedostane, ale rozdil proti ni se musi vedet.
    auc_b = [set_b["AUC_prob"][s] / 100 for s in range(common.N_SPLITS)]
    n_features, n_kept, icc_threshold = load_icc_report()
    ours_icc = load_our_on_icc()

    def icc_row(method, label):
        folds = ours_icc[method]
        auc = [folds[s][1] for s in range(common.N_SPLITS)]
        acc = [folds[s][0] for s in range(common.N_SPLITS)]
        return [
            f"Our {label} on the {n_kept} ICC-filtered features",
            "MR CLEAN NO-IV", str(n_total),
            common.f3(st.median(auc)), common.range_cell(auc),
            common.f3(st.median(acc)),
        ]

    published_n = common.manual(699, "van Voorst et al., pocet pacientu v jeho clanku")
    published_auc = common.manual(0.52, "van Voorst et al., publikovana AUC")
    acc_a = [set_a["acc"][s] / 100 for s in range(common.N_SPLITS)]

    rows = [
        ["Our best combinations, pooled", "MR CLEAN NO-IV", str(n_total),
         f"{common.f3(med)} [{common.f3(q1)}--{common.f3(q3)}]",
         common.range_cell(pooled), DASH],
        ["Reference pipeline, recomputed", "MR CLEAN NO-IV",
         str(sum(n_test.values())),
         f"${common.f3(st.mean(auc_a))} \\pm {common.f3(st.stdev(auc_a))}$",
         common.range_cell(auc_a), common.f3(st.median(acc_a))],
        icc_row("rf", "XGBRF"),
        icc_row("svc", "NuSVC"),
        ["van Voorst et al., as published", "MR CLEAN Registry", str(published_n),
         f"{published_auc:.2f}", DASH, DASH],
    ]

    numbers = dict(
        n_features=n_features, n_kept=n_kept,
        icc_threshold=f"{icc_threshold:.2f}",
        n_degenerate=sum(1 for s_ in range(common.N_SPLITS)
                         if abs(set_a["AUC"][s_] - 50.0) < 1e-9),
        n_positive=n_positive, n_patients=n_total,
        baseline=common.f3(n_positive / n_total),
        published_auc=f"{published_auc:.2f}",
        n_pooled=len(pooled), n_pool=len(POOL), k=common.N_SPLITS,
        set_a=(f"set A, {common.f3(st.mean(auc_a))} $\\pm$ "
               f"{common.f3(st.stdev(auc_a))} on {sum(n_test.values())} patients"),
        set_b=(f"set B, {common.f3(st.mean(auc_b))} $\\pm$ "
               f"{common.f3(st.stdev(auc_b))} on {sum(n_pred_b.values())}"),
    )

    colspec = (r">{\raggedright\arraybackslash}p{0.30\textwidth}"
               r">{\raggedright\arraybackslash}p{0.15\textwidth}rccc")
    header = [["Model", "Cohort", "$n$", "AUC", "AUC", "Median"],
              ["", "", "", "", "min--max", "ACC"]]
    spaced = []
    for i, row in enumerate(rows):
        if i:
            spaced.append(r"\addlinespace")
        spaced.append(row)
    style = [r"\footnotesize", r"\setlength{\tabcolsep}{2pt}"]
    body = common.tabular(colspec, header, [spaced], style)
    return body, numbers

if __name__ == "__main__":
    print(common.write(NAME, render()[0], __file__, SOURCES))
