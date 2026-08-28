"""Tabulka 3 — krizova validace vsech 24 kombinaci na NO-IV.

Sloucena verze toho, co byvalo rozdelene na Table 3 (16 pacientskych kombinaci
s permutacnimi sloupci) a Table S1 (vsech 24 s rozsahem pres foldy). Deleni
davalo smysl, jen dokud byla cast v hlavnim textu a cast v supplementu; popisek
i poznamka jsou proto slozene z obou puvodnich zneni v `paper/sections/`.

Vse ze `final_test_results_all_folds_updated.csv` (splity 0-4) a z permutacni
baseline; q-hodnoty jsou Benjamini-Hochberg pres vsech 24 kombinaci.

Poznamka je zamerne AZ ZA floatem: uvnitr nej byla tabulka vyssi nez stranka.
Vsechna cisla v ni se dopocitavaji z tychz dat jako telo tabulky, takze se
s ni nemuzou rozejit.
"""

import statistics as st

import common
import derived

TITLE = "Cross-validated performance of all 24 dataset-by-pipeline combinations"

NAME = "table3_cv_performance.tex"

LABEL = "tab:cv-performance"

SOURCES = [common.RESULTS_CSV.name, common.RANDOM_SUMMARY_CSV.name,
           common.RANDOM_CSV.name,
           "Boosting/Predictions/*_patient_results.csv (delky predikci)"]

FSET_LABEL = {"global": "global", "distribution": "distrib.", "voxel": "voxel"}
ROI_LABEL = {"whole": "whole", "centerline": "cent."}

#: Pocet permutaci na fold, ze ktereho plyne rozliseni p-hodnot.
N_PERMUTATIONS = 100

CAPTION = (
    "Cross-validated performance of all 24 dataset-by-pipeline combinations in "
    "the MR CLEAN NO-IV cohort ($n = {n_patients}$), over five outer folds. "
    r"Feature set: \emph{{global}}, eight summary statistics of each radiomic "
    r"feature over the thrombus, one row per patient; \emph{{distribution}}, a "
    "ten-bin histogram of each radiomic feature over the thrombus, one row per "
    r"patient; \emph{{voxel}}, the radiomic feature values themselves, one row "
    "per voxel. "
    r"ROI: \emph{{whole}}, the dilated thrombus mask; \emph{{centerline}}, the "
    "dilated skeleton of the thrombus mask. "
    r"Selector (Sel.): LASSO, $\ell_1$-penalized regression; L1, embedded "
    "selection by the non-zero coefficients of the classifier itself; RFI, "
    r"gain-based feature importance of an \texttt{{XGBRFClassifier}}. "
    r"Classifier (Class.): XGBRF, \texttt{{XGBRFClassifier}}; LinSVC, linear "
    r"support vector classifier with an $\ell_1$ penalty; NuSVC, $\nu$-support "
    "vector classifier with a radial basis function kernel. "
    "In the body of the table the distribution-based feature set is "
    r"abbreviated \emph{{distrib.}}\ and the centerline ROI \emph{{cent.}} "
    "AUC, area under the receiver operating characteristic curve; "
    "ACC, accuracy; "
    "IQR, interquartile range across the five folds; "
    "min--max, the smallest and largest value across the five folds; "
    r"Med.\ $n$, median number of features retained by the selector; "
    "Null AUC, mean AUC of the permutation baseline; "
    r"$\kappa$, the $\kappa$-type index of the observed AUC relative to that "
    "baseline; $p$, permutation $p$-value; $q$, the same $p$-value after "
    "Benjamini--Hochberg correction across all 24 combinations."
)

NOTE = r"""
Accuracy must be read against the majority-class accuracy of the development cohort, ${n_positive}/{n_patients} = {baseline}$; only {n_above} of the 24 combinations exceed it by median accuracy, and {folds_below} of the {n_folds} individual fold results ({folds_below_pct}\%) fall below it.
The class ratio itself varies across folds ({ratios}), so in the first fold the majority class is the absence rather than the presence of near-complete or complete reperfusion.
The largest single fold result of the whole study is {best_auc}, obtained by {best_combo} in fold {best_fold}.
Averaged over the eight whole-thrombus patient-level combinations, AUC per fold is {per_fold}, a spread within a single fold of up to {spread}; between-fold variability therefore exceeds between-method variability.
The permutation null was obtained from {m} label permutations at the patient level per outer fold; with $m = {m}$ permutations the smallest attainable $p$-value is $p = (0+1)/({m}+1) = {p_min}$, which bounds the resolution of every permutation result in this table.
The Null AUC, $\kappa$, $p$ and $q$ columns were computed from the \emph{{mean}} AUC across folds, whereas the AUC column reports the \emph{{median}}; the two summaries are not interchangeable and are shown side by side deliberately.
{n_uncorrected} of the 24 combinations reach $p < 0.05$ uncorrected and {n_bh} survive Benjamini--Hochberg correction\NOTETODO{{cite Benjamini and Hochberg 1995; the key is missing from BibFile.bib}} for AUC, while {bh_acc_phrase} for accuracy.
No centerline combination survives correction; across the eight of them the mean AUC ranges from {cent_auc_lo} to {cent_auc_hi} against a null of {cent_null_lo}--{cent_null_hi}, $\kappa$ from {cent_kappa_lo} to {cent_kappa_hi} and $p$ from {cent_p_lo} to {cent_p_hi}.\\
\textsuperscript{{a}} In these {n_fallback} combinations the $\ell_1$ penalty shrank every coefficient to zero in every fold and the code substituted the index of the first column; the retained feature is a fallback, not one the selector identified as informative.
Combinations with a median of one retained feature but no mark reached that median with genuinely non-zero coefficients.\\
\textsuperscript{{b}} The unit of analysis of the voxel-based datasets is the voxel, not the patient, and their metrics are therefore \emph{{not}} comparable with the remaining rows.
Across the five folds the voxel/whole datasets contribute {vox_total} voxel-level predictions ({vox_per_fold}) and the voxel/centerline datasets {voxs_total} ({voxs_per_fold}), against {n_patients} patient-level predictions ({pat_per_fold}) for every other dataset.
The consequence is visible in the permutation null, whose standard deviation is {vox_sd_lo}--{vox_sd_hi} for the voxel-based combinations against {other_sd_lo}--{other_sd_hi} for all others, so that the voxel-based $p$-values are computed against a spuriously narrow null and are not comparable with the rest of the table.
{n_vox_bh} voxel-based combinations are formally significant for AUC after correction; they must not be read as evidence for a signal.
\NOTETODO{{patient-level majority-vote aggregation of the voxel-based predictions, which would make these rows comparable}}
"""


def facts(stats):
    """Cisla do popisku a poznamky -- vsechna z tychz dat jako telo tabulky."""
    labels = common.load_fold_labels()
    lengths = common.load_prediction_lengths()
    n_patients = sum(len(v) for v in labels.values())
    n_positive = sum(sum(v) for v in labels.values())
    baseline = n_positive / n_patients

    patient = [k for k in stats if not k[0].startswith("voxel")]
    voxel = [k for k in stats if k[0].startswith("voxel")]
    centerline = [k for k in patient if k[0].endswith("_skeleton")]
    whole = [k for k in patient if not k[0].endswith("_skeleton")]

    best = max(((k, i, v) for k in stats for i, v in enumerate(stats[k].auc)),
               key=lambda x: x[2])
    best_fname, best_roi = common.FSETS[best[0][0]]
    best_sel, best_clf = common.METHODS[best[0][1]]

    per_fold = [st.mean(stats[k].auc[i] for k in whole)
                for i in range(common.N_SPLITS)]
    spread = max(max(stats[k].auc[i] for k in whole)
                 - min(stats[k].auc[i] for k in whole)
                 for i in range(common.N_SPLITS))

    n_above = sum(1 for k in stats if stats[k].acc_median > baseline)
    folds_below = sum(1 for k in stats for a in stats[k].acc if a < baseline)
    n_folds = len(stats) * common.N_SPLITS

    def rng(keys, attr, fmt=common.f3):
        values = [getattr(stats[k], attr) for k in keys]
        return fmt(min(values)), fmt(max(values))

    cent_auc = rng(centerline, "auc_mean")
    cent_null = rng(centerline, "null_mean")
    cent_kappa = rng(centerline, "kappa", common.f3m)
    cent_p = rng(centerline, "p", common.f4)
    vox_sd = rng(voxel, "null_std")
    other_sd = rng(patient, "null_std")

    return dict(
        n_patients=n_patients, n_positive=n_positive,
        baseline=common.f3(baseline), n_above=n_above,
        folds_below=folds_below, n_folds=n_folds,
        folds_below_pct=f"{100 * folds_below / n_folds:.1f}",
        ratios=", ".join(common.f3(sum(labels[s]) / len(labels[s]))
                         for s in sorted(labels)),
        best_auc=common.f3(best[2]), best_fold=best[1],
        best_combo=f"{best_fname}/{best_roi}/{best_sel}/{best_clf}",
        per_fold=", ".join(common.f3(v) for v in per_fold),
        spread=common.f3(spread),
        m=N_PERMUTATIONS, p_min=common.f4(1 / (N_PERMUTATIONS + 1)),
        n_fallback=sum(1 for k, folds in common.load_cv().items()
                       if all(f.is_l1_fallback for f in folds.values())),
        n_uncorrected=sum(1 for k in stats if stats[k].p < 0.05),
        n_bh=sum(1 for k in stats if stats[k].q < 0.05),
        bh_acc_phrase=("none survives it"
                       if not sum(1 for k in stats if stats[k].q_acc < 0.05)
                       else f"{sum(1 for k in stats if stats[k].q_acc < 0.05)} "
                            "survive it"),
        n_vox_bh=sum(1 for k in voxel if stats[k].q < 0.05),
        cent_auc_lo=cent_auc[0], cent_auc_hi=cent_auc[1],
        cent_null_lo=cent_null[0], cent_null_hi=cent_null[1],
        cent_kappa_lo=cent_kappa[0], cent_kappa_hi=cent_kappa[1],
        cent_p_lo=cent_p[0], cent_p_hi=cent_p[1],
        vox_sd_lo=vox_sd[0], vox_sd_hi=vox_sd[1],
        other_sd_lo=other_sd[0], other_sd_hi=other_sd[1],
        vox_total=sum(lengths["voxel"]),
        vox_per_fold=", ".join(str(v) for v in lengths["voxel"]),
        voxs_total=sum(lengths["voxel_skeleton"]),
        voxs_per_fold=", ".join(str(v) for v in lengths["voxel_skeleton"]),
        pat_per_fold=", ".join(str(len(labels[s])) for s in sorted(labels)),
    )


def render(stats=None):
    common.set_table("Tabulka 3")
    stats = stats or derived.cv_statistics()

    cv = common.load_cv()
    fallback = {k: all(f.is_l1_fallback for f in folds.values())
                for k, folds in cv.items()}

    groups = []
    for fset in common.FSETS:
        fname, roi = common.FSETS[fset]
        label = FSET_LABEL[fname]
        if fname == "voxel":
            label += r"\textsuperscript{b}"
        rows = []
        for method in common.METHODS:
            s = stats[(fset, method)]
            sel, clf = common.METHODS[method]
            n = common.integer(s.n_median)
            # Znacka patri jen tam, kde selektor doopravdy nevybral nic a
            # dosadil se index prvniho sloupce. Medi\u00e1n 1 sam o sobe nestaci:
            # distribution/whole/L1 ma medi\u00e1n 1, ale ve trech z peti foldu
            # jde o skutecny nenulovy koeficient, ne o fallback.
            if fallback[(fset, method)]:
                n += r"\textsuperscript{a}"
            rows.append([
                label, ROI_LABEL[roi], sel, clf,
                common.iqr_cell(s.auc),
                common.range_cell(s.auc),
                common.f3(s.acc_median),
                n,
                common.f3(s.null_mean),
                common.signed(s.kappa),
                common.f4(s.p),
                common.f4(s.q),
            ])
        groups.append(rows)

    header = [
        ["Feature", "ROI", "Sel.", "Class.", "Median AUC", "AUC", "Median",
         "Med.", "Null", r"$\kappa$", "$p$", "$q$"],
        ["set", "", "", "", "[IQR]", "min--max", "ACC", "$n$", "AUC", "", "",
         "(BH)"],
    ]
    style = [r"\tiny", r"\setlength{\tabcolsep}{3pt}"]
    body = common.tabular("llllccrrcrrr", header, common.align(groups), style)

    return body, facts(stats)


if __name__ == "__main__":
    print(common.write(NAME, render()[0], __file__, SOURCES))
